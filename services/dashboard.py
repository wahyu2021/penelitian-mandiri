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
        "SELECT id, year, summary_raw FROM archive ORDER BY id DESC LIMIT 6"
    ).fetchall()
    return {
        "counts": {key: int(row[key] or 0) for key in ("total", "active", "inactive", "with_file")},
        "recent": [
            {"id": item["id"], "year": item["year"], "summary_raw": item["summary_raw"]}
            for item in recent
        ],
    }
