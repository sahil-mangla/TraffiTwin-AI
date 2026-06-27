"""
benchmark_metrics.py — Evaluation Metrics
===========================================
Re-exports the core Evaluator for use in the benchmarking pipeline.
"""

from backend.models.evaluator import Evaluator

def calculate_all_metrics(y_true, y_pred, y_hist_mean=None, total_failures=None):
    return Evaluator.calculate_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_historical_mean=y_hist_mean,
        total_failures=total_failures
    )
