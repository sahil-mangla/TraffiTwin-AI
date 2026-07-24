from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.persistence.models import IncidentRow


class IncidentRepositoryProtocol(Protocol):
    async def save(self, entry: Dict[str, Any]) -> None: ...

    async def list_history(
        self,
        sensor_id: Optional[int] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]: ...

    async def prune_older_than(self, days: int) -> int: ...


class NullIncidentRepository:
    """No-op stand-in used whenever no real repository is injected (the
    default for IncidentIntelligenceService()). Keeps every existing test
    that constructs the service directly free of any DB dependency — zero
    connection attempts, zero behavior change."""

    async def save(self, entry: Dict[str, Any]) -> None:
        return

    async def list_history(
        self,
        sensor_id: Optional[int] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return []

    async def prune_older_than(self, days: int) -> int:
        return 0


def _row_to_dict(row: IncidentRow) -> Dict[str, Any]:
    return {
        "incident_id": row.incident_id,
        "timestamp": row.timestamp.isoformat(),
        "sensor_id": row.sensor_id,
        "event_type": row.event_type,
        "summary": row.summary,
        "is_ai": row.is_ai,
        "failure_duration_minutes": row.failure_duration_minutes,
        "reconstructed": row.reconstructed,
        "observability": row.observability,
        "mae": row.mae,
        "rmse": row.rmse,
        "active_failures": row.active_failures,
        "reconstructed_nodes": row.reconstructed_nodes,
        "network_status": row.network_status,
        "payload": row.payload,
    }


class PostgresIncidentRepository:
    """Real repository backed by the `incidents` table. `entry` is the exact
    dict shape produced by IncidentIntelligenceService.cache_report():
    {incident_id, timestamp, sensor_id, event_type, summary, payload, is_ai}
    — `payload` is itself the full build_incident_object() dict."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def save(self, entry: Dict[str, Any]) -> None:
        payload = entry["payload"]
        values = {
            "incident_id": entry["incident_id"],
            "timestamp": datetime.fromisoformat(entry["timestamp"]),
            "sensor_id": entry["sensor_id"],
            "event_type": entry["event_type"],
            "is_ai": entry["is_ai"],
            "summary": entry["summary"],
            "failure_duration_minutes": payload["failure_duration_minutes"],
            "reconstructed": payload["reconstructed"],
            "observability": payload["observability"],
            "mae": payload["mae"],
            "rmse": payload["rmse"],
            "active_failures": payload["active_failures"],
            "reconstructed_nodes": payload["reconstructed_nodes"],
            "network_status": payload["network_status"],
            "payload": payload,
        }
        # ON CONFLICT DO NOTHING: incident_id is second-granularity + sensor
        # keyed (see build_incident_object) and "system_check" events aren't
        # deduplicated upstream, so two rapid polls with no active failures
        # can legitimately collide — that's a harmless dropped duplicate,
        # not a bug to surface as an error.
        stmt = insert(IncidentRow).values(**values).on_conflict_do_nothing(index_elements=["incident_id"])
        async with self._session_factory() as session:
            await session.execute(stmt)
            await session.commit()

    async def list_history(
        self,
        sensor_id: Optional[int] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        stmt = select(IncidentRow).order_by(IncidentRow.timestamp.desc()).limit(limit)
        if sensor_id is not None:
            stmt = stmt.where(IncidentRow.sensor_id == sensor_id)
        if event_type is not None:
            stmt = stmt.where(IncidentRow.event_type == event_type)
        if since is not None:
            stmt = stmt.where(IncidentRow.timestamp >= since)

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [_row_to_dict(row) for row in rows]

    async def prune_older_than(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = delete(IncidentRow).where(IncidentRow.timestamp < cutoff)
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            await session.commit()
        return cast(CursorResult, result).rowcount or 0
