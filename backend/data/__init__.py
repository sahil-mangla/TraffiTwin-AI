"""
TraffiTwin AI — Data Pipeline Package
======================================
METR-LA data loading, preprocessing, failure simulation,
and sliding-window dataset construction for the Reconstruction Agent.
"""

from .loader import METRLADataLoader
from .preprocessing import ZScoreScaler, TimeSeriesSplitter
from .failure_simulator import FailureSimulator

# NOTE: ReconstructionDataset (backend/data/dataset.py) is intentionally NOT
# re-exported here. It imports torch at module level, and torch bundles its
# own libomp.dylib on macOS — loading it into the same process as lightgbm
# and scikit-learn (which also each bundle their own OpenMP runtime) causes
# native segfaults when LightGBM unpickles its checkpoint. Nothing in the
# serving path or benchmark pipeline needs torch; only backend/test_pipeline.py
# uses ReconstructionDataset, and it already imports it directly from
# backend.data.dataset, bypassing this package's eager import.
__all__ = [
    "METRLADataLoader",
    "ZScoreScaler",
    "TimeSeriesSplitter",
    "FailureSimulator",
]
