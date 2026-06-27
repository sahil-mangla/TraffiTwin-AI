"""
preprocessing.py — Normalisation and Train/Val/Test Splitting
===============================================================
Provides z-score normalisation (fit on train split only) and
strictly temporal data splitting for the METR-LA dataset.

Design rules
------------
- NEVER shuffle time-series data.  Splits are contiguous time slices.
- Scaler is fit exclusively on the training split to prevent data leakage.
- inverse_transform() is used after model inference to recover real units.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default split ratios
_TRAIN_RATIO: float = 0.70
_VAL_RATIO: float = 0.10
_TEST_RATIO: float = 0.20


# ---------------------------------------------------------------------------
# Data class for holding split arrays
# ---------------------------------------------------------------------------

@dataclass
class DataSplit:
    """
    Container for a single time-ordered data partition.

    Attributes
    ----------
    X : np.ndarray, shape (T_split, N, F)
        Feature array for this partition.
    mask : np.ndarray or None, shape (T_split, N)
        Failure mask (1=healthy, 0=failed).  None before simulation.
    name : str
        Partition label: 'train', 'val', or 'test'.
    start_idx : int
        Global start index in the original full array.
    end_idx : int
        Global end index (exclusive) in the original full array.
    """
    X: np.ndarray
    mask: Optional[np.ndarray]
    name: str
    start_idx: int
    end_idx: int

    @property
    def n_timesteps(self) -> int:
        return self.X.shape[0]

    @property
    def n_sensors(self) -> int:
        return self.X.shape[1]


# ---------------------------------------------------------------------------
# Z-Score Scaler
# ---------------------------------------------------------------------------

class ZScoreScaler:
    """
    Per-feature z-score normalisation fitted on training data only.

    Follows the scikit-learn Transformer interface (fit / transform /
    inverse_transform) but operates on 3-D NumPy arrays of shape
    (T, N, F).

    NaN values in the input are handled transparently:
      - fit()              : statistics computed ignoring NaNs.
      - transform()        : NaNs are preserved (not imputed here).
      - inverse_transform(): NaNs are preserved.

    Parameters
    ----------
    eps : float
        Small constant added to σ to prevent division by zero.
        Defaults to 1e-8.
    """

    def __init__(self, eps: float = 1e-8) -> None:
        self.eps = eps
        self.mean_: Optional[np.ndarray] = None   # shape (1, 1, F)
        self.std_: Optional[np.ndarray] = None    # shape (1, 1, F)
        self._fitted: bool = False

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    def fit(self, X_train: np.ndarray) -> "ZScoreScaler":
        """
        Compute mean and standard deviation from the training array.

        Parameters
        ----------
        X_train : np.ndarray, shape (T_train, N, F)
            Training split **only**.  Statistics are computed per-feature
            (axis F), aggregated across all sensors and timesteps.

        Returns
        -------
        self
        """
        if X_train.ndim != 3:
            raise ValueError(
                f"Expected 3-D array (T, N, F), got shape {X_train.shape}"
            )

        # Compute per-feature statistics, ignoring NaNs
        # Collapse axes 0 (time) and 1 (sensors) → shape (F,)
        self.mean_ = np.nanmean(X_train, axis=(0, 1), keepdims=True)  # (1,1,F)
        self.std_  = np.nanstd(X_train,  axis=(0, 1), keepdims=True)  # (1,1,F)

        self._fitted = True

        F = X_train.shape[2]
        for f in range(F):
            logger.info(
                "Feature %d — μ=%.4f, σ=%.4f",
                f, float(self.mean_[0, 0, f]), float(self.std_[0, 0, f])
            )

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Apply z-score normalisation using fitted statistics.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)

        Returns
        -------
        X_norm : np.ndarray, shape (T, N, F), dtype float32
            Normalised values.  NaNs in the input are preserved.
        """
        self._assert_fitted()
        return ((X - self.mean_) / (self.std_ + self.eps)).astype(np.float32)

    def inverse_transform(self, X_norm: np.ndarray) -> np.ndarray:
        """
        Reverse z-score normalisation to recover original units.

        Parameters
        ----------
        X_norm : np.ndarray, shape (T, N, F) or (N, F)
            Normalised array.  Handles both 3-D windowed and 2-D
            single-step arrays.

        Returns
        -------
        X : np.ndarray, same shape as input, dtype float32
            Values in original units (e.g., mph for METR-LA).
        """
        self._assert_fitted()

        if X_norm.ndim == 2:
            # (N, F) — single timestep output from reconstruction
            mean = self.mean_[0]   # (1, F)
            std  = self.std_[0]    # (1, F)
            return (X_norm * (std + self.eps) + mean).astype(np.float32)

        return (X_norm * (self.std_ + self.eps) + self.mean_).astype(np.float32)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def mean(self) -> np.ndarray:
        self._assert_fitted()
        return self.mean_.squeeze()

    @property
    def std(self) -> np.ndarray:
        self._assert_fitted()
        return self.std_.squeeze()

    def _assert_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(
                "ZScoreScaler has not been fitted. Call .fit(X_train) first."
            )


