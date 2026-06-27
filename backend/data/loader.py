"""
loader.py — METR-LA Dataset Loader
====================================
Loads the METR-LA traffic speed dataset from disk, validates integrity,
and returns standardised NumPy arrays ready for downstream processing.

Supported file formats
-----------------------
Speed data : metr-la.h5  (HDF5 / pandas DataFrame)
             OR metr-la.npz (NumPy compressed)
Adjacency  : adj_mx.pkl  (pickle — tuple of (ids, id_to_index, matrix))
             OR adj_mx.npy / adj_mx.npz

Download instructions
---------------------
Official source:
  https://github.com/liyaguang/DCRNN
  File: data/metr-la.h5  and  data/sensor_graph/adj_mx.pkl

Place both files in the same directory and pass that path to METRLADataLoader.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class METRLADataLoader:
    """
    Loads and validates the METR-LA traffic speed dataset.

    Parameters
    ----------
    data_dir : str | Path
        Directory containing ``metr-la.h5`` (or ``metr-la.npz``) and
        ``adj_mx.pkl`` (or ``adj_mx.npy``).
    speed_filename : str
        Name of the speed data file.  Defaults to ``'metr-la.h5'``.
    adj_filename : str
        Name of the adjacency matrix file.  Defaults to ``'adj_mx.pkl'``.

    Attributes
    ----------
    X : np.ndarray, shape (T, N, F)
        Traffic speed tensor.  T = timesteps, N = sensors, F = features.
    A : np.ndarray, shape (N, N)
        Weighted adjacency matrix (road-network distances / travel times).
    timestamps : pd.DatetimeIndex
        UTC timestamps corresponding to axis 0 of X.
    sensor_ids : list[str]
        Ordered list of sensor IDs corresponding to axis 1 of X.
    """

    # Known METR-LA constants for integrity validation
    EXPECTED_N_SENSORS: int = 207
    EXPECTED_MIN_TIMESTEPS: int = 34_000  # ~34 272 at 5-min intervals

    def __init__(
        self,
        data_dir: str | Path,
        speed_filename: str = "metr-la.h5",
        adj_filename: str = "adj_mx.pkl",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.speed_path = self.data_dir / speed_filename
        self.adj_path = self.data_dir / adj_filename

        self.X: np.ndarray = np.array([])
        self.A: np.ndarray = np.array([])
        self.timestamps: pd.DatetimeIndex = pd.DatetimeIndex([])
        self.sensor_ids: list[str] = []

        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> "METRLADataLoader":
        """
        Load speed data and adjacency matrix from disk.

        Returns
        -------
        self
            Enables method chaining: ``loader.load().print_stats()``.

        Raises
        ------
        FileNotFoundError
            If required data files are missing from ``data_dir``.
        ValueError
            If loaded arrays fail shape or integrity checks.
        """
        self._check_files_exist()

        logger.info("Loading speed data from: %s", self.speed_path)
        self.X, self.timestamps, self.sensor_ids = self._load_speed_data()

        logger.info("Loading adjacency matrix from: %s", self.adj_path)
        self.A = self._load_adjacency()

        self._validate()
        self._loaded = True

        logger.info(
            "METR-LA loaded successfully — shape X=%s, A=%s",
            self.X.shape,
            self.A.shape,
        )
        return self

    def get_arrays(self) -> Tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
        """
        Return the core dataset arrays.

        Returns
        -------
        X : np.ndarray, shape (T, N, F)
        A : np.ndarray, shape (N, N)
        timestamps : pd.DatetimeIndex, length T
        """
        self._assert_loaded()
        return self.X, self.A, self.timestamps

    def print_stats(self) -> None:
        """Print a human-readable summary of the loaded dataset."""
        self._assert_loaded()

        T, N, F = self.X.shape
        n_missing = int(np.isnan(self.X).sum())
        pct_missing = 100.0 * n_missing / self.X.size

        print("=" * 55)
        print("  METR-LA Dataset Statistics")
        print("=" * 55)
        print(f"  Sensors (N)       : {N}")
        print(f"  Timesteps (T)     : {T}")
        print(f"  Features (F)      : {F}  (speed only for MVP)")
        print(f"  Sampling interval : 5 minutes")
        print(f"  Date range        : {self.timestamps[0]}  →  {self.timestamps[-1]}")
        print(f"  Total duration    : {(self.timestamps[-1] - self.timestamps[0])}")
        print(f"  Missing values    : {n_missing:,} ({pct_missing:.2f}%)")
        print(f"  Speed range       : [{np.nanmin(self.X):.2f}, {np.nanmax(self.X):.2f}] mph")
        print(f"  Speed mean (μ)    : {np.nanmean(self.X):.2f} mph")
        print(f"  Speed std  (σ)    : {np.nanstd(self.X):.2f} mph")
        print(f"  Adjacency density : {self._adj_density():.4f}")
        print("=" * 55)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_files_exist(self) -> None:
        """Raise FileNotFoundError if required files are absent."""
        missing = []
        if not self.speed_path.exists():
            # Try .npz fallback
            alt = self.speed_path.with_suffix(".npz")
            if alt.exists():
                self.speed_path = alt
            else:
                missing.append(str(self.speed_path))

        if not self.adj_path.exists():
            for alt_name in ("adj_mx.npy", "adj_mx.npz"):
                alt = self.data_dir / alt_name
                if alt.exists():
                    self.adj_path = alt
                    break
            else:
                missing.append(str(self.adj_path))

        if missing:
            msg = (
                "Required METR-LA files not found:\n"
                + "\n".join(f"  • {p}" for p in missing)
                + "\n\nDownload from: https://github.com/liyaguang/DCRNN"
                + "\nExpected location: data/metr-la.h5 and data/sensor_graph/adj_mx.pkl"
            )
            raise FileNotFoundError(msg)

    def _load_speed_data(
        self,
    ) -> Tuple[np.ndarray, pd.DatetimeIndex, list[str]]:
        """
        Load traffic speed from HDF5 or NPZ.

        Returns
        -------
        X : np.ndarray, shape (T, N, 1)
        timestamps : pd.DatetimeIndex
        sensor_ids : list[str]
        """
        suffix = self.speed_path.suffix.lower()

        if suffix in (".h5", ".hdf5"):
            df: pd.DataFrame = pd.read_hdf(self.speed_path)
            # DataFrame: index=timestamps, columns=sensor_ids, values=speed (mph)
            timestamps = pd.DatetimeIndex(df.index)
            sensor_ids = [str(c) for c in df.columns]
            # shape: (T, N, 1)
            X = df.values[:, :, np.newaxis].astype(np.float32)

        elif suffix == ".npz":
            npz = np.load(self.speed_path, allow_pickle=True)
            X_raw = npz["data"].astype(np.float32)
            # Support both (T, N) and (T, N, F)
            if X_raw.ndim == 2:
                X_raw = X_raw[:, :, np.newaxis]
            X = X_raw

            if "timestamps" in npz:
                timestamps = pd.DatetimeIndex(npz["timestamps"])
            else:
                # Synthesise 5-min timestamps starting from 2012-03-01
                T = X.shape[0]
                timestamps = pd.date_range(
                    start="2012-03-01 00:00:00", periods=T, freq="5min"
                )

            sensor_ids = (
                [str(s) for s in npz["sensor_ids"]]
                if "sensor_ids" in npz
                else [str(i) for i in range(X.shape[1])]
            )

        else:
            raise ValueError(
                f"Unsupported speed file format: '{suffix}'. "
                "Expected .h5, .hdf5, or .npz"
            )

        return X, timestamps, sensor_ids

    def _load_adjacency(self) -> np.ndarray:
        """
        Load adjacency matrix from PKL or NPY/NPZ.

        Returns
        -------
        A : np.ndarray, shape (N, N), dtype float32
        """
        suffix = self.adj_path.suffix.lower()

        if suffix == ".pkl":
            with open(self.adj_path, "rb") as f:
                pkl_data = pickle.load(f, encoding="latin-1")
            # DCRNN format: (sensor_ids, sensor_id_to_ind, adj_matrix)
            if isinstance(pkl_data, (tuple, list)) and len(pkl_data) == 3:
                _, _, A = pkl_data
            elif isinstance(pkl_data, np.ndarray):
                A = pkl_data
            else:
                raise ValueError(
                    f"Unexpected adjacency PKL structure: {type(pkl_data)}"
                )

        elif suffix == ".npy":
            A = np.load(self.adj_path)

        elif suffix == ".npz":
            npz = np.load(self.adj_path)
            key = "adj_mx" if "adj_mx" in npz else list(npz.keys())[0]
            A = npz[key]

        else:
            raise ValueError(
                f"Unsupported adjacency file format: '{suffix}'. "
                "Expected .pkl, .npy, or .npz"
            )

        return A.astype(np.float32)

    def _validate(self) -> None:
        """Run shape and sanity checks on loaded arrays."""
        T, N, F = self.X.shape

        if N != self.EXPECTED_N_SENSORS:
            logger.warning(
                "Expected %d sensors, found %d. "
                "Proceeding — may not be standard METR-LA.",
                self.EXPECTED_N_SENSORS,
                N,
            )

        if T < self.EXPECTED_MIN_TIMESTEPS:
            logger.warning(
                "Dataset has only %d timesteps (expected >= %d). "
                "Dataset may be truncated.",
                T,
                self.EXPECTED_MIN_TIMESTEPS,
            )

        if self.A.shape != (N, N):
            raise ValueError(
                f"Adjacency matrix shape {self.A.shape} does not match "
                f"number of sensor nodes N={N}. Expected ({N}, {N})."
            )

        if np.any(np.isnan(self.A)):
            logger.warning("Adjacency matrix contains NaN values — replacing with 0.")
            self.A = np.nan_to_num(self.A, nan=0.0)

        # Ensure non-negative weights
        if np.any(self.A < 0):
            raise ValueError("Adjacency matrix contains negative edge weights.")

    def _adj_density(self) -> float:
        """Return fraction of non-zero entries in adjacency matrix."""
        total = self.A.size
        nonzero = int(np.count_nonzero(self.A))
        return nonzero / total if total > 0 else 0.0

    def _assert_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError(
                "Dataset not loaded. Call .load() before accessing data."
            )
