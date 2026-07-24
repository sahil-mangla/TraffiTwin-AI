"""
prune_incidents.py — Incident Retention Cleanup
================================================
Deletes incident rows older than settings.incident_retention_days (default
14) from the `incidents` table. Run on a schedule (see
.github/workflows/prune-incidents.yml) rather than opportunistically inside
the request path — keeps retention visible and auditable in the Actions log
instead of implicit delete-on-write logic.

Usage
-----
    DATABASE_URL=postgresql+asyncpg://... python scripts/prune_incidents.py
"""

import asyncio
import sys
from pathlib import Path

# Allow running as `python scripts/prune_incidents.py` from repo root —
# mirrors the existing convention in scripts/validate_pipeline.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.persistence.db import dispose_engine, get_session_factory
from backend.persistence.incident_repository import PostgresIncidentRepository


async def main() -> None:
    repository = PostgresIncidentRepository(get_session_factory())
    deleted = await repository.prune_older_than(settings.incident_retention_days)
    print(f"Pruned {deleted} incident row(s) older than {settings.incident_retention_days} days.")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
