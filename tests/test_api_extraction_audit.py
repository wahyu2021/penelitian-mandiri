"""Audit ekstraksi web mengikuti sampel/manifest dan metrik skrip."""

import csv
import io
import json
from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from core.evaluation.audit_metrics import VALID_VERDICTS
from scripts.evaluate_extraction_audit import evaluate_audit_data
from services.db import get_connection, init_db
from webapp import create_app

FIELDS = ("spm", "sp2d", "date", "amount", "party")
VALUES = {
    101: ("benar", "tidak_ada_di_teks", "benar", "salah", "terlewat"),
    102: ("terlewat", "benar", "benar", "benar", "tidak_ada_di_teks"),
}


@pytest.fixture
def audit_app(tmp_path):
    sample = tmp_path / "audit_extraction_sample.csv"
    manifest = tmp_path / "audit_strata_summary.json"
    rows = [
        {"sample_id": "1", "archive_id": "101", "archive_status": "Aktif",
         "summary_raw": "SPM 123/LS untuk CV Uji", "extracted_spm": "123/LS",
         "extracted_sp2d": "", "extracted_date": "2020-01-01",
         "extracted_amount": "5000", "extracted_party": "CV Uji"},
        {"sample_id": "2", "archive_id": "102", "archive_status": "Aktif",
         "summary_raw": "SP2D 44 untuk PT Contoh", "extracted_spm": "",
         "extracted_sp2d": "44", "extracted_date": "2020-01-02",
         "extracted_amount": "10000", "extracted_party": ""},
    ]
    columns = [
        "sample_id", "archive_id", "archive_status", "summary_raw",
        "extracted_spm", "verdict_spm", "extracted_sp2d", "verdict_sp2d",
        "extracted_date", "verdict_date", "extracted_amount", "verdict_amount",
        "extracted_party", "verdict_party", "auditor_notes",
    ]
    with sample.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "verdict_spm": "benar"})  # CSV lama tidak diimpor jadi putusan web.
    manifest.write_text(json.dumps({
        "extractor_version": "v1.0.0",
        "reference_records": {row["archive_id"]: row for row in rows},
    }), encoding="utf-8")
    database = tmp_path / "audit.sqlite"
    conn = init_db(database)
    with conn:
        now = datetime.now(timezone.utc).isoformat()
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            conn.execute(
                "INSERT INTO user(username,password_hash,role,created_at) VALUES (?,?,?,?)",
                (username, generate_password_hash("kata-sandi-aman"), role, now),
            )
    conn.close()
    return create_app({
        "TESTING": True, "SECRET_KEY": "test-only", "DATABASE": database,
        "SERVE_REACT": False, "AUDIT_SAMPLE_CSV": sample, "AUDIT_MANIFEST": manifest,
    })


