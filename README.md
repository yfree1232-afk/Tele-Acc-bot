# Telegram Account Bot

Complete Telegram bot for buying and selling accounts with auto-delivery.

## Features

- ✅ Buy Telegram accounts (USA, India, Pakistan)
- ✅ Auto-delivery of session files
- ✅ Manual recharge with UPI
- ✅ Redeem codes system
- ✅ Referral program
- ✅ Auto-promo channel posts
- ✅ Dynamic price management (admin commands)
- ✅ MongoDB database
- ✅ Heroku/Render ready

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/balance` | Check balance |
| `/buy` | Buy account |
| `/recharge` | Add balance |
| `/confirm <amount> <txn_id>` | Confirm payment |
| `/redeem <code>` | Use promo code |
| `/history` | View purchases |
| `/refer` | Get referral link |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/stats` | Bot statistics |
| `/approve <user_id> <amount>` | Approve payment |
| `/addcode <code> <amount>` | Add redeem code |
| `/listacc` | List available accounts |
| `/importzip` | Import session files |
| `/prices` | Show current prices |
| `/setprice +91 15` | Change price |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| BOT_TOKEN | ✅ | Telegram bot token |
| MONGO_URI | ✅ | MongoDB connection string |
| API_ID | ✅ | Telegram API ID |
| API_HASH | ✅ | Telegram API hash |
| ADMIN_IDS | ✅ | Comma-separated admin IDs |
| UPI_ID | ✅ | UPI ID for payments |
| PROMO_CHANNEL_ID | ❌ | Channel ID for auto-posts |
| BOT_USERNAME | ✅ | Bot username (without @) |
| SUPPORT_USERNAME | ❌ | Support contact |
| SALES_USERNAME | ❌ | Sales contact |
| REQUIRED_CHANNEL | ❌ | Channel to join |
| CHANNEL_LINK | ❌ | Channel invite link |

## Deploy on Heroku

1. Push this repository to GitHub
2. Create new Heroku app
3. Connect GitHub repository
4. Add environment variables
5. Deploy branch

## Deploy on Render

1. Push to GitHub
2. Create new Web Service
3. Connect repository
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
6. Add environment variables
7. Deploy

## Import Session Files

1. Create ZIP file with all `.session` files
2. Send to bot: `/importzip`
3. Attach the ZIP file
4. Bot auto-imports all accounts

## Auto Promo Channel

When user buys account, bot automatically posts to promo channel:
