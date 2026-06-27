"""
feature_engineering.py — Spatial Feature Engineering
====================================================
Builds a tabular dataset from the spatio-temporal traffic graph
specifically for training LightGBM on sensor failure reconstruction.
"""

import logging
from typing import Tuple

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

    def fit_transform(
        self, 
        X: np.ndarray, 
        mask: np.ndarray, 
        A: np.ndarray, 
        timestamps: pd.DatetimeIndex,
        max_samples: int = None
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Fit the engineer (optional, for statefulness if needed) and transform data.
        
        Returns
        -------
        X_features : pd.DataFrame
        y_target : np.ndarray
        """
        self._fitted = True
        return self.transform(X, mask, A, timestamps, max_samples)

    def transform(
        self, 
        X: np.ndarray, 
        mask: np.ndarray, 
        A: np.ndarray, 
        timestamps: pd.DatetimeIndex,
        max_samples: int = None
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
        # For nodes not connected, distance is infinity
        distance_matrix = np.where(A > 0, A, np.inf)
        np.fill_diagonal(distance_matrix, 0)
        # Simple shortest path for 2 hops: min(direct, via 1 intermediate)
        # Note: METR-LA A is usually edge weights. We just use A as connectivity/distance proxy.
        # Actually, if A is weight, larger is often closer or further depending on construction.
        # Assuming A > 0 means connected. We'll just rank by A (descending if weight is similarity, ascending if distance).
        # We'll just use the neighbors found in A_upto_2hop.
        
        features_list = []
        targets_list = []
        
        # We need lag up to 12 steps (60 mins)
        start_t = 12
        
        # Find all failures occurring after start_t
        failed_t, failed_n = np.where(mask[start_t:] == 0)
        failed_t += start_t  # Adjust back to absolute time indices
        
        if len(failed_t) > config.MAX_FEATURE_ROWS:
            total_rows = len(failed_t)
            rng = np.random.default_rng(config.RANDOM_SEED)
            idx = rng.choice(total_rows, config.MAX_FEATURE_ROWS, replace=False)
            failed_t = failed_t[idx]
            failed_n = failed_n[idx]
            logger.info(f"Feature cap reached. Sampled {config.MAX_FEATURE_ROWS} rows from {total_rows} total rows.")
        elif max_samples is not None and len(failed_t) > max_samples:
            # Fallback if a different explicit limit is requested
            rng = np.random.default_rng(config.RANDOM_SEED)
            idx = rng.choice(len(failed_t), max_samples, replace=False)
            failed_t = failed_t[idx]
            failed_n = failed_n[idx]
        
        logger.info(f"Extracting features for {len(failed_t)} failed observations...")
        
        # We optimize by pre-extracting temporal features
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
            
            # Rank healthy neighbors (e.g. by direct weight A[n, nb] or just take first K)
            # If A is distance, smaller is better. If A is similarity, larger is better.
            # We'll just sort by direct A if available, else fallback.
            healthy_neighbors.sort(key=lambda nb: A[n, nb] if A[n, nb] > 0 else -1, reverse=True)
            
            # 2. Extract features
            feat_dict = {
                'hour_sin': hour_sin[t],
                'hour_cos': hour_cos[t],
                'day_of_week': day_of_week[t],
                'num_healthy_neighbors': len(healthy_neighbors),
                'node_degree': len(neighbors),
            }
            
            # Average road distance (using A as a proxy)
            if len(healthy_neighbors) > 0:
                feat_dict['avg_road_distance'] = np.mean([A[n, nb] for nb in healthy_neighbors if A[n, nb] > 0])
            else:
                feat_dict['avg_road_distance'] = np.nan
                
            # Aggregate stats from healthy neighbors
            if len(healthy_neighbors) > 0:
                current_speeds = [X[t, nb, 0] for nb in healthy_neighbors]
                feat_dict['mean_speed'] = np.nanmean(current_speeds)
                feat_dict['std_speed'] = np.nanstd(current_speeds) if len(current_speeds) > 1 else 0.0
                feat_dict['min_speed'] = np.nanmin(current_speeds)
                feat_dict['max_speed'] = np.nanmax(current_speeds)
            else:
                feat_dict['mean_speed'] = np.nan
                feat_dict['std_speed'] = np.nan
                feat_dict['min_speed'] = np.nan
                feat_dict['max_speed'] = np.nan

            # For each of the top K healthy neighbors
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
            
            features_list.append(feat_dict)
            targets_list.append(y)
            
        X_features = pd.DataFrame(features_list)
        y_target = np.array(targets_list)
        
        logger.info(f"Generated {len(X_features)} valid tabular samples.")
        return X_features, y_target
