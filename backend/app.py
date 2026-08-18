import os,secrets,time,json
from datetime import datetime,timedelta,timezone
from fastapi import FastAPI,HTTPException,Depends,Response,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel,EmailStr,Field
from sqlalchemy import create_engine,String,Float,Boolean,DateTime,ForeignKey,select,func
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,Session
import jwt
from pwdlib import PasswordHash
from prometheus_client import Counter,Histogram,generate_latest
from app.providers import MarketData,Daraja,PayPal,Oanda,KYC

DB=os.getenv('DATABASE_URL','sqlite:///./dev.db'); SECRET=os.getenv('JWT_SECRET','change-me'); ORIGIN=os.getenv('FRONTEND_ORIGIN','http://localhost:3000')
REAL_MONEY=os.getenv('REAL_MONEY_ENABLED','false').lower()=='true'; REAL_TRADING=os.getenv('REAL_TRADING_ENABLED','false').lower()=='true'; PH=PasswordHash.recommended()
engine=create_engine(DB,pool_pre_ping=True)
class Base(DeclarativeBase): pass
class User(Base):
 __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120)); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(30),default='trader'); active:Mapped[bool]=mapped_column(Boolean,default=True); kyc:Mapped[str]=mapped_column(String(30),default='NOT_STARTED'); broker_account:Mapped[str|None]=mapped_column(String(150),nullable=True); created:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Account(Base):
 __tablename__='accounts'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True); balance:Mapped[float]=mapped_column(Float,default=0); reserved:Mapped[float]=mapped_column(Float,default=0); demo:Mapped[float]=mapped_column(Float,default=10000)
class Ledger(Base):
 __tablename__='ledger'; id:Mapped[int]=mapped_column(primary_key=True); ref:Mapped[str]=mapped_column(String(100),unique=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); kind:Mapped[str]=mapped_column(String(30)); method:Mapped[str]=mapped_column(String(30)); amount:Mapped[float]=mapped_column(Float); status:Mapped[str]=mapped_column(String(40),default='PENDING'); provider_ref:Mapped[str|None]=mapped_column(String(255),nullable=True); created:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Order(Base):
 __tablename__='orders'; id:Mapped[int]=mapped_column(primary_key=True); user_id:Mapped[int]=mapped_column(ForeignKey('users.id')); symbol:Mapped[str]=mapped_column(String(40)); side:Mapped[str]=mapped_column(String(10)); qty:Mapped[float]=mapped_column(Float); mode:Mapped[str]=mapped_column(String(10)); status:Mapped[str]=mapped_column(String(30),default='NEW'); broker_ref:Mapped[str|None]=mapped_column(String(150),nullable=True); created:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Audit(Base):
 __tablename__='audit'; id:Mapped[int]=mapped_column(primary_key=True); actor:Mapped[int|None]=mapped_column(nullable=True); action:Mapped[str]=mapped_column(String(255)); metadata_json:Mapped[str|None]=mapped_column(nullable=True); created:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Register(BaseModel): name:str=Field(min_length=2,max_length=120); email:EmailStr; password:str=Field(min_length=10,max_length=128)
class Login(BaseModel): email:EmailStr; password:str
class OrderIn(BaseModel): symbol:str; side:str; qty:float=Field(gt=0); mode:str='paper'
class Deposit(BaseModel): amount:float=Field(gt=0); method:str; phone:str|None=None
class Withdraw(BaseModel): amount:float=Field(gt=0); method:str

app=FastAPI(title='Ravin Trading Pro Advanced API',version='3.0.0')
app.add_middleware(CORSMiddleware,allow_origins=[ORIGIN],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
REQ=Counter('ravin_http_requests_total','HTTP requests'); ORD=Counter('ravin_orders_total','Orders'); LAT=Histogram('ravin_http_seconds','HTTP latency')
@app.middleware('http')
async def headers(request,call_next):
 st=time.perf_counter();REQ.inc();r=await call_next(request);LAT.observe(time.perf_counter()-st)
 r.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'strict-origin-when-cross-origin','Permissions-Policy':'camera=(), microphone=(), geolocation=()'});return r

def db():
 with Session(engine) as s: yield s
