"""Impor web dibatasi admin, dicadangkan, dan atomik."""

import json
import sqlite3
from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.db import get_connection, init_db
from webapp import create_app


SQL = """
INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES (10, 'Dinas Uji');
INSERT INTO `apptb_klasifikasi` (`id_klasifikasi`, `kode_klasifikasi`, `index`)
VALUES (1, '001', 'Umum');
INSERT INTO `apptb_arsip` (`id_arsip`, `opd_id`, `klasifikasi_id`, `user_id`,
  `no_berkas`, `index_ar`, `tahun`, `input_tahun`, `ringkasan`, `block`,
  `lokasi_rak`, `lokasi_baris`, `no_box`, `tingkat_perkembangan`, `jumlah`,
  `ket_berkas`, `ket_jra`, `stat_dokumen`, `dokumen`, `last_updates`)
VALUES (2, '10', '1', '1', '2/2020', 'Uji', '2020', '2020-05-10',
  'Pembangunan jembatan kota', 'A', '1', '1', '1', 'Asli', '1 berkas',
  'Lengkap', 'Permanen', '1', '', '2020-05-10 10:00:00');
INSERT INTO `apptb_user` (`id`, `username`, `password`) VALUES (99, 'penyusup', 'teks');
"""


@pytest.fixture
def import_app(tmp_path):
    source_dir = tmp_path / "allowed"
    source_dir.mkdir()
    (source_dir / "sample.sql").write_text(SQL, encoding="utf-8")
    (source_dir / "broken.sql").write_text("not a dump", encoding="utf-8")
    db_path = tmp_path / "app.sqlite"
    conn = init_db(db_path)
    with conn:
        now = datetime.now(timezone.utc).isoformat()
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            conn.execute(
                "INSERT INTO user(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                (username, generate_password_hash("kata-sandi-aman"), role, now),
            )
        conn.execute(
            """INSERT INTO import_batch(source_filename,source_sha256,parser_version,
               extractor_version,imported_at) VALUES ('old.sql','old','v1','v1',?)""", (now,),
        )
        conn.execute(
            """INSERT INTO archive(id,batch_id,opd_id_source,year,summary_raw,
               summary_clean,status,has_document)
               VALUES (1,1,1,2019,'Arsip lama','Arsip lama',1,0)"""
        )
    conn.close()
    return create_app({
        "TESTING": True, "SECRET_KEY": "test-only", "DATABASE": db_path,
        "SERVE_REACT": False, "IMPORT_SOURCE_DIR": source_dir,
        "IMPORT_BACKUP_DIR": tmp_path / "backups",
        "IMPORT_VERIFY_REFERENCE_COUNTS": False,
    })


def login(client, username="admin"):
    token = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session", json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    return response.get_json()["data"]["csrf_token"]


def test_admin_preview_import_backup_history_and_audit(import_app):
    client = import_app.test_client()
    assert client.get("/api/v1/imports").status_code == 401
    csrf = login(client)
    overview = client.get("/api/v1/imports").get_json()["data"]
    assert overview["configured"] is True
    assert [row["name"] for row in overview["sources"]] == ["broken.sql", "sample.sql"]
    assert overview["history"][0]["source_filename"] == "old.sql"
    preview = client.get("/api/v1/imports/preview?source=sample.sql").get_json()["data"]
    assert preview["counts"] == {"archives": 1, "opds": 1, "classifications": 1}
    payload = {"source": "sample.sql", "source_sha256": preview["source_sha256"]}
    assert client.post("/api/v1/imports", json=payload).status_code == 403
    result = client.post("/api/v1/imports", json=payload,
                         headers={"X-CSRF-Token": csrf})
    assert result.status_code == 201, result.get_data(as_text=True)
    data = result.get_json()["data"]
    assert data["raw_count"] == 1 and data["clean_count"] == 1
    backup_file = import_app.config["IMPORT_BACKUP_DIR"] / data["backup_filename"]
    assert backup_file.is_file()
    with sqlite3.connect(backup_file) as backup:
        assert backup.execute("SELECT id FROM archive").fetchall() == [(1,)]
        assert backup.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 2
    with get_connection(import_app.config["DATABASE"]) as conn:
        assert [row[0] for row in conn.execute("SELECT id FROM archive")] == [2]
        assert conn.execute("SELECT COUNT(*) FROM user").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM user WHERE username='penyusup'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0] == 2
        log = conn.execute("SELECT detail FROM activity_log WHERE action='import_completed'").fetchone()
        assert json.loads(log[0])["batch_id"] == data["batch_id"]
    assert client.get("/api/v1/imports").get_json()["data"]["history"][0]["id"] == data["batch_id"]


def test_invalid_source_corrupt_dump_and_changed_hash_preserve_archive(import_app):
    client = import_app.test_client()
    csrf = login(client)
    for source in ("../sample.sql", "..\\sample.sql", "C:\\sample.sql", "broken.sql"):
        assert client.get("/api/v1/imports/preview", query_string={"source": source}).status_code == 422
    response = client.post("/api/v1/imports", json={
        "source": "sample.sql", "source_sha256": "0" * 64,
    }, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422
    with get_connection(import_app.config["DATABASE"]) as conn:
        assert conn.execute("SELECT id FROM archive").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0] == 1
    assert not import_app.config["IMPORT_BACKUP_DIR"].exists()


def test_strict_reference_mismatch_rolls_back_after_backup(import_app):
    import_app.config["IMPORT_VERIFY_REFERENCE_COUNTS"] = True
    client = import_app.test_client()
    csrf = login(client)
    preview = client.get("/api/v1/imports/preview?source=sample.sql").get_json()["data"]
    assert preview["reference_total_matches"] is False
    response = client.post("/api/v1/imports", json={
        "source": "sample.sql", "source_sha256": preview["source_sha256"],
    }, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422
    with get_connection(import_app.config["DATABASE"]) as conn:
        assert conn.execute("SELECT id FROM archive").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM activity_log WHERE action='import_failed'").fetchone()[0] == 1
    assert len(list(import_app.config["IMPORT_BACKUP_DIR"].glob("*.sqlite"))) == 1


def test_duplicate_archive_during_import_rolls_back(import_app):
    source_dir = import_app.config["IMPORT_SOURCE_DIR"]
    source_dir.joinpath("duplicate.sql").write_text(SQL + SQL, encoding="utf-8")
    client = import_app.test_client()
    csrf = login(client)
    preview = client.get("/api/v1/imports/preview?source=duplicate.sql").get_json()["data"]
    response = client.post("/api/v1/imports", json={
        "source": "duplicate.sql", "source_sha256": preview["source_sha256"],
    }, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 500
    assert "UNIQUE" not in response.get_data(as_text=True)
    with get_connection(import_app.config["DATABASE"]) as conn:
        assert conn.execute("SELECT id FROM archive").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM import_batch").fetchone()[0] == 1


def test_petugas_and_unconfigured_source_are_rejected(import_app):
    client = import_app.test_client()
    csrf = login(client, "petugas")
    assert client.get("/api/v1/imports").status_code == 403
    assert client.get("/api/v1/imports/preview?source=sample.sql").status_code == 403
    assert client.post("/api/v1/imports", json={}, headers={"X-CSRF-Token": csrf}).status_code == 403
    import_app.config["IMPORT_SOURCE_DIR"] = None
    admin = import_app.test_client()
    login(admin)
    assert admin.get("/api/v1/imports").get_json()["data"]["configured"] is False
    assert admin.get("/api/v1/imports/preview?source=sample.sql").status_code == 409
