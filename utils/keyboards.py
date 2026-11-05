"""Keyboard layouts for the bot.

COLOURED BUTTONS (Bot API 9.4 / python-telegram-bot 22.7+):
Telegram now supports *native* coloured inline/reply buttons via the ``style``
field. We use the ``KeyboardButtonStyle`` constants:

    SUCCESS / GREEN   -> 🟢 positive actions (confirm, approve, add, "I've paid")
    DANGER  / RED     -> 🔴 destructive actions (cancel, reject, delete, remove)
    PRIMARY / BLUE    -> 🔵 primary / navigation actions (buy, deposit, stock)

Notes:
- Native colours only render on Telegram clients released after 9 Feb 2026.
  Older clients ignore ``style`` and show plain buttons — so we ALSO keep
  colour-coded emoji in the labels as a graceful fallback.
- ``style`` cannot be combined on the same button with url/callback_game/etc.
  being the "type"; it is an extra visual attribute, so it works fine
  alongside ``callback_data`` and ``url`` buttons.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import KeyboardButtonStyle

# Convenient aliases
PRIMARY = KeyboardButtonStyle.PRIMARY   # blue
SUCCESS = KeyboardButtonStyle.SUCCESS   # green
DANGER = KeyboardButtonStyle.DANGER     # red


class Keyboards:
    """All keyboard layouts used in the bot."""

    # ──────────────────────────────────────────
    # MAIN / USER MENUS
    # ──────────────────────────────────────────

    @staticmethod
    def main_menu():
        """Main menu reply keyboard (native coloured buttons)."""
        keyboard = [
            [KeyboardButton("🛒 Buy Account", style=PRIMARY),
             KeyboardButton("👛 Wallet", style=PRIMARY)],
            [KeyboardButton("💰 Deposit", style=SUCCESS),
             KeyboardButton("📜 Order History")],
            [KeyboardButton("🎁 Offers", style=SUCCESS),
             KeyboardButton("👤 Profile")],
            [KeyboardButton("❓ Help"),
             KeyboardButton("📞 Support")],
        ]
        return ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, input_field_placeholder="Choose an option 👇"
        )

    @staticmethod
    def inline_main_menu():
        """Inline version of the main menu (native coloured buttons)."""
        keyboard = [
            [InlineKeyboardButton("🛒 Buy Account", callback_data="menu_buy", style=PRIMARY),
             InlineKeyboardButton("👛 Wallet", callback_data="menu_wallet", style=PRIMARY)],
            [InlineKeyboardButton("💰 Deposit", callback_data="menu_deposit", style=SUCCESS),
             InlineKeyboardButton("📜 History", callback_data="menu_history")],
            [InlineKeyboardButton("🎁 Offers", callback_data="menu_offers", style=SUCCESS),
             InlineKeyboardButton("👤 Profile", callback_data="menu_profile")],
            [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
             InlineKeyboardButton("📞 Support", callback_data="menu_support")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # ADMIN PANEL
    # ──────────────────────────────────────────

    @staticmethod
    def admin_menu():
        """Admin panel inline keyboard (grouped & natively colour-coded)."""
        keyboard = [
            [InlineKeyboardButton("🟢 Add Account", callback_data="admin_add_account", style=SUCCESS),
             InlineKeyboardButton("🟡 Edit Account", callback_data="admin_edit_account")],
            [InlineKeyboardButton("🔴 Remove Account", callback_data="admin_remove_account", style=DANGER),
             InlineKeyboardButton("🔵 Stock Status", callback_data="admin_stock", style=PRIMARY)],
            [InlineKeyboardButton("🧾 View Orders", callback_data="admin_orders"),
             InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🌍 Countries", callback_data="admin_countries"),
             InlineKeyboardButton("💳 Pending Deposits", callback_data="admin_deposits", style=PRIMARY)],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
             InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("✖️ Close Panel", callback_data="admin_close", style=DANGER)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # BUY FLOW
    # ──────────────────────────────────────────

    @staticmethod
    def country_list(countries, prefix="buy"):
        """Generate country selection keyboard."""
        keyboard = []
        row = []
        for country in countries:
            flag = country.get("flag", "🌍")
            name = country["name"]
            stock = country.get("stock_count", "")
            label = f"{flag} {name}"
            if stock != "":
                label += f"  •  {stock} left"
            row.append(InlineKeyboardButton(
                label, callback_data=f"{prefix}_country_{country['id']}"
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"{prefix}_back")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def account_list(accounts, country_name):
        """Generate account selection keyboard for buying."""
        keyboard = []
        row = []
        for acc in accounts:
            label = f"📱 #{acc['id']}  •  ₹{acc['price']:.0f}"
            row.append(InlineKeyboardButton(
                label, callback_data=f"buy_account_{acc['id']}", style=PRIMARY
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="buy_back")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_purchase(account_id):
        """Purchase confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 Confirm Purchase", callback_data=f"confirm_buy_{account_id}", style=SUCCESS)],
            [InlineKeyboardButton("🔴 Cancel", callback_data="cancel_buy", style=DANGER)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def insufficient_balance():
        """Shown when the user cannot afford a purchase."""
        keyboard = [
            [InlineKeyboardButton("💰 Deposit Now", callback_data="menu_deposit", style=SUCCESS)],
            [InlineKeyboardButton("⬅️ Back", callback_data="buy_back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # DEPOSIT / PAYMENT FLOW
    # ──────────────────────────────────────────

    @staticmethod
    def deposit_amounts():
        """Deposit amount selection keyboard."""
        keyboard = [
            [InlineKeyboardButton("₹50", callback_data="deposit_50"),
             InlineKeyboardButton("₹100", callback_data="deposit_100"),
             InlineKeyboardButton("₹200", callback_data="deposit_200")],
            [InlineKeyboardButton("₹500", callback_data="deposit_500"),
             InlineKeyboardButton("₹1000", callback_data="deposit_1000"),
             InlineKeyboardButton("₹2000", callback_data="deposit_2000")],
            [InlineKeyboardButton("💎 Custom Amount", callback_data="deposit_custom", style=PRIMARY)],
            [InlineKeyboardButton("⬅️ Back", callback_data="deposit_back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_confirmation(deposit_id):
        """Payment done confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 I've Paid", callback_data=f"paid_{deposit_id}", style=SUCCESS)],
            [InlineKeyboardButton("📋 Copy UPI ID", callback_data=f"copyupi_{deposit_id}")],
            [InlineKeyboardButton("🔴 Cancel", callback_data=f"cancel_deposit_{deposit_id}", style=DANGER)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_verify_deposit(deposit_id):
        """Admin deposit verification keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 Approve", callback_data=f"approve_deposit_{deposit_id}", style=SUCCESS),
             InlineKeyboardButton("🔴 Reject", callback_data=f"reject_deposit_{deposit_id}", style=DANGER)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # ADMIN ACCOUNT ACTIONS
    # ──────────────────────────────────────────

    @staticmethod
    def admin_account_actions(account_id):
        """Admin actions for a specific account."""
        keyboard = [
            [InlineKeyboardButton("🟡 Edit", callback_data=f"edit_acc_{account_id}"),
             InlineKeyboardButton("🔴 Delete", callback_data=f"delete_acc_{account_id}", style=DANGER)],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_stock")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_delete(account_id):
        """Confirm account deletion."""
        keyboard = [
            [InlineKeyboardButton("🔴 Yes, Delete", callback_data=f"confirm_delete_{account_id}", style=DANGER),
             InlineKeyboardButton("⚫ No, Cancel", callback_data="admin_stock")],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # SHARED / NAVIGATION
    # ──────────────────────────────────────────

    @staticmethod
    def back_button(callback_data="back_main"):
        """Simple back button."""
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def support_button(support_contact):
        """Direct-to-support URL button (opens chat)."""
        handle = support_contact.lstrip("@")
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{handle}", style=PRIMARY)],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")],
        ]
        return InlineKeyboardMarkup(keyboard)
