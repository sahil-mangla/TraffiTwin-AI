"""
evaluator.py — TraffiTwin AI Evaluation Metrics
================================================
Implements evaluation metrics for the Reconstruction Agent, including
standard regression metrics and domain-specific metrics like RFS and FCR.
"""

import numpy as np
from typing import Dict, Optional

class Evaluator:
    """
    Evaluator for traffic reconstruction models.
    """

    @staticmethod
    def calculate_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_historical_mean: Optional[np.ndarray] = None,
        total_failures: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calculate reconstruction metrics.
        
        Parameters
        ----------
        y_true : np.ndarray
            True traffic speed values.
        y_pred : np.ndarray
            Predicted traffic speed values by the model.
        y_historical_mean : np.ndarray, optional
            Predictions from a naive historical mean baseline, used for RFS.
        total_failures : int, optional
            Total number of missing/failed data points in the dataset. 
            Used for FCR.
            
        Returns
        -------
        Dict[str, float]
            Dictionary containing mae, rmse, mape, rfs, and fcr.
        """
        # Remove NaN or zero from true values for MAPE calculation (avoid div by zero)
        mask = (y_true > 0) & ~np.isnan(y_true) & ~np.isnan(y_pred)
        y_true_valid = y_true[mask]
        y_pred_valid = y_pred[mask]
        
        if len(y_true_valid) == 0:
            return {"mae": np.nan, "rmse": np.nan, "mape": np.nan, "rfs": np.nan, "fcr": 0.0}

        mae = np.mean(np.abs(y_true_valid - y_pred_valid))
        rmse = np.sqrt(np.mean((y_true_valid - y_pred_valid) ** 2))
        mape = np.mean(np.abs((y_true_valid - y_pred_valid) / y_true_valid)) * 100.0

        rfs = np.nan
        if y_historical_mean is not None:
            hist_mask = (y_true > 0) & ~np.isnan(y_true) & ~np.isnan(y_historical_mean)
            y_true_hist = y_true[hist_mask]
            y_pred_hist = y_historical_mean[hist_mask]
            if len(y_true_hist) > 0:
                mape_hist = np.mean(np.abs((y_true_hist - y_pred_hist) / y_true_hist)) * 100.0
                if mape_hist > 0:
                    rfs = 1.0 - (mape / mape_hist)

        fcr = 100.0
        if total_failures is not None and total_failures > 0:
            fcr = (len(y_pred) / total_failures) * 100.0

        return {
            "mae": float(mae),
            "rmse": float(rmse),
            "mape": float(mape),
            "rfs": float(rfs),
            "fcr": float(fcr)
        }
