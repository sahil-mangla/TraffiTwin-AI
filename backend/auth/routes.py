from fastapi import APIRouter, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from backend.api.schemas import GoogleLoginRequest, TokenResponse
from backend.auth.jwt_utils import create_access_token
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
async def login_with_google(payload: GoogleLoginRequest) -> TokenResponse:
    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token,
            google_requests.Request(),
            settings.google_oauth_client_id.get_secret_value(),
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {e}") from e

    email = claims["email"]
    access_token = create_access_token(sub=claims["sub"], email=email)
    return TokenResponse(access_token=access_token, email=email)


@router.post("/dev-login", response_model=TokenResponse)
async def dev_login() -> TokenResponse:
    # Lets local development and CI/E2E exercise the JWT-protected routes
    # without a real Google account. Never available in production — see
    # backend/config.py's _validate_production_config for the matching
    # requirement that GOOGLE_OAUTH_CLIENT_ID/JWT_SECRET_KEY be set for real.
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="Not found")

    email = "dev@traffitwin.local"
    access_token = create_access_token(sub="dev-user", email=email)
    return TokenResponse(access_token=access_token, email=email)
