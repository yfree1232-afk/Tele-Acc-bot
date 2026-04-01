import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net/")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_account_bot")

# Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin IDs
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "123456789").split(",")]

# Required channel
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@vthnet")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/vthnet")

# Support
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "@vthnet")
SALES_USERNAME = os.environ.get("SALES_USERNAME", "@vthproofs")

# Selling prices (jo user pay karega)
SELLING_PRICES = {
    "+1": int(os.environ.get("PRICE_USA", "14")),     # USA
    "+91": int(os.environ.get("PRICE_INDIA", "12")),  # India
    "+92": int(os.environ.get("PRICE_PAK", "11")),    # Pakistan
}

# Purchase cost (kitne me account liya)
PURCHASE_COST = {
    "+1": int(os.environ.get("COST_USA", "5")),
    "+91": int(os.environ.get("COST_INDIA", "3")),
    "+92": int(os.environ.get("COST_PAK", "3")),
}

# Payment UPI
UPI_ID = os.environ.get("UPI_ID", "yourupi@okhdfcbank")

# External Panel API (jahan se accounts milte hain)
PANEL_API_URL = os.environ.get("PANEL_API_URL", "")
PANEL_API_KEY = os.environ.get("PANEL_API_KEY", "")

# Messages
START_MESSAGE = """
Hey, {}! 😊

Welcome To Account Robot - Fastest Telegram Account Seller Bot ❤️

🎉 Enjoy Fast Account buying Experience!

---
Support - @vthnet
Sales - @vthproofs
"""

MAIN_MENU_MESSAGE = """
**Main Menu**

💰 Balance: `₹{}`

📊 Total Accounts Sold: `{}`

Choose an option below:
"""
