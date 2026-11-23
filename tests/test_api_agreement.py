"""Kontrak API dan layanan ringkasan kesepakatan penilai [PM-19]."""

import csv
import io
import json

import pytest
from werkzeug.security import generate_password_hash

from core.evaluation.audit_metrics import VALID_VERDICTS
from scripts.evaluate_relevance_agreement import evaluate_relevance_agreement
from services.db import init_db
from services.testset_versions import lock_version, save_version
from webapp import create_app

ENDPOINT = "/api/v1/research/agreement"
EXPORT = "/api/v1/research/agreement/export"
ADMIN_RELEVANCE = "/api/v1/relevance-admin"
REVIEW_RELEVANCE = "/api/v1/relevance-reviews"
VERSION = "uji-pm19"


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return {"X-CSRF-Token": res.json["data"]["csrf_token"]}


def _sample_csv(rows):
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
    for query_id, query_text, archive_id, base_text, summary_raw, qtype in rows:
        writer.writerow(
            [query_id, query_text, archive_id, base_text, summary_raw, qtype, "", 0, "", "bm25", "0.8", archive_id, ""]
        )
    return stream.getvalue().encode()


def _create_five_pair_fixture(tmp_path):
    path = tmp_path / "pm19.sqlite"
    conn = init_db(path)
    items = [
        ("Q1", "Jalan desa", 101, "Jalan desa", "Ringkasan jalan", "topik"),
        ("Q2", "Pipa air", 102, "Pipa air", "Ringkasan pipa", "topik"),
        ("Q3", "SPM 001", 103, "SPM 001", "Ringkasan spm", "sp2d"),
        ("Q4", "Dinas PUPR", 104, "Dinas PUPR", "Ringkasan pupr", "sp2d"),
        ("Q5", "Dana BTT", 105, "Dana BTT", "Ringkasan btt", "sp2d"),
    ]
    with conn:
        pw = generate_password_hash("kata-sandi-aman")
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [("peneliti", pw, "admin"), ("penilai", pw, "petugas"), ("cadangan", pw, "petugas")],
        )
        conn.execute(
            """INSERT INTO import_batch(source_filename, source_sha256, parser_version, extractor_version, imported_at)
               VALUES ('fixture', 'dummy', '1', '1', '2026-01-01')"""
        )
        conn.executemany(
            """INSERT INTO archive(id, batch_id, opd_id_source, summary_raw, summary_clean, status, has_document)
               VALUES (?, 1, 0, ?, 'bersih', 1, 0)""",
            [(archive_id, summary_raw) for _, _, archive_id, _, summary_raw, _ in items],
        )
    queries = [
        {
            "query_id": qid,
            "base_query_id": f"B{aid}",
            "query_text": qtext,
            "query_type": qtype,
            "source": "sintetis",
            "noise_type": "tanpa_gangguan",
            "split": "tuning" if aid < 103 else "test",
            "origin_archive_id": aid,
            "judgments": [{"archive_id": aid, "is_relevant": 1}],
        }
        for qid, qtext, aid, _, _, qtype in items
    ]
    saved = save_version(conn, {"version": VERSION, "queries": queries}, 1)
    lock_version(conn, VERSION, saved["content_sha256"], 1)
    conn.close()
    app = create_app({"TESTING": True, "DATABASE": path, "SECRET_KEY": "test", "SERVE_REACT": False})
    return app, items, path


def _answer_all_and_submit(client, headers, decisions_by_query_base):
    for idx in range(5):
        state = client.get(f"{REVIEW_RELEVANCE}/{VERSION}?index={idx}").json["data"]
        item = state["item"]
        decision = decisions_by_query_base[item["base_query_text"]]
        res = client.put(
            f"{REVIEW_RELEVANCE}/{VERSION}/{item['id']}",
            headers=headers,
            json={"is_relevant": decision, "notes": "", "ragu": False, "revision": item["revision"]},
        )
        assert res.status_code == 200
    sub = client.post(f"{REVIEW_RELEVANCE}/{VERSION}/submit", headers=headers)
    assert sub.status_code == 200


def test_agreement_requires_admin_and_reports_empty_state(tmp_path):
    app, _, _ = _create_five_pair_fixture(tmp_path)
    anon = app.test_client()
    assert anon.get(ENDPOINT).status_code == 401
    assert anon.get(EXPORT).status_code == 401

    staff = app.test_client()
    _login(staff, "penilai")
    assert staff.get(ENDPOINT).status_code == 403
    assert staff.get(EXPORT).status_code == 403

    admin = app.test_client()
    _login(admin, "peneliti")
    res = admin.get(ENDPOINT)
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "no-store"
    data = res.json["data"]
    assert data["relevance"] == []
    assert data["audit"]["status"] == "pending"


