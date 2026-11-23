"""Endpoint admin untuk tinjauan kualitas metadata dan status kamus SPM [PM-23]."""

import sqlite3

from flask import abort, request

from services.metadata_quality import get_metadata_quality_summary
from webapp.api import api, success
from webapp.api.session import require_api_role
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


@api.get("/research/quality")
@require_api_role("admin")
def get_research_quality():
    issue_type = request.args.get("issue_type") or None
    field_name = request.args.get("field_name") or None
    spm_confidence = request.args.get("spm_confidence") or None
    page = _parse_positive_int("page", 1)
    per_page = _parse_positive_int("per_page", 25)

    try:
        data = get_metadata_quality_summary(
            db(),
            issue_type=issue_type,
            field_name=field_name,
            spm_confidence=spm_confidence,
            page=page,
            per_page=per_page,
        )
    except ValueError as error:
        abort(400, description=str(error))
    except sqlite3.Error:
        abort(500, description="Ringkasan kualitas metadata belum dapat dimuat.")

    response, status = success(data)
    response.headers["Cache-Control"] = "no-store"
    return response, status
