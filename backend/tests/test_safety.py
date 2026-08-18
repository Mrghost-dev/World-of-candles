import os
os.environ['DATABASE_URL']='sqlite:///./test.db'; os.environ['JWT_SECRET']='x'*40; os.environ['REAL_MONEY_ENABLED']='false'; os.environ['REAL_TRADING_ENABLED']='false'
from fastapi.testclient import TestClient
from app import app

def test_health():
    with TestClient(app) as c: assert c.get('/health').status_code==200

def test_real_gate():
    with TestClient(app) as c: assert c.get('/readiness').json()['real_execution_locked'] is True
