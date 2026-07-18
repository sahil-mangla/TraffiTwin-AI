import logging
import numpy as np
import pandas as pd
from typing import Tuple
from backend.data.loader import METRLADataLoader
from backend.config import settings

logger = logging.getLogger(__name__)

class StreamSimulator:
    """
    Simulates a real-time data stream by iterating through the METR-LA dataset.
    """
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or settings.data_dir
        self.loader = METRLADataLoader(data_dir=self.data_dir)
        self.X: np.ndarray = None
        self.A: np.ndarray = None
        self.timestamps: pd.DatetimeIndex = None
        self.current_step: int = -1
        self.total_steps: int = 0
        
    def load_data(self):
        """Loads the dataset into memory."""
        logger.info("Loading METR-LA dataset for Stream Simulator...")
        self.loader.load()
        self.X, self.A, self.timestamps = self.loader.get_arrays()
        self.total_steps = len(self.timestamps)
        logger.info(f"Loaded {self.total_steps} time steps across {self.X.shape[1]} sensors.")
        
    def step(self) -> Tuple[np.ndarray, pd.Timestamp]:
        """
        Advances the stream by one time step.
        Returns the ground-truth readings and the timestamp.
        """
        if self.X is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
            
        self.current_step += 1
        
        if self.current_step >= self.total_steps:
            logger.info("End of dataset reached. Wrapping around to beginning.")
            self.current_step = 0
            
        readings = self.X[self.current_step, :, 0]
        timestamp = self.timestamps[self.current_step]
        
        return readings, timestamp

    def get_num_nodes(self) -> int:
        if self.X is None:
            return 207  # Default for METR-LA
        return self.X.shape[1]
        
    def get_adjacency_matrix(self) -> np.ndarray:
        if self.A is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        return self.A
