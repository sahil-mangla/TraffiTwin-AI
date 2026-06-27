# Reconstruction Agent Design
## TraffiTwin AI — Core Component Specification

> **Document Status:** MVP Design v1.0  
> **Dataset:** METR-LA (primary), CityFlow V2 (future integration)  
> **Objective:** Reconstruct missing traffic states at failed sensor nodes using neighboring sensor observations and historical temporal patterns.

---

## 1. Problem Formulation

### 1.1 Formal Definition

Let the traffic sensor network be modelled as a **weighted undirected graph** `G = (V, E, A)` where:

- `V` is the set of `N` sensor nodes (`|V| = N = 207` for METR-LA).
- `E` is the set of edges representing road connectivity between sensors.
- `A ∈ ℝ^(N×N)` is the weighted adjacency matrix, where `A[i][j]` encodes the road network distance (or travel time) between sensors `i` and `j`.

At each discrete time step `t`, the network emits a traffic state matrix:

```
X(t) ∈ ℝ^(N × F)
```

where `F` is the number of feature channels per node (e.g., speed, occupancy).

Given:
- A set of **healthy nodes** `V_h ⊂ V` with known observations.
- A set of **failed nodes** `V_f = V \ V_h` whose observations are missing.
- A historical observation window of `T` past time steps.

**The reconstruction task is:**

```
X̂(t)[V_f] = f_θ( X(t-T:t)[V_h], A, G )
```

Estimate the current traffic state at all failed nodes, conditioned on the current and recent observations of healthy neighbors and the graph topology.

---

### 1.2 Inputs

| Input | Shape | Description |
|-------|-------|-------------|
| Observed sensor readings | `(T, N_h, F)` | Historical window of healthy node states |
| Graph adjacency matrix | `(N, N)` | Weighted road-network connectivity |
| Node mask | `(N,)` | Binary indicator: 1 = healthy, 0 = failed |
| Failure metadata | `(N_f,)` | Which nodes are failed (indices) |
| Time-of-day encoding | `(T,)` | Cyclical encoding of hour/day |

### 1.3 Outputs

| Output | Shape | Description |
|--------|-------|-------------|
| Reconstructed state | `(N_f, F)` | Estimated traffic state at failed nodes |
| Confidence scores | `(N_f,)` | Per-node reconstruction uncertainty (optional, advanced) |

### 1.4 Assumptions

1. **Spatial correlation holds:** Traffic state at a failed node is correlated with the states at its topological neighbors within a bounded road distance.
2. **Temporal smoothness:** Traffic conditions change gradually; abrupt shifts are rare within short windows (5–15 minutes).
3. **Failures are exogenous:** Sensor failures are independent of traffic state (a sensor does not fail *because* of extreme traffic).
4. **Graph is static:** Road network topology does not change during operation (valid for MVP scope).
5. **Partial observability:** At least one neighbor within the 2-hop graph neighborhood of any failed node remains healthy.

### 1.5 Missing Data Patterns

The agent must be robust to the following failure regimes, listed by increasing severity:

| Pattern | Description | Example |
|---------|-------------|---------|
| **MCAR** (Missing Completely at Random) | Random node failures, independent of time or location | Sporadic hardware glitches |
| **Block Missing** | A single node fails for a continuous temporal block | Power outage (hours) |
| **Spatial Cluster Failure** | Geographically co-located nodes fail simultaneously | Fiber cable cut, network partition |
| **Multiple Isolated Failures** | Multiple non-adjacent nodes fail independently | Multiple concurrent hardware faults |

> **MVP focus:** MCAR and Block Missing patterns, following community-standard simulation protocols used in METR-LA literature.

---

## 2. Traffic State Representation

### 2.1 Node State Definition

Each sensor node `i` at time `t` is represented by a feature vector:

```python
node_state = {
    "speed":      float,   # average vehicle speed (km/h or mph)
    "occupancy":  float,   # road occupancy ratio [0.0, 1.0]
    "timestamp":  int,     # Unix epoch seconds
    "time_of_day": float,  # sin/cos encoded hour [0.0, 1.0]
    "day_of_week": int,    # 0=Monday, 6=Sunday
    "node_id":    int,     # sensor node index in graph
    "is_healthy": bool     # True if sensor is operational
}
```

> **METR-LA MVP:** Uses `speed` as the single feature channel (`F=1`). Multi-feature extension (speed + occupancy + flow) is reserved for CityFlow integration.

