import pickle

import numpy as np
import pandas as pd
import pytest

from backend.data.loader import METRLADataLoader


def _write_speed_h5(path, T=50, N=4):
    timestamps = pd.date_range("2012-03-01", periods=T, freq="5min")
    df = pd.DataFrame(
        np.random.default_rng(0).normal(50, 5, size=(T, N)),
        index=timestamps,
        columns=[f"sensor_{i}" for i in range(N)],
    )
    df.to_hdf(path, key="df", mode="w")


def _write_adj_pkl(path, N=4, negative=False, with_nan=False):
    ids = [f"sensor_{i}" for i in range(N)]
    id_to_index = {sid: i for i, sid in enumerate(ids)}
    A = np.ones((N, N), dtype=np.float32) - np.eye(N, dtype=np.float32)
    if negative:
        A[0, 1] = -1.0
    if with_nan:
        A[0, 1] = np.nan
    with open(path, "wb") as f:
        pickle.dump((ids, id_to_index, A), f)


@pytest.fixture
def valid_data_dir(tmp_path):
    _write_speed_h5(tmp_path / "metr-la.h5")
    _write_adj_pkl(tmp_path / "adj_mx.pkl")
    return tmp_path


def test_load_succeeds_with_h5_and_pkl(valid_data_dir):
    loader = METRLADataLoader(valid_data_dir).load()
    X, A, timestamps = loader.get_arrays()

    assert X.shape == (50, 4, 1)
    assert A.shape == (4, 4)
    assert len(timestamps) == 50


def test_load_falls_back_to_npz_for_speed_data(tmp_path):
    T, N = 30, 3
    np.savez(
        tmp_path / "metr-la.npz",
        data=np.random.default_rng(0).normal(50, 5, size=(T, N)),
        sensor_ids=[f"s{i}" for i in range(N)],
    )
    _write_adj_pkl(tmp_path / "adj_mx.pkl", N=N)

    loader = METRLADataLoader(tmp_path).load()
    X, A, timestamps = loader.get_arrays()

    assert X.shape == (T, N, 1)
    assert len(timestamps) == T


def test_load_falls_back_to_npy_for_adjacency(tmp_path):
    N = 3
    _write_speed_h5(tmp_path / "metr-la.h5", N=N)
    A = np.ones((N, N), dtype=np.float32)
    np.save(tmp_path / "adj_mx.npy", A)

    loader = METRLADataLoader(tmp_path).load()
    _, A_loaded, _ = loader.get_arrays()
    assert A_loaded.shape == (N, N)


def test_load_raises_file_not_found_when_speed_file_missing(tmp_path):
    _write_adj_pkl(tmp_path / "adj_mx.pkl")
    loader = METRLADataLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_load_raises_file_not_found_when_adjacency_missing(tmp_path):
    _write_speed_h5(tmp_path / "metr-la.h5")
    loader = METRLADataLoader(tmp_path)
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_load_raises_value_error_on_adjacency_shape_mismatch(tmp_path):
    _write_speed_h5(tmp_path / "metr-la.h5", N=4)
    # Adjacency built for a different number of sensors.
    _write_adj_pkl(tmp_path / "adj_mx.pkl", N=6)

    loader = METRLADataLoader(tmp_path)
    with pytest.raises(ValueError):
        loader.load()


def test_load_raises_value_error_on_negative_adjacency_weights(tmp_path):
    _write_speed_h5(tmp_path / "metr-la.h5", N=4)
    _write_adj_pkl(tmp_path / "adj_mx.pkl", N=4, negative=True)

    loader = METRLADataLoader(tmp_path)
    with pytest.raises(ValueError):
        loader.load()


def test_load_replaces_nan_adjacency_weights_with_zero(tmp_path):
    _write_speed_h5(tmp_path / "metr-la.h5", N=4)
    _write_adj_pkl(tmp_path / "adj_mx.pkl", N=4, with_nan=True)

    loader = METRLADataLoader(tmp_path).load()
    _, A, _ = loader.get_arrays()
    assert not np.isnan(A).any()
    assert A[0, 1] == 0.0


def test_load_rejects_unsupported_speed_file_format(tmp_path):
    (tmp_path / "metr-la.csv").write_text("not a real dataset")
    _write_adj_pkl(tmp_path / "adj_mx.pkl")

    loader = METRLADataLoader(tmp_path, speed_filename="metr-la.csv")
    with pytest.raises(ValueError):
        loader.load()


def test_get_arrays_before_load_raises_runtime_error(tmp_path):
    loader = METRLADataLoader(tmp_path)
    with pytest.raises(RuntimeError):
        loader.get_arrays()


def test_print_stats_before_load_raises_runtime_error(tmp_path):
    loader = METRLADataLoader(tmp_path)
    with pytest.raises(RuntimeError):
        loader.print_stats()


def test_print_stats_after_load_does_not_raise(valid_data_dir, capsys):
    loader = METRLADataLoader(valid_data_dir).load()
    loader.print_stats()
    captured = capsys.readouterr()
    assert "METR-LA Dataset Statistics" in captured.out
