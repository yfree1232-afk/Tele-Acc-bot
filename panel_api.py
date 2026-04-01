import requests
import json
import time
from config import PANEL_API_URL, PANEL_API_KEY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PanelAPI:
    """
    Ye class external panel se accounts fetch karta hai
    Jaise: vthpanel.com, accountshop.com, etc.
    """
    
    def __init__(self, db):
        self.db = db
        self.api_url = PANEL_API_URL
        self.api_key = PANEL_API_KEY
    
    def fetch_accounts_from_panel(self, country_code, quantity=10):
        """
        Panel se accounts fetch karo
        Panel API format example:
        {
            "api_key": "xxx",
            "action": "get_accounts",
            "country": "+91",
            "quantity": 10
        }
        """
        if not self.api_url:
            logger.warning("No panel API configured")
            return []
        
        try:
            response = requests.post(
                self.api_url,
                json={
                    "api_key": self.api_key,
                    "action": "get_accounts",
                    "country": country_code,
                    "quantity": quantity
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("accounts", [])
                
                for acc in accounts:
                    self.db.add_account(
                        phone=acc["phone"],
                        country_code=acc["country_code"],
                        otp=acc.get("otp", ""),
                        two_fa=acc.get("2fa"),
                        cost_price=acc.get("price", 0)
                    )
                
                logger.info(f"Fetched {len(accounts)} accounts for {country_code}")
                return accounts
            else:
                logger.error(f"Panel API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch from panel: {e}")
            return []
    
    def check_inventory_levels(self):
        """Check agar inventory kam hai toh auto fetch karo"""
        for country in ["+1", "+91", "+92"]:
            available = self.db.accounts.count_documents({
                "country_code": country,
                "status": "available"
            })
            
            # Agar 5 se kam accounts available hain toh fetch karo
            if available < 5:
                logger.info(f"Low inventory for {country}: {available} available. Fetching more...")
                self.fetch_accounts_from_panel(country, quantity=15)
    
    def get_account_cost(self, country_code):
        """Panel se current cost price get karo"""
        # Ye panel API se price fetch karega
        # Example response: {"price": 5}
        pass
