"""Kontrak API dan jaminan non-destruktif tinjauan kandidat duplikat [PM-24]."""

from werkzeug.security import generate_password_hash

from services.db import init_db
from webapp import create_app

ENDPOINT = "/api/v1/research/duplicates"


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return {"X-CSRF-Token": res.json["data"]["csrf_token"]}


def _setup_app(tmp_path, *, with_candidates: bool):
    path = tmp_path / "duplicates.sqlite"
    conn = init_db(path)
    pw = generate_password_hash("kata-sandi-aman")
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [("peneliti", pw, "admin"), ("petugas", pw, "petugas")],
        )
        if with_candidates:
            conn.execute(
                """INSERT INTO import_batch(source_filename, source_sha256, parser_version, extractor_version, imported_at)
                   VALUES ('dump.sql', 'abc', '1', 'v1.0.0', '2026-01-01')"""
            )
            conn.execute("INSERT INTO opd(id, name, name_normalized) VALUES (1, 'Dinas PU', 'dinas pu')")
            conn.executemany(
                """INSERT INTO archive(id, batch_id, opd_id, opd_id_source, year, summary_raw, summary_clean, summary_normalized, status, has_document)
                   VALUES (?, 1, 1, 1, 2024, ?, ?, ?, 1, 0)""",
                [
                    (101, "SPM 001 perbaikan jalan", "SPM 001 perbaikan jalan", "spm 001 perbaikan jalan"),
                    (102, "SPM 001 perbaikan jalan utama", "SPM 001 perbaikan jalan utama", "spm 001 perbaikan jalan utama"),
                    (103, "Pengadaan perangkat jaringan kantor pusat", "Pengadaan perangkat jaringan kantor pusat", "pengadaan perangkat jaringan kantor pusat"),
                ],
            )
            conn.executemany(
                """INSERT INTO archive_metadata(archive_id, spm_number, has_spm_label, extractor_version, extracted_at)
                   VALUES (?, ?, 1, 'v1.0.0', '2026-01-01')""",
                [(101, "001/UP"), (102, "001/UP"), (103, "009/LS")],
            )
    conn.close()
    return create_app({"TESTING": True, "DATABASE": path, "SECRET_KEY": "test", "SERVE_REACT": False}), path


def test_duplicates_permissions_and_empty_state(tmp_path):
    app, _ = _setup_app(tmp_path, with_candidates=False)
    assert app.test_client().get(ENDPOINT).status_code == 401

    staff = app.test_client()
    h_staff = _login(staff, "petugas")
    assert staff.get(ENDPOINT).status_code == 403
    assert staff.put(f"{ENDPOINT}/1/2", headers=h_staff, json={"decision": "duplikat", "notes": ""}).status_code == 403

    admin = app.test_client()
    _login(admin, "peneliti")
    res = admin.get(ENDPOINT)
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "no-store"
    assert res.json["data"]["items"] == []
    assert res.json["data"]["summary"]["total_candidates"] == 0


def test_duplicates_review_correction_history_and_preserves_source_archives(tmp_path):
    app, db_path = _setup_app(tmp_path, with_candidates=True)
    admin = app.test_client()
    headers = _login(admin, "peneliti")

    initial = admin.get(ENDPOINT).json["data"]
    assert initial["summary"]["total_candidates"] == 1
    assert initial["summary"]["unreviewed"] == 1
    pair = initial["items"][0]
    assert (pair["archive_a_id"], pair["archive_b_id"]) == (101, 102)
    assert pair["reason"] == "same_spm"

    # Tolak tanpa CSRF
    assert (
        admin.put(f"{ENDPOINT}/101/102", json={"decision": "duplikat", "notes": "x"}).status_code
        == 403
    )

    # Simpan keputusan pertama (pakai urutan terbalik 102/101 untuk uji kanonisasi)
    saved1 = admin.put(
        f"{ENDPOINT}/102/101",
        headers=headers,
        json={"decision": "perlu_cek", "notes": "Perlu konfirmasi berkas fisik"},
    )
    assert saved1.status_code == 200
    assert (saved1.json["data"]["archive_a_id"], saved1.json["data"]["archive_b_id"]) == (101, 102)

    # Koreksi menjadi bukan_duplikat
    saved2 = admin.put(
        f"{ENDPOINT}/101/102",
        headers=headers,
        json={"decision": "bukan_duplikat", "notes": "Tanggal SPM berbeda"},
    )
    assert saved2.status_code == 200

    after = admin.get(f"{ENDPOINT}?status=bukan_duplikat").json["data"]
    assert after["summary"]["bukan_duplikat"] == 1
    assert after["summary"]["unreviewed"] == 0
    item = after["items"][0]
    assert item["decision"] == "bukan_duplikat"
    assert item["reviewed_by"] == "peneliti"
    assert len(item["history"]) == 2
    assert item["history"][0]["old_decision"] == "perlu_cek"
    assert item["history"][0]["new_decision"] == "bukan_duplikat"

    # Pastikan tabel archive dan archive_metadata tetap utuh (tidak ada operasi hapus/gabung)
    conn = init_db(db_path)
    assert conn.execute("SELECT COUNT(*) FROM archive").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM archive_metadata").fetchone()[0] == 3
    conn.close()

    # Validasi input buruk
    assert (
        admin.put(f"{ENDPOINT}/101/101", headers=headers, json={"decision": "duplikat", "notes": ""}).status_code
        == 422
    )
    assert (
        admin.put(f"{ENDPOINT}/101/102", headers=headers, json={"decision": "hapus", "notes": ""}).status_code
        == 422
    )
    assert admin.get(f"{ENDPOINT}?reason=invalid").status_code == 400
