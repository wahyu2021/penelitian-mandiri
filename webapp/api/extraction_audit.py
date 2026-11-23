"""Audit ekstraksi per penilai dan konfirmasi manual kamus SPM."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Response, abort, current_app, request
from flask_login import current_user

from services.audit_review import (
    FIELDS, can_review, export_completed_csv, load_sample, reviewer_state, save_judgment,
)
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role, require_api_user
from webapp.database import db


def _sample():
    try:
        return load_sample(
            Path(current_app.config["AUDIT_SAMPLE_CSV"]),
            Path(current_app.config["AUDIT_MANIFEST"]),
        )
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError):
        abort(409, description="Sampel audit atau manifest belum tersedia atau tidak valid.")


def _require_reviewer():
    try:
        allowed = can_review(db(), int(current_user.id), current_user.role)
    except sqlite3.Error:
        abort(500, description="Skema audit belum siap. Jalankan db upgrade.")
    if not allowed:
        abort(403, description="Akun belum ditugaskan menilai audit ekstraksi.")


@api.get("/extraction-audit")
@require_api_user
def audit_state():
    _require_reviewer()
    raw_index = request.args.get("index", "0")
    if not raw_index.isdecimal():
        abort(400, description="Nomor sampel tidak valid.")
    try:
        result = reviewer_state(db(), _sample(), int(current_user.id), int(raw_index))
    except IndexError:
        abort(404, description="Sampel tidak ditemukan.")
    except ValueError as error:
        abort(409, description=str(error))
    except sqlite3.Error:
        abort(500, description="Skema audit belum siap. Jalankan db upgrade.")
    response, status = success(result)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.patch("/extraction-audit/<int:archive_id>/fields/<field>")
@require_api_user
def audit_field(archive_id, field):
    _require_reviewer()
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict) or field not in FIELDS:
        abort(400, description="Isian audit tidak valid.")
    verdict = payload.get("verdict")
    note = payload.get("note", "")
    fingerprint = payload.get("fingerprint")
    if (verdict is not None and not isinstance(verdict, str)
            or not isinstance(note, str) or len(note) > 1000
            or not isinstance(fingerprint, str)):
        abort(422, description="Verdict, catatan, atau versi sampel tidak valid.")
    sample = _sample()
    if fingerprint != sample["fingerprint"]:
        abort(409, description="Sampel berubah. Muat ulang halaman audit.")
    try:
        changed = save_judgment(db(), sample, int(current_user.id), archive_id,
                                field, verdict, note.strip())
    except LookupError:
        abort(404, description="Arsip tidak ada dalam sampel audit.")
    except ValueError as error:
        abort(422, description=str(error))
    except sqlite3.Error:
        abort(500, description="Penilaian belum dapat disimpan.")
    response, status = success({"saved": changed})
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.get("/extraction-audit/export")
@require_api_user
def export_audit():
    _require_reviewer()
    try:
        csv_text = export_completed_csv(db(), _sample(), int(current_user.id))
    except ValueError as error:
        abort(409, description=str(error))
    except sqlite3.Error:
        abort(500, description="Ekspor audit belum tersedia.")
    response = Response(csv_text, mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = (
        f'attachment; filename="audit-ekstraksi-web-penilai-{current_user.id}.csv"'
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/extraction-audit/reviewers")
@require_api_role("admin")
def audit_reviewers():
    try:
        rows = db().execute(
            """SELECT u.id, u.username, u.role, u.is_active,
                      a.assigned_at, a.assigned_by
               FROM user u LEFT JOIN extraction_audit_assignment a ON a.user_id = u.id
               WHERE u.role = 'petugas' ORDER BY u.username"""
        ).fetchall()
    except sqlite3.Error:
        abort(500, description="Daftar petugas belum tersedia.")
    return success([dict(row) for row in rows])


def _change_assignment(user_id: int, assigned: bool):
    _check_csrf_header()
    connection = db()
    target = connection.execute(
        "SELECT role, is_active FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    if not target or target["role"] != "petugas" or not target["is_active"]:
        abort(404, description="Akun petugas aktif tidak ditemukan.")
    now = datetime.now(timezone.utc).isoformat()
    with connection:
        if assigned:
            connection.execute(
                """INSERT OR IGNORE INTO extraction_audit_assignment
                   (user_id, assigned_by, assigned_at) VALUES (?, ?, ?)""",
                (user_id, current_user.id, now),
            )
        else:
            connection.execute("DELETE FROM extraction_audit_assignment WHERE user_id = ?", (user_id,))
        connection.execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (current_user.id, "audit_reviewer_assigned" if assigned else "audit_reviewer_revoked",
             json.dumps({"reviewer_id": user_id}), now),
        )
    return success({"user_id": user_id, "assigned": assigned})


@api.put("/extraction-audit/reviewers/<int:user_id>")
@require_api_role("admin")
def assign_reviewer(user_id):
    return _change_assignment(user_id, True)


@api.delete("/extraction-audit/reviewers/<int:user_id>")
@require_api_role("admin")
def revoke_reviewer(user_id):
    return _change_assignment(user_id, False)


@api.get("/spm-types")
@require_api_role("admin")
def spm_types():
    rows = db().execute(
        """SELECT s.code, s.label, s.confidence, s.source_note,
                  s.confirmed_by, s.confirmed_at, COUNT(m.archive_id) AS archive_count
           FROM spm_type s LEFT JOIN archive_metadata m ON m.spm_type_code = s.code
           GROUP BY s.code ORDER BY s.code"""
    ).fetchall()
    return success([dict(row) for row in rows])


@api.post("/spm-types/<code>/confirm")
@require_api_role("admin")
def confirm_spm_type(code):
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    label = payload.get("label") if isinstance(payload, dict) else None
    evidence = payload.get("source_note") if isinstance(payload, dict) else None
    if (not isinstance(label, str) or not 2 <= len(label.strip()) <= 120
            or not isinstance(evidence, str) or not 10 <= len(evidence.strip()) <= 1000):
        abort(422, description="Label dan catatan sumber konfirmasi wajib diisi.")
    connection = db()
    existing = connection.execute(
        "SELECT confidence FROM spm_type WHERE code = ?", (code,)
    ).fetchone()
    if not existing:
        abort(404, description="Kode SPM tidak ditemukan.")
    if existing["confidence"] != "dugaan":
        abort(409, description="Kode SPM sudah dikonfirmasi.")
    now = datetime.now(timezone.utc).isoformat()
    with connection:
        changed = connection.execute(
            """UPDATE spm_type SET label = ?, confidence = 'terkonfirmasi',
               source_note = ?, confirmed_by = ?, confirmed_at = ?
               WHERE code = ? AND confidence = 'dugaan'""",
            (label.strip(), evidence.strip(), current_user.username, now, code),
        )
        if changed.rowcount != 1:
            abort(409, description="Kode SPM sudah dikonfirmasi.")
        connection.execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (current_user.id, "spm_type_confirmed", json.dumps({"code": code}), now),
        )
    return success({"code": code, "label": label.strip(), "confidence": "terkonfirmasi",
                    "source_note": evidence.strip(), "confirmed_by": current_user.username,
                    "confirmed_at": now})
