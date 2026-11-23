"""Endpoint admin untuk ringkasan kesepakatan penilai dan ekspor laporan."""

import json
import sqlite3

from flask import Response, abort, request

from services.agreement_summary import build_agreement_report
from webapp.api import api, success
from webapp.api.session import require_api_role
from webapp.database import db


def _parse_optional_int(param_name: str):
    raw = request.args.get(param_name)
    if raw is None or raw == "":
        return None
    if not raw.isdecimal():
        abort(400, description=f"Parameter {param_name} harus berupa bilangan bulat positif.")
    value = int(raw)
    if value <= 0:
        abort(400, description=f"Parameter {param_name} harus bernilai lebih dari 0.")
    return value


def _build_report_from_request():
    version = request.args.get("version") or None
    rater1_id = _parse_optional_int("audit_rater1")
    rater2_id = _parse_optional_int("audit_rater2")
    try:
        return build_agreement_report(
            db(),
            version=version,
            rater1_id=rater1_id,
            rater2_id=rater2_id,
        )
    except ValueError as error:
        abort(400, description=str(error))
    except sqlite3.Error:
        abort(500, description="Ringkasan kesepakatan belum dapat dihitung.")


@api.get("/research/agreement")
@require_api_role("admin")
def get_research_agreement():
    report = _build_report_from_request()
    response, status = success(report)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.get("/research/agreement/export")
@require_api_role("admin")
def export_research_agreement():
    report = _build_report_from_request()
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    response = Response(payload, mimetype="application/json; charset=utf-8")
    response.headers["Content-Disposition"] = 'attachment; filename="ringkasan-kesepakatan.json"'
    response.headers["Cache-Control"] = "no-store"
    return response
