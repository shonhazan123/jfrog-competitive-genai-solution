"""research columns: claim.stance and signal.theme_key"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_research_columns"
down_revision: Union[str, None] = "0006_suppress_self_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claim", sa.Column("stance", sa.String(length=16), nullable=True))
    op.add_column("signal", sa.Column("theme_key", sa.String(length=64), nullable=True))
    op.create_index("ix_signal_theme_key", "signal", ["theme_key"])


def downgrade() -> None:
    op.drop_index("ix_signal_theme_key", table_name="signal")
    op.drop_column("signal", "theme_key")
    op.drop_column("claim", "stance")
