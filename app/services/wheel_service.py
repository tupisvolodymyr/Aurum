from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.games.wheel import MULTIPLIERS, spin_wheel
from app.models import Transaction, TransactionType, Wallet

MIN_BET = 10
MAX_BET = 500


class WheelSpinError(Exception):
    """Expected, user-facing spin failures (bad bet, bad pick, insufficient funds)."""


@dataclass(frozen=True)
class WheelOutcome:
    landed_multiplier: int
    chosen_multiplier: int
    winnings: int
    balance: int


async def spin(
    db: AsyncSession, *, user_id: int, bet: int, chosen_multiplier: int, game_id: int | None = None
) -> WheelOutcome:
    if bet < MIN_BET or bet > MAX_BET:
        raise WheelSpinError(f"Ставка має бути від {MIN_BET} до {MAX_BET} ₴")
    if chosen_multiplier not in MULTIPLIERS:
        raise WheelSpinError("Невірний вибір множника")

    # with_for_update() row-locks the wallet under Postgres so two concurrent
    # spins from the same account can't both read the same starting balance.
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    wallet = result.scalar_one()

    if wallet.balance < bet:
        raise WheelSpinError("Недостатньо коштів на балансі")

    landed = spin_wheel()

    wallet.balance -= bet
    db.add(
        Transaction(
            user_id=user_id,
            game_id=game_id,
            type=TransactionType.BET,
            amount=-bet,
            balance_after=wallet.balance,
            description=f"Golden Wheel — ставка на x{chosen_multiplier}",
        )
    )

    winnings = bet * landed if landed == chosen_multiplier else 0
    if winnings > 0:
        wallet.balance += winnings
        db.add(
            Transaction(
                user_id=user_id,
                game_id=game_id,
                type=TransactionType.WIN,
                amount=winnings,
                balance_after=wallet.balance,
                description=f"Golden Wheel — виграш x{landed}",
            )
        )

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise WheelSpinError("Недостатньо коштів на балансі") from exc

    await db.refresh(wallet)
    return WheelOutcome(landed_multiplier=landed, chosen_multiplier=chosen_multiplier, winnings=winnings, balance=wallet.balance)
