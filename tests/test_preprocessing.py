import numpy as np
import pytest

from backend.data.preprocessing import ZScoreScaler, TimeSeriesSplitter, DataSplit


# ---------------------------------------------------------------------------
# ZScoreScaler
# ---------------------------------------------------------------------------

def test_fit_computes_mean_and_std_per_feature():
    rng = np.random.default_rng(0)
    X = rng.normal(loc=50.0, scale=10.0, size=(100, 5, 2)).astype(np.float32)

    scaler = ZScoreScaler()
    scaler.fit(X)

    assert scaler.mean_.shape == (1, 1, 2)
    assert scaler.std_.shape == (1, 1, 2)
    np.testing.assert_allclose(scaler.mean, np.nanmean(X, axis=(0, 1)), atol=1e-4)
    np.testing.assert_allclose(scaler.std, np.nanstd(X, axis=(0, 1)), atol=1e-4)


def test_fit_rejects_non_3d_input():
    scaler = ZScoreScaler()
    with pytest.raises(ValueError):
        scaler.fit(np.zeros((10, 5)))


def test_fit_ignores_nans_when_computing_statistics():
    X = np.array([[[1.0], [2.0]], [[np.nan], [4.0]], [[3.0], [np.nan]]], dtype=np.float32)
    scaler = ZScoreScaler()
    scaler.fit(X)

    assert not np.isnan(scaler.mean_).any()
    assert not np.isnan(scaler.std_).any()


def test_transform_round_trips_with_inverse_transform():
    rng = np.random.default_rng(1)
    X = rng.normal(loc=55.0, scale=12.0, size=(50, 3, 1)).astype(np.float32)

    scaler = ZScoreScaler().fit(X)
    X_norm = scaler.transform(X)
    X_recovered = scaler.inverse_transform(X_norm)

    np.testing.assert_allclose(X_recovered, X, atol=1e-2)


def test_transform_preserves_nan_positions():
    X = np.array([[[1.0], [np.nan]]], dtype=np.float32)
    scaler = ZScoreScaler().fit(X)
    X_norm = scaler.transform(X)
    assert np.isnan(X_norm[0, 1, 0])
    assert not np.isnan(X_norm[0, 0, 0])


def test_inverse_transform_handles_2d_single_step_array():
    rng = np.random.default_rng(2)
    X = rng.normal(loc=40.0, scale=5.0, size=(20, 4, 1)).astype(np.float32)
    scaler = ZScoreScaler().fit(X)

    single_step = X[0]  # (N, F)
    single_step_norm = (single_step - scaler.mean_[0]) / (scaler.std_[0] + scaler.eps)
    recovered = scaler.inverse_transform(single_step_norm.astype(np.float32))

    assert recovered.shape == single_step.shape
    np.testing.assert_allclose(recovered, single_step, atol=1e-2)


def test_transform_before_fit_raises_runtime_error():
    scaler = ZScoreScaler()
    with pytest.raises(RuntimeError):
        scaler.transform(np.zeros((10, 5, 1)))


def test_inverse_transform_before_fit_raises_runtime_error():
    scaler = ZScoreScaler()
    with pytest.raises(RuntimeError):
        scaler.inverse_transform(np.zeros((10, 5, 1)))


def test_mean_and_std_properties_require_fit():
    scaler = ZScoreScaler()
    with pytest.raises(RuntimeError):
        _ = scaler.mean
    with pytest.raises(RuntimeError):
        _ = scaler.std


def test_zero_variance_feature_does_not_divide_by_zero():
    # A constant feature has std=0; eps must prevent inf/nan.
    X = np.full((10, 3, 1), 42.0, dtype=np.float32)
    scaler = ZScoreScaler().fit(X)
    X_norm = scaler.transform(X)

    assert np.isfinite(X_norm).all()


# ---------------------------------------------------------------------------
# TimeSeriesSplitter
# ---------------------------------------------------------------------------

def test_split_ratios_must_sum_to_one():
    with pytest.raises(ValueError):
        TimeSeriesSplitter(train_ratio=0.5, val_ratio=0.2, test_ratio=0.2)


def test_split_produces_contiguous_non_overlapping_partitions():
    X = np.arange(100 * 3 * 1, dtype=np.float32).reshape(100, 3, 1)
    splitter = TimeSeriesSplitter(train_ratio=0.7, val_ratio=0.1, test_ratio=0.2)

    train, val, test = splitter.split(X)

    assert train.start_idx == 0
    assert train.end_idx == val.start_idx
    assert val.end_idx == test.start_idx
    assert test.end_idx == 100

    # No timestep is duplicated or skipped across partitions.
    total_timesteps = train.n_timesteps + val.n_timesteps + test.n_timesteps
    assert total_timesteps == 100

    np.testing.assert_array_equal(train.X, X[: train.end_idx])
    np.testing.assert_array_equal(val.X, X[train.end_idx : val.end_idx])
    np.testing.assert_array_equal(test.X, X[val.end_idx :])


def test_split_default_ratios_produce_expected_sizes():
    X = np.zeros((1000, 2, 1), dtype=np.float32)
    train, val, test = TimeSeriesSplitter().split(X)

    assert train.n_timesteps == 700
    assert val.n_timesteps == 100
    assert test.n_timesteps == 200


def test_split_rejects_non_3d_input():
    splitter = TimeSeriesSplitter()
    with pytest.raises(ValueError):
        splitter.split(np.zeros((10, 5)))


def test_split_masks_are_none_before_simulation():
    X = np.zeros((30, 2, 1), dtype=np.float32)
    train, val, test = TimeSeriesSplitter().split(X)
    assert train.mask is None
    assert val.mask is None
    assert test.mask is None


def test_data_split_n_timesteps_and_n_sensors_properties():
    split = DataSplit(X=np.zeros((15, 4, 2)), mask=None, name="train", start_idx=0, end_idx=15)
    assert split.n_timesteps == 15
    assert split.n_sensors == 4
