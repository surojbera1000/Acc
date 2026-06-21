"""Admin panel handlers for the Telegram Account Bot."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

from config import ADMIN_IDS, CURRENCY_SYMBOL
from database import Database
from utils.keyboards import Keyboards
from utils.helpers import format_price, is_admin

logger = logging.getLogger(__name__)

# Conversation states for admin flows
(ADD_COUNTRY_NAME, ADD_COUNTRY_CODE, ADD_COUNTRY_FLAG,
 ADD_ACC_COUNTRY, ADD_ACC_PHONE, ADD_ACC_OTP, ADD_ACC_2FA, ADD_ACC_SESSION, ADD_ACC_PRICE,
 EDIT_ACC_SELECT, EDIT_ACC_FIELD, EDIT_ACC_VALUE,
 DELETE_ACC_SELECT) = range(13)


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
        return await func(update, context)
    return wrapper



# ═══════════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════════

@admin_required
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - show admin panel."""
    text = (
        "🔧 <b>Admin Panel</b>\n\n"
        "Select an option below:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=Keyboards.admin_menu(), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=Keyboards.admin_menu(), parse_mode="HTML"
        )


@admin_required
async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close admin panel."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✅ Admin panel closed.")



# ═══════════════════════════════════════════
# STOCK STATUS
# ═══════════════════════════════════════════

@admin_required
async def admin_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show stock status."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    stock = await db.get_stock_summary()

    if not stock:
        text = (
            "📊 <b>Stock Status</b>\n\n"
            "No countries or accounts added yet.\n"
            "Use 'Manage Countries' to add countries first."
        )
    else:
        text = "📊 <b>Stock Status</b>\n\n"
        total_available = 0
        total_sold = 0
        for item in stock:
            flag = item.get("flag", "")
            text += (
                f"{flag} <b>{item['name']}</b> ({item['code']})\n"
                f"   ├ Available: {item['available']}\n"
                f"   ├ Sold: {item['sold']}\n"
                f"   └ Total: {item['total']}\n\n"
            )
            total_available += item["available"]
            total_sold += item["sold"]

        text += (
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Total Available: <b>{total_available}</b>\n"
            f"🛒 Total Sold: <b>{total_sold}</b>"
        )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")



# ═══════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════

