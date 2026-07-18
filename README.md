---
title: TraffiTwin Backend
emoji: 🚦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# TraffiTwin AI

**Self-Healing Traffic Digital Twin for Resilient Smart City Operations**

*   **Live Demo:** [traffitwin-ai.web.app](https://traffitwin-ai.web.app)
*   **Backend API:** [sahilmangla-traffitwin-backend.hf.space](https://sahilmangla-traffitwin-backend.hf.space)
*   **API Docs:** [sahilmangla-traffitwin-backend.hf.space/docs](https://sahilmangla-traffitwin-backend.hf.space/docs)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19%2B-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0%2B-FF8000?logo=lightgbm&logoColor=white)](https://github.com/microsoft/LightGBM)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.0%2B-4285F4?logo=google&logoColor=white)](https://github.com/google/agent-development-kit)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-F4B400?logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Project Overview

TraffiTwin AI is an AI-powered, self-healing traffic digital twin designed to maintain continuous situational awareness for urban transportation networks during telemetry outages. 

Modern intelligent transportation systems (ITS) depend heavily on real-time sensor streams. When physical loop detectors or traffic cameras fail due to hardware malfunctions, network dropouts, or power issues, traffic control centers lose visibility into congestion and incident states. TraffiTwin AI resolves this vulnerability by detecting telemetry failures in real time and automatically reconstructing missing traffic states using spatial-temporal graph-aware machine learning models. 

The system operates on the standard **METR-LA** dataset and integrates a high-fidelity traffic simulation, LightGBM-based state reconstruction, a Google ADK-powered Operations Analyst, and an interactive real-time dashboard.

---

## Problem Statement

Traffic Management Centers (TMCs) rely on continuous telemetry to coordinate emergency responses, run adaptive signal timing plans, and detect congestion anomalies. Physical sensor outages create critical blind spots, causing traditional adaptive traffic control systems to degrade rapidly or fall back to static, inefficient historical timing patterns.

```
┌────────────────┐     ┌────────────────┐     ┌─────────────────────┐     ┌────────────────────────┐
│ Sensors Online │ ──> │ Sensor Failure │ ──> │   AI Reconstruction │ ──> │ Digital Twin Restored  │
│ (Normal Flow)  │     │ (Blind Spots)  │     │ (Self-Healing State)│     │ (Situational Awareness)│
└────────────────┘     └────────────────┘     └─────────────────────┘     └────────────────────────┘
```

TraffiTwin AI bridges this gap, serving as an algorithmic backup layer that estimates actual traffic speeds across failed nodes, ensuring digital twins remain continuous, robust, and operational.

---

## Why It Matters

*   **Continuous Observability:** Eliminates data gaps, ensuring traffic operators maintain a complete network state snapshot at all times.
*   **Infrastructure Resilience:** Mitigates the risk of physical hardware degradation without requiring immediate, expensive field maintenance.
*   **Robust Downstream Decision Support:** Feeds downstream routing services and signal optimization engines with stable, uninterrupted state estimates.
*   **Production-Ready Hybrid Intelligence:** Deploys a self-healing sensor pipeline combining fast ML regressors with conversational LLM reasoning.

---

## Key Achievements

*   **207 Traffic Sensors:** Full spatial-temporal simulation of the METR-LA sensor network topology.
*   **34,272 Timesteps:** Thorough model evaluation and verification across extensive historical real-world telemetry.
*   **97.03% Flow Coverage Ratio:** Observability restoration across the road network under sensor failure conditions.
*   **2.48 mph Mean Absolute Error (MAE):** State reconstruction accuracy restoring traffic speeds close to ground-truth values.
*   **Google ADK Operations Analyst:** Conversational AI reasoning directly over live digital twin telemetry.
*   **Deterministic Fallback Engine:** Rule-based fallback mechanism guaranteeing uptime during LLM API throttling or network interruptions.
*   **Comprehensive Testing Suite:** Fully automated unit and integration tests (69 test cases) verifying simulation states, metrics calculations, domain logic, and API endpoints.
*   **Automated CI/CD Pipeline:** Fully configured GitHub Actions workflow that executes linting, unit tests, and handles automatic CD to Hugging Face Spaces (backend) and Firebase Hosting (frontend).
*   **Firebase + Hugging Face Deployment:** Decoupled architecture serving assets globally with sub-second API roundtrips.

---

## Technology Stack

| Layer | Component Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite, Zustand, Tailwind CSS, React Force Graph 2D, Framer Motion |
| **Backend** | Python 3.10, FastAPI, Uvicorn, CORS Middleware, Dotenv |
| **Machine Learning** | LightGBM, NumPy, SciPy (METR-LA adjacency matrix propagation) |
| **AI Agent** | Google Agent Development Kit (ADK) |
| **LLM** | Google Gemini 2.5 Flash |
| **Dataset** | METR-LA loop detector telemetry (207 sensors, 34,272 timesteps) |
| **Deployment** | Firebase Hosting (Frontend), Hugging Face Spaces (Backend Docker container) |

---

## System Architecture

The following diagram illustrates the flow of real-time telemetry from physical sensors through failure detection, ML reconstruction, state visualization, and conversational intelligence:

```mermaid
graph TD
    A[Traffic Sensors] --> B[Health Monitoring]
    B --> C[Failure Detection]
    C --> D{Is Sensor Failed?}
    D -- Yes --> E[Reconstruction Agent]
    D -- No --> F[Digital Twin State]
    E --> G[Spatial-Temporal LightGBM / GRIN]
    G --> F
    F --> H[Web Operations Dashboard]
    F --> I[Google ADK Operations Analyst]
    I --> H
```

---

## Key Features

| Feature | Description |
| :--- | :--- |
| **Real-time Digital Twin** | Visualizes traffic flow speeds across 207 sensor locations in the METR-LA network with a sub-second refresh rate. |
| **Sensor Failure Simulation** | Allows operators to manually inject failure states (temporary or permanent) into any individual node directly via the UI. |
| **Self-Healing Reconstruction** | Instantly replaces missing sensor values with virtual sensor readings generated by ML models. |
| **Spatial Feature Engineering** | Leverages 2-hop spatial neighborhood features and historical temporal profiles to achieve highly accurate speed predictions. |
| **Embedded ADK Analyst** | Features a smart city operations assistant capable of answering complex telemetry queries over live digital twin states. |
| **Benchmarking Framework** | Compares reconstruction performance against standard baselines (Historical Mean, Spatial K-Nearest Neighbors). |
| **Interactive Event Logs** | Displays a scrollable operations timeline tracking sensor failures, AI response engagements, and physical recoveries. |

---

## Technical Highlights

*   **Network Scale:** Simulates 207 sensor nodes over 34,272 chronological timesteps based on the METR-LA dataset.
*   **Leakage Prevention:** Uses rigorous chronological train-test splits (70% train, 30% test) to prevent temporal data leakage.
*   **Spatial Neighborhoods:** Implements 2-hop graph feature propagation, using the physical coordinates and graph topology of the METR-LA road network.
*   **High-Throughput Inference:** Features a FastAPI inference pipeline that executes ML reconstructions in under 5 milliseconds.

---

## Benchmark Results

The state reconstruction models are evaluated on root mean squared error (RMSE), mean absolute error (MAE), mean absolute percentage error (MAPE), and Flow Coverage Ratio (FCR).

| Model | MAE (mph) | RMSE (mph) | MAPE | Flow Coverage Ratio (FCR) |
| :--- | :---: | :---: | :---: | :---: |
| **Historical Mean Baseline** | ~6.50 | — | ~18.00% | 100.00% |
| **TraffiTwin LightGBM Regressor** | **2.48** | **7.82** | **6.06%** | **97.03%** |

> [!NOTE]  
> The LightGBM model achieves near-ground-truth reconstruction accuracy, restoring over 97% network observability while keeping MAE under 2.5 mph.

---

## Google Ecosystem Integration

TraffiTwin AI leverages the Google developer ecosystem to power live operational intelligence and deliver high-availability hosting:

*   **Gemini 2.5 Flash:** Acts as the cognitive core for the Operations Analyst, performing real-time reasoning over system states and diagnosing metrics.
*   **Google Agent Development Kit (ADK):** Used to construct the conversational agent, coordinate tool registration (providing API-backed network queries), and format responses.
*   **Google AI Studio:** Utilized for rapid prompt engineering, system instruction testing, and generating development keys for the Gemini API.
*   **Firebase Hosting:** Delivers the compiled React 19 frontend assets globally with low latency, fast page load speeds, and robust static hosting.

---

## AI Operations Analyst

The AI Operations Analyst is embedded directly inside the web dashboard to assist traffic operators in real time. 

*   **Live Reasoning:** The ADK agent evaluates the live Digital Twin state, tracking sensor health, active failures, and speed metrics.
*   **Real-time Queries:** Operators can converse with the agent directly in the panel to ask questions like *"Which sensors are currently offline?"* or *"Summarize recent incidents."*
*   **Deterministic Fallback Logic:** If the Gemini API becomes unavailable due to rate limits, network issues, or credential errors, the analyst seamlessly falls back to a deterministic, rule-based reasoning engine. This guarantees continuous operational responses in the dashboard under all conditions.

```
        User Query
            │
            ▼
     Google ADK Agent
            │
            ▼
     Gemini 2.5 Flash
            │
     ┌──────┴──────┐
     │   Success?  │
     └─┬─────────┬─┘
       │ Yes     │ No
       ▼         ▼
   Response  Deterministic Fallback Engine
                 (Guaranteed Operational Output)
```

---

## Deployment

*   **Frontend Web App:** [https://traffitwin-ai.web.app](https://traffitwin-ai.web.app) (Hosted on Firebase Hosting)
*   **Backend API Services:** [https://sahilmangla-traffitwin-backend.hf.space](https://sahilmangla-traffitwin-backend.hf.space) (Hosted on Hugging Face Spaces via Docker)
*   **Interactive API Docs:** [https://sahilmangla-traffitwin-backend.hf.space/docs](https://sahilmangla-traffitwin-backend.hf.space/docs) (Swagger/OpenAPI documentation)

---

## Future Work

*   **GRIN Reconstruction Model:** Transitioning from tree-based regression to Graph Recurrent Imputation Networks to model complex temporal dynamics.
*   **CityFlow V2 Integration:** Supporting dynamic traffic micro-simulations to study the downstream impacts of self-healing sensors on traffic light timing optimization.
*   **Multi-Feature Reconstruction:** Expanding prediction parameters to include precipitation, lane construction data, and public holiday temporal profiles.
*   **Online Learning:** Developing continuous training loops to update the baseline regressor as new telemetry drift is observed.
*   **Vertex AI Deployment:** Migrating backend training and model endpoints to Vertex AI for enterprise-scale orchestration and monitoring.

---

## Repository Structure

```
TraffiTwin-AI/
├── agents/
│   └── traffic_resilience_agent/   # Google ADK Agent
│       ├── agent.py                 # Agent declaration & models
│       ├── prompts.py               # Analyst system instructions
│       ├── tools.py                 # API-backed data fetchers
│       └── README.md                # Agent documentation
├── backend/
│   ├── api/                         # FastAPI router & app configuration
│   ├── services/                    # Core backend service singletons
│   ├── twin/                        # Simulation state and LightGBM models
│   ├── requirements.txt             # Python dependencies
│   └── main.py                      # Backend entrypoint
├── frontend/
│   ├── src/
│   │   ├── components/              # React UI elements (Header, OperationsRail, BriefingModal)
│   │   ├── store/                   # Zustand state managers
│   │   ├── App.tsx                  # Main layout container
│   │   └── index.css                # Global styles & design system
│   ├── package.json                 # Frontend dependencies
│   └── vite.config.ts               # Vite configuration
└── README.md                        # Project documentation
```

---

## Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Gemini API Key (optional, for Gemini-backed conversational intelligence)

### Clone the Repository
```bash
git clone https://github.com/sahil-mangla/TraffiTwin-AI.git
cd TraffiTwin-AI
```

### Backend Setup
1. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Set environment variables in a `.env` file within the `backend/` directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```

---

## Running the Project

### 1. Launch Backend Server
From the root directory, run the FastAPI application:
```bash
uvicorn backend.api.app:app --reload
```
The API documentation will be available at `http://localhost:8000/docs`.

### 2. Launch Frontend Application
From the `frontend/` directory, start the Vite development server:
```bash
npm run dev
```
Open `http://localhost:5173` in your web browser.

### 3. Run Standalone ADK Agent (Optional)
The Google ADK-powered Traffic Operations Analyst is automatically available inside the dashboard once the backend is running. For standalone debugging, CLI interaction, and evaluation, developers may optionally launch the agent directly:
```bash
adk run agents/traffic_resilience_agent
```

### 4. Run the Test Suite
Ensure you are in the root directory and your virtual environment is active, then run:
```bash
pytest tests/ -v
```
This runs the full suite of unit and integration tests covering the simulator, metrics calculations, domain logic, custom exception handlers, and endpoints.

---

## Example Workflow

1.  **Launch the System:** Start the backend and frontend servers. Open the web interface.
2.  **Acknowledge Mission Protocol:** Read and close the startup briefing modal.
3.  **Inject Anomaly:** Select a node in the web visualization and trigger a sensor failure.
4.  **Observe Autonomic Repair:** Note the live transition of the node to a "Reconstructed" state and verify that overall network observability recovers above 97%.
5.  **Audit via AI Analyst:** Use the "Ops Intelligence" panel to query: *"Which sensors are offline?"* and observe the exact virtual readings and metrics generated.

---

## Research Foundations

1.  **DCRNN:** Li et al., *Diffusion Convolutional Recurrent Neural Network: Data-Driven Traffic Forecasting*, ICLR 2018.
2.  **Graph WaveNet:** Wu et al., *Graph WaveNet for Deep Spatial-Temporal Graph Modeling*, IJCAI 2019.
3.  **GRIN:** Cini et al., *Filling the Gaps: Multivariate Time Series Imputation by Graph Recurrent Networks*, ICLR 2022.
4.  **LightGBM:** Ke et al., *LightGBM: A Highly Efficient Light Gradient Boosting Decision Tree*, NeurIPS 2017.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
