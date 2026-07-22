"""
baseline_models.py — Naive Baseline Models for Traffic Reconstruction
=====================================================================
Implements the Historical Mean and Last Observation Carried Forward (LOCF) baselines.
"""

from typing import Optional

import numpy as np

class HistoricalMeanBaseline:
    """
    Predicts the missing value as the historical mean of that specific sensor node
    computed from the training dataset.
    """
    
    def __init__(self):
        self.node_means = None
        self.global_mean = 0.0

    def fit(self, X_train: np.ndarray, mask_train: Optional[np.ndarray] = None) -> "HistoricalMeanBaseline":
        """
        Compute historical means.
        
        Parameters
        ----------
        X_train : np.ndarray
            Shape (T, N, 1) or (T, N)
        mask_train : np.ndarray, optional
            Shape (T, N). 1=healthy, 0=failed.
        """
        X = X_train.copy().astype(np.float32)
        
        if mask_train is not None:
            if X.ndim == 3:
                X = np.where(mask_train[:, :, np.newaxis] == 1, X, np.nan)
            else:
                X = np.where(mask_train == 1, X, np.nan)
                
        if X.ndim == 3:
            X = X[:, :, 0]
            
        # Compute mean per node, ignoring NaNs
        self.node_means = np.nanmean(X, axis=0)
        self.global_mean = float(np.nanmean(X))
        
        # Fill completely unobserved nodes with the global mean
        self.node_means = np.where(np.isnan(self.node_means), self.global_mean, self.node_means)
        
        return self

    def predict(self, failed_n: np.ndarray) -> np.ndarray:
        """
        Predict for a list of failed node indices.
        
        Parameters
        ----------
        failed_n : np.ndarray
            1D array of node indices.
            
        Returns
        -------
        y_pred : np.ndarray
        """
        if self.node_means is None:
            raise ValueError("Model must be fitted before calling predict.")
        return self.node_means[failed_n]


class LOCFBaseline:
    """
    Last Observation Carried Forward (LOCF).
    Predicts the missing value by using the last known healthy observation 
    for that sensor in the recent past.
    """
    
    def __init__(self):
        self.global_mean = 0.0

    def fit(self, X_train: np.ndarray, *args, **kwargs) -> "LOCFBaseline":
        """Fit just stores the global mean as an absolute fallback."""
        if X_train.ndim == 3:
            self.global_mean = float(np.nanmean(X_train[:, :, 0]))
        else:
            self.global_mean = float(np.nanmean(X_train))
        return self

    def predict(
        self, 
        X_test: np.ndarray, 
        mask_test: np.ndarray, 
        failed_t: np.ndarray, 
        failed_n: np.ndarray
    ) -> np.ndarray:
        """
        Predict using the last available observation.
        
        Parameters
        ----------
        X_test : np.ndarray
            The full test tensor (T, N, F).
        mask_test : np.ndarray
            The failure mask for the test tensor (T, N).
        failed_t : np.ndarray
            1D array of time indices for failures.
        failed_n : np.ndarray
            1D array of node indices for failures.
            
        Returns
        -------
        y_pred : np.ndarray
        """
        if X_test.ndim == 3:
            X = X_test[:, :, 0]
        else:
            X = X_test
            
        preds = np.empty(len(failed_t), dtype=np.float32)
        
        for i, (t, n) in enumerate(zip(failed_t, failed_n)):
            val = np.nan
            # Look backwards in time up to 288 steps (1 day) to avoid extreme slowness
            lookback_limit = max(0, t - 288)
            for back_t in range(t - 1, lookback_limit - 1, -1):
                if mask_test[back_t, n] == 1 and not np.isnan(X[back_t, n]):
                    val = X[back_t, n]
                    break
                    
            if np.isnan(val):
                val = self.global_mean
                
            preds[i] = val
            
        return preds
