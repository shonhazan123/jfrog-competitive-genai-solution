"""drop analyst_queue and analyst_action

The human-in-the-loop quarantine / analyst-review flow (V1 Interpret approach)
was removed. The research-engine pipeline persists directly to the ledger with
no analyst queue, so these tables are dropped. See
docs/archive/v1-interpret-approach/ for the design record.

Revision ID: 0010_drop_analyst_tables
Revises: 0009_chunk_url
Create Date: 2026-08-30 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_drop_analyst_tables"
down_revision: Union[str, None] = "0009_chunk_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("analyst_queue")
    op.drop_table("analyst_action")


def downgrade() -> None:
    op.create_table(
        "analyst_action",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "analyst_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("capture_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["capture_id"], ["raw_capture.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_id"),
    )
