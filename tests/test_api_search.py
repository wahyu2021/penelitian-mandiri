"""Kontrak API pencarian, paging, filter, dan izin metode."""

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from services.db import get_connection, init_db
from services.web_search import METHODS, compare_methods, search_archives
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
        "query": "", "method": "levenshtein", "items": [],
        "pagination": {"limit": 20, "offset": 0, "total": 0},
    }}


def test_search_pagination_order_and_minimum_fields(search_app):
    client = search_app.test_client()
    login(client)
    response = client.get("/api/v1/search?q=arsip&method=like&limit=2&offset=1")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()["data"]
    assert data["pagination"] == {"limit": 2, "offset": 1, "total": 4}
    assert [row["id"] for row in data["items"]] == [11, 12]
    assert set(data["items"][0]) == {
        "id", "summary_raw", "opd_name", "year", "spm_number",
        "file_number", "has_document", "score",
    }
    assert data["items"][0]["has_document"] is False
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
    assert client.get("/api/v1/search?q=zzzzqqqq").get_json()["data"]["pagination"]["total"] == 0
    assert client.get("/api/v1/search?q=tidak-ada-000&opd_id=999").get_json()["data"]["pagination"]["total"] == 0


@pytest.mark.parametrize(("method", "query", "legacy_ids"), [
    ("like", "arsip", [10, 11, 12, 13]),
    ("like", "jembatan", [10, 13]),
    ("levenshtein", "jembatn", [10, 13, 11, 12]),
    ("jaro_winkler", "jembatn", [10, 13]),
])
def test_search_order_matches_recorded_jinja_baseline(search_app, method, query, legacy_ids):
    # Diambil dari route Jinja /search sebelum penghapusannya pada korpus fixture ini.
    client = search_app.test_client()
    login(client)
    response = client.get(f"/api/v1/search?q={query}&method={method}&limit=100")
    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()["data"]["items"]] == legacy_ids


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


def test_petugas_cannot_choose_fuzzy_method(search_app):
    client = search_app.test_client()
    login(client, "petugas")
    default = client.get("/api/v1/search?q=jembatn")
    assert default.status_code == 200
    data = default.get_json()["data"]
    assert data["method"] == "levenshtein"
    assert [row["id"] for row in data["items"]][:2] == [10, 13]
    for disallowed in ("like", "ngram"):
        denied = client.get(f"/api/v1/search?q=jembatan&method={disallowed}")
        assert denied.status_code == 403
        assert denied.get_json()["error"]["code"] == "forbidden"


def test_search_respects_app_setting_default_method(search_app):
    connection = get_connection(search_app.config["DATABASE"])
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO app_setting(key, value) VALUES ('default_search_method', 'jaro_winkler')"
        )
    connection.close()

    client = search_app.test_client()
    login(client, "petugas")
    filters = client.get("/api/v1/search/filters")
    assert filters.status_code == 200
    assert filters.get_json()["data"]["default_method"] == "jaro_winkler"

    result = client.get("/api/v1/search?q=jembatn")
    assert result.status_code == 200
    data = result.get_json()["data"]
    assert data["method"] == "jaro_winkler"
    assert [row["id"] for row in data["items"]] == [10, 13]


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


def test_compare_requires_admin_and_never_redirects_to_html(search_app):
    anonymous = search_app.test_client()
    response = anonymous.get("/api/v1/search/compare?q=jembatan")
    assert response.status_code == 401
    assert response.is_json
    assert "Location" not in response.headers

    petugas = search_app.test_client()
    login(petugas, "petugas")
    denied = petugas.get("/api/v1/search/compare?q=jembatan")
    assert denied.status_code == 403
    assert denied.get_json()["error"]["code"] == "forbidden"


def test_compare_uses_service_order_and_unmodified_scores(search_app):
    client = search_app.test_client()
    login(client)
    response = client.get("/api/v1/search/compare?q=jembatan&limit=2")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()["data"]
    assert data["query"] == "jembatan"
    assert data["limit"] == 2
    assert data["score_note"] == "Skor antarmetode tidak selalu sebanding."
    assert [method["name"] for method in data["methods"]] == list(METHODS)
    assert all(method["label"] for method in data["methods"])
    expected = compare_methods(search_app.config["DATABASE"], "jembatan", limit=2)
    for method in data["methods"]:
        name = method["name"]
        assert method["items"] == [
            {"id": row["id"], "summary_raw": row["summary_raw"], "score": row["score"]}
            for row in expected[name]
        ]
        assert len(method["items"]) <= 2


def test_compare_applies_same_filter_to_every_method(search_app):
    client = search_app.test_client()
    login(client)
    response = client.get("/api/v1/search/compare?q=arsip&opd_id=1&year=2020&status=1&limit=1")
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["filters"] == {"opd_id": 1, "year": 2020, "status": 1}
    assert all([item["id"] for item in method["items"]] == [10] for method in data["methods"])


def test_compare_no_hits_still_lists_every_method(search_app):
    client = search_app.test_client()
    login(client)
    data = client.get("/api/v1/search/compare?q=arsip&opd_id=999").get_json()["data"]
    assert len(data["methods"]) == len(METHODS)
    assert all(method["items"] == [] for method in data["methods"])
    assert data["limit"] == 10


@pytest.mark.parametrize("params", [
    "", "q=", "q=%20%20", "q=" + "a" * 201, "q=arsip&limit=0",
    "q=arsip&limit=21", "q=arsip&limit=", "q=arsip&opd_id=abc",
    "q=arsip&year=1800", "q=arsip&status=4", "q=arsip&q=dua",
])
def test_compare_rejects_invalid_query_and_filters(search_app, params):
    client = search_app.test_client()
    login(client)
    response = client.get("/api/v1/search/compare?" + params)
    assert response.status_code == 400
    assert response.is_json


def test_compare_database_error_is_safe_json(search_app):
    client = search_app.test_client()
    login(client)
    connection = get_connection(search_app.config["DATABASE"])
    with connection:
        connection.execute("DROP TABLE archive")
    connection.close()
    response = client.get("/api/v1/search/compare?q=arsip")
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "server_error"
    assert "no such table" not in response.get_data(as_text=True)


def test_search_filter_options_use_local_opds_and_admin_methods(search_app):
    client = search_app.test_client()
    assert client.get("/api/v1/search/filters").status_code == 401
    login(client)
    response = client.get("/api/v1/search/filters")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.get_json()["data"]
    assert data["opds"] == [
        {"id": 2, "name": "Dinas Kesehatan"},
        {"id": 1, "name": "Dinas Pekerjaan Umum"},
    ]
    assert data["default_method"] == "levenshtein"
    assert [option["name"] for option in data["methods"]] == list(METHODS)
    assert all(option["label"] for option in data["methods"])


def test_petugas_filter_options_hide_admin_methods(search_app):
    client = search_app.test_client()
    login(client, "petugas")
    data = client.get("/api/v1/search/filters").get_json()["data"]
    assert data["methods"] == []
    assert data["default_method"] == "levenshtein"
    assert len(data["opds"]) == 2


def test_filter_options_database_error_is_safe_json(search_app):
    client = search_app.test_client()
    login(client)
    connection = get_connection(search_app.config["DATABASE"])
    connection.execute("PRAGMA foreign_keys = OFF")
    with connection:
        connection.execute("DROP TABLE opd")
    connection.close()
    response = client.get("/api/v1/search/filters")
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "server_error"
    assert "no such table" not in response.get_data(as_text=True)
