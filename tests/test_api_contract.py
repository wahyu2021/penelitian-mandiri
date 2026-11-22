"""Kontrak respons dasar API sebelum endpoint bisnis dipindahkan."""

from flask import abort

from webapp import create_app


def make_app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": tmp_path / "api.sqlite"})

    @app.get("/api/v1/_bad-request")
    def bad_request_for_test():
        abort(400, description="Masukan tidak valid.")

    @app.get("/api/v1/_server-error")
    def server_error_for_test():
        abort(500, description="Rincian internal tidak boleh tampil.")

    return app


def test_health_uses_versioned_data_envelope(tmp_path):
    client = make_app(tmp_path).test_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"data": {"status": "ok"}}


def test_api_unknown_path_and_method_return_json(tmp_path):
    client = make_app(tmp_path).test_client()
    missing = client.get("/api/v1/unknown")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "not_found"
    assert client.get("/api/v2/unknown").is_json

    wrong_method = client.post("/api/v1/health")
    assert wrong_method.status_code == 405
    assert wrong_method.get_json()["error"]["code"] == "method_not_allowed"
    assert "GET" in wrong_method.headers["Allow"]


def test_api_bad_request_and_server_error_have_safe_messages(tmp_path):
    client = make_app(tmp_path).test_client()
    bad = client.get("/api/v1/_bad-request")
    assert bad.status_code == 400
    assert bad.get_json() == {
        "error": {"code": "bad_request", "message": "Masukan tidak valid."}
    }

    server = client.get("/api/v1/_server-error")
    assert server.status_code == 500
    assert server.get_json()["error"]["code"] == "server_error"
    assert "Rincian internal" not in server.get_data(as_text=True)


def test_unknown_page_has_plain_error_and_legacy_routes_are_gone(tmp_path):
    app = make_app(tmp_path)
    app.config["SERVE_REACT"] = False
    client = app.test_client()
    assert client.get("/search").status_code == 404
    assert client.get("/archives/1").status_code == 404
    missing = client.get("/missing-page")
    assert missing.status_code == 404
    assert not missing.is_json
    assert missing.mimetype == "text/plain"
