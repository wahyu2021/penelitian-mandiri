"""Format CSV labeler lama untuk penyiapan sampel dan pertukaran jawaban."""

import csv
import io

SAMPLE_FIELDS = {"query_id", "archive_id", "base_query_text", "query_text",
                 "query_type", "summary_raw"}
LEGACY_FIELDS = {"query_id", "archive_id", "query_text", "query_type", "is_relevant"}
EXPORT_FIELDS = (
    "sample_id", "query_id", "base_query_id", "base_query_text", "query_text",
    "query_type", "source", "noise_type", "archive_id", "summary_raw",
    "is_relevant", "ragu", "auditor_notes", "archivist_notes", "reviewer_slot",
)


def _rows(content, required):
    try:
        stream = io.StringIO(content.decode("utf-8-sig"), newline="")
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames or []
        if not required.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("Kolom CSV tidak cocok dengan format labeler.")
        result = {}
        for index, row in enumerate(reader, start=2):
            raw_id = row.get("archive_id") or ""
            query_id = row.get("query_id") or ""
            if (None in row or None in row.values() or not query_id.strip()
                    or not raw_id.isascii() or not raw_id.isdecimal() or len(raw_id) > 18):
                raise ValueError(f"Format pasangan CSV pada baris {index} tidak valid.")
            key = (query_id.strip(), int(raw_id))
            if key in result or key[1] < 1:
                raise ValueError(f"Pasangan CSV pada baris {index} ganda atau tidak valid.")
            result[key] = row
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError("CSV harus valid dan menggunakan UTF-8.") from error
    if not result:
        raise ValueError("CSV tidak memiliki pasangan kueri dan arsip.")
    return result


def read_sample(content):
    rows = _rows(content, SAMPLE_FIELDS)
    if len(rows) > 2000:
        raise ValueError("Sampel memuat lebih dari 2.000 baris.")
    return rows


def read_legacy(content, slot):
    slot_fields = {"auditor_notes"} if slot == 1 else {"archivist_notes", "base_query_text", "summary_raw"}
    return _rows(content, LEGACY_FIELDS | slot_fields)


def legacy_answer(row, slot):
    if row.get("reviewer_slot") and row["reviewer_slot"] != str(slot):
        raise ValueError("CSV ini berasal dari nomor penilai yang berbeda.")
    decision = row["is_relevant"].strip()
    doubt = row.get("ragu", "").strip()
    if decision not in ("", "0", "1") or doubt not in ("", "0", "1"):
        raise ValueError("CSV lama memuat nilai relevansi atau ragu yang tidak valid.")
    note_field = "auditor_notes" if slot == 1 else "archivist_notes"
    notes = row.get(note_field, "").strip()
    if len(notes) > 1000:
        raise ValueError("Catatan CSV lama melebihi 1.000 karakter.")
    return (int(decision) if decision else None, doubt == "1", notes)


def export_rows(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + buffer.getvalue()
