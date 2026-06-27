"""
dataset.py — Sliding-Window Reconstruction Dataset
=====================================================
Wraps a (T, N, F) traffic tensor and its corresponding failure mask into
a PyTorch Dataset of sliding windows ready for model training.

Window structure (window_size = 12 steps = 60 minutes at 5-min intervals)
--------------------------------------------------------------------------

    t-11  t-10  ...  t-1   t          ← historical context window
    |________________________|  →  target state at timestep t
    input_window (12, N, F)          target (N, F)
    mask_window  (12, N)

At each sample index i the dataset yields:
    {
        "input_window" : Tensor (window_size, N, F)   — possibly NaN at failed entries
        "mask_window"  : Tensor (window_size, N)      — 1=healthy, 0=failed
        "target"       : Tensor (N, F)                — clean ground truth at t=i+window_size
        "target_mask"  : Tensor (N,)                  — mask at the target step
    }

Usage
-----
    from torch.utils.data import DataLoader
    ds = ReconstructionDataset(X_norm, mask, window_size=12)
    loader = DataLoader(ds, batch_size=64, shuffle=True)
"""

import logging
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Optional PyTorch import — graceful degradation for numpy-only environments
try:
    import torch
    from torch import Tensor
    from torch.utils.data import Dataset as TorchDataset

    _TORCH_AVAILABLE = True

    class ReconstructionDataset(TorchDataset):
        """
        PyTorch sliding-window dataset for traffic state reconstruction.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)
            Normalised traffic tensor.  NaN values indicate masked positions.
        mask : np.ndarray, shape (T, N), dtype uint8 | bool
            Binary failure mask (1=healthy, 0=failed).
            Must have the same T and N as ``X``.
        window_size : int
            Number of historical timesteps fed as model input.
            Default: 12  (60 minutes at 5-min intervals).
        target_offset : int
            How many steps ahead of the window end to predict.
            Default: 1  (predict the very next step).

        Attributes
        ----------
        n_samples : int
            Total number of valid windows in this dataset.
        n_sensors : int
            Number of sensor nodes N.
        n_features : int
            Number of feature channels F.

        Raises
        ------
        ValueError
            If array shapes are inconsistent or window_size is invalid.
        """

        def __init__(
            self,
            X: np.ndarray,
            mask: np.ndarray,
            window_size: int = 12,
            target_offset: int = 1,
        ) -> None:
            super().__init__()
            self._validate(X, mask, window_size, target_offset)

            self.X = X.astype(np.float32)
            self.mask = mask.astype(np.float32)
            self.window_size = window_size
            self.target_offset = target_offset

            T = X.shape[0]
            # First valid window starts at index `window_size - 1`
            # Last valid target is at index `T - target_offset`
            self.n_samples: int = T - window_size - target_offset + 1
            self.n_sensors: int = X.shape[1]
            self.n_features: int = X.shape[2]

            if self.n_samples <= 0:
                raise ValueError(
                    f"No valid samples: T={T} is too small for "
                    f"window_size={window_size} + target_offset={target_offset}."
                )

            logger.info(
                "ReconstructionDataset: %d samples | N=%d sensors | F=%d features | "
                "window=%d steps",
                self.n_samples, self.n_sensors, self.n_features, self.window_size,
            )

        # ------------------------------------------------------------------
        # PyTorch Dataset interface
        # ------------------------------------------------------------------

        def __len__(self) -> int:
            return self.n_samples

        def __getitem__(self, idx: int) -> Dict[str, Tensor]:
            """
            Retrieve a single sliding-window sample.

            Parameters
            ----------
            idx : int
                Sample index in [0, n_samples).

            Returns
            -------
            dict with keys:
                ``input_window`` : Tensor (window_size, N, F)
                ``mask_window``  : Tensor (window_size, N)
                ``target``       : Tensor (N, F)
                ``target_mask``  : Tensor (N,)
            """
            if idx < 0 or idx >= self.n_samples:
                raise IndexError(
                    f"Index {idx} out of range [0, {self.n_samples})."
                )

            # Window slice: [idx, idx + window_size)
            w_start = idx
            w_end   = idx + self.window_size
            # Target timestep
            t_idx   = w_end + self.target_offset - 1

            input_window = self.X[w_start:w_end]          # (window_size, N, F)
            mask_window  = self.mask[w_start:w_end]       # (window_size, N)
            target       = self.X[t_idx]                  # (N, F)
            target_mask  = self.mask[t_idx]               # (N,)

            return {
                "input_window": torch.from_numpy(input_window),
                "mask_window":  torch.from_numpy(mask_window),
                "target":       torch.from_numpy(target),
                "target_mask":  torch.from_numpy(target_mask),
            }

        # ------------------------------------------------------------------
        # Convenience
        # ------------------------------------------------------------------

        def get_numpy_batch(self, idx: int) -> Dict[str, np.ndarray]:
            """
            Return a single sample as NumPy arrays (no PyTorch dependency).
            Useful for LightGBM / sklearn pipelines.
            """
            w_start = idx
            w_end   = idx + self.window_size
            t_idx   = w_end + self.target_offset - 1

            return {
                "input_window": self.X[w_start:w_end],
                "mask_window":  self.mask[w_start:w_end],
                "target":       self.X[t_idx],
                "target_mask":  self.mask[t_idx],
            }

        def print_stats(self) -> None:
            """Print dataset summary to stdout."""
            T = self.X.shape[0]
            n_missing = int(np.isnan(self.X).sum())
            print("\nReconstructionDataset Summary")
            print("-" * 40)
            print(f"  Total timesteps  : {T:,}")
            print(f"  Window size      : {self.window_size} steps ({self.window_size * 5} min)")
            print(f"  Target offset    : {self.target_offset} step(s)")
            print(f"  Samples          : {self.n_samples:,}")
            print(f"  Sensors (N)      : {self.n_sensors}")
            print(f"  Features (F)     : {self.n_features}")
            print(f"  Missing entries  : {n_missing:,} ({100*n_missing/self.X.size:.2f}%)")
            print("-" * 40)

        # ------------------------------------------------------------------
        # Static helpers
        # ------------------------------------------------------------------

        @staticmethod
        def _validate(
            X: np.ndarray,
            mask: np.ndarray,
            window_size: int,
            target_offset: int,
        ) -> None:
            if X.ndim != 3:
                raise ValueError(
                    f"X must be 3-D (T, N, F), got shape {X.shape}."
                )
            if mask.ndim != 2:
                raise ValueError(
                    f"mask must be 2-D (T, N), got shape {mask.shape}."
                )
            if X.shape[0] != mask.shape[0] or X.shape[1] != mask.shape[1]:
                raise ValueError(
                    f"X shape {X.shape[:2]} and mask shape {mask.shape} "
                    "must agree on T and N dimensions."
                )
            if window_size < 1:
                raise ValueError(f"window_size must be >= 1, got {window_size}.")
            if target_offset < 1:
                raise ValueError(f"target_offset must be >= 1, got {target_offset}.")

        @staticmethod
        def from_split(
            X_norm: np.ndarray,
            mask: np.ndarray,
            window_size: int = 12,
        ) -> "ReconstructionDataset":
            """
            Convenience constructor — builds a dataset from a normalised
            split array and its mask.  Both arrays must have matching T, N.
            """
            return ReconstructionDataset(X_norm, mask, window_size=window_size)


