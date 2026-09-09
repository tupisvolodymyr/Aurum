import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# On Vercel (and other serverless hosts) each request can land on a fresh,
# short-lived function instance, so a warm connection *pool* just leaks
# connections against the DB's own limit instead of helping — NullPool
# opens one connection per checkout and closes it right after, which is
# what a hosted Postgres (Neon/Supabase/etc.) expects from a serverless
# caller. Vercel sets VERCEL=1 in every function's environment, so this
# switches automatically without needing a separate settings flag; local
# dev and Docker (no VERCEL var) keep the normal pooled engine.
_engine_kwargs = {"echo": settings.debug}
if os.environ.get("VERCEL"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
