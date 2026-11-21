"""Sumber data detail arsip untuk halaman lama dan API JSON."""

import sqlite3


def get_archive_detail(connection: sqlite3.Connection, archive_id: int) -> dict | None:
    """Baca satu arsip tanpa mengambil kolom internal yang tidak ditampilkan."""
    row = connection.execute(
        """
        SELECT a.id, a.status, a.year, a.summary_raw, a.file_number,
               a.index_label, a.location_block, a.location_rack,
               a.location_row, a.box_number, a.has_document,
               o.name AS opd_name, c.name AS classification_label,
               m.spm_number, m.sp2d_number, m.document_date, m.amount_rp,
               m.party_name, m.spm_type_code, s.label AS spm_type_label,
               s.confidence AS spm_type_confidence
        FROM archive a
        LEFT JOIN opd o ON o.id = a.opd_id
        LEFT JOIN classification c ON c.id = a.classification_id
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        LEFT JOIN spm_type s ON s.code = m.spm_type_code
        WHERE a.id = ?
        """,
        (archive_id,),
    ).fetchone()
    return dict(row) if row is not None else None
