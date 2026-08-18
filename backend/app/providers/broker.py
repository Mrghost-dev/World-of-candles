import os, httpx
class Oanda:
    def __init__(self):
        self.base=os.getenv('OANDA_BASE_URL','https://api-fxpractice.oanda.com'); self.token=os.getenv('OANDA_TOKEN',''); self.account=os.getenv('OANDA_ACCOUNT_ID','')
    def configured(self): return bool(self.token and self.account)
    async def prices(self,instruments):
        if not self.configured(): return None
        async with httpx.AsyncClient(timeout=10) as c:
            r=await c.get(f'{self.base}/v3/accounts/{self.account}/pricing',params={'instruments':','.join(instruments)},headers={'Authorization':f'Bearer {self.token}'}); r.raise_for_status(); return r.json()
    async def market_order(self,instrument,units):
        if not self.configured(): raise RuntimeError('OANDA broker is not configured')
        payload={'order':{'type':'MARKET','instrument':instrument,'units':str(units),'timeInForce':'FOK','positionFill':'DEFAULT'}}
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post(f'{self.base}/v3/accounts/{self.account}/orders',json=payload,headers={'Authorization':f'Bearer {self.token}'}); r.raise_for_status(); return r.json()
