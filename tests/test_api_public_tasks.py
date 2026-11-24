"""Kontrak API tautan 1-perangkat untuk penilaian relevansi & audit ekstraksi [PM-29]."""

import csv
import io
import json
from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.db import init_db
from services.testset_versions import lock_version, save_version
from webapp import create_app

TASK_LINKS_ADMIN = "/api/v1/research/task-links"
RELEVANCE_ADMIN = "/api/v1/relevance-admin"
PUBLIC_TASKS = "/api/v1/public/tasks"
VERSION = "uji-pm29"

SAMPLES = [
    ("Q1", "Renovasi jalan", 101, "Renovasi jalan", "Ringkasan jalan asli"),
    ("Q2", "Renovsi jalan", 101, "Renovasi jalan", "Ringkasan jalan asli"),
    ("Q3", "Pipa kota", 102, "Pipa kota", "Ringkasan pipa asli"),
]

FIELDS = ("spm", "sp2d", "date", "amount", "party")


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return {"X-CSRF-Token": res.json["data"]["csrf_token"]}


def _sample_csv():
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        [
            "query_id",
            "query_text",
            "archive_id",
            "base_query_text",
            "summary_raw",
            "query_type",
            "is_relevant",
            "ragu",
            "archivist_notes",
            "method",
            "score",
            "origin_archive_id",
            "summary_clean",
        ]
    )
    for q_id, q_text, archive_id, base_text, summary_raw in SAMPLES:
        writer.writerow(
            [q_id, q_text, archive_id, base_text, summary_raw, "topik", "", "", "", "bm25_rahasia", "0.95", archive_id, ""]
        )
    return stream.getvalue().encode("utf-8")


@pytest.fixture
def task_app(tmp_path):
    sample_csv = tmp_path / "audit_extraction_sample.csv"
    manifest_json = tmp_path / "audit_strata_summary.json"
    audit_rows = [
        {
            "sample_id": "1",
            "archive_id": "101",
            "archive_status": "Aktif",
            "summary_raw": "SPM 123/LS untuk CV Uji",
            "extracted_spm": "123/LS",
            "extracted_sp2d": "",
            "extracted_date": "2020-01-01",
            "extracted_amount": "5000",
            "extracted_party": "CV Uji",
        },
        {
            "sample_id": "2",
            "archive_id": "102",
            "archive_status": "Aktif",
            "summary_raw": "SP2D 44 untuk PT Contoh",
            "extracted_spm": "",
            "extracted_sp2d": "44",
            "extracted_date": "2020-01-02",
            "extracted_amount": "10000",
            "extracted_party": "",
        },
    ]
    audit_columns = [
        "sample_id",
        "archive_id",
        "archive_status",
        "summary_raw",
        "extracted_spm",
        "verdict_spm",
        "extracted_sp2d",
        "verdict_sp2d",
        "extracted_date",
        "verdict_date",
        "extracted_amount",
        "verdict_amount",
        "extracted_party",
        "verdict_party",
        "auditor_notes",
    ]
    with sample_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_columns)
        writer.writeheader()
        for row in audit_rows:
            writer.writerow(row)
    manifest_json.write_text(
        json.dumps(
            {
                "extractor_version": "v1.0.0",
                "reference_records": {row["archive_id"]: row for row in audit_rows},
            }
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "tasks.sqlite"
    conn = init_db(db_path)
    pw = generate_password_hash("kata-sandi-aman")
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            [("peneliti", pw, "admin", now), ("penilai2", pw, "petugas", now)],
        )
        conn.execute(
            """INSERT INTO import_batch(source_filename, source_sha256, parser_version, extractor_version, imported_at)
               VALUES ('fixture', 'dummy', '1', '1', ?)""",
            (now,),
        )
        conn.executemany(
            """INSERT INTO archive(id, batch_id, opd_id_source, summary_raw, summary_clean, status, has_document)
               VALUES (?, 1, 0, ?, 'ringkasan bersih', 1, 0)""",
            [(101, "Ringkasan jalan asli"), (102, "Ringkasan pipa asli")],
        )
    queries = [
        {
            "query_id": q,
            "base_query_id": f"B{archive}",
            "query_text": text,
            "query_type": "topik",
            "source": "sintetis",
            "noise_type": "typo" if q == "Q2" else "tanpa_gangguan",
            "split": "tuning" if archive == 101 else "test",
            "origin_archive_id": archive,
            "judgments": [{"archive_id": archive, "is_relevant": 1}],
        }
        for q, text, archive, _, _ in SAMPLES
    ]
    saved = save_version(conn, {"version": VERSION, "queries": queries}, 1)
    lock_version(conn, VERSION, saved["content_sha256"], 1)
    conn.close()

    flask_app = create_app(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test-pm29",
            "SERVE_REACT": False,
            "AUDIT_SAMPLE_CSV": sample_csv,
            "AUDIT_MANIFEST": manifest_json,
        }
    )
    return flask_app, db_path


