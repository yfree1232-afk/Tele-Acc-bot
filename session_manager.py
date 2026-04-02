import base64
import os
import tempfile
import zipfile
import shutil
import asyncio
import logging
from telethon import TelegramClient
from config import API_ID, API_HASH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, db):
        self.db = db
    
    def encode_session_to_base64(self, session_path):
        with open(session_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    async def import_session_from_file(self, session_path, country_code=None):
        try:
            session_base64 = self.encode_session_to_base64(session_path)
            
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return False, None, "Session not authorized"
            
            me = await client.get_me()
            phone = me.phone
            
            if self.db.get_account_by_phone(phone):
                await client.disconnect()
                return False, None, "Account already exists"
            
            if not country_code:
                if phone.startswith("+1"):
                    country_code = "+1"
                elif phone.startswith("+91"):
                    country_code = "+91"
                elif phone.startswith("+92"):
                    country_code = "+92"
                else:
                    country_code = phone[:3]
            
            self.db.add_account(
                phone=phone,
                country_code=country_code,
                session_base64=session_base64,
                first_name=me.first_name,
                username=me.username
            )
            
            await client.disconnect()
            logger.info(f"✅ Imported: {phone} ({country_code})")
            return True, phone, None
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, None, str(e)
    
    async def import_zip_file(self, zip_path, country_code=None):
        results = {"success": [], "failed": []}
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            session_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.session'):
                        session_files.append(os.path.join(root, file))
            
            for session_file in session_files:
                success, phone, error = await self.import_session_from_file(session_file, country_code)
                if success:
                    results["success"].append(phone)
                else:
                    results["failed"].append({"file": os.path.basename(session_file), "error": error})
                await asyncio.sleep(0.5)
            
        except Exception as e:
            results["failed"].append({"file": zip_path, "error": str(e)})
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return results
