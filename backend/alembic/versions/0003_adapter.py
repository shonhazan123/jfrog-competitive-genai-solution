"""adapter column

Revision ID: 0003_adapter
Revises: 0002_signals
Create Date: 2026-08-26 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_adapter"
down_revision: Union[str, None] = "0002_signals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("source", sa.Column("adapter", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("source", "adapter")