def test_task_link_permissions_and_csrf(task_app):
    flask_app, _ = task_app
    anon = flask_app.test_client()
    staff = flask_app.test_client()
    admin = flask_app.test_client()

    assert anon.get(TASK_LINKS_ADMIN).status_code == 401
    staff_headers = _login(staff, "penilai2")
    assert staff.get(TASK_LINKS_ADMIN).status_code == 403
    assert staff.post(TASK_LINKS_ADMIN, headers=staff_headers, json={}).status_code == 403

    _login(admin, "peneliti")
    # Tanpa header CSRF -> 403
    assert admin.post(TASK_LINKS_ADMIN, json={"task_kind": "extraction_audit", "user_id": 2}).status_code == 403


def test_public_relevance_link_lock_blindness_submit_and_pm19_parity(task_app):
    flask_app, db_path = task_app
    admin = flask_app.test_client()
    headers = _login(admin, "peneliti")

    # Setup tugas penilaian relevansi (Penilai 1 = admin id 1, Penilai 2 = petugas id 2)
    created_review = admin.post(
        f"{RELEVANCE_ADMIN}/{VERSION}?first=1&second=2",
        headers=headers,
        data=_sample_csv(),
        content_type="text/csv",
    )
    assert created_review.status_code == 201

    # Terbitkan tautan 1-perangkat untuk slot 2
    created_link = admin.post(
        TASK_LINKS_ADMIN,
        headers=headers,
        json={"task_kind": "relevance", "version": VERSION, "slot": 2, "lock_single_device": True},
    )
    assert created_link.status_code == 201
    token = created_link.json["data"]["token"]
    link_id = created_link.json["data"]["id"]
    assert token.startswith("rv_")

    # Token tersimpan sebagai hash SHA-256
    conn = init_db(db_path)
    row = conn.execute("SELECT token_hash FROM public_task_link WHERE id = ?", (link_id,)).fetchone()
    assert row["token_hash"] != token
    conn.close()

    # Penilai 1 (admin) mengisi via akun login agar kesepakatan PM-19 bisa dihitung nanti
    for idx in range(2):
        r1_state = admin.get(f"/api/v1/relevance-reviews/{VERSION}?index={idx}").json["data"]
        decision1 = 1 if "jalan" in r1_state["item"]["base_query_text"] else 0
        assert (
            admin.put(
                f"/api/v1/relevance-reviews/{VERSION}/{r1_state['item']['id']}",
                headers=headers,
                json={"is_relevant": decision1, "ragu": False, "notes": "rahasia1", "revision": r1_state["item"]["revision"]},
            ).status_code
            == 200
        )
    assert admin.post(f"/api/v1/relevance-reviews/{VERSION}/submit", headers=headers).status_code == 200

    # Perangkat 1 membuka tautan -> klaim cookie HttpOnly & cek kebutaan data
    device1 = flask_app.test_client()
    opened1 = device1.get(f"{PUBLIC_TASKS}/{token}/relevance?index=0")
    assert opened1.status_code == 200
    payload_str = json.dumps(opened1.json)
    assert "archive_id" not in payload_str
    assert "noise_type" not in payload_str
    assert "bm25_rahasia" not in payload_str
    assert "auditor_notes" not in payload_str
    assert "rahasia1" not in payload_str  # Jawaban Penilai 1 tidak bocor

    # Perangkat 2 ditolak 403
    device2 = flask_app.test_client()
    assert device2.get(f"{PUBLIC_TASKS}/{token}/relevance").status_code == 403

    # Admin reset kunci perangkat -> perangkat 2 bisa mengklaim, perangkat 1 tertolak
    assert admin.post(f"{TASK_LINKS_ADMIN}/{link_id}/reset-device", headers=headers).status_code == 200
    assert device2.get(f"{PUBLIC_TASKS}/{token}/relevance?index=0").status_code == 200
    assert device1.get(f"{PUBLIC_TASKS}/{token}/relevance?index=0").status_code == 403

    # Simpan parsial + koreksi di perangkat 2
    state0 = device2.get(f"{PUBLIC_TASKS}/{token}/relevance?index=0").json["data"]["review"]
    pair0 = state0["item"]["id"]
    target0 = 1 if "jalan" in state0["item"]["base_query_text"] else 0
    save1 = device2.put(
        f"{PUBLIC_TASKS}/{token}/relevance/{pair0}",
        json={"is_relevant": 1 - target0, "ragu": True, "notes": "cek awal", "revision": state0["item"]["revision"]},
    )
    assert save1.status_code == 200
    # Koreksi menjadi jawaban final yang sejalan dengan isi ringkasan
    save2 = device2.put(
        f"{PUBLIC_TASKS}/{token}/relevance/{pair0}",
        json={"is_relevant": target0, "ragu": False, "notes": "revisi final", "revision": save1.json["data"]["revision"]},
    )
    assert save2.status_code == 200

    # Submit sebelum semua dinilai -> 409
    assert device2.post(f"{PUBLIC_TASKS}/{token}/relevance/submit").status_code == 409

    # Nilai pasangan kedua
    state1 = device2.get(f"{PUBLIC_TASKS}/{token}/relevance?index=1").json["data"]["review"]
    pair1 = state1["item"]["id"]
    target1 = 1 if "jalan" in state1["item"]["base_query_text"] else 0
    assert (
        device2.put(
            f"{PUBLIC_TASKS}/{token}/relevance/{pair1}",
            json={"is_relevant": target1, "ragu": False, "notes": "cocok", "revision": state1["item"]["revision"]},
        ).status_code
        == 200
    )

    # Submit final -> sukses dan tautan terkunci (ubah ulang ditolak 409)
    submitted = device2.post(f"{PUBLIC_TASKS}/{token}/relevance/submit")
    assert submitted.status_code == 200
    assert submitted.json["data"]["submitted_at"] is not None
    assert (
        device2.put(
            f"{PUBLIC_TASKS}/{token}/relevance/{pair1}",
            json={"is_relevant": 0, "ragu": False, "notes": "ubah", "revision": 1},
        ).status_code
        == 409
    )

    # Riwayat perubahan tersimpan atas nama user_id=2 (penilai2)
    conn = init_db(db_path)
    changes = conn.execute(
        "SELECT COUNT(*) FROM relevance_judgment_change WHERE actor_id = 2 AND slot = 2"
    ).fetchone()[0]
    assert changes == 3
    conn.close()

    # Paritas ekspor CSV & perhitungan kesepakatan PM-19
    csv_export = admin.get(f"{RELEVANCE_ADMIN}/{VERSION}/2/export")
    assert csv_export.status_code == 200
    csv_text = csv_export.data.decode("utf-8")
    assert "revisi final" in csv_text

    agreement = admin.get(f"/api/v1/research/agreement?version={VERSION}")
    assert agreement.status_code == 200
    rel_summary = agreement.json["data"]["relevance"][0]
    assert rel_summary["status"] == "complete"
    assert rel_summary["cohen_kappa"] == pytest.approx(1.0)
    assert rel_summary["percentage_agreement"] == pytest.approx(1.0)

    # Cabut tautan -> 410 Gone
    assert admin.post(f"{TASK_LINKS_ADMIN}/{link_id}/revoke", headers=headers).status_code == 200
    assert device2.get(f"{PUBLIC_TASKS}/{token}/relevance").status_code == 410


