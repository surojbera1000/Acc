"""
Deposit Handlers
UPI payment and wallet top-up
"""

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
import random
import string
from datetime import datetime

from bot.config import UPI_ID, MINIMUM_DEPOSIT, MAXIMUM_DEPOSIT, DEFAULT_CURRENCY
from database.models import User, Transaction, TransactionType
from database import get_db

router = Router()

class DepositStates(StatesGroup):
    """States for deposit flow"""
    enter_amount = State()
    confirm_payment = State()
    verify_payment = State()

@router.callback_query(lambda c: c.data == "deposit")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """Start deposit process"""
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
    
    info_text = (
        "💳 **Deposit Funds**\n\n"
        f"**Current Balance:** ₹{user.balance}\n"
        f"**Minimum Deposit:** ₹{MINIMUM_DEPOSIT}\n"
        f"**Maximum Deposit:** ₹{MAXIMUM_DEPOSIT}\n\n"
        "**Payment Method:** UPI\n"
        "**Process:**\n"
        "1. Enter deposit amount\n"
        "2. Make payment via UPI\n"
        "3. Balance updates automatically\n\n"
        "Enter the amount you want to deposit:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="₹100", callback_data="amount_100"),
                InlineKeyboardButton(text="₹500", callback_data="amount_500"),
                InlineKeyboardButton(text="₹1000", callback_data="amount_1000")
            ],
            [
                InlineKeyboardButton(text="₹2000", callback_data="amount_2000"),
                InlineKeyboardButton(text="₹5000", callback_data="amount_5000"),
                InlineKeyboardButton(text="₹10000", callback_data="amount_10000")
            ],
            [InlineKeyboardButton(text="✏️ Custom Amount", callback_data="custom_amount")],
            [
                InlineKeyboardButton(text="🔙 Back", callback_data="menu"),
                InlineKeyboardButton(text="💰 Check Wallet", callback_data="wallet")
            ]
        ]
    )
    
    await state.set_state(DepositStates.enter_amount)
    await callback.message.edit_text(info_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("amount_"))
async def select_amount(callback: types.CallbackQuery, state: FSMContext):
    """Handle predefined amount selection"""
    amount_str = callback.data.replace("amount_", "")
    
    try:
        amount = float(amount_str)
        
        # Validate amount
        if amount < MINIMUM_DEPOSIT:
            await callback.answer(f"Minimum deposit is ₹{MINIMUM_DEPOSIT}", show_alert=True)
            return
        
        if amount > MAXIMUM_DEPOSIT:
            await callback.answer(f"Maximum deposit is ₹{MAXIMUM_DEPOSIT}", show_alert=True)
            return
        
        await state.update_data(deposit_amount=amount)
        await show_payment_details(callback, state, amount)
        
    except ValueError:
        await callback.answer("Invalid amount", show_alert=True)