def test_relevance_agreement_stays_pending_until_both_submit_and_matches_cli(tmp_path):
    app, items, _ = _create_five_pair_fixture(tmp_path)
    admin = app.test_client()
    staff = app.test_client()
    h_admin = _login(admin, "peneliti")
    h_staff = _login(staff, "penilai")

    created = admin.post(f"{ADMIN_RELEVANCE}/{VERSION}?first=1&second=2", headers=h_admin, data=_sample_csv(items))
    assert created.status_code == 201

    # Isi hanya 2 item oleh masing-masing -> status harus tetap pending
    for client_pair, headers in ((admin, h_admin), (staff, h_staff)):
        for idx in range(2):
            state = client_pair.get(f"{REVIEW_RELEVANCE}/{VERSION}?index={idx}").json["data"]["item"]
            client_pair.put(
                f"{REVIEW_RELEVANCE}/{VERSION}/{state['id']}",
                headers=headers,
                json={"is_relevant": 1, "notes": "", "ragu": False, "revision": state["revision"]},
            )
    partial = admin.get(ENDPOINT).json["data"]["relevance"][0]
    assert partial["status"] == "pending"
    assert partial["n_total"] == 5
    assert partial["n_paired"] == 2
    assert partial["cohen_kappa"] is None

    # Isi semua 5 item tapi BELUM diserahkan -> tetap pending
    r1_decisions = {"Jalan desa": 1, "Pipa air": 1, "SPM 001": 1, "Dinas PUPR": 0, "Dana BTT": 0}
    r2_decisions = {"Jalan desa": 1, "Pipa air": 1, "SPM 001": 0, "Dinas PUPR": 0, "Dana BTT": 0}
    for client_pair, headers, dec in ((admin, h_admin, r1_decisions), (staff, h_staff, r2_decisions)):
        for idx in range(5):
            state = client_pair.get(f"{REVIEW_RELEVANCE}/{VERSION}?index={idx}").json["data"]["item"]
            client_pair.put(
                f"{REVIEW_RELEVANCE}/{VERSION}/{state['id']}",
                headers=headers,
                json={
                    "is_relevant": dec[state["base_query_text"]],
                    "notes": "",
                    "ragu": False,
                    "revision": state["revision"],
                },
            )
    unsubmitted = admin.get(ENDPOINT).json["data"]["relevance"][0]
    assert unsubmitted["status"] == "pending"
    assert unsubmitted["n_paired"] == 5
    assert unsubmitted["cohen_kappa"] is None

    # Kedua akun submit -> harus lengkap dan identik dengan skrip CLI
    assert admin.post(f"{REVIEW_RELEVANCE}/{VERSION}/submit", headers=h_admin).status_code == 200
    assert staff.post(f"{REVIEW_RELEVANCE}/{VERSION}/submit", headers=h_staff).status_code == 200

    summary = admin.get(ENDPOINT).json["data"]["relevance"][0]
    assert summary["status"] == "complete"
    assert summary["n_total"] == 5
    assert summary["n_paired"] == 5
    assert summary["n_agreed"] == 4
    assert summary["percentage_agreement"] == pytest.approx(0.8)
    assert summary["relevant_class_agreement"] == pytest.approx(0.8)
    assert summary["cohen_kappa"] == pytest.approx(8 / 13)

    # Ekspor CSV dari endpoint relevance-admin dan bandingkan dengan CLI evaluate_relevance_agreement
    csv1 = tmp_path / "slot1.csv"
    csv2 = tmp_path / "slot2.csv"
    csv1.write_bytes(admin.get(f"{ADMIN_RELEVANCE}/{VERSION}/1/export").data)
    csv2.write_bytes(admin.get(f"{ADMIN_RELEVANCE}/{VERSION}/2/export").data)
    cli_report = evaluate_relevance_agreement(csv1, csv2)

    assert summary["percentage_agreement"] == pytest.approx(cli_report["percentage_agreement"])
    assert summary["relevant_class_agreement"] == pytest.approx(cli_report["relevant_class_agreement"])
    assert summary["cohen_kappa"] == pytest.approx(cli_report["cohen_kappa"])

    # Uji ekspor JSON PM-19
    exported = admin.get(EXPORT)
    assert exported.status_code == 200
    assert 'attachment; filename="ringkasan-kesepakatan.json"' in exported.headers["Content-Disposition"]
    exported_json = json.loads(exported.data.decode("utf-8"))
    assert exported_json["relevance"][0]["n_agreed"] == 4
    assert exported_json["relevance"][0]["n_total"] == 5
    assert exported_json["relevance"][0]["limitations"]


