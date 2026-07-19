"""
Regression test for the FCR test-set-cap bug: SpatialFeatureEngineer.transform's
MAX_FEATURE_ROWS safety cap must never silently subsample the test split, or FCR's
denominator (raw failure count) and numerator (predictions made) go out of sync.
See docs/archive/FCR_AUDIT_REPORT.md (§7 Addendum) for the original incident.
"""

import numpy as np
import pandas as pd

from backend.evaluation.config import config
from backend.models.evaluator import Evaluator
from backend.models.feature_engineering import SpatialFeatureEngineer


def _make_fixture(n_timesteps=60, n_sensors=5, n_failures=10):
    rng = np.random.default_rng(42)
    X = rng.uniform(20, 60, size=(n_timesteps, n_sensors, 1))

    # Simple ring adjacency so every node has healthy neighbors.
    A = np.zeros((n_sensors, n_sensors))
    for i in range(n_sensors):
        A[i, (i + 1) % n_sensors] = 1.0
        A[(i + 1) % n_sensors, i] = 1.0

    mask = np.ones((n_timesteps, n_sensors))
    # Place failures at t >= 24 (past the lag24 warmup guard) so none are excluded
    # by start_t filtering — isolates the cap's effect from the warmup gap.
    failed_t = np.arange(30, 30 + n_failures) % n_timesteps
    failed_n = np.arange(n_failures) % n_sensors
    mask[failed_t, failed_n] = 0

    timestamps = pd.date_range("2024-01-01", periods=n_timesteps, freq="5min")
    return X, mask, A, timestamps, int((mask == 0).sum())


def test_enforce_cap_false_returns_full_uncapped_set(monkeypatch):
    monkeypatch.setattr(config, "MAX_FEATURE_ROWS", 3)
    X, mask, A, timestamps, total_failures = _make_fixture(n_failures=10)

    engineer = SpatialFeatureEngineer(max_neighbors=3)
    X_feat, y = engineer.fit_transform(X, mask, A, timestamps, max_samples=None, enforce_cap=False)

    assert len(y) == total_failures, (
        "enforce_cap=False must return every eligible failed cell regardless of "
        "MAX_FEATURE_ROWS — this is what the test split relies on for correct FCR."
    )


def test_enforce_cap_true_still_caps_train_val_as_before(monkeypatch):
    monkeypatch.setattr(config, "MAX_FEATURE_ROWS", 3)
    X, mask, A, timestamps, total_failures = _make_fixture(n_failures=10)

    engineer = SpatialFeatureEngineer(max_neighbors=3)
    X_feat, y = engineer.fit_transform(X, mask, A, timestamps, max_samples=None, enforce_cap=True)

    assert len(y) == 3, "default enforce_cap=True must still bound train/val extraction cost."


def test_fcr_is_not_corrupted_when_test_set_exceeds_the_cap(monkeypatch):
    """
    The regression this guards against: if the test split is ever capped again
    (e.g. someone flips enforce_cap back to True for experiment_runner.py's test
    transform call), FCR silently collapses even though prediction quality is
    unaffected. This test pins the expected (uncapped) behavior.
    """
    monkeypatch.setattr(config, "MAX_FEATURE_ROWS", 3)
    X, mask, A, timestamps, total_failures = _make_fixture(n_failures=10)

    engineer = SpatialFeatureEngineer(max_neighbors=3)
    X_feat, y_test = engineer.fit_transform(X, mask, A, timestamps, max_samples=None, enforce_cap=False)

    y_pred = y_test  # perfect predictions; only coverage is under test here
    metrics = Evaluator.calculate_metrics(y_test, y_pred, total_failures=total_failures)

    assert metrics["fcr"] > 93.0, (
        f"FCR collapsed to {metrics['fcr']:.1f}% — the test split is being capped "
        "again, corrupting the coverage metric independently of prediction quality."
    )
