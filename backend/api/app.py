import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env file

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — initialize services here so they only run when the server starts,
    # NOT at import time (which would break tests if the model file is absent).
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
        raise RuntimeError(f"Backend startup failed: {e}") from e

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

# FastAPI's default 422 body (a raw list of pydantic error dicts, no
# error_code) doesn't match the {"detail", "error_code"} shape every other
# error response uses. Normalize it so API consumers can rely on one shape.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": exc.errors(), "error_code": "RequestValidationError"}
    )

# Framework-level HTTP errors (e.g. 404 for an unknown route, 405 for a
# disallowed method) — normalized to the same shape for consistency.
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": "HTTPException"}
    )

# Last-resort safety net: any exception not already handled above (a bug in
# a service, an unexpected third-party error, etc.) previously surfaced as
# FastAPI's bare, unstructured 500 with a traceback logged nowhere but
# stdout. Log it server-side with full context and return the same
# {"detail", "error_code"} shape as every other error path, without leaking
# internals to the client.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception while processing %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred.", "error_code": "InternalServerError"}
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
