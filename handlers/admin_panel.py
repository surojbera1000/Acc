"""Admin dashboard: stock manager, users, broadcast, sales report, countries, backup.

Everything is button-driven. When the admin has to type a value (new price,
balance amount, broadcast message ...) the expected input is stored in
``context.user_data[STATE_KEY]`` and picked up by ``admin_input_handler``,
which runs before the user/payment text handlers.
"""
import asyncio
import html
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, Forbidden, RetryAfter
from telegram.ext import (
    Application, ApplicationHandlerStop, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, TypeHandler, filters
)

from handlers.admin_handlers import admin_required, get_db
from utils.helpers import format_price, get_user_display_name, is_admin
from utils.keyboards import DANGER, PRIMARY, SUCCESS, Keyboards

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
PAGE_SIZE = 8
STATE_KEY = "admin_input"
LINE = "━━━━━━━━━━━━━━━━━━━━━"
MENU_BUTTON_TEXTS = {b.text for row in Keyboards.main_menu().keyboard for b in row}


# ═══════════════════════════════════════════
# SMALL HELPERS
# ═══════════════════════════════════════════

def btn(text, cb, style=PRIMARY):
    return InlineKeyboardButton(text, callback_data=cb, style=style)


def kb(*rows):
    return InlineKeyboardMarkup([list(r) for r in rows if r])


def esc(value):
    return "—" if value in (None, "") else html.escape(str(value))


def back_row(cb="admin_back", label="⬅ Back"):
    return (btn(label, cb),)


async def show(update: Update, text: str, markup=None):
    """Edit the panel message for button presses, or reply for typed input."""
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
    else:
        await update.effective_message.reply_text(text, reply_markup=markup, parse_mode="HTML")


def set_input(context, **state):
    context.user_data[STATE_KEY] = state


def clear_input(context):
    context.user_data.pop(STATE_KEY, None)


def cb_int(update: Update, index: int = -1) -> int:
    return int(update.callback_query.data.split("_")[index])


# ═══════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════

