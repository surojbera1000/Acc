"""Bot Configuration"""
import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Admin User IDs (Telegram user IDs who can access admin panel)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# UPI Configuration
UPI_ID = os.getenv("UPI_ID", "your-upi@bank")
UPI_NAME = os.getenv("UPI_NAME", "Account Store")

# Payment Verification Settings
PAYMENT_CHECK_INTERVAL = 30  # seconds between payment status checks
PAYMENT_TIMEOUT = 600  # 10 minutes timeout for payment verification

# Support Contact
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@Senkaizen")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Currency Symbol
CURRENCY_SYMBOL = "₹"
