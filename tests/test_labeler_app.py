"""Uji unit untuk endpoint aplikasi web pelabel relevansi."""
import csv
from pathlib import Path
import pytest
from scripts.relevance_labeler_app import app, write_pool_csv, get_local_ip


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    test_csv = tmp_path / "relevance_pool.csv"
    fieldnames = [
        "query_id", "query_text", "query_type", "source", "noise_type",
        "pool_order", "archive_id", "summary_raw", "spm_number", "party_name",
        "is_relevant", "ragu", "auditor_notes",
    ]
    rows = [
        {
            "query_id": "Q001",
            "query_text": "termin dan III",
            "query_type": "topik",
            "source": "sintetis",
            "noise_type": "tanpa_gangguan",
            "pool_order": "1",
            "archive_id": "100",
            "summary_raw": "Pembayaran termin III",
            "spm_number": "123/LS/2000",
            "party_name": "CV Contoh",
            "is_relevant": "",
            "ragu": "",
            "auditor_notes": "",
        },
        {
            "query_id": "Q001",
            "query_text": "termin dan III",
            "query_type": "topik",
            "source": "sintetis",
            "noise_type": "tanpa_gangguan",
            "pool_order": "2",
            "archive_id": "101",
            "summary_raw": "Pengadaan ATK",
            "spm_number": "456/BT/2000",
            "party_name": "PT Maju",
            "is_relevant": "1",
            "ragu": "0",
            "auditor_notes": "catatan awal",
        },
    ]
    write_pool_csv(test_csv, fieldnames, rows)

    # Monkeypatch OUTPUT_DIR ke tmp_path
    monkeypatch.setattr("scripts.relevance_labeler_app.OUTPUT_DIR", tmp_path)

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, test_csv


def test_index_route(client):
    c, _ = client
    res = c.get("/")
    assert res.status_code == 200
    assert b"Pelabel Relevansi" in res.data
    # Verifikasi elemen responsif mobile
    assert b"btnMobileRelevant" in res.data
    assert b"btnMobileIrrelevant" in res.data
    assert b"btnMobileRagu" in res.data
    assert b"mobileProgressBar" in res.data


def test_get_local_ip():
    ip = get_local_ip()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4


def test_api_get_data(client):
    c, _ = client
    res = c.get("/api/data?dataset=relevance_pool.csv")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["items"]) == 2
    assert data["stats"]["total"] == 2
    assert data["stats"]["judged"] == 1
    assert data["stats"]["relevant"] == 1


def test_api_save_item(client):
    c, test_csv = client
    payload = {
        "dataset": "relevance_pool.csv",
        "index": 0,
        "query_id": "Q001",
        "archive_id": "100",
        "is_relevant": "1",
        "ragu": "1",
        "notes": "Arsip sangat cocok",
    }
    res = c.post("/api/save", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["stats"]["judged"] == 2
    assert data["stats"]["relevant"] == 2
    assert data["stats"]["ragu"] == 1

    # Verifikasi langsung pada berkas CSV
    with open(test_csv, "r", encoding="utf-8-sig") as f:
        saved_rows = list(csv.DictReader(f))
    assert saved_rows[0]["is_relevant"] == "1"
    assert saved_rows[0]["ragu"] == "1"
    assert saved_rows[0]["auditor_notes"] == "Arsip sangat cocok"
