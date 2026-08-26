import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User, Wallet
from app.services.security import hash_password
from app.services.wheel_service import MIN_BET, WheelSpinError, spin


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
        user = await _make_user_with_balance(db, username="wheel_min_bet", balance=1000)
        with pytest.raises(WheelSpinError):
            await spin(db, user_id=user.id, bet=MIN_BET - 1, chosen_multiplier=2)


async def test_spin_rejects_insufficient_balance():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="wheel_broke", balance=5)
        with pytest.raises(WheelSpinError):
            await spin(db, user_id=user.id, bet=MIN_BET, chosen_multiplier=2)


async def test_spin_rejects_invalid_multiplier():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="wheel_bad_pick", balance=1000)
        with pytest.raises(WheelSpinError):
            await spin(db, user_id=user.id, bet=MIN_BET, chosen_multiplier=7)  # not a real segment


async def test_spin_debits_bet_and_credits_win_consistently():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="wheel_consistent", balance=10_000)
        outcome = await spin(db, user_id=user.id, bet=100, chosen_multiplier=2)

        assert outcome.balance == 10_000 - 100 + outcome.winnings
        assert outcome.balance >= 0
        assert outcome.winnings in (0, 100 * outcome.landed_multiplier)

        wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
        assert wallet.balance == outcome.balance


async def test_win_only_when_landed_matches_chosen():
    async with AsyncSessionLocal() as db:
        user = await _make_user_with_balance(db, username="wheel_match_check", balance=100_000)
        for _ in range(50):
            outcome = await spin(db, user_id=user.id, bet=10, chosen_multiplier=2)
            if outcome.landed_multiplier == outcome.chosen_multiplier:
                assert outcome.winnings == 10 * outcome.landed_multiplier
            else:
                assert outcome.winnings == 0
