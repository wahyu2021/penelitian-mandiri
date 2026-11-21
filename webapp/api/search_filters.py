"""Pilihan filter yang tersedia pada salinan data penelitian."""

import sqlite3

from flask import abort, current_app
from flask_login import current_user

from services.web_search import DEFAULT_METHOD, list_opd_options
from webapp.api import api, success
from webapp.api.method_labels import method_options
from webapp.api.session import require_api_user


@api.get("/search/filters")
@require_api_user
def search_filters():
    try:
        opds = list_opd_options(current_app.config["DATABASE"])
    except (OSError, sqlite3.Error):
        abort(500, description="Pilihan filter tidak dapat dibaca.")
    response, status = success({
        "opds": opds,
        "default_method": DEFAULT_METHOD,
        "methods": method_options() if current_user.role == "admin" else [],
    })
    response.headers["Cache-Control"] = "no-store"
    return response, status
