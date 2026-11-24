"""Layanan tautan 1-perangkat untuk penilaian relevansi & audit ekstraksi [PM-29]."""

import secrets
import sqlite3
from typing import Any, Dict, List, Optional

from services.public_forms import (
    DeviceClaimError,
    LinkConflictError,
    LinkRevokedError,
    _log,
    _now,
    _sha256,
    verify_or_claim_device,
)

VALID_TASK_KINDS = frozenset({"relevance", "extraction_audit"})


def task_device_cookie_name(link_id: int) -> str:
    return f"pm_task_device_{link_id}"


def _link_status(row: sqlite3.Row, effective_submitted_at: Optional[str]) -> str:
    if row["revoked_at"] is not None:
        return "revoked"
    if effective_submitted_at is not None:
        return "submitted"
    if row["claimed_device_hash"] is not None:
        return "claimed"
    return "unopened"


def create_task_link(
    conn: sqlite3.Connection,
    *,
    task_kind: str,
    actor_id: int,
    version: Optional[str] = None,
    slot: Optional[int] = None,
    user_id: Optional[int] = None,
    label: str = "",
    lock_single_device: bool = True,
) -> Dict[str, Any]:
    """Terbitkan tautan 1-perangkat baru untuk slot penilai relevansi atau petugas audit."""
    kind = (task_kind or "").strip().lower()
    if kind not in VALID_TASK_KINDS:
        raise ValueError("Jenis tugas tautan harus 'relevance' atau 'extraction_audit'.")

    cleaned_label = (label or "").strip()
    if len(cleaned_label) > 120:
        raise ValueError("Label tautan maksimal 120 karakter.")

    now = _now()
    target_version: Optional[str] = None
    target_slot: Optional[int] = None
    target_user_id: int
    target_username: str

    if kind == "relevance":
        ver = (version or "").strip()
        if not ver or slot not in (1, 2):
            raise ValueError("Tautan relevansi wajib menyertakan versi set uji dan slot penilai (1 atau 2).")
        reviewer_row = conn.execute(
            """
            SELECT rr.user_id, rr.submitted_at, u.username, u.is_active
            FROM relevance_reviewer rr
            JOIN user u ON u.id = rr.user_id
            WHERE rr.version = ? AND rr.slot = ?
            """,
            (ver, slot),
        ).fetchone()
        if reviewer_row is None:
            raise LookupError("Penugasan penilai relevansi tidak ditemukan untuk versi dan slot tersebut.")
        if not bool(reviewer_row["is_active"]):
            raise ValueError("Akun penilai pada slot tersebut tidak aktif.")
        if reviewer_row["submitted_at"] is not None:
            raise LinkConflictError("Penilai pada slot ini sudah menyerahkan jawaban final.")
        target_version = ver
        target_slot = int(slot)
        target_user_id = int(reviewer_row["user_id"])
        target_username = str(reviewer_row["username"])
        if not cleaned_label:
            cleaned_label = f"Penilai {target_slot} ({target_username}) · {target_version}"
    else:
        if not isinstance(user_id, int) or user_id < 1:
            raise ValueError("Tautan audit ekstraksi wajib memilih akun petugas.")
        user_row = conn.execute(
            "SELECT id, username, role, is_active FROM user WHERE id = ?",
            (user_id,),
        ).fetchone()
        if user_row is None or not bool(user_row["is_active"]):
            raise LookupError("Akun petugas aktif tidak ditemukan.")
        target_user_id = int(user_row["id"])
        target_username = str(user_row["username"])
        if not cleaned_label:
            cleaned_label = f"Audit ekstraksi · {target_username}"

    prefix = "rv" if kind == "relevance" else "au"
    raw_token = f"{prefix}_{secrets.token_urlsafe(24)}"
    token_hash = _sha256(raw_token)
    preview = f"{raw_token[:8]}...{raw_token[-4:]}"

    with conn:
        if kind == "extraction_audit":
            # Pastikan petugas otomatis terdaftar pada penugasan audit saat link diterbitkan.
            user_role = conn.execute("SELECT role FROM user WHERE id = ?", (target_user_id,)).fetchone()
            if user_role and user_role["role"] == "petugas":
                conn.execute(
                    """
                    INSERT OR IGNORE INTO extraction_audit_assignment(user_id, assigned_by, assigned_at)
                    VALUES (?, ?, ?)
                    """,
                    (target_user_id, actor_id, now),
                )
        cursor = conn.execute(
            """
            INSERT INTO public_task_link (
                task_kind, token_hash, token_preview, target_user_id, target_version,
                target_slot, label, lock_single_device, created_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kind,
                token_hash,
                preview,
                target_user_id,
                target_version,
                target_slot,
                cleaned_label,
                1 if lock_single_device else 0,
                actor_id,
                now,
            ),
        )
        link_id = int(cursor.lastrowid)
        _log(
            conn,
            actor_id,
            "public_task_link_created",
            {
                "link_id": link_id,
                "task_kind": kind,
                "target_user_id": target_user_id,
                "target_version": target_version,
                "target_slot": target_slot,
            },
            now,
        )

    return {
        "id": link_id,
        "task_kind": kind,
        "token": raw_token,
        "token_preview": preview,
        "public_path": f"/f/{raw_token}",
        "target_user_id": target_user_id,
        "target_username": target_username,
        "target_version": target_version,
        "target_slot": target_slot,
        "label": cleaned_label,
        "lock_single_device": bool(lock_single_device),
        "status": "unopened",
        "created_at": now,
    }


def list_task_links(
    conn: sqlite3.Connection,
    *,
    task_kind: Optional[str] = None,
    version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Kembalikan daftar tautan tugas beserta status kunci perangkat dan penyerahan."""
    clauses = ["1 = 1"]
    params: List[Any] = []
    if task_kind is not None:
        cleaned_kind = task_kind.strip().lower()
        if cleaned_kind not in VALID_TASK_KINDS:
            raise ValueError("Filter task_kind tidak valid.")
        clauses.append("l.task_kind = ?")
        params.append(cleaned_kind)
    if version is not None:
        clauses.append("l.target_version = ?")
        params.append(version.strip())

    rows = conn.execute(
        f"""
        SELECT l.id, l.task_kind, l.token_preview, l.target_user_id, u.username AS target_username,
               l.target_version, l.target_slot, l.label, l.lock_single_device,
               l.claimed_device_hash, l.claimed_at, l.submitted_at, l.revoked_at, l.created_at,
               rr.submitted_at AS reviewer_submitted_at
        FROM public_task_link l
        JOIN user u ON u.id = l.target_user_id
        LEFT JOIN relevance_reviewer rr
          ON l.task_kind = 'relevance' AND rr.version = l.target_version AND rr.slot = l.target_slot
        WHERE {' AND '.join(clauses)}
        ORDER BY l.id DESC
        """,
        params,
    ).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        effective_submitted = row["submitted_at"] or row["reviewer_submitted_at"]
        results.append(
            {
                "id": int(row["id"]),
                "task_kind": str(row["task_kind"]),
                "token_preview": str(row["token_preview"]),
                "target_user_id": int(row["target_user_id"]),
                "target_username": str(row["target_username"]),
                "target_version": row["target_version"],
                "target_slot": int(row["target_slot"]) if row["target_slot"] is not None else None,
                "label": str(row["label"]),
                "lock_single_device": bool(row["lock_single_device"]),
                "status": _link_status(row, effective_submitted),
                "claimed_at": row["claimed_at"],
                "submitted_at": effective_submitted,
                "revoked_at": row["revoked_at"],
                "created_at": str(row["created_at"]),
            }
        )
    return results


def reset_task_link_device(conn: sqlite3.Connection, *, link_id: int, actor_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT id FROM public_task_link WHERE id = ?", (link_id,)).fetchone()
    if row is None:
        raise LookupError("Tautan tugas tidak ditemukan.")
    now = _now()
    with conn:
        conn.execute(
            "UPDATE public_task_link SET claimed_device_hash = NULL, claimed_at = NULL WHERE id = ?",
            (link_id,),
        )
        _log(conn, actor_id, "public_task_link_device_reset", {"link_id": link_id}, now)
    return {"id": link_id, "reset": True}


def revoke_task_link(conn: sqlite3.Connection, *, link_id: int, actor_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT id, revoked_at FROM public_task_link WHERE id = ?", (link_id,)).fetchone()
    if row is None:
        raise LookupError("Tautan tugas tidak ditemukan.")
    now = row["revoked_at"] or _now()
    if row["revoked_at"] is None:
        with conn:
            conn.execute("UPDATE public_task_link SET revoked_at = ? WHERE id = ?", (now, link_id))
            _log(conn, actor_id, "public_task_link_revoked", {"link_id": link_id}, now)
    return {"id": link_id, "revoked_at": now}


def resolve_task_link(
    conn: sqlite3.Connection,
    *,
    raw_token: str,
    expected_kind: str,
    device_cookies: Dict[str, str],
) -> Dict[str, Any]:
    """Verifikasi token tugas publik dan ikat ke perangkat pertama melalui cookie HttpOnly."""
    if expected_kind not in VALID_TASK_KINDS:
        raise ValueError("Jenis tugas tidak valid.")
    token_hash = _sha256(raw_token.strip())
    row = conn.execute(
        """
        SELECT l.id AS link_id, l.task_kind, l.target_user_id, u.username AS target_username,
               u.is_active AS target_active, l.target_version, l.target_slot, l.label,
               l.lock_single_device, l.claimed_device_hash, l.submitted_at, l.revoked_at,
               rr.submitted_at AS reviewer_submitted_at
        FROM public_task_link l
        JOIN user u ON u.id = l.target_user_id
        LEFT JOIN relevance_reviewer rr
          ON l.task_kind = 'relevance' AND rr.version = l.target_version AND rr.slot = l.target_slot
        WHERE l.token_hash = ? AND l.task_kind = ?
        """,
        (token_hash, expected_kind),
    ).fetchone()
    if row is None:
        raise LookupError("Tautan penilaian tidak ditemukan atau tidak sah.")
    if row["revoked_at"] is not None:
        raise LinkRevokedError("Tautan penilaian ini telah dicabut oleh peneliti.")
    if not bool(row["target_active"]):
        raise LinkRevokedError("Akun penilai untuk tautan ini sudah dinonaktifkan.")

    link_id = int(row["link_id"])
    cookie_key = task_device_cookie_name(link_id)
    new_device_secret = verify_or_claim_device(
        conn,
        table="public_task_link",
        link_id=link_id,
        cookie_key=cookie_key,
        existing_claim=row["claimed_device_hash"],
        lock_single_device=bool(row["lock_single_device"]),
        device_cookies=device_cookies,
    )

    effective_submitted = row["submitted_at"] or row["reviewer_submitted_at"]
    return {
        "link_id": link_id,
        "cookie_name": cookie_key,
        "new_device_secret": new_device_secret,
        "task_kind": str(row["task_kind"]),
        "target_user_id": int(row["target_user_id"]),
        "target_username": str(row["target_username"]),
        "target_version": row["target_version"],
        "target_slot": int(row["target_slot"]) if row["target_slot"] is not None else None,
        "label": str(row["label"]),
        "lock_single_device": bool(row["lock_single_device"]),
        "submitted_at": effective_submitted,
    }


def mark_task_link_submitted(
    conn: sqlite3.Connection,
    *,
    link_id: int,
    target_user_id: int,
    task_kind: str,
    submitted_at: Optional[str] = None,
) -> str:
    """Kunci tautan setelah penyerahan final dan catat ke log aktivitas."""
    now = submitted_at or _now()
    with conn:
        conn.execute(
            "UPDATE public_task_link SET submitted_at = COALESCE(submitted_at, ?) WHERE id = ?",
            (now, link_id),
        )
        _log(
            conn,
            target_user_id,
            "public_task_link_submitted",
            {"link_id": link_id, "task_kind": task_kind},
            now,
        )
    return now
