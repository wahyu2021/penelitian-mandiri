"""Pabrik aplikasi Flask untuk antarmuka web SIMANIS."""

import os
import secrets
from pathlib import Path

from flask import Flask
from werkzeug.exceptions import HTTPException

from services.db import DEFAULT_DB_PATH
from webapp.api import ERROR_CODES, api, is_api_request
from webapp.auth import login_manager
from webapp.cli import register_commands
from webapp.database import close_db
from webapp.spa import register_spa

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=os.environ.get("PM_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("PM_COOKIE_SECURE") == "1",
        SERVE_REACT=os.environ.get(
            "PM_SERVE_REACT", "1" if (PROJECT_ROOT / "frontend" / "dist" / "index.html").is_file() else "0"
        ) == "1",
        FRONTEND_DIST=PROJECT_ROOT / "frontend" / "dist",
    )
    if test_config:
        app.config.update(test_config)

    login_manager.init_app(app)
    app.teardown_appcontext(close_db)
    app.register_blueprint(api)
    register_commands(app)
    register_spa(app)

    @app.errorhandler(HTTPException)
    def http_error(error):
        if is_api_request():
            status = error.code or 500
            message = "Terjadi kesalahan pada server." if status >= 500 else error.description
            response = error.get_response()
            response.set_data(app.json.dumps({
                "error": {"code": ERROR_CODES.get(status, "http_error"), "message": message}
            }))
            response.content_type = "application/json"
            response.headers["Cache-Control"] = "no-store"
            return response
        response = error.get_response()
        response.set_data(error.description)
        response.content_type = "text/plain; charset=utf-8"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app
