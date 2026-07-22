import numpy as np
import pandas as pd
import pytest

from backend.models.lightgbm_reconstructor import LightGBMReconstructor


def _make_training_data(n=200, n_features=4, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, n_features)), columns=[f"f{i}" for i in range(n_features)])
    y = X.sum(axis=1).to_numpy() + rng.normal(scale=0.1, size=n)
    return X, y


def test_init_uses_default_hyperparameters_when_none_given():
    model = LightGBMReconstructor()
    assert model.params["n_estimators"] == 500
    assert model.params["learning_rate"] == 0.05
    assert model.params["random_state"] == 42


def test_init_overrides_defaults_with_kwargs():
    model = LightGBMReconstructor(n_estimators=10, learning_rate=0.2)
    assert model.params["n_estimators"] == 10
    assert model.params["learning_rate"] == 0.2
    # Untouched defaults remain.
    assert model.params["num_leaves"] == 63


def test_fit_without_eval_set_trains_model_and_skips_early_stopping():
    X, y = _make_training_data()
    model = LightGBMReconstructor(n_estimators=5)
    result = model.fit(X, y)

    assert result is model  # fit returns self
    # No eval_set means no early stopping; best_iteration_ is whatever
    # LightGBM reports by default (not derived from early stopping).
    assert hasattr(model, "best_iteration_")
    preds = model.predict(X)
    assert preds.shape == (len(X),)


def test_fit_with_eval_set_enables_early_stopping():
    X, y = _make_training_data(n=300)
    X_train, X_val = X.iloc[:200], X.iloc[200:]
    y_train, y_val = y[:200], y[200:]

    model = LightGBMReconstructor(n_estimators=50)
    model.fit(X_train, y_train, eval_set=(X_val, y_val), early_stopping_rounds=5)

    assert model.best_iteration_ is not None
    assert model.best_iteration_ >= 1


def test_predict_returns_correct_length():
    X, y = _make_training_data()
    model = LightGBMReconstructor(n_estimators=5).fit(X, y)
    preds = model.predict(X.iloc[:10])
    assert len(preds) == 10


def test_evaluate_returns_expected_metric_keys():
    X, y = _make_training_data()
    model = LightGBMReconstructor(n_estimators=5).fit(X, y)

    metrics = model.evaluate(X, y, total_failures=len(y))
    assert set(metrics.keys()) == {"mae", "rmse", "mape", "rfs", "fcr"}
    assert metrics["fcr"] == pytest.approx(100.0)


def test_save_and_load_round_trip_preserves_predictions(tmp_path):
    X, y = _make_training_data()
    model = LightGBMReconstructor(n_estimators=5).fit(X, y)
    original_preds = model.predict(X)

    save_path = tmp_path / "nested" / "model.pkl"
    model.save(save_path)
    assert save_path.exists()

    loaded = LightGBMReconstructor.load(save_path)
    loaded_preds = loaded.predict(X)

    np.testing.assert_allclose(original_preds, loaded_preds)


def test_load_raises_file_not_found_for_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        LightGBMReconstructor.load(tmp_path / "does_not_exist.pkl")
