import logging
import asyncio
import tempfile
import base64
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config import *
from database import Database
from session_manager import SessionManager

# Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
db = Database()
session_manager = SessionManager(db)

# Temporary storage
pending_purchases = {}

# ============ HELPER FUNCTIONS ============
async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        user_id = update.effective_user.id
        chat_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, balance=0):
    stats = db.get_stats()
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("🛒 Buy Account", callback_data="buy")],
        [InlineKeyboardButton("💳 Recharge", callback_data="recharge"),
         InlineKeyboardButton("🎫 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("📜 History", callback_data="history"),
         InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("📊 Stock", callback_data="stock"),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    
    text = MAIN_MENU_MESSAGE.format(balance, stats["total_purchases"])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# ============ USER COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if REQUIRED_CHANNEL and not await is_member(update, context):
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
    
    balance = db.get_balance(user_id)
    await update.message.reply_text(START_MESSAGE.format(user.first_name, SUPPORT_USERNAME, SALES_USERNAME), parse_mode=ParseMode.MARKDOWN)
    await show_main_menu(update, context, balance)

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if await is_member(update, context):
        user_id = query.from_user.id
        if not db.get_user(user_id):
            db.create_user(user_id, query.from_user.username)
        balance = db.get_balance(user_id)
        await query.edit_message_text("✅ Verified! Welcome to the bot.")
        await show_main_menu(update, context, balance)
    else:
        await query.edit_message_text(
            f"❌ You haven't joined {REQUIRED_CHANNEL} yet.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)]])
        )

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    balance = db.get_balance(query.from_user.id)
    await query.edit_message_text(f"💰 **Your Balance:** `₹{balance}`\n\nUse /start to return to menu.", parse_mode=ParseMode.MARKDOWN)

# ============ BUY ACCOUNT ============
async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    inventory = db.get_account_stats()
    
    keyboard = []
    for code in ["+1", "+91", "+92"]:
        price = db.get_price(code)
        available = db.accounts.count_documents({"country_code": code, "status": "available"})
        status_emoji = "✅" if available > 0 else "❌"
        country_name = "🇺🇸 USA" if code == "+1" else "🇮🇳 India" if code == "+91" else "🇵🇰 Pakistan"
        keyboard.append([InlineKeyboardButton(f"{country_name} - ₹{price} {status_emoji} ({available})", callback_data=f"buy_{code}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="menu")])
    
    await query.edit_message_text(
        f"**Buy Telegram Accounts**\n\n📦 Available: {inventory['available']} accounts\n\nSelect country:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def buy_country_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    country_code = query.data.split("_")[1]
    price = db.get_price(country_code)
    user_id = query.from_user.id
    balance = db.get_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(
            f"❌ Insufficient balance!\n\nNeed: ₹{price}\nYour balance: ₹{balance}\n\nUse /recharge to add funds",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Recharge", callback_data="recharge")]])
        )
        return
    
    account = db.get_available_account(country_code)
    
    if not account:
        await query.edit_message_text(
            f"❌ No {country_code} accounts available.\n\nPlease check back later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="buy")]])
        )
        return
    
    db.update_balance(user_id, -price)
    
    # Country details for promo
    country_map = {
        "+1": {"flag": "🇺🇸", "name": "USA"},
        "+91": {"flag": "🇮🇳", "name": "India"},
        "+92": {"flag": "🇵🇰", "name": "Pakistan"},
    }
    country_info = country_map.get(country_code, {"flag": "🌍", "name": country_code})
    
    # Send promo to channel if configured
    if PROMO_CHANNEL_ID:
        promo_text = f"✅ **New Number Purchase Successful**\n\n"
        promo_text += f"➖ Country: {country_info['flag']} {country_info['name']} | ₹{price}\n"
        promo_text += f"➖ Application: Теlegr@м 🎉\n\n"
        promo_text += f"➕ Number: `{account['phone'][:8]}•••••` 📞\n"
        promo_text += f"➕ Server: (1) 🚀\n\n"
        promo_text += f"• {SUPPORT_USERNAME} || @{BOT_USERNAME}"
        
        try:
            await context.bot.send_message(
                chat_id=PROMO_CHANNEL_ID,
                text=promo_text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Promo error: {e}")
    
    # Delivery to user
    delivery_text = f"✅ **Account Purchased!**\n\n"
    delivery_text += f"📱 **Phone:** `{account['phone']}`\n\n"
    
    session_base64 = account.get("session_base64")
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
                    filename=f"{account['phone'].replace('+', '')}.session",
                    caption=f"📱 Session file for {account['phone']}"
                )
            
            os.unlink(temp_file.name)
            delivery_text += f"📁 **Session file sent above!**\n\n"
        except Exception as e:
            delivery_text += f"📁 Session file attached above\n\n"
    
    delivery_text += f"💰 Price: ₹{price}\n"
    delivery_text += f"📧 Support: {SUPPORT_USERNAME}\n\n"
    delivery_text += f"⚠️ Change password immediately after login!"
    
    db.confirm_sale(account["_id"], user_id)
    db.add_purchase(user_id, account["phone"], country_code, price)
    
    await query.edit_message_text(
        delivery_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="menu"),
                                           InlineKeyboardButton("🛒 Buy Another", callback_data="buy")]])
    )

# ============ MANUAL RECHARGE ============
async def recharge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"💳 **Manual Recharge**\n\n"
        f"UPI ID: `{UPI_ID}`\n\n"
        f"**Steps:**\n"
        f"1. Send payment to above UPI ID\n"
        f"2. Send `/confirm <amount> <transaction_id>`\n"
        f"3. Admin will verify and add balance\n\n"
        f"Example: `/confirm 100 TXN123456`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    )

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /confirm <amount> <transaction_id>\nExample: /confirm 100 TXN123456")
        return
    
    try:
        amount = int(args[0])
        txn_id = args[1]
        
        pending_purchases[user_id] = {
            "amount": amount,
            "txn_id": txn_id,
            "status": "pending"
        }
        
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                admin_id,
                f"💰 **Payment Request**\n\n"
                f"User: {update.effective_user.first_name} (ID: {user_id})\n"
                f"Amount: ₹{amount}\n"
                f"Transaction ID: {txn_id}\n\n"
                f"Approve: `/approve {user_id} {amount}`\n"
                f"Reject: `/reject {user_id}`"
            )
        
        await update.message.reply_text(
            f"✅ Payment request submitted!\n\n"
            f"Amount: ₹{amount}\n"
            f"Transaction ID: {txn_id}\n\n"
            f"Admin will verify shortly."
        )
    except:
        await update.message.reply_text("Invalid format. Use: /confirm <amount> <transaction_id>")

# ============ REDEEM ============
async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎫 **Redeem Code**\n\n"
        "Send your redeem code:\n"
        "Example: `QC-ABC123`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    )
    context.user_data['redeem_step'] = True

async def handle_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('redeem_step'):
        code = update.message.text.strip()
        user_id = update.effective_user.id
        result = db.redeem_code(code, user_id)
        
        if result == "invalid":
            await update.message.reply_text("❌ Invalid code!")
        elif result == "used":
            await update.message.reply_text("❌ Code already used!")
        else:
            await update.message.reply_text(f"✅ Code redeemed! ₹{result} added to your balance.")
        
        context.user_data['redeem_step'] = None
        balance = db.get_balance(user_id)
        await show_main_menu(update, context, balance)

# ============ HISTORY ============
async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    purchases = db.get_user_purchases(user_id, 5)
    
    if not purchases:
        text = "📜 **Purchase History**\n\nNo purchases yet."
    else:
        text = "📜 **Recent Purchases:**\n\n"
        for p in purchases:
            date = p.get("created_at", datetime.now()).strftime("%d/%m")
            text += f"• {date}: {p['phone']} - ₹{p['amount']}\n"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]))