@admin_required
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin and every 'Back to dashboard' button."""
    clear_input(context)
    r = await get_db(context).get_sales_report()
    pending = r["pending_deposits"]

    text = (
        f"🛠 <b>Admin Dashboard</b>\n{LINE}\n"
        f"💰 Today's Sales: <b>{format_price(r['today']['revenue'])}</b> "
        f"({r['today']['orders']} orders)\n"
        f"💳 Deposits Today: <b>{format_price(r['deposits_today'])}</b>\n"
        f"👥 Users: <b>{r['total_users']}</b> (+{r['new_users_today']} today)\n"
        f"📦 Stock Available: <b>{r['available_stock']}</b>\n"
        f"⏳ Pending Deposits: <b>{pending}</b>\n{LINE}\n"
        f"🕒 <i>Updated {datetime.now(IST).strftime('%d %b, %I:%M %p')}</i>"
    )
    markup = kb(
        (btn("➕ Add Stock", "adm_add", SUCCESS), btn("📦 Manage Stock", "ms_home")),
        (btn(f"💳 Deposits ({pending})" if pending else "💳 Deposits", "admin_deposits",
             DANGER if pending else PRIMARY),
         btn("🧾 Orders", "admin_orders")),
        (btn("📈 Sales Report", "admin_stats"), btn("👥 Users", "us_home")),
        (btn("🌍 Countries", "ct_home"), btn("📢 Broadcast", "bc_start", SUCCESS)),
        (btn("💾 Backup", "admin_backup"), btn("🔄 Refresh", "admin_back")),
        (btn("✖ Close", "admin_close", DANGER),),
    )
    await show(update, text, markup)


@admin_required
async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    await show(update, "✅ Admin panel closed. Send /admin to open it again.")


@admin_required
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    context.user_data.pop("bc_msg", None)
    await update.message.reply_text(
        "✖ Cancelled.", reply_markup=kb(back_row(label="🛠 Dashboard"))
    )


# ═══════════════════════════════════════════
# ADD STOCK
# ═══════════════════════════════════════════

@admin_required
async def add_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = await get_db(context).get_countries(active_only=False)
    if not countries:
        await show(update,
                   "➕ <b>Add Stock</b>\n\n❌ No countries yet. Add a country first.",
                   kb((btn("🌍 Countries", "ct_home"),), back_row()))
        return

    ids = "\n".join(f"  {c['flag']} {esc(c['name'])} → ID <b>{c['id']}</b>" for c in countries)
    text = (
        f"➕ <b>Add Stock</b>\n{LINE}\n"
        "<b>Single account:</b>\n"
        "<code>/addaccount country_id|phone|price|otp|2fa|type</code>\n"
        "e.g. <code>/addaccount 1|+919876543210|150|1234|-|Fresh</code>\n\n"
        "<b>Many accounts at once:</b>\n"
        "<code>/bulkadd country_id|type\nphone|price|otp|2fa\nphone|price|otp|2fa</code>\n\n"
        "• Use <code>-</code> for empty OTP / 2FA\n"
        "• Duplicate phone numbers are skipped\n"
        f"{LINE}\n<b>Country IDs:</b>\n{ids}"
    )
    await show(update, text, kb(back_row()))


# ═══════════════════════════════════════════
# MANAGE STOCK
# ═══════════════════════════════════════════

@admin_required
async def stock_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    countries = await get_db(context).get_country_overview()
    if not countries:
        await show(update, "📦 <b>Manage Stock</b>\n\nNo countries yet.",
                   kb((btn("🌍 Countries", "ct_home"),), back_row()))
        return

    total_av = sum(c["available"] for c in countries)
    total_sold = sum(c["sold"] for c in countries)
    text = (
        f"📦 <b>Manage Stock</b>\n{LINE}\n"
        f"🟢 Available: <b>{total_av}</b>   🛒 Sold: <b>{total_sold}</b>\n{LINE}\n"
        "Select a country to view, edit or delete accounts:"
    )
    rows = [(btn(f"{c['flag']} {c['name']}  •  {c['available']} left"
                 + ("" if c["is_active"] else "  (hidden)"),
                 f"ms_c_{c['id']}_0", PRIMARY if c["available"] else DANGER),)
            for c in countries]
    await show(update, text, kb(*rows, back_row()))


@admin_required
async def stock_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    _, _, cid, page = update.callback_query.data.split("_")
    cid, page = int(cid), int(page)
    db = get_db(context)
    country = await db.get_country(cid)
    if not country:
        await show(update, "❌ Country not found.", kb(back_row("ms_home")))
        return

    total = await db.count_available_accounts(cid)
    pages = max(1, -(-total // PAGE_SIZE))
    page = min(page, pages - 1)
    accounts = await db.get_available_accounts_page(cid, PAGE_SIZE, page * PAGE_SIZE)

    text = (
        f"📦 <b>{country['flag']} {esc(country['name'])}</b>\n{LINE}\n"
        f"🟢 Available accounts: <b>{total}</b>\n"
        + (f"📄 Page {page + 1}/{pages}\n" if pages > 1 else "")
        + ("\nTap an account to manage it:" if total else "\nNo available accounts. Use ➕ Add Stock.")
    )
    rows = [(btn(f"📱 {a['phone_number']}  •  {a['category'] or 'Standard'}  •  ₹{a['price']:.0f}",
                 f"ms_a_{a['id']}"),) for a in accounts]
    nav = []
    if page > 0:
        nav.append(btn("◀ Prev", f"ms_c_{cid}_{page - 1}"))
    if page < pages - 1:
        nav.append(btn("Next ▶", f"ms_c_{cid}_{page + 1}"))
    await show(update, text, kb(*rows, tuple(nav), back_row("ms_home", "⬅ Countries")))


async def _account_view(db, account_id):
    """Text + keyboard for one account (shared by buttons and typed edits)."""
    a = await db.get_account(account_id)
    if not a:
        return "❌ Account not found.", kb(back_row("ms_home"))
    c = await db.get_country(a["country_id"]) or {"flag": "", "name": "?"}
    text = (
        f"📱 <b>Account #{a['id']}</b>\n{LINE}\n"
        f"🌍 Country: {c['flag']} {esc(c['name'])}\n"
        f"📞 Phone: <code>{esc(a['phone_number'])}</code>\n"
        f"🏷 Type: <b>{esc(a['category'] or 'Standard')}</b>\n"
        f"💰 Price: <b>{format_price(a['price'])}</b>\n"
        f"🔑 OTP: <code>{esc(a['otp'])}</code>\n"
        f"🔐 2FA: <code>{esc(a['two_fa'])}</code>\n"
        f"📌 Status: <b>{esc(a['status'])}</b>\n"
        f"📅 Added: {esc((a['added_at'] or '')[:16])}"
    )
    back = back_row(f"ms_c_{a['country_id']}_0", "⬅ Accounts")
    if a["status"] != "available":
        return text, kb(back)
    markup = kb(
        (btn("💰 Edit Price", f"ms_e_price_{a['id']}"), btn("🏷 Edit Type", f"ms_e_category_{a['id']}")),
        (btn("🔑 Edit OTP", f"ms_e_otp_{a['id']}"), btn("🔐 Edit 2FA", f"ms_e_twofa_{a['id']}")),
        (btn("🗑 Delete Account", f"ms_d_{a['id']}", DANGER),),
        back,
    )
    return text, markup


@admin_required
async def stock_account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    text, markup = await _account_view(get_db(context), cb_int(update))
    await show(update, text, markup)


EDIT_FIELDS = {
    "price": ("price", "💰 Send the new <b>price</b> in ₹ (e.g. <code>150</code>):"),
    "category": ("category", "🏷 Send the new <b>type</b> (e.g. Fresh, Aged, Premium):"),
    "otp": ("otp", "🔑 Send the new <b>OTP</b> (send <code>-</code> to clear):"),
    "twofa": ("two_fa", "🔐 Send the new <b>2FA</b> (send <code>-</code> to clear):"),
}


@admin_required
async def stock_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, key, aid = update.callback_query.data.split("_")
    column, prompt = EDIT_FIELDS[key]
    set_input(context, type="edit_account", account_id=int(aid), column=column)
    await show(update, f"✏ <b>Edit Account #{aid}</b>\n\n{prompt}\n\n<i>Or /cancel</i>",
               kb((btn("✖ Cancel", f"ms_a_{aid}", DANGER),)))


@admin_required
async def stock_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aid = cb_int(update)
    await show(update,
               f"🗑 <b>Delete Account #{aid}?</b>\n\nIt will be removed from the store. "
               "This cannot be undone.",
               kb((btn("🗑 Yes, Delete", f"ms_dy_{aid}", DANGER), btn("✖ No", f"ms_a_{aid}"))))


@admin_required
async def stock_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aid = cb_int(update)
    db = get_db(context)
    account = await db.get_account(aid)
    if not account or not await db.delete_account(aid):
        await show(update, "⚠ Account is already sold or removed.", kb(back_row("ms_home")))
        return
    logger.info("Admin %s removed account #%s", update.effective_user.id, aid)
    await show(update, f"✅ Account <b>#{aid}</b> deleted.",
               kb(back_row(f"ms_c_{account['country_id']}_0", "⬅ Accounts")))


async def _apply_account_edit(update, context, state, text):
    db = get_db(context)
    aid, column = state["account_id"], state["column"]
    account = await db.get_account(aid)
    if not account or account["status"] != "available":
        clear_input(context)
        await update.message.reply_text("⚠ Account is no longer available.")
        return
    if column == "price":
        try:
            value = round(float(text.replace("₹", "").replace(",", "")), 2)
            if not 0 < value < 1_000_000:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Send a valid price, e.g. <code>150</code>",
                                            parse_mode="HTML")
            return
    elif column in ("otp", "two_fa") and text == "-":
        value = None
    else:
        value = text[:200]
    await db.update_account(aid, **{column: value})
    clear_input(context)
    view, markup = await _account_view(db, aid)
    await update.message.reply_text("✅ Updated!\n\n" + view, reply_markup=markup, parse_mode="HTML")


# ═══════════════════════════════════════════
# ORDERS
# ═══════════════════════════════════════════

STATUS_ICON = {"completed": "✅", "pending": "⏳", "failed": "❌", "refunded": "↩"}


@admin_required
async def orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = await get_db(context).get_all_orders(limit=15)
    if not orders:
        text = "🧾 <b>Recent Orders</b>\n\nNo orders yet."
    else:
        lines = [f"🧾 <b>Recent Orders</b> (last {len(orders)})\n{LINE}"]
        for o in orders:
            who = f"@{o['username']}" if o.get("username") else esc(o.get("first_name") or o["user_id"])
            lines.append(
                f"{STATUS_ICON.get(o['status'], '•')} <b>#{o['id']}</b>  {format_price(o['amount'])}  "
                f"{esc(o['country_name'])}\n"
                f"     👤 {html.escape(str(who))} • {esc((o['created_at'] or '')[5:16])}"
            )
        text = "\n".join(lines)
    await show(update, text, kb(back_row()))


# ═══════════════════════════════════════════
# SALES REPORT
# ═══════════════════════════════════════════

@admin_required
async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = await get_db(context).get_sales_report()

    def line(label, key):
        return f"{label}: <b>{format_price(r[key]['revenue'])}</b> ({r[key]['orders']} orders)"

    top = "\n".join(
        f"  {i}. {c['flag']} {esc(c['name'])} — {format_price(c['revenue'])} ({c['orders']})"
        for i, c in enumerate(r["top_countries"], 1)
    ) or "  No sales yet."
    text = (
        f"📈 <b>Sales Report</b>\n{LINE}\n"
        f"{line('📅 Today', 'today')}\n"
        f"{line('🗓 Last 7 days', 'week')}\n"
        f"{line('📆 Last 30 days', 'month')}\n"
        f"{line('🏆 All time', 'all')}\n{LINE}\n"
        f"💳 Deposits today: <b>{format_price(r['deposits_today'])}</b>\n"
        f"👛 Users' wallet total: <b>{format_price(r['wallet_total'])}</b>\n"
        f"📦 Stock available: <b>{r['available_stock']}</b>\n{LINE}\n"
        f"🌍 <b>Top countries (30 days)</b>\n{top}"
    )
    await show(update, text, kb((btn("🔄 Refresh", "admin_stats"),), back_row()))


# ═══════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════

@admin_required
async def users_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    db = get_db(context)
    counts = await db.get_user_counts()
    recent = await db.get_recent_users(8)
    text = (
        f"👥 <b>Users</b>\n{LINE}\n"
        f"Total: <b>{counts['total']}</b>   🚫 Banned: <b>{counts['banned']}</b>\n{LINE}\n"
        "Recently joined (tap to manage):"
    )
    rows = [(btn(f"{'🚫 ' if u['is_banned'] else ''}{get_user_display_name(u)}  •  "
                 f"{format_price(u['balance'])}", f"us_v_{u['user_id']}"),) for u in recent]
    await show(update, text, kb((btn("🔍 Find User", "us_find", SUCCESS),), *rows, back_row()))


@admin_required
async def users_find_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_input(context, type="find_user")
    await show(update, "🔍 Send the user's <b>Telegram ID</b> or <b>@username</b>:\n\n<i>Or /cancel</i>",
               kb((btn("✖ Cancel", "us_home", DANGER),)))


async def _user_view(db, user_id):
    u = await db.get_user(user_id)
    if not u:
        return "❌ User not found. They must /start the bot first.", kb(back_row("us_home"))
    orders = await db.get_user_order_count(user_id)
    text = (
        f"👤 <b>{esc(get_user_display_name(u))}</b>\n{LINE}\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"🔗 Username: {('@' + esc(u['username'])) if u['username'] else '—'}\n"
        f"💰 Balance: <b>{format_price(u['balance'])}</b>\n"
        f"💳 Deposited: {format_price(u['total_deposits'])}\n"
        f"🛒 Spent: {format_price(u['total_spent'])} ({orders} orders)\n"
        f"📅 Joined: {esc((u['joined_at'] or '')[:10])}\n"
        f"📌 Status: {'🚫 <b>Banned</b>' if u['is_banned'] else '🟢 Active'}"
    )
    uid = u["user_id"]
    ban = (btn("✅ Unban", f"us_unban_{uid}", SUCCESS) if u["is_banned"]
           else btn("🚫 Ban", f"us_ban_{uid}", DANGER))
    markup = kb(
        (btn("➕ Add Balance", f"us_add_{uid}", SUCCESS), btn("➖ Deduct", f"us_cut_{uid}", DANGER)),
        (ban, InlineKeyboardButton("💬 Message", url=f"tg://user?id={uid}", style=PRIMARY)),
        back_row("us_home", "⬅ Users"),
    )
    return text, markup


@admin_required
async def users_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    text, markup = await _user_view(get_db(context), cb_int(update))
    await show(update, text, markup)


@admin_required
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/user <id or @username>"""
    if not context.args:
        await update.message.reply_text("Usage: <code>/user ID</code> or <code>/user @username</code>",
                                        parse_mode="HTML")
        return
    await _find_and_show_user(update, context, context.args[0])


