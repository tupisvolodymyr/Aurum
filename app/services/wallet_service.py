from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Wallet


async def get_wallet(db: AsyncSession, user_id: int) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise LookupError(f"No wallet for user_id={user_id}")
    return wallet
