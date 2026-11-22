"""Bangun ZIP web untuk Flask/Waitress; data penelitian tidak ikut paket."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROOT_FILES = ("app.py", "wsgi.py", "requirements-web.txt", "docs/runbook_web_release.md")
CODE_DIRS = ("core", "services", "webapp")
ASSET_DIRS = ("templates", "static", "frontend/dist")

class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        if tag not in ("script", "link"):
            return
        key = "src" if tag == "script" else "href"
        values = dict(attrs)
        if values.get(key):
            self.references.append(values[key])


def validate_dist(root: Path) -> None:
    dist = root / "frontend" / "dist"
    index = dist / "index.html"
    if not index.is_file():
        raise ValueError("frontend/dist/index.html belum ada; build frontend gagal atau belum dijalankan.")
    html = index.read_text(encoding="utf-8")
    parser = AssetReferences()
    parser.feed(html)
    references = parser.references
    if not references:
        raise ValueError("index.html tidak merujuk aset lokal hasil Vite.")
    for reference in references:
        if not reference.startswith("/assets/"):
            raise ValueError(f"Aset eksternal atau path tak dikenal pada index.html: {reference}")
        asset = dist / reference.lstrip("/")
        if not asset.is_file():
            raise ValueError(f"Aset yang dirujuk index.html tidak ada: {reference}")


def release_files(root: Path) -> list[Path]:
    validate_dist(root)
    for name in (*CODE_DIRS, *ASSET_DIRS):
        if not (root / name).is_dir():
            raise ValueError(f"Direktori paket tidak ada: {name}")
    files = [root / name for name in ROOT_FILES]
    files += [path for name in CODE_DIRS for path in (root / name).rglob("*.py")]
    files += [path for name in ASSET_DIRS for path in (root / name).rglob("*") if path.is_file()]
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Berkas paket tidak ada atau berupa symlink: {path}")
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def package_release(root: Path, destination: Path) -> Path:
    root = root.resolve()
    files = release_files(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"format": 1, "files": {}}
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            bundle.writestr(f"pm-web/{relative}", data)
            manifest["files"][relative] = hashlib.sha256(data).hexdigest()
        bundle.writestr(
            "pm-web/release-manifest.json",
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
    return destination


def build_frontend(root: Path) -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm tidak ditemukan pada laptop pembangun paket.")
    frontend = root / "frontend"
    subprocess.run([npm, "ci"], cwd=frontend, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bangun aset React dan ZIP rilis web.")
    parser.add_argument("--output", type=Path, help="Lokasi ZIP; default output/releases/pm-web-<waktu>.zip")
    args = parser.parse_args(argv)
    destination = args.output or PROJECT_ROOT / "output" / "releases" / (
        f"pm-web-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    )
    build_frontend(PROJECT_ROOT)
    package_release(PROJECT_ROOT, destination)
    print(f"Paket web dibuat: {destination.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