@admin_required
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    stats = await db.get_stats()

    text = (
        "📈 <b>Bot Statistics</b>\n\n"
        f"👥 Total Users: <b>{stats['total_users']}</b>\n"
        f"📦 Available Accounts: <b>{stats['available_accounts']}</b>\n"
        f"🛒 Sold Accounts: <b>{stats['sold_accounts']}</b>\n"
        f"✅ Completed Orders: <b>{stats['completed_orders']}</b>\n"
        f"💰 Total Revenue: <b>{format_price(stats['total_revenue'])}</b>\n"
        f"💳 Total Deposits: <b>{format_price(stats['total_deposits'])}</b>\n"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")



# ═══════════════════════════════════════════
# VIEW ORDERS (Admin)
# ═══════════════════════════════════════════

@admin_required
async def admin_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent orders."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    orders = await db.get_all_orders(limit=15)

    if not orders:
        text = "👥 <b>Recent Orders</b>\n\nNo orders yet."
    else:
        text = "👥 <b>Recent Orders</b>\n\n"
        for order in orders:
            username = order.get("username", "") or order.get("first_name", "Unknown")
            status_emoji = {"completed": "✅", "pending": "⏳", "failed": "❌", "refunded": "💰"}
            emoji = status_emoji.get(order["status"], "❓")
            text += (
                f"{emoji} #{order['id']} | @{username} | "
                f"{order['country_name']} | {format_price(order['amount'])} | "
                f"{order['status']}\n"
            )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")



# ═══════════════════════════════════════════
# MANAGE COUNTRIES
# ═══════════════════════════════════════════

@admin_required
async def admin_countries_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show country management."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    countries = await db.get_countries(active_only=False)

    text = "🌍 <b>Manage Countries</b>\n\n"
    if countries:
        for c in countries:
            status = "✅" if c["is_active"] else "❌"
            text += f"{status} {c['flag']} {c['name']} ({c['code']})\n"
    else:
        text += "No countries added yet.\n"

    text += "\n<i>To add a country, send:</i>\n<code>/addcountry Name|CODE|Flag</code>\n"
    text += "<i>Example:</i> <code>/addcountry India|IN|🇮🇳</code>"

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


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

# ───── Interactive (button-driven) Add Account conversation ─────
# Flow: click "➕ Add Account" → pick country → send phone → send OTP
# (or Skip) → send 2FA (or Skip) → send session string (or Skip) →
# send price → saved automatically.
#
# The session string lets the buyer log in to a ready, already-authorised
# session instead of re-logging in with the OTP (which is what causes the
# "logged out right after login" problem when reselling accounts).

@admin_required
async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: show country picker to start the add-account flow."""
    query = update.callback_query
    await query.answer()
    db = get_db(context)

    countries = await db.get_countries()
    if not countries:
        await query.edit_message_text(
            "❌ <b>No countries available!</b>\n\n"
            "Add a country first using:\n"
            "<code>/addcountry Name|CODE|Flag</code>\n"
            "<i>Example:</i> <code>/addcountry India|IN|🇮🇳</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
            ]),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    # Reset any stale draft
    context.user_data["new_account"] = {}

    rows = []
    row = []
    for c in countries:
        row.append(InlineKeyboardButton(
            f"{c['flag']} {c['name']}",
            callback_data=f"addacc_country_{c['id']}"
        ))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="addacc_cancel")])

    await query.edit_message_text(
        "➕ <b>Add New Account</b>\n\n"
        "<b>Step 1 of 6</b> — Select the country for this account:",
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="HTML"
    )
    return ADD_ACC_COUNTRY


@admin_required
async def add_account_choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Country picked — ask for the phone number."""
    query = update.callback_query
    await query.answer()

    country_id = int(query.data.split("_")[-1])
    db = get_db(context)
    country = await db.get_country(country_id)
    if not country:
        await query.edit_message_text("❌ Country not found. Please try again.")
        return ConversationHandler.END

    context.user_data["new_account"] = {
        "country_id": country_id,
        "country_name": country["name"],
        "country_flag": country["flag"],
    }

    await query.edit_message_text(
        f"➕ <b>Add New Account</b>\n"
        f"🌍 Country: {country['flag']} <b>{country['name']}</b>\n\n"
        f"<b>Step 2 of 6</b> — Send the <b>phone number</b>.\n"
        f"<i>Example:</i> <code>+919876543210</code>\n\n"
        f"Send /cancel anytime to abort.",
        parse_mode="HTML"
    )
    return ADD_ACC_PHONE


@admin_required
async def add_account_receive_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Phone received — ask for the OTP."""
    phone = update.message.text.strip()
    if not phone:
        await update.message.reply_text("❌ Phone number can't be empty. Send a valid number.")
        return ADD_ACC_PHONE

    context.user_data.setdefault("new_account", {})["phone"] = phone

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip (no OTP)", callback_data="addacc_skip_otp")],
        [InlineKeyboardButton("❌ Cancel", callback_data="addacc_cancel")],
    ])
    await update.message.reply_text(
        f"📱 Phone: <code>{phone}</code>\n\n"
        f"<b>Step 3 of 6</b> — Send the <b>OTP / login code</b> for this account,\n"
        f"or tap <b>Skip</b> if there isn't one.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return ADD_ACC_OTP


@admin_required
async def add_account_receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OTP received via text — ask for 2FA."""
    otp = update.message.text.strip()
    context.user_data.setdefault("new_account", {})["otp"] = otp if otp and otp != "-" else None
    return await _ask_for_2fa(update.message.reply_text)


@admin_required
async def add_account_skip_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip OTP — ask for 2FA."""
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("new_account", {})["otp"] = None
    return await _ask_for_2fa(query.edit_message_text)


async def _ask_for_2fa(send_func):
    """Helper to prompt for the 2FA step (works for both message & callback)."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip (no 2FA)", callback_data="addacc_skip_2fa")],
        [InlineKeyboardButton("❌ Cancel", callback_data="addacc_cancel")],
    ])
    await send_func(
        "<b>Step 4 of 6</b> — Send the <b>2FA password / backup code</b> for this account,\n"
        "or tap <b>Skip</b> if there isn't one.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return ADD_ACC_2FA


@admin_required
async def add_account_receive_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """2FA received via text — ask for the session string."""
    two_fa = update.message.text.strip()
    context.user_data.setdefault("new_account", {})["two_fa"] = two_fa if two_fa and two_fa != "-" else None
    return await _ask_for_session(update.message.reply_text)


@admin_required
async def add_account_skip_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip 2FA — ask for the session string."""
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("new_account", {})["two_fa"] = None
    return await _ask_for_session(query.edit_message_text)


async def _ask_for_session(send_func):
    """Helper to prompt for the session-save step."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Skip (no session)", callback_data="addacc_skip_session")],
        [InlineKeyboardButton("❌ Cancel", callback_data="addacc_cancel")],
    ])
    await send_func(
        "<b>Step 5 of 6</b> — 💾 Send the <b>session string</b> to save with this account.\n\n"
        "This is the logged-in session (e.g. a Telethon/Pyrogram <i>string session</i>) "
        "that lets the buyer open the account <b>already logged in</b>, instead of "
        "re-logging in with the OTP — which is what causes the account to get "
        "logged out right after login.\n\n"
        "Paste the full session string, or tap <b>Skip</b> if you don't have one.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return ADD_ACC_SESSION


@admin_required
async def add_account_receive_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Session string received via text — ask for price."""
    session = update.message.text.strip()
    context.user_data.setdefault("new_account", {})["session"] = session if session and session != "-" else None
    return await _ask_for_price(update.message.reply_text)


@admin_required
async def add_account_skip_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip session — ask for price."""
    query = update.callback_query
    await query.answer()
    context.user_data.setdefault("new_account", {})["session"] = None
    return await _ask_for_price(query.edit_message_text)


async def _ask_for_price(send_func):
    """Helper to prompt for the price step."""
    await send_func(
        "💰 <b>Step 6 of 6</b> — Send the <b>price</b> for this account in ₹.\n"
        "<i>Example:</i> <code>150</code>",
        parse_mode="HTML"
    )
    return ADD_ACC_PRICE


@admin_required
async def add_account_receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Price received — save the account and finish."""
    raw = update.message.text.strip().replace("₹", "").replace(",", "").strip()
    try:
        price = float(raw)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid price. Send a number like <code>150</code>.",
            parse_mode="HTML"
        )
        return ADD_ACC_PRICE

    if price <= 0:
        await update.message.reply_text("❌ Price must be greater than 0. Try again.")
        return ADD_ACC_PRICE

    draft = context.user_data.get("new_account") or {}
    country_id = draft.get("country_id")
    phone = draft.get("phone")

    if not country_id or not phone:
        await update.message.reply_text(
            "⚠️ Something went wrong (missing data). Please start again from the Admin panel."
        )
        context.user_data.pop("new_account", None)
        return ConversationHandler.END

    db = get_db(context)
    account_id = await db.add_account(
        country_id=country_id,
        phone_number=phone,
        price=price,
        otp=draft.get("otp"),
        two_fa=draft.get("two_fa"),
        session=draft.get("session"),
        added_by=update.effective_user.id
    )

    await update.message.reply_text(
        f"✅ <b>Account Added!</b>\n\n"
        f"🆔 Account ID: <b>#{account_id}</b>\n"
        f"🌍 Country: {draft.get('country_flag', '')} {draft.get('country_name', '')}\n"
        f"📱 Phone: <code>{phone}</code>\n"
        f"💰 Price: {format_price(price)}\n"
        f"🔑 OTP: {'<code>' + draft['otp'] + '</code>' if draft.get('otp') else 'Not set'}\n"
        f"🔐 2FA: {'<code>' + draft['two_fa'] + '</code>' if draft.get('two_fa') else 'Not set'}\n"
        f"💾 Session: {'✅ Saved' if draft.get('session') else 'Not set'}\n\n"
        f"📦 Stock updated automatically!\n"
        f"<i>Tap ➕ Add Account in /admin to add another.</i>",
        parse_mode="HTML"
    )
    context.user_data.pop("new_account", None)
    logger.info(f"Admin {update.effective_user.id} added account #{account_id} (interactive)")
    return ConversationHandler.END


@admin_required
async def add_account_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the interactive add-account flow."""
    context.user_data.pop("new_account", None)
    msg = "❌ Add account cancelled.\n\nUse /admin to open the panel again."
    if update.callback_query:
        await update.callback_query.answer("Cancelled")
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)
    return ConversationHandler.END


