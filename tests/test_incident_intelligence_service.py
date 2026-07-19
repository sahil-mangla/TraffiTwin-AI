import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from backend.services.incident_intelligence_service import (
    EventDeduplicator,
    IncidentIntelligenceService,
)


def make_fake_twin(num_nodes=4, num_failures=1, num_reconstructed=0):
    """A minimal duck-typed stand-in for TwinService — only implements the
    surface IncidentIntelligenceService.build_incident_object actually uses,
    avoiding the cost of loading the real dataset/model in a unit test."""
    history = np.full((5, num_nodes), 50.0)
    history[-1, 0] = 45.0  # current reading for sensor 0 differs from history

    state = SimpleNamespace(
        num_nodes=num_nodes,
        history=history,
    )
    A = np.array([
        [0, 1, 0, 0],
        [1, 0, 1, 0],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
    ], dtype=float)
    stream = SimpleNamespace(get_adjacency_matrix=lambda: A)

    masks = {str(i): (i < num_failures) for i in range(num_nodes)}
    reconstructions = {str(i): 44.0 for i in range(num_reconstructed)}

    twin = SimpleNamespace(
        state=state,
        stream=stream,
        get_snapshot=lambda: {"masks": masks, "reconstructions": reconstructions},
        get_metrics=lambda: {"mae": 1.5, "rmse": 2.0},
    )
    return twin


# --- EventDeduplicator -------------------------------------------------

def test_deduplicator_flags_repeat_within_ttl():
    dedup = EventDeduplicator(ttl=120.0)
    assert dedup.is_duplicate("sensor_failure", 5) is False
    assert dedup.is_duplicate("sensor_failure", 5) is True


def test_deduplicator_treats_different_keys_independently():
    dedup = EventDeduplicator(ttl=120.0)
    assert dedup.is_duplicate("sensor_failure", 5) is False
    assert dedup.is_duplicate("sensor_failure", 6) is False
    assert dedup.is_duplicate("sensor_recovery", 5) is False


def test_deduplicator_expires_after_ttl(monkeypatch):
    import backend.services.incident_intelligence_service as mod
    fake_time = [1000.0]
    monkeypatch.setattr(mod.time, "time", lambda: fake_time[0])

    dedup = EventDeduplicator(ttl=10.0)
    assert dedup.is_duplicate("sensor_failure", 5) is False
    fake_time[0] += 11.0
    assert dedup.is_duplicate("sensor_failure", 5) is False


# --- build_incident_object ---------------------------------------------

def test_build_incident_object_computes_observability_and_status():
    service = IncidentIntelligenceService(gemini_service=AsyncMock())
    twin = make_fake_twin(num_nodes=4, num_failures=1, num_reconstructed=1)

    incident = service.build_incident_object(twin, "sensor_failure", sensor_id=0, duration=10)

    assert incident["sensor_id"] == 0
    assert incident["event_type"] == "sensor_failure"
    assert incident["failure_duration_minutes"] == 50.0  # duration * 5
    assert incident["active_failures"] == 1
    assert incident["reconstructed_nodes"] == 1
    # observability = (4 - 1 + 1) / 4 * 100
    assert incident["observability"] == pytest.approx(100.0)
    assert incident["network_status"] == "Operational"
    assert incident["reconstructed"] is True


def test_build_incident_object_without_sensor_id():
    service = IncidentIntelligenceService(gemini_service=AsyncMock())
    twin = make_fake_twin(num_nodes=4, num_failures=2, num_reconstructed=0)

    incident = service.build_incident_object(twin, "system_check")

    assert incident["sensor_id"] is None
    assert incident["reconstructed"] is False
    assert incident["affected_neighbors"] == []
    assert incident["neighbor_speed_change_pct"] == 0.0


# --- process_event: rate limiting / circuit breaker / dedup interplay --

