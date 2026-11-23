"""Layanan tinjauan kualitas metadata arsip dan kategori masalah ekstraksi [PM-23]."""

import sqlite3
from typing import Any, Dict, List, Optional

METADATA_FIELDS = (
    ("spm_number", "Nomor SPM"),
    ("sp2d_number", "Nomor SP2D"),
    ("document_date", "Tanggal Dokumen"),
    ("amount_rp", "Nominal (Rp)"),
    ("party_name", "Nama Pihak"),
)
VALID_SPM_CONFIDENCE = frozenset({"dugaan", "terkonfirmasi"})


def get_metadata_quality_summary(
    connection: sqlite3.Connection,
    *,
    issue_type: Optional[str] = None,
    field_name: Optional[str] = None,
    spm_confidence: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
) -> Dict[str, Any]:
    """Hitung cakupan ekstraksi metadata, status kamus SPM, dan daftar masalah kualitas."""
    if page < 1 or not 1 <= per_page <= 100:
        raise ValueError("Parameter paginasi page/per_page tidak valid.")
    if spm_confidence is not None and spm_confidence not in VALID_SPM_CONFIDENCE:
        raise ValueError("Parameter spm_confidence harus 'dugaan' atau 'terkonfirmasi'.")

    total_archives = int(connection.execute("SELECT COUNT(*) FROM archive").fetchone()[0])

    # Cakupan 5 field metadata hasil ekstraksi pada tabel archive_metadata
    coverage_row = connection.execute(
        """
        SELECT
            SUM(CASE WHEN m.spm_number IS NOT NULL AND TRIM(m.spm_number) != '' THEN 1 ELSE 0 END) AS spm_number_filled,
            SUM(CASE WHEN m.sp2d_number IS NOT NULL AND TRIM(m.sp2d_number) != '' THEN 1 ELSE 0 END) AS sp2d_number_filled,
            SUM(CASE WHEN m.document_date IS NOT NULL AND TRIM(m.document_date) != '' THEN 1 ELSE 0 END) AS document_date_filled,
            SUM(CASE WHEN m.amount_rp IS NOT NULL THEN 1 ELSE 0 END) AS amount_rp_filled,
            SUM(CASE WHEN m.party_name IS NOT NULL AND TRIM(m.party_name) != '' THEN 1 ELSE 0 END) AS party_name_filled
        FROM archive a
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        """
    ).fetchone()

    metadata_coverage: List[Dict[str, Any]] = []
    for field_key, field_label in METADATA_FIELDS:
        filled = int(coverage_row[f"{field_key}_filled"] or 0) if total_archives > 0 else 0
        missing = total_archives - filled
        fill_rate = round(filled / total_archives, 4) if total_archives > 0 else 0.0
        metadata_coverage.append(
            {
                "field": field_key,
                "label": field_label,
                "filled": filled,
                "missing": missing,
                "fill_rate": fill_rate,
            }
        )

    # Ringkasan keyakinan kode jenis SPM
    spm_counts_rows = connection.execute(
        """
        SELECT COALESCE(s.confidence, 'tanpa_kode') AS conf, COUNT(*) AS cnt
        FROM archive a
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        LEFT JOIN spm_type s ON s.code = m.spm_type_code
        GROUP BY COALESCE(s.confidence, 'tanpa_kode')
        """
    ).fetchall()
    spm_counts = {"dugaan": 0, "terkonfirmasi": 0, "tanpa_kode": 0}
    for row in spm_counts_rows:
        conf_key = str(row["conf"])
        if conf_key in spm_counts:
            spm_counts[conf_key] = int(row["cnt"])

    # Ringkasan kategori data_issue
    category_rows = connection.execute(
        """
        SELECT issue_type, field_name, COUNT(*) AS total
        FROM data_issue
        GROUP BY issue_type, field_name
        ORDER BY total DESC, issue_type ASC, field_name ASC
        """
    ).fetchall()
    issue_categories = [
        {
            "issue_type": str(row["issue_type"]),
            "field_name": str(row["field_name"]),
            "count": int(row["total"]),
        }
        for row in category_rows
    ]
    total_issues = sum(item["count"] for item in issue_categories)

    issue_types = sorted({item["issue_type"] for item in issue_categories})
    field_names = sorted({item["field_name"] for item in issue_categories})

    # Kueri masalah terfilter + terpaginasi
    conditions: List[str] = []
    params: List[Any] = []
    if issue_type:
        conditions.append("di.issue_type = ?")
        params.append(issue_type)
    if field_name:
        conditions.append("di.field_name = ?")
        params.append(field_name)
    if spm_confidence:
        conditions.append("s.confidence = ?")
        params.append(spm_confidence)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    filtered_total = int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM data_issue di
            JOIN archive a ON a.id = di.archive_id
            LEFT JOIN archive_metadata m ON m.archive_id = a.id
            LEFT JOIN spm_type s ON s.code = m.spm_type_code
            {where_sql}
            """,
            params,
        ).fetchone()[0]
    )

    pages = max(1, (filtered_total + per_page - 1) // per_page)
    safe_page = min(page, pages)
    offset = (safe_page - 1) * per_page

    rows = connection.execute(
        f"""
        SELECT
            di.id,
            di.archive_id,
            di.issue_type,
            di.field_name,
            di.raw_value,
            di.detail,
            a.year,
            COALESCE(o.name, '') AS opd_name,
            COALESCE(a.summary_raw, '') AS summary_raw,
            m.spm_type_code,
            s.confidence AS spm_confidence
        FROM data_issue di
        JOIN archive a ON a.id = di.archive_id
        LEFT JOIN opd o ON o.id = a.opd_id
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        LEFT JOIN spm_type s ON s.code = m.spm_type_code
        {where_sql}
        ORDER BY di.id DESC
        LIMIT ? OFFSET ?
        """,
        [*params, per_page, offset],
    ).fetchall()

    items = [
        {
            "id": int(row["id"]),
            "archive_id": int(row["archive_id"]),
            "issue_type": str(row["issue_type"]),
            "field_name": str(row["field_name"]),
            "raw_value": row["raw_value"],
            "detail": row["detail"],
            "year": int(row["year"]) if row["year"] is not None else None,
            "opd_name": str(row["opd_name"]),
            "spm_type_code": row["spm_type_code"],
            "spm_confidence": row["spm_confidence"],
            "summary_preview": str(row["summary_raw"])[:160],
        }
        for row in rows
    ]

    return {
        "total_archives": total_archives,
        "total_issues": total_issues,
        "spm_confidence_summary": spm_counts,
        "metadata_coverage": metadata_coverage,
        "issue_categories": issue_categories,
        "filters": {
            "issue_types": issue_types,
            "field_names": field_names,
        },
        "issues": {
            "items": items,
            "total": filtered_total,
            "page": safe_page,
            "per_page": per_page,
            "pages": pages,
        },
    }
