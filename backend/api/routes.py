from fastapi import APIRouter, HTTPException, Depends
from backend.api.schemas import (
    HealthResponse,
    SimulateFailureRequest, SimulateFailureResponse,
    StepRequest, StepResponse,
    TwinSnapshotResponse, MetricsResponse,
    GraphResponse, GraphNode, GraphEdge, SystemStateResponse,
    IncidentSummaryResponse, GenerateSummaryRequest, GenerateSummaryResponse
)
from backend.services.twin_service import TwinService
from backend.core.exceptions import ServiceUnavailableError, InvalidSimulationStepError
from datetime import datetime, timezone
from typing import Any, List

router = APIRouter()

def get_twin_service() -> TwinService:
    from backend.api.app import app
    if not hasattr(app.state, "twin_service"):
        raise ServiceUnavailableError("Twin Service")
    return app.state.twin_service

def get_incident_service() -> Any:
    from backend.api.app import app
    if not hasattr(app.state, "incident_service"):
        raise ServiceUnavailableError("Incident Service")
    return app.state.incident_service

def calculate_observability(snapshot: dict, num_nodes: int) -> float:
    active_failures = sum(1 for v in snapshot["masks"].values() if v)
    reconstructed_nodes = len(snapshot["reconstructions"])
    return ((num_nodes - active_failures + reconstructed_nodes) / num_nodes) * 100.0

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness check. Always returns 200 once the process is up — does not
    verify that the Twin/Incident services finished initializing."""
    return HealthResponse(status="ok", version="1.0.0")


@router.get(
    "/snapshot",
    response_model=TwinSnapshotResponse,
    responses={503: {"description": "Twin Service not yet initialized."}},
)
async def get_snapshot(twin: TwinService = Depends(get_twin_service)):
    """
    Current readings, failure masks, and AI reconstructions for every sensor
    at the present simulation timestep.
    """
    snapshot = twin.get_snapshot()
    return TwinSnapshotResponse(**snapshot)


@router.get("/graph", response_model=GraphResponse)
async def get_graph(twin: TwinService = Depends(get_twin_service)):
    """
    Returns the sensor network topology (nodes + weighted edges) derived from
    the METR-LA adjacency matrix. Edges are only included where weight > 0.
    Call once on startup — the topology is static.
    """
    A = twin.stream.get_adjacency_matrix()
    n = A.shape[0]
    nodes = [GraphNode(id=i) for i in range(n)]
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            w = float(A[i, j])
            if w > 0:
                edges.append(GraphEdge(source=i, target=j, weight=round(w, 4)))
    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/state", response_model=SystemStateResponse)
async def get_system_state(
    twin: TwinService = Depends(get_twin_service),
    incident: Any = Depends(get_incident_service)
):
    """
    Unified state endpoint — merges snapshot + metrics into a single coherent
    payload. This is the primary polling target for the frontend.
    """
    snapshot = twin.get_snapshot()
    metrics = twin.get_metrics()

    active_failures = sum(1 for v in snapshot["masks"].values() if v)
    if active_failures == 0:
        health = "healthy"
    elif active_failures <= 5:
        health = "degraded"
    else:
        health = "critical"

    return SystemStateResponse(
        snapshot=snapshot,
        metrics=metrics,
        timestamp=datetime.now(timezone.utc).isoformat(),
        system_health=health,
        latest_incident_summary=incident.get_latest_summary_text(),
    )


@router.post(
    "/simulate_failure",
    response_model=SimulateFailureResponse,
    responses={404: {"description": "sensor_id is out of range for this network."}},
)
async def simulate_failure(
    req: SimulateFailureRequest,
    twin: TwinService = Depends(get_twin_service),
    incident: Any = Depends(get_incident_service)
):
    """
    Inject a sensor outage for `duration` simulation steps. Clears any stale
    cached incident summary so the next `/state` poll reflects this failure.
    """
    twin.inject_failure(sensor_id=req.sensor_id, duration=req.duration)
    incident.clear_latest_summary()
    return SimulateFailureResponse(
        status="success",
        message=f"Injected failure on sensor {req.sensor_id} for {req.duration} steps."
    )


@router.post(
    "/step",
    response_model=StepResponse,
    responses={422: {"description": "steps must be greater than 0."}},
)
async def step_simulation(
    req: StepRequest,
    twin: TwinService = Depends(get_twin_service),
    incident: Any = Depends(get_incident_service)
):
    """Advance the simulation by `steps` ticks, running reconstruction for
    any sensors currently failed and healing any whose failure duration has
    elapsed."""
    if req.steps <= 0:
        raise InvalidSimulationStepError("Steps must be greater than 0")
    twin.step(steps=req.steps)
    incident.clear_latest_summary()

    return StepResponse(
        current_time=twin.state.current_time_step,
        message=f"Simulation advanced by {req.steps} steps."
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(twin: TwinService = Depends(get_twin_service)):
    """Rolling reconstruction-accuracy metrics (FCR, MAE, RMSE) computed over
    every reconstruction made so far in this simulation run."""
    metrics = twin.get_metrics()
    return MetricsResponse(
        current_time=twin.state.current_time_step,
        **metrics
    )


@router.get("/incident-summaries", response_model=List[IncidentSummaryResponse])
async def get_incident_summaries(incident: Any = Depends(get_incident_service)):
    """The most recent cached incident summaries (deterministic or
    AI-enriched), newest first, capped at 20 entries."""
    summaries = incident.get_latest_summaries()
    return [IncidentSummaryResponse(**s) for s in summaries]


@router.post("/generate-incident-summary", response_model=GenerateSummaryResponse)
async def generate_incident_summary(
    req: GenerateSummaryRequest,
    incident: Any = Depends(get_incident_service)
):
    """
    Generate a summary from a caller-supplied incident payload rather than
    the live twin state — useful for replaying or backfilling a report for
    an incident that already occurred.
    """
    payload = req.model_dump()
    summary = await incident.generate_from_payload(payload)
    return GenerateSummaryResponse(summary=summary)


@router.post("/analyze-current-state", response_model=GenerateSummaryResponse)
async def analyze_current_state(
    twin: TwinService = Depends(get_twin_service),
    incident: Any = Depends(get_incident_service)
):
    snapshot = twin.get_snapshot()
    # Find any active failures to determine if we should report a failure or nominal check
    failed_sensors = [int(k) for k, failed in snapshot["masks"].items() if failed]
    
    if failed_sensors:
        sensor_id = failed_sensors[0]
        event_type = "sensor_failure"
        summary = await incident.process_event(twin, event_type, sensor_id=sensor_id)
    else:
        event_type = "system_check"
        summary = await incident.process_event(twin, event_type)
        
    return GenerateSummaryResponse(summary=summary)
