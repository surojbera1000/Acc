from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers
from handlers.payment_handlers import register_payment_handlers
from handlers.admin_panel import register_admin_panel

__all__ = ["register_user_handlers", "register_admin_handlers", "register_payment_handlers",
           "register_admin_panel"]
