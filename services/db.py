"""Modul basis data SQLite lokal untuk sistem pencarian arsip.

Menyediakan fungsi inisialisasi skema basis data SQLite murni tanpa ketergantungan
pada kerangka kerja web (Flask/SQLAlchemy).
"""
import sqlite3
from pathlib import Path
from typing import Optional, Union

from core.spm_types import CONFIDENCE_GUESS, SPM_TYPE_CATALOG

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "instance" / "app.sqlite"

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS import_batch (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_filename TEXT NOT NULL,
        source_sha256 TEXT NOT NULL,
        parser_version TEXT NOT NULL,
        extractor_version TEXT NOT NULL,
        raw_count INTEGER NOT NULL DEFAULT 0,
        clean_count INTEGER NOT NULL DEFAULT 0,
        issue_count INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'completed',
        error_message TEXT,
        imported_by TEXT NOT NULL DEFAULT 'system',
        imported_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS opd (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        name_normalized TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS classification (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS spm_type (
        code TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        confidence TEXT NOT NULL CHECK (confidence IN ('dugaan', 'terkonfirmasi')),
        source_note TEXT,
        confirmed_by TEXT,
        confirmed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS archive_raw (
        id_arsip INTEGER PRIMARY KEY,
        batch_id INTEGER NOT NULL REFERENCES import_batch(id),
        opd_id TEXT,
        klasifikasi_id TEXT,
        user_id TEXT,
        no_berkas TEXT,
        index_ar TEXT,
        tahun TEXT,
        input_tahun TEXT,
        ringkasan TEXT,
        block TEXT,
        lokasi_rak TEXT,
        lokasi_baris TEXT,
        no_box TEXT,
        tingkat_perkembangan TEXT,
        jumlah TEXT,
        ket_berkas TEXT,
        ket_jra TEXT,
        stat_dokumen TEXT,
        dokumen TEXT,
        last_updates TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS archive (
        id INTEGER PRIMARY KEY,
        batch_id INTEGER NOT NULL REFERENCES import_batch(id),
        opd_id INTEGER REFERENCES opd(id),
        opd_id_source INTEGER NOT NULL,
        classification_id INTEGER REFERENCES classification(id),
        year INTEGER,
        input_date TEXT,
        file_number TEXT,
        index_label TEXT,
        summary_raw TEXT,
        summary_clean TEXT,
        summary_normalized TEXT,
        location_block TEXT,
        location_rack TEXT,
        location_row TEXT,
        box_number TEXT,
        development_level TEXT,
        quantity_label TEXT,
        file_note TEXT,
        retention_note TEXT,
        status INTEGER NOT NULL CHECK (status IN (1, 2, 3)),
        document_filename TEXT,
        has_document INTEGER NOT NULL CHECK (has_document IN (0, 1))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS archive_metadata (
        archive_id INTEGER PRIMARY KEY REFERENCES archive(id),
        spm_number TEXT,
        spm_sequence TEXT,
        spm_type_code TEXT REFERENCES spm_type(code),
        spm_suffix TEXT,
        sp2d_number TEXT,
        document_date TEXT,
        amount_rp INTEGER,
        party_name TEXT,
        party_normalized TEXT,
        has_spm_label INTEGER NOT NULL CHECK (has_spm_label IN (0, 1)),
        extractor_version TEXT NOT NULL,
        extracted_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS data_issue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        archive_id INTEGER NOT NULL REFERENCES archive(id),
        batch_id INTEGER NOT NULL REFERENCES import_batch(id),
        issue_type TEXT NOT NULL,
        field_name TEXT NOT NULL,
        raw_value TEXT,
        detail TEXT
    );
    """,
]


def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Buka koneksi SQLite dengan pengaturan foreign keys aktif.

    Args:
        db_path: Lokasi berkas basis data SQLite. Default ke `instance/app.sqlite`.

    Returns:
        Objek koneksi SQLite.
    """
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Inisialisasi tabel basis data dan isi kamus awal jenis SPM berstatus dugaan.

    Args:
        db_path: Lokasi berkas basis data SQLite (opsional).

    Returns:
        Objek koneksi SQLite yang telah terinisialisasi.
    """
    conn = get_connection(db_path)
    with conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)

        # Inisialisasi entri awal kamus jenis SPM berstatus dugaan
        for code, label in SPM_TYPE_CATALOG.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO spm_type (code, label, confidence, source_note)
                VALUES (?, ?, ?, ?);
                """,
                (code, label, CONFIDENCE_GUESS, "Kamus awal bawaan prototype SIMANIS"),
            )
    return conn
