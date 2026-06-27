# Problem Statement: TraffiTwin AI

## 1. Problem Overview
Modern intelligent transportation systems (ITS) and smart-city infrastructures depend heavily on continuous, high-fidelity data streams from traffic cameras and sensors. These cameras serve as the critical "eyes" of the city, providing real-time measurements of traffic flow, density, velocity, and vehicle classification. This spatial-temporal data is the foundational input for downstream applications, including adaptive traffic signal control, dynamic routing, emergency vehicle preemption, and congestion management. Without this continuous observability, the efficacy of data-driven traffic optimization algorithms degrades significantly.

## 2. Core Problem
Despite their importance, physical traffic cameras and sensors are highly susceptible to failures. These failures can manifest as sudden hardware malfunctions, communication network dropouts, power outages, physical damage, or environmental obstructions (e.g., severe weather, lens occlusion). When a traffic camera fails, the data stream is interrupted, resulting in block-missing spatial-temporal data. This creates critical blind spots in the traffic network topology, abruptly breaking the continuous data pipeline required by smart-city intelligence systems. 

## 3. Real-World Impact
The failure of traffic cameras introduces severe cascading effects across the traffic management ecosystem:
*   **Loss of Situational Awareness:** Traffic management centers (TMCs) lose real-time visibility into localized road conditions, preventing operators from identifying incidents, bottlenecks, or hazardous conditions promptly.
*   **Monitoring Degradation:** The statistical reliability of the overall traffic network state estimation is compromised. Missing nodes in the traffic network graph distort the understanding of macroscopic traffic patterns.
*   **Operational Consequences:** Automated systems relying on this data, such as dynamic signal timing and congestion routing algorithms, fail to operate optimally or revert to inefficient pre-timed, open-loop plans. This leads to increased localized congestion, elevated emissions, and delayed emergency response times.

## 4. Existing Systems
Current intelligent transportation systems handle camera and sensor failures poorly. Most existing architectures rely on simplistic, reactive fallback mechanisms:
*   **Statistical Interpolation:** Many systems use basic historical averaging (e.g., utilizing historical profiles) or simple spatial interpolation, which fail to capture complex, non-linear, and dynamic real-time traffic phenomena.
*   **Open-Loop Fallbacks:** Traffic signal controllers often revert to static, pre-programmed timing plans when real-time actuation data is lost, completely ignoring current traffic demand.
*   **Manual Intervention:** System restoration primarily relies on dispatching maintenance crews to physically repair or replace the hardware, a process that can leave the network operating with blind spots for days or weeks.

## 5. Proposed Solution: Self-Healing Traffic Twin
To address this vulnerability, we propose and implement **TraffiTwin AI**, a "Self-Healing" Traffic Digital Twin. Instead of relying solely on physical hardware repairs, TraffiTwin AI introduces a virtualized resilience layer. By leveraging the inherent spatial-temporal correlations within traffic networks, the system acts as a virtual sensor. 

When a physical camera failure is detected, the twin utilizes a highly efficient **Spatio-Temporal LightGBM Reconstruction Agent** to reconstruct the missing traffic state (speed) in real-time. This imputed data is derived from the complex spatial dependencies between the failed node and adjacent functioning sensors (up to 2 hops), combined with historical rolling temporal statistics of the failed node itself, effectively "healing" the data stream and restoring system observability without immediate physical intervention. Advanced graph recurrent architectures (such as Graph Recurrent Imputation Networks, or GRIN) remain in scope as future deep learning enhancements.

## 6. Objectives
The development of TraffiTwin AI has achieved the following key milestones:
*   **Automated Failure Simulation:** Developed a failure simulation framework capable of injecting Missing Completely at Random (MCAR) and block-missing camera failures (simulating network and power outages) to validate self-healing capabilities.
*   **Spatio-Temporal Feature Engineering:** Implemented a feature engine that extracts spatial-temporal correlations (lags, rolling averages, rolling variance, and calendar time embeddings) while enforcing strict zero-leakage constraints.
*   **LightGBM Reconstruction Agent:** Built and optimized a LightGBM-based reconstructor that operates as a high-fidelity virtual sensor for failed camera nodes.
*   **Rigorous Benchmarking & Audit:** Established a benchmarking framework to compare the reconstructor against traditional baselines and performed a leakage audit verifying the absence of temporal data contamination.

## 7. Success Metrics
The efficacy of TraffiTwin AI has been validated against key performance indicators on the METR-LA dataset:
*   **Failure Support Capacity:** Successfully maintains high accuracy under extreme infrastructure outages, supporting up to **40% simultaneous node failures**.
*   **Traffic Reconstruction Error:** Achieved a Mean Absolute Percentage Error (MAPE) of **6.06%** and a Mean Absolute Error (MAE) of **2.48**, significantly outperforming the target threshold of <10% MAPE.
*   **Recovery Fidelity Score (RFS):** Demonstrated an RFS of **0.73**, indicating a 73% improvement in reconstruction fidelity over a naive historical mean baseline.
*   **System Integrity:** Passed a rigorous leakage audit, establishing **zero temporal leakage** across all validation horizons.

## 8. Scope
To ensure focused development and rigorous evaluation, the scope of TraffiTwin AI is strictly constrained to failure detection and data reconstruction.
Explicitly, the scope defines that:
*   **We are NOT building adaptive signals:** The project will not output or control traffic light timing plans.
*   **We are NOT building congestion optimization:** The system will not generate routing suggestions or active traffic management interventions.
*   **We are NOT building violation detection:** The framework will not perform license plate reading, speeding enforcement, or any form of traffic violation identification.
