"""Vercel Python Functions entrypoint.

Vercel's Python runtime auto-detects an ASGI app named `app` inside a file
under /api and routes requests to it (see vercel.json's rewrite, which sends
every path to this function so FastAPI's own router — not Vercel — decides
what each URL does). This file is intentionally a thin re-export: all real
application code stays in app/, unchanged, so the exact same app also still
runs locally via `uvicorn app.main:app` and in Docker.
"""

from app.main import app  # noqa: F401  (Vercel looks for this exact name)
