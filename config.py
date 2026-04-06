import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGO_URI = os.environ.get("MONGO_URI")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "telegram_advanced_bot")

# Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin IDs
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]

# Support Channel
SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "@support")
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")

# Proxy List (comma separated: host:port:user:pass)
PROXY_LIST = os.environ.get("PROXY_LIST", "").split(",")

# API Credentials (multiple, comma separated)
API_IDS = [int(x.strip()) for x in os.environ.get("API_IDS", "").split(",") if x.strip()]
API_HASHES = [x.strip() for x in os.environ.get("API_HASHES", "").split(",") if x.strip()]

# Prices by country
PRICES = {
    "+1": 14,
    "+91": 12,
    "+92": 11,
    "+44": 15,
    "+61": 13,
}

# Withdrawal methods
WITHDRAWAL_METHODS = {
    "TRC20": {"min": 10, "max": 1000, "fee": 0.5},
    "BEP20": {"min": 10, "max": 1000, "fee": 0.5},
    "UPI": {"min": 50, "max": 5000, "fee": 0},
}

# Messages
START_MESSAGE = """
🔥 *Welcome to Advanced Account Bot* 🔥

⚡️ Fastest Telegram account delivery
🛡 0.01% frozen rate
🌍 Geo-matched proxies

💰 Balance: `₹{}`

Use /buy to purchase accounts
Use /withdraw to cash out
"""

ADMIN_PANEL_TEXT = """
👑 *Admin Control Panel*

📊 Users: {}
💰 Total Balance: ₹{}
📦 Available Accounts: {}
✅ Sold Accounts: {}
💸 Pending Withdrawals: {}

Choose an option:
"""
