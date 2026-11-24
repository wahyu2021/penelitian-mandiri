"""Endpoint admin & publik untuk formulir kuesioner tautan kunci 1 perangkat [PM-28]."""

import json
import sqlite3

from flask import Response, abort, current_app, request
from flask_login import current_user

from services.public_forms import (
    DeviceClaimError,
    LinkConflictError,
    LinkRevokedError,
    create_form,
    create_public_link,
    export_form_responses_csv,
    get_form_detail,
    list_forms,
    reset_link_device,
    resolve_public_link,
    revoke_link,
    submit_public_form,
)
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db


def _attach_device_cookie(response, cookie_name: str, device_secret: str) -> None:
    response.set_cookie(
        cookie_name,
        device_secret,
        httponly=True,
        samesite="Lax",
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
        path="/",
        max_age=30 * 24 * 60 * 60,
    )


@api.get("/research/forms")
@require_api_role("admin")
def admin_list_forms():
    try:
        data = list_forms(db())
    except sqlite3.Error:
        abort(500, description="Daftar formulir belum tersedia.")
    response, code = success(data)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.post("/research/forms")
@require_api_role("admin")
def admin_create_form():
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim objek JSON formulir.")
    try:
        created = create_form(
            db(),
            title=str(payload.get("title") or ""),
            description=str(payload.get("description") or ""),
            form_kind=str(payload.get("form_kind") or ""),
            questions=payload.get("questions"),
            actor_id=int(current_user.id),
        )
    except ValueError as error:
        abort(422, description=str(error))
    except sqlite3.Error:
        abort(500, description="Formulir belum dapat disimpan.")
    response, code = success(created, 201)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.get("/research/forms/<int:form_id>")
@require_api_role("admin")
def admin_form_detail(form_id: int):
    try:
        detail = get_form_detail(db(), form_id)
    except LookupError as error:
        abort(404, description=str(error))
    except sqlite3.Error:
        abort(500, description="Detail formulir belum tersedia.")
    response, code = success(detail)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.post("/research/forms/<int:form_id>/links")
@require_api_role("admin")
def admin_create_form_link(form_id: int):
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim objek JSON pembuatan tautan.")
    try:
        created = create_public_link(
            db(),
            form_id=form_id,
            participant_code=str(payload.get("participant_code") or ""),
            participant_role=str(payload.get("participant_role") or "petugas"),
            lock_single_device=bool(payload.get("lock_single_device", True)),
            actor_id=int(current_user.id),
        )
    except LookupError as error:
        abort(404, description=str(error))
    except ValueError as error:
        abort(422, description=str(error))
    except sqlite3.Error:
        abort(500, description="Tautan belum dapat dibuat.")
    response, code = success(created, 201)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.post("/research/forms/links/<int:link_id>/reset-device")
@require_api_role("admin")
def admin_reset_form_link_device(link_id: int):
    _check_csrf_header()
    try:
        res = reset_link_device(db(), link_id=link_id, actor_id=int(current_user.id))
    except LookupError as error:
        abort(404, description=str(error))
    response, code = success(res)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.post("/research/forms/links/<int:link_id>/revoke")
@require_api_role("admin")
def admin_revoke_form_link(link_id: int):
    _check_csrf_header()
    try:
        res = revoke_link(db(), link_id=link_id, actor_id=int(current_user.id))
    except LookupError as error:
        abort(404, description=str(error))
    response, code = success(res)
    response.headers["Cache-Control"] = "no-store"
    return response, code


@api.get("/research/forms/<int:form_id>/export")
@require_api_role("admin")
def admin_export_form_responses(form_id: int):
    fmt = (request.args.get("format") or "csv").strip().lower()
    if fmt not in ("csv", "json"):
        abort(400, description="Format ekspor harus 'csv' atau 'json'.")
    try:
        if fmt == "csv":
            csv_text = export_form_responses_csv(db(), form_id)
            response = Response(csv_text, mimetype="text/csv; charset=utf-8")
            response.headers["Content-Disposition"] = f'attachment; filename="formulir-{form_id}-jawaban.csv"'
        else:
            detail = get_form_detail(db(), form_id)
            response = Response(
                json.dumps(detail, indent=2, ensure_ascii=False),
                mimetype="application/json; charset=utf-8",
            )
            response.headers["Content-Disposition"] = f'attachment; filename="formulir-{form_id}-jawaban.json"'
    except LookupError as error:
        abort(404, description=str(error))
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/public/forms/<token>")
def public_get_form(token: str):
    try:
        resolved = resolve_public_link(db(), raw_token=token, device_cookies=request.cookies)
    except LookupError as error:
        abort(404, description=str(error))
    except LinkRevokedError as error:
        abort(410, description=str(error))
    except DeviceClaimError as error:
        abort(403, description=str(error))

    new_secret = resolved.pop("new_device_secret", None)
    cookie_name = resolved.pop("cookie_name")
    resolved.pop("link_id", None)
    response, code = success(resolved)
    response.headers["Cache-Control"] = "no-store"
    if new_secret:
        _attach_device_cookie(response, cookie_name, new_secret)
    return response, code


@api.post("/public/forms/<token>/submit")
def public_submit_form(token: str):
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim jawaban formulir dalam format JSON.")
    try:
        result = submit_public_form(
            db(),
            raw_token=token,
            device_cookies=request.cookies,
            raw_answers=payload.get("answers"),
        )
    except LookupError as error:
        abort(404, description=str(error))
    except LinkRevokedError as error:
        abort(410, description=str(error))
    except DeviceClaimError as error:
        abort(403, description=str(error))
    except LinkConflictError as error:
        abort(409, description=str(error))
    except ValueError as error:
        abort(422, description=str(error))

    new_secret = result.pop("new_device_secret", None)
    cookie_name = result.pop("cookie_name")
    response, code = success(result, 201)
    response.headers["Cache-Control"] = "no-store"
    if new_secret:
        _attach_device_cookie(response, cookie_name, new_secret)
    return response, code
