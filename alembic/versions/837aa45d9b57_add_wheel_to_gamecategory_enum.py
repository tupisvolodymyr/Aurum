"""add wheel to gamecategory enum

Revision ID: 837aa45d9b57
Revises: d0ff22600728
Create Date: 2026-09-09 17:36:25.817844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '837aa45d9b57'
down_revision: Union[str, Sequence[str], None] = 'd0ff22600728'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the 'WHEEL' label to the gamecategory enum.

    app/models/game.py's GameCategory gained WHEEL when the Golden Wheel
    game was added, but no migration ever taught the Postgres enum type
    about it — SQLite (used in local dev) stores Enum columns as a plain
    VARCHAR with no server-side check, so seeding a WHEEL row there always
    worked silently. Postgres enforces the enum for real, so seed_games()
    trying to insert category='WHEEL' fails with
    `invalid input value for enum gamecategory: "WHEEL"` the first time
    this runs against Postgres (e.g. on Vercel + Neon) unless this value is
    added first.

    ALTER TYPE ... ADD VALUE cannot run inside a transaction block on
    Postgres < 12; run it in an autocommit block so this migration works
    regardless of the target server's version.
    """
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE gamecategory ADD VALUE IF NOT EXISTS 'WHEEL'")


def downgrade() -> None:
    """No-op: Postgres has no ALTER TYPE ... DROP VALUE.

    Removing an enum label requires recreating the type (rename old type,
    create new one without the value, migrate the column, drop old type)
    and rewriting every row currently using it — not worth the risk/complexity
    for a straightforward additive change. If a real downgrade is ever
    needed, do it by hand against the specific target database instead.
    """
    pass
