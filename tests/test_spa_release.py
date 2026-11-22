"""Kontrak penyajian React saat rilis tanpa route halaman lama."""

import pytest

from webapp import create_app


@pytest.fixture
def spa_app(tmp_path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        '<!doctype html><div id="root"></div>'
        '<script src="/assets/index-ABCdef12.js"></script>', encoding="utf-8"
    )
    (assets / "index-ABCdef12.js").write_text("window.APP_READY = true;", encoding="utf-8")
    (assets / "index-ABCdef12.css").write_text("body{color:black}", encoding="utf-8")
    return create_app({
        "TESTING": True, "SECRET_KEY": "test-only", "DATABASE": tmp_path / "unused.sqlite",
        "SERVE_REACT": True, "FRONTEND_DIST": dist,
    })


@pytest.mark.parametrize("route", ["/", "/login", "/app", "/app/search?q=arsip",
                                   "/app/archives/41", "/app/compare"])
def test_spa_direct_urls_and_reload_serve_index(spa_app, route):
    response = spa_app.test_client().get(route)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.mimetype == "text/html"
    assert b'<div id="root"></div>' in response.data


def test_hashed_assets_load_and_missing_assets_do_not_fall_back(spa_app):
    client = spa_app.test_client()
    js = client.get("/assets/index-ABCdef12.js")
    assert js.status_code == 200
    assert js.mimetype in ("text/javascript", "application/javascript")
    assert js.headers["Cache-Control"] == "public, max-age=31536000, immutable"
    assert b"APP_READY" in js.data
    assert client.get("/assets/index-ABCdef12.css").status_code == 200
    missing = client.get("/assets/missing.js")
    assert missing.status_code == 404
    assert b'<div id="root"></div>' not in missing.data


def test_api_routes_remain_json_and_unauthorized(spa_app):
    client = spa_app.test_client()
    assert client.get("/api/v1/health").get_json() == {"data": {"status": "ok"}}
    assert client.get("/api/v2/missing").get_json()["error"]["code"] == "not_found"
    denied = client.get("/api/v1/search?q=arsip")
    assert denied.status_code == 401
    assert denied.get_json()["error"]["code"] == "unauthorized"
    assert b'<div id="root"></div>' not in denied.data


def test_missing_build_fails_fast_and_api_only_mode_has_no_jinja(tmp_path):
    with pytest.raises(RuntimeError, match="Build React tidak ditemukan"):
        create_app({"TESTING": True, "SERVE_REACT": True, "FRONTEND_DIST": tmp_path})
    api_only = create_app({
        "TESTING": True, "SECRET_KEY": "test-only", "DATABASE": tmp_path / "unused.sqlite",
        "SERVE_REACT": False,
    })
    assert api_only.test_client().get("/").status_code == 404
    assert api_only.test_client().get("/search?q=arsip").status_code == 404
    assert api_only.test_client().get("/login").status_code == 404
