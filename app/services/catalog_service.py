import random
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, Game, RecentlyPlayed, Transaction, TransactionType, User

# Filler entries for the Latest Winners feed so it never looks empty on a
# fresh database. References real catalog game titles for consistency.
_MOCK_WINNERS = [
    {"username": "Player482", "game_title": "Golden Reels", "amount": 415},
    {"username": "LuckySpin7", "game_title": "Wild Fortune", "amount": 1_120},
    {"username": "GoldRush88", "game_title": "Pharaoh's Gold", "amount": 780},
    {"username": "AceHunter", "game_title": "Lucky 7s Deluxe", "amount": 3_050},
    {"username": "SpinMaster", "game_title": "Fire Phoenix", "amount": 260},
    {"username": "CasinoKing77", "game_title": "Crystal Cascade", "amount": 990},
]


@dataclass(frozen=True)
class Winner:
    username: str
    game_title: str
    amount: int


async def list_games(db: AsyncSession) -> list[Game]:
    result = await db.execute(select(Game).order_by(Game.category, Game.title))
    return list(result.scalars().all())


async def favorite_game_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = await db.execute(select(Favorite.game_id).where(Favorite.user_id == user_id))
    return set(result.scalars().all())


async def toggle_favorite(db: AsyncSession, *, user_id: int, game_id: int) -> bool:
    """Returns the new favorited state."""
    result = await db.execute(select(Favorite).where(Favorite.user_id == user_id, Favorite.game_id == game_id))
    existing = result.scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
        await db.commit()
        return False

    db.add(Favorite(user_id=user_id, game_id=game_id))
    await db.commit()
    return True


async def record_recently_played(db: AsyncSession, *, user_id: int, game_id: int) -> None:
    result = await db.execute(
        select(RecentlyPlayed).where(RecentlyPlayed.user_id == user_id, RecentlyPlayed.game_id == game_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.last_played_at = datetime.now(timezone.utc)
    else:
        db.add(RecentlyPlayed(user_id=user_id, game_id=game_id))
    await db.commit()


async def recently_played_games(db: AsyncSession, user_id: int, *, limit: int = 6) -> list[Game]:
    result = await db.execute(
        select(Game)
        .join(RecentlyPlayed, RecentlyPlayed.game_id == Game.id)
        .where(RecentlyPlayed.user_id == user_id)
        .order_by(RecentlyPlayed.last_played_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def recommended_games(db: AsyncSession, user_id: int, *, limit: int = 6) -> list[Game]:
    """Simple heuristic, not a real recommender: prefer games in the same
    category as the most recently played one, excluding those already
    played; fall back to globally popular games for a fresh account."""
    recent = await recently_played_games(db, user_id, limit=1)
    played_ids = await recently_played_games(db, user_id, limit=50)
    exclude_ids = {g.id for g in played_ids}

    if recent:
        result = await db.execute(
            select(Game)
            .where(Game.category == recent[0].category, Game.id.notin_(exclude_ids or [0]))
            .order_by(Game.is_popular.desc(), Game.is_new.desc(), Game.title)
            .limit(limit)
        )
        games = list(result.scalars().all())
        if games:
            return games

    result = await db.execute(
        select(Game)
        .where(Game.is_popular.is_(True), Game.id.notin_(exclude_ids or [0]))
        .order_by(Game.title)
        .limit(limit)
    )
    return list(result.scalars().all())


async def latest_winners(db: AsyncSession, *, limit: int = 8) -> list[Winner]:
    result = await db.execute(
        select(Transaction, User.username, Game.title)
        .join(User, User.id == Transaction.user_id)
        .outerjoin(Game, Game.id == Transaction.game_id)
        .where(Transaction.type == TransactionType.WIN)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )

    winners = [
        Winner(username=username, game_title=game_title or "Golden Reels", amount=txn.amount)
        for txn, username, game_title in result.all()
    ]

    if len(winners) < limit:
        filler = random.sample(_MOCK_WINNERS, k=min(limit - len(winners), len(_MOCK_WINNERS)))
        winners.extend(Winner(**entry) for entry in filler)

    return winners
