"""
Buy Account Handlers
Account selection and purchase flow
"""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session

from bot.config import SUPPORTED_COUNTRIES
from database.models import Account, AccountType, User
from database import get_db

router = Router()

class BuyAccountStates(StatesGroup):
    """States for buying account flow"""
    select_country = State()
    select_account = State()
    confirm_purchase = State()
    processing_payment = State()

@router.callback_query(lambda c: c.data == "buy_account")
async def buy_account_start(callback: types.CallbackQuery, state: FSMContext):
    """Start buying account process - show country selection"""
    keyboard_buttons = []
    
    # Create country buttons in rows of 2
    for i in range(0, len(SUPPORTED_COUNTRIES), 2):
        row = []
        for j in range(2):
            if i + j < len(SUPPORTED_COUNTRIES):
                country = SUPPORTED_COUNTRIES[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=f"{country['flag']} {country['name']}",
                        callback_data=f"country_{country['code']}"
                    )
                )
        keyboard_buttons.append(row)
    
    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        "🌍 **Select Country**\n\n"
        "Choose the country for the account you want to purchase:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("country_"))
async def select_country(callback: types.CallbackQuery, state: FSMContext):
    """Handle country selection"""
    country_code = callback.data.replace("country_", "")
    
    # Find country info
    country_info = next((c for c in SUPPORTED_COUNTRIES if c["code"] == country_code), None)
    
    if not country_info:
        await callback.answer("Invalid country selection", show_alert=True)
        return
    
    await state.update_data(selected_country=country_code)
    await state.set_state(BuyAccountStates.select_account)
    
    # Get available accounts for this country
    db: Session = next(get_db())
    accounts = db.query(Account).filter(
        Account.country == country_code,
        Account.stock > 0,
        Account.is_active == True
    ).all()
    
    if not accounts:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Choose Another Country", callback_data="buy_account")],
                [InlineKeyboardButton(text="🏠 Back to Menu", callback_data="menu")]
            ]
        )
        
        await callback.message.edit_text(
            f"📭 **No Accounts Available**\n\n"
            f"Currently no accounts available for {country_info['flag']} {country_info['name']}.\n"
            f"Please check back later or select another country.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    # Create account selection buttons
    keyboard_buttons = []
    
    for account in accounts:
        account_type_emoji = {
            AccountType.SOCIAL_MEDIA.value: "📱",
            AccountType.STREAMING.value: "🎬",
            AccountType.GAMING.value: "🎮",
            AccountType.EMAIL.value: "📧",
            AccountType.OTHER.value: "🔧"
        }.get(account.account_type.value, "🔧")
        
        button_text = (
            f"{account_type_emoji} {account.title}\n"
            f"💰 ₹{account.price} | 📦 {account.stock} left"
        )
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"account_{account.id}"
            )
        ])
    
    # Add navigation buttons
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Back", callback_data="buy_account"),
        InlineKeyboardButton(text="🏠 Menu", callback_data="menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(
        f"🛒 **Available Accounts - {country_info['flag']} {country_info['name']}**\n\n"
        "Select an account to purchase:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("account_"))
async def select_account(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """Handle account selection"""
    account_id = int(callback.data.replace("account_", ""))
    
    # Get account details
    account = db.query(Account).filter(Account.id == account_id).first()
    
    if not account:
        await callback.answer("Account not found", show_alert=True)
        return
    
    # Get country info
    country_info = next((c for c in SUPPORTED_COUNTRIES if c["code"] == account.country), {})
    country_name = country_info.get("name", account.country)
    country_flag = country_info.get("flag", "🌍")
    
    # Get account type emoji
    account_type_emoji = {
        AccountType.SOCIAL_MEDIA.value: "📱 Social Media",
        AccountType.STREAMING.value: "🎬 Streaming",
        AccountType.GAMING.value: "🎮 Gaming",
        AccountType.EMAIL.value: "📧 Email",
        AccountType.OTHER.value: "🔧 Other"
    }.get(account.account_type.value, "🔧 Other")
    
    # Save selected account to state
    await state.update_data(
        selected_account_id=account.id,
        account_price=account.price,
        account_title=account.title
    )
    await state.set_state(BuyAccountStates.confirm_purchase)
    
    # Prepare account details message
    details = f"📝 **Account Details**\n\n"
    details += f"**Title:** {account.title}\n"
    details += f"**Type:** {account_type_emoji}\n"
    details += f"**Country:** {country_flag} {country_name}\n"
    details += f"**Price:** ₹{account.price}\n"
    details += f"**Stock:** {account.stock} available\n\n"
    
    if account.description:
        details += f"**Description:**\n{account.description}\n\n"
    
    details += "**Delivery:**\n"
    details += "✅ Phone Number\n"
    details += "✅ OTP (if required)\n"
    details += "✅ 2FA Details (if available)\n\n"
    details += "**Note:** Delivery is automatic after payment."

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm Purchase", callback_data="confirm_purchase")],
            [
                InlineKeyboardButton(text="🔙 Back", callback_data=f"country_{account.country}"),
                InlineKeyboardButton(text="🏠 Menu", callback_data="menu")
            ]
        ]
    )
    
    await callback.message.edit_text(details, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "confirm_purchase")