def token(u): return jwt.encode({'sub':u.id,'role':u.role,'exp':datetime.now(timezone.utc)+timedelta(minutes=30)},SECRET,algorithm='HS256')
def current(request:Request,s:Session=Depends(db)):
 t=request.cookies.get('ravin_access')
 if not t: raise HTTPException(401,'Not authenticated')
 try: uid=int(jwt.decode(t,SECRET,algorithms=['HS256'])['sub'])
 except Exception: raise HTTPException(401,'Invalid session')
 u=s.get(User,uid)
 if not u or not u.active: raise HTTPException(401,'Invalid session')
 return u
def admin(u=Depends(current)):
 if u.role not in ('admin','operations','compliance'): raise HTTPException(403,'Admin access required')
 return u
def audit(s,u,action,meta=None): s.add(Audit(actor=u.id if u else None,action=action,metadata_json=json.dumps(meta or {})))
@app.on_event('startup')
def init():
 Base.metadata.create_all(engine)
 with Session(engine) as s:
  email=os.getenv('ADMIN_EMAIL','admin@ravintrading.local').lower()
  if not s.scalar(select(User).where(User.email==email)):
   u=User(name='Master Admin',email=email,password=PH.hash(os.getenv('ADMIN_PASSWORD','ChangeMeNow123!')),role='admin');s.add(u);s.flush();s.add(Account(user_id=u.id));s.commit()
@app.get('/health')
def health(): return {'status':'ok','version':'3.0.0'}
@app.get('/readiness')
def readiness(): return {'market_data':MarketData().configured(),'daraja_sandbox':Daraja().configured(),'paypal_sandbox':PayPal().configured(),'kyc':KYC().configured(),'broker':Oanda().configured(),'real_money':REAL_MONEY,'real_trading':REAL_TRADING,'real_execution_locked':not(REAL_MONEY and REAL_TRADING)}
@app.get('/metrics')
def metrics(): return PlainTextResponse(generate_latest(),media_type='text/plain; version=0.0.4')
@app.post('/auth/register')
def register(x:Register,response:Response,s:Session=Depends(db)):
 if s.scalar(select(User).where(User.email==x.email.lower())): raise HTTPException(409,'Email already registered')
 u=User(name=x.name,email=x.email.lower(),password=PH.hash(x.password));s.add(u);s.flush();s.add(Account(user_id=u.id));audit(s,u,'REGISTER');s.commit();response.set_cookie('ravin_access',token(u),httponly=True,samesite='lax',secure=os.getenv('APP_ENV')=='production',max_age=1800);return {'id':u.id,'role':u.role}
@app.post('/auth/login')
def login(x:Login,response:Response,s:Session=Depends(db)):
 u=s.scalar(select(User).where(User.email==x.email.lower()))
 if not u or not PH.verify(x.password,u.password): raise HTTPException(401,'Invalid credentials')
 response.set_cookie('ravin_access',token(u),httponly=True,samesite='lax',secure=os.getenv('APP_ENV')=='production',max_age=1800);return {'id':u.id,'name':u.name,'role':u.role}
@app.post('/auth/logout')
def logout(response:Response): response.delete_cookie('ravin_access');return {'ok':True}
@app.get('/me')
def me(u=Depends(current),s:Session=Depends(db)):
 a=s.scalar(select(Account).where(Account.user_id==u.id));return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'kyc':u.kyc,'balance':a.balance,'demo':a.demo,'reserved':a.reserved}
@app.get('/markets/quote/{symbol}')
async def quote(symbol:str,u=Depends(current)): return await MarketData().quote(symbol.upper()) or {'status':'market_data_not_configured','symbol':symbol.upper()}
@app.get('/markets/candles/{symbol}')
async def candles(symbol:str,interval='15min',u=Depends(current)): return await MarketData().candles(symbol.upper(),interval) or {'status':'market_data_not_configured','values':[]}
@app.post('/trading/orders')
async def order(x:OrderIn,u=Depends(current),s:Session=Depends(db)):
 if x.side not in ('buy','sell') or x.mode not in ('paper','real'): raise HTTPException(400,'Invalid order')
 if x.mode=='real':
  if not(REAL_MONEY and REAL_TRADING): raise HTTPException(403,'REAL execution locked by server safety gates')
  if u.kyc!='VERIFIED' or not u.broker_account: raise HTTPException(403,'Verified KYC and broker mapping required')
  result=await Oanda().market_order(x.symbol.upper(),x.qty if x.side=='buy' else -x.qty); tx=result.get('orderFillTransaction') or result.get('orderCreateTransaction') or {}; ref=tx.get('id')
  o=Order(user_id=u.id,symbol=x.symbol.upper(),side=x.side,qty=x.qty,mode='real',status='FILLED',broker_ref=ref);s.add(o);audit(s,u,'REAL_ORDER',{'broker_ref':ref});s.commit();ORD.inc();return {'id':o.id,'status':'FILLED','broker_ref':ref}
 o=Order(user_id=u.id,symbol=x.symbol.upper(),side=x.side,qty=x.qty,mode='paper',status='FILLED');s.add(o);audit(s,u,'PAPER_ORDER');s.commit();ORD.inc();return {'id':o.id,'status':'FILLED','mode':'paper'}
