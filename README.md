# Account Marketplace Telegram Bot

A comprehensive Telegram bot for buying and selling premium accounts from various countries with automatic delivery and UPI payment integration.

## 📋 Features

### User Side
- 🛒 **Buy Account** - Browse accounts by country with automatic delivery
- 📋 **Order History** - Track all purchases and transactions
- 💳 **Deposit System** - UPI payments with automatic balance updates
- 💰 **Wallet Management** - Real-time balance tracking
- ❓ **Help & Support** - Direct contact support

### Admin Side
- 👑 **Admin Panel** - Comprehensive management interface
- 📊 **Statistics Dashboard** - Real-time bot analytics
- 👥 **User Management** - View all registered users
- 📦 **Stock Management** - Add, edit, remove accounts
- 📋 **Order Monitoring** - Track all user purchases
- 💳 **Transaction Logs** - Financial transaction tracking

### Safety Features
- 🛡️ **Auto-Refund System** - Automatic refunds for failed deliveries
- 🔒 **Secure Delivery** - Encrypted credential storage
- 📞 **Admin Notifications** - Instant alerts for issues
- 💰 **Balance Protection** - No permanent deduction on failures

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database
- Telegram Bot Token from [@BotFather](https://t.me/botfather)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/surojbera1000/Acc.git
cd Acc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
```

### 3. Configuration

Edit `.env` file:

```env
# Bot Configuration
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=123456789  # Your Telegram ID

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/account_bot

# UPI Payment
UPI_ID=your.upi@id
SUPPORT_USERNAME=@Senkaizen
```

### 4. Database Setup

```bash
# Create database
createdb account_bot

# Initialize tables
python -c "from database import init_db; init_db()"
```

### 5. Run the Bot

```bash
python -m bot.main
```

## 📁 Project Structure

```
account_bot/
├── bot/
│   ├── handlers/
│   │   ├── user/
│   │   │   ├── menu.py      # Main menu and navigation
│   │   │   ├── buy_account.py # Account purchase flow
│   │   │   ├── deposit.py   # UPI payment system
│   │   │   └── wallet.py    # Balance and history
│   │   ├── admin/
│   │   │   └── panel.py     # Admin commands and management
│   │   └── __init__.py      # Handler registration
│   ├── middlewares/
│   │   ├── admin.py         # Admin access control
│   │   └── database.py      # Database session management
│   ├── config.py           # Configuration settings
│   └── main.py            # Bot entry point
├── database/
│   ├── models.py          # SQLAlchemy models
│   └── __init__.py        # Database initialization
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── README.md            # This file
```

## 🔧 Configuration Details

### Bot Setup
1. Create bot with [@BotFather](https://t.me/botfather)
2. Get `BOT_TOKEN`
3. Add your Telegram ID to `ADMIN_IDS`
4. Enable inline mode and payments in BotFather settings

### Database
- Uses PostgreSQL for reliable transaction handling
- SQLAlchemy ORM for database operations
- Automatic table creation on first run

### Payment Integration
- **UPI Manual**: Users send payment to UPI ID, then verify
- **Razorpay** (Optional): Automated payment verification
- **Auto Balance Update**: Instant wallet top-up after verification

## 🛒 Account Types

The bot supports these account categories:
- 📱 Social Media (Facebook, Instagram, Twitter, etc.)
- 🎬 Streaming (Netflix, Prime Video, Disney+, etc.)
- 🎮 Gaming (Steam, Epic Games, PlayStation, etc.)
- 📧 Email (Gmail, Outlook, Yahoo, etc.)
- 🔧 Other (Various premium accounts)

## 🌍 Supported Countries

- 🇮🇳 India
- 🇺🇸 United States
- 🇬🇧 United Kingdom
- 🇨🇦 Canada
- 🇦🇺 Australia
- 🇩🇪 Germany
- 🇫🇷 France
- 🇯🇵 Japan
- 🇸🇬 Singapore
- 🇦🇪 UAE

## 🛡️ Safety System

### Failed Delivery Protection
1. Automatic delivery attempt tracking
2. Multiple retry attempts on failure
3. Auto-refund to user wallet
4. Admin notification for manual intervention

### Security Features
- Encrypted credential storage
- Secure transaction logging
- Admin access control
- Balance validation before purchases

## 📈 Admin Commands

- `/admin` - Admin panel dashboard
- `/stats` - Bot statistics and analytics
- `/users` - List all registered users
- `/add_account` - Add new account to stock
- `/stock` - View current stock status
- `/orders` - Monitor recent purchases
- `/transactions` - View financial transactions

## 🤝 Support

For support and questions:
- Telegram: @Senkaizen
- GitHub Issues: [Create issue](https://github.com/surojbera1000/Acc/issues)

## 📄 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Modern Telegram Bot Framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL Toolkit
- [Razorpay](https://razorpay.com/) - Payment Gateway (Optional)

---

**⚠️ Important Note:** This bot is for educational purposes. Always comply with terms of service of platforms and local laws when dealing with account sales.