"""Preserve raw measurement records alongside numeric columns.

Revision ID: 0002_source_payload
Revises: 0001_initial
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_source_payload"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("measurements", sa.Column("source_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("measurements", "source_payload")
