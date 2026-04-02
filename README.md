# Telegram Account Bot

Telegram bot for buying and selling accounts.

## Commands

### User Commands
- `/start` - Start the bot
- `/balance` - Check balance
- `/buy` - Buy account
- `/recharge` - Add balance (manual)
- `/confirm <amount> <txn_id>` - Confirm payment
- `/redeem <code>` - Use promo code
- `/history` - View purchase history
- `/refer` - Get referral link

### Admin Commands
- `/stats` - Bot statistics
- `/approve <user_id> <amount>` - Approve payment
- `/addcode <code> <amount>` - Add redeem code
- `/listacc` - List available accounts
- `/importzip` - Import ZIP with .session files

## Environment Variables

| Variable | Description |
|----------|-------------|
| BOT_TOKEN | Telegram bot token |
| MONGO_URI | MongoDB connection string |
| API_ID | Telegram API ID (my.telegram.org) |
| API_HASH | Telegram API hash |
| ADMIN_IDS | Comma-separated admin IDs |
| PRICE_USA | Price for USA accounts |
| PRICE_INDIA | Price for India accounts |
| PRICE_PAK | Price for Pakistan accounts |
| UPI_ID | UPI ID for payments |
| SUPPORT_USERNAME | Support contact |
| SALES_USERNAME | Sales contact |

## Deploy on Heroku

1. Push to GitHub
2. Create new Heroku app
3. Set environment variables
4. Deploy
