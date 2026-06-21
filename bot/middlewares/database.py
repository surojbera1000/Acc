"""
Database Middleware
Provides database session to handlers
"""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from database import Session, get_db

class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Add db to data for handlers
            data["db"] = db
            result = await handler(event, data)
            return result
        finally:
            # Close session
            try:
                next(db_gen, None)
            except StopIteration:
                pass