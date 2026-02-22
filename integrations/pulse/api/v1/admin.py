"""Admin-only endpoints for Pulse.

All endpoints under /api/v1/admin/ require the ADMIN role.  Non-ADMIN
requests are rejected with 403 Forbidden.

Endpoints
---------
POST /api/v1/admin/users/{user_id}/role-detail
    Assign or update role + role_detail for a user profile.
    This is how Dave sets SecTreas vs ExecSec for the officer staff.

GET  /api/v1/admin/users/{user_id}
    Retrieve a user profile (ADMIN only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from integrations.pulse.api.v1.schemas import RoleDetailRequest, UserProfileResponse
from integrations.pulse.core.auth import get_current_user_with_role
from integrations.pulse.core.database import get_db
from integrations.pulse.core.models import RoleDetail, UserProfile, UserRole

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Role validation helpers
# ---------------------------------------------------------------------------

_VALID_ROLE_DETAILS = {rd.value for rd in RoleDetail}
_VALID_ROLES = {r.value for r in UserRole}

# Automatic top-level role inference from role_detail
_ROLE_FROM_DETAIL: dict[str, str] = {
    "president": UserRole.ADMIN.value,
    "sectreasurer": UserRole.OFFICER.value,
    "execsecretary": UserRole.OFFICER.value,
    "staff": UserRole.STAFF.value,
}


def _require_admin(user: dict[str, Any]) -> None:
    """Raise 403 if the user is not ADMIN."""
    if user.get("role") != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires ADMIN role.",
        )


# ---------------------------------------------------------------------------
# POST /api/v1/admin/users/{user_id}/role-detail
# ---------------------------------------------------------------------------

@router.post(
    "/users/{user_id}/role-detail",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def set_user_role_detail(
    user_id: str,
    body: RoleDetailRequest,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Assign or update a user's role_detail (and optionally role).

    If *role* is omitted in the request body, it is inferred from
    *role_detail* automatically:
      - president      → ADMIN
      - sectreasurer   → OFFICER
      - execsecretary  → OFFICER
      - staff          → STAFF

    Only ADMIN (Dave) can call this endpoint.
    """
    _require_admin(caller)

    # Validate role_detail
    if body.role_detail not in _VALID_ROLE_DETAILS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid role_detail {body.role_detail!r}. "
                f"Must be one of: {', '.join(sorted(_VALID_ROLE_DETAILS))}"
            ),
        )

    # Determine top-level role
    if body.role:
        if body.role not in _VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid role {body.role!r}. "
                    f"Must be one of: {', '.join(sorted(_VALID_ROLES))}"
                ),
            )
        resolved_role = body.role
    else:
        resolved_role = _ROLE_FROM_DETAIL[body.role_detail]

    # Upsert user profile
    profile: UserProfile | None = (
        db.query(UserProfile)
        .filter(UserProfile.azure_user_id == user_id)
        .first()
    )

    if profile is None:
        profile = UserProfile(
            azure_user_id=user_id,
            role=resolved_role,
            role_detail=body.role_detail,
            display_name=body.display_name,
            email=body.email,
        )
        db.add(profile)
        action = "created"
    else:
        profile.role = resolved_role
        profile.role_detail = body.role_detail
        if body.display_name is not None:
            profile.display_name = body.display_name
        if body.email is not None:
            profile.email = body.email
        profile.updated_at = datetime.utcnow()
        action = "updated"

    db.commit()
    db.refresh(profile)

    return UserProfileResponse(
        user_id=profile.azure_user_id,
        role=profile.role,
        role_detail=profile.role_detail,
        display_name=profile.display_name,
        email=profile.email,
        message=f"User profile {action} successfully.",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users/{user_id}
# ---------------------------------------------------------------------------

@router.get(
    "/users/{user_id}",
    response_model=UserProfileResponse,
)
async def get_user_profile(
    user_id: str,
    caller: dict[str, Any] = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Retrieve a user's role profile.  ADMIN only."""
    _require_admin(caller)

    profile: UserProfile | None = (
        db.query(UserProfile)
        .filter(UserProfile.azure_user_id == user_id)
        .first()
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No profile found for user_id={user_id!r}.",
        )

    return UserProfileResponse(
        user_id=profile.azure_user_id,
        role=profile.role,
        role_detail=profile.role_detail,
        display_name=profile.display_name,
        email=profile.email,
        message="Profile retrieved.",
    )