@router.callback_query(lambda c: c.data == "custom_amount")
async def custom_amount(callback: types.CallbackQuery, state: FSMContext):
    """Request custom amount"""
    await state.set_state(DepositStates.enter_amount)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="deposit")]
        ]
    )
    
    await callback.message.edit_text(
        "✏️ **Enter Custom Amount**\n\n"
        f"Please enter the amount you want to deposit (₹{MINIMUM_DEPOSIT} - ₹{MAXIMUM_DEPOSIT}):\n\n"
        "Example: 1500",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(DepositStates.enter_amount)
async def process_custom_amount(message: types.Message, state: FSMContext):
    """Process custom amount input"""
    try:
        amount = float(message.text.strip())
        
        # Validate amount
        if amount < MINIMUM_DEPOSIT:
            await message.answer(f"❌ Minimum deposit is ₹{MINIMUM_DEPOSIT}")
            return
        
        if amount > MAXIMUM_DEPOSIT:
            await message.answer(f"❌ Maximum deposit is ₹{MAXIMUM_DEPOSIT}")
            return
        
        await state.update_data(deposit_amount=amount)
        await show_payment_details(message, state, amount)
        
    except ValueError:
        await message.answer("❌ Please enter a valid number")

async def show_payment_details(update, state: FSMContext, amount: float):
    """Show payment details for the selected amount"""
    # Generate unique transaction ID
    transaction_id = generate_transaction_id()
    await state.update_data(transaction_id=transaction_id)
    
    payment_text = (
        "✅ **Payment Details**\n\n"
        f"**Amount:** ₹{amount}\n"
        f"**Transaction ID:** {transaction_id}\n\n"
        "**UPI Payment Instructions:**\n\n"
    )
    
    if UPI_ID:
        # Show UPI ID for payment
        payment_text += f"**Send payment to:** `{UPI_ID}`\n\n"
        payment_text += "**Steps:**\n"
        payment_text += "1. Open your UPI app\n"
        payment_text += f"2. Send ₹{amount} to {UPI_ID}\n"
        payment_text += f"3. Add note: {transaction_id}\n"
        payment_text += "4. Click 'I have paid' below\n\n"
        payment_text += "**Important:**\n"
        payment_text += "• Include transaction ID in payment note\n"
        payment_text += "• Balance updates automatically\n"
        payment_text += "• Contact support if issues occur"
    else:
        # Manual payment instructions
        payment_text += "**Contact Admin for Payment:**\n"
        payment_text += "Send your payment receipt with transaction ID to admin\n"
        payment_text += "Admin will manually update your balance"
    
    keyboard_buttons = []
    
    if UPI_ID:
        keyboard_buttons.append([InlineKeyboardButton(text="✅ I have paid", callback_data="verify_payment")])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Change Amount", callback_data="deposit"),
        InlineKeyboardButton(text="🏠 Menu", callback_data="menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if isinstance(update, types.CallbackQuery):
        await update.message.edit_text(payment_text, reply_markup=keyboard, parse_mode="Markdown")
        await update.answer()
    else:
        await update.answer(payment_text, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.set_state(DepositStates.confirm_payment)

@router.callback_query(lambda c: c.data == "verify_payment", DepositStates.confirm_payment)
async def verify_payment(callback: types.CallbackQuery, state: FSMContext, db: Session):
    """Verify payment and update balance"""
    # Get state data
    state_data = await state.get_data()
    amount = state_data.get("deposit_amount")
    transaction_id = state_data.get("transaction_id")
    
    if not amount or not transaction_id:
        await callback.answer("Session expired", show_alert=True)
        await state.clear()
        return
    
    # Get user
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    # In a real implementation, you would:
    # 1. Verify payment with payment gateway API
    # 2. Check if transaction is successful
    # 3. Update balance only if payment is verified
    
    # For this example, we'll simulate automatic verification
    try:
        # Simulate payment verification (replace with actual API call)
        payment_verified = simulate_payment_verification(transaction_id)
        
        if payment_verified:
            # Update user balance
            user.balance += amount
            
            # Create transaction record
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user.id,
                transaction_type=TransactionType.DEPOSIT,
                amount=amount,
                description=f"UPI Deposit - ₹{amount}",
                metadata="{}",
                is_successful=True
            )
            db.add(transaction)
            
            db.commit()
            
            success_text = (
                "🎉 **Payment Successful!**\n\n"
                f"**Amount:** ₹{amount}\n"
                f"**Transaction ID:** {transaction_id}\n"
                f"**New Balance:** ₹{user.balance}\n\n"
                "Your balance has been updated successfully."
            )
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 Buy Account", callback_data="buy_account")],
                    [InlineKeyboardButton(text="💰 Check Wallet", callback_data="wallet")],
                    [InlineKeyboardButton(text="🏠 Main Menu", callback_data="menu")]
                ]
            )
            
            await callback.message.edit_text(success_text, reply_markup=keyboard, parse_mode="Markdown")
            await state.clear()
            
        else:
            # Payment not verified
            await callback.answer("Payment not verified. Please try again or contact support.", show_alert=True)
            
    except Exception as e:
        db.rollback()
        error_text = (
            "❌ **Payment Error**\n\n"
            f"Error: {str(e)}\n\n"
            "Please contact support with your transaction ID."
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Try Again", callback_data="deposit")],
                [InlineKeyboardButton(text="🏠 Menu", callback_data="menu")]
            ]
        )
        
        await callback.message.edit_text(error_text, reply_markup=keyboard, parse_mode="Markdown")
    
    await callback.answer()

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TXN{timestamp}{random_str}"

def simulate_payment_verification(transaction_id: str) -> bool:
    """
    Simulate payment verification
    In production, replace with actual payment gateway API call
    """
    # For demo purposes, always return True
    # In real implementation:
    # 1. Call payment gateway API with transaction_id
    # 2. Check payment status
    # 3. Return True if payment is successful
    return True

# Helper function for manual admin verification (if needed)
@router.callback_query(lambda c: c.data == "admin_verify_payment")
async def admin_verify_payment(callback: types.CallbackQuery):
    """Admin verification option (for manual processing)"""
    verify_text = (
        "👑 **Admin Verification**\n\n"
        "Payment requires manual verification.\n"
        "Please contact admin with:\n"
        "• Transaction ID\n"
        "• Payment screenshot\n"
        "• Amount\n\n"
        "Admin will verify and update your balance."
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="deposit")],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="menu")]
        ]
    )
    
    await callback.message.edit_text(verify_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()