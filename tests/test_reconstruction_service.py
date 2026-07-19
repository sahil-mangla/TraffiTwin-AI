import pytest
import numpy as np
import pandas as pd
from backend.services.reconstruction_service import ReconstructionService
from backend.twin.twin_state import TwinState


@pytest.fixture(scope="module")
def loaded_service():
    """Loading the LightGBM checkpoint is expensive; share one loaded
    ReconstructionService across the tests in this module."""
    rs = ReconstructionService()
    rs.load_model()
    return rs


def _make_state():
    state = TwinState(num_nodes=207, history_size=25)
    state.history = np.random.randn(25, 207)
    state.current_timestamp = pd.Timestamp("2020-01-01 00:00:00")
    return state


def test_reconstruction_service():
    rs = ReconstructionService()
    # It shouldn't load model automatically
    assert rs.model is None

    rs.load_model()
    assert rs.model is not None

    # Test reconstruct on a state with no failures
    state = TwinState(num_nodes=207, history_size=25)
    # Mock history and timestamps
    state.history = np.random.randn(25, 207)
    state.current_timestamp = pd.Timestamp("2020-01-01 00:00:00")

    A = np.random.randn(207, 207)
    reconstructions = rs.reconstruct(state, A)
    assert reconstructions == {}

    # Test reconstruct with failure
    state.inject_failure(sensor_id=5, duration=5)
    reconstructions = rs.reconstruct(state, A)
    # Should reconstruct value for sensor 5
    assert "5" in reconstructions
    assert isinstance(reconstructions["5"], float)


def test_reconstruct_raises_if_model_not_loaded():
    rs = ReconstructionService()
    state = _make_state()
    A = np.random.randn(207, 207)
    with pytest.raises(RuntimeError):
        rs.reconstruct(state, A)


def test_reconstruct_raises_without_current_timestamp(loaded_service):
    state = _make_state()
    state.current_timestamp = None
    state.inject_failure(sensor_id=3, duration=5)
    A = np.random.randn(207, 207)

    with pytest.raises(ValueError):
        loaded_service.reconstruct(state, A)


def test_reconstruct_handles_multiple_simultaneous_failures(loaded_service):
    state = _make_state()
    A = np.random.randn(207, 207)
    for sensor_id in (2, 8, 15):
        state.inject_failure(sensor_id=sensor_id, duration=5)

    reconstructions = loaded_service.reconstruct(state, A)

    assert set(reconstructions.keys()) == {"2", "8", "15"}
    for value in reconstructions.values():
        assert isinstance(value, float)


def test_load_model_raises_and_logs_on_missing_file():
    rs = ReconstructionService(model_path="does/not/exist.pkl")
    with pytest.raises(Exception):
        rs.load_model()
    assert rs.model is None


def test_reconstruct_returns_empty_dict_when_feature_engineering_fails(loaded_service, monkeypatch):
    state = _make_state()
    state.inject_failure(sensor_id=5, duration=5)
    A = np.random.randn(207, 207)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated feature engineering failure")

    monkeypatch.setattr(loaded_service.engineer, "transform", _boom)
    reconstructions = loaded_service.reconstruct(state, A)
    assert reconstructions == {}
