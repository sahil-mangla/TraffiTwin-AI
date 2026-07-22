import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pytest
import torch

from backend.data.dataset import ReconstructionDataset


def _make_arrays(T=30, N=5, F=1):
    X = np.arange(T * N * F, dtype=np.float32).reshape(T, N, F)
    mask = np.ones((T, N), dtype=np.uint8)
    return X, mask


def test_len_matches_number_of_valid_windows():
    X, mask = _make_arrays(T=30)
    ds = ReconstructionDataset(X, mask, window_size=12, target_offset=1)
    # n_samples = T - window_size - target_offset + 1
    assert len(ds) == 30 - 12 - 1 + 1


def test_getitem_returns_correctly_shaped_tensors():
    X, mask = _make_arrays(T=30, N=5, F=2)
    ds = ReconstructionDataset(X, mask, window_size=12, target_offset=1)
    sample = ds[0]

    assert sample["input_window"].shape == (12, 5, 2)
    assert sample["mask_window"].shape == (12, 5)
    assert sample["target"].shape == (5, 2)
    assert sample["target_mask"].shape == (5,)
    assert isinstance(sample["input_window"], torch.Tensor)


def test_getitem_window_boundaries_are_correct():
    X, mask = _make_arrays(T=30, N=5, F=1)
    ds = ReconstructionDataset(X, mask, window_size=12, target_offset=1)

    sample = ds[0]
    np.testing.assert_array_equal(sample["input_window"].numpy(), X[0:12])
    np.testing.assert_array_equal(sample["target"].numpy(), X[12])

    last_idx = len(ds) - 1
    last_sample = ds[last_idx]
    np.testing.assert_array_equal(last_sample["target"].numpy(), X[-1])


def test_getitem_respects_target_offset():
    X, mask = _make_arrays(T=30, N=5, F=1)
    ds = ReconstructionDataset(X, mask, window_size=10, target_offset=3)
    sample = ds[0]
    # target at t_idx = w_end + target_offset - 1 = 10 + 3 - 1 = 12
    np.testing.assert_array_equal(sample["target"].numpy(), X[12])


def test_getitem_out_of_range_index_raises_index_error():
    X, mask = _make_arrays(T=30)
    ds = ReconstructionDataset(X, mask, window_size=12, target_offset=1)
    with pytest.raises(IndexError):
        ds[len(ds)]
    with pytest.raises(IndexError):
        ds[-1]


def test_constructor_rejects_mismatched_shapes():
    X, _ = _make_arrays(T=30, N=5)
    bad_mask = np.ones((30, 4), dtype=np.uint8)
    with pytest.raises(ValueError):
        ReconstructionDataset(X, bad_mask, window_size=12)


def test_constructor_rejects_non_3d_input():
    mask = np.ones((30, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        ReconstructionDataset(np.zeros((30, 5)), mask, window_size=12)


def test_constructor_rejects_too_small_window():
    X, mask = _make_arrays(T=5)
    with pytest.raises(ValueError):
        ReconstructionDataset(X, mask, window_size=12, target_offset=1)


def test_constructor_rejects_invalid_window_size_and_offset():
    X, mask = _make_arrays(T=30)
    with pytest.raises(ValueError):
        ReconstructionDataset(X, mask, window_size=0)
    with pytest.raises(ValueError):
        ReconstructionDataset(X, mask, window_size=12, target_offset=0)


def test_get_numpy_batch_matches_getitem_values():
    X, mask = _make_arrays(T=30, N=5, F=1)
    ds = ReconstructionDataset(X, mask, window_size=12, target_offset=1)

    tensor_sample = ds[3]
    numpy_sample = ds.get_numpy_batch(3)

    np.testing.assert_array_equal(tensor_sample["input_window"].numpy(), numpy_sample["input_window"])
    np.testing.assert_array_equal(tensor_sample["target"].numpy(), numpy_sample["target"])


def test_from_split_builds_equivalent_dataset():
    X, mask = _make_arrays(T=30)
    ds_direct = ReconstructionDataset(X, mask, window_size=12)
    ds_from_split = ReconstructionDataset.from_split(X, mask, window_size=12)

    assert len(ds_direct) == len(ds_from_split)
    np.testing.assert_array_equal(ds_direct[0]["input_window"].numpy(), ds_from_split[0]["input_window"].numpy())


def test_print_stats_does_not_raise(capsys):
    X, mask = _make_arrays(T=30)
    ds = ReconstructionDataset(X, mask, window_size=12)
    ds.print_stats()
    captured = capsys.readouterr()
    assert "ReconstructionDataset Summary" in captured.out
