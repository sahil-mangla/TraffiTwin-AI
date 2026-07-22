import logging
import numpy as np
import pandas as pd
import joblib
from backend.models.feature_engineering import SpatialFeatureEngineer
from backend.models.lightgbm_reconstructor import LightGBMReconstructor
from backend.twin.twin_state import TwinState
from backend.config import settings
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ReconstructionService:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.model_path
        self.model = None
        self.engineer = SpatialFeatureEngineer(max_neighbors=3)
        self.engineer._fitted = True  # Avoid warnings since we only transform

    def load_model(self):
        logger.info(f"Loading LightGBM model from {self.model_path}...")
        try:
            self.model = LightGBMReconstructor.load(self.model_path)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def reconstruct(self, state: TwinState, A: np.ndarray) -> Dict[str, float]:
        """
        Reconstruct values for currently failed sensors in the TwinState.
        Returns a dictionary mapping sensor_id (str) to reconstructed value.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Identify failed sensors
        failed_sensors = np.where(state.masks)[0]
        if len(failed_sensors) == 0:
            return {}

        T, N = state.history.shape
        
        # SpatialFeatureEngineer expects X of shape (T, N, 1)
        X_tensor = state.history.reshape(T, N, 1)
        
        # Engineer expects mask of shape (T, N) where 0=failed, 1=healthy.
        # We assume sensors were healthy in the past history for simplicity, 
        # and only mask the current step T-1.
        mask_matrix = np.ones((T, N), dtype=int)
        
        # Set current step failures to 0
        mask_matrix[-1, failed_sensors] = 0
        
        # Generate timestamps for the history buffer ending at current_timestamp
        # METR-LA is in 5-minute intervals
        if state.current_timestamp is None:
            raise ValueError("TwinState has no current_timestamp.")
            
        freq = pd.Timedelta(minutes=5)
        start_time = state.current_timestamp - freq * (T - 1)
        timestamps = pd.date_range(start=start_time, end=state.current_timestamp, periods=T)
        
        # Call the feature engineer. It will only extract features for the 0s in the mask,
        # which are at time T-1.
        try:
            X_features, _ = self.engineer.transform(
                X=X_tensor,
                mask=mask_matrix,
                A=A,
                timestamps=timestamps,
                max_samples=None
            )
        except Exception as e:
            logger.error(f"Feature engineering failed: {e}")
            return {}
            
        if len(X_features) == 0:
            return {}

        # Predict
        try:
            preds = self.model.predict(X_features)
        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            return {}
            
        reconstructions = {}
        for idx, sensor_id in enumerate(failed_sensors):
            reconstructions[str(sensor_id)] = float(preds[idx])
            
        return reconstructions
