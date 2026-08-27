"""add why_it_matters to signal

Revision ID: 0005_why_it_matters
Revises: 0004_delivery_vector
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_why_it_matters"
down_revision: Union[str, None] = "0004_delivery_vector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("signal", sa.Column("why_it_matters", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("signal", "why_it_matters")
