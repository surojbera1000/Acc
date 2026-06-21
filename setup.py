#!/usr/bin/env python3
"""
Setup script for Account Marketplace Bot
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run shell command with error handling"""
    print(f"\n🔧 {description}...")
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def setup_environment():
    """Setup Python virtual environment"""
    print("\n" + "="*50)
    print("🚀 Account Marketplace Bot Setup")
    print("="*50)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ is required")
        return False
    
    # Create virtual environment
    if not Path("venv").exists():
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    
    # Install dependencies
    pip_cmd = "venv/bin/pip" if sys.platform != "win32" else "venv\\Scripts\\pip"
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies"):
        return False
    
    # Copy environment file
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        env_example.copy(env_file)
        print("\n📄 Created .env file from .env.example")
        print("⚠️ Please edit .env file with your configuration:")
        print("   - BOT_TOKEN from @BotFather")
        print("   - ADMIN_IDS (your Telegram ID)")
        print("   - DATABASE_URL (PostgreSQL connection)")
        print("   - UPI_ID (for payments)")
    
    # Initialize database
    print("\n📦 Database setup:")
    print("1. Make sure PostgreSQL is running")
    print("2. Create database: createdb account_bot")
    print("3. Update DATABASE_URL in .env")
    print("4. Run: python -c \"from database import init_db; init_db()\"")
    
    return True

def show_next_steps():
    """Display next steps after setup"""
    print("\n" + "="*50)
    print("🎉 Setup Complete! Next Steps:")
    print("="*50)
    print("\n1. 📝 Edit .env file with your configuration")
    print("2. 🗄️ Setup PostgreSQL database")
    print("3. 🏃 Run the bot:")
    print("   - Using Python: python -m bot.main")
    print("   - Using Docker: docker-compose up")
    print("\n4. 🤖 Test the bot:")
    print("   - Start: /start")
    print("   - Admin: /admin (if added to ADMIN_IDS)")
    print("\n5. 📚 Read README.md for detailed instructions")
    print("\n💡 Quick start with Docker:")
    print("   cp .env.example .env")
    print("   docker-compose up")

if __name__ == "__main__":
    if setup_environment():
        show_next_steps()
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)