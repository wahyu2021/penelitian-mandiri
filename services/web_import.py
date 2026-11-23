"""Batas berkas dan cadangan untuk impor dump lewat antarmuka web."""

import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from core.sql_dump_parser import parse_sql_dump
from services.importer import REFERENCE_COUNTS, import_simanis_dump

MAX_DUMP_BYTES = 100 * 1024 * 1024


def allowed_source(directory: Path, name: str) -> Path:
    """Terima hanya nama berkas .sql langsung di direktori yang diizinkan."""
    if (not isinstance(name, str) or not name or name != Path(name).name
            or "/" in name or "\\" in name or not name.lower().endswith(".sql")):
        raise ValueError("Nama berkas dump tidak valid.")
    root = directory.resolve(strict=True)
    path = root / name
    if not path.is_file() or path.resolve(strict=True).parent != root:
        raise ValueError("Berkas tidak ada dalam direktori impor yang diizinkan.")
    if path.stat().st_size > MAX_DUMP_BYTES:
        raise ValueError("Berkas dump melebihi batas 100 MB.")
    return path


def list_sources(directory: Path) -> list[dict]:
    root = directory.resolve(strict=True)
    return sorted(
        [
            {"name": path.name, "size_bytes": path.stat().st_size}
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() == ".sql"
            and path.resolve().parent == root and path.stat().st_size <= MAX_DUMP_BYTES
        ],
        key=lambda item: item["name"].lower(),
    )


def preview_source(directory: Path, name: str) -> dict:
    path = allowed_source(directory, name)
    parsed = parse_sql_dump(str(path))
    counts = {
        "archives": len(parsed["arsip"]),
        "opds": len(parsed["opd"]),
        "classifications": len(parsed["klasifikasi"]),
    }
    if counts["archives"] == 0:
        raise ValueError("Dump tidak memuat arsip yang dapat diimpor.")
    return {
        "source": path.name,
        "source_sha256": parsed["sha256"],
        "size_bytes": path.stat().st_size,
        "counts": counts,
        "reference_archive_count": REFERENCE_COUNTS["total"],
        "reference_total_matches": counts["archives"] == REFERENCE_COUNTS["total"],
    }


def backup_database(db_path: Path, backup_dir: Path) -> Path | None:
    """Gunakan backup SQLite konsisten sebelum impor ulang."""
    if not db_path.is_file():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{db_path.stem}-{stamp}-{secrets.token_hex(4)}.sqlite"
    try:
        with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
            if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("Cadangan SQLite tidak valid.")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def import_source(directory: Path, name: str, expected_sha256: str, db_path: Path,
                  backup_dir: Path, imported_by: str, verify_reference_counts: bool,
                  audit_user_id: int | None = None) -> dict:
    path = allowed_source(directory, name)
    preview = preview_source(directory, name)
    if preview["source_sha256"] != expected_sha256:
        raise ValueError("Dump berubah sejak pratinjau. Pilih dan periksa ulang berkas.")
    backup = backup_database(db_path, backup_dir)
    summary = import_simanis_dump(
        path, db_path=db_path, verify_reference_counts=verify_reference_counts,
        imported_by=imported_by, expected_source_sha256=expected_sha256,
        audit_user_id=audit_user_id, backup_filename=backup.name if backup else None,
    )
    return {**summary, "backup_filename": backup.name if backup else None}
