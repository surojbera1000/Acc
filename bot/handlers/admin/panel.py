"""
Admin Panel Handlers
Admin-only commands and functionality
"""

from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from sqlalchemy import func

from bot.config import ADMIN_IDS
from database.models import User, Account, Order, Transaction
from database import get_db

router = Router()

class AddAccountStates(StatesGroup):
    """States for adding new account"""
    enter_type = State()
    enter_country = State()
    enter_title = State()
    enter_description = State()
    enter_price = State()
    enter_stock = State()
    enter_credentials = State()
    confirm_details = State()

@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Admin panel access"""
    # Check if user is admin
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied. Admin only.")
        return
    
    admin_text = (
        "👑 **Admin Panel**\n\n"
        "**Available Commands:**\n"
        "/stats - View bot statistics\n"
        "/users - List all users\n"
        "/add_account - Add new account\n"
        "/stock - View stock status\n"
        "/orders - View recent orders\n"
        "/transactions - View transactions\n\n"
        "**Quick Actions:**"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="➕ Add Account", callback_data="admin_add_account"),
                InlineKeyboardButton(text="📦 Stock", callback_data="admin_stock")
            ],
            [
                InlineKeyboardButton(text="📋 Orders", callback_data="admin_orders"),
                InlineKeyboardButton(text="💳 Transactions", callback_data="admin_transactions")
            ]
        ]
    )
    
    await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(Command("stats"))
async def admin_stats(message: types.Message, db: Session):
    """Show bot statistics"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied")
        return
    
    # Get statistics
    total_users = db.query(func.count(User.id)).scalar()
    total_accounts = db.query(func.count(Account.id)).scalar()
    active_accounts = db.query(func.count(Account.id)).filter(Account.is_active == True).scalar()
    total_stock = db.query(func.sum(Account.stock)).scalar() or 0
    total_orders = db.query(func.count(Order.id)).scalar()
    total_transactions = db.query(func.count(Transaction.id)).scalar()
    total_revenue = db.query(func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == "purchase",
        Transaction.is_successful == True
    ).scalar() or 0
    
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"**👥 Total Users:** {total_users}\n"
        f"**🛍️ Total Accounts:** {total_accounts}\n"
        f"**✅ Active Accounts:** {active_accounts}\n"
        f"**📦 Total Stock:** {total_stock}\n"
        f"**📋 Total Orders:** {total_orders}\n"
        f"**💳 Total Transactions:** {total_transactions}\n"
        f"**💰 Total Revenue:** ₹{total_revenue}\n\n"
        
        "**📈 Recent Activity (Last 24h):**\n"
        "• New users: [Loading...]\n"
        "• New orders: [Loading...]\n"
        "• Revenue: [Loading...]\n\n"
        
        "💡 Use /users, /orders, /transactions for detailed info."
    )
    
    await message.answer(stats_text, parse_mode="Markdown")

