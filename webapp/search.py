"""Pencarian arsip dan pembandingan metode."""

from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required

from services.web_search import DEFAULT_METHOD, METHODS, compare_methods, list_opd_options, search_archives
from webapp.auth import admin_required

search_pages = Blueprint("search", __name__)


def optional_int(name):
    value = request.args.get(name, "").strip()
    if not value:
        return None
    if not value.isdecimal():
        abort(400, description=f"Filter {name} harus berupa angka.")
    return int(value)


@search_pages.get("/search")
@login_required
def search():
    query = request.args.get("q", "").strip()
    method = request.args.get("method", DEFAULT_METHOD)
    if len(query) > 200 or method not in METHODS:
        abort(400, description="Kueri atau metode pencarian tidak valid.")
    if current_user.role != "admin" and method != DEFAULT_METHOD:
        abort(403, description="Pemilihan metode hanya tersedia untuk admin.")
    filters = {name: optional_int(name) for name in ("opd_id", "year", "status")}
    if filters["status"] not in (None, 1, 2, 3):
        abort(400, description="Status arsip tidak valid.")
    results = (
        search_archives(current_app.config["DATABASE"], query, method, **filters)
        if query else []
    )
    opds = list_opd_options(current_app.config["DATABASE"])
    return render_template("search.html", query=query, method=method, methods=METHODS,
                           filters=filters, results=results, opds=opds)


@search_pages.get("/search/compare")
@admin_required
def compare():
    query = request.args.get("q", "").strip()
    if len(query) > 200:
        abort(400, description="Kueri terlalu panjang.")
    results = compare_methods(current_app.config["DATABASE"], query) if query else {}
    return render_template("compare.html", query=query, results=results)
