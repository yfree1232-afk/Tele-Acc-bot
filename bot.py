import os
import sqlite3
import zipfile
import tempfile
import shutil
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== CONFIG ====================
BOT_TOKEN = "8380437346:AAHQETsx6ZMIRdn6DzCFUNUz8pOOoCp24YA"  # Apna token daalo
ADMIN_IDS = [8365074618]  # Apna Telegram ID daalo (screenshot mein dikh raha hai)
PROMO_CHANNEL_ID = "-1001234567890"  # Apna channel ID daalo (optional)

# ==================== DATABASE ====================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)''')

c.execute('''CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    country TEXT,
    session_base64 TEXT,
    status TEXT DEFAULT 'available'
)''')

c.execute('''CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    file_name TEXT,
    session_base64 TEXT,
    imported_at TEXT
)''')

conn.commit()

# ==================== DATABASE FUNCTIONS ====================
def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

def update_balance(user_id, amount):
    c.execute("INSERT OR REPLACE INTO users (user_id, balance) VALUES (?, COALESCE((SELECT balance FROM users WHERE user_id=?), 0) + ?)", 
              (user_id, user_id, amount))
    conn.commit()

def add_account(phone, country, session_base64):
    c.execute("INSERT INTO accounts (phone, country, session_base64) VALUES (?, ?, ?)", (phone, country, session_base64))
    conn.commit()
    print(f"✅ Account added: {phone}")

def get_account():
    c.execute("SELECT id, phone, session_base64 FROM accounts WHERE status='available' LIMIT 1")
    row = c.fetchone()
    if row:
        c.execute("UPDATE accounts SET status='sold' WHERE id=?", (row[0],))
        conn.commit()
        return row
    return None

def add_session(phone, file_name, session_base64):
    c.execute("INSERT INTO sessions (phone, file_name, session_base64, imported_at) VALUES (?, ?, ?, ?)", 
              (phone, file_name, session_base64, datetime.now().isoformat()))
    conn.commit()
    print(f"✅ Session saved: {phone}")

def get_all_sessions():
    c.execute("SELECT phone, file_name FROM sessions ORDER BY imported_at DESC")
    return c.fetchall()

def count_accounts():
    c.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")
    available = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'")
    sold = c.fetchone()[0]
    return available, sold

# ==================== BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not get_balance(user_id):
        update_balance(user_id, 0)
    
    await update.message.reply_text(
        "🔥 *Welcome to Account Bot!*\n\n"
        "💰 Buy Telegram accounts instantly!\n\n"
        "Commands:\n"
        "/balance - Check balance\n"
        "/buy - Buy account\n"
        "/recharge - Add balance\n"
        "/redeem - Use promo code\n"
        "/history - Your purchases",
        parse_mode="Markdown"
    )

async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    await update.message.reply_text(f"💰 Your balance: *₹{bal}*", parse_mode="Markdown")

async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇺🇸 USA - ₹14", callback_data="buy_+1")],
        [InlineKeyboardButton("🇮🇳 India - ₹12", callback_data="buy_+91")],
        [InlineKeyboardButton("🇵🇰 Pakistan - ₹11", callback_data="buy_+92")],
    ]
    await update.message.reply_text("Select country:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    country = query.data.split("_")[1]
    
    prices = {"+1": 14, "+91": 12, "+92": 11}
    price = prices.get(country, 10)
    
    balance = get_balance(user_id)
    
    if balance < price:
        await query.edit_message_text(f"❌ Insufficient balance!\nNeed: ₹{price}\nYour balance: ₹{balance}")
        return
    
    account = get_account()
    
    if not account:
        await query.edit_message_text("❌ No accounts available! Admin needs to add accounts using /importzip")
        return
    
    account_id, phone, session_base64 = account
    
    update_balance(user_id, -price)
    
    # Send session file to user
    import base64
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
                caption=f"✅ Account purchased!\nPhone: {phone}\nPrice: ₹{price}"
            )
        
        os.unlink(temp_file.name)
    except Exception as e:
        await query.edit_message_text(f"✅ Account Purchased!\n\nPhone: {phone}\nPrice: ₹{price}\n\nSession file: {session_base64[:50]}...")
    
    # Send promo to channel
    if PROMO_CHANNEL_ID:
        promo_text = f"✅ **New Number Purchase Successful**\n\n"
        promo_text += f"➖ Country: {country} | ₹{price}\n"
        promo_text += f"➖ Application: Telegram 🎉\n\n"
        promo_text += f"➕ Number: `{phone[:8]}•••••` 📞\n"
        promo_text += f"➕ Server: (1) 🚀"
        
        try:
            await context.bot.send_message(chat_id=PROMO_CHANNEL_ID, text=promo_text, parse_mode="Markdown")
        except:
            pass
    
    await query.edit_message_text(f"✅ Account delivered!\n\nPhone: {phone}\nPrice: ₹{price}\n\nCheck your DM for session file.")