def test_process_event_uses_gemini_when_all_gates_pass():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="AI-enriched summary")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    twin = make_fake_twin()

    result = asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))

    assert result == "AI-enriched summary"
    assert service.get_latest_summary_text() == "AI-enriched summary"
    assert len(service.get_latest_summaries()) == 1
    assert service.get_latest_summaries()[0]["is_ai"] is True


def test_process_event_falls_back_when_gemini_raises():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(side_effect=RuntimeError("boom"))
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    twin = make_fake_twin()

    result = asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))

    assert "Sensor 0" in result  # deterministic rule-based report
    assert service.get_latest_summaries()[0]["is_ai"] is False
    assert service.circuit_breaker.failure_count == 1


def test_process_event_skips_gemini_when_circuit_breaker_open():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="should not be used")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    service.circuit_breaker.max_failures = 1
    service.circuit_breaker.record_failure()
    assert service.circuit_breaker.is_open() is True

    twin = make_fake_twin()
    result = asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))

    fake_gemini.enrich_report.assert_not_called()
    assert "Sensor 0" in result


def test_process_event_skips_gemini_when_rate_limited():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="should not be used")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    service.rate_limiter.max_requests = 0  # exhaust immediately

    twin = make_fake_twin()
    result = asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))

    fake_gemini.enrich_report.assert_not_called()
    assert "Sensor 0" in result


def test_process_event_skips_gemini_for_duplicate_event():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="first call result")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    twin = make_fake_twin()

    asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))
    fake_gemini.enrich_report.reset_mock()

    # Same event_type + sensor_id within TTL should be deduplicated.
    result = asyncio.run(service.process_event(twin, "sensor_failure", sensor_id=0, duration=5))
    fake_gemini.enrich_report.assert_not_called()
    assert "Sensor 0" in result


def test_process_event_does_not_call_gemini_for_non_meaningful_event():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="should not be used")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    twin = make_fake_twin()

    result = asyncio.run(service.process_event(twin, "system_check"))
    fake_gemini.enrich_report.assert_not_called()
    assert "System check" in result or "System Event" in result


def test_summaries_cache_is_capped_at_20():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(side_effect=RuntimeError("offline"))
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    service.deduplicator.ttl = 0.0  # never dedup so every call is recorded

    twin = make_fake_twin()
    for i in range(25):
        asyncio.run(service.process_event(twin, "sensor_recovery", sensor_id=i % 4, duration=1))

    assert len(service.get_latest_summaries()) == 20


# --- generate_from_payload ----------------------------------------------

def test_generate_from_payload_uses_gemini_on_success():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="payload-based AI summary")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)

    result = asyncio.run(service.generate_from_payload({"sensor_id": 2, "event_type": "sensor_failure"}))
    assert result == "payload-based AI summary"
    assert service.get_latest_summary_text() == result


def test_generate_from_payload_falls_back_when_circuit_open():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(return_value="should not be used")
    service = IncidentIntelligenceService(gemini_service=fake_gemini)
    service.circuit_breaker.max_failures = 1
    service.circuit_breaker.record_failure()

    result = asyncio.run(service.generate_from_payload({"sensor_id": 2, "event_type": "sensor_failure"}))
    fake_gemini.enrich_report.assert_not_called()
    assert "Sensor 2" in result


def test_generate_from_payload_falls_back_on_gemini_error():
    fake_gemini = AsyncMock()
    fake_gemini.enrich_report = AsyncMock(side_effect=RuntimeError("boom"))
    service = IncidentIntelligenceService(gemini_service=fake_gemini)

    result = asyncio.run(service.generate_from_payload({"sensor_id": 2, "event_type": "sensor_failure"}))
    assert "Sensor 2" in result
    assert service.circuit_breaker.failure_count == 1


def test_clear_latest_summary():
    service = IncidentIntelligenceService(gemini_service=AsyncMock())
    service.latest_summary_text = "something"
    service.clear_latest_summary()
    assert service.get_latest_summary_text() is None
