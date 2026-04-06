import random
import aiohttp
from aiohttp_socks import ProxyConnector
from config import PROXY_LIST

class ProxyManager:
    def __init__(self):
        self.proxies = [p for p in PROXY_LIST if p]
        self.current_index = 0
    
    def get_next_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def get_random_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_proxy_for_country(self, country_code):
        """Return proxy matching country code"""
        country_map = {
            "+1": "us",
            "+91": "in",
            "+92": "pk",
            "+44": "gb",
            "+61": "au"
        }
        target = country_map.get(country_code, "")
        
        for proxy in self.proxies:
            if target and target in proxy.lower():
                return proxy
        return self.get_random_proxy()
    
    async def create_session(self, proxy_url=None):
        if not proxy_url:
            proxy_url = self.get_random_proxy()
        
        if proxy_url:
            connector = ProxyConnector.from_url(proxy_url)
            return aiohttp.ClientSession(connector=connector)
        return aiohttp.ClientSession()
