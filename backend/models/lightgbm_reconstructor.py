"""
lightgbm_reconstructor.py — Baseline Reconstructor Model
==========================================================
Wraps the LightGBM Regressor for the traffic reconstruction task,
providing a clean API for training, evaluation, and persistence.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from backend.models.evaluator import Evaluator

logger = logging.getLogger(__name__)


class LightGBMReconstructor:
    """
    LightGBM model for predicting missing traffic speed data.
    """
    
    def __init__(self, **kwargs: Any):
        """
        Initialize the LightGBM model with default or custom hyperparameters.
        """
        # Default parameters from specification
        self.params: Dict[str, Any] = {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "num_leaves": 63,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": 1
        }
        self.params.update(kwargs)

        self.model = lgb.LGBMRegressor(**self.params)
        self.best_iteration_: Optional[int] = None
        logger.info(f"Initialized LightGBMReconstructor with params: {self.params}")

    def fit(
        self, 
        X_train: pd.DataFrame, 
        y_train: np.ndarray, 
        eval_set: Optional[Tuple[pd.DataFrame, np.ndarray]] = None,
        early_stopping_rounds: int = 50
    ) -> "LightGBMReconstructor":
        """
        Train the LightGBM model.
        
        Parameters
        ----------
        X_train : pd.DataFrame
            Training features.
        y_train : np.ndarray
            Training targets.
        eval_set : tuple of (X_val, y_val), optional
            Validation set for early stopping.
        early_stopping_rounds : int
            Number of rounds to allow without improvement before stopping.
            
        Returns
        -------
        self
        """
        logger.info(f"Training LightGBM on {len(X_train)} samples...")
        
        callbacks: list = []
        if eval_set is not None:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))
            callbacks.append(lgb.log_evaluation(period=50))
            self.model.fit(
                X_train, y_train,
                eval_set=[eval_set],
                eval_metric="rmse",
                callbacks=callbacks
            )
            self.best_iteration_ = self.model.best_iteration_
            logger.info(f"Training completed. Best iteration: {self.best_iteration_}")
        else:
            self.model.fit(X_train, y_train)
            self.best_iteration_ = getattr(self.model, "best_iteration_", None)
            logger.info("Training completed.")
            
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict traffic speed for failed nodes.
        
        Parameters
        ----------
        X : pd.DataFrame
            Features.
            
        Returns
        -------
        y_pred : np.ndarray
            Predicted traffic speeds.
        """
        return np.asarray(self.model.predict(X))

    def evaluate(
        self, 
        X_test: pd.DataFrame, 
        y_test: np.ndarray, 
        y_historical_mean: Optional[np.ndarray] = None,
        total_failures: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Evaluate the model on a test set.
        
        Returns
        -------
        metrics : dict
        """
        logger.info(f"Evaluating model on {len(X_test)} test samples...")
        y_pred = self.predict(X_test)
        
        metrics = Evaluator.calculate_metrics(
            y_true=y_test,
            y_pred=y_pred,
            y_historical_mean=y_historical_mean,
            total_failures=total_failures
        )
        return metrics

    def save(self, path: str | Path) -> None:
        """Save the trained model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str | Path) -> "LightGBMReconstructor":
        """Load a trained model from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found at {path}")
            
        with open(path, "rb") as f:
            model = pickle.load(f)
            
        instance = cls()
        instance.model = model
        logger.info(f"Model loaded from {path}")
        return instance
