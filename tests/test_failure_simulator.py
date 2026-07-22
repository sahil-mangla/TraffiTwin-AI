import numpy as np
import pytest

from backend.data.failure_simulator import FailureSimulator, FailureResult


@pytest.fixture
def clean_tensor():
    rng = np.random.default_rng(0)
    return rng.normal(loc=50.0, scale=10.0, size=(200, 10, 1)).astype(np.float32)


# ---------------------------------------------------------------------------
# MCAR
# ---------------------------------------------------------------------------

def test_simulate_mcar_produces_expected_missing_rate(clean_tensor):
    sim = FailureSimulator(random_seed=42)
    result = sim.simulate_mcar(clean_tensor, missing_rate=0.20)

    assert isinstance(result, FailureResult)
    assert result.failure_type == "mcar"
    # With T*N = 2000 samples, actual rate should land close to target.
    assert abs(result.actual_missing_rate - 0.20) < 0.05


def test_simulate_mcar_masks_all_features_at_failed_positions(clean_tensor):
    sim = FailureSimulator(random_seed=1)
    result = sim.simulate_mcar(clean_tensor, missing_rate=0.30)

    failed_t, failed_n = np.where(result.mask_matrix == 0)
    assert len(failed_t) > 0
    assert np.isnan(result.masked_data[failed_t, failed_n, :]).all()


def test_simulate_mcar_leaves_healthy_positions_unmodified(clean_tensor):
    sim = FailureSimulator(random_seed=1)
    result = sim.simulate_mcar(clean_tensor, missing_rate=0.30)

    healthy_t, healthy_n = np.where(result.mask_matrix == 1)
    np.testing.assert_array_equal(
        result.masked_data[healthy_t, healthy_n, :],
        clean_tensor[healthy_t, healthy_n, :],
    )


def test_simulate_mcar_is_reproducible_with_same_seed(clean_tensor):
    result_a = FailureSimulator(random_seed=7).simulate_mcar(clean_tensor, missing_rate=0.15)
    result_b = FailureSimulator(random_seed=7).simulate_mcar(clean_tensor, missing_rate=0.15)

    np.testing.assert_array_equal(result_a.mask_matrix, result_b.mask_matrix)


@pytest.mark.parametrize("bad_rate", [0.0, 1.0, -0.1, 1.5])
def test_simulate_mcar_rejects_out_of_range_missing_rate(clean_tensor, bad_rate):
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_mcar(clean_tensor, missing_rate=bad_rate)


def test_simulate_mcar_rejects_non_3d_input():
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_mcar(np.zeros((10, 5)), missing_rate=0.1)


def test_reset_rng_restores_original_sequence(clean_tensor):
    sim = FailureSimulator(random_seed=99)
    first = sim.simulate_mcar(clean_tensor, missing_rate=0.1)
    sim.reset_rng()
    second = sim.simulate_mcar(clean_tensor, missing_rate=0.1)
    np.testing.assert_array_equal(first.mask_matrix, second.mask_matrix)


# ---------------------------------------------------------------------------
# Block missing
# ---------------------------------------------------------------------------

def test_simulate_block_missing_masks_only_targeted_window(clean_tensor):
    sim = FailureSimulator(random_seed=0)
    result = sim.simulate_block_missing(clean_tensor, node_ids=[2, 5], start_time=10, duration=20)

    # Targeted nodes are masked within [10, 30).
    assert (result.mask_matrix[10:30, [2, 5]] == 0).all()
    assert np.isnan(result.masked_data[10:30, [2, 5], :]).all()

    # Everything outside the window/nodes remains healthy.
    assert (result.mask_matrix[:10, [2, 5]] == 1).all()
    assert (result.mask_matrix[30:, [2, 5]] == 1).all()
    other_nodes = [n for n in range(clean_tensor.shape[1]) if n not in (2, 5)]
    assert (result.mask_matrix[:, other_nodes] == 1).all()


def test_simulate_block_missing_accepts_single_int_node_id(clean_tensor):
    sim = FailureSimulator(random_seed=0)
    result = sim.simulate_block_missing(clean_tensor, node_ids=3, start_time=0, duration=5)
    assert (result.mask_matrix[0:5, 3] == 0).all()


def test_simulate_block_missing_clips_duration_to_array_bounds(clean_tensor):
    T = clean_tensor.shape[0]
    sim = FailureSimulator(random_seed=0)
    result = sim.simulate_block_missing(clean_tensor, node_ids=[0], start_time=T - 5, duration=50)

    event = result.failure_events[0]
    assert event["end_time"] == T
    assert event["duration"] == 5


def test_simulate_block_missing_rejects_empty_node_ids(clean_tensor):
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_block_missing(clean_tensor, node_ids=[], start_time=0, duration=5)


def test_simulate_block_missing_rejects_out_of_range_node_id(clean_tensor):
    N = clean_tensor.shape[1]
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_block_missing(clean_tensor, node_ids=[N], start_time=0, duration=5)


def test_simulate_block_missing_rejects_out_of_range_start_time(clean_tensor):
    T = clean_tensor.shape[0]
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_block_missing(clean_tensor, node_ids=[0], start_time=T, duration=5)


def test_simulate_block_missing_rejects_non_positive_duration(clean_tensor):
    sim = FailureSimulator(random_seed=0)
    with pytest.raises(ValueError):
        sim.simulate_block_missing(clean_tensor, node_ids=[0], start_time=0, duration=0)


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

def test_simulate_combined_merges_mcar_and_block_masks(clean_tensor):
    sim = FailureSimulator(random_seed=3)
    result = sim.simulate_combined(
        clean_tensor,
        mcar_rate=0.05,
        block_node_ids=[1],
        block_start=50,
        block_duration=10,
    )

    assert result.failure_type == "combined"
    # Block window must be fully masked regardless of MCAR draw.
    assert (result.mask_matrix[50:60, 1] == 0).all()
    assert len(result.failure_events) == 2


def test_simulate_combined_skips_block_when_node_ids_none(clean_tensor):
    sim = FailureSimulator(random_seed=3)
    result = sim.simulate_combined(clean_tensor, mcar_rate=0.05, block_node_ids=None)
    assert result.failure_type == "mcar"


def test_failure_result_summary_reports_counts(clean_tensor):
    sim = FailureSimulator(random_seed=0)
    result = sim.simulate_mcar(clean_tensor, missing_rate=0.1)
    summary = result.summary()
    assert "MCAR" in summary
    assert "Sensors" in summary
