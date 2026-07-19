# Experiments

Benchmarking and training pipeline for the LightGBM sensor-failure
reconstruction model. Run in order:

1. **`step1_train_baseline.py`** — trains a single LightGBM reconstruction
   model on the METR-LA dataset and saves the checkpoint to
   `backend/models/checkpoints/lightgbm_baseline.pkl` (the path the backend
   API loads at inference time — see `backend/config.py`).
2. **`step2_run_benchmark_suite.py`** — runs the full evaluation sweep
   (Historical Mean, LOCF, LightGBM) across all configured failure rates and
   repetitions (`backend/evaluation/config.py`), writing
   `results/results.csv` and `results/summary.csv`.
3. **`step3_visualize_results.py`** — generates diagnostic and
   publication-quality figures from `results/summary.csv` into
   `results/figures/`. Called automatically at the end of
   `step2_run_benchmark_suite.py`, or run standalone to regenerate figures
   from existing results.

Results and figures land in `results/`; see `docs/benchmark_results.md` for
the write-up of the latest sweep.
