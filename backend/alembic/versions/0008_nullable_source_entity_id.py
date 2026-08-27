"""nullable source.entity_id for synthetic agent research sources"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_nullable_source_entity_id"
down_revision: Union[str, None] = "0007_research_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("source", "entity_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("source", "entity_id", existing_type=sa.Integer(), nullable=False)
