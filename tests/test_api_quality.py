"""Kontrak API dan konsistensi hitungan tinjauan kualitas metadata [PM-23]."""

import pytest
from werkzeug.security import generate_password_hash

from services.db import init_db
from webapp import create_app

ENDPOINT = "/api/v1/research/quality"


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200


def _setup_app(tmp_path, *, with_data: bool):
    path = tmp_path / "quality.sqlite"
    conn = init_db(path)
    pw = generate_password_hash("kata-sandi-aman")
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [("peneliti", pw, "admin"), ("petugas", pw, "petugas")],
        )
        if with_data:
            conn.execute(
                """INSERT INTO import_batch(source_filename, source_sha256, parser_version, extractor_version, imported_at)
                   VALUES ('dump.sql', 'abc', '1', 'v1.0.0', '2026-01-01')"""
            )
            conn.execute("INSERT INTO opd(id, name, name_normalized) VALUES (1, 'Dinas PU', 'dinas pu')")
            conn.execute(
                """UPDATE spm_type SET confidence = 'terkonfirmasi', source_note = 'Resmi',
                   confirmed_by = 'peneliti', confirmed_at = '2026-01-02' WHERE code = 'UP'"""
            )
            conn.executemany(
                """INSERT INTO archive(id, batch_id, opd_id, opd_id_source, year, summary_raw, summary_clean, status, has_document)
                   VALUES (?, 1, ?, ?, 2024, ?, 'bersih', 1, 0)""",
                [
                    (1, 1, 1, "SPM UP 001 pembangunan jalan"),
                    (2, None, 99, "SPM LS 002 pembayaran honor"),
                    (3, 1, 1, "Dokumen tanpa kode spm"),
                ],
            )
            conn.executemany(
                """INSERT INTO archive_metadata(archive_id, spm_number, spm_type_code, sp2d_number, document_date, amount_rp, party_name, has_spm_label, extractor_version, extracted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v1.0.0', '2026-01-01')""",
                [
                    (1, "001/UP", "UP", "SP2D-1", "2024-05-01", 1000000, "CV Maju", 1),
                    (2, "002/LS", "LS", None, None, None, None, 1),
                    (3, None, None, None, None, None, None, 0),
                ],
            )
            conn.executemany(
                """INSERT INTO data_issue(archive_id, batch_id, issue_type, field_name, raw_value, detail)
                   VALUES (?, 1, ?, ?, ?, ?)""",
                [
                    (2, "orphan_opd", "opd_id", "99", "OPD tidak ditemukan pada tabel referensi."),
                    (2, "invalid_input_date", "input_tahun", "0000-00-00", "Tanggal input tidak valid."),
                    (1, "upload_error_document", "dokumen", "err.pdf", "Penanda unggah galat pada dokumen."),
                ],
            )
    conn.close()
    return create_app({"TESTING": True, "DATABASE": path, "SECRET_KEY": "test", "SERVE_REACT": False})


def test_quality_permissions_and_empty_state(tmp_path):
    app = _setup_app(tmp_path, with_data=False)
    assert app.test_client().get(ENDPOINT).status_code == 401

    staff = app.test_client()
    _login(staff, "petugas")
    assert staff.get(ENDPOINT).status_code == 403

    admin = app.test_client()
    _login(admin, "peneliti")
    res = admin.get(ENDPOINT)
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "no-store"
    data = res.json["data"]
    assert data["total_archives"] == 0
    assert data["total_issues"] == 0
    assert len(data["metadata_coverage"]) == 5
    assert all(item["filled"] == 0 and item["missing"] == 0 for item in data["metadata_coverage"])
    assert data["issues"]["items"] == []


def test_quality_counts_consistency_filters_and_validation(tmp_path):
    app = _setup_app(tmp_path, with_data=True)
    admin = app.test_client()
    _login(admin, "peneliti")

    res = admin.get(ENDPOINT)
    assert res.status_code == 200
    data = res.json["data"]

    assert data["total_archives"] == 3
    assert data["total_issues"] == 3
    assert sum(cat["count"] for cat in data["issue_categories"]) == data["total_issues"]
    assert data["spm_confidence_summary"] == {"dugaan": 1, "terkonfirmasi": 1, "tanpa_kode": 1}

    by_field = {item["field"]: item for item in data["metadata_coverage"]}
    for item in data["metadata_coverage"]:
        assert item["filled"] + item["missing"] == data["total_archives"]
    assert by_field["spm_number"]["filled"] == 2
    assert by_field["sp2d_number"]["filled"] == 1
    assert by_field["party_name"]["filled"] == 1

    # Filter berdasarkan kategori dan status dugaan SPM
    filtered_orphan = admin.get(f"{ENDPOINT}?issue_type=orphan_opd").json["data"]
    assert filtered_orphan["issues"]["total"] == 1
    assert filtered_orphan["issues"]["items"][0]["archive_id"] == 2
    assert filtered_orphan["issues"]["items"][0]["spm_confidence"] == "dugaan"

    filtered_conf = admin.get(f"{ENDPOINT}?spm_confidence=terkonfirmasi").json["data"]
    assert filtered_conf["issues"]["total"] == 1
    assert filtered_conf["issues"]["items"][0]["archive_id"] == 1

    # Paginasi per_page=1
    page2 = admin.get(f"{ENDPOINT}?page=2&per_page=1").json["data"]
    assert page2["issues"]["total"] == 3
    assert page2["issues"]["pages"] == 3
    assert len(page2["issues"]["items"]) == 1

    # Validasi parameter buruk
    assert admin.get(f"{ENDPOINT}?spm_confidence=salah").status_code == 400
    assert admin.get(f"{ENDPOINT}?per_page=500").status_code == 400
    assert admin.get(f"{ENDPOINT}?page=abc").status_code == 400
