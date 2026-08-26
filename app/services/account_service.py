from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionType, Wallet

MIN_DEPOSIT = 50
MAX_DEPOSIT = 5_000

MIN_WITHDRAWAL = 50
MAX_WITHDRAWAL = 5_000


class AccountError(Exception):
    """Expected, user-facing deposit/withdrawal failures."""


@dataclass(frozen=True)
class AccountOutcome:
    amount: int
    balance: int


async def deposit(db: AsyncSession, *, user_id: int, amount: int) -> AccountOutcome:
    if amount < MIN_DEPOSIT or amount > MAX_DEPOSIT:
        raise AccountError(f"Deposit must be between {MIN_DEPOSIT} and {MAX_DEPOSIT} ₴")

    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    wallet = result.scalar_one()

    wallet.balance += amount
    db.add(
        Transaction(
            user_id=user_id,
            type=TransactionType.DEPOSIT,
            amount=amount,
            balance_after=wallet.balance,
            description="Deposit",
        )
    )

    await db.commit()
    await db.refresh(wallet)
    return AccountOutcome(amount=amount, balance=wallet.balance)


async def withdraw(db: AsyncSession, *, user_id: int, amount: int) -> AccountOutcome:
    if amount < MIN_WITHDRAWAL or amount > MAX_WITHDRAWAL:
        raise AccountError(f"Withdrawal must be between {MIN_WITHDRAWAL} and {MAX_WITHDRAWAL} ₴")

    # with_for_update() row-locks the wallet under Postgres so a concurrent
    # request can't read the same starting balance twice; SQLite serializes
    # writes anyway. CHECK(balance >= 0) is the last line of defense either way.
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    wallet = result.scalar_one()

    if wallet.balance < amount:
        raise AccountError("Insufficient balance for this withdrawal")

    wallet.balance -= amount
    db.add(
        Transaction(
            user_id=user_id,
            type=TransactionType.WITHDRAWAL,
            amount=-amount,
            balance_after=wallet.balance,
            description="Withdrawal",
        )
    )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AccountError("Insufficient balance for this withdrawal") from exc

    await db.refresh(wallet)
    return AccountOutcome(amount=amount, balance=wallet.balance)


async def recent_transactions(db: AsyncSession, user_id: int, *, limit: int = 20) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
