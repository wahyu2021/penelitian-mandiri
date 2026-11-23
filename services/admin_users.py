"""Layanan pengelolaan akun lokal dan pembacaan log aktivitas untuk admin."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from werkzeug.security import generate_password_hash

ALLOWED_ROLES = ("admin", "petugas")
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 1024
MAX_USERNAME_LENGTH = 80


class DuplicateUsernameError(ValueError):
    """Nama pengguna sudah terdaftar di basis data lokal."""


class UserNotFoundError(LookupError):
    """Akun yang dituju tidak ditemukan."""


class SelfDisableError(ValueError):
    """Admin mencoba menonaktifkan akunnya sendiri."""


def _serialize_user(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def _validate_password(password: str) -> str:
    if (
        not isinstance(password, str)
        or len(password) < MIN_PASSWORD_LENGTH
        or len(password) > MAX_PASSWORD_LENGTH
    ):
        raise ValueError(
            f"Kata sandi harus {MIN_PASSWORD_LENGTH} hingga {MAX_PASSWORD_LENGTH} karakter."
        )
    return password


def list_users(connection: sqlite3.Connection) -> list[dict]:
    """Kembalikan daftar akun lokal tanpa kolom kata sandi."""
    rows = connection.execute(
        "SELECT id, username, role, is_active, created_at FROM user ORDER BY id ASC"
    ).fetchall()
    return [_serialize_user(row) for row in rows]


def create_local_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    password: str,
    role: str,
    actor_id: int,
) -> dict:
    """Buat akun lokal baru dan catat ke log aktivitas tanpa kata sandi."""
    if not isinstance(username, str):
        raise ValueError("Nama pengguna wajib diisi.")
    clean_username = username.strip()
    if (
        not clean_username
        or len(clean_username) > MAX_USERNAME_LENGTH
        or any(ch.isspace() for ch in clean_username)
    ):
        raise ValueError(
            f"Nama pengguna wajib diisi (1–{MAX_USERNAME_LENGTH} karakter tanpa spasi)."
        )
    if role not in ALLOWED_ROLES:
        raise ValueError("Peran akun harus admin atau petugas.")
    valid_password = _validate_password(password)
    now = datetime.now(timezone.utc).isoformat()
    password_hash = generate_password_hash(valid_password)

    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO user(username, password_hash, role, is_active, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (clean_username, password_hash, role, now),
            )
            user_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (
                    actor_id,
                    "user_create",
                    json.dumps(
                        {"target_user_id": user_id, "username": clean_username, "role": role},
                        ensure_ascii=False,
                    ),
                    now,
                ),
            )
            row = connection.execute(
                "SELECT id, username, role, is_active, created_at FROM user WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        raise DuplicateUsernameError("Nama pengguna sudah dipakai.") from exc
    return _serialize_user(row)


def set_user_active(
    connection: sqlite3.Connection,
    *,
    target_user_id: int,
    is_active: bool,
    actor_id: int,
) -> dict:
    """Aktifkan atau nonaktifkan akun lokal kecuali menonaktifkan diri sendiri."""
    if target_user_id == actor_id and not is_active:
        raise SelfDisableError("Admin tidak dapat menonaktifkan akunnya sendiri.")

    target = connection.execute(
        "SELECT id, username, role, is_active, created_at FROM user WHERE id = ?",
        (target_user_id,),
    ).fetchone()
    if target is None:
        raise UserNotFoundError("Akun tidak ditemukan.")

    now = datetime.now(timezone.utc).isoformat()
    action = "user_enable" if is_active else "user_disable"
    with connection:
        connection.execute(
            "UPDATE user SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, target_user_id),
        )
        connection.execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                actor_id,
                action,
                json.dumps(
                    {"target_user_id": target_user_id, "username": target["username"]},
                    ensure_ascii=False,
                ),
                now,
            ),
        )
        updated = connection.execute(
            "SELECT id, username, role, is_active, created_at FROM user WHERE id = ?",
            (target_user_id,),
        ).fetchone()
    return _serialize_user(updated)


def reset_user_password(
    connection: sqlite3.Connection,
    *,
    target_user_id: int,
    new_password: str,
    actor_id: int,
) -> dict:
    """Atur ulang kata sandi akun lokal dan catat ke log tanpa kata sandi."""
    valid_password = _validate_password(new_password)
    target = connection.execute(
        "SELECT id, username, role, is_active, created_at FROM user WHERE id = ?",
        (target_user_id,),
    ).fetchone()
    if target is None:
        raise UserNotFoundError("Akun tidak ditemukan.")

    now = datetime.now(timezone.utc).isoformat()
    password_hash = generate_password_hash(valid_password)
    with connection:
        connection.execute(
            "UPDATE user SET password_hash = ? WHERE id = ?",
            (password_hash, target_user_id),
        )
        connection.execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                actor_id,
                "user_reset_password",
                json.dumps(
                    {"target_user_id": target_user_id, "username": target["username"]},
                    ensure_ascii=False,
                ),
                now,
            ),
        )
    return _serialize_user(target)


def list_activity_logs(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
    action: Optional[str] = None,
    username: Optional[str] = None,
) -> list[dict]:
    """Baca riwayat log aktivitas terbaru dengan filter opsional."""
    clauses = []
    params: list[object] = []
    if action:
        clauses.append("l.action = ?")
        params.append(action)
    if username:
        clauses.append("u.username = ?")
        params.append(username)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = connection.execute(
        f"""
        SELECT l.id, l.user_id, u.username, l.action, l.detail, l.created_at
        FROM activity_log l
        LEFT JOIN user u ON u.id = l.user_id
        {where_sql}
        ORDER BY l.id DESC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "user_id": int(row["user_id"]) if row["user_id"] is not None else None,
            "username": row["username"],
            "action": row["action"],
            "detail": row["detail"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