@app.get('/trading/orders')
def orders(u=Depends(current),s:Session=Depends(db)): return [{'id':o.id,'symbol':o.symbol,'side':o.side,'qty':o.qty,'mode':o.mode,'status':o.status} for o in s.scalars(select(Order).where(Order.user_id==u.id).order_by(Order.created.desc()))]
@app.post('/wallet/deposit')
async def deposit(x:Deposit,u=Depends(current),s:Session=Depends(db)):
 ref='DEP-'+secrets.token_hex(8).upper()
 if x.method=='demo':
  a=s.scalar(select(Account).where(Account.user_id==u.id));a.demo+=x.amount;s.add(Ledger(ref=ref,user_id=u.id,kind='deposit',method='demo',amount=x.amount,status='SETTLED'));s.commit();return {'status':'SETTLED','reference':ref}
 if not REAL_MONEY: raise HTTPException(403,'Real-money wallet disabled')
 e=Ledger(ref=ref,user_id=u.id,kind='deposit',method=x.method,amount=x.amount,status='PENDING');s.add(e);s.commit()
 if x.method=='mpesa':
  if not x.phone: raise HTTPException(400,'Phone required')
  result=await Daraja().stk_push(x.phone,x.amount,ref);e.provider_ref=result.get('CheckoutRequestID');s.commit();return {'status':'PENDING','reference':ref,'provider':result}
 if x.method=='paypal':
  result=await PayPal().create_order(x.amount);e.provider_ref=result.get('id');s.commit();return {'status':'PENDING','reference':ref,'provider':result}
 raise HTTPException(400,'Unsupported provider')
@app.post('/payments/daraja/callback')
async def daraja_callback(payload:dict): return {'ResultCode':0,'ResultDesc':'Accepted; settlement must be verified server-side'}
@app.post('/payments/paypal/webhook')
async def paypal_webhook(request:Request): return {'received':True,'note':'Verify PayPal webhook transmission before settling a ledger entry'}
@app.post('/wallet/withdraw')
def withdraw(x:Withdraw,u=Depends(current),s:Session=Depends(db)):
 if not REAL_MONEY: raise HTTPException(403,'Withdrawals disabled')
 a=s.scalar(select(Account).where(Account.user_id==u.id))
 if x.amount>a.balance: raise HTTPException(400,'Insufficient balance')
 a.balance-=x.amount;a.reserved+=x.amount;ref='WDR-'+secrets.token_hex(8).upper();s.add(Ledger(ref=ref,user_id=u.id,kind='withdrawal',method=x.method,amount=x.amount,status='PENDING_REVIEW'));s.commit();return {'status':'PENDING_REVIEW','reference':ref}
@app.get('/admin/overview')
def overview(u=Depends(admin),s:Session=Depends(db)): return {'users':s.scalar(select(func.count()).select_from(User)),'orders':s.scalar(select(func.count()).select_from(Order)),'ledger':s.scalar(select(func.count()).select_from(Ledger)),'kyc_pending':s.scalar(select(func.count()).select_from(User).where(User.kyc!='VERIFIED'))}
@app.get('/admin/users')
def users(u=Depends(admin),s:Session=Depends(db)): return [{'id':x.id,'name':x.name,'email':x.email,'role':x.role,'kyc':x.kyc} for x in s.scalars(select(User).order_by(User.created.desc()))]
@app.get('/admin/audit')
def audits(u=Depends(admin),s:Session=Depends(db)): return [{'id':a.id,'actor':a.actor,'action':a.action,'created':a.created.isoformat()} for a in s.scalars(select(Audit).order_by(Audit.created.desc()).limit(300))]