### 2.2 Graph State Schema

```python
graph_state = {
    "timestamp":    int,             # snapshot time
    "node_features": np.ndarray,     # shape: (N, F) — full state matrix
    "node_mask":    np.ndarray,      # shape: (N,)  — 1=healthy, 0=failed
    "adj_matrix":   np.ndarray,      # shape: (N, N) — weighted adjacency
    "failed_nodes": List[int],       # indices of failed nodes
    "healthy_nodes": List[int]       # indices of operational nodes
}
```

### 2.3 Data Normalization

All feature channels are normalized using **z-score normalization** computed on the training split:

```python
X_normalized = (X - μ_train) / σ_train
```

Reconstruction outputs are denormalized before evaluation and digital twin update:

```python
X_reconstructed = X̂_normalized * σ_train + μ_train
```

### 2.4 Historical Window Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `T` (lookback window) | 12 steps | Standard METR-LA protocol (60 minutes at 5-min intervals) |
| `Δt` (sampling interval) | 5 minutes | METR-LA native resolution |
| Feature channels `F` | 1 (speed) | MVP scope; extensible to 3 |

---

## 3. Baseline Model

### 3.1 Recommendation: **LightGBM with Spatial Feature Engineering**

**Rationale:**

LightGBM is recommended as the baseline over XGBoost and Random Forest for the following reasons:

| Criterion | LightGBM | XGBoost | Random Forest |
|-----------|:--------:|:-------:|:-------------:|
| Training speed | ✅ Fastest | ⚠️ Medium | ❌ Slowest |
| Missing data handling | ✅ Native | ✅ Native | ⚠️ Requires imputation |
| Histogram-based learning | ✅ Yes | ✅ Yes (recent) | ❌ No |
| Memory efficiency | ✅ High | ⚠️ Medium | ❌ Low |
| Established traffic baselines | ✅ Yes | ✅ Yes | ⚠️ Fewer |
| Implementation complexity | ✅ Low | ✅ Low | ✅ Low |

### 3.2 Feature Engineering for LightGBM

For each failed node `i`, construct a tabular feature vector from:

```python
features = [
    # Temporal features
    time_of_day_sin,          # sin(2π * hour / 24)
    time_of_day_cos,          # cos(2π * hour / 24)
    day_of_week,              # integer 0–6
    is_weekend,               # boolean

    # Neighbor spatial features (for each k-hop neighbor j)
    speed_t_neighbor_j,       # current speed at neighbor j
    speed_lag1_neighbor_j,    # speed 5 min ago at neighbor j
    speed_lag3_neighbor_j,    # speed 15 min ago at neighbor j
    speed_lag12_neighbor_j,   # speed 60 min ago at neighbor j

    # Neighbor aggregated statistics
    neighbor_speed_mean,      # mean speed across 1-hop neighbors
    neighbor_speed_std,       # speed variance across neighbors
    neighbor_speed_min,       # minimum speed (congestion proxy)
    neighbor_speed_max,       # maximum speed (free flow proxy)

    # Graph structural features
    road_distance_to_neighbor, # weighted edge distance
    num_healthy_neighbors,     # degree of healthy neighbors
]
```

### 3.3 Training Strategy

- **Train:** One LightGBM regressor per feature channel (one model for speed).
- **Target:** The ground-truth speed at node `i` at time `t`.
- **Missing simulation:** Mask node `i` during training, use only neighbor features.
- **Validation:** Standard 70/10/20 split by time (no shuffling — respect temporal order).

```python
import lightgbm as lgb

model = lgb.LGBMRegressor(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)
```

**Expected implementation time:** ~1 day including feature engineering.

---

## 4. Advanced Model

### 4.1 Recommendation: **GRIN — Graph Recurrent Imputation Network**

**Architecture:** Bidirectional Graph Convolutional Recurrent Network with spatial message passing.

**Why GRIN for TraffiTwin AI:**

1. **Designed exactly for this task.** GRIN (Cini et al., NeurIPS 2022) was purpose-built for traffic state imputation with missing node data — it is not a repurposed forecasting model.
2. **State-of-the-art on METR-LA.** GRIN achieves competitive MAE/RMSE on METR-LA under both MCAR and block-missing regimes, outperforming standard GCN-based approaches.
3. **Graph-aware.** It explicitly leverages the adjacency matrix `A` to propagate information from healthy neighbors to failed nodes, matching the spatial reconstruction paradigm of TraffiTwin AI exactly.
4. **Bidirectional temporal processing.** Uses both forward and backward GRU passes, capturing past trends and future context for more accurate hole-filling.