def test_relevance_all_agree_reports_undefined_kappa(tmp_path):
    app, items, _ = _create_five_pair_fixture(tmp_path)
    admin = app.test_client()
    staff = app.test_client()
    h_admin = _login(admin, "peneliti")
    h_staff = _login(staff, "penilai")
    admin.post(f"{ADMIN_RELEVANCE}/{VERSION}?first=1&second=2", headers=h_admin, data=_sample_csv(items))
    all_ones = {base: 1 for _, _, _, base, _, _ in items}
    _answer_all_and_submit(admin, h_admin, all_ones)
    _answer_all_and_submit(staff, h_staff, all_ones)

    summary = admin.get(ENDPOINT).json["data"]["relevance"][0]
    assert summary["status"] == "complete_kappa_undefined"
    assert summary["percentage_agreement"] == 1.0
    assert summary["cohen_kappa"] is None


def test_audit_agreement_partial_complete_and_bad_params(tmp_path):
    app, _, path = _create_five_pair_fixture(tmp_path)
    conn = init_db(path)
    fields = ("spm", "sp2d", "date", "amount", "party")
    with conn:
        conn.execute(
            """INSERT INTO extraction_audit_dataset(id, fingerprint, sample_count, source_filename, created_at)
               VALUES (1, 'fp-test', 2, 'audit_sample.csv', '2026-01-01')"""
        )
        conn.executemany(
            "INSERT INTO extraction_audit_assignment(user_id, assigned_by, assigned_at) VALUES (?, 1, '2026-01-01')",
            [(1,), (2,)],
        )
        # Penilai 1 menilai arsip 101 dan 102 semua field sebagai benar
        for aid in (101, 102):
            for field in fields:
                conn.execute(
                    """INSERT INTO extraction_audit_judgment(user_id, archive_id, field_name, verdict, note, updated_at)
                       VALUES (1, ?, ?, 'benar', '', '2026-01-01')""",
                    (aid, field),
                )
        # Penilai 2 baru menilai 1 arsip -> status masih pending
        for field in fields:
            conn.execute(
                """INSERT INTO extraction_audit_judgment(user_id, archive_id, field_name, verdict, note, updated_at)
                   VALUES (2, 101, ?, 'benar', '', '2026-01-01')""",
                (field,),
            )
    conn.close()

    admin = app.test_client()
    _login(admin, "peneliti")
    partial_audit = admin.get(ENDPOINT).json["data"]["audit"]
    assert partial_audit["status"] == "pending"
    assert partial_audit["overall"]["n_total"] == 10
    assert partial_audit["overall"]["n_paired"] == 5

    # Lengkapi arsip 102 untuk penilai 2 dengan variasi verdict agar kappa terdefinisi
    conn = init_db(path)
    with conn:
        for field in fields:
            verdict = "salah" if field == "spm" else "benar"
            assert verdict in VALID_VERDICTS
            conn.execute(
                """INSERT INTO extraction_audit_judgment(user_id, archive_id, field_name, verdict, note, updated_at)
                   VALUES (2, 102, ?, ?, '', '2026-01-01')""",
                (field, verdict),
            )
    conn.close()

    complete_audit = admin.get(f"{ENDPOINT}?audit_rater1=1&audit_rater2=2").json["data"]["audit"]
    assert complete_audit["status"] == "complete"
    assert complete_audit["overall"]["n_paired"] == 10
    assert complete_audit["overall"]["n_agreed"] == 9
    assert complete_audit["overall"]["percentage_agreement"] == pytest.approx(0.9)
    assert complete_audit["overall"]["cohen_kappa"] == pytest.approx(0.0)

    # Parameter tidak valid (sama / non-numeric / hanya 1 penilai)
    assert admin.get(f"{ENDPOINT}?audit_rater1=1&audit_rater2=1").status_code == 400
    assert admin.get(f"{ENDPOINT}?audit_rater1=abc&audit_rater2=2").status_code == 400
    assert admin.get(f"{ENDPOINT}?audit_rater1=1").status_code == 400
