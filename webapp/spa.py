"""Penyajian build React lokal tanpa proses Node.js saat aplikasi berjalan."""

import re
from pathlib import Path

from flask import abort, request, send_file, send_from_directory


HASHED_ASSET = re.compile(r"-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+$")


def register_spa(app):
    """Aktifkan route React bila build Vite tersedia dan UI diaktifkan."""
    if not app.config["SERVE_REACT"]:
        return

    dist = Path(app.config["FRONTEND_DIST"]).resolve()
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Build React tidak ditemukan: {index}. Jalankan npm run build.")

    @app.before_request
    def serve_spa_navigation():
        path = request.path
        if request.method not in ("GET", "HEAD"):
            return None
        if (
            path not in ("/", "/login", "/app")
            and not path.startswith("/app/")
            and not path.startswith("/f/")
        ):
            return None
        response = send_file(index)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/assets/<path:filename>")
    def serve_spa_asset(filename):
        if not (dist / "assets").is_dir():
            abort(404)
        response = send_from_directory(dist / "assets", filename)
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable"
            if HASHED_ASSET.search(filename)
            else "no-cache"
        )
        return response
