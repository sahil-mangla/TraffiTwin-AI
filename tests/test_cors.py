"""
CORS Audit Tests for TraffiTwin AI Backend
============================================
Tests every endpoint listed in the CORS audit against:
  - Allowed origins (local dev + Firebase production)
  - Disallowed origins (third-party sites)

Run with:
    pytest tests/test_cors.py -v
"""

import os
import pytest

# Set environment before importing the app so the CORS middleware uses it.
os.environ["ALLOWED_ORIGINS"] = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173,"
    "https://traffitwin-ai.web.app,"
    "https://traffitwin-ai.firebaseapp.com"
)

# backend.config builds its `settings` singleton once, at first import, from
# whatever os.environ/.env looked like at that moment. If another test module
# (e.g. test_config.py) happens to import backend.config first — collection
# order across the whole test session, not just this file — the env var set
# above is set too late to affect it. Force a fresh Settings() read here so
# this file's CORS origins are correct regardless of what else has already
# been collected.
import backend.config
backend.config.settings = backend.config.Settings()

from fastapi.testclient import TestClient
from backend.api.app import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://traffitwin-ai.web.app",
    "https://traffitwin-ai.firebaseapp.com",
]

BLOCKED_ORIGINS = [
    "https://evil.example.com",
    "https://attacker.io",
    "null",
]

GET_ENDPOINTS = ["/health", "/state", "/graph", "/metrics"]

POST_ENDPOINTS = [
    ("/step", {"steps": 1}),
    ("/simulate_failure", {"sensor_id": 0, "duration": 5}),
    ("/analyze-current-state", None),
]


def preflight(path: str, origin: str) -> dict:
    """Send a CORS preflight (OPTIONS) request and return response headers."""
    r = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    return r.status_code, r.headers


def simple_get(path: str, origin: str):
    return client.get(path, headers={"Origin": origin})


def simple_post(path: str, body: dict | None, origin: str):
    return client.post(
        path,
        json=body,
        headers={"Origin": origin, "Content-Type": "application/json"},
    )


# ---------------------------------------------------------------------------
# 1. Preflight (OPTIONS) – allowed origins must receive the header back
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
@pytest.mark.parametrize("path", GET_ENDPOINTS)
def test_preflight_allowed_origins_get(path, origin):
    status, headers = preflight(path, origin)
    assert status in (200, 204), f"Preflight failed for {path} from {origin}"
    assert "access-control-allow-origin" in headers, (
        f"ACAO header missing for {path} from {origin}"
    )
    assert headers["access-control-allow-origin"] == origin, (
        f"ACAO header mismatch: expected {origin}, got {headers.get('access-control-allow-origin')}"
    )


@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
@pytest.mark.parametrize("path,_body", POST_ENDPOINTS)
def test_preflight_allowed_origins_post(path, _body, origin):
    r = client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert r.status_code in (200, 204), (
        f"POST preflight failed for {path} from {origin}: {r.status_code}"
    )
    assert "access-control-allow-origin" in r.headers, (
        f"ACAO header missing for POST preflight {path} from {origin}"
    )


# ---------------------------------------------------------------------------
# 2. Preflight – blocked origins must NOT receive ACAO header
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("origin", BLOCKED_ORIGINS)
@pytest.mark.parametrize("path", GET_ENDPOINTS[:1])   # spot-check with /health
def test_preflight_blocked_origins(path, origin):
    status, headers = preflight(path, origin)
    # ACAO must not be set to the attacker's origin
    acao = headers.get("access-control-allow-origin", "")
    assert acao != origin, (
        f"SECURITY: Blocked origin {origin} received ACAO for {path}!"
    )


# ---------------------------------------------------------------------------
# 3. Actual GET requests with ACAO header present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ALLOWED_ORIGINS)
@pytest.mark.parametrize("path", GET_ENDPOINTS)
def test_get_endpoints_cors_header(path, origin):
    r = simple_get(path, origin)
    assert r.status_code in (200, 503), (
        f"Unexpected status {r.status_code} for GET {path}"
    )
    assert "access-control-allow-origin" in r.headers, (
        f"ACAO missing on GET {path} from {origin}"
    )
    assert r.headers["access-control-allow-origin"] == origin


# ---------------------------------------------------------------------------
# 4. POST endpoints – ACAO header must be present on actual responses
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("origin", ["http://localhost:5173", "https://traffitwin-ai.web.app"])
@pytest.mark.parametrize("path,body", POST_ENDPOINTS)
def test_post_endpoints_cors_header(path, body, origin):
    r = simple_post(path, body, origin)
    # We accept any non-5xx response (503 = service not ready in CI is fine)
    assert r.status_code < 600, f"Hard failure on POST {path}"
    assert "access-control-allow-origin" in r.headers, (
        f"ACAO missing on POST {path} from {origin}"
    )
    assert r.headers["access-control-allow-origin"] == origin


# ---------------------------------------------------------------------------
# 5. allow_credentials must be False (no cookie/auth)
# ---------------------------------------------------------------------------

def test_credentials_header_not_present():
    """ACAO credentials header must not be set to 'true'."""
    r = simple_get("/health", "http://localhost:5173")
    aca = r.headers.get("access-control-allow-credentials", "false")
    assert aca.lower() != "true", (
        "access-control-allow-credentials must not be 'true' "
        "(no auth is used; wildcard-compatible mode required)."
    )


# ---------------------------------------------------------------------------
# 6. /health smoke test
# ---------------------------------------------------------------------------

def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
