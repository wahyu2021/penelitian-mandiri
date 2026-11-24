"""Endpoint admin & publik untuk tautan 1-perangkat penilaian relevansi dan audit ekstraksi [PM-29]."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from flask import abort, current_app, request
from flask_login import current_user

from services import audit_review as audit_svc
from services import relevance_review as reviews
from services.public_tasks import (
    DeviceClaimError,
    LinkConflictError,
    LinkRevokedError,
    create_task_link,
    list_task_links,
    mark_task_link_submitted,
    reset_task_link_device,
    resolve_task_link,
    revoke_task_link,
)
from webapp.api import api, success
from webapp.api.public_forms import _attach_device_cookie
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db


def _no_store(data: Any, status: int = 200):
    response, code = success(data, status)
    response.headers["Cache-Control"] = "no-store"
    return response, code


def _no_store_with_cookie(data: Any, link: Dict[str, Any], status: int = 200):
    response, code = _no_store(data, status)
    if link.get("new_device_secret"):
        _attach_device_cookie(response, link["cookie_name"], link["new_device_secret"])
    return response, code


def _link_summary(link: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "label": link["label"],
        "target_username": link["target_username"],
        "target_version": link["target_version"],
        "target_slot": link["target_slot"],
        "lock_single_device": link["lock_single_device"],
        "submitted_at": link["submitted_at"],
    }


def _audit_sample():
    try:
        return audit_svc.load_sample(
            Path(current_app.config["AUDIT_SAMPLE_CSV"]),
            Path(current_app.config["AUDIT_MANIFEST"]),
        )
    except (FileNotFoundError, ValueError, OSError):
        abort(409, description="Sampel audit atau manifest belum tersedia atau tidak valid.")


def _resolve_or_abort(token: str, expected_kind: str) -> Dict[str, Any]:
    try:
        return resolve_task_link(
            db(),
            raw_token=token,
            expected_kind=expected_kind,
            device_cookies=request.cookies,
        )
    except LookupError as error:
        abort(404, description=str(error))
    except LinkRevokedError as error:
        abort(410, description=str(error))
    except DeviceClaimError as error:
        abort(403, description=str(error))


@api.get("/research/task-links")
@require_api_role("admin")
def admin_list_task_links():
    task_kind = request.args.get("task_kind") or None
    version = request.args.get("version") or None
    try:
        items = list_task_links(db(), task_kind=task_kind, version=version)
    except ValueError as error:
        abort(400, description=str(error))
    except sqlite3.Error:
        abort(500, description="Daftar tautan tugas belum tersedia.")
    return _no_store(items)


@api.post("/research/task-links")
@require_api_role("admin")
def admin_create_task_link():
    _check_csrf_header()
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict):
        abort(400, description="Kirim objek JSON pembuatan tautan tugas.")

    raw_slot = payload.get("slot")
    slot: Optional[int] = raw_slot if isinstance(raw_slot, int) and not isinstance(raw_slot, bool) else None
    raw_uid = payload.get("user_id")
    user_id: Optional[int] = raw_uid if isinstance(raw_uid, int) and not isinstance(raw_uid, bool) else None

    try:
        created = create_task_link(
            db(),
            task_kind=str(payload.get("task_kind") or ""),
            actor_id=int(current_user.id),
            version=str(payload["version"]) if payload.get("version") is not None else None,
            slot=slot,
            user_id=user_id,
            label=str(payload.get("label") or ""),
            lock_single_device=bool(payload.get("lock_single_device", True)),
        )
    except LookupError as error:
        abort(404, description=str(error))
    except LinkConflictError as error:
        abort(409, description=str(error))
    except ValueError as error:
        abort(422, description=str(error))
    except sqlite3.Error:
        abort(500, description="Tautan tugas belum dapat dibuat.")
    return _no_store(created, 201)


@api.post("/research/task-links/<int:link_id>/reset-device")
@require_api_role("admin")
def admin_reset_task_link_device(link_id: int):
    _check_csrf_header()
    try:
        result = reset_task_link_device(db(), link_id=link_id, actor_id=int(current_user.id))
    except LookupError as error:
        abort(404, description=str(error))
    return _no_store(result)


@api.post("/research/task-links/<int:link_id>/revoke")
@require_api_role("admin")
def admin_revoke_task_link(link_id: int):
    _check_csrf_header()
    try:
        result = revoke_task_link(db(), link_id=link_id, actor_id=int(current_user.id))
    except LookupError as error:
        abort(404, description=str(error))
    return _no_store(result)


@api.get("/public/tasks/<token>/relevance")
def public_get_relevance(token: str):
    index = request.args.get("index")
    if index is not None and (not index.isascii() or not index.isdecimal() or len(index) > 4):
        abort(400, description="Nomor pasangan tidak valid.")
    link = _resolve_or_abort(token, "relevance")
    try:
        state = reviews.reviewer_item(
            db(),
            str(link["target_version"]),
            int(link["target_user_id"]),
            None if index is None else int(index),
        )
    except reviews.ReviewForbidden as error:
        abort(403, description=str(error))
    except LookupError as error:
        abort(404, description=str(error))
    return _no_store_with_cookie({"link": _link_summary(link), "review": state}, link)


@api.put("/public/tasks/<token>/relevance/<int:pair_id>")
def public_save_relevance(token: str, pair_id: int):
    link = _resolve_or_abort(token, "relevance")
    if link["submitted_at"] is not None:
        abort(409, description="Penilaian pada tautan ini sudah diserahkan dan dikunci.")
    request.max_content_length = 16 * 1024
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"revision", "is_relevant", "ragu", "notes"}:
        abort(400, description="Isian penilaian belum lengkap.")
    decision, doubt, notes, revision = data["is_relevant"], data["ragu"], data["notes"], data["revision"]
    if (
        (decision is not None and (type(decision) is not int or decision not in (0, 1)))
        or type(doubt) is not bool
        or not isinstance(notes, str)
        or len(notes) > 1000
        or type(revision) is not int
        or revision < 0
    ):
        abort(422, description="Keputusan, keraguan, catatan, atau revisi tidak valid.")

    try:
        saved = reviews.save_answer(
            db(),
            str(link["target_version"]),
            pair_id,
            int(link["target_user_id"]),
            revision,
            (decision, doubt, notes.strip()),
        )
    except reviews.ReviewConflict as error:
        abort(409, description=str(error))
    except reviews.ReviewForbidden as error:
        abort(403, description=str(error))
    except LookupError as error:
        abort(404, description=str(error))
    return _no_store_with_cookie(saved, link)


@api.post("/public/tasks/<token>/relevance/submit")
def public_submit_relevance(token: str):
    link = _resolve_or_abort(token, "relevance")
    if link["submitted_at"] is not None:
        abort(409, description="Penilaian pada tautan ini sudah diserahkan dan dikunci.")
    try:
        result = reviews.submit_review(
            db(),
            str(link["target_version"]),
            int(link["target_user_id"]),
        )
    except reviews.ReviewConflict as error:
        abort(409, description=str(error))
    except reviews.ReviewForbidden as error:
        abort(403, description=str(error))

    mark_task_link_submitted(
        db(),
        link_id=int(link["link_id"]),
        target_user_id=int(link["target_user_id"]),
        task_kind="relevance",
        submitted_at=result["submitted_at"],
    )
    return _no_store_with_cookie(result, link)


@api.get("/public/tasks/<token>/audit")
def public_get_audit(token: str):
    raw_index = request.args.get("index", "0")
    if not raw_index.isdecimal():
        abort(400, description="Nomor sampel tidak valid.")
    link = _resolve_or_abort(token, "extraction_audit")
    try:
        state = audit_svc.reviewer_state(
            db(),
            _audit_sample(),
            int(link["target_user_id"]),
            int(raw_index),
        )
    except IndexError:
        abort(404, description="Sampel tidak ditemukan.")
    except ValueError as error:
        abort(409, description=str(error))
    return _no_store_with_cookie({"link": _link_summary(link), "audit": state}, link)


@api.patch("/public/tasks/<token>/audit/<int:archive_id>/fields/<field>")
def public_save_audit_field(token: str, archive_id: int, field: str):
    link = _resolve_or_abort(token, "extraction_audit")
    if link["submitted_at"] is not None:
        abort(409, description="Audit pada tautan ini sudah diserahkan dan dikunci.")
    payload = request.get_json(silent=True) if request.is_json else None
    if not isinstance(payload, dict) or field not in audit_svc.FIELDS:
        abort(400, description="Isian audit tidak valid.")
    verdict = payload.get("verdict")
    note = payload.get("note", "")
    fingerprint = payload.get("fingerprint")
    if (
        (verdict is not None and not isinstance(verdict, str))
        or not isinstance(note, str)
        or len(note) > 1000
        or not isinstance(fingerprint, str)
    ):
        abort(422, description="Verdict, catatan, atau versi sampel tidak valid.")
    sample = _audit_sample()
    if fingerprint != sample["fingerprint"]:
        abort(409, description="Sampel berubah. Muat ulang halaman audit.")
    try:
        changed = audit_svc.save_judgment(
            db(),
            sample,
            int(link["target_user_id"]),
            archive_id,
            field,
            verdict,
            note.strip(),
        )
    except LookupError:
        abort(404, description="Arsip tidak ada dalam sampel audit.")
    except ValueError as error:
        abort(422, description=str(error))
    return _no_store_with_cookie({"saved": changed}, link)


@api.post("/public/tasks/<token>/audit/submit")
def public_submit_audit(token: str):
    link = _resolve_or_abort(token, "extraction_audit")
    if link["submitted_at"] is not None:
        abort(409, description="Audit pada tautan ini sudah diserahkan dan dikunci.")
    try:
        state = audit_svc.reviewer_state(db(), _audit_sample(), int(link["target_user_id"]), 0)
    except ValueError as error:
        abort(409, description=str(error))
    if not state["final"]:
        abort(409, description="Nilai seluruh sel sampel audit sebelum menyerahkan hasil final.")

    submitted_at = mark_task_link_submitted(
        db(),
        link_id=int(link["link_id"]),
        target_user_id=int(link["target_user_id"]),
        task_kind="extraction_audit",
    )
    return _no_store_with_cookie({"submitted_at": submitted_at}, link)
