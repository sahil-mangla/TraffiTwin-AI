import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.persistence.db import get_engine
from backend.persistence.incident_repository import PostgresIncidentRepository
from backend.persistence.models import IncidentRow


def make_entry(incident_id: str, sensor_id=1, event_type="sensor_failure", is_ai=False, timestamp=None):
    ts = timestamp or datetime.now(timezone.utc)
    return {
        "incident_id": incident_id,
        "timestamp": ts.isoformat(),
        "sensor_id": sensor_id,
        "event_type": event_type,
        "summary": f"summary for {incident_id}",
        "is_ai": is_ai,
        "payload": {
            "incident_id": incident_id,
            "timestamp": ts.isoformat(),
            "sensor_id": sensor_id,
            "event_type": event_type,
            "failure_duration_minutes": 25.0,
            "reconstructed": True,
            "observability": 92.5,
            "mae": 1.2,
            "rmse": 2.3,
            "active_failures": 1,
            "reconstructed_nodes": 1,
            "affected_neighbors": [2, 3],
            "neighbor_speed_change_pct": -5.0,
            "network_status": "Degraded",
        },
    }


@pytest.fixture(scope="module")
def session_factory():
    # Exercises the actual migration file (not Base.metadata.create_all()),
    # so drift between migrations/versions/ and models.py is caught here.
    # Deliberately does NOT downgrade afterward — tests/test_routes.py (and
    # CI's single upfront `alembic upgrade head`, see ci.yml) depend on the
    # `incidents` table still existing for the rest of the pytest session.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    yield factory


@pytest.fixture(autouse=True)
def clean_table(session_factory):
    async def _clean():
        async with session_factory() as session:
            await session.execute(IncidentRow.__table__.delete())
            await session.commit()

    asyncio.run(_clean())
    yield


@pytest.fixture
def repo(session_factory):
    return PostgresIncidentRepository(session_factory)


def test_save_and_list_history_round_trip(repo):
    asyncio.run(repo.save(make_entry("inc-1000-1")))

    rows = asyncio.run(repo.list_history())
    assert len(rows) == 1
    row = rows[0]
    assert row["incident_id"] == "inc-1000-1"
    assert row["sensor_id"] == 1
    assert row["event_type"] == "sensor_failure"
    assert row["is_ai"] is False
    assert row["observability"] == 92.5
    assert row["payload"]["affected_neighbors"] == [2, 3]


def test_save_duplicate_incident_id_does_not_raise(repo):
    asyncio.run(repo.save(make_entry("inc-dup-1")))
    asyncio.run(repo.save(make_entry("inc-dup-1")))  # same incident_id, must not raise

    rows = asyncio.run(repo.list_history())
    assert len(rows) == 1


def test_list_history_filters_by_sensor_id(repo):
    asyncio.run(repo.save(make_entry("inc-a", sensor_id=1)))
    asyncio.run(repo.save(make_entry("inc-b", sensor_id=2)))

    rows = asyncio.run(repo.list_history(sensor_id=2))
    assert len(rows) == 1
    assert rows[0]["incident_id"] == "inc-b"


def test_list_history_filters_by_event_type(repo):
    asyncio.run(repo.save(make_entry("inc-c", event_type="sensor_failure")))
    asyncio.run(repo.save(make_entry("inc-d", event_type="system_check")))

    rows = asyncio.run(repo.list_history(event_type="system_check"))
    assert len(rows) == 1
    assert rows[0]["incident_id"] == "inc-d"


def test_list_history_respects_limit(repo):
    for i in range(5):
        asyncio.run(repo.save(make_entry(f"inc-limit-{i}")))

    rows = asyncio.run(repo.list_history(limit=2))
    assert len(rows) == 2


def test_list_history_filters_by_since(repo):
    now = datetime.now(timezone.utc)
    asyncio.run(repo.save(make_entry("inc-old", timestamp=now - timedelta(days=10))))
    asyncio.run(repo.save(make_entry("inc-new", timestamp=now)))

    rows = asyncio.run(repo.list_history(since=now - timedelta(days=1)))
    assert len(rows) == 1
    assert rows[0]["incident_id"] == "inc-new"


def test_prune_older_than_deletes_only_stale_rows(repo):
    now = datetime.now(timezone.utc)
    asyncio.run(repo.save(make_entry("inc-stale", timestamp=now - timedelta(days=20))))
    asyncio.run(repo.save(make_entry("inc-fresh", timestamp=now)))

    deleted = asyncio.run(repo.prune_older_than(14))
    assert deleted == 1

    rows = asyncio.run(repo.list_history())
    assert len(rows) == 1
    assert rows[0]["incident_id"] == "inc-fresh"
