"""Endpoint API admin untuk manajemen akun lokal dan log aktivitas."""

import sqlite3

from flask import abort, request
from flask_login import current_user

from services.admin_users import (
    DuplicateUsernameError,
    SelfDisableError,
    UserNotFoundError,
    create_local_user,
    list_activity_logs,
    list_users,
    reset_user_password,
    set_user_active,
)
from webapp.api import api, success
from webapp.api.query_params import optional_int, reject_duplicate_params
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db


def _json_payload() -> dict:
    if not request.is_json:
        abort(400, description="Kirim data sebagai JSON.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Isi JSON tidak valid.")
    return payload


def _no_store(data, status: int = 200):
    response, code = success(data, status)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.get("/admin/users")
@require_api_role("admin")
def admin_list_users():
    try:
        users = list_users(db())
    except sqlite3.Error:
        abort(500, description="Daftar akun belum dapat dibaca.")
    return _no_store({"users": users})


@api.post("/admin/users")
@require_api_role("admin")
def admin_create_user():
    _check_csrf_header()
    payload = _json_payload()
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role")
    if not isinstance(username, str) or not isinstance(password, str) or not isinstance(role, str):
        abort(422, description="Nama pengguna, peran, dan kata sandi wajib berupa teks.")

    try:
        created = create_local_user(
            db(),
            username=username,
            password=password,
            role=role,
            actor_id=int(current_user.id),
        )
    except DuplicateUsernameError as exc:
        abort(409, description=str(exc))
    except ValueError as exc:
        abort(422, description=str(exc))
    except sqlite3.Error:
        abort(500, description="Akun baru belum dapat disimpan.")
    return _no_store({"user": created}, 201)


@api.patch("/admin/users/<int:user_id>/status")
@require_api_role("admin")
def admin_update_user_status(user_id: int):
    _check_csrf_header()
    payload = _json_payload()
    is_active = payload.get("is_active")
    if not isinstance(is_active, bool):
        abort(422, description="Status aktif akun wajib berupa nilai boolean.")

    try:
        updated = set_user_active(
            db(),
            target_user_id=user_id,
            is_active=is_active,
            actor_id=int(current_user.id),
        )
    except SelfDisableError as exc:
        abort(409, description=str(exc))
    except UserNotFoundError as exc:
        abort(404, description=str(exc))
    except sqlite3.Error:
        abort(500, description="Status akun belum dapat diperbarui.")
    return _no_store({"user": updated})


@api.post("/admin/users/<int:user_id>/reset-password")
@require_api_role("admin")
def admin_reset_user_password(user_id: int):
    _check_csrf_header()
    payload = _json_payload()
    password = payload.get("password")
    if not isinstance(password, str):
        abort(422, description="Kata sandi baru wajib berupa teks.")

    try:
        updated = reset_user_password(
            db(),
            target_user_id=user_id,
            new_password=password,
            actor_id=int(current_user.id),
        )
    except UserNotFoundError as exc:
        abort(404, description=str(exc))
    except ValueError as exc:
        abort(422, description=str(exc))
    except sqlite3.Error:
        abort(500, description="Kata sandi akun belum dapat diatur ulang.")
    return _no_store({"user": updated})


@api.get("/admin/activity")
@require_api_role("admin")
def admin_list_activity():
    reject_duplicate_params(("limit", "action", "username"))
    limit = optional_int("limit", minimum=1, maximum=200, default=50)
    action = request.args.get("action", "").strip() or None
    if action and len(action) > 60:
        abort(400, description="Filter aksi maksimal 60 karakter.")
    username = request.args.get("username", "").strip() or None
    if username and len(username) > 80:
        abort(400, description="Filter pengguna maksimal 80 karakter.")

    try:
        items = list_activity_logs(db(), limit=limit, action=action, username=username)
    except sqlite3.Error:
        abort(500, description="Log aktivitas belum dapat dibaca.")
    return _no_store({"items": items})
