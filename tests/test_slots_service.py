import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User, Wallet
from app.services.security import hash_password
from app.services.slots_service import MIN_BET, SpinError, spin


async def _make_user_with_balance(db: AsyncSession, *, username: str, balance: int) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("irrelevant-pw"))
    db.add(user)
    await db.flush()
    db.add(Wallet(user_id=user.id, balance=balance))
    await db.commit()
    await db.refresh(user)
    return user


async def test_spin_rejects_bet_below_minimum():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="svc_min_bet", balance=1000)
        with pytest.raises(SpinError):
            await spin(db, user_id=user.id, bet=MIN_BET - 1)


async def test_spin_rejects_insufficient_balance():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="svc_broke", balance=5)
        with pytest.raises(SpinError):
            await spin(db, user_id=user.id, bet=MIN_BET)


async def test_spin_debits_bet_and_credits_win_consistently():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="svc_consistent", balance=10_000)
        outcome = await spin(db, user_id=user.id, bet=100)

        assert outcome.balance == 10_000 - 100 + outcome.winnings
        assert outcome.balance >= 0

        wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
        assert wallet.balance == outcome.balance
