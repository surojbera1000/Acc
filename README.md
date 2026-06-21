# Telegram Account Store Bot

A fully-featured Telegram bot for selling accounts with automatic delivery, UPI payment integration, wallet system, and admin panel.

## Features

### User Side
- **Buy Account** - Browse accounts by country, select and purchase instantly
- **Order History** - View all past purchases and transaction status
- **Deposit** - Add funds via UPI with preset or custom amounts
- **Wallet** - Check balance, total deposits, and spending stats
- **Help** - Instructions and support contact

### Admin Side
- **Add Accounts** - Single or bulk account addition
- **Edit Accounts** - Update phone, OTP, 2FA, or price
- **Remove Accounts** - Delete unsold accounts from stock
- **Stock Status** - Country-wise stock tracking
- **View Orders** - Monitor all user transactions
- **Statistics** - Revenue, users, and sales data
- **Manage Countries** - Add/manage country categories
- **Deposit Verification** - Approve/reject pending deposits

### Safety & Automation
- Auto-refund on failed delivery
- Admin notification for failed deliveries
- Live stock synchronization
- Automatic balance updates after deposit approval

---

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Your Telegram User ID (for admin access)

### 2. Installation

```bash
# Clone/download the project
cd telegram-account-bot

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Edit `.env` with your details:

```env
# Telegram Bot Token (get from @BotFather)
BOT_TOKEN=your_bot_token_here

# Admin Telegram User IDs (comma-separated)
ADMIN_IDS=123456789,987654321

# UPI Payment Details
UPI_ID=your-upi@bank
UPI_NAME=Account Store

# Support Contact
SUPPORT_CONTACT=@Senkaizen

# Database Path (default: bot_database.db)
DATABASE_PATH=bot_database.db
```

### 4. Run the Bot

```bash
python bot.py
```

---

## Bot Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot / Main menu |
| `/buy` | Browse and buy accounts |
| `/wallet` | Check wallet balance |
| `/deposit` | Deposit funds via UPI |
| `/history` | View order history |
| `/help` | Get help & support |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |
| `/addcountry Name\|CODE\|Flag` | Add a country |
| `/addaccount country_id\|phone\|price\|otp\|2fa` | Add single account |
| `/bulkadd` | Bulk add multiple accounts |
| `/editaccount ID\|field\|value` | Edit account details |
| `/removeaccount ID` | Remove an account |
| `/approve DEPOSIT_ID` | Approve a deposit |
| `/reject DEPOSIT_ID` | Reject a deposit |

---

## Admin Quick Start

### Step 1: Add a Country
```
/addcountry India|IN|🇮🇳
/addcountry United States|US|🇺🇸
/addcountry United Kingdom|UK|🇬🇧
```

### Step 2: Add Accounts
Single account:
```
/addaccount 1|+919876543210|150|1234|backup_code_here
```

Bulk add (same country & price):
```
/bulkadd 1|150
+919876543210|1234|backup1
+919876543211|5678|backup2
+919876543212|9012|-
```

### Step 3: Monitor
- Use `/admin` to access the full admin panel
- Deposits will appear for approval automatically
- Failed deliveries trigger admin notifications

---

## Project Structure

```
telegram-account-bot/
├── bot.py                  # Main entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── database/
│   ├── __init__.py
│   └── db.py              # Database operations (SQLite)
├── handlers/
│   ├── __init__.py
│   ├── user_handlers.py   # User-facing handlers
│   ├── admin_handlers.py  # Admin panel handlers
│   └── payment_handlers.py # Deposit/payment handlers
├── payments/
│   ├── __init__.py
│   └── delivery.py        # Delivery service with auto-refund
└── utils/
    ├── __init__.py
    ├── keyboards.py        # All keyboard layouts
    └── helpers.py          # Utility functions
```

---

## Purchase Flow

```
User selects country → Picks account → Confirms purchase
    → Balance deducted → Account details sent automatically
    → If delivery fails → Auto-refund to wallet + Admin notified
```

## Deposit Flow

```
User selects amount → UPI details shown → User pays & enters UTR
    → Admin notified → Admin approves → Balance credited automatically
    → User notified of successful deposit
```

---

## Safety Features

1. **Auto-Refund**: If delivery fails for any technical reason, the user's balance is automatically restored.
2. **Admin Alerts**: Admins are notified of every failed delivery and pending deposit.
3. **Double-Check**: Account availability is verified at purchase time to prevent race conditions.
4. **Transaction Logging**: All financial operations are logged with before/after balances.

---

## Tech Stack

- **Python 3.10+**
- **python-telegram-bot 21.x** - Telegram Bot API
- **aiosqlite** - Async SQLite database
- **python-dotenv** - Environment variable management

---

## Support

Contact: @Senkaizen
