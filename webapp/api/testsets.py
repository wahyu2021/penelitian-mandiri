"""API admin untuk meninjau, mengunci, dan mengunduh versi set uji."""

import json
import re
from functools import wraps

from flask import Response, abort, request
from flask_login import current_user
from werkzeug.exceptions import RequestEntityTooLarge

from services import testset_versions
from webapp.api import api, success
from webapp.api.session import _check_csrf_header, require_api_role
from webapp.database import db


def _testset_endpoint(view):
    @wraps(view)
    @require_api_role("admin")
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except testset_versions.VersionConflict as error:
            abort(409, description=str(error))
        except LookupError as error:
            abort(404, description=str(error))
        except ValueError as error:
            abort(422, description=str(error))

    return wrapped


def _json(data, status=200):
    response, status = success(data, status)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def _read_upload():
    request.max_content_length = 4 * 1024 * 1024
    try:
        raw = request.get_json(silent=True)
    except RequestEntityTooLarge:
        abort(413, description="Berkas set uji melebihi 4 MiB.")
    except RecursionError:
        abort(400, description="Struktur JSON terlalu dalam.")
    if not isinstance(raw, dict):
        abort(400, description="Kirim berkas set uji berupa objek JSON.")
    return raw


def _expected_hash():
    match = re.fullmatch(r'"([a-f0-9]{64})"', request.headers.get("If-Match", ""))
    if not match:
        abort(400, description="SHA-256 versi yang ditinjau wajib dikirim melalui If-Match.")
    return match[1]


@api.get("/testsets")
@_testset_endpoint
def testset_list():
    return _json(testset_versions.list_versions(db()))


@api.get("/testsets/<version>")
@_testset_endpoint
def testset_detail(version):
    return _json(testset_versions.version_detail(db(), version))


@api.post("/testsets")
@_testset_endpoint
def testset_create():
    _check_csrf_header()
    return _json(testset_versions.save_version(db(), _read_upload(), current_user.id), 201)


@api.put("/testsets/<version>")
@_testset_endpoint
def testset_replace(version):
    _check_csrf_header()
    expected = _expected_hash()
    return _json(testset_versions.save_version(
        db(), _read_upload(), current_user.id, version=version, expected_hash=expected,
    ))


@api.post("/testsets/<version>/lock")
@_testset_endpoint
def testset_lock(version):
    _check_csrf_header()
    return _json(testset_versions.lock_version(db(), version, _expected_hash(), current_user.id))


@api.get("/testsets/<version>/export")
@_testset_endpoint
def testset_export(version):
    row, payload = testset_versions.get_version(db(), version)
    if row["locked_at"] is None:
        abort(409, description="Kunci versi sebelum mengunduh JSON.")
    response = Response(json.dumps(payload, ensure_ascii=False, indent=2), mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="testset-{row["version"]}.json"'
    response.headers["Cache-Control"] = "no-store"
    return response
