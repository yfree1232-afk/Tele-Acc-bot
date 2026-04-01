import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import *
from database import Database
from panel_api import PanelAPI

# Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
db = Database()
panel = PanelAPI(db)

# Store temporary data for purchase flow
user_pending_purchase = {}

async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        chat_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if not await is_member(update, context):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ Verify", callback_data="verify")]]
        await update.message.reply_text(
            f"❌ You must subscribe to the official channel to use the bot.\n\n📧 Channel - {REQUIRED_CHANNEL}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if not db.get_user(user_id):
        ref = context.args[0] if context.args else None
        db.create_user(user_id, user.username, ref)
        if ref:
            db.update_balance(int(ref), 5)
    
    stats = db.get_stats()
    balance = db.get_balance(user_id)
    
    await update.message.reply_text(START_MESSAGE.format(user.first_name), parse_mode=ParseMode.MARKDOWN)
    await show_main_menu(update, context, balance, stats["total_purchases"])

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, balance=0, total_sold=0):
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("🛒 Buy Account", callback_data="buy")],
        [InlineKeyboardButton("💳 Recharge", callback_data="recharge"),
         InlineKeyboardButton("🎫 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("📜 History", callback_data="history"),
         InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("📊 Stock Status", callback_data="stock"),
         InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    
    text = MAIN_MENU_MESSAGE.format(balance, total_sold)
    
    if isinstance(update, Update) and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# ============ BUY ACCOUNT WITH AUTO-DELIVERY ============
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Check inventory before showing options
    inventory = db.get_account_stats()
    
    keyboard = []
    for code, price in SELLING_PRICES.items():
        available = db.accounts.count_documents({"country_code": code, "status": "available"})
        status_emoji = "✅" if available > 0 else "❌"
        keyboard.append([InlineKeyboardButton(f"{code} - ₹{price} {status_emoji} ({available} left)", callback_data=f"buy_{code}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    
    await query.edit_message_text(
        f"**Buy SpamFree Telegram Accounts**\n\n📦 **Available Stock:**\n"
        f"USA: {inventory['available']} accounts\n\n"
        f"Select country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def buy_country_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    country_code = query.data.split("_")[1]
    price = SELLING_PRICES.get(country_code, 0)
    user_id = query.from_user.id
    balance = db.get_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nNeed: ₹{price}\nYour balance: ₹{balance}\n\nPlease recharge first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Recharge", callback_data="recharge"),
                                               InlineKeyboardButton("🔙 Back", callback_data="buy")]])
        )
        return
    
    # Reserve an account from inventory
    account = db.get_available_account(country_code)
    
    if not account:
        # Auto-fetch from panel if available
        await query.edit_message_text("🔄 No accounts available. Trying to fetch from panel...")
        panel.fetch_accounts_from_panel(country_code, quantity=5)
        
        # Try again
        account = db.get_available_account(country_code)
        
        if not account:
            await query.edit_message_text(
                f"❌ Sorry, no {country_code} accounts available right now.\n\n"
                f"Please check back in a few minutes.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="buy")]])
            )
            return
    
    # Deduct balance
    db.update_balance(user_id, -price)
    
    # Store account details for delivery
    user_pending_purchase[user_id] = {
        "account_id": account["_id"],
        "phone": account["phone"],
        "otp": account["otp"],
        "two_fa": account.get("two_fa"),
        "country_code": country_code,
        "price": price
    }
    
    # Format account details for delivery
    account_text = f"✅ **Account Purchased!**\n\n"
    account_text += f"📱 **Phone:** `{account['phone']}`\n"
    account_text += f"🔑 **OTP:** `{account['otp']}`\n"
    if account.get("two_fa"):
        account_text += f"🔐 **2FA Password:** `{account['two_fa']}`\n"
    account_text += f"\n🌍 **Country:** {country_code}\n"
    account_text += f"💰 **Price:** ₹{price}\n\n"
    account_text += f"⚠️ **Instructions:**\n"
    account_text += f"1. Login using phone + OTP\n"
    account_text += f"2. Change password immediately\n"
    account_text += f"3. Enable 2FA for security\n\n"
    account_text += f"📧 Support: {SUPPORT_USERNAME}"
    
    # Confirm sale in database
    db.confirm_account_sold(account["_id"], user_id)
    db.add_purchase(user_id, account["phone"], country_code, price)
    
    # Check inventory levels after sale
    panel.check_inventory_levels()
    
    await query.edit_message_text(
        account_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu"),
                                           InlineKeyboardButton("🛒 Buy Another", callback_data="buy")]])
    )

