import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GameCategory(str, enum.Enum):
    SLOTS = "slots"
    LIVE_CASINO = "live_casino"
    ROULETTE = "roulette"
    BLACKJACK = "blackjack"
    POKER = "poker"
    JACKPOT = "jackpot"
    WHEEL = "wheel"


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[GameCategory] = mapped_column(Enum(GameCategory), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # actually playable
    is_new: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
