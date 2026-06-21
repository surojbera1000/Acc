"""
User Menu Handlers
Main menu and navigation
"""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.config import SUPPORT_USERNAME

router = Router()

@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """Start command handler - shows main menu"""
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Account", callback_data="buy_account")],
            [InlineKeyboardButton(text="📋 Order History", callback_data="order_history")],
            [InlineKeyboardButton(text="💳 Deposit", callback_data="deposit")],
            [InlineKeyboardButton(text="💰 Wallet", callback_data="wallet")],
            [InlineKeyboardButton(text="❓ Help", callback_data="help")],
        ]
    )
    
    welcome_text = (
        "👋 Welcome to Account Marketplace Bot!\n\n"
        "📱 Buy premium accounts from various countries\n"
        "💳 Easy UPI payments\n"
        "⚡ Automatic delivery\n"
        "🛡️ Safe & secure transactions\n\n"
        "Choose an option from the menu below:"
    )
    
    await message.answer(welcome_text, reply_markup=keyboard)

@router.message(Command("menu"))
async def menu_command(message: types.Message, state: FSMContext):
    """Show main menu"""
    await start_command(message, state)

@router.callback_query(lambda c: c.data == "menu")
async def menu_callback(callback: types.CallbackQuery, state: FSMContext):
    """Return to main menu"""
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Account", callback_data="buy_account")],
            [InlineKeyboardButton(text="📋 Order History", callback_data="order_history")],
            [InlineKeyboardButton(text="💳 Deposit", callback_data="deposit")],
            [InlineKeyboardButton(text="💰 Wallet", callback_data="wallet")],
            [InlineKeyboardButton(text="❓ Help", callback_data="help")],
        ]
    )
    
    await callback.message.edit_text(
        "📱 Main Menu\n\n"
        "Choose an option below:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "help")
async def help_callback(callback: types.CallbackQuery):
    """Show help information"""
    help_text = (
        "❓ **Help & Support**\n\n"
        "📋 **How to use:**\n"
        "1. Use /start to see main menu\n"
        "2. Select 'Buy Account' to browse available accounts\n"
        "3. Choose country and account type\n"
        "4. Complete payment via UPI\n"
        "5. Receive account details automatically\n\n"
        
        "💳 **Payment Methods:**\n"
        "• UPI (Automatic payment system)\n"
        "• Instant balance updates\n\n"
        
        "🛡️ **Safety Features:**\n"
        "• Auto-refund on failed delivery\n"
        "• Secure transaction system\n"
        "• Live stock updates\n\n"
        
        "📞 **Contact Support:**\n"
        f"{SUPPORT_USERNAME}\n\n"
        
        "⚠️ **Important:**\n"
        "• Never share your credentials with anyone\n"
        "• Report any issues immediately\n"
        "• Check account details carefully after purchase"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu")]
        ]
    )
    
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()