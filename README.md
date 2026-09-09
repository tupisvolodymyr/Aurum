# AURUM — Online Casino Platform

**AURUM** is an online casino platform I built, powered by **FastAPI**. This
repository represents the functionality and architecture of that project:
player registration and authentication, a game catalog, a wallet with full
transaction accounting, custom game RNG logic, and a fully custom UI.

## Features

- 🎰 **Slots (Golden Reels)** — a classic 3-reel slot with a spin animation
  built on the Web Animations API (staggered reel timing, motion blur,
  big-win celebration)
- 🎡 **Wheel of Fortune (Golden Wheel)** — bet on a multiplier (x2…x40); the
  higher the multiplier, the smaller its slice of the wheel
- 🏛 **Public lobby** — game catalog, category filters, search, favorites,
  recently played, recommendations, latest-winners feed, jackpot ticker
- 🔐 **Authentication** — registration/login with Argon2id password hashing,
  revocable server-side sessions (hashed tokens), double-submit-cookie CSRF
  protection
- 💰 **Wallet** — atomic debit/credit operations with row-level locking
  (`FOR UPDATE`), a full transaction ledger, and a `CHECK(balance >= 0)`
  database constraint
- 👤 **Account dashboard** — balance deposits/withdrawals, transaction history
- 🎲 **Game RNG logic** — `secrets.SystemRandom` (CSPRNG), a controlled RTP for
  every betting option, verified with large-sample RTP tests
- 🐳 **Docker-ready** — `docker-compose` with PostgreSQL for a
  production-like setup

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Database | PostgreSQL (docker) / SQLite (local development) |
| Templates | Jinja2 (server-rendered) |
| Frontend | Vanilla JS (fetch API, Web Animations API) — no frameworks |
| Security | Argon2id, CSRF (double-submit cookie), safe redirects (`next` param) |
| Testing | pytest, pytest-asyncio |

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env
# generate your own SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(64))"

alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

### Or via Docker (PostgreSQL)

```bash
cp .env.example .env   # fill in SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

### Tests

```bash
pytest -q
```

## Deploying to Vercel

The app is a standard FastAPI/ASGI app, so `app/main.py` didn't need to
change — `api/index.py` just re-exports it, and `vercel.json` rewrites every
request to that one Python function.

**Vercel's filesystem is read-only and each function invocation can be a
fresh instance, so this deployment needs an external Postgres — the bundled
SQLite (`casino.db`) will not work there.** [Neon](https://neon.tech) has a
free tier and a one-click Vercel integration; Supabase/Railway Postgres work
the same way.

1. **Provision Postgres** and grab its connection string. SQLAlchemy's async
   driver needs `postgresql+asyncpg://` (not the bare `postgresql://` most
   providers give you) — e.g.:
   `postgresql+asyncpg://user:pass@host/dbname?sslmode=require`.

2. **Run migrations against it once, from your machine** (Vercel never runs
   this for you — its functions only serve requests):
   ```bash
   DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
   ```
   Re-run this after any future migration is added, same as you would for
   any other remote database.

3. **Install the Vercel CLI and link the project:**
   ```bash
   npm i -g vercel
   vercel login
   vercel link
   ```

4. **Set environment variables** (Vercel dashboard → Project → Settings →
   Environment Variables, or `vercel env add <NAME>`):
   | Variable | Value |
   |---|---|
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `DATABASE_URL` | the `postgresql+asyncpg://...` string from step 1 |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |

5. **Deploy:**
   ```bash
   vercel --prod
   ```
   (Or connect the GitHub repo in the Vercel dashboard for automatic
   deploys on every push — same env vars, same one-time migration step.)

Notes specific to this setup:
- `app/database.py` switches to `NullPool` automatically when Vercel's
  `VERCEL=1` environment variable is present, since a warm connection pool
  doesn't help (and can exhaust a free-tier Postgres's connection limit)
  across short-lived serverless instances. Local dev and Docker are
  unaffected.
- `/static/*` is served through the same Python function (FastAPI's
  `StaticFiles` mount) rather than as separate Vercel static assets — fine
  for a demo, but worth moving to Vercel's own static hosting if this ever
  needs to handle real production traffic.
