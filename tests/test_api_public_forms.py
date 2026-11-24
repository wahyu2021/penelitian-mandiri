"""Kontrak API formulir publik & tautan kunci 1 perangkat [PM-28]."""

import json

import pytest
from werkzeug.security import generate_password_hash

from services.db import init_db
from webapp import create_app

ADMIN = "/api/v1/research/forms"
PUBLIC = "/api/v1/public/forms"


def _login(client, username):
    csrf = client.get("/api/v1/session").json["data"]["csrf_token"]
    res = client.post(
        "/api/v1/session",
        json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    return {"X-CSRF-Token": res.json["data"]["csrf_token"]}


@pytest.fixture
def app(tmp_path):
    path = tmp_path / "forms.sqlite"
    conn = init_db(path)
    pw = generate_password_hash("kata-sandi-aman")
    with conn:
        conn.executemany(
            "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, '2026-01-01')",
            [("peneliti", pw, "admin"), ("petugas", pw, "petugas")],
        )
    conn.close()
    return create_app({"TESTING": True, "DATABASE": path, "SECRET_KEY": "test", "SERVE_REACT": False}), path


def test_sus_form_device_claim_lock_reset_revoke_and_export(app):
    flask_app, db_path = app
    admin = flask_app.test_client()
    staff = flask_app.test_client()
    assert admin.get(ADMIN).status_code == 401
    _login(staff, "petugas")
    assert staff.get(ADMIN).status_code == 403

    headers = _login(admin, "peneliti")
    created = admin.post(
        ADMIN,
        headers=headers,
        json={"title": "Kuesioner SUS Petugas", "description": "Uji lapangan", "form_kind": "sus"},
    )
    assert created.status_code == 201
    form_id = created.json["data"]["id"]
    assert len(created.json["data"]["questions"]) == 11

    link_res = admin.post(
        f"{ADMIN}/{form_id}/links",
        headers=headers,
        json={"participant_code": "P01", "participant_role": "petugas", "lock_single_device": True},
    )
    assert link_res.status_code == 201
    token = link_res.json["data"]["token"]
    link_id = link_res.json["data"]["id"]

    # Pastikan token mentah tidak disimpan di DB
    conn = init_db(db_path)
    row = conn.execute("SELECT token_hash FROM public_form_link WHERE id = ?", (link_id,)).fetchone()
    assert row["token_hash"] != token
    conn.close()

    # Perangkat pertama membuka tautan -> klaim berhasil via cookie HttpOnly
    device1 = flask_app.test_client()
    opened1 = device1.get(f"{PUBLIC}/{token}")
    assert opened1.status_code == 200
    assert opened1.json["data"]["participant_code"] == "P01"
    assert opened1.json["data"]["already_submitted"] is False

    # Perangkat kedua membuka tautan yang sama -> ditolak 403
    device2 = flask_app.test_client()
    assert device2.get(f"{PUBLIC}/{token}").status_code == 403

    # Admin reset kunci perangkat -> sekarang device2 boleh mengklaim, dan device1 ditolak
    assert admin.post(f"{ADMIN}/links/{link_id}/reset-device", headers=headers).status_code == 200
    assert device2.get(f"{PUBLIC}/{token}").status_code == 200
    assert device1.get(f"{PUBLIC}/{token}").status_code == 403

    # Device2 mengirim jawaban SUS hitung tangan (skor 82.5)
    answers = {
        "q1": 4, "q2": 2, "q3": 5, "q4": 2, "q5": 4,
        "q6": 2, "q7": 4, "q8": 1, "q9": 5, "q10": 2,
        "notes": "Mudah dipakai di HP",
    }
    submitted = device2.post(f"{PUBLIC}/{token}/submit", json={"answers": answers})
    assert submitted.status_code == 201
    assert submitted.json["data"]["sus_score"] == pytest.approx(82.5)

    # Kirim ulang ditolak 409
    assert device2.post(f"{PUBLIC}/{token}/submit", json={"answers": answers}).status_code == 409

    # Detail admin memuat rekap SUS dan respons
    detail = admin.get(f"{ADMIN}/{form_id}").json["data"]
    assert detail["sus_summary"]["mean_sus"] == pytest.approx(82.5)
    assert detail["links"][0]["status"] == "submitted"

    # Ekspor CSV dan JSON
    csv_res = admin.get(f"{ADMIN}/{form_id}/export?format=csv")
    assert csv_res.status_code == 200
    assert "P01" in csv_res.data.decode("utf-8")
    assert "82.5" in csv_res.data.decode("utf-8")
    json_res = admin.get(f"{ADMIN}/{form_id}/export?format=json")
    assert json_res.status_code == 200
    assert json.loads(json_res.data.decode("utf-8"))["sus_summary"]["n_respondents"] == 1

    # Cabut tautan -> 410 Gone
    assert admin.post(f"{ADMIN}/links/{link_id}/revoke", headers=headers).status_code == 200
    assert device2.get(f"{PUBLIC}/{token}").status_code == 410


def test_custom_form_validation(app):
    flask_app, _ = app
    admin = flask_app.test_client()
    headers = _login(admin, "peneliti")

    created = admin.post(
        ADMIN,
        headers=headers,
        json={
            "title": "Survei Tambahan",
            "description": "",
            "form_kind": "custom",
            "questions": [
                {"id": "kendala", "type": "choice", "label": "Kendala utama", "options": ["Tidak ada", "Jaringan"], "required": True},
                {"id": "saran", "type": "text", "label": "Saran singkat", "required": False},
            ],
        },
    )
    assert created.status_code == 201
    form_id = created.json["data"]["id"]
    token = admin.post(
        f"{ADMIN}/{form_id}/links",
        headers=headers,
        json={"participant_code": "P02", "participant_role": "petugas", "lock_single_device": False},
    ).json["data"]["token"]

    pub = flask_app.test_client()
    # Pilihan di luar daftar opsi ditolak 422
    assert pub.post(f"{PUBLIC}/{token}/submit", json={"answers": {"kendala": "Lainnya"}}).status_code == 422
    ok = pub.post(f"{PUBLIC}/{token}/submit", json={"answers": {"kendala": "Tidak ada", "saran": "Bagus"}})
    assert ok.status_code == 201
    assert ok.json["data"]["sus_score"] is None