def login(client, username="admin"):
    token = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post("/api/v1/session", json={
        "username": username, "password": "kata-sandi-aman",
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    return response.get_json()["data"]["csrf_token"]


def save(client, csrf, archive_id, field, verdict, fingerprint, note=""):
    return client.patch(
        f"/api/v1/extraction-audit/{archive_id}/fields/{field}",
        json={"verdict": verdict, "note": note, "fingerprint": fingerprint},
        headers={"X-CSRF-Token": csrf},
    )


def test_partial_save_reload_correction_and_empty_not_counted(audit_app):
    client = audit_app.test_client()
    assert client.get("/api/v1/extraction-audit").status_code == 401
    csrf = login(client)
    state = client.get("/api/v1/extraction-audit").get_json()["data"]
    assert state["total_cells"] == 10 and state["completed_cells"] == 0
    assert state["results"]["spm"]["metrics"] is None
    assert state["judgments"]["spm"]["verdict"] is None  # CSV sumber terisi, web tetap kosong.
    assert client.get("/api/v1/extraction-audit/export").status_code == 409
    fingerprint = state["fingerprint"]
    assert save(client, csrf, 101, "spm", "benar", fingerprint).status_code == 200
    assert save(client, csrf, 101, "sp2d", None, fingerprint).status_code == 200
    refreshed = client.get("/api/v1/extraction-audit").get_json()["data"]
    assert refreshed["completed_cells"] == 1
    assert refreshed["results"]["spm"]["metrics"]["n_benar"] == 1
    assert refreshed["results"]["sp2d"]["metrics"] is None
    assert refreshed["final"] is False
    assert save(client, csrf, 101, "spm", "salah", fingerprint, "Koreksi pembacaan").status_code == 200
    assert save(client, csrf, 101, "spm", None, fingerprint).status_code == 200
    assert client.get("/api/v1/extraction-audit").get_json()["data"]["completed_cells"] == 0
    with get_connection(audit_app.config["DATABASE"]) as conn:
        history = conn.execute("SELECT old_verdict,new_verdict FROM extraction_audit_change ORDER BY id").fetchall()
        assert [(row[0], row[1]) for row in history] == [
            (None, "benar"), ("benar", "salah"), ("salah", None),
        ]


def test_complete_export_matches_existing_audit_script(audit_app):
    client = audit_app.test_client()
    csrf = login(client)
    fingerprint = client.get("/api/v1/extraction-audit").get_json()["data"]["fingerprint"]
    for archive_id, verdicts in VALUES.items():
        for field, verdict in zip(FIELDS, verdicts):
            assert verdict in VALID_VERDICTS
            assert save(client, csrf, archive_id, field, verdict, fingerprint).status_code == 200
    state = client.get("/api/v1/extraction-audit?index=1").get_json()["data"]
    assert state["completed_cells"] == 10 and state["completed_samples"] == 2
    assert state["final"] is True
    assert state["results"]["spm"]["metrics"]["ketepatan"] == 1.0
    assert state["results"]["spm"]["metrics"]["keterambilan"] == 0.5
    exported = client.get("/api/v1/extraction-audit/export")
    assert exported.status_code == 200 and exported.mimetype == "text/csv"
    rows = list(csv.DictReader(io.StringIO(exported.get_data(as_text=True))))
    report = evaluate_audit_data(rows, manifest_path=audit_app.config["AUDIT_MANIFEST"])
    for field in FIELDS:
        assert state["results"][field]["metrics"] == {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in report["fields"][field].items()
        }
    assert rows[0]["verdict_spm"] == "benar"


def test_assignment_role_and_sample_integrity(audit_app):
    petugas = audit_app.test_client()
    csrf_petugas = login(petugas, "petugas")
    assert petugas.get("/api/v1/extraction-audit").status_code == 403
    assert petugas.put("/api/v1/extraction-audit/reviewers/2",
                       headers={"X-CSRF-Token": csrf_petugas}).status_code == 403
    admin = audit_app.test_client()
    csrf_admin = login(admin)
    assert admin.put("/api/v1/extraction-audit/reviewers/2").status_code == 403
    assert admin.put("/api/v1/extraction-audit/reviewers/2",
                     headers={"X-CSRF-Token": csrf_admin}).status_code == 200
    assert petugas.get("/api/v1/extraction-audit").status_code == 200
    state = petugas.get("/api/v1/extraction-audit").get_json()["data"]
    assert save(petugas, csrf_petugas, 101, "spm", "benar", state["fingerprint"]).status_code == 200
    assert admin.get("/api/v1/extraction-audit").get_json()["data"]["completed_cells"] == 0
    assert admin.delete("/api/v1/extraction-audit/reviewers/2",
                        headers={"X-CSRF-Token": csrf_admin}).status_code == 200
    assert petugas.get("/api/v1/extraction-audit").status_code == 403
    audit_app.config["AUDIT_SAMPLE_CSV"].write_text("broken", encoding="utf-8")
    assert admin.get("/api/v1/extraction-audit").status_code == 409


def test_spm_type_requires_recorded_admin_confirmation(audit_app):
    admin = audit_app.test_client()
    csrf = login(admin)
    before = admin.get("/api/v1/spm-types").get_json()["data"]
    assert next(row for row in before if row["code"] == "BT")["confidence"] == "dugaan"
    path = "/api/v1/spm-types/BT/confirm"
    payload = {"label": "Belanja Tidak Langsung (BT)",
               "source_note": "Dokumen tertulis konfirmasi dari petugas arsip, 23 November 2026"}
    assert admin.post(path, json=payload).status_code == 403
    assert admin.post(path, json={"label": "BT", "source_note": "singkat"},
                      headers={"X-CSRF-Token": csrf}).status_code == 422
    assert admin.post(path, json=payload, headers={"X-CSRF-Token": csrf}).status_code == 200
    assert admin.post(path, json=payload, headers={"X-CSRF-Token": csrf}).status_code == 409
    with get_connection(audit_app.config["DATABASE"]) as conn:
        row = conn.execute("SELECT confidence,confirmed_by,source_note FROM spm_type WHERE code='BT'").fetchone()
        assert tuple(row) == ("terkonfirmasi", "admin", payload["source_note"])
        assert conn.execute("SELECT COUNT(*) FROM activity_log WHERE action='spm_type_confirmed'").fetchone()[0] == 1
    petugas = audit_app.test_client()
    token = login(petugas, "petugas")
    assert petugas.post("/api/v1/spm-types/BS/confirm", json=payload,
                        headers={"X-CSRF-Token": token}).status_code == 403
