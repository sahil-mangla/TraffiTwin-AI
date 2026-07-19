# Benchmark Results: Spatio-Temporal Reconstruction

This document presents a comprehensive benchmark report of the self-healing models in TraffiTwin AI.

---

## 1. Experimental Setup

To validate reconstruction accuracy and outage resilience, we established a rigorous benchmarking suite running on real-world traffic telemetry:

*   **Dataset**: METR-LA (Los Angeles highway traffic speed sensor network, 207 sensors).
*   **Benchmark Window**: 14 days of continuous observations (4,032 timesteps at 5-minute sampling resolution).
*   **Failure Rates**: Missing Completely at Random (MCAR) failure rates evaluated at:
    *   **5%** sensor outage
    *   **10%** sensor outage
    *   **20%** sensor outage
    *   **30%** sensor outage
    *   **40%** sensor outage
*   **Runs per setting**: 5 independent runs per failure rate configuration (using deterministic seeds) to capture mean and standard deviation variations.
*   **Train/Val/Test Split**: Temporal partition of **70% training, 10% validation, and 20% testing**, preserving chronological order to prevent information leakage.

---

## 2. Models Evaluated

The benchmarking framework evaluates four distinct reconstruction methodologies:

1.  **Historical Mean (Naive Baseline)**: Imputes missing values at a failed node using its historical daily profile computed over the training set.
2.  **Last Observation Carried Forward (LOCF)**: Imputes missing values using the last available valid reading of the failed sensor before the outage occurred.
3.  **Spatial LightGBM**: A gradient-boosted tree model utilizing spatial topology features (e.g., neighbor speeds at current step $t$) but lacking extensive historical rolling window statistics.
4.  **Spatio-Temporal LightGBM**: Our proposed reconstruction agent leveraging spatial neighbor aggregates, rolling temporal statistics, multi-step lags, motion trends, and cyclical calendar embeddings.

---

## 3. Benchmark Tables

Below is the summary of results aggregated over 5 repetitions across all failure rates.

### 3.1 Mean Absolute Error (MAE)
| Model | 5% Outage | 10% Outage | 20% Outage | 30% Outage | 40% Outage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Historical Mean** | 9.97 ± 0.09 | 9.94 ± 0.06 | 9.93 ± 0.03 | 9.95 ± 0.03 | 9.94 ± 0.04 |
| **LOCF** | 3.05 ± 0.08 | 3.05 ± 0.06 | 3.11 ± 0.04 | 3.18 ± 0.04 | 3.27 ± 0.02 |
| **Spatial LightGBM** | 5.75 ± 0.12 | 5.78 ± 0.10 | 5.82 ± 0.08 | 5.88 ± 0.07 | 5.95 ± 0.05 |
| **Spatio-Temporal LightGBM** | **2.51 ± 0.04** | **2.50 ± 0.02** | **2.50 ± 0.02** | **2.51 ± 0.02** | **2.53 ± 0.01** |

### 3.2 Root Mean Squared Error (RMSE)
| Model | 5% Outage | 10% Outage | 20% Outage | 30% Outage | 40% Outage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Historical Mean** | 12.94 ± 0.12 | 12.90 ± 0.10 | 12.90 ± 0.06 | 12.92 ± 0.05 | 12.91 ± 0.03 |
| **LOCF** | 5.92 ± 0.19 | 5.87 ± 0.19 | 6.05 ± 0.15 | 6.22 ± 0.16 | 6.48 ± 0.08 |
| **Spatial LightGBM** | 9.15 ± 0.20 | 9.20 ± 0.18 | 9.25 ± 0.15 | 9.32 ± 0.12 | 9.42 ± 0.10 |
| **Spatio-Temporal LightGBM** | **4.32 ± 0.06** | **4.28 ± 0.06** | **4.32 ± 0.04** | **4.34 ± 0.06** | **4.35 ± 0.03** |

### 3.3 Mean Absolute Percentage Error (MAPE)
| Model | 5% Outage | 10% Outage | 20% Outage | 30% Outage | 40% Outage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Historical Mean** | 28.19% ± 0.61% | 28.03% ± 0.53% | 28.05% ± 0.28% | 28.17% ± 0.30% | 28.11% ± 0.13% |
| **LOCF** | 6.88% ± 0.23% | 6.89% ± 0.12% | 7.05% ± 0.07% | 7.29% ± 0.16% | 7.58% ± 0.10% |
| **Spatial LightGBM** | 13.92% ± 0.35% | 14.01% ± 0.28% | 14.10% ± 0.22% | 14.22% ± 0.18% | 14.38% ± 0.15% |
| **Spatio-Temporal LightGBM** | **6.03% ± 0.16%** | **5.96% ± 0.08%** | **6.02% ± 0.06%** | **6.05% ± 0.10%** | **6.09% ± 0.07%** |

### 3.4 Recovery Fidelity Score (RFS)
*Higher is better. Measures improvement over naive Historical Mean baseline.*
| Model | 5% Outage | 10% Outage | 20% Outage | 30% Outage | 40% Outage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Spatial LightGBM** | 0.51 | 0.50 | 0.50 | 0.49 | 0.49 |
| **Spatio-Temporal LightGBM** | **0.786** | **0.787** | **0.785** | **0.785** | **0.783** |

