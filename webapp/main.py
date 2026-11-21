"""Dashboard dan detail arsip."""

from flask import Blueprint, abort, render_template
from flask_login import login_required

from services.archive_detail import get_archive_detail
from services.dashboard import get_dashboard_summary
from webapp.database import db

main = Blueprint("main", __name__)


@main.get("/")
@login_required
def dashboard():
    summary = get_dashboard_summary(db())
    return render_template("dashboard.html", **summary)


@main.get("/archives/<int:archive_id>")
@login_required
def archive_detail(archive_id):
    archive = get_archive_detail(db(), archive_id)
    if archive is None:
        abort(404)
    return render_template("archive_detail.html", archive=archive)
