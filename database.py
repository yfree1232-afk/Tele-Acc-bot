from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime
from config import MONGO_URI, DATABASE_NAME

class Database:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DATABASE_NAME]
        
        # Collections
        self.users = self.db.users
        self.accounts = self.db.accounts
        self.transactions = self.db.transactions
        self.redeem_codes = self.db.redeem_codes
        self.settings = self.db.settings
        
        # Indexes
        self.users.create_index("user_id", unique=True)
        self.accounts.create_index("phone", unique=True)
        self.accounts.create_index("status")
        self.redeem_codes.create_index("code", unique=True)
    
    # ============ USER METHODS ============
    def get_user(self, user_id):
        return self.users.find_one({"user_id": user_id})
    
    def create_user(self, user_id, username=None, referred_by=None):
        try:
            self.users.insert_one({
                "user_id": user_id,
                "username": username,
                "balance": 0,
                "total_purchases": 0,
                "total_spent": 0,
                "joined_date": datetime.now(),
                "referred_by": referred_by
            })
            return True
        except DuplicateKeyError:
            return False
    
    def update_balance(self, user_id, amount):
        self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
    
    def get_balance(self, user_id):
        user = self.users.find_one({"user_id": user_id})
        return user["balance"] if user else 0
    
    # ============ PRICE METHODS ============
    def get_price(self, country_code):
        setting = self.settings.find_one({"key": f"price_{country_code}"})
        if setting:
            return setting["value"]
        defaults = {"+1": 14, "+91": 12, "+92": 11}
        return defaults.get(country_code, 10)
    
    def set_price(self, country_code, price):
        self.settings.update_one(
            {"key": f"price_{country_code}"},
            {"$set": {"value": price, "updated_at": datetime.now()}},
            upsert=True
        )
        return True
    
    def get_all_prices(self):
        prices = {}
        for code in ["+1", "+91", "+92"]:
            prices[code] = self.get_price(code)
        return prices
    
    # ============ ACCOUNT METHODS ============
    def add_account(self, phone, country_code, session_base64, first_name=None, username=None):
        try:
            self.accounts.insert_one({
                "phone": phone,
                "country_code": country_code,
                "session_base64": session_base64,
                "first_name": first_name,
                "username": username,
                "status": "available",
                "sold_to": None,
                "sold_at": None,
                "added_at": datetime.now()
            })
            return True
        except DuplicateKeyError:
            return False
    
    def get_account_by_phone(self, phone):
        return self.accounts.find_one({"phone": phone})
    
    def get_available_account(self, country_code):
        account = self.accounts.find_one_and_update(
            {
                "country_code": country_code,
                "status": "available"
            },
            {
                "$set": {"status": "reserved"}
            },
            return_document=True
        )
        return account
    
    def confirm_sale(self, account_id, user_id):
        from bson.objectid import ObjectId
        self.accounts.update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "status": "sold",
                    "sold_to": user_id,
                    "sold_at": datetime.now()
                }
            }
        )
    
    def release_account(self, account_id):
        from bson.objectid import ObjectId
        self.accounts.update_one(
            {"_id": ObjectId(account_id)},
            {"$set": {"status": "available"}}
        )
    
    def get_account_stats(self):
        total = self.accounts.count_documents({})
        available = self.accounts.count_documents({"status": "available"})
        sold = self.accounts.count_documents({"status": "sold"})
        return {"total": total, "available": available, "sold": sold}
    
    def get_all_available_accounts(self):
        return list(self.accounts.find({"status": "available"}))
    
    # ============ PURCHASE METHODS ============
    def add_purchase(self, user_id, phone, country_code, amount):
        self.transactions.insert_one({
            "user_id": user_id,
            "type": "purchase",
            "amount": amount,
            "phone": phone,
            "country_code": country_code,
            "status": "completed",
            "created_at": datetime.now()
        })
        
        self.users.update_one(
            {"user_id": user_id},
            {"$inc": {"total_purchases": 1, "total_spent": amount}}
        )
    
    def get_user_purchases(self, user_id, limit=10):
        return list(self.transactions.find(
            {"user_id": user_id, "type": "purchase"}
        ).sort("created_at", -1).limit(limit))
    
    # ============ REDEEM CODES ============
    def add_redeem_code(self, code, amount):
        try:
            self.redeem_codes.insert_one({
                "code": code,
                "amount": amount,
                "used_by": None,
                "used_at": None,
                "created_at": datetime.now()
            })
            return True
        except DuplicateKeyError:
            return False
    
    def redeem_code(self, code, user_id):
        code_data = self.redeem_codes.find_one({"code": code})
        
        if not code_data:
            return "invalid"
        if code_data.get("used_by"):
            return "used"
        
        amount = code_data["amount"]
        
        self.redeem_codes.update_one(
            {"code": code},
            {"$set": {"used_by": user_id, "used_at": datetime.now()}}
        )
        
        self.update_balance(user_id, amount)
        
        self.transactions.insert_one({
            "user_id": user_id,
            "type": "redeem",
            "amount": amount,
            "code": code,
            "status": "completed",
            "created_at": datetime.now()
        })
        
        return amount
    
    # ============ STATS ============
    def get_stats(self):
        total_users = self.users.count_documents({})
        total_balance = sum([u.get("balance", 0) for u in self.users.find()])
        total_purchases = self.transactions.count_documents({"type": "purchase"})
        total_revenue = sum([t.get("amount", 0) for t in self.transactions.find({"type": "purchase"})])
        inventory = self.get_account_stats()
        
        return {
            "total_users": total_users,
            "total_balance": total_balance,
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "inventory": inventory
        }
