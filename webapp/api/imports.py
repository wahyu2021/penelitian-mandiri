"""Daftar, pratinjau, dan eksekusi impor dump oleh admin."""

import json
import re
import sqlite3
from pathlib import Path

from flask import abort, current_app, request
from flask_login import current_user

from services.web_import import import_source, list_sources, preview_source
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db, log_action

SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _source_dir() -> Path:
    directory = current_app.config["IMPORT_SOURCE_DIR"]
    if directory is None:
        abort(409, description="Direktori impor belum diatur oleh pengelola aplikasi.")
    path = Path(directory)
    if not path.is_dir():
        abort(409, description="Direktori impor tidak tersedia pada komputer ini.")
    return path


@api.get("/imports")
@require_api_role("admin")
def import_overview():
    directory = current_app.config["IMPORT_SOURCE_DIR"]
    sources = list_sources(Path(directory)) if directory is not None and Path(directory).is_dir() else []
    try:
        rows = db().execute(
            """SELECT id, source_filename, source_sha256, parser_version, extractor_version,
                      raw_count, clean_count, issue_count, status, imported_by, imported_at
               FROM import_batch ORDER BY id DESC LIMIT 20"""
        ).fetchall()
    except sqlite3.Error:
        abort(500, description="Riwayat impor belum dapat dibaca.")
    response, status = success({
        "configured": directory is not None and Path(directory).is_dir(),
        "verify_reference_counts": current_app.config["IMPORT_VERIFY_REFERENCE_COUNTS"],
        "sources": sources,
        "history": [dict(row) for row in rows],
    })
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.get("/imports/preview")
@require_api_role("admin")
def import_preview():
    source = request.args.get("source", "")
    try:
        preview = preview_source(_source_dir(), source)
    except (ValueError, OSError) as error:
        abort(422, description=str(error) if isinstance(error, ValueError) else "Dump tidak dapat dibaca.")
    response, status = success(preview)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.post("/imports")
@require_api_role("admin")
def execute_import():
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim pilihan dump dan hash pratinjau sebagai JSON.")
    source = payload.get("source")
    digest = payload.get("source_sha256")
    if not isinstance(source, str) or not isinstance(digest, str) or not SHA256.fullmatch(digest):
        abort(422, description="Pilihan dump atau hash pratinjau tidak valid.")
    directory = _source_dir()
    db_path = Path(current_app.config["DATABASE"])
    backup_dir = current_app.config["IMPORT_BACKUP_DIR"] or db_path.parent / "backups"
    try:
        result = import_source(
            directory, source, digest, db_path, Path(backup_dir),
            current_user.username, current_app.config["IMPORT_VERIFY_REFERENCE_COUNTS"],
            audit_user_id=current_user.id,
        )
    except ValueError as error:
        log_action("import_failed", user_id=current_user.id,
                   detail=json.dumps({"source": source, "reason": "invalid_dump"}))
        abort(422, description=str(error))
    except (OSError, sqlite3.Error):
        log_action("import_failed", user_id=current_user.id,
                   detail=json.dumps({"source": source, "reason": "system_error"}))
        abort(500, description="Impor gagal. Data sebelumnya tetap tersedia.")
    response, status = success(result, 201)
    response.headers["Cache-Control"] = "no-store"
    return response, status
