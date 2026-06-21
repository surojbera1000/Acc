"""Bot Configuration"""
import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "7984346452:AAEC4BrCFZ97VoP5pHVzYkpGZtE2hUMUqI4")

# Admin User IDs (Telegram user IDs who can access admin panel)
ADMIN_IDS = [int(x) for x in os.getenv("7091794658", "7091794658").split(",") if x.strip()]

# UPI Configuration
UPI_ID = os.getenv("surojseller@fam", "surojseller@fam")
UPI_NAME = os.getenv("SANDIP BERA", "Sandip Bera")

# Payment Verification Settings
PAYMENT_CHECK_INTERVAL = 30  # seconds between payment status checks
PAYMENT_TIMEOUT = 600  # 10 minutes timeout for payment verification

# Support Contact
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@Senkaizen")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Currency Symbol
CURRENCY_SYMBOL = "₹"
