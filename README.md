# TraffiTwin AI

> An AI-powered self-healing traffic digital twin that autonomously detects traffic camera failures and reconstructs missing traffic information to keep smart-city traffic intelligence operational.

---

## 📌 Problem Statement
Modern smart cities depend heavily on real-time traffic camera feeds to feed traffic optimization algorithms, signal control systems, and emergency dispatch platforms. However, physical cameras are prone to frequent failures due to hardware glitches, connectivity drops, lens obstruction, and power outages. When these feeds fail, traffic control networks suffer from blind spots, leading to sub-optimal traffic flow, gridlocks, and delayed response times.

## 💡 Proposed Solution
**TraffiTwin AI** introduces a "self-healing" traffic digital twin framework. Rather than waiting for manual hardware repairs, TraffiTwin AI:
1. **Detects anomalies or outages** in camera feeds in real time.
2. **Reconstructs missing traffic spatial-temporal information** (e.g., flow rate, vehicle count, speed, and density) using adjacent working sensors, historical spatial correlations, and AI-driven spatial-temporal reconstruction models ranging from tree-based ensemble methods to advanced graph neural networks.
3. **Restores operations** virtually, ensuring downstream smart-city systems continue receiving continuous, high-fidelity traffic estimates.

## 🏗️ Core Architecture Overview
The system is divided into four main pillars:
- **Data Ingestion Engine**: Collects real-time streams from traffic sensors, cameras, and IoT endpoints.
- **Anomaly Detection Service**: Monitors streams for physical or data-level failures.
- **Self-Healing Reconstruction Core**: Employs AI-driven spatial-temporal reconstruction models ranging from tree-based ensemble methods to advanced graph neural networks to impute missing datasets dynamically.
- **Web-Based Twin Console**: Visualizes live traffic conditions and virtual sensor states in a responsive digital twin environment.

---

## 🤖 Agentic Workflow
The self-healing capability of TraffiTwin AI is powered by an autonomous, multi-agent orchestration layer that detects failures, calculates corrections, and updates the digital twin loop.

### 1. Health Monitoring Agent
*   **Responsibility**: Continuously audits incoming traffic camera feeds and telemetry data for anomalies (e.g., frozen frames, frame drops, network outages, or out-of-bounds telemetry values).
*   **Input**: Real-time traffic camera video streams, HTTP ping statuses, and raw sensor telemetry logs.
*   **Output**: Node health state alerts (healthy, degraded, or offline) and active sensor failure logs.
*   **Contribution to Self-Healing**: Acts as the system's nervous system. It immediately triggers the healing process the moment a physical sensor fails, preventing corrupt or empty data from propagating to downstream city systems.

### 2. Reconstruction Agent
*   **Responsibility**: Generates high-fidelity virtual estimates for failed sensors using neighboring sensor data and historical spatial-temporal patterns.
*   **Input**: Topological graph metadata, active failure alerts from the Health Monitoring Agent, and real-time telemetry from nearby operational sensors.
*   **Output**: High-fidelity virtual telemetry data (imputed vehicle counts, speeds, and densities).
*   **Contribution to Self-Healing**: Acts as the cognitive core. By dynamically selecting and executing the best-fit spatial-temporal model, it fills data voids with accurate virtual sensor readings, maintaining continuous data flow.

### 3. Digital Twin Layer
*   **Responsibility**: Maintains the global state representation of the traffic network and synchronizes the real-world state with virtual reconstructions.
*   **Input**: Live streams from operational physical sensors and virtual data payloads from the Reconstruction Agent.
*   **Output**: A unified, uninterrupted, real-time traffic intelligence feed and visual digital twin representation.
*   **Contribution to Self-Healing**: Serves as the consumer-facing interface and API bridge. It guarantees that external systems (like emergency dispatch or traffic signal networks) receive a seamless stream of traffic intelligence, completely unaware of physical camera downtime.

---

## 🚀 What Makes TraffiTwin AI Different?

### Traditional Traffic Digital Twins
Standard digital twins act as passive mirrors. They ingest real-time traffic camera feeds, visualize traffic states, and build historical analytics. 

### Limitations of Existing Systems
*   **Hardware Vulnerability**: Traditional systems are highly fragile. If a camera lens gets obstructed, loses power, or goes offline, the digital twin develops permanent blind spots.
*   **Reactive Diagnostics**: Identifying camera issues often depends on daily/weekly automated checks or manual reports, during which traffic optimization algorithms revert to inefficient defaults.
*   **No Fallbacks**: They lack the intelligence to estimate traffic conditions dynamically when sensor data is lost.

### Why TraffiTwin AI is Novel
TraffiTwin AI introduces the concept of a **Self-Healing Digital Twin**. It moves beyond passive observation to active, autonomous resilience:
*   **Virtual Sensing**: It turns the network topology itself into a sensor. By exploiting spatial correlations (i.e., traffic passing sensor A is highly likely to reach sensor B within a time delta), it can act as a reliable fallback.
*   **Agentic Orchestration**: The continuous feedback loop between detection and reconstruction happens autonomously within milliseconds, requiring zero human intervention to keep smart-city systems operational.
*   **Adaptive Imputation**: It supports a range of spatial-temporal models—from fast, tree-based ensembles for edge deployments to complex Graph Neural Networks (GNNs) for dense urban centers.

### Why Resilience is Crucial
In modern metropolitan areas, traffic signals and emergency routing are increasingly automated. A single camera failure can lead to gridlock, increased fuel emissions, and delayed emergency responses. TraffiTwin AI guarantees **operational continuity**, protecting smart cities against the inevitability of hardware failure.

---

## 🏛️ System Architecture
Architecture diagram coming soon.

---

## 📂 Repository Structure

Below is the directory structure of the repository:

```text
.
├── README.md                 # Project vision, overview, and layout
├── backend/                  # API services, detection engine, & ML model logic
├── datasets/                 # Raw/processed traffic telemetry data
├── demo_assets/              # Slides, screenshots, and demo media
├── docs/                     # Technical specifications and design documents
│   ├── architecture.md       # Detailed system design
│   ├── literature_review.md  # Research background
│   └── problem_statement.md  # Deep dive into the problem definition
├── experiments/              # Model training scripts, configurations, and evaluation metrics
├── frontend/                 # Interactive dashboard and twin visualization
└── notebooks/                # Exploratory Data Analysis (EDA) and prototyping
```

---

## 👥 Team
- **Team Name Placeholder**
  - Team Member 1 (Role/Email)
  - Team Member 2 (Role/Email)
  - Team Member 3 (Role/Email)
