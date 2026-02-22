"""Tests for /api/v1/admin/ endpoints.

Phase 9c — Part 3 tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestRoleDetailEndpoint:
    def test_admin_can_set_role_detail(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/sectreasurer@chca.org/role-detail",
            json={
                "role_detail": "sectreasurer",
                "display_name": "Jane Smith",
                "email": "sectreasurer@chca.org",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "sectreasurer@chca.org"
        assert data["role"] == "OFFICER"
        assert data["role_detail"] == "sectreasurer"
        assert data["display_name"] == "Jane Smith"

    def test_role_inferred_from_role_detail_president(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/dave2@chca.org/role-detail",
            json={"role_detail": "president"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "ADMIN"

    def test_role_inferred_from_role_detail_execsecretary(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/execsec@chca.org/role-detail",
            json={"role_detail": "execsecretary"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "OFFICER"
        assert data["role_detail"] == "execsecretary"

    def test_role_inferred_from_role_detail_staff(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/staff4@chca.org/role-detail",
            json={"role_detail": "staff"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "STAFF"

    def test_explicit_role_overrides_inference(self, admin_client: TestClient) -> None:
        """Explicit role parameter beats the auto-inferred value."""
        resp = admin_client.post(
            "/api/v1/admin/users/testuser@chca.org/role-detail",
            json={"role_detail": "staff", "role": "OFFICER"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "OFFICER"

    def test_invalid_role_detail_rejected(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/anyone@chca.org/role-detail",
            json={"role_detail": "superadmin"},
        )
        assert resp.status_code == 422

    def test_invalid_role_rejected(self, admin_client: TestClient) -> None:
        resp = admin_client.post(
            "/api/v1/admin/users/anyone@chca.org/role-detail",
            json={"role_detail": "staff", "role": "SUPERUSER"},
        )
        assert resp.status_code == 422

    def test_staff_cannot_set_role_detail(self, staff_client: TestClient) -> None:
        resp = staff_client.post(
            "/api/v1/admin/users/anyone@chca.org/role-detail",
            json={"role_detail": "president"},
        )
        assert resp.status_code == 403

    def test_officer_cannot_set_role_detail(self, sectreasurer_client: TestClient) -> None:
        resp = sectreasurer_client.post(
            "/api/v1/admin/users/anyone@chca.org/role-detail",
            json={"role_detail": "staff"},
        )
        assert resp.status_code == 403

    def test_upsert_updates_existing_profile(self, admin_client: TestClient) -> None:
        """Calling the endpoint twice for the same user_id updates the profile."""
        admin_client.post(
            "/api/v1/admin/users/retest@chca.org/role-detail",
            json={"role_detail": "staff"},
        )
        resp2 = admin_client.post(
            "/api/v1/admin/users/retest@chca.org/role-detail",
            json={"role_detail": "sectreasurer"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["role_detail"] == "sectreasurer"
        assert data["role"] == "OFFICER"


class TestGetUserProfile:
    def test_admin_can_get_user_profile(self, admin_client: TestClient) -> None:
        # First create the profile
        admin_client.post(
            "/api/v1/admin/users/gettest@chca.org/role-detail",
            json={"role_detail": "execsecretary"},
        )
        resp = admin_client.get("/api/v1/admin/users/gettest@chca.org")
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_detail"] == "execsecretary"

    def test_get_missing_user_returns_404(self, admin_client: TestClient) -> None:
        resp = admin_client.get("/api/v1/admin/users/nobody@chca.org")
        assert resp.status_code == 404

    def test_staff_cannot_get_profile(self, staff_client: TestClient) -> None:
        resp = staff_client.get("/api/v1/admin/users/anyone@chca.org")
        assert resp.status_code == 403