@router.message(Command("users"))
async def admin_users(message: types.Message, db: Session):
    """List all users"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied")
        return
    
    # Get users ordered by registration date
    users = db.query(User).order_by(User.created_at.desc()).limit(50).all()
    
    if not users:
        await message.answer("📭 No users found")
        return
    
    users_text = "👥 **Registered Users**\n\n"
    
    for i, user in enumerate(users, 1):
        username = f"@{user.username}" if user.username else "No username"
        created = user.created_at.strftime("%d %b")
        
        users_text += f"{i}. {username} - ₹{user.balance} (ID: {user.telegram_id}) - {created}\n"
        
        # Limit to avoid message too long
        if i >= 20:
            users_text += f"\n... and {len(users) - i} more users"
            break
    
    users_text += f"\n\n📊 **Total:** {len(users)} users"
    
    await message.answer(users_text, parse_mode="Markdown")

@router.message(Command("stock"))
async def admin_stock(message: types.Message, db: Session):
    """View stock status"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied")
        return
    
    # Get accounts grouped by country
    accounts_by_country = {}
    accounts = db.query(Account).filter(Account.is_active == True).all()
    
    for account in accounts:
        if account.country not in accounts_by_country:
            accounts_by_country[account.country] = []
        accounts_by_country[account.country].append(account)
    
    if not accounts_by_country:
        await message.answer("📭 No accounts in stock")
        return
    
    stock_text = "📦 **Stock Status**\n\n"
    
    for country_code, country_accounts in accounts_by_country.items():
        total_stock = sum(acc.stock for acc in country_accounts)
        total_value = sum(acc.price * acc.stock for acc in country_accounts)
        
        stock_text += f"**{country_code}:** {len(country_accounts)} items, {total_stock} units, ₹{total_value} value\n"
        
        # Show top 3 accounts for each country
        for i, account in enumerate(country_accounts[:3], 1):
            stock_text += f"  {i}. {account.title} - ₹{account.price} ({account.stock} left)\n"
        
        stock_text += "\n"
    
    # Add summary
    all_accounts = sum(len(accs) for accs in accounts_by_country.values())
    all_stock = sum(sum(acc.stock for acc in accs) for accs in accounts_by_country.values())
    all_value = sum(sum(acc.price * acc.stock for acc in accs) for accs in accounts_by_country.values())
    
    stock_text += f"📊 **Total:** {all_accounts} items, {all_stock} units, ₹{all_value} total value"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Add Stock", callback_data="admin_add_account")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stock")]
        ]
    )
    
    await message.answer(stock_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(Command("orders"))
async def admin_orders(message: types.Message, db: Session):
    """View recent orders"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied")
        return
    
    # Get recent orders
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(20).all()
    
    if not orders:
        await message.answer("📭 No orders found")
        return
    
    orders_text = "📋 **Recent Orders**\n\n"
    
    for i, order in enumerate(orders, 1):
        # Get user info
        user = db.query(User).filter(User.id == order.user_id).first()
        username = f"@{user.username}" if user and user.username else f"ID:{user.telegram_id}" if user else "Unknown"
        
        # Get account info
        account = db.query(Account).filter(Account.id == order.account_id).first()
        account_title = account.title if account else "Unknown"
        
        # Format time
        time_str = order.created_at.strftime("%d %b %H:%M")
        
        # Status emoji
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "delivered": "✅",
            "failed": "❌",
            "refunded": "↩️"
        }.get(order.status.value, "❓")
        
        orders_text += f"{i}. {status_emoji} ₹{order.amount} - {account_title[:20]}... ({username}) - {time_str}\n"
        
        if i >= 10:
            orders_text += f"\n... and {len(orders) - i} more orders"
            break
    
    orders_text += f"\n\n📊 **Total Orders:** {len(orders)}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_orders")],
            [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")]
        ]
    )
    
    await message.answer(orders_text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(Command("transactions"))
async def admin_transactions(message: types.Message, db: Session):
    """View recent transactions"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Access denied")
        return
    
    # Get recent transactions
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(20).all()
    
    if not transactions:
        await message.answer("📭 No transactions found")
        return
    
    trans_text = "💳 **Recent Transactions**\n\n"
    
    for i, tx in enumerate(transactions, 1):
        # Get user info
        user = db.query(User).filter(User.id == tx.user_id).first()
        username = f"@{user.username}" if user and user.username else f"ID:{user.telegram_id}" if user else "Unknown"
        
        # Format type
        type_emoji = {
            "deposit": "⬆️",
            "withdrawal": "⬇️",
            "purchase": "🛒",
            "refund": "↩️"
        }.get(tx.transaction_type.value, "💳")
        
        type_text = tx.transaction_type.value.capitalize()
        
        # Format time
        time_str = tx.created_at.strftime("%d %b %H:%M")
        
        # Status
        status = "✅" if tx.is_successful else "❌"
        
        trans_text += f"{i}. {type_emoji} {type_text} ₹{tx.amount} ({username}) - {time_str} {status}\n"
        
        if i >= 10:
            trans_text += f"\n... and {len(transactions) - i} more"
            break
    
    # Summary
    total_amount = sum(tx.amount for tx in transactions if tx.is_successful)
    trans_text += f"\n📊 **Total:** {len(transactions)} transactions, ₹{total_amount} amount"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_transactions")],
            [InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")]
        ]
    )
    
    await message.answer(trans_text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback_handlers(callback: types.CallbackQuery, db: Session):
    """Handle admin callback queries"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Access denied", show_alert=True)
        return
    
    action = callback.data
    
    if action == "admin_stats":
        await admin_stats(callback.message, db)
    elif action == "admin_users":
        await admin_users(callback.message, db)
    elif action == "admin_stock":
        await admin_stock(callback.message, db)
    elif action == "admin_orders":
        await admin_orders(callback.message, db)
    elif action == "admin_transactions":
        await admin_transactions(callback.message, db)
    elif action == "admin_add_account":
        await admin_add_account_start(callback)
    
    await callback.answer()

async def admin_add_account_start(callback: types.CallbackQuery):
    """Start adding new account"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Access denied", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Social Media", callback_data="acc_type_social_media"),
                InlineKeyboardButton(text="🎬 Streaming", callback_data="acc_type_streaming")
            ],
            [
                InlineKeyboardButton(text="🎮 Gaming", callback_data="acc_type_gaming"),
                InlineKeyboardButton(text="📧 Email", callback_data="acc_type_email")
            ],
            [InlineKeyboardButton(text="🔧 Other", callback_data="acc_type_other")],
            [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin")]
        ]
    )
    
    await callback.message.edit_text(
        "➕ **Add New Account**\n\n"
        "Select account type:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

# Note: The full add account flow with states would be implemented here
# This is a simplified version showing the structure