"""Endpoint admin untuk melihat dan mengekspor run evaluasi penelitian [PM-20]."""

import json
from pathlib import Path

from flask import Response, abort, current_app, request

from services.evaluation_runs import export_evaluation_csv, load_evaluation_run
from webapp.api import api, success
from webapp.api.session import require_api_role


def _parse_positive_int(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    if not raw.isdecimal():
        abort(400, description=f"Parameter {name} harus berupa bilangan bulat positif.")
    val = int(raw)
    if val < 1:
        abort(400, description=f"Parameter {name} harus bernilai minimal 1.")
    return val


@api.get("/research/evaluation")
@require_api_role("admin")
def get_research_evaluation():
    split = (request.args.get("split") or "test").strip()
    method = request.args.get("method") or None
    config = request.args.get("config") or None
    query_type = request.args.get("query_type") or None
    noise_type = request.args.get("noise_type") or None
    source = request.args.get("source") or None
    page = _parse_positive_int("page", 1)
    per_page = _parse_positive_int("per_page", 25)

    try:
        data = load_evaluation_run(
            Path(current_app.config["EVALUATION_BUNDLE_DIR"]),
            split=split,
            method=method,
            config=config,
            query_type=query_type,
            noise_type=noise_type,
            source=source,
            page=page,
            per_page=per_page,
        )
    except ValueError as error:
        abort(400, description=str(error))

    response, status = success(data)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@api.get("/research/evaluation/export")
@require_api_role("admin")
def export_research_evaluation():
    split = (request.args.get("split") or "test").strip()
    fmt = (request.args.get("format") or "json").strip().lower()
    if fmt not in ("json", "csv"):
        abort(400, description="Format ekspor harus 'json' atau 'csv'.")

    bundle_dir = Path(current_app.config["EVALUATION_BUNDLE_DIR"])
    if fmt == "csv":
        try:
            csv_text = export_evaluation_csv(bundle_dir, split=split)
        except FileNotFoundError as error:
            abort(404, description=str(error))
        except ValueError as error:
            abort(400, description=str(error))
        response = Response(csv_text, mimetype="text/csv; charset=utf-8")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="evaluasi-run-{split}.csv"'
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    try:
        payload = load_evaluation_run(bundle_dir, split=split, page=1, per_page=100)
    except ValueError as error:
        abort(400, description=str(error))

    response = Response(
        json.dumps(payload, indent=2, ensure_ascii=False),
        mimetype="application/json; charset=utf-8",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="evaluasi-run-{split}.json"'
    response.headers["Cache-Control"] = "no-store"
    return response
