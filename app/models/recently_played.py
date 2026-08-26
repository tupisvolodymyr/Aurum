from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecentlyPlayed(Base):
    """One row per (user, game) — upserted on each play so this stays small
    and naturally orders by recency, unlike an ever-growing play log."""

    __tablename__ = "recently_played"
    __table_args__ = (UniqueConstraint("user_id", "game_id", name="uq_recently_played_user_game"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False)

    last_played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
