# RAVIN TRADING PRO — ADVANCED

This is the upgraded version of the earlier **Ravin Trading Pro Full Stack** project.

## Staged architecture

**Market data → payments sandbox → PostgreSQL → KYC → broker practice → production security/monitoring**.

Provider adapters are server-side. Real money is hard-disabled by default.

### Run
```bash
cp .env.example .env
docker compose up --build
```
- Web: http://localhost:3000
- API: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

### Tests
```bash
docker compose run --rm api pytest -q
```

### Real-money gate
Keep both false until regulatory, KYC/AML, client-money, provider, broker, security and operational requirements are completed:
```env
REAL_MONEY_ENABLED=false
REAL_TRADING_ENABLED=false
```

Never put API secrets in Git. Never request/store an M-Pesa PIN.
