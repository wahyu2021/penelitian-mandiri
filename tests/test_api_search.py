"""Kontrak API pencarian, paging, filter, dan izin metode."""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.db import get_connection, init_db
from services.web_search import search_archives
from webapp import create_app


@pytest.fixture
def search_app(tmp_path):
    path = tmp_path / "search.sqlite"
    connection = init_db(path)
    with connection:
        now = datetime.now(timezone.utc).isoformat()
        for username, role in (("admin", "admin"), ("petugas", "petugas")):
            connection.execute(
                "INSERT INTO user(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash("kata-sandi-aman"), role, now),
            )
        connection.execute(
            """INSERT INTO import_batch
               (source_filename, source_sha256, parser_version, extractor_version, imported_at)
               VALUES ('sample.sql', 'abc', 'v1', 'v1', ?)""", (now,),
        )
        connection.executemany(
            "INSERT INTO opd(id, name, name_normalized) VALUES (?, ?, ?)",
            [(1, "Dinas Pekerjaan Umum", "dinas pekerjaan umum"),
             (2, "Dinas Kesehatan", "dinas kesehatan")],
        )
        connection.executemany(
            """INSERT INTO archive
               (id, batch_id, opd_id, opd_id_source, year, summary_raw,
                summary_clean, status, has_document)
               VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (10, 1, 1, 2020, "Arsip jembatan kota", "arsip jembatan kota", 1, 1),
                (11, 1, 1, 2021, "Arsip irigasi desa", "arsip irigasi desa", 2, 0),
                (12, 2, 2, 2020, "Arsip vaksin", "arsip vaksin", 1, 0),
                (13, 1, 1, 2022, "Arsip jembatan baru", "arsip jembatan baru", 3, 0),
            ],
        )
    connection.close()
    return create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": path})


def login(client, username="admin"):
    token = client.get("/api/v1/session").get_json()["data"]["csrf_token"]
    response = client.post(
        "/api/v1/session", json={"username": username, "password": "kata-sandi-aman"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200


def test_search_requires_login_and_returns_empty_for_blank_query(search_app):
    client = search_app.test_client()
    assert client.get("/api/v1/search?q=jembatan").status_code == 401
    login(client)
    response = client.get("/api/v1/search?q=%20%20")
    assert response.status_code == 200
    assert response.get_json() == {"data": {
        "query": "", "method": "like", "items": [],
        "pagination": {"limit": 20, "offset": 0, "total": 0},
    }}


def test_search_pagination_order_and_minimum_fields(search_app):
    client = search_app.test_client()
    login(client)
    response = client.get("/api/v1/search?q=arsip&limit=2&offset=1")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()["data"]
    assert data["pagination"] == {"limit": 2, "offset": 1, "total": 4}
    assert [row["id"] for row in data["items"]] == [11, 12]
    assert set(data["items"][0]) == {
        "id", "summary_raw", "opd_name", "year", "spm_number",
        "file_number", "has_document", "score",
    }
    assert client.get("/api/v1/search?q=arsip&offset=99").get_json()["data"]["items"] == []


def test_search_filters_and_typo_matcher_use_service_results(search_app):
    client = search_app.test_client()
    login(client)
    filtered = client.get("/api/v1/search?q=arsip&opd_id=1&year=2020&status=1")
    assert [row["id"] for row in filtered.get_json()["data"]["items"]] == [10]
    typo = client.get("/api/v1/search?q=jembatn&method=levenshtein")
    assert typo.status_code == 200
    data = typo.get_json()["data"]
    expected = search_archives(search_app.config["DATABASE"], "jembatn", "levenshtein", limit=None)
    assert [row["id"] for row in data["items"]] == [row["id"] for row in expected]
    assert [row["score"] for row in data["items"]] == [row["score"] for row in expected]
    assert client.get("/api/v1/search?q=tidak-ada-000").get_json()["data"]["pagination"]["total"] == 0


@pytest.mark.parametrize("parameter", [
    "q=" + "a" * 201, "method=unknown", "opd_id=-1", "year=1899",
    "year=2101", "status=4", "limit=0", "limit=101", "limit=", "offset=", "offset=-1",
    "offset=99999999999999999999999999999999", "opd_id=abc", "q=dua",
])
def test_search_rejects_invalid_parameters(search_app, parameter):
    client = search_app.test_client()
    login(client)
    url = "/api/v1/search?" + (parameter if parameter.startswith("q=" + "a" * 201) else "q=arsip&" + parameter)
    response = client.get(url)
    assert response.status_code == 400
    assert response.is_json


def test_petugas_cannot_choose_fuzzy_method_or_open_jinja_method(search_app):
    client = search_app.test_client()
    login(client, "petugas")
    default = client.get("/api/v1/search?q=jembatan")
    assert default.status_code == 200
    assert default.get_json()["data"]["method"] == "like"
    denied = client.get("/api/v1/search?q=jembatan&method=levenshtein")
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "forbidden"
    assert client.get("/search?q=jembatan&method=levenshtein").status_code == 403
    assert b'name="method"' not in client.get("/search?q=jembatan").data


def test_search_database_error_is_safe_json(search_app):
    client = search_app.test_client()
    login(client)
    connection = get_connection(search_app.config["DATABASE"])
    with connection:
        connection.execute("DROP TABLE archive")
    connection.close()
    response = client.get("/api/v1/search?q=arsip")
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "server_error"
    assert "no such table" not in response.get_data(as_text=True)