async def _find_and_show_user(update, context, query_text):
    db = get_db(context)
    user = await db.find_user(query_text)
    if not user:
        await update.message.reply_text("❌ User not found. They must /start the bot first.",
                                        reply_markup=kb(back_row("us_home", "⬅ Users")))
        return
    clear_input(context)
    text, markup = await _user_view(db, user["user_id"])
    await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


@admin_required
async def users_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action, uid = update.callback_query.data.split("_")[1:]
    uid = int(uid)
    if action == "ban" and is_admin(uid):
        await update.callback_query.answer("You can't ban an admin.", show_alert=True)
        return
    db = get_db(context)
    await db.set_banned(uid, action == "ban")
    logger.info("Admin %s %sned user %s", update.effective_user.id, action, uid)
    text, markup = await _user_view(db, uid)
    await show(update, text, markup)


@admin_required
async def users_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action, uid = update.callback_query.data.split("_")[1:]
    op = "add" if action == "add" else "subtract"
    set_input(context, type="balance", user_id=int(uid), op=op)
    word = "add to" if op == "add" else "deduct from"
    await show(update, f"💰 Send the amount in ₹ to <b>{word}</b> user <code>{uid}</code>:\n\n<i>Or /cancel</i>",
               kb((btn("✖ Cancel", f"us_v_{uid}", DANGER),)))


