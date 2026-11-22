"""Paket web hanya memuat berkas aplikasi dan aset build yang diizinkan."""

import json
import zipfile

import pytest

from scripts.build_web_release import package_release, validate_dist


def make_source(root):
    for name in ("app.py", "wsgi.py", "requirements-web.txt", "docs/runbook_web_release.md"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    for name in ("core/search/like.py", "services/db.py", "webapp/spa.py",
                 "templates/error.html", "static/css/app.css"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    dist = root / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        '<script src="/assets/index-AbCd1234.js"></script>'
        '<link href="/assets/index-AbCd1234.css">', encoding="utf-8"
    )
    (dist / "assets" / "index-AbCd1234.js").write_text("test JS", encoding="utf-8")
    (dist / "assets" / "index-AbCd1234.css").write_text("test CSS", encoding="utf-8")


def test_package_has_runtime_assets_manifest_and_no_data(tmp_path):
    root = tmp_path / "project"
    make_source(root)
    (root / "instance").mkdir()
    (root / "instance" / "app.sqlite").write_text("PRIVATE", encoding="utf-8")
    (root / "frontend" / "node_modules").mkdir()
    (root / "frontend" / "node_modules" / "package.js").write_text("dev", encoding="utf-8")
    (root / "output").mkdir()
    (root / "output" / "judgments.csv").write_text("PRIVATE", encoding="utf-8")
    (root / ".env").write_text("PRIVATE", encoding="utf-8")
    destination = tmp_path / "release.zip"
    package_release(root, destination)
    with zipfile.ZipFile(destination) as bundle:
        names = set(bundle.namelist())
        assert "pm-web/app.py" in names
        assert "pm-web/webapp/spa.py" in names
        assert "pm-web/frontend/dist/assets/index-AbCd1234.js" in names
        assert "pm-web/release-manifest.json" in names
        assert all(not any(part in name for part in ("instance/", "node_modules/", "output/", ".env"))
                   for name in names)
        manifest = json.loads(bundle.read("pm-web/release-manifest.json"))
        assert manifest["format"] == 1
        assert "frontend/dist/index.html" in manifest["files"]
        assert len(manifest["files"]["frontend/dist/index.html"]) == 64


def test_package_rejects_missing_hashed_asset(tmp_path):
    make_source(tmp_path)
    (tmp_path / "frontend" / "dist" / "assets" / "index-AbCd1234.js").unlink()
    with pytest.raises(ValueError, match="tidak ada"):
        validate_dist(tmp_path)


def test_package_rejects_external_runtime_asset(tmp_path):
    make_source(tmp_path)
    (tmp_path / "frontend" / "dist" / "index.html").write_text(
        '<script src="https://cdn.example.invalid/app.js"></script>', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Aset eksternal"):
        validate_dist(tmp_path)
