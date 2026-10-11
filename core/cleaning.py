"""Pembersihan dan validasi baris arsip mentah.

Nilai asli tidak diperbaiki secara diam-diam: nilai tak valid menjadi None
dan dicatat sebagai masalah data (issue).
"""
import re
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

MIN_YEAR = 1900
MAX_YEAR = 2100
VALID_STATUSES = frozenset({1, 2, 3})

ISSUE_ORPHAN_OPD = "orphan_opd"
ISSUE_ORPHAN_CLASSIFICATION = "orphan_classification"
ISSUE_INVALID_YEAR = "invalid_year"
ISSUE_INVALID_INPUT_DATE = "invalid_input_date"
ISSUE_EMPTY_SUMMARY = "empty_summary"
ISSUE_INVALID_STATUS = "invalid_status"
ISSUE_MISSING_DOCUMENT = "missing_document"
ISSUE_UPLOAD_ERROR_DOCUMENT = "upload_error_document"

Issue = Dict[str, Optional[str]]


def collapse_whitespace(value: Optional[str]) -> str:
    """Ganti deret spasi/baris baru dengan satu spasi dan pangkas tepi."""
    return re.sub(r"\s+", " ", value or "").strip()


def parse_int(value: Optional[str]) -> Optional[int]:
    """Ubah teks bilangan bulat menjadi int; None bila bukan bilangan bulat."""
    text = (value or "").strip()
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def parse_iso_date(value: Optional[str]) -> Optional[str]:
    """Validasi tanggal `YYYY-MM-DD`; `0000-00-00` dan tanggal mustahil menjadi None."""
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (value or "").strip())
    if not match:
        return None
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return None


def _issue(issue_type: str, field: str, raw: Optional[str], detail: str) -> Issue:
    return {
        "issue_type": issue_type,
        "field_name": field,
        "raw_value": raw,
        "detail": detail,
    }


def clean_archive_row(
    raw: Dict[str, Optional[str]],
    valid_opd_ids: Set[int],
    valid_classification_ids: Set[int],
) -> Tuple[Dict[str, object], List[Issue]]:
    """Bersihkan satu baris `apptb_arsip`.

    Args:
        raw: Baris mentah (kolom -> teks).
        valid_opd_ids: ID OPD yang ada pada master.
        valid_classification_ids: ID klasifikasi yang ada pada master.

    Returns:
        Pasangan (record bersih, daftar masalah data).

    Raises:
        ValueError: `id_arsip` bukan bilangan bulat.
    """
    archive_id = parse_int(raw.get("id_arsip"))
    if archive_id is None:
        raise ValueError(f"id_arsip tidak valid: {raw.get('id_arsip')!r}")
    issues: List[Issue] = []

    opd_source = parse_int(raw.get("opd_id"))
    opd_id = opd_source if opd_source in valid_opd_ids else None
    if opd_id is None:
        issues.append(_issue(
            ISSUE_ORPHAN_OPD, "opd_id", raw.get("opd_id"),
            "ID OPD tidak ada pada master OPD"))

    class_source = parse_int(raw.get("klasifikasi_id"))
    class_id = class_source if class_source in valid_classification_ids else None
    if class_id is None:
        issues.append(_issue(
            ISSUE_ORPHAN_CLASSIFICATION, "klasifikasi_id", raw.get("klasifikasi_id"),
            "ID klasifikasi tidak ada pada master klasifikasi"))

    year = parse_int(raw.get("tahun"))
    if year is None or not MIN_YEAR <= year <= MAX_YEAR:
        issues.append(_issue(
            ISSUE_INVALID_YEAR, "tahun", raw.get("tahun"),
            "Tahun bukan angka dalam rentang wajar"))
        year = None

    input_date = parse_iso_date(raw.get("input_tahun"))
    if input_date is None:
        issues.append(_issue(
            ISSUE_INVALID_INPUT_DATE, "input_tahun", raw.get("input_tahun"),
            "Tanggal input kosong atau tidak valid"))

    summary_raw = raw.get("ringkasan") or ""
    summary_clean = collapse_whitespace(summary_raw)
    if not summary_clean:
        issues.append(_issue(
            ISSUE_EMPTY_SUMMARY, "ringkasan", summary_raw, "Ringkasan kosong"))

    status = parse_int(raw.get("stat_dokumen"))
    if status not in VALID_STATUSES:
        issues.append(_issue(
            ISSUE_INVALID_STATUS, "stat_dokumen", raw.get("stat_dokumen"),
            "Status di luar 1 (In Aktif), 2 (Statis), 3 (Musnah)"))
        status = None

    document = collapse_whitespace(raw.get("dokumen"))
    document_filename: Optional[str] = None
    if not document:
        issues.append(_issue(
            ISSUE_MISSING_DOCUMENT, "dokumen", raw.get("dokumen"),
            "Tidak ada berkas terlampir"))
    elif document.startswith("<"):
        # Pesan galat unggah dari aplikasi lama tersimpan sebagai nama berkas.
        issues.append(_issue(
            ISSUE_UPLOAD_ERROR_DOCUMENT, "dokumen", document[:200],
            "Kolom dokumen berisi pesan galat unggah, bukan nama berkas"))
    else:
        document_filename = document

    record: Dict[str, object] = {
        "id": archive_id,
        "opd_id": opd_id,
        "opd_id_source": opd_source,
        "classification_id": class_id,
        "year": year,
        "input_date": input_date,
        "file_number": collapse_whitespace(raw.get("no_berkas")),
        "index_label": collapse_whitespace(raw.get("index_ar")),
        "summary_raw": summary_raw,
        "summary_clean": summary_clean,
        "location_block": collapse_whitespace(raw.get("block")),
        "location_rack": collapse_whitespace(raw.get("lokasi_rak")),
        "location_row": collapse_whitespace(raw.get("lokasi_baris")),
        "box_number": collapse_whitespace(raw.get("no_box")),
        "development_level": collapse_whitespace(raw.get("tingkat_perkembangan")),
        # Kolom `jumlah` sumber berisi banyak berkas (mis. "1 Berkas"), bukan uang.
        "quantity_label": collapse_whitespace(raw.get("jumlah")),
        "file_note": collapse_whitespace(raw.get("ket_berkas")),
        "retention_note": collapse_whitespace(raw.get("ket_jra")),
        "status": status,
        "document_filename": document_filename,
        "has_document": document_filename is not None,
    }
    return record, issues