async def _apply_balance(update, context, state, text):
    db = get_db(context)
    uid, op = state["user_id"], state["op"]
    try:
        amount = round(float(text.replace("₹", "").replace(",", "")), 2)
        if not 0 < amount <= 1_000_000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Send a valid amount, e.g. <code>100</code>", parse_mode="HTML")
        return
    balance = await db.get_user_balance(uid)
    if op == "subtract" and amount > balance:
        await update.message.reply_text(f"❌ User only has {format_price(balance)}.")
        return

    new_balance = await db.update_balance(uid, amount, op)
    tx = await db.create_transaction(
        uid, "admin_credit" if op == "add" else "admin_debit", amount,
        description=f"Manual {'credit' if op == 'add' else 'debit'} by admin {update.effective_user.id}",
        reference="ADMIN"
    )
    await db.complete_transaction(tx, new_balance)
    clear_input(context)
    logger.info("Admin %s %s %.2f for user %s", update.effective_user.id, op, amount, uid)

    sign = "+" if op == "add" else "-"
    try:
        await context.bot.send_message(
            uid,
            f"{'💰' if op == 'add' else '➖'} <b>Wallet {'Credited' if op == 'add' else 'Debited'}</b>\n\n"
            f"Amount: <b>{sign}{format_price(amount)}</b>\n"
            f"New Balance: <b>{format_price(new_balance)}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Could not notify user %s: %s", uid, e)

    view, markup = await _user_view(db, uid)
    await update.message.reply_text(f"✅ {sign}{format_price(amount)} done.\n\n" + view,
                                    reply_markup=markup, parse_mode="HTML")


