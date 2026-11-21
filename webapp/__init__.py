"""Pabrik aplikasi Flask untuk antarmuka web SIMANIS."""

import os
import secrets
from pathlib import Path

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from services.db import DEFAULT_DB_PATH
from webapp.api import ERROR_CODES, api, is_api_request
from webapp.auth import auth, csrf_token, login_manager
from webapp.cli import register_commands
from webapp.database import close_db
from webapp.main import main
from webapp.search import search_pages

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.config.update(
        SECRET_KEY=os.environ.get("PM_SECRET_KEY") or secrets.token_hex(32),
        DATABASE=Path(os.environ.get("PM_DB_PATH", str(DEFAULT_DB_PATH))),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    login_manager.init_app(app)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(search_pages)
    app.register_blueprint(api)
    register_commands(app)

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
            return response
        return render_template("error.html", code=error.code, message=error.description), error.code

    return app
