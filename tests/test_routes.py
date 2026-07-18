import pytest
from fastapi.testclient import TestClient
from backend.api.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

def test_health_route(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "1.0.0"}


def test_snapshot_route(client):
    r = client.get("/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "current_time" in data
    assert "readings" in data
    assert "masks" in data
    assert "reconstructions" in data


def test_graph_route(client):
    r = client.get("/graph")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0


def test_state_route(client):
    r = client.get("/state")
    assert r.status_code == 200
    data = r.json()
    assert "snapshot" in data
    assert "metrics" in data
    assert "system_health" in data


def test_metrics_route(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "current_time" in data
    assert "mae" in data
    assert "rmse" in data


def test_simulate_failure_success(client):
    # Valid sensor ID and duration
    r = client.post("/simulate_failure", json={"sensor_id": 10, "duration": 5})
    assert r.status_code == 200
    assert r.json()["status"] == "success"


def test_simulate_failure_invalid_sensor(client):
    # Invalid sensor ID
    r = client.post("/simulate_failure", json={"sensor_id": 9999, "duration": 5})
    assert r.status_code == 404
    assert r.json()["error_code"] == "SensorNotFoundError"


def test_simulate_failure_invalid_duration(client):
    # Invalid duration <= 0
    r = client.post("/simulate_failure", json={"sensor_id": 10, "duration": 0})
    assert r.status_code == 422
    assert r.json()["error_code"] == "InvalidSimulationStepError"


def test_step_simulation_success(client):
    r = client.post("/step", json={"steps": 2})
    assert r.status_code == 200
    assert "current_time" in r.json()


def test_step_simulation_invalid_steps(client):
    r = client.post("/step", json={"steps": 0})
    assert r.status_code == 422
    assert r.json()["error_code"] == "InvalidSimulationStepError"
