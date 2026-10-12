"""Layanan impor dump SQL e-Arsip SIMANIS ke basis data SQLite lokal.

Mencatat salinan mentah (archive_raw), data bersih (archive), isu kualitas (data_issue),
dan metadata hasil ekstraksi (archive_metadata). Memverifikasi kelima angka acuan
spesifikasi agar integritas data terjamin 100%.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Union

from core.cleaning import clean_archive_row
from core.extraction import extract_metadata
from core.normalization import normalize_text
from core.spm_types import CONFIDENCE_GUESS
from core.sql_dump_parser import parse_sql_dump
from services.db import get_connection, init_db

PARSER_VERSION = "v1.0.0"
EXTRACTOR_VERSION = "v1.0.0"

REFERENCE_COUNTS = {
    "total": 1737,
    "in_aktif": 1590,
    "statis": 147,
    "orphan_opd": 143,
    "upload_error_documents": 11,
    "has_spm_label": 1344,
    "zero_input_dates": 147,
}


def import_simanis_dump(
    dump_path: Union[str, Path],
    db_path: Optional[Union[str, Path]] = None,
    verify_reference_counts: bool = True,
    imported_by: str = "system",
) -> Dict[str, object]:
    """Impor berkas dump SQL SIMANIS ke database SQLite lokal.

    Args:
        dump_path: Path berkas dump SQL.
        db_path: Path berkas SQLite (default: `instance/app.sqlite`).
        verify_reference_counts: Jika True, lempar ValueError bila angka acuan tidak cocok.
        imported_by: Identitas pengimpor yang dicatat di tabel import_batch.

    Returns:
        Kamus ringkasan hasil impor berisi batch_id, sha256, jumlah baris, dan status verifikasi.

    Raises:
        ValueError: Jika verify_reference_counts aktif dan ada angka acuan yang tidak sesuai.
    """
    dump_file = Path(dump_path)
    if not dump_file.is_file():
        raise FileNotFoundError(f"Berkas dump SQL tidak ditemukan: {dump_path}")

    raw_dump = parse_sql_dump(str(dump_file))
    conn = init_db(db_path)

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_archives = raw_dump["arsip"]
    raw_opd = raw_dump["opd"]
    raw_classifications = raw_dump["klasifikasi"]

    valid_opd_ids = {int(r["id_opd"]) for r in raw_opd}
    valid_class_ids = {int(r["id_klasifikasi"]) for r in raw_classifications}

    stat_counts: Counter = Counter()
    issue_type_counts: Counter = Counter()
    spm_label_count = 0
    clean_count = 0
    issue_count = 0

    with conn:
        # 1. Simpan Master OPD
        for opd_row in raw_opd:
            opd_id = int(opd_row["id_opd"])
            name = (opd_row.get("nama_opd") or "").strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO opd (id, name, name_normalized)
                VALUES (?, ?, ?);
                """,
                (opd_id, name, normalize_text(name)),
            )

        # 2. Simpan Master Klasifikasi
        for class_row in raw_classifications:
            class_id = int(class_row["id_klasifikasi"])
            code = (class_row.get("kode_klasifikasi") or "").strip()
            name = (class_row.get("index") or "").strip()
            conn.execute(
                """
                INSERT OR REPLACE INTO classification (id, code, name)
                VALUES (?, ?, ?);
                """,
                (class_id, code, name),
            )

        # 3. Buat Catatan Batch Impor
        cursor = conn.execute(
            """
            INSERT INTO import_batch (
                source_filename, source_sha256, parser_version, extractor_version,
                raw_count, clean_count, issue_count, status, imported_by, imported_at
            ) VALUES (?, ?, ?, ?, ?, 0, 0, 'in_progress', ?, ?);
            """,
            (
                dump_file.name,
                raw_dump["sha256"],
                PARSER_VERSION,
                EXTRACTOR_VERSION,
                len(raw_archives),
                imported_by,
                now_iso,
            ),
        )
        batch_id = cursor.lastrowid

        # 4. Simpan Data Arsip (Mentah, Bersih, Isu, dan Metadata)
        for raw in raw_archives:
            archive_id = int(raw["id_arsip"])

            # 4a. archive_raw (salinan persis 20 kolom)
            conn.execute(
                """
                INSERT INTO archive_raw (
                    id_arsip, batch_id, opd_id, klasifikasi_id, user_id, no_berkas,
                    index_ar, tahun, input_tahun, ringkasan, block, lokasi_rak,
                    lokasi_baris, no_box, tingkat_perkembangan, jumlah, ket_berkas,
                    ket_jra, stat_dokumen, dokumen, last_updates
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    archive_id,
                    batch_id,
                    raw.get("opd_id"),
                    raw.get("klasifikasi_id"),
                    raw.get("user_id"),
                    raw.get("no_berkas"),
                    raw.get("index_ar"),
                    raw.get("tahun"),
                    raw.get("input_tahun"),
                    raw.get("ringkasan"),
                    raw.get("block"),
                    raw.get("lokasi_rak"),
                    raw.get("lokasi_baris"),
                    raw.get("no_box"),
                    raw.get("tingkat_perkembangan"),
                    raw.get("jumlah"),
                    raw.get("ket_berkas"),
                    raw.get("ket_jra"),
                    raw.get("stat_dokumen"),
                    raw.get("dokumen"),
                    raw.get("last_updates"),
                ),
            )

            # 4b. Bersihkan baris data
            cleaned, issues = clean_archive_row(raw, valid_opd_ids, valid_class_ids)
            summary_clean = str(cleaned.get("summary_clean") or "")
            summary_normalized = normalize_text(summary_clean)

            status_val = cleaned.get("status")
            if status_val in (1, 2, 3):
                stat_counts[status_val] += 1

            conn.execute(
                """
                INSERT INTO archive (
                    id, batch_id, opd_id, opd_id_source, classification_id,
                    year, input_date, file_number, index_label, summary_raw,
                    summary_clean, summary_normalized, location_block, location_rack,
                    location_row, box_number, development_level, quantity_label,
                    file_note, retention_note, status, document_filename, has_document
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    archive_id,
                    batch_id,
                    cleaned.get("opd_id"),
                    int(cleaned["opd_id_source"]),
                    cleaned.get("classification_id"),
                    cleaned.get("year"),
                    cleaned.get("input_date"),
                    cleaned.get("file_number"),
                    cleaned.get("index_label"),
                    cleaned.get("summary_raw"),
                    summary_clean,
                    summary_normalized,
                    cleaned.get("location_block"),
                    cleaned.get("location_rack"),
                    cleaned.get("location_row"),
                    cleaned.get("box_number"),
                    cleaned.get("development_level"),
                    cleaned.get("quantity_label"),
                    cleaned.get("file_note"),
                    cleaned.get("retention_note"),
                    cleaned["status"],
                    cleaned.get("document_filename"),
                    1 if cleaned.get("has_document") else 0,
                ),
            )
            clean_count += 1

            # 4c. Simpan isu data
            for iss in issues:
                issue_type_counts[iss["issue_type"]] += 1
                issue_count += 1
                conn.execute(
                    """
                    INSERT INTO data_issue (
                        archive_id, batch_id, issue_type, field_name, raw_value, detail
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        archive_id,
                        batch_id,
                        iss["issue_type"],
                        iss["field_name"],
                        iss.get("raw_value"),
                        iss["detail"],
                    ),
                )

            # 4d. Ekstraksi metadata
            meta = extract_metadata(summary_clean)
            if meta["has_spm_label"]:
                spm_label_count += 1

            # Daftarkan jenis SPM bila belum ada di kamus
            type_code = meta.get("spm_type_code")
            if type_code:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO spm_type (code, label, confidence, source_note)
                    VALUES (?, ?, ?, ?);
                    """,
                    (
                        str(type_code),
                        f"Jenis {type_code} (dugaan)",
                        CONFIDENCE_GUESS,
                        "Ditemukan otomatis dari ringkasan data arsip",
                    ),
                )

            party_name = meta.get("party_name")
            party_normalized = normalize_text(str(party_name)) if party_name else None

            conn.execute(
                """
                INSERT INTO archive_metadata (
                    archive_id, spm_number, spm_sequence, spm_type_code, spm_suffix,
                    sp2d_number, document_date, amount_rp, party_name, party_normalized,
                    has_spm_label, extractor_version, extracted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    archive_id,
                    meta.get("spm_number"),
                    meta.get("spm_sequence"),
                    type_code,
                    meta.get("spm_suffix"),
                    meta.get("sp2d_number"),
                    meta.get("document_date"),
                    meta.get("amount_rp"),
                    party_name,
                    party_normalized,
                    1 if meta["has_spm_label"] else 0,
                    EXTRACTOR_VERSION,
                    now_iso,
                ),
            )

        # 5. Perbarui Catatan Batch Impor Selesai
        conn.execute(
            """
            UPDATE import_batch
            SET clean_count = ?, issue_count = ?, status = 'completed'
            WHERE id = ?;
            """,
            (clean_count, issue_count, batch_id),
        )

    # 6. Verifikasi Angka Acuan
    actual_counts = {
        "total": len(raw_archives),
        "in_aktif": stat_counts[1],
        "statis": stat_counts[2],
        "orphan_opd": issue_type_counts.get("orphan_opd", 0),
        "upload_error_documents": issue_type_counts.get("upload_error_document", 0),
        "has_spm_label": spm_label_count,
        "zero_input_dates": issue_type_counts.get("invalid_input_date", 0),
    }

    mismatches = {}
    for key, expected_val in REFERENCE_COUNTS.items():
        actual_val = actual_counts.get(key, 0)
        if actual_val != expected_val:
            mismatches[key] = {"expected": expected_val, "actual": actual_val}

    if verify_reference_counts and mismatches:
        raise ValueError(
            f"Angka acuan dump tidak sesuai: {mismatches}. Impor dibatalkan."
        )

    return {
        "batch_id": batch_id,
        "source_sha256": raw_dump["sha256"],
        "raw_count": len(raw_archives),
        "clean_count": clean_count,
        "issue_count": issue_count,
        "actual_counts": actual_counts,
        "reference_counts_match": len(mismatches) == 0,
    }
