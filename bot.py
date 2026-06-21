"""Main bot entry point - Telegram Account Store Bot."""
import logging
import asyncio
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import BOT_TOKEN
from database import Database
from handlers import register_user_handlers, register_admin_handlers, register_payment_handlers

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Initialize bot data after application starts."""
    # Initialize database
    db = Database()
    await db.connect()
    application.bot_data["db"] = db
    logger.info("Database connected successfully.")

    # Set bot commands
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Start the bot / Main menu"),
        BotCommand("buy", "Buy an account"),
        BotCommand("wallet", "Check your wallet balance"),
        BotCommand("deposit", "Deposit funds"),
        BotCommand("history", "View order history"),
        BotCommand("help", "Get help & support"),
        BotCommand("admin", "Admin panel (admins only)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set.")


async def post_shutdown(application: Application):
    """Cleanup on shutdown."""
    db = application.bot_data.get("db")
    if db:
        await db.close()
        logger.info("Database connection closed.")


def main():
    """Start the bot."""
    # Reload env vars
    load_dotenv(override=True)

    from config import BOT_TOKEN as token

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not set! Please set it in .env file.")
        return

    # Build application
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register all handlers.
    # Admin handlers are registered first so the interactive "Add Account"
    # ConversationHandler (group 0) takes priority over the generic text
    # message handler in user_handlers when an admin is mid-flow.
    register_admin_handlers(application)
    register_user_handlers(application)
    register_payment_handlers(application)

    # Start polling
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
