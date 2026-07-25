from typing import Any, Dict

from fastapi import Header

from backend.auth.jwt_utils import decode_access_token
from backend.core.exceptions import AuthenticationError


async def get_current_user(authorization: str | None = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_access_token(token)
    except ValueError as e:
        raise AuthenticationError(str(e)) from e