except ImportError:
    _TORCH_AVAILABLE = False

    class ReconstructionDataset:  # type: ignore[no-redef]
        """
        Fallback NumPy-only dataset when PyTorch is not installed.

        Returns dictionaries of NumPy arrays instead of Tensors.
        Not compatible with torch.utils.data.DataLoader.
        """

        def __init__(
            self,
            X: np.ndarray,
            mask: np.ndarray,
            window_size: int = 12,
            target_offset: int = 1,
        ) -> None:
            import warnings
            warnings.warn(
                "PyTorch not found — ReconstructionDataset running in NumPy-only mode. "
                "Install PyTorch for full functionality: pip install torch",
                ImportWarning,
                stacklevel=2,
            )
            self.X = X.astype(np.float32)
            self.mask = mask.astype(np.float32)
            self.window_size = window_size
            self.target_offset = target_offset
            T = X.shape[0]
            self.n_samples = T - window_size - target_offset + 1
            self.n_sensors = X.shape[1]
            self.n_features = X.shape[2]

        def __len__(self) -> int:
            return self.n_samples

        def __getitem__(self, idx: int) -> Dict[str, np.ndarray]:
            w_start = idx
            w_end   = idx + self.window_size
            t_idx   = w_end + self.target_offset - 1
            return {
                "input_window": self.X[w_start:w_end],
                "mask_window":  self.mask[w_start:w_end],
                "target":       self.X[t_idx],
                "target_mask":  self.mask[t_idx],
            }

        def print_stats(self) -> None:
            T = self.X.shape[0]
            n_missing = int(np.isnan(self.X).sum())
            print("\nReconstructionDataset Summary (NumPy-only mode)")
            print("-" * 40)
            print(f"  Samples    : {self.n_samples:,}")
            print(f"  Sensors    : {self.n_sensors}")
            print(f"  Features   : {self.n_features}")
            print(f"  Missing    : {n_missing:,} ({100*n_missing/self.X.size:.2f}%)")
            print("-" * 40)
