"""
Handlers package initialization
"""

from aiogram import Dispatcher

def register_user_handlers(dp: Dispatcher):
    """Register all user handlers"""
    from .user.menu import router as menu_router
    from .user.buy_account import router as buy_account_router
    from .user.deposit import router as deposit_router
    from .user.wallet import router as wallet_router
    
    dp.include_router(menu_router)
    dp.include_router(buy_account_router)
    dp.include_router(deposit_router)
    dp.include_router(wallet_router)

def register_admin_handlers(dp: Dispatcher):
    """Register all admin handlers"""
    from .admin.panel import router as admin_router
    
    dp.include_router(admin_router)