"""Kontrak versi web, integritas split, dan kompatibilitas ekspor."""

import hashlib
import json

import pytest
from werkzeug.security import generate_password_hash

from services.db import get_connection, init_db
from webapp import create_app


@pytest.fixture
def testset_app(tmp_path):
    path = tmp_path / "testsets.sqlite"
    conn = init_db(path)
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            [(role, generate_password_hash("kata-sandi-aman"), role, "2026-11-23")
             for role in ("admin", "petugas")],
        )
    conn.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path, "SERVE_REACT": False})


def login(client, role="admin"):
    token = client.get("/api/v1/session").json["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session", json={"username": role, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    return response.json["data"]["csrf_token"]


def query(number, split, **overrides):
    return {
        "query_id": f"Q{number}", "base_query_id": f"B{number}",
        "query_text": f"Renovasi {number}", "source": "sintetis",
        "query_type": "topik", "noise_type": "tanpa_gangguan",
        "origin_archive_id": number, "split": split, "judgments": [],
        **overrides,
    }


def payload(*queries):
    return {"version": "v2-uji", "queries": list(queries)}


def cli_hash(contents):
    return hashlib.sha256(json.dumps(contents, indent=2, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def test_testset_lifecycle_and_export(testset_app):
    client = testset_app.test_client()
    token = login(client)
    headers = {"X-CSRF-Token": token}
    base = "/api/v1/testsets"
    route = f"{base}/v2-uji"
    data = payload(query(1, "tuning"), query(2, "test", source="arsiparis", origin_archive_id=None))
    assert client.get(base).json["data"] == []
    assert client.post(base, json=data).status_code == 403
    created = client.post(base, json={**data, "content_sha256": cli_hash(data)}, headers=headers)
    assert created.status_code == 201
    draft = created.json["data"]
    assert draft["locked_at"] is None and draft["sources"] == {"sintetis": 1, "arsiparis": 1}
    assert client.get(route).json["data"]["n_tuning_base_queries"] == 1
    assert client.get(f"{route}/export").status_code == 409
    assert client.post(base, json=data, headers=headers).status_code == 409
    guarded = {**headers, "If-Match": f'"{draft["content_sha256"]}"'}
    updated = {**data, "queries": [data["queries"][0], {**data["queries"][1], "query_text": " Pekerjaan gedung "}]}
    assert client.put(route, json=updated, headers=guarded).status_code == 200
    assert client.post(f"{route}/lock", headers=guarded).status_code == 409
    guarded["If-Match"] = f'"{cli_hash(updated)}"'
    locked = client.post(f"{route}/lock", headers=guarded)
    assert locked.status_code == 200
    assert locked.json["data"]["locked_at"] and locked.json["data"]["locked_by"] == 1
    assert client.put(route, json=data, headers=guarded).status_code == 409
    assert client.post(f"{route}/lock", headers=guarded).status_code == 409
    exported = client.get(f"{route}/export")
    assert exported.headers["Content-Disposition"] == 'attachment; filename="testset-v2-uji.json"'
    assert exported.headers["Cache-Control"] == "no-store"
    assert exported.json == {**updated, "content_sha256": cli_hash(updated)}
    conn = get_connection(testset_app.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM activity_log WHERE action='testset_locked'").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize("first,second", [
    ({}, {"base_query_id": "B1", "origin_archive_id": 1}),
    ({}, {"origin_archive_id": 1}),
    ({"spm_number": "03 / LS"}, {"spm_number": "03/ls"}),
    ({"party_name": "PT. Contoh"}, {"party_name": "PT Contoh"}),
    ({"duplicate_group_id": "D1"}, {"duplicate_group_id": "d1"}),
])
def test_testset_rejects_split_leakage(testset_app, first, second):
    client = testset_app.test_client()
    headers = {"X-CSRF-Token": login(client)}
    response = client.post("/api/v1/testsets", headers=headers, json=payload(
        query(1, "tuning", **first), query(2, "test", **second),
    ))
    assert response.status_code == 422
    assert "split" in response.json["error"]["message"].lower()
    assert client.get("/api/v1/testsets").json["data"] == []


def test_testset_rejects_bad_hash_and_inconsistent_variants(testset_app):
    client = testset_app.test_client()
    headers = {"X-CSRF-Token": login(client)}
    base = "/api/v1/testsets"
    assert client.post(base, headers=headers, json={
        **payload(query(1, "test")), "content_sha256": "0" * 64,
    }).status_code == 422
    changed = query(2, "test", base_query_id="B1", origin_archive_id=1, judgments=[
        {"archive_id": 1, "is_relevant": 1},
    ])
    assert client.post(base, headers=headers, json=payload(query(1, "test"), changed)).status_code == 422
    draft = client.post(base, headers=headers, json=payload(query(1, "test"))).json["data"]
    headers["If-Match"] = f'"{draft["content_sha256"]}"'
    assert client.post(f"{base}/v2-uji/lock", headers=headers).status_code == 422


def test_testset_requires_admin(testset_app):
    client = testset_app.test_client()
    assert client.get("/api/v1/testsets").status_code == 401
    token = login(client, "petugas")
    assert client.get("/api/v1/testsets").status_code == 403
    assert client.get("/api/v1/testsets/v2-uji/export").status_code == 403
    assert client.post("/api/v1/testsets", headers={"X-CSRF-Token": token}, json={}).status_code == 403
