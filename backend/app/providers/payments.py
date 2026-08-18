import base64, os
from datetime import datetime
import httpx

class Daraja:
    def __init__(self):
        self.base=os.getenv('DARAJA_BASE_URL','https://sandbox.safaricom.co.ke')
        self.key=os.getenv('DARAJA_CONSUMER_KEY',''); self.secret=os.getenv('DARAJA_CONSUMER_SECRET','')
        self.shortcode=os.getenv('DARAJA_SHORTCODE',''); self.passkey=os.getenv('DARAJA_PASSKEY',''); self.callback=os.getenv('DARAJA_CALLBACK_URL','')
    def configured(self): return all([self.key,self.secret,self.shortcode,self.passkey,self.callback])
    async def token(self):
        raw=base64.b64encode(f'{self.key}:{self.secret}'.encode()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.get(f'{self.base}/oauth/v1/generate?grant_type=client_credentials',headers={'Authorization':f'Basic {raw}'}); r.raise_for_status(); return r.json()['access_token']
    async def stk_push(self,phone,amount,reference):
        if not self.configured(): raise RuntimeError('Daraja sandbox is not configured')
        ts=datetime.now().strftime('%Y%m%d%H%M%S')
        password=base64.b64encode(f'{self.shortcode}{self.passkey}{ts}'.encode()).decode()
        payload={'BusinessShortCode':self.shortcode,'Password':password,'Timestamp':ts,'TransactionType':'CustomerPayBillOnline','Amount':int(amount),'PartyA':phone,'PartyB':self.shortcode,'PhoneNumber':phone,'CallBackURL':self.callback,'AccountReference':reference,'TransactionDesc':'Ravin Trading deposit'}
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.post(f'{self.base}/mpesa/stkpush/v1/processrequest',json=payload,headers={'Authorization':f'Bearer {await self.token()}'}); r.raise_for_status(); return r.json()

class PayPal:
    def __init__(self):
        self.base=os.getenv('PAYPAL_BASE_URL','https://api-m.sandbox.paypal.com'); self.client=os.getenv('PAYPAL_CLIENT_ID',''); self.secret=os.getenv('PAYPAL_CLIENT_SECRET',''); self.webhook=os.getenv('PAYPAL_WEBHOOK_ID','')
    def configured(self): return bool(self.client and self.secret)
    async def token(self):
        raw=base64.b64encode(f'{self.client}:{self.secret}'.encode()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post(f'{self.base}/v1/oauth2/token',data={'grant_type':'client_credentials'},headers={'Authorization':f'Basic {raw}','Content-Type':'application/x-www-form-urlencoded'}); r.raise_for_status(); return r.json()['access_token']
    async def create_order(self,amount,currency='USD'):
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.post(f'{self.base}/v2/checkout/orders',json={'intent':'CAPTURE','purchase_units':[{'amount':{'currency_code':currency,'value':f'{amount:.2f}'}}]},headers={'Authorization':f'Bearer {await self.token()}'}); r.raise_for_status(); return r.json()
    async def capture(self,order_id):
        async with httpx.AsyncClient(timeout=20) as c:
            r=await c.post(f'{self.base}/v2/checkout/orders/{order_id}/capture',headers={'Authorization':f'Bearer {await self.token()}'}); r.raise_for_status(); return r.json()