# ---------------------------------------------------------------------------
# Train / Val / Test Splitter
# ---------------------------------------------------------------------------

class TimeSeriesSplitter:
    """
    Strictly temporal (non-shuffling) train / val / test split.

    Slices the time-series array into three contiguous partitions:

        |←── 70% train ──→|←10% val→|←── 20% test ──→|
        t=0                                             t=T

    Parameters
    ----------
    train_ratio : float
        Fraction of timesteps for training. Default 0.70.
    val_ratio : float
        Fraction of timesteps for validation. Default 0.10.
    test_ratio : float
        Fraction of timesteps for testing. Default 0.20.

    Notes
    -----
    Ratios must sum to 1.0.  A small rounding tolerance (< 3 samples)
    is acceptable due to integer truncation.
    """

    def __init__(
        self,
        train_ratio: float = _TRAIN_RATIO,
        val_ratio: float = _VAL_RATIO,
        test_ratio: float = _TEST_RATIO,
    ) -> None:
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total:.6f}. "
                f"(train={train_ratio}, val={val_ratio}, test={test_ratio})"
            )
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(self, X: np.ndarray) -> Tuple[DataSplit, DataSplit, DataSplit]:
        """
        Split array into train, val, and test partitions.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)
            Full time-series array.

        Returns
        -------
        train, val, test : tuple of DataSplit
            Three contiguous, temporally-ordered partitions.
        """
        if X.ndim != 3:
            raise ValueError(
                f"Expected 3-D array (T, N, F), got shape {X.shape}"
            )

        T = X.shape[0]
        train_end = int(T * self.train_ratio)
        val_end   = train_end + int(T * self.val_ratio)
        # test_end  = T  (remaining samples to handle rounding)

        train = DataSplit(
            X=X[:train_end],
            mask=None,
            name="train",
            start_idx=0,
            end_idx=train_end,
        )
        val = DataSplit(
            X=X[train_end:val_end],
            mask=None,
            name="val",
            start_idx=train_end,
            end_idx=val_end,
        )
        test = DataSplit(
            X=X[val_end:],
            mask=None,
            name="test",
            start_idx=val_end,
            end_idx=T,
        )

        self._log_splits(T, train, val, test)
        return train, val, test

    @staticmethod
    def _log_splits(
        T: int, train: DataSplit, val: DataSplit, test: DataSplit
    ) -> None:
        logger.info(
            "Split %d timesteps → train=%d (%.1f%%), val=%d (%.1f%%), test=%d (%.1f%%)",
            T,
            train.n_timesteps, 100 * train.n_timesteps / T,
            val.n_timesteps,   100 * val.n_timesteps / T,
            test.n_timesteps,  100 * test.n_timesteps / T,
        )

    def print_split_summary(self, T: int) -> None:
        """Print human-readable split boundary information."""
        train_end = int(T * self.train_ratio)
        val_end   = train_end + int(T * self.val_ratio)

        print("\nTrain / Val / Test Split")
        print("-" * 45)
        print(f"  Total timesteps : {T:,}")
        print(f"  Train           : t=0       → t={train_end:,}  ({train_end:,} steps)")
        print(f"  Val             : t={train_end:,} → t={val_end:,}  ({val_end - train_end:,} steps)")
        print(f"  Test            : t={val_end:,} → t={T:,}  ({T - val_end:,} steps)")
        print("-" * 45)
