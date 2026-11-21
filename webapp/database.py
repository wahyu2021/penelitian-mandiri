"""Koneksi dan pencatatan aktivitas aplikasi web."""

from datetime import datetime, timezone

from flask import current_app, g

from services.db import get_connection


def db():
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE"])
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def log_action(action, *, user_id, detail=None):
    with db():
        db().execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, detail, datetime.now(timezone.utc).isoformat()),
        )
