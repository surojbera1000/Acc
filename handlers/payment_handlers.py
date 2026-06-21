"""Payment/Deposit handlers for the Telegram Account Bot."""
import logging
import random
import string
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

from config import UPI_ID, UPI_NAME, CURRENCY_SYMBOL, SUPPORT_CONTACT, ADMIN_IDS
from database import Database
from utils.keyboards import Keyboards
from utils.helpers import format_price

logger = logging.getLogger(__name__)

# Conversation states
WAITING_CUSTOM_AMOUNT = 1
WAITING_UTR = 2


def get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    """Get the database instance from bot data."""
    return context.bot_data["db"]


def generate_unique_ref() -> str:
    """Generate a unique payment reference for tracking."""
    chars = string.ascii_uppercase + string.digits
    return "PAY" + "".join(random.choices(chars, k=8))



# ═══════════════════════════════════════════
# DEPOSIT FLOW
# ═══════════════════════════════════════════

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit command - show deposit options."""
    user = update.effective_user
    db = get_db(context)

    await db.get_or_create_user(user_id=user.id, username=user.username,
                                 first_name=user.first_name, last_name=user.last_name)

    balance = await db.get_user_balance(user.id)

    text = (
        f"💰 <b>Deposit Funds</b>\n\n"
        f"👛 Current Balance: <b>{format_price(balance)}</b>\n\n"
        f"Select an amount to deposit or choose custom amount:\n"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=Keyboards.deposit_amounts(), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=Keyboards.deposit_amounts(), parse_mode="HTML"
        )


async def deposit_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit amount selection."""
    query = update.callback_query
    await query.answer()

    amount = int(query.data.split("_")[1])
    await show_payment_details(query, context, amount)


async def deposit_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom deposit amount request."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "💎 <b>Custom Deposit Amount</b>\n\n"
        "Please enter the amount you want to deposit (in ₹):\n"
        "<i>Minimum: ₹10 | Maximum: ₹50,000</i>",
        parse_mode="HTML"
    )

    # Store state for next message
    context.user_data["awaiting_custom_amount"] = True


async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom amount input from user."""
    if not context.user_data.get("awaiting_custom_amount"):
        return False  # Not in custom amount flow

    text = update.message.text.strip()

    # Remove currency symbol if present
    text = text.replace("₹", "").replace(",", "").strip()

    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number.\n"
            "Example: <code>500</code>",
            parse_mode="HTML"
        )
        return True

    if amount < 10:
        await update.message.reply_text("❌ Minimum deposit is ₹10.")
        return True

    if amount > 50000:
        await update.message.reply_text("❌ Maximum deposit is ₹50,000.")
        return True

    context.user_data["awaiting_custom_amount"] = False
    amount = int(amount)  # Round to whole number

    # Show payment details
    await show_payment_details_message(update, context, amount)
    return True



# ═══════════════════════════════════════════
# PAYMENT DETAILS & UPI
# ═══════════════════════════════════════════

async def show_payment_details(query, context: ContextTypes.DEFAULT_TYPE, amount: int):
    """Show UPI payment details (from callback query)."""
    user_id = query.from_user.id
    db = get_db(context)

    # Create a pending deposit record
    deposit_id = await db.create_deposit(user_id, amount)
    ref = generate_unique_ref()

    # Generate UPI deep link
    upi_link = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={ref}"

    text = (
        f"💳 <b>Payment Details</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: <b>{format_price(amount)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        f"👤 <b>Name:</b> {UPI_NAME}\n"
        f"🔖 <b>Reference:</b> <code>{ref}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Instructions:</b>\n"
        f"1️⃣ Copy the UPI ID above\n"
        f"2️⃣ Open any UPI app (GPay, PhonePe, Paytm)\n"
        f"3️⃣ Send <b>{format_price(amount)}</b> to the UPI ID\n"
        f"4️⃣ After payment, click \"I've Paid\" below\n"
        f"5️⃣ Enter your UTR/Transaction ID\n\n"
        f"⚠️ <i>Amount must match exactly!</i>\n"
        f"⏳ <i>Payment will be verified and credited automatically.</i>"
    )

    # Store deposit info in user_data for later
    context.user_data["pending_deposit_id"] = deposit_id
    context.user_data["pending_amount"] = amount
    context.user_data["pending_ref"] = ref

    keyboard = Keyboards.payment_confirmation(deposit_id)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def show_payment_details_message(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int):
    """Show UPI payment details (from message)."""
    user_id = update.effective_user.id
    db = get_db(context)

    deposit_id = await db.create_deposit(user_id, amount)
    ref = generate_unique_ref()

    upi_link = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={ref}"

    text = (
        f"💳 <b>Payment Details</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: <b>{format_price(amount)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        f"👤 <b>Name:</b> {UPI_NAME}\n"
        f"🔖 <b>Reference:</b> <code>{ref}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Instructions:</b>\n"
        f"1️⃣ Copy the UPI ID above\n"
        f"2️⃣ Open any UPI app (GPay, PhonePe, Paytm)\n"
        f"3️⃣ Send <b>{format_price(amount)}</b> to the UPI ID\n"
        f"4️⃣ After payment, click \"I've Paid\" below\n"
        f"5️⃣ Enter your UTR/Transaction ID\n\n"
        f"⚠️ <i>Amount must match exactly!</i>\n"
        f"⏳ <i>Payment will be verified and credited automatically.</i>"
    )

    context.user_data["pending_deposit_id"] = deposit_id
    context.user_data["pending_amount"] = amount
    context.user_data["pending_ref"] = ref

    keyboard = Keyboards.payment_confirmation(deposit_id)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")



# ═══════════════════════════════════════════
# PAYMENT CONFIRMATION
# ═══════════════════════════════════════════

async def paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'I've Paid' button click."""
    query = update.callback_query
    await query.answer()

    deposit_id = int(query.data.split("_")[1])

    await query.edit_message_text(
        "✅ <b>Payment Submitted!</b>\n\n"
        "Please enter your <b>UTR Number / Transaction ID</b>\n"
        "from your UPI app:\n\n"
        "<i>This helps us verify your payment faster.</i>\n"
        "<i>You can find it in your payment history.</i>",
        parse_mode="HTML"
    )

    # Set state to await UTR input
    context.user_data["awaiting_utr"] = True
    context.user_data["utr_deposit_id"] = deposit_id


