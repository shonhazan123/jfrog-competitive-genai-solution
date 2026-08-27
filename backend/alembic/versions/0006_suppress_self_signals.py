"""suppress stale self (JFrog) signals

Revision ID: 0006_suppress_self_signals
Revises: 0005_why_it_matters
Create Date: 2026-08-27 16:00:00.000000

One-time data cleanup. JFrog's own positioning is authored config, never a card
(see jfrog_positions.yaml). Signals about a `kind='self'` entity were created by
the now-removed jfrog_homepage scrape before the self-suppression guard landed;
this deactivates them so they stop appearing as competitive cards. The removed
interpret pipeline no longer creates new self signals.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0006_suppress_self_signals"
down_revision: Union[str, None] = "0005_why_it_matters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE signal
        SET status = 'suppressed'
        WHERE status = 'active'
          AND entity_id IN (SELECT id FROM entity WHERE kind = 'self')
        """
    )


def downgrade() -> None:
    # Data-only cleanup; no structural change to reverse.
    pass
