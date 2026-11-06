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
        """Main menu reply keyboard (every button natively coloured)."""
        keyboard = [
            [KeyboardButton("🛒 Buy Account", style=SUCCESS),
             KeyboardButton("👛 Wallet", style=PRIMARY)],
            [KeyboardButton("💰 Deposit", style=SUCCESS),
             KeyboardButton("📜 Order History", style=PRIMARY)],
            [KeyboardButton("👤 Profile", style=PRIMARY),
             KeyboardButton("📞 Support", style=DANGER)],
        ]
        return ReplyKeyboardMarkup(
            keyboard, resize_keyboard=True, input_field_placeholder="Choose an option 👇"
        )

    # ──────────────────────────────────────────
    # ADMIN
    # ──────────────────────────────────────────

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
                label, callback_data=f"{prefix}_country_{country['id']}", style=PRIMARY
            ))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"{prefix}_back", style=PRIMARY)])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def account_list(accounts, country_name):
        """Generate account selection keyboard for buying (legacy per-account)."""
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
        keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="buy_back", style=PRIMARY)])
        return InlineKeyboardMarkup(keyboard)

    # Category icons for a nicer, differentiated buy experience
    CATEGORY_ICONS = {
        "fresh": "🆕", "aged": "⏳", "premium": "💎", "vip": "👑",
        "otp": "🔑", "standard": "📱",
    }

    @classmethod
    def _category_icon(cls, category):
        return cls.CATEGORY_ICONS.get((category or "standard").strip().lower(), "📦")

    @classmethod
    def account_groups(cls, country_id, groups, sort="price_asc"):
        """Grouped offers keyboard: one button per (category, price) with stock.

        ``groups`` items have: category, price, stock_count.
        ``sort`` controls the toggle label (handled by the caller).
        """
        keyboard = []
        for g in groups:
            icon = cls._category_icon(g["category"])
            label = (f"{icon} {g['category']}  •  ₹{g['price']:.0f}  "
                     f"•  {g['stock_count']} left")
            # callback carries country, category and price so the handler is stateless
            cb = f"grp_{country_id}_{g['category']}_{g['price']:.0f}"
            keyboard.append([InlineKeyboardButton(label, callback_data=cb, style=PRIMARY)])

        # Sort toggle
        toggle_label = ("🔽 Price: High → Low" if sort == "price_asc"
                        else "🔼 Price: Low → High")
        next_sort = "price_desc" if sort == "price_asc" else "price_asc"
        keyboard.append([InlineKeyboardButton(
            toggle_label, callback_data=f"grpsort_{country_id}_{next_sort}", style=PRIMARY)])
        keyboard.append([InlineKeyboardButton("⬅️ Back to Countries", callback_data="buy_back", style=PRIMARY)])
        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def confirm_group_purchase(cls, country_id, category, price):
        """Confirmation keyboard for a grouped (category/price) purchase."""
        keyboard = [
            [InlineKeyboardButton(
                "🟢 Confirm Purchase",
                callback_data=f"cgrp_{country_id}_{category}_{price:.0f}", style=SUCCESS)],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"buy_country_{country_id}", style=PRIMARY)],
        ]
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
            [InlineKeyboardButton("⬅️ Back", callback_data="buy_back", style=PRIMARY)],
        ]
        return InlineKeyboardMarkup(keyboard)

    # ──────────────────────────────────────────
    # DEPOSIT / PAYMENT FLOW
    # ──────────────────────────────────────────

    @staticmethod
    def deposit_amounts():
        """Deposit amount selection keyboard."""
        keyboard = [
            [InlineKeyboardButton("₹50", callback_data="deposit_50", style=SUCCESS),
             InlineKeyboardButton("₹100", callback_data="deposit_100", style=SUCCESS),
             InlineKeyboardButton("₹200", callback_data="deposit_200", style=SUCCESS)],
            [InlineKeyboardButton("₹500", callback_data="deposit_500", style=SUCCESS),
             InlineKeyboardButton("₹1000", callback_data="deposit_1000", style=SUCCESS),
             InlineKeyboardButton("₹2000", callback_data="deposit_2000", style=SUCCESS)],
            [InlineKeyboardButton("💎 Custom Amount", callback_data="deposit_custom", style=PRIMARY)],
            [InlineKeyboardButton("⬅️ Back", callback_data="deposit_back", style=PRIMARY)],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_confirmation(deposit_id):
        """Payment done confirmation keyboard."""
        keyboard = [
            [InlineKeyboardButton("🟢 I've Paid", callback_data=f"paid_{deposit_id}", style=SUCCESS)],
            [InlineKeyboardButton("📋 Copy UPI ID", callback_data=f"copyupi_{deposit_id}", style=PRIMARY)],
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

    # ──────────────────────────────────────────
    # SHARED / NAVIGATION
    # ──────────────────────────────────────────

    @staticmethod
    def back_button(callback_data="back_main"):
        """Simple back button."""
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=callback_data, style=PRIMARY)]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def support_button(support_contact):
        """Direct-to-support URL button: opens a private chat with the support account."""
        handle = support_contact.strip().lstrip("@")
        keyboard = [
            [InlineKeyboardButton(f"💬 Chat with @{handle}", url=f"https://t.me/{handle}", style=SUCCESS)],
        ]
        return InlineKeyboardMarkup(keyboard)
