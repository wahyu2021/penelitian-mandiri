"""Fondasi API JSON berversi untuk antarmuka React."""

from flask import Blueprint, jsonify, request

api = Blueprint("api", __name__, url_prefix="/api/v1")

ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    500: "server_error",
}


def is_api_request() -> bool:
    """Kenali seluruh prefiks API, termasuk versi/path yang belum tersedia."""
    return request.path == "/api" or request.path.startswith("/api/")


def success(data, status: int = 200):
    """Bentuk respons sukses yang digunakan endpoint API."""
    return jsonify({"data": data}), status


@api.get("/health")
def health():
    """Pemeriksaan HTTP ringan tanpa membuka isi database."""
    return success({"status": "ok"})


# Impor setelah blueprint dan utilitas tersedia agar route sesi terdaftar.
from webapp.api import session as _session  # noqa: E402,F401
from webapp.api import dashboard as _dashboard  # noqa: E402,F401
from webapp.api import search as _search  # noqa: E402,F401
from webapp.api import archives as _archives  # noqa: E402,F401
from webapp.api import compare as _compare  # noqa: E402,F401
from webapp.api import search_filters as _search_filters  # noqa: E402,F401
from webapp.api import imports as _imports  # noqa: E402,F401
from webapp.api import extraction_audit as _extraction_audit  # noqa: E402,F401
from webapp.api import testsets as _testsets  # noqa: E402,F401
from webapp.api import relevance_reviews as _relevance_reviews  # noqa: E402,F401
from webapp.api import agreement as _agreement  # noqa: E402,F401
from webapp.api import evaluation as _evaluation  # noqa: E402,F401
from webapp.api import quality as _quality  # noqa: E402,F401
from webapp.api import admin_users as _admin_users  # noqa: E402,F401
