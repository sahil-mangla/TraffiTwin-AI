import pytest
import numpy as np
import pandas as pd
from backend.twin.stream_simulator import StreamSimulator

def test_stream_simulator():
    sim = StreamSimulator()
    # It shouldn't load data automatically
    assert sim.X is None
    
    sim.load_data()
    assert sim.X is not None
    assert sim.A is not None
    assert sim.timestamps is not None
    assert sim.total_steps == len(sim.timestamps)
    assert sim.get_num_nodes() == sim.X.shape[1]

    # Test stepping
    readings, timestamp = sim.step()
    assert readings.shape == (sim.get_num_nodes(),)
    assert isinstance(timestamp, pd.Timestamp)
    assert sim.current_step == 0

    # Test get adjacency matrix
    A = sim.get_adjacency_matrix()
    assert isinstance(A, np.ndarray)