async def recharge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 *Recharge*\n\n"
        "UPI ID: `yourupi@okhdfcbank`\n\n"
        "After payment, send:\n"
        "`/confirm 100 TXN123456`",
        parse_mode="Markdown"
    )

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /confirm <amount> <transaction_id>")
        return
    
    amount = int(args[0])
    txn_id = args[1]
    
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(
            admin_id,
            f"💰 Payment Request\n\nUser: {user_id}\nAmount: ₹{amount}\nTxn ID: {txn_id}\n\n/approve {user_id} {amount}"
        )
    
    await update.message.reply_text(f"✅ Request sent! Admin will approve soon.")

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /approve <user_id> <amount>")
        return
    
    user_id = int(args[0])
    amount = int(args[1])
    
    update_balance(user_id, amount)
    await update.message.reply_text(f"✅ Added ₹{amount} to user {user_id}")
    
    try:
        await context.bot.send_message(user_id, f"✅ ₹{amount} added to your balance!")
    except:
        pass

async def import_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not update.message.document:
        await update.message.reply_text("Please send a ZIP file containing .session files.")
        return
    
    await update.message.reply_text("🔄 Processing ZIP file... Please wait.")
    
    file = await update.message.document.get_file()
    zip_path = f"/tmp/{file.file_id}.zip"
    await file.download_to_drive(zip_path)
    
    temp_dir = tempfile.mkdtemp()
    imported = []
    failed = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        for root, dirs, files in os.walk(temp_dir):
            for file_name in files:
                if file_name.endswith('.session'):
                    session_path = os.path.join(root, file_name)
                    
                    try:
                        with open(session_path, 'rb') as f:
                            session_base64 = base64.b64encode(f.read()).decode('utf-8')
                        
                        phone = file_name.replace('.session', '')
                        
                        # Detect country
                        if phone.startswith('+1'):
                            country = '+1'
                        elif phone.startswith('+91'):
                            country = '+91'
                        elif phone.startswith('+92'):
                            country = '+92'
                        else:
                            country = '+91'
                        
                        add_account(phone, country, session_base64)
                        add_session(phone, file_name, session_base64)
                        imported.append(phone)
                        print(f"✅ Imported: {phone}")
                        
                    except Exception as e:
                        failed.append(f"{file_name}: {str(e)}")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.remove(zip_path)
        return
    
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.remove(zip_path)
    
    await update.message.reply_text(
        f"✅ Import complete!\n\n"
        f"Imported: {len(imported)} accounts\n"
        f"Failed: {len(failed)}\n\n"
        f"Use /listacc to see all accounts."
    )

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    accounts = get_all_sessions()
    
    if not accounts:
        await update.message.reply_text("No accounts found. Use /importzip first.")
        return
    
    text = f"📦 **Session Files ({len(accounts)}):**\n\n"
    for phone, file_name in accounts[:20]:
        text += f"• {phone} ({file_name})\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    available, sold = count_accounts()
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0] or 0
    
    await update.message.reply_text(
        f"📊 **Bot Stats**\n\n"
        f"Users: {users}\n"
        f"Available accounts: {available}\n"
        f"Sold accounts: {sold}\n"
        f"Total balance: ₹{total_balance}",
        parse_mode="Markdown"
    )

async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("📜 Use /listacc (admin only) to see accounts")

async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎫 Send redeem code. Coming soon.")

# ==================== MAIN ====================
def main():
    import base64  # Add this import
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_handler))
    app.add_handler(CommandHandler("buy", buy_handler))
    app.add_handler(CommandHandler("recharge", recharge_handler))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    app.add_handler(CommandHandler("redeem", redeem_handler))
    app.add_handler(CommandHandler("history", history_handler))
    
    # Admin commands
    app.add_handler(CommandHandler("approve", approve_payment))
    app.add_handler(CommandHandler("importzip", import_zip))
    app.add_handler(CommandHandler("listacc", list_accounts))
    app.add_handler(CommandHandler("stats", stats_handler))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="buy_"))
    
    print("🤖 Bot started! Ready to import sessions.")
    app.run_polling()

if __name__ == "__main__":
    main()
