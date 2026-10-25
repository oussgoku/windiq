from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from windiq.database import Base


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint("mast_id", "timestamp", name="uq_measurements_mast_timestamp"),
        Index("ix_measurements_upstream_updated_at", "upstream_updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mast_id: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    upstream_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    upstream_version: Mapped[str] = mapped_column(String(128), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    source_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSON, nullable=True
    )


class SyncState(Base):
    __tablename__ = "sync_states"

    stream: Mapped[str] = mapped_column(String(128), primary_key=True)
    last_successful_updated_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    records_seen: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    records_inserted: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    records_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
