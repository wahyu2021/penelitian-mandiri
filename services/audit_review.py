"""Sampel audit ekstraksi dan penilaian web yang terpisah dari CSV sumber."""

import csv
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.evaluation.audit_metrics import (
    VALID_VERDICTS,
    calculate_field_audit_metrics,
    validate_audit_row_integrity,
)
from services.importer import EXTRACTOR_VERSION

FIELDS = ("spm", "sp2d", "date", "amount", "party")
REFERENCE_COLUMNS = (
    "sample_id", "archive_id", "archive_status", "summary_raw",
    "extracted_spm", "extracted_sp2d", "extracted_date",
    "extracted_amount", "extracted_party",
)
CSV_COLUMNS = (
    "sample_id", "archive_id", "archive_status", "summary_raw",
    "extracted_spm", "verdict_spm", "extracted_sp2d", "verdict_sp2d",
    "extracted_date", "verdict_date", "extracted_amount", "verdict_amount",
    "extracted_party", "verdict_party", "auditor_notes",
)


def load_sample(csv_path: Path, manifest_path: Path) -> dict:
    if not csv_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("CSV sampel atau manifest audit belum tersedia.")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = handle.readline()
        delimiter = ";" if ";" in header and "," not in header else ","
        handle.seek(0)
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames or not set(CSV_COLUMNS).issubset(reader.fieldnames):
            raise ValueError("Kolom sampel audit tidak lengkap.")
        rows = list(reader)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("extractor_version") != EXTRACTOR_VERSION:
        raise ValueError("Versi ekstraktor sampel tidak sesuai aplikasi.")
    refs = manifest.get("reference_records")
    if not isinstance(refs, dict) or not refs:
        raise ValueError("Manifest audit tidak memuat data acuan.")
    try:
        validate_audit_row_integrity(rows, refs)
    except ValueError as error:
        raise ValueError("Kolom acuan sampel audit tidak cocok dengan manifest.") from error

    records = []
    for row in rows:
        try:
            sample_id = int(row["sample_id"])
            archive_id = int(row["archive_id"])
        except (TypeError, ValueError) as error:
            raise ValueError("ID sampel audit tidak valid.") from error
        if sample_id < 1 or archive_id < 1:
            raise ValueError("ID sampel audit tidak valid.")
        records.append({
            **{key: row[key] or "" for key in REFERENCE_COLUMNS if key != "sample_id" and key != "archive_id"},
            "sample_id": sample_id,
            "archive_id": archive_id,
        })
    records.sort(key=lambda row: row["sample_id"])
    if len({row["sample_id"] for row in records}) != len(records):
        raise ValueError("Nomor sampel audit berulang.")
    canonical = json.dumps(sorted(records, key=lambda row: row["archive_id"]),
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "records": records,
        "fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "extractor_version": EXTRACTOR_VERSION,
        "source_filename": csv_path.name,
    }


def check_dataset(conn: sqlite3.Connection, sample: dict) -> None:
    locked = conn.execute("SELECT fingerprint FROM extraction_audit_dataset WHERE id = 1").fetchone()
    if locked and locked["fingerprint"] != sample["fingerprint"]:
        raise ValueError("Sampel audit berubah sejak penilaian dimulai. Pulihkan sampel semula.")


def can_review(conn: sqlite3.Connection, user_id: int, role: str) -> bool:
    if role == "admin":
        return True
    return conn.execute(
        "SELECT 1 FROM extraction_audit_assignment WHERE user_id = ?", (user_id,)
    ).fetchone() is not None


