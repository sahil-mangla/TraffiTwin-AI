"""
Integration tests that wire the REAL TwinService, ReconstructionService, and
IncidentIntelligenceService together, without any HTTP layer or fake/duck-typed
twin — only the Gemini network call is replaced with an AsyncMock, since that
is the one genuinely external dependency the codebase always stubs in tests
(see tests/test_incident_intelligence_service.py). Everything else — the
LightGBM checkpoint, the METR-LA stream, the rule-based reporter, rate
limiter, circuit breaker, and deduplicator — runs for real, exercising the
same object graph production uses.

Complements:
  - tests/test_twin_service.py (TwinService in isolation)
  - tests/test_incident_intelligence_service.py (IncidentIntelligenceService
    against a lightweight duck-typed twin)
  - tests/test_integration_flow.py (HTTP layer, with incident service faked)
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.services.incident_intelligence_service import IncidentIntelligenceService
from backend.services.twin_service import TwinService


@pytest.fixture(scope="module")
def twin():
    """Loading the dataset + LightGBM checkpoint is expensive; share one
    initialized TwinService across every test in this module."""
    service = TwinService()
    service.initialize()
    return service


@pytest.fixture
def incident_service():
    """A real IncidentIntelligenceService with only the Gemini network call
    stubbed out — the rate limiter, circuit breaker, deduplicator, and
    rule-based reporter are all the genuine production objects."""
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(side_effect=RuntimeError("no network in tests"))
    return IncidentIntelligenceService(gemini_service=fake_gemini)


def test_failure_reconstruction_and_incident_summary_chain(twin, incident_service):
    sensor_id = 15
    twin.inject_failure(sensor_id=sensor_id, duration=10)

    # Advancing the real TwinService triggers the real ReconstructionService
    # under the hood (TwinService.step -> reconstructor.reconstruct).
    twin.step(steps=1)
    assert str(sensor_id) in twin.state.reconstructions

    summary = asyncio.run(
        incident_service.process_event(twin, "sensor_failure", sensor_id=sensor_id, duration=10)
    )

    # Gemini always fails in this test (no real network access), so the
    # summary must be the deterministic rule-based report, and the circuit
    # breaker must have recorded the failed enrichment attempt.
    assert f"Sensor {sensor_id}" in summary
    assert "TraffiTwin successfully restored observability" in summary
    assert incident_service.circuit_breaker.failure_count == 1
    assert incident_service.get_latest_summaries()[0]["is_ai"] is False
    assert incident_service.get_latest_summary_text() == summary


def test_recovery_after_failure_heals_and_reports_recovery(twin, incident_service):
    sensor_id = 22
    twin.inject_failure(sensor_id=sensor_id, duration=1)

    # One step both reconstructs (while still failed) and then heals the
    # sensor, since duration=1 expires on the very next tick.
    twin.step(steps=1)
    assert bool(twin.state.masks[sensor_id]) is False  # healed

    summary = asyncio.run(
        incident_service.process_event(twin, "sensor_recovery", sensor_id=sensor_id)
    )

    assert f"Sensor {sensor_id} has recovered" in summary


def test_repeated_real_failures_open_the_circuit_breaker(twin, incident_service):
    # Distinct sensor IDs so the deduplicator treats each as a new event —
    # isolating circuit-breaker behavior from dedup behavior.
    for sensor_id in (30, 31, 32):
        twin.inject_failure(sensor_id=sensor_id, duration=5)
        twin.step(steps=1)
        asyncio.run(incident_service.process_event(twin, "sensor_failure", sensor_id=sensor_id, duration=5))

    assert incident_service.circuit_breaker.failure_count == 3
    assert incident_service.circuit_breaker.is_open() is True

    # A 4th real incident must skip Gemini entirely once the circuit is open.
    twin.inject_failure(sensor_id=33, duration=5)
    twin.step(steps=1)
    summary = asyncio.run(
        incident_service.process_event(twin, "sensor_failure", sensor_id=33, duration=5)
    )
    assert "Sensor 33" in summary
    assert incident_service.circuit_breaker.failure_count == 3  # unchanged — never attempted


def test_duplicate_real_event_is_not_reprocessed_by_gemini(twin, incident_service):
    sensor_id = 40
    twin.inject_failure(sensor_id=sensor_id, duration=5)
    twin.step(steps=1)

    asyncio.run(incident_service.process_event(twin, "sensor_failure", sensor_id=sensor_id, duration=5))
    failures_after_first = incident_service.circuit_breaker.failure_count

    # Same event_type + sensor_id within the dedup TTL must be suppressed
    # before ever reaching the (stubbed) Gemini call.
    asyncio.run(incident_service.process_event(twin, "sensor_failure", sensor_id=sensor_id, duration=5))
    assert incident_service.circuit_breaker.failure_count == failures_after_first


def test_multi_step_advance_reconstructs_and_then_heals_on_schedule(twin, incident_service):
    sensor_id = 50
    twin.inject_failure(sensor_id=sensor_id, duration=3)

    twin.step(steps=1)
    assert bool(twin.state.masks[sensor_id]) is True
    assert str(sensor_id) in twin.state.reconstructions

    twin.step(steps=2)  # duration elapses
    assert bool(twin.state.masks[sensor_id]) is False
    assert str(sensor_id) not in twin.state.reconstructions

    metrics = twin.get_metrics()
    assert metrics["total_failures_simulated"] >= 1
