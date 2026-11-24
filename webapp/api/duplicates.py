"""Endpoint admin untuk tinjauan pasangan kandidat duplikat non-destruktif [PM-24]."""

import sqlite3

from flask import abort, request
from flask_login import current_user

from services.duplicate_review import list_duplicate_candidates, save_duplicate_decision
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db


def _parse_positive_int(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    if not raw.isdecimal():
        abort(400, description=f"Parameter {name} harus berupa bilangan bulat positif.")
    value = int(raw)
    if value < 1:
        abort(400, description=f"Parameter {name} harus bernilai minimal 1.")
    return value


@api.get("/research/duplicates")
@require_api_role("admin")
def get_research_duplicates():
    reason = request.args.get("reason") or None
    status = request.args.get("status") or None
    page = _parse_positive_int("page", 1)
    per_page = _parse_positive_int("per_page", 20)

    try:
        data = list_duplicate_candidates(
            db(),
            reason=reason,
            status=status,
            page=page,
            per_page=per_page,
        )
    except ValueError as error:
        abort(400, description=str(error))
    except sqlite3.Error:
        abort(500, description="Daftar kandidat duplikat belum dapat dimuat.")

    response, code = success(data)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.put("/research/duplicates/<int:archive_a_id>/<int:archive_b_id>")
@require_api_role("admin")
def update_duplicate_decision(archive_a_id: int, archive_b_id: int):
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim objek JSON keputusan tinjauan duplikat.")

    decision = payload.get("decision")
    notes = payload.get("notes", "")
    if not isinstance(decision, str) or not isinstance(notes, str):
        abort(422, description="Keputusan dan catatan harus berupa teks.")

    try:
        saved = save_duplicate_decision(
            db(),
            archive_a_id=archive_a_id,
            archive_b_id=archive_b_id,
            decision=decision,
            notes=notes,
            actor_id=int(current_user.id),
        )
    except LookupError as error:
        abort(404, description=str(error))
    except ValueError as error:
        abort(422, description=str(error))
    except sqlite3.Error:
        abort(500, description="Keputusan duplikat belum dapat disimpan.")

    response, code = success(saved)
    response.headers["Cache-Control"] = "no-store"
    return response, code
