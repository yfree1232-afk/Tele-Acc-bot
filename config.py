import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_account_bot")

# Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Telegram API (for session validation)
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")

# Admin IDs (comma separated)
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

# Required channel (optional)
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "")

# Promo channel (auto-post after purchase)
PROMO_CHANNEL_ID = os.environ.get("PROMO_CHANNEL_ID", "")
PROMO_CHANNEL_LINK = os.environ.get("PROMO_CHANNEL_LINK", "")

# Support
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "@support")
SALES_USERNAME = os.environ.get("SALES_USERNAME", "@sales")

# UPI ID for manual recharge
UPI_ID = os.environ.get("UPI_ID", "yourupi@okhdfcbank")

# Bot username (without @)
BOT_USERNAME = os.environ.get("BOT_USERNAME", "QuickCodesBot")

# Messages
START_MESSAGE = """
Hey, {}! 😊

Welcome To Account Robot - Fastest Telegram Account Seller Bot ❤️

🎉 Enjoy Fast Account buying Experience!

---
Support - {}
Sales - {}
"""

MAIN_MENU_MESSAGE = """
**Main Menu**

💰 Balance: `₹{}`

📊 Total Accounts Sold: `{}`

Choose an option below:
"""
