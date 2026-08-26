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
