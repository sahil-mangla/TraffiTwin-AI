import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import lightgbm as lgb
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from backend.core.exceptions import TraffiTwinException
from backend.api.routes import router
from backend.services.twin_service import TwinService
from backend.services.incident_intelligence_service import IncidentIntelligenceService
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS – build allowed origins from environment variable ALLOWED_ORIGINS.
# Falls back to a safe default set that covers local dev.
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = settings.allowed_origins
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

logger.info("Starting TraffiTwin AI Backend...")
twin_service = TwinService()
incident_service = IncidentIntelligenceService()
try:
    twin_service.initialize()
    logger.info("==================================================")
    logger.info("TraffiTwin AI Backend Initialized")
    logger.info("==================================================")
    logger.info(f"Nodes          : {twin_service.stream.get_num_nodes()}")
    logger.info("Model          : LightGBM Baseline")
    logger.info("State          : Ready")
    logger.info("==================================================")
except Exception as e:
    logger.error(f"Failed to initialize TwinService: {e}")
    raise e

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.twin_service = twin_service
    app.state.incident_service = incident_service
    yield
    # Shutdown
    logger.info("Shutting down TraffiTwin AI Backend...")

app = FastAPI(
    title="TraffiTwin AI API",
    description="Digital Twin Backend for self-healing traffic intelligence.",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(TraffiTwinException)
async def traffitwin_exception_handler(request: Request, exc: TraffiTwinException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.__class__.__name__}
    )

# CORS – explicit origins only; credentials not needed (no cookies/auth).
# NOTE: allow_credentials=False is intentional — combining credentials=True
# with a wildcard origin is forbidden by the CORS spec and would be rejected
# by all modern browsers anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin"],
)

app.include_router(router)