### 4.2 Architecture Overview

```
Input: X_masked (T, N, F) + Mask M (T, N) + Adjacency A (N, N)
         │
         ▼
┌─────────────────────────────┐
│  Spatial Message Passing    │  ← GraphConv(A) aggregates
│  (Graph Convolutional Layer)│    healthy neighbor features
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Bidirectional GRU          │  ← Forward + Backward recurrence
│  (Temporal Processing)      │    over T time steps
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Reconstruction Head        │  ← Linear projection → (N_f, F)
│  (MLP per failed node)      │
└─────────────────────────────┘
         │
         ▼
Output: X̂ (N_f, F) — reconstructed states at failed nodes
```

### 4.3 Lightweight Alternative: **STGCN Imputer**

If GRIN proves too complex to implement from scratch under hackathon time pressure, a **Spatio-Temporal Graph Convolutional Network (STGCN)** adapted for imputation serves as an excellent intermediate option:

- Replace the temporal convolution output with a masked reconstruction loss.
- Apply only to the subgraph of failed nodes conditioned on healthy neighbors.
- Implementable in ~2–3 days using PyTorch Geometric.

### 4.4 Complexity and Feasibility

| Factor | GRIN | STGCN Imputer |
|--------|------|---------------|
| Implementation effort | High (3–5 days) | Medium (2–3 days) |
| Published code available | ✅ Yes (GitHub) | ✅ Yes |
| METR-LA baseline published | ✅ Yes | ✅ Yes |
| Hyperparameter sensitivity | Medium | Low |
| Training time (GPU) | ~2–4 hrs | ~1–2 hrs |
| Research novelty | High | Medium |

> **Hackathon strategy:** Use the official GRIN repository as a starting point; adapt the data loader for TraffiTwin AI's failure simulation and evaluation harness. This avoids implementing from scratch.

---

## 5. Reconstruction Agent Pipeline

### 5.1 Full Pipeline Workflow

```
HEALTHY SENSOR STREAM
        │
        │  Real-time telemetry at 5-min intervals
        ▼
┌────────────────────────┐
│   Data Buffer          │  Sliding window buffer: last T=12 steps
│   (Ring Buffer)        │  Shape: (T, N, F)
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Health Monitor Signal │  ← Incoming from Health Monitoring Agent
│  (Node Failure Alert)  │  Failed node indices: V_f = {i₁, i₂, ...}
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Mask Application      │  Zero out X[V_f, :] in buffer
│                        │  Set M[V_f] = 0 (failed), M[V_h] = 1
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Neighbor Selection    │  For each v ∈ V_f:
│                        │  - Extract k-hop neighbors from A
│                        │  - Filter to healthy neighbors only
│                        │  - Rank by edge weight (road proximity)
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Feature Extraction    │  Construct input features:
│                        │  - Neighbor temporal readings (T steps)
│                        │  - Time encoding (sin/cos)
│                        │  - Graph structural features
│                        │  - Mask vector M
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Model Inference       │  X̂[V_f] = f_θ(X[V_h], A, M, t)
│  (LightGBM → GRIN)    │  Select model tier based on failure type
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Denormalization       │  X̂_real = X̂_norm * σ + μ
│  & Validation          │  Clip to physical bounds [0, speed_limit]
└────────────────────────┘
        │
        ▼
┌────────────────────────┐
│  Digital Twin Update   │  Merge X̂[V_f] with X[V_h]
│                        │  Publish unified state to dashboard API
└────────────────────────┘
        │
        ▼
DIGITAL TWIN: UNIFIED TRAFFIC STATE (All N nodes active)
```

### 5.2 Neighbor Selection Logic

```python
def select_neighbors(failed_node: int, adj_matrix: np.ndarray,
                     healthy_mask: np.ndarray, k_hops: int = 2) -> List[int]:
    """
    Select k-hop healthy neighbors for a failed node,
    ranked by proximity (edge weight).
    """
    neighbors = set()
    frontier = {failed_node}
    for _ in range(k_hops):
        next_frontier = set()
        for node in frontier:
            connected = np.where(adj_matrix[node] > 0)[0]
            healthy_connected = [n for n in connected if healthy_mask[n] == 1]
            neighbors.update(healthy_connected)
            next_frontier.update(connected)
        frontier = next_frontier - neighbors
    # Rank by road distance (descending edge weight = closer proximity)
    return sorted(neighbors, key=lambda n: adj_matrix[failed_node][n], reverse=True)
```

