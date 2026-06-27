# Architecture Overview

This document details the software architecture, component responsibilities, and data processing pipeline implemented in TraffiTwin AI.

---

## 1. High-Level System Architecture

TraffiTwin AI employs a modular, data-driven self-healing architecture designed to process traffic stream data, simulate hardware/network failures, construct spatio-temporal representations, and reconstruct missing observations in real-time.

### Data Flow Diagram

```text
       ┌────────────────────────┐
       │   Real METR-LA Data    │  <-- raw metr-la.h5 + adj_mx.pkl
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   Failure Simulator    │  <-- MCAR and Block-Missing injection
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │ Spatio-Temporal Engine │  <-- Neighborhood aggregates + Lags + Trends
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │ LightGBM Reconstructor │  <-- Virtual sensor speed estimator
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   Evaluation Engine    │  <-- MAE, RMSE, MAPE, RFS, FCR
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   Digital Twin Layer   │  <-- [Upcoming] Real-time visualization
       └────────────────────────┘
```

---

## 2. Component Responsibilities and Code Mapping

The codebase is split into distinct functional modules, each mapped to a specific stage of the self-healing workflow.

### 2.1 Data Ingestion and Loader
*   **Code Location**: [loader.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/data/loader.py), [dataset.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/data/dataset.py)
*   **Responsibility**:
    *   Ingests sensor speed readings and graph topology metadata from raw files.
    *   Parses temporal indexes (5-minute resolution) and constructs the spatial adjacency matrix.
    *   Builds the sliding window datasets ([ReconstructionDataset](file:///Users/sahilmangla/TraffiTwin-AI/backend/data/dataset.py)) to represent historical context.
*   **Interface**: Returns speed arrays of shape `(T, N, F)` and adjacency matrices of shape `(N, N)`.

### 2.2 Failure Simulator
*   **Code Location**: [failure_simulator.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/data/failure_simulator.py)
*   **Responsibility**:
    *   Simulates realistic sensor and camera failures to test the system's resilience.
    *   Supports **Missing Completely at Random (MCAR)** representing random, transient sensor noise/dropouts.
    *   Supports **Block-Missing Outages** representing sustained hardware failures, fiber cuts, or power loss at specific nodes.
*   **Interface**: Emits a masked speed array and a binary health mask matrix of shape `(T, N)` (where `0` denotes failure and `1` denotes healthy).

### 2.3 Spatio-Temporal Feature Engine
*   **Code Location**: [feature_engineering.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/models/feature_engineering.py)
*   **Responsibility**:
    *   Transforms raw multi-dimensional tensors into a tabular format for machine learning.
    *   Extracts spatial features: 1-hop and 2-hop topological neighbor speeds, distance-weighted averages, standard deviations, and boundaries of healthy neighbor nodes.
    *   Extracts temporal features: historical lags (1, 3, 6, 12, 24 steps), rolling statistical windows (means, standard deviations, minimums, maximums), and trend indicators (delta speed, speed acceleration).
    *   Extracts calendar embeddings: cyclical trigonometric encodings of the hour of the day (`hour_sin`, `hour_cos`) and day of the week.
*   **Leakage Prevention**: Enforces a strict boundary ensuring that information from future timesteps or the current failed time step `t` is never leaked.

### 2.4 LightGBM Reconstruction Agent
*   **Code Location**: [lightgbm_reconstructor.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/models/lightgbm_reconstructor.py)
*   **Responsibility**:
    *   Encapsulates the training and inference wrapper for the LightGBM regressor model.
    *   Uses early stopping on validation splits to prevent overfitting.
    *   Saves and loads trained models (`.pkl` format) for edge deployments.
*   **Interface**: Consumes engineered tabular features to predict the speed at failed nodes.

### 2.5 Evaluation Engine
*   **Code Location**: [evaluator.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/models/evaluator.py), [benchmark_metrics.py](file:///Users/sahilmangla/TraffiTwin-AI/backend/evaluation/benchmark_metrics.py)
*   **Responsibility**:
    *   Calculates standard regression accuracy metrics: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE).
    *   Calculates domain-specific resilience metrics: **Recovery Fidelity Score (RFS)** measuring performance improvement over naive historical baselines, and **Failure Coverage Rate (FCR)** measuring model output completeness.

### 2.6 Digital Twin Layer (Upcoming)
*   **Code Location**: [frontend/](file:///Users/sahilmangla/TraffiTwin-AI/frontend)
*   **Responsibility**:
    *   Maintains the real-time spatial graph state.
    *   Combines operational physical camera telemetry with reconstructed speed values from the agent.
    *   Exposes APIs for smart-city systems (e.g., adaptive traffic controls, dynamic routing) and renders the visual digital twin dashboard.

---

## 3. Data Processing Pipeline Lifecycle

The end-to-end data lifecycle guarantees consistency from ingestion to prediction:

```text
[Raw Ingestion] ──> [Temporal Splitting (70/10/20)] ──> [Fit Normalizer (Train Split)]
                                                                  │
                                                                  ▼
[Reconstruct Outputs] <── [LightGBM Inference] <── [Feature Eng.] <── [Apply Failure Simulator]
          │
          ▼
[Denormalize & Validate] ──> [Compute Evaluation Metrics] ──> [Digital Twin Integration]
```

1.  **Temporal Splitting**: Handled by [TimeSeriesSplitter](file:///Users/sahilmangla/TraffiTwin-AI/backend/data/preprocessing.py), ensuring no chronological shuffling to avoid future-to-past data leakage.
2.  **Normalization**: Z-score scaler parameters are fit *exclusively* on the training split, then applied across validation and test splits.
3.  **Denormalization**: Predictions are mapped back to their original physical scale (mph/kph) and validated against physical bounds before serving downstream platforms.
