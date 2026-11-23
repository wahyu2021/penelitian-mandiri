"""API penilaian relevansi untuk admin dan akun yang ditugaskan."""

from functools import wraps

from flask import Response, abort, request
from flask_login import current_user
from werkzeug.exceptions import RequestEntityTooLarge

from services import relevance_review as reviews
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role, require_api_user
from webapp.database import db


def _review_endpoint(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except reviews.ReviewConflict as error:
            abort(409, description=str(error))
        except reviews.ReviewForbidden as error:
            abort(403, description=str(error))
        except LookupError as error:
            abort(404, description=str(error))
        except ValueError as error:
            abort(422, description=str(error))
    return wrapped


def _json(data, status=200):
    response, status = success(data, status)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def _csv():
    request.max_content_length = 8 * 1024 * 1024
    try:
        return request.get_data(cache=False)
    except RequestEntityTooLarge:
        abort(413, description="Berkas CSV melebihi 8 MiB.")


def _account_arg(key):
    value = request.args.get(key, "")
    if not value.isascii() or not value.isdecimal() or not 1 <= len(value) <= 18 or int(value) < 1:
        abort(400, description="Pilih akun penilai yang valid.")
    return int(value)


def _validate_slot(slot):
    if slot not in (1, 2):
        abort(404, description="Penilai tidak ditemukan.")


@api.get("/relevance-admin")
@require_api_role("admin")
@_review_endpoint
def relevance_admin():
    return _json(reviews.admin_overview(db()))


@api.post("/relevance-admin/<version>")
@require_api_role("admin")
@_review_endpoint
def setup_relevance(version):
    _check_csrf_header()
    return _json(reviews.create_review(
        db(), version, _account_arg("first"), _account_arg("second"), _csv(), current_user.id,
    ), 201)


@api.post("/relevance-admin/<version>/<int:slot>/migration")
@require_api_role("admin")
@_review_endpoint
def relevance_migration(version, slot):
    _check_csrf_header()
    _validate_slot(slot)
    return _json(reviews.migrate_legacy(db(), version, slot, _csv(), current_user.id))


@api.get("/relevance-admin/<version>/<int:slot>/export")
@require_api_role("admin")
@_review_endpoint
def relevance_export(version, slot):
    _validate_slot(slot)
    response = Response(reviews.export_review(db(), version, slot), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="relevansi-{version}-penilai-{slot}.csv"'
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/relevance-reviews")
@require_api_user
@_review_endpoint
def relevance_assignments():
    return _json(reviews.assigned_reviews(db(), current_user.id))


@api.get("/relevance-reviews/<version>")
@require_api_user
@_review_endpoint
def relevance_item(version):
    index = request.args.get("index")
    if index is not None and (not index.isascii() or not index.isdecimal() or len(index) > 4):
        abort(400, description="Nomor pasangan tidak valid.")
    return _json(reviews.reviewer_item(db(), version, current_user.id, None if index is None else int(index)))


@api.put("/relevance-reviews/<version>/<int:pair>")
@require_api_user
@_review_endpoint
def relevance_answer(version, pair):
    _check_csrf_header()
    request.max_content_length = 16 * 1024
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"revision", "is_relevant", "ragu", "notes"}:
        abort(400, description="Isian penilaian belum lengkap.")
    decision, doubt, notes, revision = data["is_relevant"], data["ragu"], data["notes"], data["revision"]
    if ((decision is not None and (type(decision) is not int or decision not in (0, 1)))
            or type(doubt) is not bool or not isinstance(notes, str) or len(notes) > 1000
            or type(revision) is not int or revision < 0):
        abort(422, description="Keputusan, keraguan, catatan, atau revisi tidak valid.")
    return _json(reviews.save_answer(
        db(), version, pair, current_user.id, revision, (decision, doubt, notes.strip()),
    ))


@api.post("/relevance-reviews/<version>/submit")
@require_api_user
@_review_endpoint
def relevance_submit(version):
    _check_csrf_header()
    return _json(reviews.submit_review(db(), version, current_user.id))
