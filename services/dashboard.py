"""Sumber tunggal angka dan daftar ringkas dashboard arsip."""

import sqlite3


def get_dashboard_summary(connection: sqlite3.Connection) -> dict:
    """Baca ringkasan dari salinan SQLite tanpa nilai contoh atau cache."""
    row = connection.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS inactive,
               SUM(CASE WHEN has_document = 1 THEN 1 ELSE 0 END) AS with_file
        FROM archive
        """
    ).fetchone()
    recent = connection.execute(
        """
        SELECT a.id, a.year, a.summary_raw, o.name AS opd_name
        FROM archive a
        LEFT JOIN opd o ON o.id = a.opd_id
        ORDER BY a.id DESC
        LIMIT 6
        """
    ).fetchall()
    latest_batch = connection.execute(
        """
        SELECT source_filename, imported_at, clean_count
        FROM import_batch
        WHERE status = 'completed'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return {
        "counts": {key: int(row[key] or 0) for key in ("total", "active", "inactive", "with_file")},
        "recent": [
            {
                "id": item["id"],
                "year": item["year"],
                "summary_raw": item["summary_raw"],
                "opd_name": item["opd_name"],
            }
            for item in recent
        ],
        "latest_import": (
            {
                "source_filename": latest_batch["source_filename"],
                "imported_at": latest_batch["imported_at"],
                "clean_count": int(latest_batch["clean_count"] or 0),
            }
            if latest_batch is not None
            else None
        ),
    }