# ============ REFER ============
async def refer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot_username = BOT_USERNAME
    
    await query.edit_message_text(
        f"👥 **Referral Program**\n\n"
        f"Invite friends and earn ₹5 when they join!\n\n"
        f"Your referral link:\n"
        f"`https://t.me/{bot_username}?start={user_id}`\n\n"
        f"Share this link with your friends.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    )

# ============ STOCK ============
async def stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    inventory = db.get_account_stats()
    
    text = f"📦 **Account Inventory**\n\n"
    for code in ["+1", "+91", "+92"]:
        price = db.get_price(code)
        available = db.accounts.count_documents({"country_code": code, "status": "available"})
        sold = db.accounts.count_documents({"country_code": code, "status": "sold"})
        country_name = "USA" if code == "+1" else "India" if code == "+91" else "Pakistan"
        text += f"📱 {country_name}: {available} available | {sold} sold | ₹{price} each\n"
    
    text += f"\n📊 **Total:** {inventory['total']} accounts"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]]))

# ============ HELP ============
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"**Help & Support**\n\n"
        f"• /buy - Purchase Telegram account\n"
        f"• /balance - Check your balance\n"
        f"• /recharge - Add balance\n"
        f"• /redeem - Use promo code\n"
        f"• /history - View purchases\n"
        f"• /refer - Get referral link\n\n"
        f"📧 Support: {SUPPORT_USERNAME}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="menu")]])
    )

