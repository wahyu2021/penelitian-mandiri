"""Kontrak penilaian buta, revisi, dan perpindahan CSV."""

import csv
import io

import pytest
from werkzeug.security import generate_password_hash

from scripts.evaluate_relevance_agreement import evaluate_relevance_agreement
from services.db import get_connection, init_db
from services.testset_versions import lock_version, save_version
from webapp import create_app

ADMIN = "/api/v1/relevance-admin"
REVIEW = "/api/v1/relevance-reviews"
VERSION = "uji-v2"
SAMPLES = [
    ("Q1", "Renovasi jalan", 101, "Renovasi jalan", "Ringkasan jalan asli"),
    ("Q2", "Renovsi jalan", 101, "Renovasi jalan", "Ringkasan jalan asli"),
    ("Q3", "Pipa kota", 102, "Pipa kota", "Ringkasan pipa asli"),
]


def _file(items, *, slot=2, summary_clean=""):
    note_field = "auditor_notes" if slot == 1 else "archivist_notes"
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["query_id", "query_text", "archive_id", "base_query_text", "summary_raw",
                     "query_type", "is_relevant", "ragu", note_field, "method", "score",
                     "origin_archive_id", "summary_clean"])
    for row, decision, doubt, notes in items:
        writer.writerow([*row, "topik", decision, doubt, notes, "metode_rahasia", "0.98", 101, summary_clean])
    return stream.getvalue().encode()


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    login = client.post("/api/v1/session", json={"username": username, "password": "kata-sandi-aman"},
                        headers={"X-CSRF-Token": csrf})
    assert login.status_code == 200
    return {"X-CSRF-Token": login.json["data"]["csrf_token"]}


@pytest.fixture
def app(tmp_path):
    path = tmp_path / "relevance.sqlite"
    conn = init_db(path)
    with conn:
        password = generate_password_hash("kata-sandi-aman")
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [(name, password, role) for name, role in (("peneliti", "admin"), ("penilai", "petugas"), ("lain", "petugas"))],
        )
        conn.execute("""INSERT INTO import_batch(source_filename, source_sha256, parser_version, extractor_version, imported_at)
                        VALUES ('fixture', 'dummy', '1', '1', '2026-01-01')""")
        conn.executemany(
            """INSERT INTO archive(id, batch_id, opd_id_source, summary_raw, summary_clean, status, has_document)
               VALUES (?, 1, 0, ?, 'ringkasan bersih', 1, 0)""",
            [(101, "Ringkasan jalan asli"), (102, "Ringkasan pipa asli")],
        )
    queries = [
        {"query_id": q, "base_query_id": f"B{archive}", "query_text": text,
         "query_type": "topik", "source": "sintetis", "noise_type": "typo" if q == "Q2" else "tanpa_gangguan",
         "split": "tuning" if archive == 101 else "test", "origin_archive_id": archive,
         "judgments": [{"archive_id": archive, "is_relevant": 1}]}
        for q, text, archive, _, _ in SAMPLES
    ]
    data = save_version(conn, {"version": VERSION, "queries": queries}, 1)
    lock_version(conn, VERSION, data["content_sha256"], 1)
    conn.close()
    return create_app({"TESTING": True, "DATABASE": path, "SECRET_KEY": "test", "SERVE_REACT": False})


def _create(admin, headers, sample=None):
    return admin.post(f"{ADMIN}/{VERSION}?first=1&second=2", headers=headers,
                      data=sample or _file([(row, 1, "", "jawaban lama") for row in SAMPLES]))


def _answer(client, headers, item, decision, note="", doubt=False):
    return client.put(f"{REVIEW}/{VERSION}/{item['id']}", headers=headers,
                      json={"is_relevant": decision, "notes": note, "ragu": doubt,
                            "revision": item["revision"]})


