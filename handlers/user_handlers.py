"""User-facing handlers for the Telegram Account Bot."""
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

from config import SUPPORT_CONTACT, CURRENCY_SYMBOL, ADMIN_IDS
from database import Database
from utils.keyboards import Keyboards
from utils.helpers import format_price, is_admin, get_user_display_name, format_order_status

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
        f"❓ <b>Help</b> - Contact support\n"
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

    accounts = await db.get_available_accounts(country_id)

    if not accounts:
        await query.edit_message_text(
            f"😔 No accounts available for <b>{country['flag']} {country['name']}</b> right now.\n\n"
            f"Please check back later!",
            parse_mode="HTML",
            reply_markup=Keyboards.back_button("buy_back")
        )
        return

    text = (
        f"🌍 <b>{country['flag']} {country['name']}</b>\n\n"
        f"📦 Available accounts: <b>{len(accounts)}</b>\n\n"
        f"Select an account to purchase:\n"
    )

    keyboard = Keyboards.account_list(accounts, country['name'])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


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
        keyboard = Keyboards.back_button("buy_back")
    else:
        text += f"\n✅ You have enough balance to purchase."
        keyboard = Keyboards.confirm_purchase(account_id)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase confirmation - process the purchase."""
    query = update.callback_query
    await query.answer()

    account_id = int(query.data.split("_")[-1])
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

    # Process purchase. We track progress so a failure can be cleanly rolled back.
    order_id = None
    balance_deducted = False
    try:
        # Create order
        order_id = await db.create_order(user_id, account_id, account["price"])

        # Create transaction
        tx_id = await db.create_transaction(
            user_id, "purchase", account["price"],
            description=f"Purchase account #{account_id}",
            reference=f"ORDER-{order_id}"
        )

        # Deduct balance (auto)
        new_balance = await db.update_balance(user_id, account["price"], "subtract")
        balance_deducted = True
        await db.add_to_total_spent(user_id, account["price"])

        # Complete transaction
        await db.complete_transaction(tx_id, new_balance)

        # Mark account as sold
        await db.mark_account_sold(account_id, user_id)

        # Complete order and deliver
        await db.complete_order(order_id)

        # Get fresh account details for delivery
        account = await db.get_account(account_id)
        country = await db.get_country(account["country_id"])

        # Deliver account details automatically (number / OTP / 2FA)
        delivery_text = (
            f"✅ <b>Purchase Successful!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 <b>Order #{order_id}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🌍 Country: <b>{country['flag']} {country['name']}</b>\n"
            f"📱 Phone: <code>{account['phone_number']}</code>\n"
        )

        if account.get("otp"):
            delivery_text += f"🔑 OTP: <code>{account['otp']}</code>\n"

        if account.get("two_fa"):
            delivery_text += f"🔐 2FA: <code>{account['two_fa']}</code>\n"

        delivery_text += (
            f"\n💰 Amount Paid: <b>{format_price(account['price'])}</b>\n"
            f"👛 Remaining Balance: <b>{format_price(new_balance)}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>Save this information! It won't be shown again.</i>"
        )

        await query.edit_message_text(delivery_text, parse_mode="HTML")
        logger.info(f"Order #{order_id} completed - User {user_id} bought account #{account_id}")

        # Notify admins about the sale (best-effort, never blocks delivery)
        sale_alert = (
            f"🛒 <b>Account Sold</b>\n\n"
            f"📋 Order #{order_id}\n"
            f"👤 Buyer: {get_user_display_name(query.from_user)} "
            f"(<code>{user_id}</code>)\n"
            f"🌍 {country['flag']} {country['name']}\n"
            f"📱 <code>{account['phone_number']}</code>\n"
            f"💰 {format_price(account['price'])}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, sale_alert, parse_mode="HTML")
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Purchase failed for user {user_id}, account {account_id}: {e}")

        # Auto-refund on failure — only undo what actually happened.
        try:
            # Restore balance only if it was actually deducted
            if balance_deducted:
                await db.update_balance(user_id, account["price"], "add")

            # Roll back the order record
            if order_id is not None:
                await db.fail_order(order_id, "Technical error during delivery")
                await db.refund_order(order_id, "Auto-refund: delivery failed")

            # Mark account available again so it can be resold
            await db.mark_account_available(account_id)

            # Record a refund transaction if money had moved
            if balance_deducted:
                refund_balance = await db.get_user_balance(user_id)
                refund_tx = await db.create_transaction(
                    user_id, "refund", account["price"],
                    description="Auto-refund for failed order",
                    reference=f"REFUND-ORDER-{order_id}"
                )
                await db.complete_transaction(refund_tx, refund_balance)

            await query.edit_message_text(
                "❌ <b>Delivery Failed</b>\n\n"
                "A technical error occurred during delivery.\n"
                + ("💰 Your balance has been <b>automatically refunded</b>.\n\n"
                   if balance_deducted else "\n")
                + f"If the issue persists, contact support: {SUPPORT_CONTACT}",
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
# HELP
# ═══════════════════════════════════════════

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show help info."""
    text = (
        f"❓ <b>Help & Support</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>How to buy an account:</b>\n"
        f"1️⃣ Deposit funds using /deposit\n"
        f"2️⃣ Browse accounts using /buy\n"
        f"3️⃣ Select a country and account\n"
        f"4️⃣ Confirm your purchase\n"
        f"5️⃣ Receive account details instantly!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Commands:</b>\n"
        f"/start - Main menu\n"
        f"/buy - Buy an account\n"
        f"/wallet - Check balance\n"
        f"/deposit - Add funds\n"
        f"/history - Order history\n"
        f"/help - This help message\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Need assistance?</b>\n"
        f"📩 Contact support: {SUPPORT_CONTACT}\n\n"
        f"<b>Refund Policy:</b>\n"
        f"If an account fails to deliver, your balance\n"
        f"is automatically refunded to your wallet."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.message.reply_text(text, parse_mode="HTML")


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
    elif text == "❓ Help":
        await help_command(update, context)
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
    application.add_handler(CommandHandler("help", help_command))

    # Buy flow callback handlers
    application.add_handler(CallbackQueryHandler(buy_country_callback, pattern=r"^buy_country_\d+$"))
    application.add_handler(CallbackQueryHandler(buy_account_callback, pattern=r"^buy_account_\d+$"))
    application.add_handler(CallbackQueryHandler(confirm_purchase_callback, pattern=r"^confirm_buy_\d+$"))
    application.add_handler(CallbackQueryHandler(cancel_buy_callback, pattern=r"^cancel_buy$"))
    application.add_handler(CallbackQueryHandler(buy_back_callback, pattern=r"^buy_back$"))

    # Text message handler (for reply keyboard buttons) - added last with lowest priority
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, text_message_handler
    ))

    logger.info("User handlers registered.")
