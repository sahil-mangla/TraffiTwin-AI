from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.api.app import app
from backend.auth.jwt_utils import create_access_token, decode_access_token
from backend.config import settings


def test_create_and_decode_access_token_round_trip():
    token = create_access_token(sub="user-123", email="user@example.com")
    claims = decode_access_token(token)
    assert claims["sub"] == "user-123"
    assert claims["email"] == "user@example.com"


def test_decode_access_token_rejects_expired_token():
    from datetime import datetime, timedelta, timezone

    expired_claims = {
        "sub": "user-123",
        "email": "user@example.com",
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_claims, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_tampered_token():
    token = create_access_token(sub="user-123", email="user@example.com")
    tampered = token[:-4] + "abcd"

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(tampered)


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_dev_login_returns_usable_token(client):
    r = client.post("/auth/dev-login")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["email"] == "dev@traffitwin.local"

    claims = decode_access_token(body["access_token"])
    assert claims["email"] == "dev@traffitwin.local"


def test_google_login_rejects_invalid_id_token(client):
    with patch(
        "backend.auth.routes.google_id_token.verify_oauth2_token",
        side_effect=ValueError("Token used too late"),
    ):
        r = client.post("/auth/google", json={"id_token": "not-a-real-token"})
    assert r.status_code == 401


def test_google_login_succeeds_with_verified_token(client):
    with patch(
        "backend.auth.routes.google_id_token.verify_oauth2_token",
        return_value={"sub": "google-user-1", "email": "someone@gmail.com"},
    ):
        r = client.post("/auth/google", json={"id_token": "a-valid-looking-token"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "someone@gmail.com"


def test_mutating_route_rejects_missing_token(client):
    r = client.post("/step", json={"steps": 1})
    assert r.status_code == 401
    assert r.json()["error_code"] == "AuthenticationError"


def test_mutating_route_rejects_malformed_header(client):
    r = client.post("/step", json={"steps": 1}, headers={"Authorization": "not-bearer-format"})
    assert r.status_code == 401


def test_mutating_route_rejects_garbage_bearer_token(client):
    r = client.post("/step", json={"steps": 1}, headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "AuthenticationError"


def test_mutating_route_accepts_valid_dev_token(client):
    token = client.post("/auth/dev-login").json()["access_token"]
    r = client.post("/step", json={"steps": 1}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_read_only_route_does_not_require_auth(client):
    r = client.get("/state")
    assert r.status_code == 200


def test_health_does_not_require_auth(client):
    """Regression guard: /health must stay unauthenticated so the wake-up
    probe in useWakeUpBackend can ping it before a user has logged in."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_auth_google_route_is_registered(client):
    """Regression guard: /auth/google must exist in the running app.
    This test catches the production regression where the auth router was
    not included and the endpoint returned 404."""
    # We don't provide a real token — we just want a 401/422, not a 404.
    with patch(
        "backend.auth.routes.google_id_token.verify_oauth2_token",
        side_effect=ValueError("Token used too late"),
    ):
        r = client.post("/auth/google", json={"id_token": "not-a-real-token"})
    # 401 means the route exists and rejected the bad token — not 404.
    assert r.status_code == 401, (
        f"Expected 401 from /auth/google but got {r.status_code}. "
        "The auth router may not be registered in app.py."
    )
