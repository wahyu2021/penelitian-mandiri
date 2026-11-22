"""Model akun lokal dan pemuatan sesi untuk API."""

import secrets
import sqlite3

from flask import session
from flask_login import LoginManager, UserMixin

from webapp.database import db

login_manager = LoginManager()


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
