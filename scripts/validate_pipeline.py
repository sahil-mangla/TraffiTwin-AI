"""
validate_pipeline.py — End-to-End Data Pipeline Validation
========================================================
Standalone script that exercises the full METR-LA data pipeline:

    1. Load METR-LA (speed + adjacency)
    2. Print dataset statistics
    3. Split into train / val / test
    4. Fit z-score normalisation on train split
    5. Normalise all splits
    6. Simulate MCAR failure on training data
    7. Simulate block-missing failure on test data
    8. Build sliding-window ReconstructionDatasets
    9. Print tensor shapes and summary statistics

Usage
-----
    python scripts/validate_pipeline.py --data_dir /path/to/metr-la/

If the real METR-LA files are not available, pass --synthetic to run
against a procedurally generated dataset of the correct shape.

    python scripts/validate_pipeline.py --synthetic
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Configure logging before any local imports
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("validate_pipeline")

# ---------------------------------------------------------------------------
# Local imports — allow running as `python backend/test_pipeline.py` from repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.data.loader import METRLADataLoader
from backend.data.preprocessing import ZScoreScaler, TimeSeriesSplitter
from backend.data.failure_simulator import FailureSimulator
from backend.data.dataset import ReconstructionDataset


# ---------------------------------------------------------------------------
# Synthetic data generator (no real files needed)
# ---------------------------------------------------------------------------

def make_synthetic_metrla(
    n_sensors: int = 207,
    n_timesteps: int = 34_272,
    n_features: int = 1,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a plausible synthetic METR-LA substitute.

    Speed values are drawn from a mixture that approximates real
    highway distributions: mostly free-flow (55–75 mph) with a fraction
    of congested readings (5–30 mph).  Roughly 8% of entries are NaN to
    mimic the real dataset's missingness rate.

    Returns
    -------
    X : np.ndarray, shape (n_timesteps, n_sensors, n_features)
    A : np.ndarray, shape (n_sensors, n_sensors)  — sparse adjacency
    """
    rng = np.random.default_rng(seed)

    # ---- Speed signal -------------------------------------------------------
    # Sinusoidal daily pattern + Gaussian noise + congestion spikes
    t = np.arange(n_timesteps)
    daily_cycle = np.sin(2 * np.pi * t / (288))          # 288 steps/day
    weekly_cycle = 0.3 * np.sin(2 * np.pi * t / (288 * 7))

    base_speed = 55.0 + 15.0 * daily_cycle + 5.0 * weekly_cycle
    sensor_offsets = rng.uniform(-10, 10, size=(1, n_sensors))
    noise = rng.normal(0, 3, size=(n_timesteps, n_sensors))

    X_raw = base_speed[:, np.newaxis] + sensor_offsets + noise

    # Inject congestion events
    n_events = 50
    for _ in range(n_events):
        s  = rng.integers(0, n_sensors)
        t0 = rng.integers(0, n_timesteps - 30)
        duration = rng.integers(6, 30)
        X_raw[t0: t0 + duration, s] = rng.uniform(5, 30, size=duration)

    X_raw = np.clip(X_raw, 0, 90).astype(np.float32)
    X = X_raw[:, :, np.newaxis]  # (T, N, 1)

    # Inject ~8% structural NaN (pre-existing missingness like real dataset)
    nan_mask = rng.random(size=(n_timesteps, n_sensors)) < 0.08
    X[nan_mask, 0] = np.nan

    # ---- Adjacency matrix ---------------------------------------------------
    # Sparse symmetric matrix: random edges within radius-5 sensor bands
    A = np.zeros((n_sensors, n_sensors), dtype=np.float32)
    for i in range(n_sensors):
        neighbors = rng.integers(
            max(0, i - 5), min(n_sensors, i + 6),
            size=rng.integers(2, 6),
        )
        for j in neighbors:
            if j != i:
                w = float(rng.uniform(0.1, 1.0))
                A[i, j] = w
                A[j, i] = w  # symmetric

    return X, A


# ---------------------------------------------------------------------------
# Section printer helper
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'━' * 60}")
    print(f"  {title}")
    print(f"{'━' * 60}")


# ---------------------------------------------------------------------------
# Main pipeline test
# ---------------------------------------------------------------------------

