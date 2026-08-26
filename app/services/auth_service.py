from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Transaction, TransactionType, User, UserSession, Wallet
from app.services.security import generate_token, hash_password, hash_token, verify_password

settings = get_settings()

# Precomputed so authenticate_user can always run a real argon2 verify, even
# when the user doesn't exist — keeps response timing from leaking whether
# a username/email is registered.
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-constant-time-auth")


def _as_aware_utc(dt: datetime) -> datetime:
    # SQLite has no real timezone-aware column type, so DateTime(timezone=True)
    # round-trips as naive. Postgres would already return it aware; this is a
    # no-op there.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class AuthError(Exception):
    """Raised for expected auth failures (bad credentials, taken username, ...)."""


class NotAuthenticated(Exception):
    """Raised by require_user when there is no valid session; handled in main.py."""

    def __init__(self, next_path: str | None = None) -> None:
        super().__init__()
        self.next_path = next_path


async def register_user(db: AsyncSession, *, username: str, email: str, password: str) -> User:
    existing = await db.execute(select(User).where(or_(User.username == username, User.email == email)))
    if existing.scalar_one_or_none() is not None:
        raise AuthError("Username or email is already taken")

    user = User(username=username, email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()  # assigns user.id without committing yet

    wallet = Wallet(user_id=user.id, balance=settings.starting_balance)
    db.add(wallet)
    await db.flush()

    db.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.BONUS,
            amount=settings.starting_balance,
            balance_after=wallet.balance,
            description="Welcome bonus",
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, *, identifier: str, password: str) -> User:
    result = await db.execute(select(User).where(or_(User.username == identifier, User.email == identifier)))
    user = result.scalar_one_or_none()
    # Always run verify_password, even on a missing user, so response timing
    # doesn't reveal whether the username/email exists.
    valid = verify_password(password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    if user is None or not user.is_active or not valid:
        raise AuthError("Invalid username/email or password")
    return user


async def create_session(db: AsyncSession, *, user: User, user_agent: str | None, ip_address: str | None) -> str:
    raw_token = generate_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=ip_address,
    )
    db.add(session)
    await db.commit()
    return raw_token


async def get_valid_session(db: AsyncSession, raw_token: str) -> UserSession | None:
    result = await db.execute(select(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    now = datetime.now(timezone.utc)
    if session.revoked_at is not None or _as_aware_utc(session.expires_at) < now:
        return None
    session.last_seen_at = now
    await db.commit()
    return session


async def revoke_session(db: AsyncSession, raw_token: str) -> None:
    result = await db.execute(select(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
    session = result.scalar_one_or_none()
    if session is not None:
        session.revoked_at = datetime.now(timezone.utc)
        await db.commit()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        return None
    session = await get_valid_session(db, raw_token)
    if session is None:
        return None
    result = await db.execute(select(User).where(User.id == session.user_id))
    return result.scalar_one_or_none()


async def require_user(request: Request, user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise NotAuthenticated(next_path=f"{request.url.path}?{request.url.query}" if request.url.query else request.url.path)
    return user