@admin_required
async def add_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addaccount command (power-user one-liner alternative)."""
    if not context.args:
        await update.message.reply_text(
            "Usage: <code>/addaccount country_id|phone|price|otp|2fa|session</code>\n"
            "Example: <code>/addaccount 1|+919876543210|150|1234|backup_code|1ApWap...</code>\n\n"
            "<i>otp, 2fa and session are optional — use - to skip a field.</i>",
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
        session = parts[5].strip() if len(parts) > 5 and parts[5].strip() != "-" else None
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid values. Check format and try again.")
        return

    db = get_db(context)

    # Verify country exists
    country = await db.get_country(country_id)
    if not country:
        await update.message.reply_text(f"❌ Country ID {country_id} not found.")
        return

    account_id = await db.add_account(
        country_id=country_id,
        phone_number=phone,
        price=price,
        otp=otp,
        two_fa=two_fa,
        session=session,
        added_by=update.effective_user.id
    )

    await update.message.reply_text(
        f"✅ <b>Account Added!</b>\n\n"
        f"🆔 Account ID: <b>#{account_id}</b>\n"
        f"🌍 Country: {country['flag']} {country['name']}\n"
        f"📱 Phone: <code>{phone}</code>\n"
        f"💰 Price: {format_price(price)}\n"
        f"🔑 OTP: {'Set' if otp else 'Not set'}\n"
        f"🔐 2FA: {'Set' if two_fa else 'Not set'}\n"
        f"💾 Session: {'Saved' if session else 'Not set'}\n\n"
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
            "Send multiple accounts, one per line:\n"
            "<code>/bulkadd country_id|price\n"
            "phone1|otp1|2fa1\n"
            "phone2|otp2|2fa2\n"
            "phone3|otp3|2fa3</code>\n\n"
            "First line: country_id and price\n"
            "Following lines: phone|otp|2fa for each account\n"
            "Use - for empty otp/2fa fields.",
            parse_mode="HTML"
        )
        return

    lines = update.message.text.replace("/bulkadd ", "").strip().split("\n")
    if len(lines) < 2:
        await update.message.reply_text("❌ Need at least header line + 1 account.")
        return

    # Parse header
    header = lines[0].split("|")
    try:
        country_id = int(header[0].strip())
        price = float(header[1].strip())
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid header. Format: country_id|price")
        return

    db = get_db(context)
    country = await db.get_country(country_id)
    if not country:
        await update.message.reply_text(f"❌ Country ID {country_id} not found.")
        return

    added = 0
    errors = 0
    for line in lines[1:]:
        parts = line.strip().split("|")
        if not parts or not parts[0].strip():
            continue
        phone = parts[0].strip()
        otp = parts[1].strip() if len(parts) > 1 and parts[1].strip() != "-" else None
        two_fa = parts[2].strip() if len(parts) > 2 and parts[2].strip() != "-" else None

        try:
            await db.add_account(country_id, phone, price, otp, two_fa, update.effective_user.id)
            added += 1
        except Exception as e:
            errors += 1
            logger.error(f"Bulk add error: {e}")

    await update.message.reply_text(
        f"📦 <b>Bulk Add Complete</b>\n\n"
        f"✅ Added: {added} accounts\n"
        f"❌ Errors: {errors}\n"
        f"🌍 Country: {country['flag']} {country['name']}\n"
        f"💰 Price each: {format_price(price)}",
        parse_mode="HTML"
    )



# ═══════════════════════════════════════════
# EDIT ACCOUNT
# ═══════════════════════════════════════════

@admin_required
async def admin_edit_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show edit account instructions."""
    query = update.callback_query
    await query.answer()

    text = (
        "📝 <b>Edit Account</b>\n\n"
        "To edit an account, use:\n"
        "<code>/editaccount ID|field|new_value</code>\n\n"
        "<b>Editable fields:</b>\n"
        "• phone_number\n"
        "• otp\n"
        "• two_fa\n"
        "• session\n"
        "• price\n\n"
        "<b>Examples:</b>\n"
        "<code>/editaccount 5|price|200</code>\n"
        "<code>/editaccount 5|otp|5678</code>\n"
        "<code>/editaccount 5|session|1ApWap...</code>\n"
        "<code>/editaccount 5|phone_number|+919999999999</code>"
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


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

    valid_fields = ["phone_number", "otp", "two_fa", "session", "price"]
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
async def admin_remove_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show remove account instructions."""
    query = update.callback_query
    await query.answer()

    text = (
        "🗑 <b>Remove Account</b>\n\n"
        "To remove an account, use:\n"
        "<code>/removeaccount ID</code>\n\n"
        "⚠️ This action cannot be undone!\n"
        "Only available (unsold) accounts can be removed."
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


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

    await db.delete_account(account_id)
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
                f"👤 @{username} (ID: {dep['user_id']})\n"
                f"💰 Amount: {format_price(dep['amount'])}\n"
                f"📝 UPI Ref: <code>{dep.get('upi_reference', 'N/A')}</code>\n"
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
                callback_data=f"approve_deposit_{dep['id']}"
            ),
            InlineKeyboardButton(
                f"❌ #{dep['id']}",
                callback_data=f"reject_deposit_{dep['id']}"
            )
        ])
    keyboard_rows.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")])
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
            f"Support: {ADMIN_IDS}",
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


@admin_required
async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to admin panel."""
    await admin_command(update, context)



# ═══════════════════════════════════════════
# REGISTER ADMIN HANDLERS
# ═══════════════════════════════════════════

def register_admin_handlers(application: Application):
    """Register all admin handlers."""
    # Admin panel command
    application.add_handler(CommandHandler("admin", admin_command))

    # Interactive Add Account conversation (button-driven number/OTP/2FA flow).
    # Registered first so its text states win over the generic text handler.
    add_account_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_account_start, pattern=r"^admin_add_account$")
        ],
        states={
            ADD_ACC_COUNTRY: [
                CallbackQueryHandler(add_account_choose_country, pattern=r"^addacc_country_\d+$"),
            ],
            ADD_ACC_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive_phone),
            ],
            ADD_ACC_OTP: [
                CallbackQueryHandler(add_account_skip_otp, pattern=r"^addacc_skip_otp$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive_otp),
            ],
            ADD_ACC_2FA: [
                CallbackQueryHandler(add_account_skip_2fa, pattern=r"^addacc_skip_2fa$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive_2fa),
            ],
            ADD_ACC_SESSION: [
                CallbackQueryHandler(add_account_skip_session, pattern=r"^addacc_skip_session$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive_session),
            ],
            ADD_ACC_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive_price),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(add_account_cancel, pattern=r"^addacc_cancel$"),
            CommandHandler("cancel", add_account_cancel),
        ],
        allow_reentry=True,
        per_message=False,
    )
    application.add_handler(add_account_conv)

    # Admin action commands
    application.add_handler(CommandHandler("addcountry", add_country_command))
    application.add_handler(CommandHandler("addaccount", add_account_command))
    application.add_handler(CommandHandler("bulkadd", bulk_add_command))
    application.add_handler(CommandHandler("editaccount", edit_account_command))
    application.add_handler(CommandHandler("removeaccount", remove_account_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))

    # Admin panel callbacks
    application.add_handler(CallbackQueryHandler(admin_edit_account_callback, pattern=r"^admin_edit_account$"))
    application.add_handler(CallbackQueryHandler(admin_remove_account_callback, pattern=r"^admin_remove_account$"))
    application.add_handler(CallbackQueryHandler(admin_stock_callback, pattern=r"^admin_stock$"))
    application.add_handler(CallbackQueryHandler(admin_orders_callback, pattern=r"^admin_orders$"))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern=r"^admin_stats$"))
    application.add_handler(CallbackQueryHandler(admin_countries_callback, pattern=r"^admin_countries$"))
    application.add_handler(CallbackQueryHandler(admin_deposits_callback, pattern=r"^admin_deposits$"))
    application.add_handler(CallbackQueryHandler(admin_close_callback, pattern=r"^admin_close$"))
    application.add_handler(CallbackQueryHandler(admin_back_callback, pattern=r"^admin_back$"))

    # Deposit approval/rejection callbacks
    application.add_handler(CallbackQueryHandler(approve_deposit_callback, pattern=r"^approve_deposit_\d+$"))
    application.add_handler(CallbackQueryHandler(reject_deposit_callback, pattern=r"^reject_deposit_\d+$"))

    logger.info("Admin handlers registered.")
