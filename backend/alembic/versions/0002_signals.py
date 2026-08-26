"""signals and analyst queue

Revision ID: 0002_signals
Revises: 711aa9f5dcf3
Create Date: 2026-08-26 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_signals"
down_revision: Union[str, None] = "711aa9f5dcf3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    op.create_table(
        "signal",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("subject_entity_id", sa.Integer(), nullable=True),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("headline", sa.String(length=256), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capability_tags", sa.JSON(), nullable=False),
        sa.Column("cluster_key", sa.String(length=128), nullable=False),
        sa.Column("corroboration_count", sa.Integer(), nullable=False),
        sa.Column("score_sales", sa.Float(), nullable=False),
        sa.Column("score_product", sa.Float(), nullable=False),
        sa.Column("score_exec", sa.Float(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("so_what_sales", sa.Text(), nullable=True),
        sa.Column("so_what_product", sa.Text(), nullable=True),
        sa.Column("so_what_exec", sa.Text(), nullable=True),
        sa.Column("handling", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entity.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"]),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entity.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signal_cluster_key"), "signal", ["cluster_key"], unique=False)
    op.create_index(op.f("ix_signal_occurred_at"), "signal", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_signal_signal_type"), "signal", ["signal_type"], unique=False)
    op.create_table(
        "signal_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.Integer(), nullable=False),
        sa.Column("capture_id", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("quote_offset", sa.Integer(), nullable=False),
        sa.Column("match_method", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["capture_id"], ["raw_capture.id"]),
        sa.ForeignKeyConstraint(["signal_id"], ["signal.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("raw_capture", sa.Column("external_id", sa.String(length=256), nullable=True))
    op.create_index(op.f("ix_raw_capture_external_id"), "raw_capture", ["external_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_raw_capture_external_id"), table_name="raw_capture")
    op.drop_column("raw_capture", "external_id")
    op.drop_table("signal_evidence")
    op.drop_index(op.f("ix_signal_signal_type"), table_name="signal")
    op.drop_index(op.f("ix_signal_occurred_at"), table_name="signal")
    op.drop_index(op.f("ix_signal_cluster_key"), table_name="signal")
    op.drop_table("signal")
    op.drop_table("analyst_queue")
    op.drop_table("analyst_action")
