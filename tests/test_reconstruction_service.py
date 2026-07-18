import pytest
import numpy as np
import pandas as pd
from backend.services.reconstruction_service import ReconstructionService
from backend.twin.twin_state import TwinState

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