> [!NOTE]
> RFS in this table comes from a separate one-off run (`experiments/step1_train_baseline.py`), not the 5-run sweep in `experiments/step2_run_benchmark_suite.py`. The sweep's `experiment_runner.py` currently calls `Evaluator.calculate_metrics` without a `y_historical_mean` argument for the LightGBM rows, so `RFS_mean` is `NaN` in `results/summary.csv` for every failure rate — RFS is not yet computed per-rate across repetitions. Wiring that in (passing the Historical-Mean baseline's predictions on the same test cells into the LightGBM metrics call) would let this table be regenerated directly from the sweep like §3.1–3.3 and §3.5 are.

### 3.5 Failure Coverage Rate (FCR)
*Measures network observability (percentage of missing nodes successfully reconstructed).*
| Model | 5% Outage | 10% Outage | 20% Outage | 30% Outage | 40% Outage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Historical Mean** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| **LOCF** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| **Spatial LightGBM** | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| **Spatio-Temporal LightGBM** | **97.20%** | **97.13%** | **97.06%** | **97.09%** | **97.08%** |

*(Source: `experiments/results/summary.csv`, `FCR_mean` column, regenerated 2026-07-19 after the fix described in §6.)*

---

## 4. Key Findings

1.  **Temporal Continuity Dominates Reconstruction Quality**: Traffic states are highly continuous over short intervals. The first-order lag feature (`failed_node_speed_lag1`) yields the highest correlation and feature importance, anchoring predictions to the sensor's state immediately preceding the outage.
2.  **Lag Features Dramatically Improve Accuracy**: Integrating longer-term temporal dependencies (e.g., `lag3`, `lag6`, `lag12`, `lag24`) enables the model to resolve cyclical trends, reducing MAPE from ~14% (Spatial LightGBM) to ~6% (Spatio-Temporal LightGBM).
3.  **Neighboring Sensors Remain Highly Informative**: Spatial correlation patterns in the METR-LA network remain robust even under massive outage scenarios. Features like `nb_0_speed_t0` (first-hop neighbor speed at the current timestep) ensure that spatial anomalies are properly integrated into the reconstruction.

---

## 5. Leakage Audit Summary

### Status: **ZERO TEMPORAL LEAKAGE DETECTED**

To guarantee absolute scientific validity, the evaluation pipeline enforces a strict information boundary:
*   **No Chronological Shuffling**: Validation and testing sets are strictly split chronologically, ensuring the model never learns from future time intervals to predict past values.
*   **Feature Isolation**: The target node's speed at the current timestep $t$ (`failed_node_speed_t0`) is programmatically excluded, verified by explicit pipeline assertions:
    ```python
    assert 'failed_node_speed_t0' not in feat_dict
    ```
*   **Scaler Isolation**: Scaling parameters are computed *solely* on the training split, preventing forward-looking data contamination.

---

## 6. FCR Audit Summary

An extensive audit of the Failure Coverage Rate (FCR) was completed:
*   **Original FCR Issue**: In early versions, FCR incorrectly used `len(y_test)` as the denominator. Because `y_test` is the post-filtered feature set, this led to a misleading FCR of exactly 100%, masking coverage limitations.
*   **Denominator Correction**: The denominator has been corrected to use the true total count of failed $(t, n)$ cells across the test mask.
*   **Unavoidable 2.97% Coverage Gap**: Due to the 24-timestep warmup requirement of `lag24` (necessary for temporal features), the first 24 timesteps are excluded from reconstruction eligibility.
*   **Final FCR**: After accounting for this warmup exclusion, Spatio-Temporal LightGBM achieves a stable FCR in the **~97.1–97.2%** band across failure rates 5–30%.
*   **Second issue found (2026-07-19)**: at `failure_rate=40%`, FCR was observed to collapse to ~74.8% while MAE/RMSE/MAPE stayed flat — a pipeline artifact, not a model limitation. `SpatialFeatureEngineer.transform`'s `MAX_FEATURE_ROWS=50,000` safety cap was silently subsampling the **test** split whenever the eligible failed-cell count exceeded it (only triggered at the 40% rate for this 14-day/207-sensor configuration), while FCR's denominator used the true uncapped mask count. Fixed by adding an `enforce_cap` parameter so `experiment_runner.py` can request the full, uncapped test set (`enforce_cap=False`) while keeping the cap for train/val extraction speed. Post-fix, FCR at 40% is **97.08%**, consistent with the other rates. Full root-cause writeup: `docs/archive/FCR_AUDIT_REPORT.md` (§7 Addendum).

---

## 7. Scientific Contributions

1.  **Resilience-Driven Evaluation**: Introduces RFS and FCR as core metrics to quantify not just prediction error, but reconstruction completeness and baseline improvements.
2.  **Self-Healing Paradigm**: Establishes a highly efficient, production-grade fallback capable of restoring network observability within milliseconds without waiting for hardware dispatch.
3.  **Benchmark Reproducibility**: Employs deterministic seeding, chronological partitions, and standardized METR-LA pipelines to ensure transparent, reproducible baselines.
