"""Dashboard API memakai angka dari database sumber."""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.dashboard import get_dashboard_summary
from services.db import get_connection, init_db
from webapp import create_app


@pytest.fixture
def dashboard_app(tmp_path):
    path = tmp_path / "dashboard.sqlite"
    connection = init_db(path)
    with connection:
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            connection.execute(
                "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash("kata-sandi-aman"), role,
                 datetime.now(timezone.utc).isoformat()),
            )
    connection.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path})


def login(client, username="admin"):
    csrf = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session", json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200


def insert_archives(path):
    connection = get_connection(path)
    with connection:
        connection.execute(
            """INSERT INTO import_batch
               (source_filename, source_sha256, parser_version, extractor_version, imported_at)
               VALUES ('sample.sql', 'abc', 'v1', 'v1', ?)""",
            (datetime.now(timezone.utc).isoformat(),),
        )
        for archive_id, status, has_document, year, summary in (
            (7, 1, 1, 2020, "Jembatan kota"),
            (9, 2, 0, None, None),
            (13, 3, 1, 2022, "Surat izin"),
        ):
            connection.execute(
                """INSERT INTO archive
                   (id, batch_id, opd_id_source, year, summary_raw, status, has_document)
                   VALUES (?, 1, 1, ?, ?, ?, ?)""",
                (archive_id, year, summary, status, has_document),
            )
    connection.close()


def test_dashboard_requires_login_and_returns_json(dashboard_app):
    client = dashboard_app.test_client()
    denied = client.get("/api/v1/dashboard")
    assert denied.status_code == 401
    assert denied.is_json
    assert "Location" not in denied.headers


@pytest.mark.parametrize("role", ["admin", "petugas"])
def test_dashboard_empty_database_has_zero_counts(dashboard_app, role):
    client = dashboard_app.test_client()
    login(client, role)
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.get_json() == {"data": {
        "counts": {"total": 0, "active": 0, "inactive": 0, "with_file": 0},
        "recent": [],
        "latest_import": None,
    }}


def test_dashboard_matches_database_counts_and_jinja(dashboard_app):
    path = dashboard_app.config["DATABASE"]
    insert_archives(path)
    client = dashboard_app.test_client()
    login(client)
    api = client.get("/api/v1/dashboard")
    assert api.status_code == 200
    data = api.get_json()["data"]
    connection = get_connection(path)
    try:
        assert data == get_dashboard_summary(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total, SUM(status = 1) AS active, "
            "SUM(status = 2) AS inactive, SUM(has_document = 1) AS with_file FROM archive"
        ).fetchone()
        assert data["counts"] == {key: row[key] for key in data["counts"]}
    finally:
        connection.close()
    assert data["recent"] == [
        {"id": 13, "year": 2022, "summary_raw": "Surat izin", "opd_name": None},
        {"id": 9, "year": None, "summary_raw": None, "opd_name": None},
        {"id": 7, "year": 2020, "summary_raw": "Jembatan kota", "opd_name": None},
    ]
    assert data["latest_import"]["source_filename"] == "sample.sql"
    assert data["latest_import"]["clean_count"] == 0
    assert data["latest_import"]["imported_at"]


def test_dashboard_database_failure_does_not_leak_sql_error(dashboard_app):
    client = dashboard_app.test_client()
    login(client)
    path = dashboard_app.config["DATABASE"]
    connection = get_connection(path)
    with connection:
        connection.execute("DROP TABLE archive")
    connection.close()
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "server_error"
    assert "no such table" not in response.get_data(as_text=True)
