"""Sesi JSON untuk frontend pada origin yang sama dengan Flask."""

import secrets
import sqlite3
from functools import wraps

from flask import abort, request, session
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash

from webapp.api import api, success
from webapp.auth import User, csrf_token
from webapp.database import db, log_action


def require_api_user(view):
    """Tolak API tanpa sesi dengan 401 JSON, bukan redirect halaman login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401, description="Sesi telah berakhir. Silakan masuk kembali.")
        return view(*args, **kwargs)
    return wrapped


def require_api_role(role):
    """Periksa peran di server untuk endpoint API."""
    def decorate(view):
        @wraps(view)
        @require_api_user
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                abort(403, description="Akun tidak berhak mengakses fitur ini.")
            return view(*args, **kwargs)
        return wrapped
    return decorate


def _check_csrf_header():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(403, description="Token keamanan tidak valid. Muat ulang halaman dan coba lagi.")


def _user_data():
    return {"id": current_user.id, "username": current_user.username, "role": current_user.role}


def _session_data():
    return {
        "authenticated": current_user.is_authenticated,
        "user": _user_data() if current_user.is_authenticated else None,
        "csrf_token": csrf_token(),
    }


@api.get("/session")
def session_status():
    response, status = success(_session_data())
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.post("/session")
def session_login():
    _check_csrf_header()
    if not request.is_json:
        abort(400, description="Kirim nama pengguna dan kata sandi sebagai JSON.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Isi JSON tidak valid.")
    username = payload.get("username")
    password = payload.get("password")
    if (not isinstance(username, str) or not username.strip() or len(username) > 100
            or not isinstance(password, str) or not password or len(password) > 1024):
        abort(422, description="Nama pengguna atau kata sandi tidak valid.")

    try:
        row = db().execute("SELECT * FROM user WHERE username = ?", (username.strip(),)).fetchone()
    except sqlite3.OperationalError:
        row = None
    if not row or not row["is_active"] or not check_password_hash(row["password_hash"], password):
        abort(401, description="Nama pengguna atau kata sandi tidak sesuai.")

    # Buang data sesi sebelumnya agar identitas dan token CSRF berganti saat masuk.
    session.clear()
    login_user(User(row))
    log_action("login", user_id=row["id"])
    response, status = success(_session_data())
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.delete("/session")
@require_api_user
def session_logout():
    _check_csrf_header()
    log_action("logout", user_id=current_user.id)
    logout_user()
    session.clear()
    response, status = success({"authenticated": False})
    response.headers["Cache-Control"] = "no-store"
    return response, status
