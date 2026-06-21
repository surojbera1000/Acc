"""Database module for the Telegram Account Bot."""
import aiosqlite
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import DATABASE_PATH


class Database:
    """Handles all database operations."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to the database and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()

    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()

    async def _create_tables(self):
        """Create all required tables."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0.0,
                total_spent REAL DEFAULT 0.0,
                total_deposits REAL DEFAULT 0.0,
                joined_at TEXT DEFAULT (datetime('now')),
                is_banned INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                code TEXT UNIQUE NOT NULL,
                flag TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                phone_number TEXT NOT NULL,
                otp TEXT,
                two_fa TEXT,
                session TEXT,
                price REAL NOT NULL,
                status TEXT DEFAULT 'available',
                added_by INTEGER,
                added_at TEXT DEFAULT (datetime('now')),
                sold_to INTEGER,
                sold_at TEXT,
                FOREIGN KEY (country_id) REFERENCES countries(id),
                FOREIGN KEY (added_by) REFERENCES users(user_id),
                FOREIGN KEY (sold_to) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT,
                refunded_at TEXT,
                refund_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_before REAL DEFAULT 0.0,
                balance_after REAL DEFAULT 0.0,
                reference TEXT,
                description TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                upi_reference TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                verified_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_accounts_country ON accounts(country_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
            CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_deposits_user ON deposits(user_id);
            CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status);
        """)
        await self._db.commit()
        await self._migrate()

    async def _migrate(self):
        """Apply lightweight schema migrations for existing databases."""
        # Add the `session` column to accounts if an older DB doesn't have it.
        cursor = await self._db.execute("PRAGMA table_info(accounts)")
        columns = [row["name"] for row in await cursor.fetchall()]
        if "session" not in columns:
            await self._db.execute("ALTER TABLE accounts ADD COLUMN session TEXT")
            await self._db.commit()

    # ═══════════════════════════════════════════
    # USER OPERATIONS
    # ═══════════════════════════════════════════

    async def get_or_create_user(self, user_id: int, username: str = None,
                                  first_name: str = None, last_name: str = None) -> Dict:
        """Get existing user or create a new one."""
        cursor = await self._db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        user = await cursor.fetchone()

        if user:
            # Update user info if changed
            await self._db.execute(
                """UPDATE users SET username = ?, first_name = ?, last_name = ?
                   WHERE user_id = ?""",
                (username, first_name, last_name, user_id)
            )
            await self._db.commit()
            cursor = await self._db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            user = await cursor.fetchone()
        else:
            await self._db.execute(
                """INSERT INTO users (user_id, username, first_name, last_name)
                   VALUES (?, ?, ?, ?)""",
                (user_id, username, first_name, last_name)
            )
            await self._db.commit()
            cursor = await self._db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            user = await cursor.fetchone()

        return dict(user)

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get a user by ID."""
        cursor = await self._db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_user_balance(self, user_id: int) -> float:
        """Get user's current balance."""
        cursor = await self._db.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row["balance"] if row else 0.0

    async def update_balance(self, user_id: int, amount: float, operation: str = "add") -> float:
        """Update user balance. Returns new balance."""
        current = await self.get_user_balance(user_id)
        if operation == "add":
            new_balance = current + amount
        elif operation == "subtract":
            new_balance = current - amount
        else:
            raise ValueError(f"Invalid operation: {operation}")

        await self._db.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (new_balance, user_id)
        )
        await self._db.commit()
        return new_balance

    async def add_to_total_spent(self, user_id: int, amount: float):
        """Add to user's total spent."""
        await self._db.execute(
            "UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await self._db.commit()

    async def add_to_total_deposits(self, user_id: int, amount: float):
        """Add to user's total deposits."""
        await self._db.execute(
            "UPDATE users SET total_deposits = total_deposits + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await self._db.commit()

    # ═══════════════════════════════════════════
    # COUNTRY OPERATIONS
    # ═══════════════════════════════════════════

    async def add_country(self, name: str, code: str, flag: str = "") -> int:
        """Add a new country. Returns the country ID."""
        cursor = await self._db.execute(
            "INSERT OR IGNORE INTO countries (name, code, flag) VALUES (?, ?, ?)",
            (name, code.upper(), flag)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_countries(self, active_only: bool = True) -> List[Dict]:
        """Get all countries."""
        query = "SELECT * FROM countries"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        cursor = await self._db.execute(query)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_country(self, country_id: int) -> Optional[Dict]:
        """Get a country by ID."""
        cursor = await self._db.execute(
            "SELECT * FROM countries WHERE id = ?", (country_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_countries_with_stock(self) -> List[Dict]:
        """Get countries that have available accounts in stock."""
        cursor = await self._db.execute("""
            SELECT c.*, COUNT(a.id) as stock_count
            FROM countries c
            JOIN accounts a ON a.country_id = c.id AND a.status = 'available'
            WHERE c.is_active = 1
            GROUP BY c.id
            HAVING stock_count > 0
            ORDER BY c.name
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════
    # ACCOUNT OPERATIONS
    # ═══════════════════════════════════════════

    async def add_account(self, country_id: int, phone_number: str, price: float,
                          otp: str = None, two_fa: str = None, session: str = None,
                          added_by: int = None) -> int:
        """Add a new account to stock. Returns account ID."""
        cursor = await self._db.execute(
            """INSERT INTO accounts (country_id, phone_number, otp, two_fa, session, price, added_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (country_id, phone_number, otp, two_fa, session, price, added_by)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_available_accounts(self, country_id: int) -> List[Dict]:
        """Get available accounts for a country."""
        cursor = await self._db.execute(
            """SELECT * FROM accounts
               WHERE country_id = ? AND status = 'available'
               ORDER BY price ASC""",
            (country_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_account(self, account_id: int) -> Optional[Dict]:
        """Get an account by ID."""
        cursor = await self._db.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def mark_account_sold(self, account_id: int, user_id: int):
        """Mark an account as sold."""
        await self._db.execute(
            """UPDATE accounts SET status = 'sold', sold_to = ?, sold_at = datetime('now')
               WHERE id = ?""",
            (user_id, account_id)
        )
        await self._db.commit()

    async def mark_account_available(self, account_id: int):
        """Mark an account as available again (for refund cases)."""
        await self._db.execute(
            """UPDATE accounts SET status = 'available', sold_to = NULL, sold_at = NULL
               WHERE id = ?""",
            (account_id,)
        )
        await self._db.commit()

    async def update_account(self, account_id: int, **kwargs):
        """Update account details."""
        valid_fields = ["phone_number", "otp", "two_fa", "session", "price", "status", "country_id"]
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [account_id]

        await self._db.execute(
            f"UPDATE accounts SET {set_clause} WHERE id = ?", values
        )
        await self._db.commit()

    async def delete_account(self, account_id: int):
        """Delete an account from stock."""
        await self._db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await self._db.commit()

    async def get_stock_summary(self) -> List[Dict]:
        """Get stock summary by country."""
        cursor = await self._db.execute("""
            SELECT c.name, c.code, c.flag,
                   COUNT(CASE WHEN a.status = 'available' THEN 1 END) as available,
                   COUNT(CASE WHEN a.status = 'sold' THEN 1 END) as sold,
                   COUNT(a.id) as total
            FROM countries c
            LEFT JOIN accounts a ON a.country_id = c.id
            WHERE c.is_active = 1
            GROUP BY c.id
            ORDER BY c.name
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_all_accounts(self, status: str = None, country_id: int = None) -> List[Dict]:
        """Get all accounts with optional filters."""
        query = """
            SELECT a.*, c.name as country_name, c.flag as country_flag
            FROM accounts a
            JOIN countries c ON a.country_id = c.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND a.status = ?"
            params.append(status)
        if country_id:
            query += " AND a.country_id = ?"
            params.append(country_id)

        query += " ORDER BY a.added_at DESC"
        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════
    # ORDER OPERATIONS
    # ═══════════════════════════════════════════

    async def create_order(self, user_id: int, account_id: int, amount: float) -> int:
        """Create a new order. Returns order ID."""
        cursor = await self._db.execute(
            """INSERT INTO orders (user_id, account_id, amount, status)
               VALUES (?, ?, ?, 'pending')""",
            (user_id, account_id, amount)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def complete_order(self, order_id: int):
        """Mark an order as completed."""
        await self._db.execute(
            """UPDATE orders SET status = 'completed', delivery_status = 'delivered',
               completed_at = datetime('now') WHERE id = ?""",
            (order_id,)
        )
        await self._db.commit()

    async def fail_order(self, order_id: int, reason: str = "Delivery failed"):
        """Mark an order as failed."""
        await self._db.execute(
            """UPDATE orders SET status = 'failed', delivery_status = 'failed',
               completed_at = datetime('now') WHERE id = ?""",
            (order_id,)
        )
        await self._db.commit()

    async def refund_order(self, order_id: int, reason: str = "Auto-refund"):
        """Mark an order as refunded."""
        await self._db.execute(
            """UPDATE orders SET status = 'refunded', refunded_at = datetime('now'),
               refund_reason = ? WHERE id = ?""",
            (reason, order_id)
        )
        await self._db.commit()

    async def get_user_orders(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's order history."""
        cursor = await self._db.execute(
            """SELECT o.*, a.phone_number, c.name as country_name, c.flag as country_flag
               FROM orders o
               JOIN accounts a ON o.account_id = a.id
               JOIN countries c ON a.country_id = c.id
               WHERE o.user_id = ?
               ORDER BY o.created_at DESC
               LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_order(self, order_id: int) -> Optional[Dict]:
        """Get an order by ID."""
        cursor = await self._db.execute(
            """SELECT o.*, a.phone_number, a.otp, a.two_fa, a.session,
                      c.name as country_name, c.flag as country_flag
               FROM orders o
               JOIN accounts a ON o.account_id = a.id
               JOIN countries c ON a.country_id = c.id
               WHERE o.id = ?""",
            (order_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_orders(self, limit: int = 50) -> List[Dict]:
        """Get all orders (admin view)."""
        cursor = await self._db.execute(
            """SELECT o.*, u.username, u.first_name,
                      a.phone_number, c.name as country_name
               FROM orders o
               JOIN users u ON o.user_id = u.user_id
               JOIN accounts a ON o.account_id = a.id
               JOIN countries c ON a.country_id = c.id
               ORDER BY o.created_at DESC
               LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════
    # TRANSACTION OPERATIONS
    # ═══════════════════════════════════════════

    async def create_transaction(self, user_id: int, type_: str, amount: float,
                                  description: str = "", reference: str = "") -> int:
        """Create a transaction record. Returns transaction ID."""
        balance = await self.get_user_balance(user_id)
        cursor = await self._db.execute(
            """INSERT INTO transactions (user_id, type, amount, balance_before,
               description, reference, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (user_id, type_, amount, balance, description, reference)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def complete_transaction(self, transaction_id: int, new_balance: float):
        """Complete a transaction."""
        await self._db.execute(
            """UPDATE transactions SET status = 'completed', balance_after = ?,
               completed_at = datetime('now') WHERE id = ?""",
            (new_balance, transaction_id)
        )
        await self._db.commit()

    async def fail_transaction(self, transaction_id: int):
        """Mark a transaction as failed."""
        await self._db.execute(
            """UPDATE transactions SET status = 'failed',
               completed_at = datetime('now') WHERE id = ?""",
            (transaction_id,)
        )
        await self._db.commit()

    async def get_user_transactions(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's transaction history."""
        cursor = await self._db.execute(
            """SELECT * FROM transactions
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════
    # DEPOSIT OPERATIONS
    # ═══════════════════════════════════════════

    async def create_deposit(self, user_id: int, amount: float, upi_reference: str = "") -> int:
        """Create a deposit record. Returns deposit ID."""
        cursor = await self._db.execute(
            """INSERT INTO deposits (user_id, amount, upi_reference, status)
               VALUES (?, ?, ?, 'pending')""",
            (user_id, amount, upi_reference)
        )
        await self._db.commit()
        return cursor.lastrowid

    async def verify_deposit(self, deposit_id: int):
        """Mark a deposit as verified."""
        await self._db.execute(
            """UPDATE deposits SET status = 'verified', verified_at = datetime('now')
               WHERE id = ?""",
            (deposit_id,)
        )
        await self._db.commit()

    async def reject_deposit(self, deposit_id: int):
        """Mark a deposit as rejected."""
        await self._db.execute(
            "UPDATE deposits SET status = 'rejected' WHERE id = ?",
            (deposit_id,)
        )
        await self._db.commit()

    async def get_pending_deposits(self) -> List[Dict]:
        """Get all pending deposits (admin view)."""
        cursor = await self._db.execute(
            """SELECT d.*, u.username, u.first_name
               FROM deposits d
               JOIN users u ON d.user_id = u.user_id
               WHERE d.status = 'pending'
               ORDER BY d.created_at ASC"""
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_deposit(self, deposit_id: int) -> Optional[Dict]:
        """Get a deposit by ID."""
        cursor = await self._db.execute(
            "SELECT * FROM deposits WHERE id = ?", (deposit_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_user_deposits(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get user's deposit history."""
        cursor = await self._db.execute(
            """SELECT * FROM deposits
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ═══════════════════════════════════════════
    # STATISTICS (Admin)
    # ═══════════════════════════════════════════

    async def get_stats(self) -> Dict:
        """Get bot statistics."""
        stats = {}

        cursor = await self._db.execute("SELECT COUNT(*) as count FROM users")
        row = await cursor.fetchone()
        stats["total_users"] = row["count"]

        cursor = await self._db.execute(
            "SELECT COUNT(*) as count FROM accounts WHERE status = 'available'"
        )
        row = await cursor.fetchone()
        stats["available_accounts"] = row["count"]

        cursor = await self._db.execute(
            "SELECT COUNT(*) as count FROM accounts WHERE status = 'sold'"
        )
        row = await cursor.fetchone()
        stats["sold_accounts"] = row["count"]

        cursor = await self._db.execute(
            "SELECT COUNT(*) as count FROM orders WHERE status = 'completed'"
        )
        row = await cursor.fetchone()
        stats["completed_orders"] = row["count"]

        cursor = await self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM orders WHERE status = 'completed'"
        )
        row = await cursor.fetchone()
        stats["total_revenue"] = row["total"]

        cursor = await self._db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM deposits WHERE status = 'verified'"
        )
        row = await cursor.fetchone()
        stats["total_deposits"] = row["total"]

        return stats
