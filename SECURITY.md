# Production Security Baseline

- Never commit `.env` or provider secrets.
- Keep real-money and real-trading flags false until compliance sign-off.
- Use HTTPS, WAF/rate limiting, secure cookies, strict CORS and a secrets manager in production.
- Verify payment webhooks cryptographically and make every callback idempotent.
- Credit balances only from provider-verified settlement events.
- Keep a durable audit log for privileged actions.
- Use PostgreSQL TLS, encryption/backups/PITR and least-privilege database credentials.
- Add dependency/SAST/DAST scanning and penetration testing before launch.
- Never request, receive or store an M-Pesa PIN.
- Use broker practice/demo first; live execution must be a separately approved deployment.
