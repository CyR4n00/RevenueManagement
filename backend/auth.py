"""Supabase access-token validation for the application API.

The browser holds only a Supabase publishable key and its own session token.
This module asks Supabase Auth to validate that token; it never accepts a user
identifier supplied by the browser and never exposes a secret/service key.
"""

from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException, status

from settings import get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str


async def require_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    settings = get_settings()
    if not settings.supabase_auth_required:
        # Local demo data is intentionally isolated from production by a
        # different SQLite file.  Production always validates a real session.
        return CurrentUser(id="demo-user", email="demo@example.invalid")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_publishable_key},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is unavailable") from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your sign-in session is invalid or expired")
    payload = response.json()
    user_id = payload.get("id")
    email = payload.get("email")
    if not isinstance(user_id, str) or not isinstance(email, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication response is invalid")
    return CurrentUser(id=user_id, email=email)