def run_pipeline(data_dir: str | None, use_synthetic: bool) -> None:
    t_total = time.perf_counter()

    # =========================================================
    # STEP 1 — Load data
    # =========================================================
    _section("STEP 1 — Load METR-LA")

    if use_synthetic:
        print("  [SYNTHETIC MODE] Generating procedural METR-LA substitute …")
        t0 = time.perf_counter()
        X, A = make_synthetic_metrla()
        import pandas as pd
        timestamps = pd.date_range("2012-03-01", periods=X.shape[0], freq="5min")
        sensor_ids = [str(i) for i in range(X.shape[1])]
        print(f"  Generated in {time.perf_counter() - t0:.2f}s")

    else:
        loader = METRLADataLoader(data_dir=data_dir)
        t0 = time.perf_counter()
        loader.load()
        X, A, timestamps = loader.get_arrays()
        sensor_ids = loader.sensor_ids
        print(f"  Loaded in {time.perf_counter() - t0:.2f}s")

    T, N, F = X.shape

    print(f"\n  Loaded METR-LA")
    print(f"  Sensors    : {N}")
    print(f"  Timesteps  : {T:,}")
    print(f"  Features   : {F}")
    print(f"  X.shape    : {X.shape}")
    print(f"  A.shape    : {A.shape}")
    print(f"  NaN in X   : {np.isnan(X).sum():,} ({100*np.isnan(X).mean():.2f}%)")
    if not use_synthetic:
        print(f"  Date range : {timestamps[0]}  →  {timestamps[-1]}")
        loader.print_stats()

    # =========================================================
    # STEP 2 — Train / Val / Test Split
    # =========================================================
    _section("STEP 2 — Temporal Train / Val / Test Split")

    splitter = TimeSeriesSplitter(train_ratio=0.70, val_ratio=0.10, test_ratio=0.20)
    train_split, val_split, test_split = splitter.split(X)
    splitter.print_split_summary(T)

    print(f"\n  train.X.shape : {train_split.X.shape}")
    print(f"  val.X.shape   : {val_split.X.shape}")
    print(f"  test.X.shape  : {test_split.X.shape}")

    # =========================================================
    # STEP 3 — Z-Score Normalisation (fit on train only)
    # =========================================================
    _section("STEP 3 — Z-Score Normalisation")

    scaler = ZScoreScaler()
    scaler.fit(train_split.X)

    X_train_norm = scaler.transform(train_split.X)
    X_val_norm   = scaler.transform(val_split.X)
    X_test_norm  = scaler.transform(test_split.X)

    print(f"\n  Train stats (post-norm):")
    print(f"    mean = {np.nanmean(X_train_norm):.6f}  (target ≈ 0.0)")
    print(f"    std  = {np.nanstd(X_train_norm):.6f}   (target ≈ 1.0)")

    # Verify inverse_transform round-trip
    X_train_recovered = scaler.inverse_transform(X_train_norm)
    max_roundtrip_err = float(np.nanmax(np.abs(X_train_recovered - train_split.X)))
    print(f"\n  Inverse-transform round-trip error : {max_roundtrip_err:.2e}  (target < 1e-4)")
    assert max_roundtrip_err < 1e-3, "Round-trip error too large — check scaler."

    # =========================================================
    # STEP 4 — Failure Simulation: MCAR on training data
    # =========================================================
    _section("STEP 4 — MCAR Failure Simulation (Train Split)")

    sim = FailureSimulator(random_seed=42)
    mcar_result = sim.simulate_mcar(X_train_norm, missing_rate=0.10)

    print(f"\n  MCAR applied:")
    print(f"    Missing rate (target)  : 10.00%")
    print(f"    Missing rate (actual)  : {mcar_result.actual_missing_rate * 100:.2f}%")
    print(f"    masked_data.shape      : {mcar_result.masked_data.shape}")
    print(f"    mask_matrix.shape      : {mcar_result.mask_matrix.shape}")
    print(f"    mask dtype             : {mcar_result.mask_matrix.dtype}")
    print(f"    Mask unique values     : {np.unique(mcar_result.mask_matrix).tolist()}  (expect [0, 1])")
    print(f"\n  {mcar_result.summary()}")

    # =========================================================
    # STEP 5 — Failure Simulation: Block Missing on test data
    # =========================================================
    _section("STEP 5 — Block-Missing Failure Simulation (Test Split)")

    # Simulate a 4-hour outage (48 steps × 5 min) on 3 sensors
    block_node_ids = [0, 42, 100]
    block_start    = 500
    block_duration = 48    # 4 hours

    block_result = sim.simulate_block_missing(
        X_test_norm,
        node_ids=block_node_ids,
        start_time=block_start,
        duration=block_duration,
    )

    print(f"\n  Block outage applied:")
    print(f"    Failed nodes           : {block_node_ids}")
    print(f"    Start timestep         : {block_start}")
    print(f"    Duration               : {block_duration} steps ({block_duration * 5 / 60:.1f} hours)")
    print(f"    masked_data.shape      : {block_result.masked_data.shape}")
    print(f"    mask_matrix.shape      : {block_result.mask_matrix.shape}")
    print(f"    Actual missing rate    : {block_result.actual_missing_rate * 100:.4f}%")

    # Verify failure is correctly applied
    failed_block = block_result.mask_matrix[block_start: block_start + block_duration, block_node_ids]
    assert failed_block.sum() == 0, "Block failure not correctly applied to mask!"
    healthy_elsewhere = block_result.mask_matrix[:block_start, :]
    assert healthy_elsewhere.sum() == block_start * N, "Mask modified outside failure window!"
    print(f"\n  ✓ Block failure integrity check passed.")
    print(f"\n  {block_result.summary()}")

    # =========================================================
    # STEP 6 — Build Sliding-Window Datasets
    # =========================================================
    _section("STEP 6 — ReconstructionDataset (Sliding Windows)")

    WINDOW_SIZE = 12   # 60 minutes of history

    # Training dataset uses MCAR-masked normalised data
    train_mask = mcar_result.mask_matrix                     # (T_train, N)
    train_dataset = ReconstructionDataset(
        X=mcar_result.masked_data,
        mask=train_mask,
        window_size=WINDOW_SIZE,
    )

    # Validation — no synthetic failure (evaluate on clean data)
    val_mask = np.ones((X_val_norm.shape[0], N), dtype=np.uint8)
    val_dataset = ReconstructionDataset(
        X=X_val_norm,
        mask=val_mask,
        window_size=WINDOW_SIZE,
    )

    # Test dataset uses block-missing-masked normalised data
    test_mask = block_result.mask_matrix                     # (T_test, N)
    test_dataset = ReconstructionDataset(
        X=block_result.masked_data,
        mask=test_mask,
        window_size=WINDOW_SIZE,
    )

    print(f"\n  Window size             : {WINDOW_SIZE} steps ({WINDOW_SIZE * 5} min)")
    print(f"\n  Train dataset:")
    print(f"    Samples               : {len(train_dataset):,}")
    train_dataset.print_stats()

    print(f"\n  Val dataset:")
    print(f"    Samples               : {len(val_dataset):,}")
    val_dataset.print_stats()

    print(f"\n  Test dataset:")
    print(f"    Samples               : {len(test_dataset):,}")
    test_dataset.print_stats()

    # =========================================================
    # STEP 7 — Sample Inspection
    # =========================================================
    _section("STEP 7 — Sample Tensor Shape Inspection")

    sample = train_dataset[0]
    print("\n  Sample[0] from train_dataset:")
    for key, val in sample.items():
        if hasattr(val, "shape"):
            dtype = val.dtype if hasattr(val, "dtype") else "ndarray"
            print(f"    {key:<20}: shape={tuple(val.shape)}  dtype={dtype}")
        else:
            print(f"    {key:<20}: {val}")

    # Verify expected shapes
    assert sample["input_window"].shape == (WINDOW_SIZE, N, F), \
        f"input_window shape mismatch: {sample['input_window'].shape}"
    assert sample["mask_window"].shape == (WINDOW_SIZE, N), \
        f"mask_window shape mismatch: {sample['mask_window'].shape}"
    assert sample["target"].shape == (N, F), \
        f"target shape mismatch: {sample['target'].shape}"
    assert sample["target_mask"].shape == (N,), \
        f"target_mask shape mismatch: {sample['target_mask'].shape}"

    print("\n  ✓ All tensor shape assertions passed.")

    # =========================================================
    # STEP 8 — Summary
    # =========================================================
    _section("PIPELINE SUMMARY")

    elapsed = time.perf_counter() - t_total
    print(f"""
  Dataset          : {'Synthetic METR-LA' if use_synthetic else 'METR-LA (real)'}
  Sensors (N)      : {N}
  Timesteps (T)    : {T:,}
  Features (F)     : {F}

  Split sizes:
    Train          : {len(train_split.X):,} steps → {len(train_dataset):,} windows
    Val            : {len(val_split.X):,} steps   → {len(val_dataset):,} windows
    Test           : {len(test_split.X):,} steps  → {len(test_dataset):,} windows

  Normalisation:
    μ (per feature): {scaler.mean.squeeze().tolist()}
    σ (per feature): {scaler.std.squeeze().tolist()}

  Failure simulation:
    MCAR rate      : {mcar_result.actual_missing_rate * 100:.2f}%
    Block outage   : nodes={block_node_ids}, {block_duration * 5 / 60:.1f}h @ t={block_start}

  Window size      : {WINDOW_SIZE} steps
  Total time       : {elapsed:.2f}s

  ✅  Pipeline test PASSED — all components operational.
""")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TraffiTwin AI — METR-LA data pipeline end-to-end test"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--data_dir",
        type=str,
        default=None,
        help="Path to directory containing metr-la.h5 and adj_mx.pkl.",
    )
    group.add_argument(
        "--synthetic",
        action="store_true",
        default=False,
        help="Run with a synthetic dataset (no real files required).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if not args.synthetic and args.data_dir is None:
        default_dir = Path(REPO_ROOT) / "datasets" / "raw"
        if (default_dir / "metr-la.h5").exists() and (default_dir / "adj_mx.pkl").exists():
            print(f"\n[INFO] No --data_dir provided. Found METR-LA in {default_dir}. Using it.")
            args.data_dir = str(default_dir)
        else:
            print(
                "\n[INFO] No --data_dir provided and dataset not found in datasets/raw/.\n"
                "       To run with real data, use:\n"
                "         python scripts/validate_pipeline.py --data_dir /path/to/metr-la/\n"
                "       To run with synthetic data, use:\n"
                "         python scripts/validate_pipeline.py --synthetic\n"
            )
            print("       Aborting. Please explicitly pass --synthetic if you want to use synthetic data.")
            sys.exit(1)

    run_pipeline(
        data_dir=args.data_dir,
        use_synthetic=args.synthetic,
    )
