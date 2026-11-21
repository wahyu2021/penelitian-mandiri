"""Perbandingan metode pencarian hanya untuk admin penelitian."""

import sqlite3

from flask import abort, current_app, request

from services.web_search import METHODS, compare_methods
from webapp.api import api, success
from webapp.api.method_labels import METHOD_LABELS
from webapp.api.query_params import optional_int, reject_duplicate_params
from webapp.api.session import require_api_role


@api.get("/search/compare")
@require_api_role("admin")
def compare():
    reject_duplicate_params(("q", "opd_id", "year", "status", "limit"))
    query = request.args.get("q", "").strip()
    if not query or len(query) > 200:
        abort(400, description="Kueri perbandingan wajib diisi, maksimal 200 karakter.")
    opd_id = optional_int("opd_id", minimum=1)
    year = optional_int("year", minimum=1900, maximum=2100)
    status = optional_int("status", minimum=1, maximum=3)
    limit = optional_int("limit", minimum=1, maximum=20, default=10)

    try:
        results = compare_methods(
            current_app.config["DATABASE"], query,
            opd_id=opd_id, year=year, status=status, limit=limit,
        )
    except (OSError, sqlite3.Error):
        abort(500, description="Perbandingan metode tidak dapat dijalankan.")

    methods = [
        {
            "name": method,
            "label": METHOD_LABELS[method],
            "items": [
                {"id": row["id"], "summary_raw": row["summary_raw"], "score": row["score"]}
                for row in results[method]
            ],
        }
        for method in METHODS
    ]
    response, code = success({
        "query": query,
        "limit": limit,
        "filters": {"opd_id": opd_id, "year": year, "status": status},
        "methods": methods,
        "score_note": "Skor antarmetode tidak selalu sebanding.",
    })
    response.headers["Cache-Control"] = "no-store"
    return response, code
