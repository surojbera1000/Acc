"""Helper utility functions."""
from config import ADMIN_IDS, CURRENCY_SYMBOL


def format_price(amount: float) -> str:
    """Format a price with currency symbol."""
    return f"{CURRENCY_SYMBOL}{amount:.2f}"


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin."""
    return user_id in ADMIN_IDS


def get_user_display_name(user) -> str:
    """Get display name for a user."""
    if hasattr(user, 'first_name'):
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        return name.strip() or user.username or str(user.id)
    # Dict format
    name = user.get("first_name", "") or ""
    if user.get("last_name"):
        name += f" {user['last_name']}"
    return name.strip() or user.get("username", "") or str(user.get("user_id", "Unknown"))


def format_order_status(status: str) -> str:
    """Format order status with emoji."""
    status_map = {
        "pending": "⏳ Pending",
        "completed": "✅ Completed",
        "failed": "❌ Failed",
        "refunded": "💰 Refunded",
    }
    return status_map.get(status, status)


def format_transaction_type(type_: str) -> str:
    """Format transaction type with emoji."""
    type_map = {
        "deposit": "💰 Deposit",
        "purchase": "🛒 Purchase",
        "refund": "↩️ Refund",
    }
    return type_map.get(type_, type_)
