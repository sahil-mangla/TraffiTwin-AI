from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class HealthResponse(BaseModel):
    status: str
    version: str

class SimulateFailureRequest(BaseModel):
    sensor_id: int = Field(..., description="ID of the sensor to fail")
    duration: int = Field(..., description="Duration of the failure in time steps")

class SimulateFailureResponse(BaseModel):
    status: str
    message: str

class StepRequest(BaseModel):
    steps: int = Field(1, description="Number of steps to advance the simulation")

class StepResponse(BaseModel):
    current_time: int
    message: str

class TwinSnapshotResponse(BaseModel):
    current_time: int
    readings: Dict[str, float]
    masks: Dict[str, bool]
    reconstructions: Dict[str, float]

class MetricsResponse(BaseModel):
    current_time: int
    fcr: float
    mae: float
    rmse: float
    total_failures_simulated: int

# ── New: Graph topology ───────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: int

class GraphEdge(BaseModel):
    source: int
    target: int
    weight: float

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# ── New: Unified system state ─────────────────────────────────────────────────

class SystemStateResponse(BaseModel):
    snapshot: Dict[str, Any]
    metrics: Dict[str, Any]
    timestamp: str
    system_health: str  # "healthy" | "degraded" | "critical"
