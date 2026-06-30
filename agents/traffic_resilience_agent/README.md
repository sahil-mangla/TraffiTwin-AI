# Traffic Resilience Agent

An AI Operations Analyst built with Google's Agent Development Kit (ADK) 2.0 to monitor, analyze, and communicate the status of the TraffiTwin AI network.

## Architecture Overview

This agent leverages Google's `google-adk` to construct an LLM-powered assistant (`gemini-2.5-flash`) that acts as a Smart City Traffic Operations Analyst. 
It operates by fetching live data from the TraffiTwin backend API (running on `http://localhost:8000`), allowing it to have a completely accurate, hallucination-free view of the active simulation. 

The agent is stateless and relies exclusively on its tools to retrieve:
- Incident intelligence reports.
- Current active sensor failures.
- Live performance metrics (MAE, RMSE, FCR, Observability).
- Specific sensor statuses and readings.

## Tool Descriptions

- **`get_network_health()`**: Retrieves the macroscopic system state including overall status, percentage of network observability, and the count of active failures.
- **`get_active_failures()`**: Returns a list of the specific sensor IDs that are currently offline or masked.
- **`get_latest_incidents()`**: Fetches recent incident reports from the incident intelligence service (which includes both deterministic and AI-enriched summaries).
- **`get_system_metrics()`**: Retrieves the system's live performance metrics such as MAE, RMSE, and FCR, along with observability.
- **`get_sensor_status(sensor_id)`**: Queries the state for a single sensor to determine if it is online, offline, reconstructed, and its current speed.

## Implementation Details

- **`agent.py`**: The ADK entry point declaring `root_agent` with instructions, model (`gemini-2.5-flash`), and tools.
- **`prompts.py`**: Contains the system instruction defining the strict constraints and persona.
- **`tools.py`**: A suite of HTTP-backed Python functions querying the TraffiTwin API. They treat the backend as the single source of truth.

## Example Conversations

**Example 1: General Status Query**
*User:* "What is happening in the city right now?"
*Agent:* "Two sensors are currently offline. TraffiTwin has reconstructed both using virtual sensing. Current observability remains 98.1%. The network remains operational."

**Example 2: Specific Sensor Inquiry**
*User:* "What is the status of sensor 42?"
*Agent:* "Sensor 42 is currently offline. However, TraffiTwin has successfully reconstructed its data, and its current estimated speed is 54.2 mph."

**Example 3: Incident Summary**
*User:* "Were there any recent incidents?"
*Agent:* "Yes, an incident occurred recently where sensor 12 failed. This resulted in a temporary observability drop, but the system successfully reconstructed the data maintaining network stability."

## Affected Files
- `backend/requirements.txt`: Added `google-adk` and `httpx` dependencies.
- `agents/traffic_resilience_agent/agent.py`
- `agents/traffic_resilience_agent/tools.py`
- `agents/traffic_resilience_agent/prompts.py`
- `agents/traffic_resilience_agent/README.md`