# ============ ADMIN COMMANDS ============
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
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

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /approve <user_id> <amount>")
        return
    
    user_id = int(args[0])
    amount = int(args[1])
    
    db.update_balance(user_id, amount)
    
    await update.message.reply_text(f"✅ Added ₹{amount} to user {user_id}")
    
    try:
        await context.bot.send_message(user_id, f"✅ Your payment of ₹{amount} has been approved! Balance updated.")
    except:
        pass

async def admin_add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addcode <code> <amount>\nExample: /addcode SALE50 50")
        return
    
    code = args[0]
    amount = int(args[1])
    
    if db.add_redeem_code(code, amount):
        await update.message.reply_text(f"✅ Code {code} added with ₹{amount}")
    else:
        await update.message.reply_text("❌ Code already exists!")

async def admin_list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    accounts = db.get_all_available_accounts()
    
    if not accounts:
        await update.message.reply_text("No available accounts.")
        return
    
    text = f"📦 **Available Accounts ({len(accounts)}):**\n\n"
    for acc in accounts[:20]:
        text += f"• {acc['phone']} ({acc['country_code']})\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_import_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if not update.message.document:
        await update.message.reply_text("Please send a ZIP file containing .session files.")
        return
    
    file = await update.message.document.get_file()
    
    await update.message.reply_text("🔄 Downloading and importing sessions... This may take a while.")
    
    zip_path = f"/tmp/{file.file_id}.zip"
    await file.download_to_drive(zip_path)
    
    results = await session_manager.import_zip_file(zip_path)
    
    os.remove(zip_path)
    
    success_text = f"✅ Imported: {len(results['success'])} accounts\n"
    if results['success']:
        success_text += "\n".join(results['success'][:5])
    failed_text = f"\n\n❌ Failed: {len(results['failed'])} accounts"
    
    await update.message.reply_text(f"{success_text}{failed_text}")

async def admin_show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await update.message.reply_text(
        f"📊 **Current Selling Prices:**\n\n"
        f"🇺🇸 USA: `₹{db.get_price('+1')}`\n"
        f"🇮🇳 India: `₹{db.get_price('+91')}`\n"
        f"🇵🇰 Pakistan: `₹{db.get_price('+92')}`\n\n"
        f"To change price:\n"
        f"`/setprice +91 15` - Change India price to ₹15\n"
        f"`/setprice +1 20` - Change USA price to ₹20\n"
        f"`/setprice +92 13` - Change Pakistan price to ₹13",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/setprice +91 15`\n\n"
            "Examples:\n"
            "/setprice +1 20 - USA ₹20\n"
            "/setprice +91 15 - India ₹15\n"
            "/setprice +92 13 - Pakistan ₹13",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    country_code = args[0]
    try:
        new_price = int(args[1])
    except:
        await update.message.reply_text("❌ Invalid price. Use number only.")
        return
    if country_code not in ["+1", "+91", "+92"]:
        await update.message.reply_text("❌ Invalid country. Use: +1, +91, +92")
        return
    
    if new_price < 1:
        await update.message.reply_text("❌ Price must be at least ₹1")
        return
    
    db.set_price(country_code, new_price)
    
    country_name = "USA" if country_code == "+1" else "India" if country_code == "+91" else "Pakistan"
    await update.message.reply_text(
        f"✅ **Price Updated!**\n\n"
        f"{country_name} ({country_code}) → ₹{new_price}\n\n"
        f"**Current Prices:**\n"
        f"🇺🇸 USA: ₹{db.get_price('+1')}\n"
        f"🇮🇳 India: ₹{db.get_price('+91')}\n"
        f"🇵🇰 Pakistan: ₹{db.get_price('+92')}",
        parse_mode=ParseMode.MARKDOWN
    )

# ============ MENU CALLBACK ============
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    balance = db.get_balance(query.from_user.id)
    await show_main_menu(update, context, balance)

# ============ MAIN ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    
    # Admin commands
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("approve", admin_approve))
    app.add_handler(CommandHandler("addcode", admin_add_code))
    app.add_handler(CommandHandler("listacc", admin_list_accounts))
    app.add_handler(CommandHandler("importzip", admin_import_zip))
    app.add_handler(CommandHandler("prices", admin_show_prices))

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
    app.add_handler(CallbackQueryHandler(menu_callback, pattern="menu"))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_redeem))
    
    print("🤖 Bot started successfully!")
    app.run_polling()

if __name__ == "__main__":
    main()
  