def reviewer_state(conn: sqlite3.Connection, sample: dict, user_id: int, index: int) -> dict:
    check_dataset(conn, sample)
    records = sample["records"]
    if index < 0 or index >= len(records):
        raise IndexError("Nomor sampel di luar rentang.")
    judgments = conn.execute(
        """SELECT archive_id, field_name, verdict, note FROM extraction_audit_judgment
           WHERE user_id = ?""", (user_id,),
    ).fetchall()
    by_archive = {(row["archive_id"], row["field_name"]): dict(row) for row in judgments}
    completed_cells = sum(row["verdict"] is not None for row in judgments)
    completed_samples = sum(
        all(by_archive.get((record["archive_id"], field), {}).get("verdict") is not None
            for field in FIELDS)
        for record in records
    )
    results = {}
    for field in FIELDS:
        values = [row["verdict"] for row in judgments
                  if row["field_name"] == field and row["verdict"] is not None]
        results[field] = {
            "rated": len(values),
            "total": len(records),
            "status": "belum" if not values else (
                "final" if len(values) == len(records) else "sementara"
            ),
            "metrics": calculate_field_audit_metrics(values) if values else None,
        }
    record = records[index]
    return {
        "fingerprint": sample["fingerprint"],
        "extractor_version": sample["extractor_version"],
        "source_filename": sample["source_filename"],
        "index": index,
        "total_samples": len(records),
        "completed_samples": completed_samples,
        "completed_cells": completed_cells,
        "total_cells": len(records) * len(FIELDS),
        "final": completed_cells == len(records) * len(FIELDS),
        "sample": record,
        "judgments": {
            field: {
                "verdict": by_archive.get((record["archive_id"], field), {}).get("verdict"),
                "note": by_archive.get((record["archive_id"], field), {}).get("note", ""),
            }
            for field in FIELDS
        },
        "results": results,
    }


def save_judgment(conn: sqlite3.Connection, sample: dict, user_id: int, archive_id: int,
                  field: str, verdict: str | None, note: str) -> bool:
    if field not in FIELDS or verdict not in VALID_VERDICTS and verdict is not None:
        raise ValueError("Nilai penilaian tidak valid.")
    if archive_id not in {row["archive_id"] for row in sample["records"]}:
        raise LookupError("Arsip tidak ada dalam sampel audit.")
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        check_dataset(conn, sample)
        old = conn.execute(
            """SELECT verdict, note FROM extraction_audit_judgment
               WHERE user_id = ? AND archive_id = ? AND field_name = ?""",
            (user_id, archive_id, field),
        ).fetchone()
        if old is None and verdict is None and not note:
            return False
        if old and old["verdict"] == verdict and old["note"] == note:
            return False
        conn.execute(
            """INSERT OR IGNORE INTO extraction_audit_dataset
               (id, fingerprint, sample_count, source_filename, created_at)
               VALUES (1, ?, ?, ?, ?)""",
            (sample["fingerprint"], len(sample["records"]), sample["source_filename"], now),
        )
        check_dataset(conn, sample)
        if verdict is None and not note:
            conn.execute(
                """DELETE FROM extraction_audit_judgment
                   WHERE user_id = ? AND archive_id = ? AND field_name = ?""",
                (user_id, archive_id, field),
            )
        else:
            conn.execute(
                """INSERT INTO extraction_audit_judgment
                   (user_id, archive_id, field_name, verdict, note, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, archive_id, field_name) DO UPDATE SET
                   verdict = excluded.verdict, note = excluded.note,
                   updated_at = excluded.updated_at""",
                (user_id, archive_id, field, verdict, note, now),
            )
        conn.execute(
            """INSERT INTO extraction_audit_change
               (user_id, archive_id, field_name, old_verdict, new_verdict, note, changed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, archive_id, field, old["verdict"] if old else None, verdict, note, now),
        )
        conn.execute(
            """INSERT INTO activity_log(user_id, action, detail, created_at)
               VALUES (?, 'audit_extraction_judgment', ?, ?)""",
            (user_id, json.dumps({"archive_id": archive_id, "field": field}), now),
        )
    return True


def export_completed_csv(conn: sqlite3.Connection, sample: dict, user_id: int) -> str:
    state = reviewer_state(conn, sample, user_id, 0)
    if not state["final"]:
        raise ValueError("Seluruh sel sampel audit harus dinilai sebelum ekspor untuk skrip.")
    judgments = conn.execute(
        "SELECT archive_id, field_name, verdict, note FROM extraction_audit_judgment WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    by_key = {(row["archive_id"], row["field_name"]): row for row in judgments}
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for record in sample["records"]:
        row = dict(record)
        notes = []
        for field in FIELDS:
            judgment = by_key[(record["archive_id"], field)]
            row[f"verdict_{field}"] = judgment["verdict"]
            if judgment["note"]:
                notes.append(f"{field}: {judgment['note']}")
        row["auditor_notes"] = " | ".join(notes)
        writer.writerow(row)
    return output.getvalue()
