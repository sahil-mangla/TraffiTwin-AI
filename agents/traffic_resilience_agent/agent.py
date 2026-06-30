from google.adk import Agent
from .prompts import SYSTEM_INSTRUCTION
from .tools import (
    get_network_health,
    get_active_failures,
    get_latest_incidents,
    get_system_metrics,
    get_sensor_status,
)

root_agent = Agent(
    name="traffic_operations_analyst",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_network_health,
        get_active_failures,
        get_latest_incidents,
        get_system_metrics,
        get_sensor_status,
    ],
)
