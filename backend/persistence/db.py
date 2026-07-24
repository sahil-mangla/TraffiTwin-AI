from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import settings

# Lazily initialized so importing this module (or constructing a service
# that depends on it) never opens a DB connection at import time — mirrors
# the app's existing "services only initialize on startup" pattern
# (backend/api/app.py's lifespan).
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # NullPool: asyncpg connections are bound to the event loop that
        # created them. This app's tests follow the existing repo
        # convention of wrapping each async call in its own asyncio.run()
        # (see tests/test_incident_intelligence_service.py), which spins up
        # a fresh event loop per call — a pooled connection reused across
        # those loops raises "Future attached to a different loop". NullPool
        # opens a new connection per checkout instead of retaining one.
        _engine = create_async_engine(settings.database_url.get_secret_value(), poolclass=NullPool)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