def test_public_audit_link_lock_partial_submit_and_export_parity(task_app):
    flask_app, db_path = task_app
    admin = flask_app.test_client()
    headers = _login(admin, "peneliti")

    # Terbitkan tautan audit ekstraksi untuk petugas (id=2)
    created = admin.post(
        TASK_LINKS_ADMIN,
        headers=headers,
        json={"task_kind": "extraction_audit", "user_id": 2, "lock_single_device": True},
    )
    assert created.status_code == 201
    token = created.json["data"]["token"]
    link_id = created.json["data"]["id"]
    assert token.startswith("au_")

    # Perangkat 1 klaim, perangkat 2 ditolak 403
    device1 = flask_app.test_client()
    device2 = flask_app.test_client()
    first_get = device1.get(f"{PUBLIC_TASKS}/{token}/audit?index=0")
    assert first_get.status_code == 200
    fingerprint = first_get.json["data"]["audit"]["fingerprint"]
    assert device2.get(f"{PUBLIC_TASKS}/{token}/audit?index=0").status_code == 403

    # Isi parsial 1 field dulu & koreksi
    patch1 = device1.patch(
        f"{PUBLIC_TASKS}/{token}/audit/101/fields/spm",
        json={"verdict": "salah", "note": "ragu awal", "fingerprint": fingerprint},
    )
    assert patch1.status_code == 200
    patch2 = device1.patch(
        f"{PUBLIC_TASKS}/{token}/audit/101/fields/spm",
        json={"verdict": "benar", "note": "sesuai ringkasan", "fingerprint": fingerprint},
    )
    assert patch2.status_code == 200

    # Submit sebelum seluruh 10 sel terisi -> 409
    assert device1.post(f"{PUBLIC_TASKS}/{token}/audit/submit").status_code == 409

    # Lengkapi sisa sel untuk arsip 101 dan 102
    values = {
        101: ("benar", "tidak_ada_di_teks", "benar", "salah", "terlewat"),
        102: ("terlewat", "benar", "benar", "benar", "tidak_ada_di_teks"),
    }
    for archive_id, verdicts in values.items():
        for field, verdict in zip(FIELDS, verdicts):
            res = device1.patch(
                f"{PUBLIC_TASKS}/{token}/audit/{archive_id}/fields/{field}",
                json={"verdict": verdict, "note": "", "fingerprint": fingerprint},
            )
            assert res.status_code == 200

    # Submit final sukses dan mengunci tautan
    submit_res = device1.post(f"{PUBLIC_TASKS}/{token}/audit/submit")
    assert submit_res.status_code == 200
    assert submit_res.json["data"]["submitted_at"] is not None
    assert (
        device1.patch(
            f"{PUBLIC_TASKS}/{token}/audit/101/fields/spm",
            json={"verdict": "salah", "note": "", "fingerprint": fingerprint},
        ).status_code
        == 409
    )

    # Riwayat perubahan tersimpan atas nama user_id=2
    conn = init_db(db_path)
    audit_changes = conn.execute(
        "SELECT COUNT(*) FROM extraction_audit_change WHERE user_id = 2"
    ).fetchone()[0]
    assert audit_changes >= 10
    conn.close()

    # Paritas ekspor CSV oleh admin untuk user_id=2
    export_res = admin.get("/api/v1/extraction-audit/reviewers/2/export")
    assert export_res.status_code == 200
    assert "123/LS" in export_res.data.decode("utf-8")

    # Reset device dan cabut link berfungsi
    assert admin.post(f"{TASK_LINKS_ADMIN}/{link_id}/reset-device", headers=headers).status_code == 200
    assert admin.post(f"{TASK_LINKS_ADMIN}/{link_id}/revoke", headers=headers).status_code == 200
    assert device1.get(f"{PUBLIC_TASKS}/{token}/audit").status_code == 410
