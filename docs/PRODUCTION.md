# Production Runbook

## 1. Environment

Copy the template and replace every `replace-with-*` value:

```bash
cp .env.production.example .env
```

Required:

- `SECRET_KEY`
- `HMAC_SECRET`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `POSTGRES_PASSWORD`
- `TYPESENSE_API_KEY`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`

Optional email (seller notifications on approve/reject):

- `EMAIL_BACKEND` — e.g. SMTP backend in production
- `DEFAULT_FROM_EMAIL`
- `NOTIFY_SELLER_EMAIL=true`

Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The web container runs migrations when `RUN_DB_UPGRADE=true`, then bootstrap (admin, MinIO, Typesense).

Background jobs run in the `scheduler` container.

## 3. Reverse Proxy

HTTPS only. Forward `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`.
Keep `TRUST_PROXY=true` only behind a trusted proxy.

## 4. Post-Deploy Checks

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 web
```

URLs:

- `/health`, `/ready`
- `/`
- `/posts/new`
- `/moderation/`
- `/robots.txt`
- `/sitemap.xml`

Smoke:

- register → create listing → approve/reject with reason in `/moderation/`
- edit photos, contact rate limit, report with honeypot empty
- search + pagination filters preserved

## 5. Backups

Back up PostgreSQL, MinIO, and `.env`. Do a restore drill before launch.

## 6. Rollback

Record image/build and migration revision before deploy.
