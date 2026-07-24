from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Float, Index, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class IncidentRow(Base):
    """Durable record of an incident summary — mirrors the shape produced by
    IncidentIntelligenceService.cache_report() plus the nested
    build_incident_object() payload, kept verbatim in `payload` as a
    durability hedge against that function gaining fields later without a
    migration."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    sensor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    failure_duration_minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reconstructed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mae: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rmse: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    active_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconstructed_nodes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    network_status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_incidents_timestamp", timestamp.desc()),
        Index("ix_incidents_sensor_id", "sensor_id", postgresql_where=sensor_id.isnot(None)),
        Index("ix_incidents_event_type", "event_type"),
    )
