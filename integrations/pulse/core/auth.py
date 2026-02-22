"""Azure AD JWT authentication for Pulse agent-plane endpoints.

Validates tokens issued by Azure AD (v2.0 endpoint) and extracts the
authenticated user identity (preferred_username / oid).

DEVELOPMENT vs PRODUCTION mode
-------------------------------
Dev mode (PULSE_DEV_MODE=true) decodes the JWT payload without verifying
the RS256 signature. This is ONLY acceptable for local development against
a real Azure AD tenant where the token structure is still enforced.

Production mode (default) verifies the RS256 signature using JWKS fetched
from the Azure AD discovery endpoint, and validates aud/iss claims.

To enable dev mode explicitly set:
    PULSE_DEV_MODE=true  # in .env — must not be set in production
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from integrations.pulse.core.config import AgentPlaneSettings, get_settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer()

# Dev mode must be explicitly opted into — default is False (production-safe).
_DEV_MODE: bool = os.environ.get("PULSE_DEV_MODE", "").lower() in ("true", "1", "yes")

if _DEV_MODE:
    logger.warning(
        "PULSE_DEV_MODE=true — JWT signature verification is DISABLED. "
        "This must not be used in production."
    )


def _b64_decode(segment: str) -> bytes:
    """Decode a URL-safe base64 segment with padding fix."""
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += "=" * padding
    return base64.urlsafe_b64decode(segment)


def _decode_payload_unverified(token: str) -> dict[str, Any]:
    """Decode JWT payload without signature check (dev mode only).

    Raises HTTPException(401) on structural failures.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Token does not have a valid JWT structure")
        payload_bytes = _b64_decode(parts[1])
        return json.loads(payload_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def _verify_token_production(
    token: str,
    settings: AgentPlaneSettings,
) -> dict[str, Any]:
    """Verify RS256 JWT signature using Azure AD JWKS.

    Fetches public keys from the Azure AD v2.0 discovery endpoint, verifies
    the token signature, and validates the aud and iss claims.

    Requires PyJWT[crypto] (already in requirements.txt).
    """
    import jwt as pyjwt  # PyJWT

    tenant = settings.azure_ad_tenant_id
    audience = settings.azure_ad_audience

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server misconfiguration: AZURE_AD_TENANT_ID not set",
        )

    jwks_uri = f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"
    issuer = f"https://login.microsoftonline.com/{tenant}/v2.0"

    try:
        jwks_client = pyjwt.PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=3600)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload: dict[str, Any] = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except pyjwt.PyJWKClientError as exc:
        logger.error("Failed to fetch/resolve JWKS from %s: %s", jwks_uri, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch authentication keys",
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch JWKS from %s: %s", jwks_uri, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch authentication keys",
        ) from exc


async def _decode_token(
    token: str,
    settings: AgentPlaneSettings,
) -> dict[str, Any]:
    """Route to dev-mode or production token validation."""
    if _DEV_MODE:
        return _decode_payload_unverified(token)
    return await _verify_token_production(token, settings)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: AgentPlaneSettings = Depends(get_settings),
) -> dict[str, Any]:
    """FastAPI dependency — returns the authenticated user's token claims.

    Injects ``user_id`` (preferred_username or oid) into the dict for
    convenience.
    """
    payload = await _decode_token(credentials.credentials, settings)
    payload["user_id"] = payload.get("preferred_username") or payload.get("oid", "unknown")
    return payload
