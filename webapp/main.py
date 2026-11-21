"""Dashboard dan detail arsip."""

from flask import Blueprint, abort, render_template
from flask_login import login_required

from webapp.database import db

main = Blueprint("main", __name__)


@main.get("/")
@login_required
def dashboard():
    counts = db().execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS inactive,
               SUM(CASE WHEN has_document = 1 THEN 1 ELSE 0 END) AS with_file
        FROM archive
    """).fetchone()
    recent = db().execute(
        "SELECT id, year, summary_raw FROM archive ORDER BY id DESC LIMIT 6"
    ).fetchall()
    return render_template("dashboard.html", counts=counts, recent=recent)


@main.get("/archives/<int:archive_id>")
@login_required
def archive_detail(archive_id):
    archive = db().execute("""
        SELECT a.*, o.name AS opd_name, c.name AS classification_label,
               m.spm_number, m.sp2d_number, m.document_date, m.amount_rp,
               m.party_name, m.spm_type_code, s.label AS spm_type_label,
               s.confidence AS spm_type_confidence
        FROM archive a
        LEFT JOIN opd o ON o.id = a.opd_id
        LEFT JOIN classification c ON c.id = a.classification_id
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        LEFT JOIN spm_type s ON s.code = m.spm_type_code
        WHERE a.id = ?
    """, (archive_id,)).fetchone()
    if archive is None:
        abort(404)
    return render_template("archive_detail.html", archive=archive)
