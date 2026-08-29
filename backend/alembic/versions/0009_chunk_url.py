"""add chunk.url and backfill origin urls from the capture chain"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_chunk_url"
down_revision: Union[str, None] = "0008_nullable_source_entity_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chunk", sa.Column("url", sa.Text(), nullable=True))

    # Backfill existing chunks with the origin URL captured at collection time.
    # signals: chunk.record_id -> signal_evidence.signal_id -> raw_capture.blob_path
    op.execute(
        """
        UPDATE chunk c
        SET url = sub.blob_path
        FROM (
            SELECT se.signal_id AS record_id, MIN(rc.blob_path) AS blob_path
            FROM signal_evidence se
            JOIN raw_capture rc ON rc.id = se.capture_id
            WHERE rc.blob_path LIKE 'http%'
            GROUP BY se.signal_id
        ) sub
        WHERE c.record_type = 'signal'
          AND c.record_id = sub.record_id
          AND c.url IS NULL
        """
    )
    # claims: chunk.record_id -> evidence.claim_id -> raw_capture.blob_path
    op.execute(
        """
        UPDATE chunk c
        SET url = sub.blob_path
        FROM (
            SELECT e.claim_id AS record_id, MIN(rc.blob_path) AS blob_path
            FROM evidence e
            JOIN raw_capture rc ON rc.id = e.capture_id
            WHERE rc.blob_path LIKE 'http%'
            GROUP BY e.claim_id
        ) sub
        WHERE c.record_type = 'claim'
          AND c.record_id = sub.record_id
          AND c.url IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("chunk", "url")
