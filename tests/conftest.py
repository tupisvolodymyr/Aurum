import os
import pathlib
import tempfile

_TEST_DB_PATH = pathlib.Path(tempfile.gettempdir()) / "demo_casino_test.db"
_TEST_DB_PATH.unlink(missing_ok=True)

# Must be set before anything imports app.config / app.database, since the
# settings are lru_cache'd and the async engine is created at import time.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-do-not-use-in-prod")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_games  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        await seed_games(db)
    yield
    await engine.dispose()
    _TEST_DB_PATH.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac
