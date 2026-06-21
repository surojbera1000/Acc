"""
Bot Configuration Settings
Environment variables are loaded from .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/account_bot")

# Payment Configuration
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "razorpay")  # razorpay, paytm, phonepe
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# UPI Configuration
UPI_ID = os.getenv("UPI_ID")  # Your UPI ID for manual payments
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@Senkaizen")

# Bot Settings
DEFAULT_CURRENCY = "INR"
MINIMUM_DEPOSIT = 100  # Minimum deposit amount in INR
MAXIMUM_DEPOSIT = 100000  # Maximum deposit amount in INR

# Delivery Settings
MAX_DELIVERY_RETRIES = 3
DELIVERY_TIMEOUT_SECONDS = 30

# Countries Configuration
SUPPORTED_COUNTRIES = [
    {"code": "IN", "name": "India", "flag": "🇮🇳"},
    {"code": "US", "name": "United States", "flag": "🇺🇸"},
    {"code": "UK", "name": "United Kingdom", "flag": "🇬🇧"},
    {"code": "CA", "name": "Canada", "flag": "🇨🇦"},
    {"code": "AU", "name": "Australia", "flag": "🇦🇺"},
    {"code": "DE", "name": "Germany", "flag": "🇩🇪"},
    {"code": "FR", "name": "France", "flag": "🇫🇷"},
    {"code": "JP", "name": "Japan", "flag": "🇯🇵"},
    {"code": "SG", "name": "Singapore", "flag": "🇸🇬"},
    {"code": "AE", "name": "UAE", "flag": "🇦🇪"},
]

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# Validate required configurations
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

if not ADMIN_IDS:
    print("WARNING: ADMIN_IDS not set. Admin features will be disabled.")