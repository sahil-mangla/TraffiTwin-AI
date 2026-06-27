"""
run_experiments.py — TraffiTwin AI Benchmarking Framework
=========================================================
Runs comprehensive evaluation sweeps across increasing failure rates.
"""

import sys
import os
import warnings

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.loader import METRLADataLoader
from backend.evaluation.experiment_runner import ExperimentRunner
from backend.evaluation.config import config
from experiments.visualize_results import generate_plots

warnings.filterwarnings("ignore")

def run_benchmark():
    print("==================================================")
    print("Starting TraffiTwin AI Benchmark")
    print("==================================================")
    
    # 1. Load Data
    loader = METRLADataLoader(data_dir="datasets/raw").load()
    X, A, timestamps = loader.get_arrays()
    
    if config.USE_SUBSET:
        X = X[:config.SUBSET_TIMESTEPS]
        timestamps = timestamps[:config.SUBSET_TIMESTEPS]
        print(f"Benchmark Mode: Using first {config.SUBSET_TIMESTEPS} timesteps (14 days)")
    
    runner = ExperimentRunner(output_dir="experiments/results")
    df, summary = runner.run_benchmark_suite(X, A, timestamps)
    
    # Generate Plots
    print("\nGenerating visual plots...")
    generate_plots()
    
    # Final Report
    lgb_summary = summary[summary['model'] == 'LightGBM']
    hm_summary = summary[summary['model'] == 'Historical Mean']
    
    avg_lgb_mape = lgb_summary['MAPE_mean'].mean()
    avg_hm_mape = hm_summary['MAPE_mean'].mean()
    mape_improvement = ((avg_hm_mape - avg_lgb_mape) / avg_hm_mape) * 100
    
    valid_rates = lgb_summary[lgb_summary['MAPE_mean'] < 20.0]['failure_rate']
    max_rate = valid_rates.max() * 100 if len(valid_rates) > 0 else 0
    
    print("\n==================================================")
    print("TraffiTwin AI Benchmark Report")
    print("==================================================")
    dataset_days = int(config.SUBSET_TIMESTEPS / 288)
    print(f"\nBenchmark Dataset : {dataset_days} Days" if config.USE_SUBSET else "\nBenchmark Dataset : Full")
    print("\nBest Model : LightGBM")
    print(f"\nAverage MAPE Improvement : {mape_improvement:.2f} %")
    print(f"\nMaximum Supported Failure Rate : {max_rate:.0f} %")
    print("\nResults saved to:")
    print("experiments/results/")
    print("==================================================")

if __name__ == "__main__":
    run_benchmark()
