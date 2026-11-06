"""Admin panel handlers for the Telegram Account Bot."""
import html
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

from config import ADMIN_IDS, CURRENCY_SYMBOL, SUPPORT_CONTACT
from database import Database
from utils.keyboards import Keyboards, PRIMARY, SUCCESS, DANGER
from utils.helpers import format_price, is_admin

logger = logging.getLogger(__name__)

# Conversation states for admin flows
(ADD_COUNTRY_NAME, ADD_COUNTRY_CODE, ADD_COUNTRY_FLAG,
 ADD_ACC_COUNTRY, ADD_ACC_PHONE, ADD_ACC_OTP, ADD_ACC_2FA, ADD_ACC_PRICE,
 EDIT_ACC_SELECT, EDIT_ACC_FIELD, EDIT_ACC_VALUE,
 DELETE_ACC_SELECT) = range(12)


def get_db(context: ContextTypes.DEFAULT_TYPE) -> Database:
    """Get the database instance from bot data."""
    return context.bot_data["db"]


def admin_required(func):
    """Decorator to restrict access to admins only."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("⛔ Access denied!", show_alert=True)
            else:
                await update.message.reply_text("⛔ You don't have admin access.")
            return
        # accounts.added_by has a FOREIGN KEY to users, so the admin must exist there
        user = update.effective_user
        await get_db(context).get_or_create_user(
            user_id=user.id, username=user.username,
            first_name=user.first_name, last_name=user.last_name
        )
        return await func(update, context)
    return wrapper


# ═══════════════════════════════════════════
# MANAGE COUNTRIES
# ═══════════════════════════════════════════


@admin_required
async def add_country_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcountry command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/addcountry Name|CODE|Flag</code>\n"
            "Example: <code>/addcountry India|IN|🇮🇳</code>",
            parse_mode="HTML"
        )
        return

    parts = " ".join(context.args).split("|")
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Invalid format. Use: <code>/addcountry Name|CODE|Flag</code>",
            parse_mode="HTML"
        )
        return

    name = parts[0].strip()
    code = parts[1].strip().upper()
    flag = parts[2].strip() if len(parts) > 2 else ""

    db = get_db(context)
    country_id = await db.add_country(name, code, flag)

    if country_id:
        await update.message.reply_text(
            f"✅ Country added: {flag} <b>{name}</b> ({code})\n"
            f"ID: {country_id}",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"⚠️ Country '{name}' might already exist.",
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════
# ADD ACCOUNT
# ═══════════════════════════════════════════


@admin_required
async def add_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addaccount command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/addaccount country_id|phone|price|otp|2fa</code>\n"
            "Example: <code>/addaccount 1|+919876543210|150|1234|backup_code</code>",
            parse_mode="HTML"
        )
        return

    parts = " ".join(context.args).split("|")
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Invalid format. Minimum: country_id|phone|price",
            parse_mode="HTML"
        )
        return

    try:
        country_id = int(parts[0].strip())
        phone = parts[1].strip()
        price = float(parts[2].strip())
        otp = parts[3].strip() if len(parts) > 3 and parts[3].strip() != "-" else None
        two_fa = parts[4].strip() if len(parts) > 4 and parts[4].strip() != "-" else None
        category = parts[5].strip() if len(parts) > 5 and parts[5].strip() != "-" else "Standard"
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid values. Check format and try again.")
        return

    db = get_db(context)

    # Verify country exists
    country = await db.get_country(country_id)
    if not country:
        await update.message.reply_text(f"❌ Country ID {country_id} not found.")
        return

    # Prevent duplicate phone numbers within a country
    if await db.account_exists(country_id, phone):
        await update.message.reply_text(
            f"⚠️ Account with phone <code>{phone}</code> already exists for "
            f"{country['flag']} {country['name']}. Skipped.",
            parse_mode="HTML"
        )
        return

    account_id = await db.add_account(
        country_id=country_id,
        phone_number=phone,
        price=price,
        otp=otp,
        two_fa=two_fa,
        category=category,
        added_by=update.effective_user.id
    )

    await update.message.reply_text(
        f"✅ <b>Account Added!</b>\n\n"
        f"🆔 Account ID: <b>#{account_id}</b>\n"
        f"🌍 Country: {country['flag']} {country['name']}\n"
        f"🏷 Type: <b>{category}</b>\n"
        f"📱 Phone: <code>{phone}</code>\n"
        f"💰 Price: {format_price(price)}\n"
        f"🔑 OTP: {'Set' if otp else 'Not set'}\n"
        f"🔐 2FA: {'Set' if two_fa else 'Not set'}\n\n"
        f"📦 Stock updated automatically!",
        parse_mode="HTML"
    )
    logger.info(f"Admin {update.effective_user.id} added account #{account_id}")


# ═══════════════════════════════════════════
# BULK ADD ACCOUNTS
# ═══════════════════════════════════════════

@admin_required
async def bulk_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /bulkadd command - add multiple accounts at once."""
    if not context.args:
        await update.message.reply_text(
            "📦 <b>Bulk Add Accounts</b>\n\n"
            "Header line sets the country and default type.\n"
            "Each following line is one account with its own price:\n\n"
            "<code>/bulkadd country_id|category\n"
            "phone1|price1|otp1|2fa1\n"
            "phone2|price2|otp2|2fa2</code>\n\n"
            "• <b>category</b> is optional (defaults to Standard)\n"
            "• <b>price</b> is per-account; if omitted, uses the previous line's price\n"
            "• Use <code>-</code> for empty otp/2fa fields\n"
            "• Duplicate phone numbers are skipped automatically\n\n"
            "<b>Example:</b>\n"
            "<code>/bulkadd 1|Fresh\n"
            "+919876543210|150|1234|-\n"
            "+919876543211|150|5678|backup2\n"
            "+919876543212|200|-|-</code>",
            parse_mode="HTML"
        )
        return

    body = update.message.text.split(maxsplit=1)
    lines = body[1].strip().split("\n") if len(body) > 1 else []
    if len(lines) < 2:
        await update.message.reply_text("❌ Need at least header line + 1 account.")
        return

    # Parse header: country_id|category(optional)
    header = lines[0].split("|")
    try:
        country_id = int(header[0].strip())
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid header. Format: country_id|category")
        return
    category = header[1].strip() if len(header) > 1 and header[1].strip() else "Standard"

    db = get_db(context)
    country = await db.get_country(country_id)
    if not country:
        await update.message.reply_text(f"❌ Country ID {country_id} not found.")
        return

    added = 0
    skipped = 0
    errors = 0
    last_price = None
    for line in lines[1:]:
        parts = line.strip().split("|")
        if not parts or not parts[0].strip():
            continue
        phone = parts[0].strip()

        # Per-line price (falls back to previous line's price)
        if len(parts) > 1 and parts[1].strip() and parts[1].strip() != "-":
            try:
                price = float(parts[1].strip())
            except ValueError:
                errors += 1
                continue
        elif last_price is not None:
            price = last_price
        else:
            errors += 1
            continue
        last_price = price

        otp = parts[2].strip() if len(parts) > 2 and parts[2].strip() != "-" else None
        two_fa = parts[3].strip() if len(parts) > 3 and parts[3].strip() != "-" else None

        if await db.account_exists(country_id, phone):
            skipped += 1
            continue

        try:
            await db.add_account(country_id, phone, price, otp, two_fa,
                                 update.effective_user.id, category=category)
            added += 1
        except Exception as e:
            errors += 1
            logger.error(f"Bulk add error: {e}")

    await update.message.reply_text(
        f"📦 <b>Bulk Add Complete</b>\n\n"
        f"✅ Added: {added}\n"
        f"⏭ Skipped (duplicate): {skipped}\n"
        f"❌ Errors: {errors}\n"
        f"🌍 Country: {country['flag']} {country['name']}\n"
        f"🏷 Type: <b>{category}</b>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# EDIT ACCOUNT
# ═══════════════════════════════════════════


@admin_required
async def edit_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /editaccount command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/editaccount ID|field|new_value</code>",
            parse_mode="HTML"
        )
        return

    parts = " ".join(context.args).split("|")
    if len(parts) < 3:
        await update.message.reply_text("❌ Invalid format. Use: ID|field|new_value")
        return

    try:
        account_id = int(parts[0].strip())
        field = parts[1].strip()
        value = parts[2].strip()
    except ValueError:
        await update.message.reply_text("❌ Invalid account ID.")
        return

    valid_fields = ["phone_number", "otp", "two_fa", "price"]
    if field not in valid_fields:
        await update.message.reply_text(
            f"❌ Invalid field. Valid fields: {', '.join(valid_fields)}"
        )
        return

    db = get_db(context)
    account = await db.get_account(account_id)
    if not account:
        await update.message.reply_text(f"❌ Account #{account_id} not found.")
        return

    # Convert price to float
    if field == "price":
        try:
            value = float(value)
        except ValueError:
            await update.message.reply_text("❌ Invalid price value.")
            return

    await db.update_account(account_id, **{field: value})
    await update.message.reply_text(
        f"✅ Account <b>#{account_id}</b> updated!\n"
        f"Field: <b>{field}</b>\n"
        f"New value: <code>{value}</code>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# REMOVE ACCOUNT
# ═══════════════════════════════════════════


@admin_required
async def remove_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeaccount command."""
    if not context.args:
        await update.message.reply_text("Usage: <code>/removeaccount ID</code>", parse_mode="HTML")
        return

    try:
        account_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid account ID.")
        return

    db = get_db(context)
    account = await db.get_account(account_id)

    if not account:
        await update.message.reply_text(f"❌ Account #{account_id} not found.")
        return

    if account["status"] == "sold":
        await update.message.reply_text(
            f"⚠️ Account #{account_id} is already sold. Cannot remove."
        )
        return

    if not await db.delete_account(account_id):
        await update.message.reply_text(f"⚠ Account #{account_id} is not available.")
        return
    await update.message.reply_text(
        f"✅ Account <b>#{account_id}</b> has been removed.\n"
        f"📦 Stock updated.",
        parse_mode="HTML"
    )
    logger.info(f"Admin {update.effective_user.id} removed account #{account_id}")


# ═══════════════════════════════════════════
# PENDING DEPOSITS (Admin Verification)
# ═══════════════════════════════════════════

@admin_required
async def admin_deposits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending deposits for verification."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    deposits = await db.get_pending_deposits()

    if not deposits:
        text = "💳 <b>Pending Deposits</b>\n\n✅ No pending deposits!"
    else:
        text = f"💳 <b>Pending Deposits</b> ({len(deposits)})\n\n"
        for dep in deposits:
            username = dep.get("username", "") or dep.get("first_name", "Unknown")
            text += (
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Deposit #{dep['id']}\n"
                f"👤 {html.escape(str(username))} (ID: <code>{dep['user_id']}</code>)\n"
                f"💰 Amount: {format_price(dep['amount'])}\n"
                f"📝 UTR: <code>{html.escape(dep.get('upi_reference') or 'N/A')}</code>\n"
                f"📅 {dep['created_at'][:16]}\n"
            )

    text += "\n\nUse buttons below or:\n"
    text += "<code>/approve DEPOSIT_ID</code> to approve\n"
    text += "<code>/reject DEPOSIT_ID</code> to reject"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard_rows = []
    for dep in deposits[:5]:  # Show buttons for first 5
        keyboard_rows.append([
            InlineKeyboardButton(
                f"✅ #{dep['id']} ({format_price(dep['amount'])})",
                callback_data=f"approve_deposit_{dep['id']}", style=SUCCESS
            ),
            InlineKeyboardButton(
                f"❌ #{dep['id']}",
                callback_data=f"reject_deposit_{dep['id']}", style=DANGER
            )
        ])
    keyboard_rows.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back", style=PRIMARY)])
    keyboard = InlineKeyboardMarkup(keyboard_rows)

    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


@admin_required
async def approve_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending deposit."""
    query = update.callback_query
    await query.answer()

    deposit_id = int(query.data.split("_")[-1])
    db = get_db(context)

    deposit = await db.get_deposit(deposit_id)
    if not deposit:
        await query.edit_message_text("❌ Deposit not found.")
        return

    if deposit["status"] != "pending":
        await query.edit_message_text(f"⚠️ Deposit #{deposit_id} is already {deposit['status']}.")
        return

    # Verify deposit and credit user
    await db.verify_deposit(deposit_id)

    # Credit user balance
    new_balance = await db.update_balance(deposit["user_id"], deposit["amount"], "add")
    await db.add_to_total_deposits(deposit["user_id"], deposit["amount"])

    # Create transaction record
    tx_id = await db.create_transaction(
        deposit["user_id"], "deposit", deposit["amount"],
        description=f"UPI Deposit #{deposit_id} approved",
        reference=deposit.get("upi_reference", "")
    )
    await db.complete_transaction(tx_id, new_balance)

    await query.edit_message_text(
        f"✅ <b>Deposit #{deposit_id} Approved!</b>\n\n"
        f"💰 Amount: {format_price(deposit['amount'])}\n"
        f"👤 User ID: {deposit['user_id']}\n"
        f"👛 New Balance: {format_price(new_balance)}",
        parse_mode="HTML"
    )

    # Notify the user
    try:
        await context.bot.send_message(
            deposit["user_id"],
            f"✅ <b>Deposit Approved!</b>\n\n"
            f"💰 Amount: {format_price(deposit['amount'])}\n"
            f"👛 New Balance: {format_price(new_balance)}\n\n"
            f"You can now buy accounts!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Could not notify user {deposit['user_id']}: {e}")


@admin_required
async def reject_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending deposit."""
    query = update.callback_query
    await query.answer()

    deposit_id = int(query.data.split("_")[-1])
    db = get_db(context)

    deposit = await db.get_deposit(deposit_id)
    if not deposit:
        await query.edit_message_text("❌ Deposit not found.")
        return

    await db.reject_deposit(deposit_id)

    await query.edit_message_text(
        f"❌ <b>Deposit #{deposit_id} Rejected</b>\n\n"
        f"💰 Amount: {format_price(deposit['amount'])}\n"
        f"👤 User ID: {deposit['user_id']}",
        parse_mode="HTML"
    )

    # Notify user
    try:
        await context.bot.send_message(
            deposit["user_id"],
            f"❌ <b>Deposit Rejected</b>\n\n"
            f"Your deposit of {format_price(deposit['amount'])} was not approved.\n"
            f"Please contact support if you believe this is an error.\n"
            f"Support: {SUPPORT_CONTACT}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"Could not notify user {deposit['user_id']}: {e}")


# ═══════════════════════════════════════════
# ADMIN COMMAND HANDLERS (approve/reject via command)
# ═══════════════════════════════════════════

@admin_required
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command."""
    if not context.args:
        await update.message.reply_text("Usage: /approve DEPOSIT_ID")
        return

    try:
        deposit_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid deposit ID.")
        return

    db = get_db(context)
    deposit = await db.get_deposit(deposit_id)

    if not deposit:
        await update.message.reply_text(f"❌ Deposit #{deposit_id} not found.")
        return

    if deposit["status"] != "pending":
        await update.message.reply_text(f"⚠️ Deposit #{deposit_id} is already {deposit['status']}.")
        return

    await db.verify_deposit(deposit_id)
    new_balance = await db.update_balance(deposit["user_id"], deposit["amount"], "add")
    await db.add_to_total_deposits(deposit["user_id"], deposit["amount"])

    tx_id = await db.create_transaction(
        deposit["user_id"], "deposit", deposit["amount"],
        description=f"UPI Deposit #{deposit_id} approved",
        reference=deposit.get("upi_reference", "")
    )
    await db.complete_transaction(tx_id, new_balance)

    await update.message.reply_text(
        f"✅ Deposit #{deposit_id} approved! User balance: {format_price(new_balance)}",
        parse_mode="HTML"
    )

    try:
        await context.bot.send_message(
            deposit["user_id"],
            f"✅ <b>Deposit Approved!</b>\n\n"
            f"💰 {format_price(deposit['amount'])} added to your wallet.\n"
            f"👛 Balance: {format_price(new_balance)}",
            parse_mode="HTML"
        )
    except Exception:
        pass


@admin_required
async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reject command."""
    if not context.args:
        await update.message.reply_text("Usage: /reject DEPOSIT_ID")
        return

    try:
        deposit_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid deposit ID.")
        return

    db = get_db(context)
    deposit = await db.get_deposit(deposit_id)

    if not deposit:
        await update.message.reply_text(f"❌ Deposit #{deposit_id} not found.")
        return

    await db.reject_deposit(deposit_id)
    await update.message.reply_text(f"❌ Deposit #{deposit_id} rejected.")

    try:
        await context.bot.send_message(
            deposit["user_id"],
            f"❌ Your deposit of {format_price(deposit['amount'])} was rejected.\n"
            f"Contact support if this is an error.",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ═══════════════════════════════════════════
# REGISTER ADMIN HANDLERS
# ═══════════════════════════════════════════

def register_admin_handlers(application: Application):
    """Register all admin handlers."""

    # Admin action commands
    application.add_handler(CommandHandler("addcountry", add_country_command))
    application.add_handler(CommandHandler("addaccount", add_account_command))
    application.add_handler(CommandHandler("bulkadd", bulk_add_command))
    application.add_handler(CommandHandler("editaccount", edit_account_command))
    application.add_handler(CommandHandler("removeaccount", remove_account_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))

    application.add_handler(CallbackQueryHandler(admin_deposits_callback, pattern=r"^admin_deposits$"))

    # Deposit approval/rejection callbacks
    application.add_handler(CallbackQueryHandler(approve_deposit_callback, pattern=r"^approve_deposit_\d+$"))
    application.add_handler(CallbackQueryHandler(reject_deposit_callback, pattern=r"^reject_deposit_\d+$"))

    logger.info("Admin handlers registered.")
