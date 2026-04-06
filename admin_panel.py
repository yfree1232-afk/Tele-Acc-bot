from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_PANEL_TEXT

async def admin_panel(update, context, db):
    stats = await db.get_admin_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
         InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("💰 Balance", callback_data="admin_balance"),
         InlineKeyboardButton("💸 Withdrawals", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("📦 Accounts", callback_data="admin_accounts"),
         InlineKeyboardButton("🌍 Countries", callback_data="admin_countries")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔑 API/Proxy", callback_data="admin_api"),
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")]
    ]
    
    text = ADMIN_PANEL_TEXT.format(
        stats["users"],
        stats["total_balance"],
        stats["available_accounts"],
        stats["sold_accounts"],
        stats["pending_withdrawals"]
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# User dashboard
async def user_dashboard(update, context, db, user_id):
    user = await db.get_user(user_id)
    balance = user["balance"] if user else 0
    
    stats = await db.get_account_stats()
    
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Account", callback_data="buy"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("📜 History", callback_data="history")],
        [InlineKeyboardButton("👥 Refer", callback_data="refer"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ]
    
    text = f"""
🔥 *Your Dashboard*

💰 Balance: `₹{balance}`
📦 Available: {stats['available']} accounts
✅ Purchased: {user.get('total_purchases', 0)}

Use /buy to purchase accounts
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