def test_two_sessions_blind_partial_correction_and_export(app, tmp_path):
    admin, second, unrelated = (app.test_client() for _ in range(3))
    first_token = _login(admin, "peneliti")
    second_token = _login(second, "penilai")
    _login(unrelated, "lain")
    assert _create(admin, {}).status_code == 403
    new = _create(admin, first_token)
    assert new.status_code == 201
    assert new.json["data"] == {"version": VERSION, "pairs": 2, "sample_rows": 3}
    assert _create(admin, first_token).status_code == 409
    assert unrelated.get(REVIEW).json["data"] == []
    assert unrelated.get(f"{REVIEW}/{VERSION}").status_code == 403
    assert second.get(ADMIN).status_code == 403
    assert second.get(f"{ADMIN}/{VERSION}/1/export").status_code == 403
    assert admin.get(f"{ADMIN}/{VERSION}/1/export").status_code == 409

    route = f"{REVIEW}/{VERSION}"
    item = admin.get(route).json["data"]["item"]
    assert set(item) == {"id", "base_query_text", "query_type", "summary_raw", "is_relevant", "ragu", "notes", "revision"}
    assert item["is_relevant"] is None and item["notes"] == ""
    assert _answer(admin, first_token, item, None, "rahasia peneliti", True).json["data"]["rated"] == 0
    assert admin.post(f"{route}/submit", headers=first_token).status_code == 409
    assert _answer(admin, first_token, item, 1).status_code == 409
    own = admin.get(route).json["data"]["item"]
    assert own["ragu"] and own["notes"] == "rahasia peneliti"
    response = second.get(route)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["data"]["item"] == item
    assert "rahasia peneliti" not in response.get_data(as_text=True)
    assert _answer(admin, first_token, own, 1, "dikoreksi").status_code == 200
    assert _answer(second, second_token, item, 0).status_code == 200

    for client, token, value in ((admin, first_token, 1), (second, second_token, 0)):
        last = client.get(f"{route}?index=1").json["data"]["item"]
        assert _answer(client, token, last, value).status_code == 200
        assert client.post(f"{route}/submit", headers=token).status_code == 200
        assert _answer(client, token, last, 1 - value).status_code == 409

    exported = []
    for slot in (1, 2):
        response = admin.get(f"{ADMIN}/{VERSION}/{slot}/export")
        assert response.status_code == 200
        assert "attachment" in response.headers["Content-Disposition"]
        path = tmp_path / f"slot-{slot}.csv"
        path.write_bytes(response.data)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert [row["query_id"] for row in rows] == ["Q1", "Q2", "Q3"]
        assert {row["is_relevant"] for row in rows} == {str(2 - slot)}
        exported.append(path)
    assert evaluate_relevance_agreement(*exported)["n_verification_samples"] == 3
    conn = get_connection(app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM relevance_judgment_change WHERE slot = 1").fetchone()[0] == 3
    conn.close()


def test_legacy_migration_keeps_existing_and_checks_snapshot(app):
    admin = app.test_client()
    token = _login(admin, "peneliti")
    wrong = ("Q1", "Renovasi jalan", 101, "Renovasi jalan", "Ringkasan berbeda")
    assert _create(admin, token, _file([(wrong, "", "", "")])).status_code == 422
    assert _create(admin, token).status_code == 201
    target = admin.get(f"{REVIEW}/{VERSION}").json["data"]["item"]
    assert _answer(admin, token, target, None, "parsial").status_code == 200
    url = f"{ADMIN}/{VERSION}/1/migration"
    mismatch = _file([(SAMPLES[0], 0, "", ""), (SAMPLES[1], 1, "", "")], slot=1)
    assert admin.post(url, headers=token, data=mismatch).status_code == 422
    wrong_archive = _file([(SAMPLES[0], 1, "", "")], slot=1, summary_clean="arsip berbeda")
    assert admin.post(url, headers=token, data=wrong_archive).status_code == 422
    data = _file([(row, 1, "", "") for row in SAMPLES], slot=1)
    assert admin.post(f"{ADMIN}/{VERSION}/2/migration", headers=token, data=data).status_code == 422
    migrated = admin.post(url, headers=token, data=data)
    assert migrated.json["data"] == {"inserted": 1, "matched_rows": 3, "outside_rows": 0, "preserved": 1}
    assert admin.post(url, headers=token, data=data).json["data"]["inserted"] == 0
    own = admin.get(f"{REVIEW}/{VERSION}").json["data"]
    assert own["rated"] == 1 and own["item"]["notes"] == "parsial"
