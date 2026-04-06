import asyncio
import logging
import tempfile
import base64
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import *
from database import Database
from proxy_manager import ProxyManager
from fraud_detection import FraudDetection
from admin_panel import admin_panel, user_dashboard

# Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
db = Database()
proxy_manager = ProxyManager()
fraud_detection = FraudDetection(db)

# ============ USER COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check fraud
    fraud_score = await fraud_detection.analyze_user(user_id)
    if fraud_score >= 81:
        await update.message.reply_text("❌ Account blocked due to suspicious activity.")
        return
    
    if not await db.get_user(user_id):
        ref = context.args[0] if context.args else None
        await db.create_user(user_id, update.effective_user.username, ref)
        if ref:
            await db.update_balance(int(ref), 5)
    
    balance = await db.get_balance(user_id)
    await update.message.reply_text(START_MESSAGE.format(balance), parse_mode="Markdown")
    await user_dashboard(update, context, db, user_id)

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    balance = await db.get_balance(query.from_user.id)
    await query.edit_message_text(f"💰 Your balance: *₹{balance}*", parse_mode="Markdown")

async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        user_id = query.from_user.id
    else:
        user_id = update.effective_user.id
    
    # Check fraud
    fraud_score = await fraud_detection.analyze_user(user_id)
    if fraud_score >= 81:
        msg = "❌ Account blocked due to suspicious activity."
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    keyboard = []
    for code, price in PRICES.items():
        country_name = {
            "+1": "🇺🇸 USA", "+91": "🇮🇳 India", 
            "+92": "🇵🇰 Pakistan", "+44": "🇬🇧 UK", "+61": "🇦🇺 Australia"
        }.get(code, code)
        keyboard.append([InlineKeyboardButton(f"{country_name} - ₹{price}", callback_data=f"buy_{code}")])
    
    if query:
        await query.edit_message_text("Select country:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Select country:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    country_code = query.data.split("_")[1]
    price = PRICES.get(country_code, 12)
    
    balance = await db.get_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(f"❌ Insufficient balance!\nNeed: ₹{price}\nYour balance: ₹{balance}\n\nUse /recharge to add funds")
        return
    
    # Get account with proxy matching country
    proxy = proxy_manager.get_proxy_for_country(country_code)
    account = await db.get_available_account(country_code)
    
    if not account:
        await query.edit_message_text(f"❌ No {country_code} accounts available. Please check later.")
        return
    
    # Deduct balance
    await db.update_balance(user_id, -price)
    
    # Add transaction
    await db.add_transaction(user_id, "purchase", price, "completed", f"Bought {country_code} account")
    
    # Send session file
    session_base64 = account.get("session_base64")
    phone = account.get("phone")
    
    delivery_text = f"✅ *Account Purchased!*\n\n📱 Phone: `{phone}`\n💰 Price: ₹{price}\n\n"
    
    if session_base64:
        try:
            session_bytes = base64.b64decode(session_base64)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.session')
            temp_file.write(session_bytes)
            temp_file.close()
            
            with open(temp_file.name, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename=f"{phone}.session",
                    caption=f"✅ Account purchased!\nPhone: {phone}"
                )
            
            os.unlink(temp_file.name)
            delivery_text += "📁 *Session file sent above!*"
        except Exception as e:
            delivery_text += f"⚠️ Error sending file: {str(e)[:50]}"
    
    await db.confirm_sale(account["_id"], user_id, price)
    
    await query.edit_message_text(delivery_text, parse_mode="Markdown")
    await user_dashboard(update, context, db, user_id)

# ============ ADMIN COMMANDS ============
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await admin_panel(update, context, db)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    stats = await db.get_admin_stats()
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Users: {stats['users']}\n"
        f"💰 Total Balance: ₹{stats['total_balance']}\n"
        f"📦 Available: {stats['available_accounts']}\n"
        f"✅ Sold: {stats['sold_accounts']}\n"
        f"💸 Pending Withdrawals: {stats['pending_withdrawals']}",
        parse_mode="Markdown"
    )

# ============ WITHDRAWAL ============
async def withdraw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = await db.get_balance(user_id)
    
    if balance < 50:
        await query.edit_message_text("❌ Minimum withdrawal amount is ₹50")
        return
    
    keyboard = []
    for method, details in WITHDRAWAL_METHODS.items():
        keyboard.append([InlineKeyboardButton(f"{method} (Min: ₹{details['min']})", callback_data=f"withdraw_{method}")])
    
    await query.edit_message_text("Select withdrawal method:", reply_markup=InlineKeyboardMarkup(keyboard))

# ============ MAIN ============
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("admin", admin_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(balance_handler, pattern="balance"))
    app.add_handler(CallbackQueryHandler(buy_handler, pattern="^buy$"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="buy_"))
    app.add_handler(CallbackQueryHandler(withdraw_handler, pattern="withdraw"))
    
    print("🤖 Advanced Bot Started!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
