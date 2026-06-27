from dataclasses import dataclass
from typing import List

@dataclass
class BenchmarkConfig:
    USE_SUBSET: bool = True
    
    # exactly 14 days (METR-LA has 288 samples/day)
    SUBSET_TIMESTEPS: int = 4032
    
    # safety cap only
    MAX_FEATURE_ROWS: int = 50000
    
    FAILURE_RATES: tuple = (0.05, 0.10, 0.20, 0.30, 0.40)
    
    N_RUNS: int = 5
    
    RANDOM_SEED: int = 42
    
    FAILURE_MODE: str = "mcar"
    
    WINDOW_SIZE: int = 12

config = BenchmarkConfig()
