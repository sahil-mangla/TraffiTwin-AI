import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import lightgbm as lgb
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.services.twin_service import TwinService
from backend.services.incident_intelligence_service import IncidentIntelligenceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
