from fastapi import APIRouter, HTTPException, Depends
from backend.api.schemas import (
    HealthResponse,
    SimulateFailureRequest, SimulateFailureResponse,
    StepRequest, StepResponse,
    TwinSnapshotResponse, MetricsResponse,
    GraphResponse, SystemStateResponse
)
from backend.services.twin_service import TwinService
from datetime import datetime, timezone

router = APIRouter()

def get_twin_service() -> TwinService:
    from backend.api.app import app
    if not hasattr(app.state, "twin_service"):
        raise HTTPException(status_code=503, detail="Twin Service not initialized")
    return app.state.twin_service


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/snapshot", response_model=TwinSnapshotResponse)
async def get_snapshot(twin: TwinService = Depends(get_twin_service)):
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
    nodes = [{"id": i} for i in range(n)]
    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            w = float(A[i, j])
            if w > 0:
                edges.append({"source": i, "target": j, "weight": round(w, 4)})
    return GraphResponse(nodes=nodes, edges=edges)


@router.get("/state", response_model=SystemStateResponse)
async def get_system_state(twin: TwinService = Depends(get_twin_service)):
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
    )


@router.post("/simulate_failure", response_model=SimulateFailureResponse)
async def simulate_failure(req: SimulateFailureRequest, twin: TwinService = Depends(get_twin_service)):
    try:
        twin.inject_failure(sensor_id=req.sensor_id, duration=req.duration)
        return SimulateFailureResponse(
            status="success",
            message=f"Injected failure on sensor {req.sensor_id} for {req.duration} steps."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step", response_model=StepResponse)
async def step_simulation(req: StepRequest, twin: TwinService = Depends(get_twin_service)):
    twin.step(steps=req.steps)
    return StepResponse(
        current_time=twin.state.current_time_step,
        message=f"Simulation advanced by {req.steps} steps."
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(twin: TwinService = Depends(get_twin_service)):
    metrics = twin.get_metrics()
    return MetricsResponse(
        current_time=twin.state.current_time_step,
        **metrics
    )
