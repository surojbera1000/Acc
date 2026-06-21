"""
Admin Middleware
Checks if user is admin before processing admin commands
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from bot.config import ADMIN_IDS

class AdminMiddleware(BaseMiddleware):
    """Middleware to check admin access"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Check if this is an admin-related action
        is_admin_action = False
        
        if isinstance(event, Message):
            # Check commands
            if event.text and event.text.startswith('/'):
                cmd = event.text.split()[0].lower()
                is_admin_action = cmd in ['/admin', '/stats', '/users', '/add_account', 
                                        '/stock', '/orders', '/transactions']
        
        elif isinstance(event, CallbackQuery):
            # Check callback data
            if event.data and event.data.startswith('admin_'):
                is_admin_action = True
        
        # If it's not an admin action, proceed normally
        if not is_admin_action:
            return await handler(event, data)
        
        # Check if user is admin
        user_id = event.from_user.id
        
        if user_id not in ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer("⛔ Access denied. Admin only.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Access denied", show_alert=True)
            return
        
        # User is admin, proceed
        return await handler(event, data)