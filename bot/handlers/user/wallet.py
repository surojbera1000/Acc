"""
Wallet Handlers
Balance display and transaction history
"""

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database.models import User, Transaction, TransactionType
from database import get_db

router = Router()

@router.callback_query(lambda c: c.data == "wallet")
async def show_wallet(callback: types.CallbackQuery, db: Session):
    """Show wallet balance and options"""
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
    
    # Get recent transactions (last 5)
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    # Prepare wallet info
    wallet_text = (
        "💰 **Your Wallet**\n\n"
        f"**Current Balance:** ₹{user.balance}\n"
        f"**Member Since:** {user.created_at.strftime('%d %b %Y')}\n\n"
    )
    
    # Add recent transactions if any
    if recent_transactions:
        wallet_text += "📋 **Recent Transactions:**\n"
        
        for i, tx in enumerate(recent_transactions, 1):
            # Format transaction type emoji
            type_emoji = {
                TransactionType.DEPOSIT.value: "⬆️",
                TransactionType.WITHDRAWAL.value: "⬇️",
                TransactionType.PURCHASE.value: "🛒",
                TransactionType.REFUND.value: "↩️"
            }.get(tx.transaction_type.value, "💳")
            
            # Format amount with sign
            amount_sign = "+" if tx.transaction_type == TransactionType.DEPOSIT or tx.transaction_type == TransactionType.REFUND else "-"
            amount_formatted = f"{amount_sign}₹{tx.amount}"
            
            # Truncate description if too long
            description = tx.description if len(tx.description or '') <= 30 else tx.description[:27] + "..."
            
            wallet_text += f"{i}. {type_emoji} {description} {amount_formatted}\n"
        
        wallet_text += "\n"
    else:
        wallet_text += "📭 **No transactions yet**\n\n"
    
    wallet_text += "💡 **Quick Actions:**\n"
    wallet_text += "• Deposit funds to buy accounts\n"
    wallet_text += "• Check order history for purchases\n"
    wallet_text += "• Contact support for any issues"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Deposit", callback_data="deposit"),
                InlineKeyboardButton(text="📋 History", callback_data="order_history")
            ],
            [
                InlineKeyboardButton(text="🛒 Buy Account", callback_data="buy_account"),
                InlineKeyboardButton(text="📊 Full History", callback_data="full_history")
            ],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="menu")]
        ]
    )
    
    await callback.message.edit_text(wallet_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "full_history")
async def show_full_history(callback: types.CallbackQuery, db: Session):
    """Show full transaction history"""
    # Get user
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Get all transactions
    all_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(Transaction.created_at.desc()).all()
    
    if not all_transactions:
        history_text = "📭 **No Transaction History**\n\nYou haven't made any transactions yet."
    else:
        history_text = "📊 **Transaction History**\n\n"
        
        # Group by date
        transactions_by_date = {}
        for tx in all_transactions:
            date_str = tx.created_at.strftime("%d %b %Y")
            if date_str not in transactions_by_date:
                transactions_by_date[date_str] = []
            transactions_by_date[date_str].append(tx)
        
        # Format history
        for date_str, transactions in transactions_by_date.items():
            history_text += f"📅 **{date_str}**\n"
            
            for tx in transactions:
                # Format transaction type emoji and text
                type_info = {
                    TransactionType.DEPOSIT.value: ("⬆️", "Deposit"),
                    TransactionType.WITHDRAWAL.value: ("⬇️", "Withdrawal"),
                    TransactionType.PURCHASE.value: ("🛒", "Purchase"),
                    TransactionType.REFUND.value: ("↩️", "Refund")
                }.get(tx.transaction_type.value, ("💳", "Transaction"))
                
                type_emoji, type_text = type_info
                
                # Format amount with sign
                amount_sign = "+" if tx.transaction_type == TransactionType.DEPOSIT or tx.transaction_type == TransactionType.REFUND else "-"
                amount_formatted = f"{amount_sign}₹{tx.amount}"
                
                # Time
                time_str = tx.created_at.strftime("%H:%M")
                
                # Status
                status = "✅" if tx.is_successful else "❌"
                
                history_text += f"  {type_emoji} {type_text} {amount_formatted} at {time_str} {status}\n"
            
            history_text += "\n"
        
        # Summary
        total_deposits = sum(tx.amount for tx in all_transactions 
                           if tx.transaction_type == TransactionType.DEPOSIT and tx.is_successful)
        total_purchases = sum(tx.amount for tx in all_transactions 
                            if tx.transaction_type == TransactionType.PURCHASE and tx.is_successful)
        
        history_text += f"📈 **Summary:**\n"
        history_text += f"Total Deposits: ₹{total_deposits}\n"
        history_text += f"Total Purchases: ₹{total_purchases}\n"
        history_text += f"Current Balance: ₹{user.balance}\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Wallet", callback_data="wallet")],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="menu")]
        ]
    )
    
    await callback.message.edit_text(history_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "order_history")
async def show_order_history(callback: types.CallbackQuery, db: Session):
    """Show order/purchase history"""
    # Get user
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    # Get purchase transactions
    purchase_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.transaction_type == TransactionType.PURCHASE
    ).order_by(Transaction.created_at.desc()).all()
    
    if not purchase_transactions:
        order_text = "🛍️ **No Purchase History**\n\nYou haven't purchased any accounts yet."
    else:
        order_text = "🛍️ **Purchase History**\n\n"
        
        for i, tx in enumerate(purchase_transactions, 1):
            # Parse metadata for account info (in real implementation)
            # For now, use description
            time_str = tx.created_at.strftime("%d %b %Y %H:%M")
            status = "✅" if tx.is_successful else "❌"
            
            order_text += f"{i}. {status} ₹{tx.amount} - {tx.description or 'Account Purchase'} at {time_str}\n"
        
        order_text += f"\n📊 **Total Purchases:** {len(purchase_transactions)} accounts\n"
        order_text += f"💰 **Total Spent:** ₹{sum(tx.amount for tx in purchase_transactions if tx.is_successful)}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy More", callback_data="buy_account")],
            [
                InlineKeyboardButton(text="🔙 Wallet", callback_data="wallet"),
                InlineKeyboardButton(text="🏠 Menu", callback_data="menu")
            ]
        ]
    )
    
    await callback.message.edit_text(order_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(lambda c: c.data == "refresh_balance")
async def refresh_balance(callback: types.CallbackQuery, db: Session):
    """Refresh and show updated balance"""
    # Get user
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if not user:
        await callback.answer("User not found", show_alert=True)
        return
    
    await show_wallet(callback, db)
    await callback.answer("Balance refreshed")