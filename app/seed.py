"""Idempotent game-catalog seeding, run once from the FastAPI lifespan.

All titles/providers below are invented for this demo catalog — not real
licensed games or studios. Only "slots" (Golden Reels) and "golden-wheel"
are actually playable; everything else is a Coming Soon browsing entry.
LIVE_CASINO intentionally has zero entries, so the lobby's empty-state UI
has something real to show.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Game, GameCategory

_CATALOG: list[dict] = [
    # slug, title, provider, category, is_active, is_new, is_popular
    dict(slug="slots", title="Golden Reels", provider="Silverline Gaming", category=GameCategory.SLOTS, is_active=True, is_popular=True),
    dict(slug="wild-fortune", title="Wild Fortune", provider="Nova Studios", category=GameCategory.SLOTS, is_new=True),
    dict(slug="diamond-rush", title="Diamond Rush", provider="Vertex Games", category=GameCategory.SLOTS),
    dict(slug="fruit-blast", title="Fruit Blast", provider="Lucky Forge", category=GameCategory.SLOTS),
    dict(slug="mystic-forest", title="Mystic Forest", provider="Crown Interactive", category=GameCategory.SLOTS),
    dict(slug="pharaohs-gold", title="Pharaoh's Gold", provider="Obsidian Play", category=GameCategory.SLOTS, is_popular=True),
    dict(slug="fire-phoenix", title="Fire Phoenix", provider="Nova Studios", category=GameCategory.SLOTS, is_new=True),
    dict(slug="crystal-cascade", title="Crystal Cascade", provider="Silverline Gaming", category=GameCategory.SLOTS),
    dict(slug="lucky-sevens-deluxe", title="Lucky 7s Deluxe", provider="Vertex Games", category=GameCategory.SLOTS, is_popular=True),
    dict(slug="european-roulette", title="European Roulette", provider="Crown Interactive", category=GameCategory.ROULETTE),
    dict(slug="american-roulette", title="American Roulette", provider="Obsidian Play", category=GameCategory.ROULETTE),
    dict(slug="classic-blackjack", title="Classic Blackjack", provider="Vertex Games", category=GameCategory.BLACKJACK),
    dict(slug="blackjack-pro", title="Blackjack Pro", provider="Silverline Gaming", category=GameCategory.BLACKJACK, is_popular=True),
    dict(slug="texas-holdem", title="Texas Hold'em", provider="Nova Studios", category=GameCategory.POKER),
    dict(slug="casino-stud-poker", title="Casino Stud Poker", provider="Crown Interactive", category=GameCategory.POKER),
    dict(slug="golden-wheel", title="Golden Wheel", provider="Silverline Gaming", category=GameCategory.WHEEL, is_active=True, is_new=True),
]


async def seed_games(db: AsyncSession) -> None:
    """Insert any catalog entries missing from the DB, keyed by slug.

    Per-entry rather than "only seed if the table is empty": that all-or-
    nothing version meant a game added to _CATALOG later (e.g. Golden Wheel)
    would silently never appear for anyone whose DB already had rows from
    an earlier run.
    """
    existing_slugs = set((await db.execute(select(Game.slug))).scalars().all())

    for entry in _CATALOG:
        if entry["slug"] not in existing_slugs:
            db.add(Game(**entry))

    await db.commit()
