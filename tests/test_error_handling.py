"""
Tests for the app-wide exception handlers in backend/api/app.py: the
normalized 422 shape for request validation errors, the normalized shape for
framework-level HTTP errors (e.g. unknown routes), and the catch-all 500
safety net for genuinely unexpected exceptions raised inside a route.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.api.routes import get_twin_service


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_unknown_route_returns_normalized_404(client):
    r = client.get("/this-route-does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error_code"] == "HTTPException"
    assert "detail" in body


def test_disallowed_method_returns_normalized_405(client):
    # /health only supports GET.
    r = client.post("/health")
    assert r.status_code == 405
    assert r.json()["error_code"] == "HTTPException"


def test_malformed_request_body_returns_normalized_422(client):
    # sensor_id/duration are required ints — send a string sensor_id instead.
    r = client.post("/simulate_failure", json={"sensor_id": "not-an-int", "duration": 5})
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "RequestValidationError"
    assert isinstance(body["detail"], list)
    assert any("sensor_id" in str(err.get("loc", "")) for err in body["detail"])


def test_missing_required_field_returns_normalized_422(client):
    r = client.post("/simulate_failure", json={"sensor_id": 5})  # duration missing
    assert r.status_code == 422
    assert r.json()["error_code"] == "RequestValidationError"


def test_unhandled_exception_in_a_route_returns_normalized_500(client):
    def _broken_twin_service():
        class _Boom:
            def get_snapshot(self):
                raise RuntimeError("simulated unexpected failure deep in a service")
        return _Boom()

    app.dependency_overrides[get_twin_service] = _broken_twin_service
    try:
        r = client.get("/snapshot")
    finally:
        app.dependency_overrides.pop(get_twin_service, None)

    assert r.status_code == 500
    body = r.json()
    assert body["error_code"] == "InternalServerError"
    # The client must never see the raw exception message/traceback.
    assert "simulated unexpected failure" not in r.text


def test_sensor_not_found_error_still_returns_404_alongside_new_handlers(client):
    r = client.post("/simulate_failure", json={"sensor_id": 999999, "duration": 5})
    assert r.status_code == 404
    assert r.json()["error_code"] == "SensorNotFoundError"
