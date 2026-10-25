"""Initial database foundation.

Revision ID: 0001_initial
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "measurements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mast_id", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wind_speed", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("wind_direction_deg", sa.Float(), nullable=True),
        sa.Column("upstream_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("upstream_version", sa.String(length=128), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "mast_id", "timestamp", name="uq_measurements_mast_timestamp"
        ),
    )
    op.create_index(
        "ix_measurements_upstream_updated_at", "measurements", ["upstream_updated_at"]
    )
    op.create_table(
        "sync_states",
        sa.Column("stream", sa.String(length=128), primary_key=True),
        sa.Column("last_successful_updated_since", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_seen", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("sync_states")
    op.drop_index("ix_measurements_upstream_updated_at", table_name="measurements")
    op.drop_table("measurements")
