"""Tests for role bootstrap behavior in get_current_user_with_role."""

from __future__ import annotations

import asyncio

from fastapi.security import HTTPAuthorizationCredentials

from integrations.pulse.core import auth
from integrations.pulse.core.models import UserProfile


def _run_get_current_user_with_role(db_session, user_id: str, monkeypatch):
    async def _fake_decode_token(_token: str, _settings):
        return {
            "preferred_username": user_id,
            "name": user_id.split("@")[0],
        }

    monkeypatch.setattr(auth, "_decode_token", _fake_decode_token)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake.token")
    return asyncio.run(
        auth.get_current_user_with_role(
            credentials=credentials,
            settings=None,
            db=db_session,
        )
    )


def test_first_authenticated_user_bootstraps_to_admin(db_session, monkeypatch) -> None:
    payload = _run_get_current_user_with_role(db_session, "first@chca.org", monkeypatch)

    assert payload["role"] == "ADMIN"
    assert payload["role_detail"] == "president"

    profile = db_session.query(UserProfile).filter_by(azure_user_id="first@chca.org").first()
    assert profile is not None
    assert profile.role == "ADMIN"
    assert profile.role_detail == "president"


def test_subsequent_new_users_default_to_staff(db_session, monkeypatch) -> None:
    _run_get_current_user_with_role(db_session, "first@chca.org", monkeypatch)
    payload = _run_get_current_user_with_role(db_session, "second@chca.org", monkeypatch)

    assert payload["role"] == "STAFF"
    assert payload["role_detail"] == "staff"

    profile = db_session.query(UserProfile).filter_by(azure_user_id="second@chca.org").first()
    assert profile is not None
    assert profile.role == "STAFF"
    assert profile.role_detail == "staff"
