"""Detail arsip JSON dengan daftar field yang dibatasi."""

import sqlite3

from flask import abort

from services.archive_detail import get_archive_detail
from webapp.api import api, success
from webapp.api.session import require_api_user
from webapp.database import db


def _public_detail(row: dict) -> dict:
    spm_type = None
    if row["spm_type_code"] is not None:
        spm_type = {
            "code": row["spm_type_code"],
            "label": row["spm_type_label"],
            "confidence": row["spm_type_confidence"],
        }
    return {
        "id": row["id"],
        "status": row["status"],
        "year": row["year"],
        "opd_name": row["opd_name"],
        "classification_label": row["classification_label"],
        "file_number": row["file_number"],
        "index_label": row["index_label"],
        "summary_raw": row["summary_raw"],
        "has_document": bool(row["has_document"]),
        "location": {
            "block": row["location_block"],
            "rack": row["location_rack"],
            "row": row["location_row"],
            "box_number": row["box_number"],
        },
        "extraction": {
            "spm_number": row["spm_number"],
            "sp2d_number": row["sp2d_number"],
            "document_date": row["document_date"],
            "amount_rp": row["amount_rp"],
            "party_name": row["party_name"],
            "spm_type": spm_type,
        },
    }


@api.get("/archives/<archive_id>")
@require_api_user
def archive_detail(archive_id):
    if len(archive_id) > 10 or not archive_id.isascii() or not archive_id.isdecimal():
        abort(400, description="ID arsip harus berupa bilangan bulat positif.")
    numeric_id = int(archive_id)
    if numeric_id <= 0:
        abort(400, description="ID arsip harus berupa bilangan bulat positif.")
    try:
        archive = get_archive_detail(db(), numeric_id)
    except sqlite3.Error:
        abort(500, description="Detail arsip tidak dapat dibaca.")
    if archive is None:
        abort(404, description="Arsip tidak ditemukan.")
    response, status = success(_public_detail(archive))
    response.headers["Cache-Control"] = "no-store"
    return response, status