# ============ STOCK STATUS (Admin & Users) ============
async def stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    inventory = db.get_account_stats()
    
    text = f"📦 **Account Inventory Status**\n\n"
    for code, price in SELLING_PRICES.items():
        available = db.accounts.count_documents({"country_code": code, "status": "available"})
        sold = db.accounts.count_documents({"country_code": code, "status": "sold"})
        text += f"{code}: {available} available | {sold} sold\n"
    
    text += f"\n📊 **Total:** {inventory['total']} accounts\n"
    text += f"🟢 **Available:** {inventory['available']}\n"
    text += f"🔴 **Sold:** {inventory['sold']}\n"
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    )

# ============ ADMIN: ADD ACCOUNTS MANUALLY ============
async def admin_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /addaccount <country_code> <phone> <otp> [2fa]\n\n"
            "Example: /addaccount +91 9876543210 12345"
        )
        return
    
    country_code = args[0]
    phone = args[1]
    otp = args[2]
    two_fa = args[3] if len(args) > 3 else None
    
    db.add_account(phone, country_code, otp, two_fa)
    await update.message.reply_text(f"✅ Account added: {phone} ({country_code})")

async def admin_bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bulk add accounts from file"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    # Expected format: country_code,phone,otp,2fa
    # Can be sent as document
    pass

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    stats = db.get_stats()
    await update.message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Users: {stats['total_users']}\n"
        f"💰 Total Balance: ₹{stats['total_balance']}\n"
        f"🛒 Purchases: {stats['total_purchases']}\n"
        f"💵 Revenue: ₹{stats['total_revenue']}\n\n"
        f"📦 Inventory: {stats['inventory']['available']}/{stats['inventory']['total']} available",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_refresh_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual inventory refresh from panel"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    await update.message.reply_text("🔄 Refreshing inventory from panel...")
    
    for country in ["+1", "+91", "+92"]:
        panel.fetch_accounts_from_panel(country, quantity=20)
    
    await update.message.reply_text("✅ Inventory refreshed!")

# ============ OTHER HANDLERS (Balance, Recharge, Redeem, History, Refer) ============
# [Previous handlers with similar structure, updated for MongoDB]

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("addaccount", admin_add_account))
    app.add_handler(CommandHandler("refresh", admin_refresh_inventory))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="verify"))
    app.add_handler(CallbackQueryHandler(balance_handler, pattern="balance"))
    app.add_handler(CallbackQueryHandler(buy_handler, pattern="buy$"))
    app.add_handler(CallbackQueryHandler(buy_country_handler, pattern="buy_"))
    app.add_handler(CallbackQueryHandler(recharge_handler, pattern="recharge"))
    app.add_handler(CallbackQueryHandler(redeem_handler, pattern="redeem"))
    app.add_handler(CallbackQueryHandler(history_handler, pattern="history"))
    app.add_handler(CallbackQueryHandler(refer_handler, pattern="refer"))
    app.add_handler(CallbackQueryHandler(stock_handler, pattern="stock"))
    app.add_handler(CallbackQueryHandler(help_handler, pattern="help"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_main_menu(u,c,db.get_balance(u.effective_user.id), db.get_stats()["total_purchases"]), pattern="menu"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_redeem))
    
    print("Bot started with MongoDB...")
    app.run_polling()

if __name__ == "__main__":
    main()
