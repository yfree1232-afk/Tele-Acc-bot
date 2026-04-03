import os
import sqlite3
import tempfile
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== CONFIG ====================
BOT_TOKEN = "8380437346:AAHQETsx6ZMIRdn6DzCFUNUz8pOOoCp24YA"
ADMIN_IDS = [8342248523]  # Apna ID daalo

# ==================== DATABASE ====================
conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    session_base64 TEXT,
    status TEXT DEFAULT 'available'
)''')

conn.commit()

def add_account(phone, session_base64):
    c.execute("INSERT INTO accounts (phone, session_base64) VALUES (?, ?)", (phone, session_base64))
    conn.commit()
    print(f"✅ Added: {phone}")

def get_account():
    c.execute("SELECT id, phone, session_base64 FROM accounts WHERE status='available' LIMIT 1")
    row = c.fetchone()
    if row:
        c.execute("UPDATE accounts SET status='sold' WHERE id=?", (row[0],))
        conn.commit()
        return row
    return None

def count_accounts():
    c.execute("SELECT COUNT(*) FROM accounts WHERE status='available'")
    return c.fetchone()[0]

# ==================== BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Bot is working!\n\nSend me a .session file to import.\nUse /buy to purchase account.")

async def buy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇮🇳 India - ₹12", callback_data="buy")],
    ]
    await update.message.reply_text("Select:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    account = get_account()
    
    if not account:
        await query.edit_message_text("❌ No accounts available! Send .session file to admin.")
        return
    
    account_id, phone, session_base64 = account
    
    try:
        session_bytes = base64.b64decode(session_base64)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.session')
        temp_file.write(session_bytes)
        temp_file.close()
        
        with open(temp_file.name, 'rb') as f:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=f,
                filename=f"{phone}.session",
                caption=f"✅ Account delivered!\nPhone: {phone}"
            )
        
        os.unlink(temp_file.name)
        await query.edit_message_text(f"✅ Account delivered! Check your DM.")
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

# ⭐ IMPORTANT: File handler - DIRECT .session file import
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Only admin can upload files.")
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ Send a .session file.")
        return
    
    file_name = update.message.document.file_name
    
    if not file_name.endswith('.session'):
        await update.message.reply_text("❌ Only .session files allowed.")
        return
    
    await update.message.reply_text(f"🔄 Importing {file_name}...")
    
    file = await update.message.document.get_file()
    session_bytes = await file.download_as_bytearray()
    
    # Check file size
    if len(session_bytes) < 5000:
        await update.message.reply_text(f"❌ File too small ({len(session_bytes)} bytes). Corrupted session?")
        return
    
    phone = file_name.replace('.session', '')
    session_base64 = base64.b64encode(session_bytes).decode('utf-8')
    
    add_account(phone, session_base64)
    
    available = count_accounts()
    await update.message.reply_text(f"✅ Imported: {phone}\n\n📦 Total available accounts: {available}")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    available = count_accounts()
    await update.message.reply_text(f"📦 Available accounts: {available}")

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="buy"))
    
    # ⭐ This handles DIRECT .session file upload (NO COMMAND NEEDED)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    print("🤖 Bot started! Send me a .session file directly.")
    app.run_polling()

if __name__ == "__main__":
    main()
