"""Pencarian arsip JSON dengan izin peran dan paging yang terukur."""

import sqlite3

from flask import abort, current_app, request
from flask_login import current_user

from services.web_search import DEFAULT_METHOD, METHODS, search_archives
from webapp.api import api, success
from webapp.api.query_params import optional_int, reject_duplicate_params
from webapp.api.session import require_api_user


@api.get("/search")
@require_api_user
def search():
    reject_duplicate_params(("q", "method", "opd_id", "year", "status", "limit", "offset"))
    query = request.args.get("q", "").strip()
    if len(query) > 200:
        abort(400, description="Kueri maksimal 200 karakter.")

    requested_method = request.args.get("method")
    if requested_method and requested_method not in METHODS:
        abort(400, description="Metode pencarian tidak dikenal.")
    if current_user.role != "admin" and requested_method not in (None, "", DEFAULT_METHOD):
        abort(403, description="Pemilihan metode hanya tersedia untuk admin.")
    method = requested_method or DEFAULT_METHOD

    opd_id = optional_int("opd_id", minimum=1)
    year = optional_int("year", minimum=1900, maximum=2100)
    status = optional_int("status", minimum=1, maximum=3)
    limit = optional_int("limit", minimum=1, maximum=100, default=20)
    offset = optional_int("offset", minimum=0, default=0)

    try:
        # Mesin pencarian mengurutkan semua hasil sebelum dipotong. Hitung total
        # dari daftar yang sama agar halaman berikutnya tidak mengubah peringkat.
        matches = search_archives(
            current_app.config["DATABASE"], query, method,
            opd_id=opd_id, year=year, status=status, limit=None,
        ) if query else []
    except (OSError, sqlite3.Error):
        abort(500, description="Pencarian arsip tidak dapat dijalankan.")

    items = [
        {
            **{key: row[key] for key in (
                "id", "summary_raw", "opd_name", "year", "spm_number",
                "file_number", "score",
            )},
            "has_document": bool(row["has_document"]),
        }
        for row in matches[offset:offset + limit]
    ]
    response, code = success({
        "query": query,
        "method": method,
        "items": items,
        "pagination": {"limit": limit, "offset": offset, "total": len(matches)},
    })
    response.headers["Cache-Control"] = "no-store"
    return response, code
