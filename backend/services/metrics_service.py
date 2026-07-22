import collections
import numpy as np
from typing import Dict, Tuple

class MetricsService:
    """
    Tracks rolling metrics for the live Digital Twin.
    """
    def __init__(self, window_size: int = 1000):
        # Keep a rolling queue of (y_true, y_pred)
        self.window_size = window_size
        self.history: collections.deque[Tuple[float, float]] = collections.deque(maxlen=window_size)
        self.total_failures_simulated = 0
        
    def add_reconstructions(self, y_true_dict: Dict[str, float], y_pred_dict: Dict[str, float]):
        """
        Record a set of reconstructions for the current step.
        """
        for sensor_id, y_pred in y_pred_dict.items():
            if sensor_id in y_true_dict:
                y_true = y_true_dict[sensor_id]
                if not np.isnan(y_true):
                    self.history.append((y_true, y_pred))
                    self.total_failures_simulated += 1

    def get_metrics(self) -> Dict[str, float]:
        """Calculate metrics over the current rolling window."""
        if not self.history:
            return {
                "fcr": 0.0,
                "mae": 0.0,
                "rmse": 0.0,
                "total_failures_simulated": self.total_failures_simulated
            }
            
        y_true = np.array([x[0] for x in self.history])
        y_pred = np.array([x[1] for x in self.history])
        
        # Calculate MAE and RMSE
        errors = np.abs(y_true - y_pred)
        mae = float(np.mean(errors))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        
        # Calculate FCR with a tolerance of 5.0 speed units
        # Assuming the same logic as the benchmark
        tolerance = 5.0
        covered = np.sum(errors <= tolerance)
        fcr = float(covered / len(y_true)) * 100.0 if len(y_true) > 0 else 0.0
        
        return {
            "fcr": fcr,
            "mae": mae,
            "rmse": rmse,
            "total_failures_simulated": self.total_failures_simulated
        }
