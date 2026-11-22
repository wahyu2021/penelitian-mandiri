"""Kontrak detail arsip: field terbatas, nilai kosong, dan galat aman."""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.archive_detail import get_archive_detail
from services.db import get_connection, init_db
from webapp import create_app


@pytest.fixture
def archive_app(tmp_path):
    path = tmp_path / "archive-detail.sqlite"
    connection = init_db(path)
    with connection:
        now = datetime.now(timezone.utc).isoformat()
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            connection.execute(
                "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash("kata-sandi-aman"), role, now),
            )
        connection.execute(
            """INSERT INTO import_batch
               (source_filename, source_sha256, parser_version, extractor_version, imported_at)
               VALUES ('sample.sql', 'abc', 'v1', 'v1', ?)""", (now,),
        )
        connection.execute(
            "INSERT INTO opd(id, name, name_normalized) VALUES (1, 'Dinas PU', 'dinas pu')"
        )
        connection.execute(
            "INSERT INTO classification(id, code, name) VALUES (3, 'K3', 'Pekerjaan Umum')"
        )
        connection.execute(
            """INSERT INTO spm_type(code, label, confidence, source_note)
               VALUES ('ZZ_TEST', 'Jenis dugaan', 'dugaan', 'data uji')"""
        )
        connection.execute(
            """INSERT INTO archive
               (id, batch_id, opd_id, opd_id_source, classification_id, year,
                summary_raw, file_number, index_label, location_block,
                location_rack, location_row, box_number, status, has_document,
                document_filename, retention_note)
               VALUES (41, 1, 1, 1, 3, 2020, ?, 'BRK-41', 'Jembatan',
                       'A', '2', '3', 'Box 4', 1, 1, 'rahasia.pdf', 'catatan internal')""",
            ("Permohonan jembatan <script>alert(1)</script>",),
        )
        connection.execute(
            """INSERT INTO archive_metadata
               (archive_id, spm_number, spm_type_code, sp2d_number, document_date,
                amount_rp, party_name, party_normalized, has_spm_label,
                extractor_version, extracted_at)
               VALUES (41, 'SPM-41', 'ZZ_TEST', 'SP2D-41', '2020-04-20',
                       2500000, 'CV Contoh', 'cv contoh', 1, 'v1', ?)""",
            (now,),
        )
        connection.execute(
            """INSERT INTO archive
               (id, batch_id, opd_id_source, status, has_document)
               VALUES (42, 1, 0, 3, 0)"""
        )
    connection.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path})


def login(client, username="admin"):
    token = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session", json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["admin", "petugas"])
def test_archive_detail_contains_original_and_extraction_with_guess_status(archive_app, role):
    client = archive_app.test_client()
    login(client, role)
    response = client.get("/api/v1/archives/41")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.is_json
    detail = response.get_json()["data"]
    assert detail == {
        "id": 41, "status": 1, "year": 2020,
        "opd_name": "Dinas PU", "classification_label": "Pekerjaan Umum",
        "file_number": "BRK-41", "index_label": "Jembatan",
        "summary_raw": "Permohonan jembatan <script>alert(1)</script>",
        "has_document": True,
        "location": {"block": "A", "rack": "2", "row": "3", "box_number": "Box 4"},
        "extraction": {
            "spm_number": "SPM-41", "sp2d_number": "SP2D-41",
            "document_date": "2020-04-20", "amount_rp": 2500000,
            "party_name": "CV Contoh",
            "spm_type": {"code": "ZZ_TEST", "label": "Jenis dugaan", "confidence": "dugaan"},
        },
    }
    body = response.get_data(as_text=True)
    assert "rahasia.pdf" not in body
    assert "catatan internal" not in body
    assert "party_normalized" not in body
    assert "password_hash" not in body

    # API tetap mengirim teks asli yang sama dengan sumber data.
    connection = get_connection(archive_app.config["DATABASE"])
    try:
        source = get_archive_detail(connection, 41)
        assert detail["summary_raw"] == source["summary_raw"]
    finally:
        connection.close()


def test_archive_detail_preserves_missing_values_as_null(archive_app):
    client = archive_app.test_client()
    login(client)
    detail = client.get("/api/v1/archives/42").get_json()["data"]
    assert detail["year"] is None
    assert detail["summary_raw"] is None
    assert detail["opd_name"] is None
    assert detail["classification_label"] is None
    assert detail["has_document"] is False
    assert detail["location"] == {"block": None, "rack": None, "row": None, "box_number": None}
    assert detail["extraction"] == {
        "spm_number": None, "sp2d_number": None, "document_date": None,
        "amount_rp": None, "party_name": None, "spm_type": None,
    }


def test_archive_detail_requires_login_and_checks_id(archive_app):
    client = archive_app.test_client()
    denied = client.get("/api/v1/archives/41")
    assert denied.status_code == 401
    assert denied.is_json
    login(client)
    for invalid in ("0", "-1", "abc", "9999999999999999999999999999"):
        response = client.get("/api/v1/archives/" + invalid)
        assert response.status_code == 400
        assert response.is_json
    missing = client.get("/api/v1/archives/999")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "not_found"


def test_archive_detail_database_failure_is_safe_json(archive_app):
    client = archive_app.test_client()
    login(client)
    connection = get_connection(archive_app.config["DATABASE"])
    with connection:
        connection.execute("DROP TABLE archive_metadata")
    connection.close()
    response = client.get("/api/v1/archives/41")
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "server_error"
    assert "no such table" not in response.get_data(as_text=True)