# ═══════════════════════════════════════════
# COUNTRIES
# ═══════════════════════════════════════════

@admin_required
async def countries_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = await get_db(context).get_country_overview()
    text = (
        f"🌍 <b>Countries</b>\n{LINE}\n"
        "Tap a country to <b>show / hide</b> it in the store.\n"
        "🟢 = visible   🔴 = hidden\n\n"
        "<b>Add a country:</b>\n<code>/addcountry Name|CODE|Flag</code>\n"
        "e.g. <code>/addcountry India|IN|🇮🇳</code>"
    )
    rows = [(btn(f"{'🟢' if c['is_active'] else '🔴'} {c['flag']} {c['name']} (ID {c['id']})  •  "
                 f"{c['available']} left", f"ct_t_{c['id']}",
                 SUCCESS if c["is_active"] else DANGER),) for c in countries]
    await show(update, text, kb(*rows, back_row()))


@admin_required
async def countries_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db(context)
    country = await db.get_country(cb_int(update))
    if country:
        await db.set_country_active(country["id"], not country["is_active"])
    await countries_home_callback(update, context)


# ═══════════════════════════════════════════
# BROADCAST
# ═══════════════════════════════════════════

@admin_required
async def broadcast_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_input(context, type="broadcast")
    await show(update,
               "📢 <b>Broadcast</b>\n\nSend the message you want to send to all users.\n"
               "Text, photo, video or file all work, and it is sent exactly as you write it.\n\n"
               "<i>Or /cancel</i>",
               kb((btn("✖ Cancel", "bc_cancel", DANGER),)))


