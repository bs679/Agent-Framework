"""Azure AD JWT authentication for Pulse agent-plane endpoints.

Validates tokens issued by Azure AD (v2.0 endpoint) and extracts the
authenticated user identity (preferred_username / oid).

In development mode, signature verification is skipped and the token
payload is decoded directly.  Production should enable full JWKS-based
RS256 verification against the Azure AD discovery endpoint.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from integrations.pulse.core.config import AgentPlaneSettings, get_settings

_bearer_scheme = HTTPBearer()


def _b64_decode(segment: str) -> bytes:
    """Decode a URL-safe base64 segment with padding fix."""
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += "=" * padding
    return base64.urlsafe_b64decode(segment)


def _decode_token(
    token: str,
    settings: AgentPlaneSettings,
) -> dict[str, Any]:
    """Decode a JWT payload without signature verification (dev mode).

    Raises ``HTTPException(401)`` on any decode failure.

    Production TODO: fetch JWKS from
      https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys
    and verify RS256 signature + aud/iss claims.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Token does not have a valid JWT structure")
        payload_bytes = _b64_decode(parts[1])
        payload: dict[str, Any] = json.loads(payload_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: AgentPlaneSettings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency — returns the authenticated user's token claims.

    Injects ``user_id`` (preferred_username or oid) into the dict for
    convenience.
    """
    payload = _decode_token(credentials.credentials, settings)
    payload["user_id"] = payload.get("preferred_username") or payload.get("oid", "unknown")
    return payload
