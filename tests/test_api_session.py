"""Kontrak sesi API, proteksi CSRF, dan izin peran."""

from datetime import datetime, timezone

import pytest
from flask import jsonify
from werkzeug.security import generate_password_hash

from services.db import init_db
from webapp import create_app
from webapp.api.session import require_api_role, require_api_user


@pytest.fixture
def app(tmp_path):
    path = tmp_path / "api-session.sqlite"
    connection = init_db(path)
    with connection:
        for username, role, active in (("admin", "admin", 1), ("petugas", "petugas", 1),
                                       ("nonaktif", "petugas", 0)):
            connection.execute(
                "INSERT INTO user (username, password_hash, role, is_active, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, generate_password_hash("kata-sandi-aman"), role, active,
                 datetime.now(timezone.utc).isoformat()),
            )
    connection.close()
    result = create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path})

    @result.get("/api/v1/_protected")
    @require_api_user
    def protected():
        return jsonify({"data": "ok"})

    @result.get("/api/v1/_admin")
    @require_api_role("admin")
    def admin_only():
        return jsonify({"data": "ok"})

    return result


def token(client):
    response = client.get("/api/v1/session")
    assert response.headers["Cache-Control"] == "no-store"
    return response.get_json()["data"]["csrf_token"]


def login(client, username="admin", password="kata-sandi-aman", csrf=None):
    return client.post(
        "/api/v1/session", json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf if csrf is not None else token(client)},
    )


def test_session_login_logout_rotates_csrf_and_records_role(app):
    client = app.test_client()
    before = token(client)
    response = login(client, csrf=before)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["authenticated"] is True
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
    assert "password" not in str(data)
    assert data["csrf_token"] != before
    assert response.headers["Cache-Control"] == "no-store"
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    assert client.get("/api/v1/_admin").status_code == 200
    assert client.delete("/api/v1/session", headers={"X-CSRF-Token": data["csrf_token"]}).status_code == 200
    assert client.get("/api/v1/_protected").status_code == 401
    assert client.get("/api/v1/session").get_json()["data"]["authenticated"] is False


def test_login_rejects_bad_credentials_inactive_user_and_invalid_body(app):
    client = app.test_client()
    csrf = token(client)
    assert login(client, password="salah", csrf=csrf).status_code == 401
    assert login(client, username="nonaktif", csrf=csrf).status_code == 401
    assert client.post("/api/v1/session", data="not-json", headers={"X-CSRF-Token": csrf}).status_code == 400
    assert client.post("/api/v1/session", json={}, headers={"X-CSRF-Token": csrf}).status_code == 422
    assert client.get("/api/v1/session").get_json()["data"]["authenticated"] is False


def test_csrf_missing_wrong_and_stale_are_rejected(app):
    client = app.test_client()
    old = token(client)
    assert client.post("/api/v1/session", json={"username": "admin", "password": "kata-sandi-aman"}).status_code == 403
    assert login(client, csrf="salah").status_code == 403
    assert login(client, csrf=old).status_code == 200
    assert client.delete("/api/v1/session", headers={"X-CSRF-Token": old}).status_code == 403
    assert client.delete("/api/v1/session").status_code == 403
    assert client.get("/api/v1/session").get_json()["data"]["authenticated"] is True


def test_unauthorized_and_forbidden_are_distinct_without_html_redirect(app):
    client = app.test_client()
    anonymous = client.get("/api/v1/_admin")
    assert anonymous.status_code == 401
    assert anonymous.is_json
    assert "Location" not in anonymous.headers
    assert login(client, username="petugas").status_code == 200
    assert client.get("/api/v1/_protected").status_code == 200
    denied = client.get("/api/v1/_admin")
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "forbidden"


def test_expired_or_disabled_session_is_anonymous(app):
    client = app.test_client()
    assert login(client).status_code == 200
    with client.session_transaction() as cookie:
        cookie.clear()
    assert client.get("/api/v1/_protected").status_code == 401
    assert login(client).status_code == 200
    with app.app_context():
        from webapp.database import db
        with db():
            db().execute("UPDATE user SET is_active = 0 WHERE username = 'admin'")
    assert client.get("/api/v1/_protected").status_code == 401
    assert client.get("/api/v1/session").get_json()["data"]["authenticated"] is False


def test_secure_cookie_can_be_enabled_for_https(app):
    app.config["SESSION_COOKIE_SECURE"] = True
    response = login(app.test_client())
    assert response.status_code == 200
    assert "Secure" in response.headers["Set-Cookie"]
