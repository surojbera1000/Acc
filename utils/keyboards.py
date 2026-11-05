"""Keyboard layouts for the bot.

NOTE on "colours": The Telegram Bot API does NOT allow changing the real
background colour of inline buttons — their colour is controlled by the user's
Telegram theme (light/dark). To create a professional, "coloured" look we use
colour-coded emoji/icons (🟢 positive, 🔴 destructive, 🔵 primary, 🟡 info,
⚫ neutral/navigation) together with balanced layouts and clear grouping.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class Keyboards:
    """All keyboard layouts used in the bot."""

    # ──────────────────────────────────────────
    # MAIN / USER MENUS
    # ──────────────────────────────────────────

    @staticmethod
    def main_menu():
        """Main menu reply keyboard."""
        keyboard = [
            [KeyboardButton("🛒 Buy Account"), KeyboardButton("👛 Wallet")],
            [KeyboardButton("💰 Deposit"), KeyboardButton("📜 Order History")],
            [KeyboardButton("🎁 Offers"), KeyboardButton("👤 Profile")],
            [KeyboardButton("❓ Help"), KeyboardButton("📞 Support")],
        ]
        return ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, input_field_placeholder="Choose an option 👇"
        )

    @staticmethod
    def inline_main_menu():
        """Inline version of the main menu (colour-coded)."""
        keyboard = [
            [InlineKeyboardButton("🛒 Buy Account", callback_data="menu_buy"),
             InlineKeyboardButton("👛 Wallet", callback_data="menu_wallet")],
            [InlineKeyboardButton("💰 Deposit", callback_data="menu_deposit"),
             InlineKeyboardButton("📜 History", callback_data="menu_history")],
            [InlineKeyboardButton("🎁 Offers", callback_data="menu_offers"),
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
        """Admin panel inline keyboard (grouped & colour-coded)."""
        keyboard = [
            [InlineKeyboardButton("🟢 Add Account", callback_data="admin_add_account"),
             InlineKeyboardButton("🟡 Edit Account", callback_data="admin_edit_account")],
            [InlineKeyboardButton("🔴 Remove Account", callback_data="admin_remove_account"),
             InlineKeyboardButton("🔵 Stock Status", callback_data="admin_stock")],
            [InlineKeyboardButton("🧾 View Orders", callback_data="admin_orders"),
             InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🌍 Countries", callback_data="admin_countries"),
             InlineKeyboardButton("💳 Pending Deposits", callback_data="admin_deposits")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
             InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("✖️ Close Panel", callback_data="admin_close")],
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
                label, callback_data=f"buy_account_{acc['id']}"
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
            [InlineKeyboardButton("🟢 Confirm Purchase", callback_data=f"confirm_buy_{account_id}")],
            [InlineKeyboardButton("🔴 Cancel", callback_data="cancel_buy")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def insufficient_balance():
        """Shown when the user cannot afford a purchase."""
        keyboard = [
            [InlineKeyboardButton("💰 Deposit Now", callback_data="menu_deposit")],
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
            [InlineKeyboardButton("💎 Custom Amount", callback_data="deposit_custom")],
            [InlineKeyboardButton("⬅️ Back", callback_data="deposit_back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_confirmation(deposit_id):
        """Payment done confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 I've Paid", callback_data=f"paid_{deposit_id}")],
            [InlineKeyboardButton("📋 Copy UPI ID", callback_data=f"copyupi_{deposit_id}")],
            [InlineKeyboardButton("🔴 Cancel", callback_data=f"cancel_deposit_{deposit_id}")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_verify_deposit(deposit_id):
        """Admin deposit verification keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 Approve", callback_data=f"approve_deposit_{deposit_id}"),
             InlineKeyboardButton("🔴 Reject", callback_data=f"reject_deposit_{deposit_id}")],
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
             InlineKeyboardButton("🔴 Delete", callback_data=f"delete_acc_{account_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_stock")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_delete(account_id):
        """Confirm account deletion."""
        keyboard = [
            [InlineKeyboardButton("🔴 Yes, Delete", callback_data=f"confirm_delete_{account_id}"),
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
            [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{handle}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu_back")],
        ]
        return InlineKeyboardMarkup(keyboard)