async def confirm_purchase(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """Confirm purchase and check user balance"""
    # Get state data
    state_data = await state.get_data()
    account_id = state_data.get("selected_account_id")
    account_price = state_data.get("account_price")
    
    if not account_id or not account_price:
        await callback.answer("Session expired. Please start again.", show_alert=True)
        await state.clear()
        return
    
    # Get account
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account or account.stock <= 0:
        await callback.answer("Account is out of stock", show_alert=True)
        return
    
    # Get user
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not user:
        # Create user if doesn't exist
        user = User(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            balance=0.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Check balance
    if user.balance < account_price:
        insufficient_text = (
            "💰 **Insufficient Balance**\n\n"
            f"Required: ₹{account_price}\n"
            f"Your balance: ₹{user.balance}\n\n"
            "Please deposit funds to continue."
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Deposit Now", callback_data="deposit")],
                [
                    InlineKeyboardButton(text="🔙 Back", callback_data=f"account_{account_id}"),
                    InlineKeyboardButton(text="🏠 Menu", callback_data="menu")
                ]
            ]
        )
        
        await callback.message.edit_text(insufficient_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
    
    # Proceed with purchase
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Complete Purchase", callback_data="complete_purchase")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"account_{account_id}")]
        ]
    )
    
    confirm_text = (
        "✅ **Purchase Confirmation**\n\n"
        f"**Account:** {account.title}\n"
        f"**Price:** ₹{account_price}\n"
        f"**Your Balance:** ₹{user.balance}\n"
        f"**After Purchase:** ₹{user.balance - account_price}\n\n"
        "Click 'Complete Purchase' to proceed."
    )
    
    await callback.message.edit_text(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "complete_purchase")
async def complete_purchase(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """Complete the purchase and deliver account"""
    # Get state data
    state_data = await state.get_data()
    account_id = state_data.get("selected_account_id")
    account_price = state_data.get("account_price")
    
    if not account_id or not account_price:
        await callback.answer("Session expired", show_alert=True)
        await state.clear()
        return
    
    # Get account and user
    account = db.query(Account).filter(Account.id == account_id).first()
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not account or account.stock <= 0:
        await callback.answer("Account is out of stock", show_alert=True)
        return
    
    if not user or user.balance < account_price:
        await callback.answer("Insufficient balance", show_alert=True)
        return
    
    try:
        # Start transaction
        # Deduct balance
        user.balance -= account_price
        
        # Reduce stock
        account.stock -= 1
        
        # Create order (simplified for now)
        # In full implementation, you would create proper order with delivery logic
        
        db.commit()
        
        # Prepare delivery message
        delivery_text = (
            "🎉 **Purchase Successful!**\n\n"
            f"**Account:** {account.title}\n"
            f"**Amount:** ₹{account_price}\n"
            f"**New Balance:** ₹{user.balance}\n\n"
            "📦 **Account Details Delivered:**\n\n"
        )
        
        # Add credentials if available
        if account.credentials:
            delivery_text += f"**Phone Number:** {account.credentials}\n"
        
        if account.otp:
            delivery_text += f"**OTP:** {account.otp}\n"
        
        if account.two_factor:
            delivery_text += f"**2FA Details:** {account.two_factor}\n"
        
        delivery_text += "\n⚠️ **Important:**\n"
        delivery_text += "• Never share these details with anyone\n"
        delivery_text += "• Change passwords immediately\n"
        delivery_text += "• Contact support if you face any issues\n\n"
        delivery_text += f"**Support:** {SUPPORT_USERNAME}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Order History", callback_data="order_history")],
                [InlineKeyboardButton(text="🛒 Buy Another Account", callback_data="buy_account")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu")]
            ]
        )
        
        await callback.message.edit_text(delivery_text, reply_markup=keyboard, parse_mode="Markdown")
        await state.clear()
        
    except Exception as e:
        db.rollback()
        await callback.answer(f"Purchase failed: {str(e)}", show_alert=True)
        raise
    
    await callback.answer()