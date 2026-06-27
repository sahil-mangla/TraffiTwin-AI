"""
experiment_runner.py — Experiment Runner & Metrics Aggregation
==============================================================
"""

import os
import pandas as pd
import numpy as np

from backend.evaluation.config import config
from backend.data.preprocessing import TimeSeriesSplitter
from backend.data.failure_simulator import FailureSimulator
from backend.evaluation.baseline_models import HistoricalMeanBaseline, LOCFBaseline
from backend.evaluation.benchmark_metrics import calculate_all_metrics
from backend.models.feature_engineering import SpatialFeatureEngineer
from backend.models.lightgbm_reconstructor import LightGBMReconstructor

class ExperimentRunner:
    def __init__(self, output_dir="experiments/results"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.results = []
        
    def run_benchmark_suite(self, X, A, timestamps):
        splitter = TimeSeriesSplitter(train_ratio=0.70, val_ratio=0.10, test_ratio=0.20)
        train_split, val_split, test_split = splitter.split(X)
        
        t_train = timestamps[:train_split.X.shape[0]]
        t_val = timestamps[train_split.X.shape[0]:train_split.X.shape[0] + val_split.X.shape[0]]
        t_test = timestamps[-test_split.X.shape[0]:]
        
        for rate in config.FAILURE_RATES:
            for run in range(config.N_RUNS):
                # Ensure seed is deterministic for the given run
                seed = config.RANDOM_SEED + run
                
                print("==================================================")
                print("Running Benchmark")
                print("==================================================")
                print(f"Dataset Timesteps : {len(X)}")
                print(f"Failure Rate      : {int(rate * 100)}%")
                print(f"Run               : {run + 1}/{config.N_RUNS}")
                
                # Simulate failures
                sim = FailureSimulator(random_seed=seed)
                train_fail = sim.simulate_mcar(train_split.X, missing_rate=rate)
                val_fail = sim.simulate_mcar(val_split.X, missing_rate=rate)
                test_fail = sim.simulate_mcar(test_split.X, missing_rate=rate)
                
                # Identify test set failures explicitly for baselines
                failed_t, failed_n = np.where(test_fail.mask_matrix == 0)
                
                # Evaluate 1: Historical Mean Baseline
                hm_model = HistoricalMeanBaseline()
                hm_model.fit(train_split.X, train_fail.mask_matrix)
                y_pred_hm = hm_model.predict(failed_n)
                
                if test_split.X.ndim == 3:
                    y_true_test = test_split.X[failed_t, failed_n, 0]
                else:
                    y_true_test = test_split.X[failed_t, failed_n]
                    
                metrics_hm = calculate_all_metrics(y_true_test, y_pred_hm, total_failures=len(failed_t))
                self.add_result("Historical Mean", rate, run + 1, metrics_hm)
                print("Model             : Historical Mean")
                
                # Evaluate 2: LOCF Baseline
                locf_model = LOCFBaseline()
                locf_model.fit(train_split.X)
                y_pred_locf = locf_model.predict(test_split.X, test_fail.mask_matrix, failed_t, failed_n)
                
                metrics_locf = calculate_all_metrics(y_true_test, y_pred_locf, total_failures=len(failed_t))
                self.add_result("LOCF", rate, run + 1, metrics_locf)
                print("Model             : LOCF")
                
                # Evaluate 3: LightGBM Reconstructor
                engineer = SpatialFeatureEngineer(max_neighbors=3)
                
                X_train_df, y_train = engineer.fit_transform(
                    train_split.X, train_fail.mask_matrix, A, t_train, max_samples=None
                )
                
                X_val_df, y_val = engineer.transform(
                    val_split.X, val_fail.mask_matrix, A, t_val, max_samples=None
                )
                
                X_test_df, y_test = engineer.transform(
                    test_split.X, test_fail.mask_matrix, A, t_test, max_samples=None
                )
                
                print("Model             : LightGBM")
                print("==================================================" )
                # Using 500 estimators per user request, early stopping enabled internally
                lgb_model = LightGBMReconstructor(n_estimators=500, n_jobs=1, random_state=seed)
                lgb_model.fit(X_train_df, y_train, eval_set=(X_val_df, y_val))
                
                y_pred_lgb = lgb_model.predict(X_test_df)
                
                # FCR FIX: total_failures must be the raw count of all failed (t,n)
                # cells in the test mask — NOT len(y_test), which is already filtered
                # by the start_t=24 guard inside SpatialFeatureEngineer and loses
                # ~2.97% of events unconditionally. Passing len(y_test) makes FCR
                # measure len(y_pred)/len(y_test) ≈ 100% regardless of true coverage.
                total_test_failures = int((test_fail.mask_matrix == 0).sum())
                metrics_lgb = calculate_all_metrics(y_test, y_pred_lgb, total_failures=total_test_failures)
                
                # If LightGBM recorded a best_iteration_, track it
                if hasattr(lgb_model, 'best_iteration_') and lgb_model.best_iteration_ is not None:
                    metrics_lgb["Best_Iteration"] = lgb_model.best_iteration_

                self.add_result("LightGBM", rate, run + 1, metrics_lgb)
                
        return self.save_results()

    def add_result(self, model: str, failure_rate: float, run: int, metrics: dict):
        """Record the metrics for a single experiment run."""
        self.results.append({
            "model": model,
            "failure_rate": failure_rate,
            "run": run,
            "mae": metrics.get("mae", np.nan),
            "rmse": metrics.get("rmse", np.nan),
            "mape": metrics.get("mape", np.nan),
            "rfs": metrics.get("rfs", np.nan),
            "fcr": metrics.get("fcr", np.nan),
            "best_iteration": metrics.get("Best_Iteration", np.nan)
        })
        
    def save_results(self):
        """Save raw results and aggregated summary to CSV."""
        df = pd.DataFrame(self.results)
        df.to_csv(os.path.join(self.output_dir, "results.csv"), index=False)
        
        # Aggregate statistics
        agg_dict = {
            "mae": ["mean", "std"],
            "rmse": ["mean", "std"],
            "mape": ["mean", "std"],
            "rfs": ["mean"],
            "fcr": ["mean"]
        }
        
        if "best_iteration" in df.columns:
            agg_dict["best_iteration"] = ["mean"]
            
        summary = df.groupby(["model", "failure_rate"]).agg(agg_dict)
        
        # Flatten MultiIndex columns
        summary.columns = [f"{col[0].upper()}_{col[1]}" if col[0] != "best_iteration" else "Best_Iteration_mean" for col in summary.columns.values]
        summary = summary.reset_index()
        
        summary.to_csv(os.path.join(self.output_dir, "summary.csv"), index=False)
        return df, summary
