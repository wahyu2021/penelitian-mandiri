"""Ringkasan dashboard yang dibaca dari salinan SQLite lokal."""

import sqlite3

from flask import abort

from services.dashboard import get_dashboard_summary
from webapp.api import api, success
from webapp.api.session import require_api_user
from webapp.database import db


@api.get("/dashboard")
@require_api_user
def dashboard():
    try:
        summary = get_dashboard_summary(db())
    except sqlite3.Error:
        abort(500, description="Ringkasan arsip tidak dapat dibaca.")
    response, status = success(summary)
    response.headers["Cache-Control"] = "no-store"
    return response, status
