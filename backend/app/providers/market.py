import os
import httpx

class MarketData:
    def __init__(self):
        self.key=os.getenv('TWELVE_DATA_API_KEY','')
        self.base=os.getenv('TWELVE_DATA_BASE_URL','https://api.twelvedata.com')
    def configured(self): return bool(self.key)
    async def quote(self,symbol):
        if not self.configured(): return None
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'{self.base}/quote',params={'symbol':symbol,'apikey':self.key}); r.raise_for_status(); return r.json()
    async def candles(self,symbol,interval='15min',outputsize=200):
        if not self.configured(): return None
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'{self.base}/time_series',params={'symbol':symbol,'interval':interval,'outputsize':outputsize,'apikey':self.key}); r.raise_for_status(); return r.json()
