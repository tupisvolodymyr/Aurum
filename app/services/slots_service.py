from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.games.slots import SpinResult, play
from app.models import Transaction, TransactionType, Wallet

MIN_BET = 10
MAX_BET = 500


class SpinError(Exception):
    """Expected, user-facing spin failures (bad bet, insufficient funds)."""


@dataclass(frozen=True)
class SpinOutcome:
    result: SpinResult
    winnings: int
    balance: int


async def spin(db: AsyncSession, *, user_id: int, bet: int, game_id: int | None = None) -> SpinOutcome:
    if bet < MIN_BET or bet > MAX_BET:
        raise SpinError(f"Bet must be between {MIN_BET} and {MAX_BET} ₴")

    # with_for_update() row-locks the wallet under Postgres so two concurrent
    # spins from the same account can't both read the same starting balance.
    # SQLite has no real row locking, but its single-writer transaction
    # semantics serialize this anyway — the CHECK(balance >= 0) constraint is
    # the last line of defense either way.
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    wallet = result.scalar_one()

    if wallet.balance < bet:
        raise SpinError("Insufficient balance")

    outcome = play()

    wallet.balance -= bet
    db.add(
        Transaction(
            user_id=user_id,
            game_id=game_id,
            type=TransactionType.BET,
            amount=-bet,
            balance_after=wallet.balance,
            description="Slots — bet",
        )
    )

    winnings = bet * outcome.multiplier
    if winnings > 0:
        wallet.balance += winnings
        db.add(
            Transaction(
                user_id=user_id,
                game_id=game_id,
                type=TransactionType.WIN,
                amount=winnings,
                balance_after=wallet.balance,
                description=f"Slots — win x{outcome.multiplier}",
            )
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise SpinError("Insufficient balance") from exc

    await db.refresh(wallet)
    return SpinOutcome(result=outcome, winnings=winnings, balance=wallet.balance)
