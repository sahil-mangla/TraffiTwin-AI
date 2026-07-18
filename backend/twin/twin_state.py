import numpy as np
from typing import Dict, Optional
import pandas as pd
import logging

from backend.core.exceptions import SensorNotFoundError, InvalidSimulationStepError

logger = logging.getLogger(__name__)

class TwinState:
    """
    Maintains the live state of the traffic Digital Twin.
    It holds the recent history of readings necessary for feature engineering,
    as well as current failures and reconstructions.
    """
    def __init__(self, num_nodes: int, history_size: int = 25):
        self.num_nodes = num_nodes
        self.history_size = history_size
        self.current_time_step: int = -1
        self.current_timestamp: Optional[pd.Timestamp] = None
        
        # Buffer to keep the last `history_size` readings. 
        # Shape: (history_size, num_nodes)
        self.history = np.full((history_size, num_nodes), np.nan)
        
        # Current active failures (True means failed/masked)
        # Shape: (num_nodes,)
        self.masks = np.zeros(num_nodes, dtype=bool)
        
        # Keep track of how many steps a failure has left
        self.failure_timers = np.zeros(num_nodes, dtype=int)
        
        # Store the latest reconstructed values. Keys are string node IDs.
        self.reconstructions: Dict[str, float] = {}

    def update_readings(self, readings: np.ndarray, timestamp: pd.Timestamp):
        """
        Push new ground-truth readings into the history buffer, and update time.
        readings should be of shape (num_nodes,)
        """
        self.current_time_step += 1
        self.current_timestamp = timestamp
        
        # Shift history up by one
        self.history[:-1, :] = self.history[1:, :]
        # Add new readings at the end (the "present")
        self.history[-1, :] = readings
        
        # Update failure timers
        self._decrement_failure_timers()
        
    def _decrement_failure_timers(self):
        """Decrement the timer for active failures and heal if timer reaches 0."""
        active_failures = self.failure_timers > 0
        self.failure_timers[active_failures] -= 1
        
        # Heal sensors where timer reached 0
        healed_nodes = np.where((self.masks == True) & (self.failure_timers == 0))[0]
        for node in healed_nodes:
            self.heal_sensor(node)

    def inject_failure(self, sensor_id: int, duration: int):
        """
        Inject a failure for a given sensor ID and duration (in steps).
        """
        if sensor_id < 0 or sensor_id >= self.num_nodes:
            raise SensorNotFoundError(sensor_id)
        if duration <= 0:
            raise InvalidSimulationStepError("Failure duration must be greater than 0")
        
        self.masks[sensor_id] = True
        self.failure_timers[sensor_id] = duration
        logger.info(f"Injected failure on sensor {sensor_id} for {duration} steps.")

    def heal_sensor(self, sensor_id: int):
        """
        Heal a previously failed sensor.
        """
        self.masks[sensor_id] = False
        self.failure_timers[sensor_id] = 0
        self.reconstructions.pop(str(sensor_id), None)
        logger.info(f"Sensor {sensor_id} healed.")

    def get_current_readings(self) -> np.ndarray:
        """Get the ground truth readings for the current time step."""
        return self.history[-1, :]

    def get_snapshot(self) -> Dict:
        """
        Return a snapshot of the current state.
        """
        readings = self.get_current_readings()
        readings_dict = {str(i): float(readings[i]) for i in range(self.num_nodes) if not np.isnan(readings[i])}
        masks_dict = {str(i): bool(self.masks[i]) for i in range(self.num_nodes)}
        
        return {
            "current_time": self.current_time_step,
            "readings": readings_dict,
            "masks": masks_dict,
            "reconstructions": self.reconstructions.copy()
        }
