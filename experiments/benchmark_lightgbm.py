"""
benchmark_lightgbm.py
=====================
Alias/entry point for running the LightGBM benchmarks.
"""

import os
import sys

# Ensure experiments module can be resolved
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_experiments import run_benchmark

if __name__ == "__main__":
    run_benchmark()
