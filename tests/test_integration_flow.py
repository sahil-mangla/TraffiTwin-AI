"""
End-to-end integration tests that exercise the full HTTP stack — TwinService,
ReconstructionService, MetricsService, and IncidentIntelligenceService wired
together exactly as they are in production — rather than unit-testing any one
service in isolation. Complements tests/test_routes.py (which checks each
route independently) by chaining requests and asserting the state actually
changes as a result of prior requests.

The incident service is swapped for a fake with no real Gemini/network calls
so the AI-enrichment path stays deterministic and offline in CI.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.routes import get_incident_service


class FakeIncidentService:
    """Minimal stand-in matching the interface routes.py actually depends on,
    without touching the real Gemini SDK or network."""

    def __init__(self):
        self.latest_summary_text = None
        self._summaries = []

    def get_latest_summary_text(self):
        return self.latest_summary_text

    def get_latest_summaries(self):
        return self._summaries

    def clear_latest_summary(self):
        self.latest_summary_text = None

    async def generate_from_payload(self, payload):
        self.latest_summary_text = f"fake summary for sensor {payload.get('sensor_id')}"
        return self.latest_summary_text

    async def process_event(self, twin, event_type, sensor_id=None, duration=None):
        self.latest_summary_text = f"fake summary: {event_type} sensor={sensor_id}"
        return self.latest_summary_text


@pytest.fixture(scope="module")
def client():
    fake_incident_service = FakeIncidentService()
    # Return the SAME instance on every call — FastAPI resolves dependency
    # overrides fresh per request, so a lambda that instantiates a new
    # FakeIncidentService() each time would silently lose state (e.g. a
    # summary set by one request would never be visible to the next).
    app.dependency_overrides[get_incident_service] = lambda: fake_incident_service
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_incident_service, None)


def test_full_failure_and_recovery_flow_updates_state(client):
    # 1. Baseline: no failures.
    baseline = client.get("/state").json()
    baseline_active_failures = sum(1 for v in baseline["snapshot"]["masks"].values() if v)

    # 2. Inject a failure on a sensor known to exist (graph confirms count).
    graph = client.get("/graph").json()
    num_sensors = len(graph["nodes"])
    assert num_sensors > 20
    sensor_id = 20

    r = client.post("/simulate_failure", json={"sensor_id": sensor_id, "duration": 5})
    assert r.status_code == 200

    # 3. Advance the simulation so reconstruction actually runs for that sensor.
    r = client.post("/step", json={"steps": 1})
    assert r.status_code == 200

    # 4. State must now reflect the failure and, typically, a reconstruction.
    state_after = client.get("/state").json()
    masks_after = state_after["snapshot"]["masks"]
    assert masks_after[str(sensor_id)] is True

    active_failures_after = sum(1 for v in masks_after.values() if v)
    assert active_failures_after == baseline_active_failures + 1

    # 5. Metrics endpoint must be consistent with /state's embedded metrics.
    metrics = client.get("/metrics").json()
    assert metrics["current_time"] == state_after["snapshot"]["current_time"]
    assert metrics["total_failures_simulated"] >= 1

    # 6. Advance until the failure duration elapses; mask should clear.
    client.post("/step", json={"steps": 5})
    state_final = client.get("/state").json()
    assert state_final["snapshot"]["masks"][str(sensor_id)] is False


def test_simulate_failure_clears_previous_incident_summary(client):
    graph = client.get("/graph").json()
    sensor_id = min(15, len(graph["nodes"]) - 1)

    # Seed a summary via the fake incident service.
    r = client.post("/generate-incident-summary", json={
        "sensor_id": sensor_id,
        "event_type": "sensor_failure",
        "failure_duration_minutes": 25.0,
        "reconstructed": True,
        "observability": 97.0,
        "mae": 1.0,
        "rmse": 1.5,
        "active_failures": 1,
        "reconstructed_nodes": 1,
        "affected_neighbors": [1, 2],
        "neighbor_speed_change_pct": -3.0,
        "network_status": "Operational",
    })
    assert r.status_code == 200
    assert r.json()["summary"].startswith("fake summary")

    state = client.get("/state").json()
    assert state["latest_incident_summary"] is not None

    # A new failure injection should clear the stale summary (routes.py calls
    # incident.clear_latest_summary() on /simulate_failure).
    client.post("/simulate_failure", json={"sensor_id": sensor_id, "duration": 3})
    state_after = client.get("/state").json()
    assert state_after["latest_incident_summary"] is None


def test_analyze_current_state_reports_active_failure(client):
    graph = client.get("/graph").json()
    sensor_id = min(30, len(graph["nodes"]) - 1)

    client.post("/simulate_failure", json={"sensor_id": sensor_id, "duration": 5})

    # The route reports the FIRST currently-failed sensor it finds, which may
    # not be the one just injected if an earlier test's failure is still
    # active on the shared module-scoped client/state.
    snapshot = client.get("/snapshot").json()
    expected_sensor_id = next(int(sid) for sid, failed in snapshot["masks"].items() if failed)

    r = client.post("/analyze-current-state", json={})
    assert r.status_code == 200
    assert f"sensor_failure sensor={expected_sensor_id}" in r.json()["summary"]


def test_incident_summaries_route_reflects_fake_service_state(client):
    r = client.get("/incident-summaries")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
