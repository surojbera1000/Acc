"""User-facing handlers for the Telegram Account Bot."""
import html
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

from config import SUPPORT_CONTACT, CURRENCY_SYMBOL
from database import Database
from utils.keyboards import Keyboards
from utils.helpers import (
    format_price, get_user_display_name, format_order_status, build_delivery_text
)

logger = logging.getLogger(__name__)


def get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    """Get the database instance from bot data."""
    return context.bot_data["db"]


# ═══════════════════════════════════════════
# START / MAIN MENU
# ═══════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show main menu."""
    user = update.effective_user
    db = get_db(context)

    # Register/update user
    await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    welcome_text = (
        f"👋 Welcome, <b>{user.first_name}</b>!\n\n"
        f"🏪 <b>Account Store Bot</b>\n\n"
        f"Buy premium accounts instantly with automatic delivery.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>Buy Account</b> - Browse & purchase accounts\n"
        f"📜 <b>Order History</b> - View your purchases\n"
        f"💰 <b>Deposit</b> - Add funds via UPI\n"
        f"👛 <b>Wallet</b> - Check your balance\n"
        f"👤 <b>Profile</b> - Your account details\n"
        f"📞 <b>Support</b> - Chat with us directly\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Use the buttons below to navigate! 👇"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=Keyboards.main_menu(),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# BUY ACCOUNT
# ═══════════════════════════════════════════

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command or 'Buy Account' button - show countries with stock."""
    db = get_db(context)
    user = update.effective_user

    # Register user if not registered
    await db.get_or_create_user(user_id=user.id, username=user.username,
                                 first_name=user.first_name, last_name=user.last_name)

    countries = await db.get_countries_with_stock()

    if not countries:
        text = (
            "😔 <b>No accounts available right now!</b>\n\n"
            "All accounts are currently sold out.\n"
            "Please check back later or contact support."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML")
        else:
            await update.message.reply_text(text, parse_mode="HTML")
        return

    text = (
        "🌍 <b>Select a Country</b>\n\n"
        "Choose a country to view available accounts:\n"
    )

    keyboard = Keyboards.country_list(countries, prefix="buy")

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def buy_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection for buying."""
    query = update.callback_query
    await query.answer()

    country_id = int(query.data.split("_")[-1])
    db = get_db(context)

    country = await db.get_country(country_id)
    if not country:
        await query.edit_message_text("❌ Country not found.")
        return

    await _show_country_groups(query, db, country, sort="price_asc")


async def _show_country_groups(query, db, country, sort="price_asc"):
    """Render the grouped (category + price) offer list for a country."""
    groups = await db.get_account_groups(country["id"])

    if not groups:
        await query.edit_message_text(
            f"😔 No accounts available for <b>{country['flag']} {country['name']}</b> right now.\n\n"
            f"Please check back later!",
            parse_mode="HTML",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    if sort == "price_desc":
        groups = sorted(groups, key=lambda g: g["price"], reverse=True)
    else:
        groups = sorted(groups, key=lambda g: g["price"])

    total = sum(g["stock_count"] for g in groups)
    text = (
        f"🌍 <b>{country['flag']} {country['name']}</b>\n\n"
        f"📦 Available: <b>{total}</b> accounts across <b>{len(groups)}</b> option(s)\n\n"
        f"Choose an option to purchase:\n"
    )

    keyboard = Keyboards.account_groups(country["id"], groups, sort=sort)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def buy_group_sort_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle sort order of the grouped offer list."""
    query = update.callback_query
    await query.answer()
    _, country_id, sort = query.data.split("_", 2)
    db = get_db(context)
    country = await db.get_country(int(country_id))
    if not country:
        await query.edit_message_text("❌ Country not found.")
        return
    await _show_country_groups(query, db, country, sort=sort)


async def buy_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selecting a (category, price) group - show confirmation."""
    query = update.callback_query
    await query.answer()

    # grp_{country_id}_{category}_{price} — parse from both ends so the
    # category is allowed to contain underscores.
    body = query.data[len("grp_"):]
    country_id_str, rest = body.split("_", 1)
    category, price_str = rest.rsplit("_", 1)
    country_id = int(country_id_str)
    price = float(price_str)
    db = get_db(context)

    country = await db.get_country(country_id)
    account = await db.get_next_available_account(country_id, category, price)
    if not country or not account:
        await query.edit_message_text(
            "❌ This option is no longer available.\nPlease pick another one.",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    groups = await db.get_account_groups(country_id)
    stock = next((g["stock_count"] for g in groups
                  if g["category"] == category and g["price"] == price), 0)
    user_balance = await db.get_user_balance(query.from_user.id)

    text = (
        f"🛒 <b>Confirm Purchase</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 Country: <b>{country['flag']} {country['name']}</b>\n"
        f"🏷 Type: <b>{category}</b>\n"
        f"📦 In stock: <b>{stock}</b>\n"
        f"💰 Price: <b>{format_price(price)}</b>\n"
    )
    if account.get("description"):
        text += f"📝 {account['description']}\n"
    text += (
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👛 Your Balance: <b>{format_price(user_balance)}</b>\n"
    )

    if user_balance < price:
        text += (
            f"\n⚠️ <b>Insufficient balance!</b>\n"
            f"You need <b>{format_price(price - user_balance)}</b> more.\n"
            f"Please deposit funds first."
        )
        keyboard = Keyboards.insufficient_balance()
    else:
        text += f"\n✅ You have enough balance to purchase."
        keyboard = Keyboards.confirm_group_purchase(country_id, category, price)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_group_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm a grouped purchase - picks the next available account & delivers."""
    query = update.callback_query
    await query.answer()

    # cgrp_{country_id}_{category}_{price} — parse from both ends (see above).
    body = query.data[len("cgrp_"):]
    country_id_str, rest = body.split("_", 1)
    category, price_str = rest.rsplit("_", 1)
    country_id = int(country_id_str)
    price = float(price_str)
    db = get_db(context)

    account = await db.get_next_available_account(country_id, category, price)
    if not account:
        await query.edit_message_text(
            "❌ Sorry, this option just sold out!\nPlease pick another one.",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    # Reuse the shared purchase routine with the resolved account id
    await _process_purchase(query, context, account["id"])


async def buy_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle account selection - show purchase confirmation."""
    query = update.callback_query
    await query.answer()

    account_id = int(query.data.split("_")[-1])
    db = get_db(context)

    account = await db.get_account(account_id)
    if not account or account["status"] != "available":
        await query.edit_message_text(
            "❌ This account is no longer available.\n"
            "Please select another one.",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    country = await db.get_country(account["country_id"])
    user_balance = await db.get_user_balance(query.from_user.id)

    text = (
        f"🛒 <b>Confirm Purchase</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 Country: <b>{country['flag']} {country['name']}</b>\n"
        f"📱 Account ID: <b>#{account['id']}</b>\n"
        f"💰 Price: <b>{format_price(account['price'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👛 Your Balance: <b>{format_price(user_balance)}</b>\n"
    )

    if user_balance < account["price"]:
        text += (
            f"\n⚠️ <b>Insufficient balance!</b>\n"
            f"You need <b>{format_price(account['price'] - user_balance)}</b> more.\n"
            f"Please deposit funds first."
        )
        keyboard = Keyboards.insufficient_balance()
    else:
        text += f"\n✅ You have enough balance to purchase."
        keyboard = Keyboards.confirm_purchase(account_id)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase confirmation (legacy per-account flow)."""
    query = update.callback_query
    await query.answer()
    account_id = int(query.data.split("_")[-1])
    await _process_purchase(query, context, account_id)


async def _process_purchase(query, context: ContextTypes.DEFAULT_TYPE, account_id: int):
    """Shared purchase/delivery routine with auto-refund on failure."""
    user_id = query.from_user.id
    db = get_db(context)

    # Double-check account availability
    account = await db.get_account(account_id)
    if not account or account["status"] != "available":
        await query.edit_message_text(
            "❌ Sorry, this account was just sold!\n"
            "Please select another one.",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    # Check balance
    user_balance = await db.get_user_balance(user_id)
    if user_balance < account["price"]:
        await query.edit_message_text(
            "❌ Insufficient balance! Please deposit funds first.",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    # Track progress so the error path only reverses steps that actually happened
    price = account["price"]
    order_id = None
    balance_deducted = False
    account_marked_sold = False

    # Process purchase
    try:
        # Create order
        order_id = await db.create_order(user_id, account_id, price)

        # Create transaction
        tx_id = await db.create_transaction(
            user_id, "purchase", price,
            description=f"Purchase account #{account_id}",
            reference=f"ORDER-{order_id}"
        )

        # Deduct balance
        new_balance = await db.update_balance(user_id, price, "subtract")
        balance_deducted = True
        await db.add_to_total_spent(user_id, price)

        # Complete transaction
        await db.complete_transaction(tx_id, new_balance)

        # Mark account as sold
        await db.mark_account_sold(account_id, user_id)
        account_marked_sold = True

        # Complete order and deliver
        await db.complete_order(order_id)

        # Get fresh account details for delivery
        account = await db.get_account(account_id)
        country = await db.get_country(account["country_id"])

        # Deliver account details
        delivery_text = build_delivery_text(order_id, account, country, new_balance)
        await query.edit_message_text(delivery_text, parse_mode="HTML")
        logger.info(f"Order #{order_id} completed - User {user_id} bought account #{account_id}")

    except Exception as e:
        logger.error(f"Purchase failed for user {user_id}, account {account_id}: {e}")

        # Auto-refund on failure — only reverse what actually happened
        try:
            if order_id is not None:
                await db.fail_order(order_id, "Technical error during delivery")
                await db.refund_order(order_id, "Auto-refund: delivery failed")

            if account_marked_sold:
                await db.mark_account_available(account_id)

            if balance_deducted:
                refund_balance = await db.update_balance(user_id, price, "add")
                await db.add_to_total_spent(user_id, -price)
                refund_tx = await db.create_transaction(
                    user_id, "refund", price,
                    description="Auto-refund for failed order",
                    reference=f"REFUND-ORDER-{order_id}"
                )
                await db.complete_transaction(refund_tx, refund_balance)

            await query.edit_message_text(
                "❌ <b>Delivery Failed</b>\n\n"
                "A technical error occurred during delivery.\n"
                "💰 Your balance has been <b>automatically refunded</b>.\n\n"
                f"If the issue persists, contact support: {SUPPORT_CONTACT}",
                parse_mode="HTML"
            )
        except Exception as refund_error:
            logger.error(f"Refund also failed: {refund_error}")
            await query.edit_message_text(
                "❌ <b>Error Occurred</b>\n\n"
                f"Please contact support immediately: {SUPPORT_CONTACT}\n"
                f"Reference: Order attempt for account #{account_id}",
                parse_mode="HTML"
            )


async def cancel_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase cancellation."""
    query = update.callback_query
    await query.answer("Purchase cancelled.")
    await query.edit_message_text("❌ Purchase cancelled.\n\nUse /buy to browse accounts again.")


async def buy_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button in buy flow."""
    await buy_command(update, context)


# ═══════════════════════════════════════════
# WALLET
# ═══════════════════════════════════════════

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wallet command - show wallet info."""
    user = update.effective_user
    db = get_db(context)

    user_data = await db.get_or_create_user(
        user_id=user.id, username=user.username,
        first_name=user.first_name, last_name=user.last_name
    )

    text = (
        f"👛 <b>Your Wallet</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance: <b>{format_price(user_data['balance'])}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 <b>Statistics:</b>\n"
        f"├ Total Deposited: {format_price(user_data['total_deposits'])}\n"
        f"├ Total Spent: {format_price(user_data['total_spent'])}\n"
        f"└ Member Since: {user_data['joined_at'][:10]}\n\n"
        f"💡 Use /deposit to add funds to your wallet."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


# ═══════════════════════════════════════════
# ORDER HISTORY
# ═══════════════════════════════════════════

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /history command - show order history."""
    user = update.effective_user
    db = get_db(context)

    await db.get_or_create_user(user_id=user.id, username=user.username,
                                 first_name=user.first_name, last_name=user.last_name)

    orders = await db.get_user_orders(user.id)

    if not orders:
        text = (
            "📜 <b>Order History</b>\n\n"
            "You haven't made any purchases yet.\n"
            "Use /buy to browse available accounts!"
        )
    else:
        text = f"📜 <b>Order History</b>\n\n"
        for order in orders[:10]:  # Show last 10 orders
            status = format_order_status(order["status"])
            text += (
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 Order <b>#{order['id']}</b>\n"
                f"🌍 {order.get('country_flag', '')} {order['country_name']}\n"
                f"📱 {order['phone_number']}\n"
                f"💰 {format_price(order['amount'])}\n"
                f"📅 {order['created_at'][:16]}\n"
                f"Status: {status}\n"
            )
        text += "━━━━━━━━━━━━━━━━━━━━━"

        if len(orders) > 10:
            text += f"\n\n<i>Showing last 10 of {len(orders)} orders.</i>"

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


# ═══════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the user's profile: identity, balance and order count."""
    user = update.effective_user
    db = get_db(context)

    user_data = await db.get_or_create_user(
        user_id=user.id, username=user.username,
        first_name=user.first_name, last_name=user.last_name
    )
    orders = await db.get_user_orders(user.id, limit=1000)
    completed = sum(1 for o in orders if o["status"] == "completed")

    text = (
        f"👤 <b>My Profile</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🙍 Name: <b>{html.escape(get_user_display_name(user))}</b>\n"
        f"🔗 Username: {'@' + html.escape(user.username) if user.username else 'Not set'}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balance: <b>{format_price(user_data['balance'])}</b>\n"
        f"🛒 Orders Completed: <b>{completed}</b>\n"
        f"📅 Member Since: {user_data['joined_at'][:10]}"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ═══════════════════════════════════════════
# SUPPORT
# ═══════════════════════════════════════════

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a button that opens a direct chat with the support account."""
    handle = SUPPORT_CONTACT.strip().lstrip("@")
    text = (
        f"📞 <b>Customer Support</b>\n\n"
        f"Need help with an order, deposit or refund?\n"
        f"Tap the button below to chat directly with <b>@{html.escape(handle)}</b>.\n\n"
        f"💡 <i>Share your Order ID or Deposit ID for faster help.</i>"
    )
    await update.message.reply_text(
        text, reply_markup=Keyboards.support_button(SUPPORT_CONTACT), parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# TEXT MESSAGE HANDLER (for menu buttons)
# ═══════════════════════════════════════════

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages from reply keyboard buttons."""
    text = update.message.text

    if text == "🛒 Buy Account":
        await buy_command(update, context)
    elif text == "📜 Order History":
        await history_command(update, context)
    elif text == "💰 Deposit":
        # Import here to avoid circular imports
        from handlers.payment_handlers import deposit_command
        await deposit_command(update, context)
    elif text == "👛 Wallet":
        await wallet_command(update, context)
    elif text == "👤 Profile":
        await profile_command(update, context)
    elif text == "📞 Support":
        await support_command(update, context)
    else:
        # Unknown text - show main menu
        await update.message.reply_text(
            "Please use the menu buttons below 👇",
            reply_markup=Keyboards.main_menu()
        )


# ═══════════════════════════════════════════
# REGISTER HANDLERS
# ═══════════════════════════════════════════

def register_user_handlers(application: Application):
    """Register all user-facing handlers."""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("support", support_command))

    # Buy flow callback handlers
    application.add_handler(CallbackQueryHandler(buy_country_callback, pattern=r"^buy_country_\d+$"))
    # Grouped buy flow (category + price)
    application.add_handler(CallbackQueryHandler(buy_group_sort_callback, pattern=r"^grpsort_\d+_(price_asc|price_desc)$"))
    application.add_handler(CallbackQueryHandler(buy_group_callback, pattern=r"^grp_\d+_.+_\d+$"))
    application.add_handler(CallbackQueryHandler(confirm_group_purchase_callback, pattern=r"^cgrp_\d+_.+_\d+$"))
    # Legacy per-account buy flow (kept for backward compatibility)
    application.add_handler(CallbackQueryHandler(buy_account_callback, pattern=r"^buy_account_\d+$"))
    application.add_handler(CallbackQueryHandler(confirm_purchase_callback, pattern=r"^confirm_buy_\d+$"))
    application.add_handler(CallbackQueryHandler(cancel_buy_callback, pattern=r"^cancel_buy$"))
    application.add_handler(CallbackQueryHandler(buy_back_callback, pattern=r"^buy_back$"))

    # Text message handler (for reply keyboard buttons) - added last with lowest priority
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, text_message_handler
    ))

    logger.info("User handlers registered.")
