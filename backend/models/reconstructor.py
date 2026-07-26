"""
reconstructor.py — Reconstructor Interface
============================================
Defines the contract any traffic-speed reconstruction model must satisfy so
that callers (e.g. ReconstructionService) depend on this interface instead
of a specific model implementation such as LightGBMReconstructor.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd


class Reconstructor(ABC):
    """Abstract base class for traffic-speed reconstruction models."""

    @abstractmethod
    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        eval_set: Optional[Tuple[pd.DataFrame, np.ndarray]] = None,
        early_stopping_rounds: int = 50,
    ) -> "Reconstructor":
        ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        ...

    @abstractmethod
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
        y_historical_mean: Optional[np.ndarray] = None,
        total_failures: Optional[int] = None,
    ) -> Dict[str, float]:
        ...

    @abstractmethod
    def save(self, path: str | Path) -> None:
        ...

    @classmethod
    @abstractmethod
    def load(cls, path: str | Path) -> "Reconstructor":
        ...