### 5.3 Model Tier Selection

```python
def select_model_tier(failure_pattern: str, n_failed: int) -> str:
    """
    Adaptive model selection based on failure characteristics.
    """
    if failure_pattern == "MCAR" and n_failed <= 5:
        return "lightgbm"       # Fast, sufficient for sparse random failures
    elif failure_pattern == "block_missing":
        return "grin"           # Temporal depth required for sustained outages
    elif n_failed > 10:
        return "grin"           # Spatial complexity requires graph-aware model
    else:
        return "lightgbm"       # Default to fast baseline
```

---

## 6. Evaluation Metrics

### 6.1 Standard Reconstruction Accuracy Metrics

These are the community-standard metrics for METR-LA benchmarking and enable direct comparison with published literature.

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **MAE** | `mean(|y - ŷ|)` | Average absolute reconstruction error (km/h) |
| **RMSE** | `sqrt(mean((y - ŷ)²))` | Penalizes large errors more than MAE |
| **MAPE** | `mean(|y - ŷ| / y) × 100` | Percentage error; scale-invariant |

```python
def evaluate_reconstruction(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mae  = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
    return {"MAE": mae, "RMSE": rmse, "MAPE": mape}
```

> **Target thresholds (from METR-LA literature):**  
> MAE < 3.5 mph | RMSE < 7.0 mph | MAPE < 10%

### 6.2 Resilience-Specific Metrics

These metrics are novel to TraffiTwin AI and directly quantify the self-healing behavior — suitable for research contribution and hackathon differentiation.

| Metric | Definition | Why It Matters |
|--------|-----------|----------------|
| **Recovery Fidelity Score (RFS)** | `1 - MAPE_failed / MAPE_baseline` | Measures reconstruction quality relative to a naive baseline (e.g., historical mean) |
| **Neighbor Dependency Ratio (NDR)** | `n_healthy_neighbors / total_neighbors` | Quantifies reconstruction confidence based on available topology |
| **Failure Coverage Rate (FCR)** | `n_reconstructed / n_failed × 100%` | % of failed nodes successfully reconstructed (vs. left as null) |
| **Reconstruction Latency** | `ms per inference call` | End-to-end time from failure detection to digital twin update |
| **State Drift Index (SDI)** | `mean(|X̂(t) - X(t-1)|)` over sustained failures | Measures stability of reconstruction over long outages |

```python
def recovery_fidelity_score(y_true, y_pred, y_baseline) -> float:
    """
    RFS: how much better is the model vs. a naive baseline?
    RFS = 1.0 → perfect reconstruction
    RFS = 0.0 → no better than baseline
    RFS < 0.0 → worse than baseline (failure case)
    """
    mape_model    = np.mean(np.abs((y_true - y_pred)     / (y_true + 1e-8)))
    mape_baseline = np.mean(np.abs((y_true - y_baseline) / (y_true + 1e-8)))
    return 1.0 - (mape_model / (mape_baseline + 1e-8))
```

---

## 7. MVP Implementation Strategy

### 7.1 Implement First (Week 1–2)

| Priority | Component | Rationale |
|----------|-----------|-----------|
| ✅ P0 | METR-LA data loader with graph adjacency | Foundation for all experiments |
| ✅ P0 | Block-missing and MCAR failure simulation | Required to generate training/evaluation data |
| ✅ P0 | LightGBM baseline with spatial feature engineering | Fast, strong benchmark; demonstrates the concept end-to-end |
| ✅ P0 | MAE/RMSE/MAPE evaluation harness | Required for any result claim |
| ✅ P1 | Neighbor selection module | Shared by both baseline and advanced models |
| ✅ P1 | Denormalization and output validation | Prevents physically impossible outputs |

### 7.2 Implement Second (Week 3–4)

| Priority | Component | Rationale |
|----------|-----------|-----------|
| ✅ P1 | GRIN or STGCN imputer (from published code) | Core research contribution |
| ✅ P1 | Resilience metrics (RFS, FCR, Latency) | Differentiator for hackathon judging |
| ✅ P2 | Model tier selection logic | Enables adaptive pipeline demo |
| ✅ P2 | REST API endpoint for digital twin output | Integration with frontend dashboard |

