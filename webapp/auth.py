"""Autentikasi akun lokal, peran, dan perlindungan formulir."""

import secrets
import sqlite3
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from webapp.database import db, log_action

auth = Blueprint("auth", __name__)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Silakan masuk untuk membuka halaman ini."
login_manager.login_message_category = "info"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.role = row["role"]
        self.active = bool(row["is_active"])

    @property
    def is_active(self):
        return self.active


@login_manager.user_loader
def load_user(user_id):
    if not str(user_id).isdigit():
        return None
    try:
        row = db().execute(
            "SELECT * FROM user WHERE id = ? AND is_active = 1", (int(user_id),)
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return User(row) if row else None


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    expected = session.get("csrf_token")
    supplied = request.form.get("csrf_token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(400, description="Formulir kedaluwarsa. Muat ulang halaman dan coba lagi.")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        check_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            row = db().execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()
        except sqlite3.OperationalError:
            row = None
        if row and row["is_active"] and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            session.pop("csrf_token", None)
            log_action("login", user_id=row["id"])
            target = request.args.get("next", "")
            safe_target = target.startswith("/") and not target.startswith("//") and "\\" not in target
            return redirect(target if safe_target else url_for("main.dashboard"))
        flash("Nama pengguna atau kata sandi tidak sesuai.", "error")
    return render_template("login.html")


@auth.post("/logout")
@login_required
def logout():
    check_csrf()
    log_action("logout", user_id=current_user.id)
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))
