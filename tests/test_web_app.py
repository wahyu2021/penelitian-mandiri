from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from app import create_app
from services.db import init_db


@pytest.fixture
def web_app(tmp_path):
    database = tmp_path / "web.sqlite"
    conn = init_db(database)
    with conn:
        conn.execute("""INSERT INTO import_batch
            (source_filename, source_sha256, parser_version, extractor_version, imported_at)
            VALUES ('sample.sql', 'abc', 'v1', 'v1', ?)""", (datetime.now(timezone.utc).isoformat(),))
        conn.execute("""INSERT INTO archive
            (id, batch_id, opd_id_source, year, summary_raw, summary_clean, status, has_document)
            VALUES (1, 1, 1, 2005, 'Pembangunan jembatan kota',
                    'Pembangunan jembatan kota', 1, 0)""")
        conn.execute("""INSERT INTO user(username, password_hash, role, created_at)
            VALUES ('admin', ?, 'admin', ?), ('petugas', ?, 'petugas', ?)""",
            (generate_password_hash("password-aman-123"), datetime.now(timezone.utc).isoformat(),
             generate_password_hash("password-aman-456"), datetime.now(timezone.utc).isoformat()))
    conn.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": database})


def log_in(client, username, password):
    client.get("/login")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    return client.post("/login", data={"csrf_token": token, "username": username,
                                       "password": password}, follow_redirects=True)


def test_login_protects_pages_and_rejects_missing_csrf(web_app):
    client = web_app.test_client()
    assert client.get("/").status_code == 302
    assert client.post("/login", data={"username": "admin", "password": "password-aman-123"}).status_code == 400
    assert b"Dashboard arsip" in log_in(client, "admin", "password-aman-123").data


def test_search_compare_and_detail_use_local_corpus(web_app):
    client = web_app.test_client()
    log_in(client, "admin", "password-aman-123")
    assert b"Arsip #1" in client.get("/search?q=jembatan&method=like").data
    assert b"Arsip #1" in client.get("/search?q=jembatan&method=levenshtein").data
    assert b"Levenshtein" in client.get("/search/compare?q=jembatan").data
    detail = client.get("/archives/1")
    assert detail.status_code == 200
    assert b"Pembangunan jembatan kota" in detail.data
    assert client.get("/archives/999").status_code == 404


def test_petugas_cannot_open_admin_comparison(web_app):
    client = web_app.test_client()
    log_in(client, "petugas", "password-aman-456")
    assert client.get("/search?q=jembatan").status_code == 200
    assert client.get("/search/compare?q=jembatan").status_code == 403


def test_invalid_method_is_rejected(web_app):
    client = web_app.test_client()
    log_in(client, "admin", "password-aman-123")
    assert client.get("/search?q=jembatan&method=unknown").status_code == 400


def test_cli_creates_hashed_user_without_touching_existing_accounts(web_app):
    result = web_app.test_cli_runner().invoke(
        args=["user", "create", "--username", "arsiparis", "--role", "petugas"],
        input="kata-sandi-contoh-123\nkata-sandi-contoh-123\n",
    )
    assert result.exit_code == 0, result.output
    with web_app.app_context():
        from webapp.database import db
        row = db().execute(
            "SELECT password_hash, role FROM user WHERE username = ?", ("arsiparis",)
        ).fetchone()
        assert row["role"] == "petugas"
        assert row["password_hash"] != "kata-sandi-contoh-123"
        assert check_password_hash(row["password_hash"], "kata-sandi-contoh-123")
