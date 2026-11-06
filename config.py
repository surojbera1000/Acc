"""Bot Configuration"""
import os

from dotenv import load_dotenv

# Load .env before reading any setting (config is imported before bot.main runs)
load_dotenv()

# Telegram Bot Token (set in .env, never hardcode it here)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Admin User IDs (Telegram user IDs who can access admin panel, comma-separated)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7091794658").split(",") if x.strip()]

# UPI Configuration
UPI_ID = os.getenv("UPI_ID", "surojseller@fam")
UPI_NAME = os.getenv("UPI_NAME", "Sandip Bera")

# Payment Verification Settings
PAYMENT_CHECK_INTERVAL = 30  # seconds between payment status checks
PAYMENT_TIMEOUT = 600  # 10 minutes timeout for payment verification

# Support Contact
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@Senkaizen")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Currency Symbol
CURRENCY_SYMBOL = "₹"