async def handle_utr_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle UTR/Transaction ID input from user."""
    if not context.user_data.get("awaiting_utr"):
        return False

    utr = update.message.text.strip()
    deposit_id = context.user_data.get("utr_deposit_id")

    if not utr or len(utr) < 4:
        await update.message.reply_text(
            "❌ Invalid UTR. Please enter a valid transaction reference number."
        )
        return True

    db = get_db(context)

    # Update deposit with UTR reference
    deposit = await db.get_deposit(deposit_id)
    if deposit:
        await db._db.execute(
            "UPDATE deposits SET upi_reference = ? WHERE id = ?",
            (utr, deposit_id)
        )
        await db._db.commit()

    # Clear state
    context.user_data["awaiting_utr"] = False
    context.user_data.pop("utr_deposit_id", None)

    amount = context.user_data.get("pending_amount", 0)

    await update.message.reply_text(
        f"✅ <b>Payment Recorded!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: <b>{format_price(amount)}</b>\n"
        f"🔖 UTR: <code>{utr}</code>\n"
        f"🆔 Deposit ID: #{deposit_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏳ Your payment is being verified.\n"
        f"Your balance will be updated automatically once confirmed.\n\n"
        f"📩 If it takes too long, contact: {SUPPORT_CONTACT}",
        parse_mode="HTML"
    )

    # Notify admins about new deposit
    await notify_admins_new_deposit(context, update.effective_user, deposit_id, amount, utr)

    return True


async def notify_admins_new_deposit(context: ContextTypes.DEFAULT_TYPE,
                                     user, deposit_id: int, amount: float, utr: str):
    """Notify all admins about a new deposit pending verification."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit_id}")]
    ])

    text = (
        f"💳 <b>New Deposit Pending!</b>\n\n"
        f"👤 User: {user.first_name} (@{user.username or 'N/A'})\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"💰 Amount: <b>{format_price(amount)}</b>\n"
        f"🔖 UTR: <code>{utr}</code>\n"
        f"📋 Deposit ID: #{deposit_id}\n\n"
        f"Approve or reject this deposit:"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id, text, reply_markup=keyboard, parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify admin {admin_id}: {e}")



# ═══════════════════════════════════════════
# CANCEL DEPOSIT
# ═══════════════════════════════════════════

async def cancel_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit cancellation."""
    query = update.callback_query
    await query.answer("Deposit cancelled.")

    deposit_id = int(query.data.split("_")[-1])
    db = get_db(context)

    # Mark deposit as rejected/cancelled
    await db.reject_deposit(deposit_id)

    # Clear user data
    context.user_data.pop("pending_deposit_id", None)
    context.user_data.pop("pending_amount", None)
    context.user_data.pop("pending_ref", None)
    context.user_data.pop("awaiting_utr", None)

    await query.edit_message_text(
        "❌ Deposit cancelled.\n\n"
        "Use /deposit to try again."
    )


async def deposit_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button from deposit."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Use the menu buttons below to navigate! 👇")


# ═══════════════════════════════════════════
# CUSTOM MESSAGE HANDLER (integrates with user_handlers)
# ═══════════════════════════════════════════

async def payment_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages that might be payment-related."""
    # Check if user is in UTR input mode
    if context.user_data.get("awaiting_utr"):
        return await handle_utr_input(update, context)

    # Check if user is entering custom amount
    if context.user_data.get("awaiting_custom_amount"):
        return await handle_custom_amount(update, context)

    return False



# ═══════════════════════════════════════════
# REGISTER PAYMENT HANDLERS
# ═══════════════════════════════════════════

def register_payment_handlers(application: Application):
    """Register all payment-related handlers."""
    # Deposit command
    application.add_handler(CommandHandler("deposit", deposit_command))

    # Deposit amount callbacks
    application.add_handler(CallbackQueryHandler(
        deposit_amount_callback, pattern=r"^deposit_(50|100|200|500|1000|2000)$"
    ))
    application.add_handler(CallbackQueryHandler(
        deposit_custom_callback, pattern=r"^deposit_custom$"
    ))
    application.add_handler(CallbackQueryHandler(
        deposit_back_callback, pattern=r"^deposit_back$"
    ))

    # Payment confirmation callbacks
    application.add_handler(CallbackQueryHandler(paid_callback, pattern=r"^paid_\d+$"))
    application.add_handler(CallbackQueryHandler(
        cancel_deposit_callback, pattern=r"^cancel_deposit_\d+$"
    ))

    # Text handler for payment inputs (UTR, custom amount)
    # This needs to be added with a lower group so it processes before the main text handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, payment_text_handler),
        group=1
    )

    logger.info("Payment handlers registered.")
