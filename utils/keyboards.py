"""Keyboard layouts for the bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


class Keyboards:
    """All keyboard layouts used in the bot."""

    @staticmethod
    def main_menu():
        """Main menu reply keyboard."""
        keyboard = [
            [KeyboardButton("🛒 Buy Account"), KeyboardButton("📜 Order History")],
            [KeyboardButton("💰 Deposit"), KeyboardButton("👛 Wallet")],
            [KeyboardButton("❓ Help")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def admin_menu():
        """Admin panel inline keyboard."""
        keyboard = [
            [InlineKeyboardButton("➕ Add Account", callback_data="admin_add_account"),
             InlineKeyboardButton("📝 Edit Account", callback_data="admin_edit_account")],
            [InlineKeyboardButton("🗑 Remove Account", callback_data="admin_remove_account"),
             InlineKeyboardButton("📊 Stock Status", callback_data="admin_stock")],
            [InlineKeyboardButton("👥 View Orders", callback_data="admin_orders"),
             InlineKeyboardButton("📈 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🌍 Manage Countries", callback_data="admin_countries"),
             InlineKeyboardButton("💳 Pending Deposits", callback_data="admin_deposits")],
            [InlineKeyboardButton("🔙 Close", callback_data="admin_close")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def country_list(countries, prefix="buy"):
        """Generate country selection keyboard."""
        keyboard = []
        row = []
        for i, country in enumerate(countries):
            flag = country.get("flag", "")
            name = country["name"]
            stock = country.get("stock_count", "")
            label = f"{flag} {name}"
            if stock:
                label += f" ({stock})"
            row.append(InlineKeyboardButton(
                label, callback_data=f"{prefix}_country_{country['id']}"
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"{prefix}_back")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def account_list(accounts, country_name):
        """Generate account selection keyboard for buying."""
        keyboard = []
        for acc in accounts:
            label = f"📱 #{acc['id']} - ₹{acc['price']:.0f}"
            keyboard.append([InlineKeyboardButton(
                label, callback_data=f"buy_account_{acc['id']}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Back to Countries", callback_data="buy_back")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_purchase(account_id):
        """Purchase confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_buy_{account_id}"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy")]
        ]
        return InlineKeyboardMarkup(keyboard)

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
            [InlineKeyboardButton("🔙 Back", callback_data="deposit_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_confirmation(deposit_id):
        """Payment done confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("✅ I've Paid", callback_data=f"paid_{deposit_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_deposit_{deposit_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_verify_deposit(deposit_id):
        """Admin deposit verification keyboard."""
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_account_actions(account_id):
        """Admin actions for a specific account."""
        keyboard = [
            [InlineKeyboardButton("📝 Edit", callback_data=f"edit_acc_{account_id}"),
             InlineKeyboardButton("🗑 Delete", callback_data=f"delete_acc_{account_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_stock")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_button(callback_data="back_main"):
        """Simple back button."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=callback_data)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_delete(account_id):
        """Confirm account deletion."""
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{account_id}"),
             InlineKeyboardButton("❌ No, Cancel", callback_data="admin_stock")]
        ]
        return InlineKeyboardMarkup(keyboard)
