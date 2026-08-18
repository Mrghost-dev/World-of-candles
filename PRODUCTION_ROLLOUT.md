# Staged rollout

1. Local: paper trading + synthetic test data.
2. Market data: configure Twelve Data and validate quotes/candles without placing trades.
3. Daraja: configure sandbox STK Push and verify callbacks/reconciliation; do not settle from client UI.
4. PayPal: configure sandbox Orders API + webhook verification; test approved, completed, denied, reversed and duplicate events.
5. PostgreSQL: migrate to managed PostgreSQL with TLS, backups and PITR; test restore.
6. KYC: connect a provider sandbox and require VERIFIED before live capability.
7. Broker: connect OANDA practice; verify order lifecycle, rejection, fills, positions and reconciliation.
8. Security: HTTPS, WAF/rate limits, secrets manager, alerts, logs, metrics, backup/restore and incident procedures.
9. Compliance: complete applicable licensing, AML/KYC, client-money, privacy and broker/payment-provider requirements.
10. Production: enable real-money and real-trading gates only in a controlled server deployment after all checks pass.
