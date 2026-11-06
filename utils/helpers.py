"""Helper utility functions."""
import html

from config import ADMIN_IDS, CURRENCY_SYMBOL


def format_price(amount: float) -> str:
    """Format a price with currency symbol."""
    return f"{CURRENCY_SYMBOL}{amount:.2f}"


def _row(account, key):
    """Read a column from a sqlite Row or dict, tolerating older schemas."""
    try:
        value = account[key]
    except (KeyError, IndexError):
        return None
    return value


def build_delivery_text(order_id, account, country, new_balance=None) -> str:
    """Build the account-delivery message shown to the buyer.

    Includes identity (name, username, number), credentials (OTP / 2FA) and a
    security summary (Gmail added, 2FA on/off) for a professional handover.
    """
    icon = _row(account, "icon") or ""
    name = _row(account, "name") or _row(account, "category") or "Account"
    flag = (country or {}).get("flag", "") if country else ""
    cname = (country or {}).get("name", "") if country else ""

    lines = [
        "✅ <b>Purchase Successful!</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"📋 <b>Order #{order_id}</b>",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{(icon + ' ') if icon else ''}<b>{html.escape(str(name))}</b>",
        f"🌍 Country: <b>{flag} {html.escape(str(cname))}</b>",
        f"📞 Number: <code>{html.escape(str(_row(account, 'phone_number') or '—'))}</code>",
    ]

    username = _row(account, "username")
    if username:
        lines.append(f"🔗 Username: <code>{html.escape(str(username))}</code>")
    if _row(account, "otp"):
        lines.append(f"🔑 OTP: <code>{html.escape(str(account['otp']))}</code>")

    two_fa_enabled = _row(account, "two_fa_enabled")
    if two_fa_enabled and _row(account, "two_fa"):
        lines.append(f"🔐 2FA Code: <code>{html.escape(str(account['two_fa']))}</code>")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━",
        "🔒 <b>Security</b>",
        f"📧 Gmail Added: <b>{'✅ Yes' if _row(account, 'gmail_added') else '❌ No'}</b>",
        f"🔐 2FA: <b>{'🟢 On' if two_fa_enabled else '🔴 Off'}</b>",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]

    if new_balance is not None:
        lines.append(f"👛 Remaining Balance: <b>{format_price(new_balance)}</b>")
        lines.append("")
    lines.append("⚠️ <i>Save this information! It won't be shown again.</i>")
    return "\n".join(lines)


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
