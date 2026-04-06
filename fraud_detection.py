import random
from datetime import datetime, timedelta

class FraudDetection:
    def __init__(self, db):
        self.db = db
    
    async def analyze_user(self, user_id):
        """Calculate fraud risk score 0-100"""
        score = 0
        user = await self.db.get_user(user_id)
        
        if not user:
            return 50
        
        # 1. Account age check
        joined_date = user.get("joined_date")
        if joined_date:
            days_old = (datetime.now() - joined_date).days
            if days_old < 1:
                score += 20
            elif days_old < 7:
                score += 10
        
        # 2. Purchase frequency
        purchases = await self.db.get_user_transactions(user_id, 10)
        purchase_count = len([t for t in purchases if t["type"] == "purchase"])
        if purchase_count > 5:
            score -= 10  # Trusted user
        
        # 3. Withdrawal patterns
        withdrawals = [t for t in purchases if t["type"] == "withdrawal"]
        if len(withdrawals) > 3 and sum(w["amount"] for w in withdrawals) > 500:
            score += 15
        
        # 4. Referral check
        if user.get("referred_by"):
            score -= 5
        
        # 5. Random noise for unpredictability
        score += random.randint(-5, 5)
        
        # Clamp between 0-100
        score = max(0, min(100, score))
        
        # Auto-block if high risk
        if score >= 81:
            await self.db.update_fraud_score(user_id, score)
        
        return score
    
    async def analyze_phone(self, phone):
        """Check if phone number has fraud patterns"""
        risk = 0
        
        # Check for suspicious patterns
        if phone.endswith("0000") or phone.endswith("1234"):
            risk += 30
        
        if phone.count("7") > 6 or phone.count("0") > 5:
            risk += 20
        
        return min(100, risk)
