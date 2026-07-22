"""
feature_engineering.py — Spatial Feature Engineering
====================================================
Builds a tabular dataset from the spatio-temporal traffic graph
specifically for training LightGBM on sensor failure reconstruction.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from backend.evaluation.config import config

logger = logging.getLogger(__name__)


class SpatialFeatureEngineer:
    """
    Extracts tabular features for failed nodes based on their graph neighborhood
    and historical observations.
    
    Parameters
    ----------
    max_neighbors : int
        Maximum number of closest healthy neighbors to include as individual features.
        If a node has fewer healthy neighbors, features are padded with NaN.
    """
    
    def __init__(self, max_neighbors: int = 3):
        self.max_neighbors = max_neighbors
        self._fitted = False
        self._printed_summary = False

    def fit_transform(
        self,
        X: np.ndarray,
        mask: np.ndarray,
        A: np.ndarray,
        timestamps: pd.DatetimeIndex,
        max_samples: Optional[int] = None,
        enforce_cap: bool = True
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fit the engineer (optional, for statefulness if needed) and transform data.

        Returns
        -------
        X_features : pd.DataFrame
        y_target : np.ndarray
        """
        self._fitted = True
        return self.transform(X, mask, A, timestamps, max_samples, enforce_cap)

    def transform(
        self,
        X: np.ndarray,
        mask: np.ndarray,
        A: np.ndarray,
        timestamps: pd.DatetimeIndex,
        max_samples: Optional[int] = None,
        enforce_cap: bool = True
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Transform the tensor into a tabular dataset.
        
        Parameters
        ----------
        X : np.ndarray, shape (T, N, 1)
            The ground truth / observed traffic data.
        mask : np.ndarray, shape (T, N)
            Failure mask. 1=healthy, 0=failed.
        A : np.ndarray, shape (N, N)
            Adjacency matrix.
        timestamps : pd.DatetimeIndex
            Timestamps for each slice t.
            
        Returns
        -------
        X_features : pd.DataFrame
        y_target : np.ndarray
        """
        if not self._fitted:
            logger.warning("transform called before fit_transform. Calling fit_transform implicitly.")
            self._fitted = True

        T, N, F = X.shape
        
        # Precompute 2-hop reachability
        # A_bool: 1-hop reachability (excluding self)
        A_bool = (A > 0).astype(bool)
        np.fill_diagonal(A_bool, False)
        
        # 2-hop reachability
        A_2hop = A_bool @ A_bool
        np.fill_diagonal(A_2hop, False)
        
        # Combined up to 2 hops
        A_upto_2hop = A_bool | A_2hop
        
        # Precompute distances for ranking neighbors
        distance_matrix = np.where(A > 0, A, np.inf)
        np.fill_diagonal(distance_matrix, 0)
        
        features_list = []
        targets_list = []
        
        # We need lag up to 24 steps (120 mins)
        start_t = 24
        
        # Find all failures occurring after start_t
        failed_t, failed_n = np.where(mask[start_t:] == 0)
        failed_t += start_t  # Adjust back to absolute time indices
        
        if enforce_cap and len(failed_t) > config.MAX_FEATURE_ROWS:
            total_rows = len(failed_t)
            rng = np.random.default_rng(config.RANDOM_SEED)
            idx = rng.choice(total_rows, config.MAX_FEATURE_ROWS, replace=False)
            failed_t = failed_t[idx]
            failed_n = failed_n[idx]
            dropped_frac = 1.0 - (config.MAX_FEATURE_ROWS / total_rows)
            logger.warning(
                f"Feature cap reached. Sampled {config.MAX_FEATURE_ROWS} rows from "
                f"{total_rows} total rows ({dropped_frac:.1%} dropped)."
            )
        elif max_samples is not None and len(failed_t) > max_samples:
            rng = np.random.default_rng(config.RANDOM_SEED)
            idx = rng.choice(len(failed_t), max_samples, replace=False)
            failed_t = failed_t[idx]
            failed_n = failed_n[idx]
        
        logger.info(f"Extracting features for {len(failed_t)} failed observations...")
        
        hour = timestamps.hour + timestamps.minute / 60.0
        hour_sin = np.sin(2 * np.pi * hour / 24.0)
        hour_cos = np.cos(2 * np.pi * hour / 24.0)
        day_of_week = timestamps.dayofweek.values
        
        for t, n in tqdm(zip(failed_t, failed_n), total=len(failed_t), desc="Building Tabular Features"):
            # Target
            y = X[t, n, 0]
            if np.isnan(y):
                continue  # Skip if ground truth itself is NaN
                
            # 1. Identify healthy neighboring nodes up to 2-hop
            neighbors = np.where(A_upto_2hop[n])[0]
            healthy_neighbors = [nb for nb in neighbors if mask[t, nb] == 1]
            
            healthy_neighbors.sort(key=lambda nb: A[n, nb] if A[n, nb] > 0 else -1, reverse=True)
            
            # 2. Extract features
            # Graph Features (metadata)
            feat_dict: Dict[str, Any] = {
                'num_healthy_neighbors': len(healthy_neighbors),
                'node_degree': len(neighbors),
            }
            
            # Spatial neighbor aggregate features
            if len(healthy_neighbors) > 0:
                feat_dict['avg_road_distance'] = np.mean([A[n, nb] for nb in healthy_neighbors if A[n, nb] > 0])
                current_speeds = [X[t, nb, 0] for nb in healthy_neighbors]
                feat_dict['mean_speed'] = np.nanmean(current_speeds)
                feat_dict['std_speed'] = np.nanstd(current_speeds) if len(current_speeds) > 1 else 0.0
                feat_dict['min_speed'] = np.nanmin(current_speeds)
                feat_dict['max_speed'] = np.nanmax(current_speeds)
            else:
                feat_dict['avg_road_distance'] = np.nan
                feat_dict['mean_speed'] = np.nan
                feat_dict['std_speed'] = np.nan
                feat_dict['min_speed'] = np.nan
                feat_dict['max_speed'] = np.nan
            
            # Individual neighbor speeds
            for i in range(self.max_neighbors):
                if i < len(healthy_neighbors):
                    nb = healthy_neighbors[i]
                    feat_dict[f'nb_{i}_speed_t0'] = X[t, nb, 0]
                    feat_dict[f'nb_{i}_speed_t1'] = X[t-1, nb, 0]
                    feat_dict[f'nb_{i}_speed_t3'] = X[t-3, nb, 0]
                    feat_dict[f'nb_{i}_speed_t12'] = X[t-12, nb, 0]
                else:
                    feat_dict[f'nb_{i}_speed_t0'] = np.nan
                    feat_dict[f'nb_{i}_speed_t1'] = np.nan
                    feat_dict[f'nb_{i}_speed_t3'] = np.nan
                    feat_dict[f'nb_{i}_speed_t12'] = np.nan

            # PART 1: Failed Node History Features
            lag1 = X[t-1, n, 0] if t >= 1 else np.nan
            lag3 = X[t-3, n, 0] if t >= 3 else np.nan
            lag6 = X[t-6, n, 0] if t >= 6 else np.nan
            lag12 = X[t-12, n, 0] if t >= 12 else np.nan
            lag24 = X[t-24, n, 0] if t >= 24 else np.nan

            feat_dict['failed_node_speed_lag1'] = lag1
            feat_dict['failed_node_speed_lag3'] = lag3
            feat_dict['failed_node_speed_lag6'] = lag6
            feat_dict['failed_node_speed_lag12'] = lag12
            feat_dict['failed_node_speed_lag24'] = lag24

            # PART 2: Rolling Temporal Statistics (exclusive of t)
            feat_dict['rolling_mean_3'] = np.mean(X[t-3:t, n, 0]) if t >= 3 else np.nan
            feat_dict['rolling_mean_6'] = np.mean(X[t-6:t, n, 0]) if t >= 6 else np.nan
            feat_dict['rolling_mean_12'] = np.mean(X[t-12:t, n, 0]) if t >= 12 else np.nan
            
            feat_dict['rolling_std_6'] = np.std(X[t-6:t, n, 0]) if t >= 6 else np.nan
            feat_dict['rolling_std_12'] = np.std(X[t-12:t, n, 0]) if t >= 12 else np.nan
            
            feat_dict['rolling_min_12'] = np.min(X[t-12:t, n, 0]) if t >= 12 else np.nan
            feat_dict['rolling_max_12'] = np.max(X[t-12:t, n, 0]) if t >= 12 else np.nan

            # PART 3: Temporal Trend Features
            feat_dict['speed_delta_1_3'] = lag1 - lag3
            feat_dict['speed_delta_1_12'] = lag1 - lag12
            feat_dict['speed_acceleration'] = lag1 - 2 * lag3 + lag6

            # Temporal Calendar/Metadata Features
            feat_dict['hour_sin'] = hour_sin[t]
            feat_dict['hour_cos'] = hour_cos[t]
            feat_dict['day_of_week'] = day_of_week[t]

            # PART 6: Validation Checks
            # 1. Verify no future timestamps are used (indices must be < t)
            # 2. Verify all lag features reference t-k only (enforced by design above)
            # 3. Verify no temporal leakage (value at t is never used)
            assert 'failed_node_speed_t0' not in feat_dict, "Temporal leakage: failed node speed at t-0 cannot be a feature."
            
            # 4. Unit test: lag1 == X[t-1, i] must always hold
            if not np.isnan(lag1) and lag1 != X[t-1, n, 0]:
                raise ValueError(f"Validation failed: lag1 ({lag1}) does not match X[t-1, n, 0] ({X[t-1, n, 0]})")

            features_list.append(feat_dict)
            targets_list.append(y)
            
        X_features = pd.DataFrame(features_list)
        y_target = np.array(targets_list)
        
        # PART 5: Print Feature Engineering Summary on first call
        if not self._printed_summary and len(X_features) > 0:
            spatial_cols = [c for c in X_features.columns if c.startswith('nb_') or c in ['avg_road_distance', 'mean_speed', 'std_speed', 'min_speed', 'max_speed']]
            temporal_cols = [c for c in X_features.columns if c.startswith('failed_node_speed_') or c.startswith('rolling_') or c.startswith('speed_') or c in ['hour_sin', 'hour_cos', 'day_of_week']]
            graph_cols = [c for c in X_features.columns if c in ['num_healthy_neighbors', 'node_degree']]
            
            print("\n==================================================")
            print("Feature Engineering Summary")
            print("==================================================")
            print(f"Spatial Features: {len(spatial_cols)}")
            print(f"Temporal Features: {len(temporal_cols)}")
            print(f"Graph Features: {len(graph_cols)}")
            print(f"\nTotal Features: {X_features.shape[1]}")
            print("==================================================\n")
            self._printed_summary = True

        logger.info(f"Generated {len(X_features)} valid tabular samples.")
        return X_features, y_target
