"""Kontrak API dan layanan halaman hasil evaluasi & bukti run [PM-20]."""

import csv
import hashlib
import json

import pytest
from werkzeug.security import generate_password_hash

from services.db import init_db
from webapp import create_app

ENDPOINT = "/api/v1/research/evaluation"
EXPORT = "/api/v1/research/evaluation/export"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200


def _make_app(tmp_path, bundle_dir):
    db_path = tmp_path / "eval.sqlite"
    conn = init_db(db_path)
    pw = generate_password_hash("kata-sandi-aman")
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [("peneliti", pw, "admin"), ("petugas1", pw, "petugas")],
        )
    conn.close()
    return create_app(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "SECRET_KEY": "test",
            "SERVE_REACT": False,
            "EVALUATION_BUNDLE_DIR": bundle_dir,
        }
    )


def _write_bundle(bundle_dir, *, mode="final", tree_clean=True, agreement_status="complete", leak=False, forbidden_col=False):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    run_meta = {
        "commit_sha": "abc1234",
        "tree_clean": tree_clean,
        "mode": mode,
        "seed": 42,
        "data_hash": "d" * 64,
        "testset_hash": "t" * 64,
        "extractor_version": "v1.0.0",
        "exported_at": "2026-11-23T14:00:00Z",
        "n_queries": 3,
        "n_tuning_queries": 1,
        "n_test_queries": 2,
        "n_base_queries": 3 if not leak else 2,
        "n_tuning_base_queries": 1,
        "n_test_base_queries": 2,
        "query_to_base_id": {"Q1": "B1", "Q2": "B2", "Q3": "B1" if leak else "B3"},
    }
    meta_path = bundle_dir / "run_meta.json"
    meta_path.write_text(json.dumps(run_meta), encoding="utf-8")

    headers = [
        "query_id", "method", "config", "split", "source", "query_type", "noise_type",
        "n_relevant", "p5", "r10", "rr10", "hit5", "hit10", "zero_result", "latency_ms", "unjudged_in_top10",
    ]
    if forbidden_col:
        headers.append("summary_raw")
    pq_path = bundle_dir / "per_query_results.csv"
    with pq_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        rows = [
            ["Q1", "levenshtein", "tuned", "test", "sintetis", "topik", "tanpa_gangguan", 2, 0.4, 1.0, 1.0, 1, 1, 0, 12.0, 0],
            ["Q2", "levenshtein", "tuned", "test", "arsiparis", "sp2d", "typo", 2, 0.2, 0.5, 0.5, 0, 1, 0, 18.0, 1],
            ["Q3", "levenshtein", "tuned", "tuning", "sintetis", "topik", "tanpa_gangguan", 2, 0.6, 1.0, 1.0, 1, 1, 0, 10.0, 0],
        ]
        for r in rows:
            writer.writerow([*r, "rahasia"] if forbidden_col else r)

    tuning_path = bundle_dir / "tuning_results.csv"
    with tuning_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["matcher", "summary_weight", "spm_weight", "party_weight", "mrr_at_10", "precision_at_5", "unjudged_top10"])
        writer.writerow(["levenshtein", 0.6, 0.2, 0.2, 0.85, 0.4, 5])

    agr_path = bundle_dir / "agreement_summary.json"
    agr_path.write_text(json.dumps({"status": agreement_status, "n_samples": 120}), encoding="utf-8")

    manifest_lines = [
        f"{_sha256(bundle_dir / name)}  {name}"
        for name in ("run_meta.json", "per_query_results.csv", "tuning_results.csv", "agreement_summary.json")
    ]
    (bundle_dir / "manifest.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")


def test_evaluation_permissions_and_empty_state(tmp_path):
    app = _make_app(tmp_path, tmp_path / "missing_bundle")
    anon = app.test_client()
    assert anon.get(ENDPOINT).status_code == 401

    staff = app.test_client()
    _login(staff, "petugas1")
    assert staff.get(ENDPOINT).status_code == 403
    assert staff.get(EXPORT).status_code == 403

    admin = app.test_client()
    _login(admin, "peneliti")
    res = admin.get(ENDPOINT)
    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "no-store"
    assert res.json["data"]["status"] == "empty"
    assert res.json["data"]["available"] is False


def test_evaluation_statuses_split_separation_and_exports(tmp_path):
    bundle_dir = tmp_path / "bundle"
    _write_bundle(bundle_dir, mode="final", tree_clean=True, agreement_status="complete")
    app = _make_app(tmp_path, bundle_dir)
    admin = app.test_client()
    _login(admin, "peneliti")

    test_res = admin.get(f"{ENDPOINT}?split=test").json["data"]
    assert test_res["status"] == "final"
    assert test_res["manifest"]["valid"] is True
    assert test_res["split_counts"]["split_leakage_count"] == 0
    assert test_res["method_summary"][0]["mrr_at_10"] == pytest.approx(0.75)
    assert test_res["per_query"]["total"] == 2
    assert test_res["tuning_best"][0]["summary_weight"] == pytest.approx(0.6)

    tuning_res = admin.get(f"{ENDPOINT}?split=tuning").json["data"]
    assert tuning_res["split"] == "tuning"
    assert tuning_res["method_summary"][0]["mrr_at_10"] == pytest.approx(1.0)
    assert tuning_res["per_query"]["total"] == 1

    # Ekspor JSON dan CSV
    exp_json = admin.get(f"{EXPORT}?split=test&format=json")
    assert exp_json.status_code == 200
    assert "evaluasi-run-test.json" in exp_json.headers["Content-Disposition"]
    assert json.loads(exp_json.data.decode("utf-8"))["status"] == "final"

    exp_csv = admin.get(f"{EXPORT}?split=test&format=csv")
    assert exp_csv.status_code == 200
    assert "evaluasi-run-test.csv" in exp_csv.headers["Content-Disposition"]
    assert "Q1" in exp_csv.data.decode("utf-8")
    assert "Q3" not in exp_csv.data.decode("utf-8")

    # Parameter tidak sah
    assert admin.get(f"{ENDPOINT}?split=all").status_code == 400
    assert admin.get(f"{EXPORT}?format=xlsx").status_code == 400


def test_evaluation_pending_draft_leakage_and_forbidden_columns(tmp_path):
    # Pending karena kesepakatan penilai belum selesai
    bundle_pending = tmp_path / "bundle_pending"
    _write_bundle(bundle_pending, mode="final", tree_clean=True, agreement_status="pending_second_rater")
    app = _make_app(tmp_path, bundle_pending)
    admin = app.test_client()
    _login(admin, "peneliti")
    assert admin.get(ENDPOINT).json["data"]["status"] == "pending"

    # Draft karena kebocoran split tuning/test
    bundle_leak = tmp_path / "bundle_leak"
    _write_bundle(bundle_leak, mode="final", tree_clean=True, agreement_status="complete", leak=True)
    app.config["EVALUATION_BUNDLE_DIR"] = bundle_leak
    leak_data = admin.get(ENDPOINT).json["data"]
    assert leak_data["status"] == "draft"
    assert leak_data["split_counts"]["split_leakage_count"] == 1

    # Menolak kolom sensitif summary_raw
    bundle_bad = tmp_path / "bundle_bad"
    _write_bundle(bundle_bad, forbidden_col=True)
    app.config["EVALUATION_BUNDLE_DIR"] = bundle_bad
    assert admin.get(ENDPOINT).status_code == 400
