from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import random
from config import MONGO_URI, DATABASE_NAME

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DATABASE_NAME]
        
        # Collections
        self.users = self.db.users
        self.accounts = self.db.accounts
        self.transactions = self.db.transactions
        self.withdrawals = self.db.withdrawals
        self.sessions = self.db.sessions
        self.proxies = self.db.proxies
        self.api_keys = self.db.api_keys
        self.settings = self.db.settings
    
    # ============ USER METHODS ============
    async def get_user(self, user_id):
        return await self.users.find_one({"user_id": user_id})
    
    async def create_user(self, user_id, username=None, referred_by=None):
        if await self.get_user(user_id):
            return False
        
        await self.users.insert_one({
            "user_id": user_id,
            "username": username,
            "balance": 0,
            "total_purchases": 0,
            "total_spent": 0,
            "is_blocked": False,
            "is_trusted": False,
            "fraud_score": 0,
            "withdrawal_address": {},
            "joined_date": datetime.now(),
            "referred_by": referred_by
        })
        return True
    
    async def update_balance(self, user_id, amount):
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
        return await self.get_user(user_id)
    
    async def get_balance(self, user_id):
        user = await self.get_user(user_id)
        return user["balance"] if user else 0
    
    async def get_all_users(self, limit=100):
        cursor = self.users.find().limit(limit)
        return await cursor.to_list(length=limit)
    
    async def get_user_count(self):
        return await self.users.count_documents({})
    
    async def get_total_balance(self):
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$balance"}}}]
        result = await self.users.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0
    
    # ============ ACCOUNT METHODS ============
    async def add_account(self, phone, country_code, session_base64, cost_price=0):
        await self.accounts.insert_one({
            "phone": phone,
            "country_code": country_code,
            "session_base64": session_base64,
            "cost_price": cost_price,
            "status": "available",
            "health_score": 100,
            "sold_to": None,
            "sold_at": None,
            "added_at": datetime.now()
        })
        return True
    
    async def get_available_account(self, country_code):
        account = await self.accounts.find_one_and_update(
            {
                "country_code": country_code,
                "status": "available",
                "health_score": {"$gt": 70}
            },
            {"$set": {"status": "reserved"}},
            return_document=True
        )
        return account
    
    async def confirm_sale(self, account_id, user_id, price):
        from bson.objectid import ObjectId
        result = await self.accounts.update_one(
            {"_id": ObjectId(account_id)},
            {"$set": {
                "status": "sold",
                "sold_to": user_id,
                "sold_at": datetime.now(),
                "sold_price": price
            }}
        )
        return result.modified_count > 0
    
    async def get_account_stats(self):
        total = await self.accounts.count_documents({})
        available = await self.accounts.count_documents({"status": "available"})
        sold = await self.accounts.count_documents({"status": "sold"})
        return {"total": total, "available": available, "sold": sold}
    
    async def update_account_health(self, account_id, health_score):
        from bson.objectid import ObjectId
        await self.accounts.update_one(
            {"_id": ObjectId(account_id)},
            {"$set": {"health_score": health_score}}
        )
    
    # ============ TRANSACTIONS ============
    async def add_transaction(self, user_id, type, amount, status, details=""):
        await self.transactions.insert_one({
            "user_id": user_id,
            "type": type,
            "amount": amount,
            "status": status,
            "details": details,
            "created_at": datetime.now()
        })
    
    async def get_user_transactions(self, user_id, limit=20):
        cursor = self.transactions.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    # ============ WITHDRAWALS ============
    async def create_withdrawal(self, user_id, amount, method, address):
        withdrawal = {
            "user_id": user_id,
            "amount": amount,
            "method": method,
            "address": address,
            "status": "pending",
            "created_at": datetime.now()
        }
        result = await self.withdrawals.insert_one(withdrawal)
        return result.inserted_id
    
    async def get_pending_withdrawals(self):
        cursor = self.withdrawals.find({"status": "pending"})
        return await cursor.to_list(length=100)
    
    async def approve_withdrawal(self, withdrawal_id):
        from bson.objectid import ObjectId
        await self.withdrawals.update_one(
            {"_id": ObjectId(withdrawal_id)},
            {"$set": {"status": "completed", "approved_at": datetime.now()}}
        )
    
    # ============ FRAUD DETECTION ============
    async def update_fraud_score(self, user_id, score):
        await self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"fraud_score": score}}
        )
        
        user = await self.get_user(user_id)
        if user and user.get("fraud_score", 0) >= 81:
            await self.users.update_one(
                {"user_id": user_id},
                {"$set": {"is_blocked": True}}
            )
            return True
        return False
    
    # ============ STATS ============
    async def get_admin_stats(self):
        user_count = await self.get_user_count()
        total_balance = await self.get_total_balance()
        account_stats = await self.get_account_stats()
        pending_withdrawals = await self.withdrawals.count_documents({"status": "pending"})
        
        return {
            "users": user_count,
            "total_balance": total_balance,
            "available_accounts": account_stats["available"],
            "sold_accounts": account_stats["sold"],
            "pending_withdrawals": pending_withdrawals
        }