async def _broadcast_preview(update, context):
    msg = update.message
    context.user_data["bc_msg"] = (msg.chat_id, msg.message_id)
    clear_input(context)
    users = len(await get_db(context).get_broadcast_user_ids())
    await msg.reply_text(
        f"👆 <b>Preview above.</b>\n\nSend this to <b>{users}</b> users?",
        reply_markup=kb((btn(f"✅ Send to {users} users", "bc_send", SUCCESS),
                         btn("✖ Cancel", "bc_cancel", DANGER))),
        parse_mode="HTML"
    )


@admin_required
async def broadcast_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_input(context)
    context.user_data.pop("bc_msg", None)
    await show(update, "✖ Broadcast cancelled.", kb(back_row(label="🛠 Dashboard")))


@admin_required
async def broadcast_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = context.user_data.pop("bc_msg", None)
    if not source:
        await show(update, "⚠ Nothing to send. Start again.", kb(back_row()))
        return
    user_ids = await get_db(context).get_broadcast_user_ids()
    await show(update, f"📤 Broadcasting to <b>{len(user_ids)}</b> users…\nI'll report when done.")
    context.application.create_task(
        _run_broadcast(context.bot, update.effective_chat.id, source, user_ids)
    )


async def _run_broadcast(bot, admin_chat_id, source, user_ids):
    from_chat, message_id = source
    sent = blocked = failed = 0
    for uid in user_ids:
        for attempt in range(2):
            try:
                await bot.copy_message(uid, from_chat, message_id)
                sent += 1
                break
            except RetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except Forbidden:
                blocked += 1
                break
            except Exception as e:
                failed += 1
                logger.warning("Broadcast to %s failed: %s", uid, e)
                break
        else:
            failed += 1
        await asyncio.sleep(0.05)  # ~20 msg/s, under Telegram's 30/s limit

    await bot.send_message(
        admin_chat_id,
        f"📢 <b>Broadcast finished</b>\n\n✅ Sent: <b>{sent}</b>\n"
        f"🚫 Blocked bot: <b>{blocked}</b>\n❌ Failed: <b>{failed}</b>",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════

@admin_required
async def backup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button or /backup: send a copy of the database file to the admin."""
    if update.callback_query:
        await update.callback_query.answer("Preparing backup…")
    path = os.path.join(tempfile.gettempdir(), f"backup_{datetime.now(IST):%Y%m%d_%H%M%S}.db")
    try:
        await get_db(context).backup_to(path)
        with open(path, "rb") as f:
            await context.bot.send_document(
                update.effective_chat.id, f, filename=os.path.basename(path),
                caption=f"💾 Database backup • {datetime.now(IST):%d %b %Y, %I:%M %p}\n"
                        "Keep this file private: it contains all accounts and balances."
            )
    except Exception as e:
        logger.error("Backup failed: %s", e)
        await context.bot.send_message(update.effective_chat.id, f"❌ Backup failed: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)


# ═══════════════════════════════════════════
# TYPED INPUT ROUTER + BAN GUARD
# ═══════════════════════════════════════════

async def admin_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route the admin's next message to whatever the panel asked for."""
    state = context.user_data.get(STATE_KEY)
    if not state or not update.effective_user or not is_admin(update.effective_user.id):
        return
    text = (update.message.text or "").strip()

    # Pressing a main-menu button leaves the admin input mode
    if text in MENU_BUTTON_TEXTS:
        clear_input(context)
        return

    kind = state["type"]
    if kind == "broadcast":
        await _broadcast_preview(update, context)
    elif not text:
        await update.message.reply_text("✏ Please send text, or /cancel.")
    elif kind == "edit_account":
        await _apply_account_edit(update, context, state, text)
    elif kind == "balance":
        await _apply_balance(update, context, state, text)
    elif kind == "find_user":
        await _find_and_show_user(update, context, text)
    raise ApplicationHandlerStop


async def ban_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block banned users from using the bot at all."""
    user = update.effective_user
    db = context.bot_data.get("db")
    if not user or not db or is_admin(user.id) or not await db.is_banned(user.id):
        return
    if update.callback_query:
        await update.callback_query.answer("🚫 You are banned from this bot.", show_alert=True)
    elif update.message:
        await update.message.reply_text("🚫 You are banned from using this bot.")
    raise ApplicationHandlerStop


# ═══════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════

def register_admin_panel(application: Application):
    application.add_handler(TypeHandler(Update, ban_guard), group=-10)
    application.add_handler(
        MessageHandler(filters.UpdateType.MESSAGE & filters.ChatType.PRIVATE & ~filters.COMMAND,
                       admin_input_handler), group=-2
    )

    for name, fn in (("admin", admin_command), ("cancel", cancel_command),
                     ("user", user_command), ("backup", backup_handler)):
        application.add_handler(CommandHandler(name, fn))

    for pattern, fn in (
        (r"^admin_back$", admin_command),
        (r"^admin_close$", admin_close_callback),
        (r"^adm_add$", add_stock_callback),
        (r"^ms_home$", stock_home_callback),
        (r"^ms_c_\d+_\d+$", stock_country_callback),
        (r"^ms_a_\d+$", stock_account_callback),
        (r"^ms_e_(price|category|otp|twofa)_\d+$", stock_edit_callback),
        (r"^ms_d_\d+$", stock_delete_callback),
        (r"^ms_dy_\d+$", stock_delete_confirm_callback),
        (r"^admin_orders$", orders_callback),
        (r"^admin_stats$", stats_callback),
        (r"^us_home$", users_home_callback),
        (r"^us_find$", users_find_callback),
        (r"^us_v_\d+$", users_view_callback),
        (r"^us_(ban|unban)_\d+$", users_ban_callback),
        (r"^us_(add|cut)_\d+$", users_balance_callback),
        (r"^ct_home$", countries_home_callback),
        (r"^ct_t_\d+$", countries_toggle_callback),
        (r"^bc_start$", broadcast_start_callback),
        (r"^bc_send$", broadcast_send_callback),
        (r"^bc_cancel$", broadcast_cancel_callback),
        (r"^admin_backup$", backup_handler),
    ):
        application.add_handler(CallbackQueryHandler(fn, pattern=pattern))

    logger.info("Admin panel registered.")
