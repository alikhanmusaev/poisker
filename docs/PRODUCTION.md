# Production Runbook

## 1. Environment

Copy the template and replace every `replace-with-*` value:

```bash
cp .env.production.example .env
```

Required secrets:

- `SECRET_KEY`
- `HMAC_SECRET`
- `ADMIN_PASSWORD`
- `POSTGRES_PASSWORD`
- `TYPESENSE_API_KEY`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `TURNSTILE_SITE_KEY`
- `TURNSTILE_SECRET_KEY`

Generate Flask/HMAC secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 2. Start

Use the production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build web
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The web container runs database migrations when `RUN_DB_UPGRADE=true`.
Use `RUN_DB_INIT=true` only for a controlled first-time legacy bootstrap, not for normal restarts.

## 3. Reverse Proxy

Expose the app through HTTPS only. The compose file binds the app to `127.0.0.1:8000`.
Your public reverse proxy should terminate TLS and forward:

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

Keep `TRUST_PROXY=true` only when the app is reachable exclusively through that trusted proxy.

## 4. Post-Deploy Checks

Run:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 web
```

Check in browser:

- `/`
- `/posts/new`
- `/admin`
- `/robots.txt`
- `/sitemap.xml`
- `/sw.js`
- `/.well-known/assetlinks.json`

Functional smoke:

- publish an ad with Turnstile enabled
- save/copy edit link
- open own ad and verify edit button appears only for the owner token
- search by title/category/city
- upload an image
- file a report
- login to admin and hide/publish a test ad

## 5. Backups

Back up at least:

- PostgreSQL volume/database
- MinIO data volume
- `.env` secret file in a secure password manager

Do a restore drill before public launch.

## 6. Rollback

Before deploy, record the image/build and database migration revision.
Rollback code first, then database only if the migration is known to be reversible.
