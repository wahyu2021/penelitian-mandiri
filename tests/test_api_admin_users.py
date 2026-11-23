"""Uji kontrak API admin akun lokal dan log aktivitas (PM-21)."""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.db import get_connection, init_db
from webapp import create_app


@pytest.fixture
def admin_app(tmp_path):
    path = tmp_path / "admin_users.sqlite"
    connection = init_db(path)
    with connection:
        now = datetime.now(timezone.utc).isoformat()
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            connection.execute(
                "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash("kata-sandi-aman"), role, now),
            )
    connection.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path})


def login(client, username="admin", password="kata-sandi-aman"):
    csrf = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    return response.get_json()["data"]["csrf_token"]


def test_admin_endpoints_require_login_and_admin_role(admin_app):
    anon = admin_app.test_client()
    for method, url in (
        ("GET", "/api/v1/admin/users"),
        ("POST", "/api/v1/admin/users"),
        ("PATCH", "/api/v1/admin/users/2/status"),
        ("POST", "/api/v1/admin/users/2/reset-password"),
        ("GET", "/api/v1/admin/activity"),
    ):
        resp = anon.open(url, method=method)
        assert resp.status_code == 401
        assert resp.is_json

    petugas = admin_app.test_client()
    csrf = login(petugas, "petugas")
    for method, url, body in (
        ("GET", "/api/v1/admin/users", None),
        ("POST", "/api/v1/admin/users", {"username": "baru", "role": "petugas", "password": "sandi-baru-123"}),
        ("PATCH", "/api/v1/admin/users/2/status", {"is_active": False}),
        ("POST", "/api/v1/admin/users/2/reset-password", {"password": "sandi-baru-123"}),
        ("GET", "/api/v1/admin/activity", None),
    ):
        resp = petugas.open(
            url,
            method=method,
            json=body,
            headers={"X-CSRF-Token": csrf} if body is not None else None,
        )
        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "forbidden"


def test_admin_mutations_require_csrf(admin_app):
    client = admin_app.test_client()
    login(client)
    for method, url, body in (
        ("POST", "/api/v1/admin/users", {"username": "baru", "role": "petugas", "password": "sandi-baru-123"}),
        ("PATCH", "/api/v1/admin/users/2/status", {"is_active": False}),
        ("POST", "/api/v1/admin/users/2/reset-password", {"password": "sandi-baru-123"}),
    ):
        missing = client.open(url, method=method, json=body)
        assert missing.status_code == 403
        wrong = client.open(url, method=method, json=body, headers={"X-CSRF-Token": "salah"})
        assert wrong.status_code == 403


def test_create_user_validation_duplicate_and_no_password_leak(admin_app):
    client = admin_app.test_client()
    csrf = login(client)
    secret_pw = "rahasia-sangat-aman-2026"

    created = client.post(
        "/api/v1/admin/users",
        json={"username": "petugas_dua", "role": "petugas", "password": secret_pw},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    assert created.headers["Cache-Control"] == "no-store"
    user = created.get_json()["data"]["user"]
    assert user["username"] == "petugas_dua"
    assert user["role"] == "petugas"
    assert user["is_active"] is True
    assert "password_hash" not in user
    assert secret_pw not in created.get_data(as_text=True)

    duplicate = client.post(
        "/api/v1/admin/users",
        json={"username": "petugas_dua", "role": "petugas", "password": secret_pw},
        headers={"X-CSRF-Token": csrf},
    )
    assert duplicate.status_code == 409

    for bad in (
        {"username": "a b", "role": "petugas", "password": secret_pw},
        {"username": "petugas_tiga", "role": "superadmin", "password": secret_pw},
        {"username": "petugas_tiga", "role": "petugas", "password": "pendek"},
    ):
        resp = client.post("/api/v1/admin/users", json=bad, headers={"X-CSRF-Token": csrf})
        assert resp.status_code == 422

    # Akun baru dapat login
    other = admin_app.test_client()
    login(other, "petugas_dua", secret_pw)

    # Pastikan kata sandi dan password_hash tidak pernah muncul di log maupun list users
    users_resp = client.get("/api/v1/admin/users")
    assert users_resp.status_code == 200
    assert "password_hash" not in users_resp.get_data(as_text=True)

    logs_resp = client.get("/api/v1/admin/activity")
    assert logs_resp.status_code == 200
    raw_logs = logs_resp.get_data(as_text=True)
    assert secret_pw not in raw_logs
    assert "password_hash" not in raw_logs
    assert any(item["action"] == "user_create" for item in logs_resp.get_json()["data"]["items"])


def test_disable_enable_self_disable_and_reset_password(admin_app):
    client = admin_app.test_client()
    csrf = login(client)

    # Admin tidak dapat menonaktifkan dirinya sendiri
    self_disable = client.patch(
        "/api/v1/admin/users/1/status",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert self_disable.status_code == 409

    # Akun tidak ditemukan -> 404
    missing = client.patch(
        "/api/v1/admin/users/999/status",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert missing.status_code == 404

    # Nonaktifkan petugas -> tidak bisa login lagi
    disabled = client.patch(
        "/api/v1/admin/users/2/status",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert disabled.status_code == 200
    assert disabled.get_json()["data"]["user"]["is_active"] is False

    petugas_client = admin_app.test_client()
    p_csrf = petugas_client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    denied_login = petugas_client.post(
        "/api/v1/session",
        json={"username": "petugas", "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": p_csrf},
    )
    assert denied_login.status_code == 401

    # Aktifkan kembali & reset kata sandi
    enabled = client.patch(
        "/api/v1/admin/users/2/status",
        json={"is_active": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert enabled.status_code == 200
    assert enabled.get_json()["data"]["user"]["is_active"] is True

    new_pw = "kata-sandi-reset-2026"
    reset = client.post(
        "/api/v1/admin/users/2/reset-password",
        json={"password": new_pw},
        headers={"X-CSRF-Token": csrf},
    )
    assert reset.status_code == 200
    assert new_pw not in reset.get_data(as_text=True)

    # Sandi lama gagal, sandi baru berhasil
    old_attempt = petugas_client.post(
        "/api/v1/session",
        json={"username": "petugas", "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": p_csrf},
    )
    assert old_attempt.status_code == 401
    login(petugas_client, "petugas", new_pw)

    # Filter log aktivitas
    filtered = client.get("/api/v1/admin/activity?action=user_reset_password&username=admin&limit=5")
    assert filtered.status_code == 200
    items = filtered.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["action"] == "user_reset_password"
    assert new_pw not in filtered.get_data(as_text=True)

    connection = get_connection(admin_app.config["DATABASE"])
    try:
        actions = [
            row["action"]
            for row in connection.execute("SELECT action FROM activity_log ORDER BY id").fetchall()
        ]
    finally:
        connection.close()
    assert {"login", "user_disable", "user_enable", "user_reset_password"}.issubset(set(actions))
