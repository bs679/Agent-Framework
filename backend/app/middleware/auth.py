"""JWT authentication middleware for admin endpoints.

All admin endpoints require ADMIN role. Returns 403 for non-admins.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt
from jwt.exceptions import PyJWTError as JWTError

security = HTTPBearer()

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Dependency that verifies the JWT and checks for ADMIN role."""
    payload = decode_token(credentials.credentials)

    role = payload.get("role", "")
    roles = payload.get("roles", [])

    if role != "ADMIN" and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return payload
