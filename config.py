"""Bot Configuration.

All sensitive values are read from environment variables (see .env.example).
Never hard-code real tokens, UPI IDs, or admin IDs here — they belong in .env,
which must stay out of version control.
"""
import os

from dotenv import load_dotenv

# Load .env here: bot.py imports config before its own load_dotenv() call,
# so without this every value below would ignore the .env file.
load_dotenv()

# Telegram Bot Token (get from @BotFather). Required — set it in .env.
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin User IDs (Telegram user IDs who can access admin panel), comma-separated.
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

# UPI Configuration
UPI_ID = os.getenv("UPI_ID", "")
UPI_NAME = os.getenv("UPI_NAME", "Account Store")

# Payment Verification Settings
PAYMENT_CHECK_INTERVAL = 30  # seconds between payment status checks
PAYMENT_TIMEOUT = 600  # 10 minutes timeout for payment verification

# Telegram API credentials for the bot to log into accounts (Add Account wizard).
# Get them at https://my.telegram.org -> API development tools.
API_ID = os.getenv("API_ID", "")
API_HASH = os.getenv("API_HASH", "")

# Support Contact
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@M4rolex")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Currency Symbol
CURRENCY_SYMBOL = "₹"