### 7.3 Postpone (Post-MVP)

| Component | Reason to Defer |
|-----------|-----------------|
| Uncertainty / confidence estimation | Adds complexity without improving demo impact |
| Online learning / real-time model updating | Significant infrastructure overhead |
| CityFlow visual integration | Requires camera feature engineering pipeline |
| Multi-feature (speed + occupancy + flow) | Extends scope beyond METR-LA MVP |
| Model ensembling | Diminishing returns vs. implementation cost |

### 7.4 Avoid Entirely

| Anti-Pattern | Why to Avoid |
|-------------|-------------|
| Building a custom GNN from scratch | Published GRIN/STGCN code exists — use it |
| Training on shuffled time-series data | Temporal leakage will invalidate all results |
| Using test-time failure masks during training | Data leakage — inflates metrics artificially |
| Optimizing for extreme edge cases (>50% node failure) | Outside realistic scope; hurts demo clarity |
| Adaptive traffic signal control integration | Out of scope per problem statement |

---

## 8. Final Recommendation

### 8.1 Recommended Architecture: **Tiered MVP — LightGBM First, GRIN Second**

**Do not choose between baseline and advanced. Build both, in sequence.**

This tiered strategy is the optimal approach for a national-level hackathon because it:

1. **Guarantees a working demo.** The LightGBM baseline is implementable in under 2 days and produces meaningful, defensible results against published benchmarks.
2. **Creates a compelling narrative arc.** "We started with a fast ML baseline and progressively advanced to a graph neural network" is a stronger research story than presenting only one model.
3. **De-risks the timeline.** If GRIN integration runs over schedule, the LightGBM baseline is still a complete, functional system.
4. **Enables a direct ablation study.** Comparing LightGBM vs. GRIN on the same evaluation harness produces a publishable result and demonstrates rigorous benchmarking methodology to judges.

### 8.2 Implementation Roadmap

```
Week 1 ──────────────────────────────────────────────────────────────
  Day 1–2:  METR-LA loader + failure simulation + normalization
  Day 3–4:  LightGBM baseline + spatial feature engineering
  Day 5:    Evaluation harness (MAE/RMSE/MAPE + RFS)

Week 2 ──────────────────────────────────────────────────────────────
  Day 1–2:  Adapt GRIN codebase (data loader, failure masks)
  Day 3–4:  GRIN training + hyperparameter tuning
  Day 5:    Ablation comparison: LightGBM vs. GRIN

Week 3 ──────────────────────────────────────────────────────────────
  Day 1–2:  Reconstruction Agent pipeline (neighbor selection + tier logic)
  Day 3–4:  REST API + digital twin integration
  Day 5:    End-to-end demo rehearsal + documentation
```

### 8.3 Expected Performance Targets (METR-LA, Block-Missing 20%)

| Model | Expected MAE | Expected MAPE | Implementation Time |
|-------|:-----------:|:-------------:|:-------------------:|
| Historical Mean (naive) | ~6.5 | ~18% | 1 hour |
| LightGBM (spatial features) | ~4.2 | ~12% | 1–2 days |
| STGCN Imputer | ~3.8 | ~10% | 2–3 days |
| GRIN (target) | ~3.2 | ~8% | 3–5 days |

> **Hackathon winning position:** Demonstrating a functional end-to-end self-healing pipeline with a 50%+ MAPE reduction over the naive baseline, real-time digital twin visualization, and a novel set of resilience metrics (RFS, FCR, SDI) constitutes a compelling, differentiated, and technically rigorous submission.

---

## 9. Key References

- Cini, A., Marisca, I., & Alippi, C. (2022). **Filling the G_ap_s: Multivariate Time Series Imputation by Graph Neural Networks.** *International Conference on Learning Representations (ICLR).*
- Li, Y., et al. (2018). **Diffusion Convolutional Recurrent Neural Network: Data-Driven Traffic Forecasting.** *ICLR.*
- Wu, Z., et al. (2019). **Graph WaveNet for Deep Spatial-Temporal Graph Modeling.** *IJCAI.*
- Chen, X., et al. (2021). **A Nonconvex Low-Rank Tensor Completion Model for Spatiotemporal Traffic Data Recovery.** *Transportation Research Part C.*
- LightGBM: Ke, G., et al. (2017). **LightGBM: A Highly Efficient Gradient Boosting Decision Tree.** *NeurIPS.*
