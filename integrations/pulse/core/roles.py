"""Role-based access control for Pulse officer module endpoints.

Azure AD app roles are surfaced in the JWT `roles` claim as a list of strings.
Configure the app role "OFFICER" in the Azure AD app registration and assign
it to SecTreas and ExecSec users.

Role hierarchy:
  OFFICER — paid officers (President, SecTreas, ExecSec)
  (default) — standard staff agents

Usage in endpoints::

    from integrations.pulse.core.roles import require_officer

    @router.post("/disburse")
    async def create(user = Depends(require_officer)):
        ...
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status

from integrations.pulse.core.auth import get_current_user

OFFICER_ROLE = "OFFICER"


def _has_officer_role(user: dict[str, Any]) -> bool:
    """Return True if the user's JWT contains the OFFICER app role."""
    roles = user.get("roles", [])
    if isinstance(roles, list):
        return OFFICER_ROLE in roles
    # Some tenants return a space-separated string
    if isinstance(roles, str):
        return OFFICER_ROLE in roles.split()
    return False


async def require_officer(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """FastAPI dependency — raises 403 if the caller is not an OFFICER.

    Returns the full user dict (same shape as get_current_user) so callers
    can read user_id etc. without a separate Depends call.
    """
    if not _has_officer_role(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officer role required for this action.",
        )
    return user
