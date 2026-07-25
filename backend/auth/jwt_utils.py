from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from backend.config import settings

_ALGORITHM = "HS256"


def create_access_token(sub: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret_key.get_secret_value(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=[_ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}") from e
