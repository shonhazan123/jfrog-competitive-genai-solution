"""delivery tables and chunk vector index

Revision ID: 0004_delivery_vector
Revises: 0003_adapter
Create Date: 2026-08-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "0004_delivery_vector"
down_revision: Union[str, None] = "0003_adapter"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("source", sa.Column("check_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("source", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source", sa.Column("covers", sa.JSON(), nullable=False, server_default="[]"))

    op.create_table(
        "user_visit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "digest_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("persona", sa.String(length=16), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "delivery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("digest_run_id", sa.Integer(), nullable=False),
        sa.Column("recipient", sa.String(length=256), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["digest_run_id"], ["digest_run.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chunk",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("prefix", sa.Text(), nullable=True),
        sa.Column("section_path", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("signal_type", sa.String(length=32), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reliability_grade", sa.String(length=1), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embed_model", sa.String(length=64), nullable=True),
        sa.Column("embed_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunk_content_hash", "chunk", ["content_hash"])

    op.execute(
        "ALTER TABLE chunk ADD COLUMN tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', coalesce(prefix,'') || ' ' || text)) STORED"
    )
    op.execute(
        "CREATE INDEX chunk_embedding_hnsw ON chunk "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute("CREATE INDEX chunk_tsv_gin ON chunk USING gin (tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chunk_tsv_gin")
    op.execute("DROP INDEX IF EXISTS chunk_embedding_hnsw")
    op.drop_index("ix_chunk_content_hash", table_name="chunk")

    op.drop_table("delivery")
    op.drop_table("digest_run")
    op.drop_table("user_visit")
    op.drop_table("chunk")

    op.drop_column("source", "covers")
    op.drop_column("source", "last_checked_at")
    op.drop_column("source", "check_count")
