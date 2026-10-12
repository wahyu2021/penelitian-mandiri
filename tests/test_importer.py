"""Uji unit untuk modul layanan basis data dan impor dump SQLite."""
import os
import sqlite3
from pathlib import Path

import pytest

from services.db import init_db
from services.importer import REFERENCE_COUNTS, import_simanis_dump

SYNTHETIC_SQL = """
INSERT INTO `apptb_opd` (`id_opd`, `nama_opd`) VALUES
(10, 'Dinas Komunikasi dan Informatika'),
(20, 'Dinas Pendidikan');

INSERT INTO `apptb_klasifikasi` (`id_klasifikasi`, `kode_klasifikasi`, `index`) VALUES
(1, '001', 'Umum');

INSERT INTO `apptb_arsip` (
    `id_arsip`, `opd_id`, `klasifikasi_id`, `user_id`, `no_berkas`, `index_ar`,
    `tahun`, `input_tahun`, `ringkasan`, `block`, `lokasi_rak`, `lokasi_baris`,
    `no_box`, `tingkat_perkembangan`, `jumlah`, `ket_berkas`, `ket_jra`,
    `stat_dokumen`, `dokumen`, `last_updates`
) VALUES
(
    1, '10', '1', '1', '01/2021', 'Arsip Uji', '2021', '2021-05-10',
    'Pembayaran termin I pengadaan komputer CV Contoh Mandiri No SPM : 123/LS/Diskominfo/2021',
    'A', '1', '1', '01', 'Asli', '1 Berkas', 'Lengkap', '10 Tahun', '1', 'berkas.pdf',
    '2021-05-10 10:00:00'
),
(
    2, '999', '1', '1', '02/2021', 'Arsip Yatim', '2021', '0000-00-00',
    'Arsip tanpa OPD valid dan tanggal input nol',
    'B', '2', '1', '02', 'Asli', '1 Berkas', 'Lengkap', 'Permanen', '2', '',
    '2021-05-10 10:00:00'
);
"""

REAL_DUMP_PATH = os.environ.get(
    "SIMANIS_DUMP_PATH",
    r"D:\Coding\earsip\alsys_arsip(1).sql",
)


def test_init_db_creates_tables_and_spm_types(tmp_path: Path):
    db_file = tmp_path / "test_init.sqlite"
    conn = init_db(db_file)
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    expected_tables = {
        "import_batch",
        "opd",
        "classification",
        "spm_type",
        "archive_raw",
        "archive",
        "archive_metadata",
        "data_issue",
    }
    assert expected_tables.issubset(set(tables))

    # Pastikan kamus SPM terisi minimal 7 kode awal
    spm_count = conn.execute("SELECT count(*) FROM spm_type;").fetchone()[0]
    assert spm_count >= 7
    conn.close()


def test_import_synthetic_dump_stores_all_layers(tmp_path: Path):
    sql_file = tmp_path / "synthetic.sql"
    sql_file.write_text(SYNTHETIC_SQL, encoding="latin-1")
    db_file = tmp_path / "synthetic.sqlite"

    summary = import_simanis_dump(
        dump_path=sql_file,
        db_path=db_file,
        verify_reference_counts=False,
        imported_by="tester",
    )

    assert summary["raw_count"] == 2
    assert summary["clean_count"] == 2
    assert summary["issue_count"] >= 2  # orphan OPD dan invalid_input_date

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    # Cek import_batch
    batch = conn.execute(
        "SELECT * FROM import_batch WHERE id = ?;", (summary["batch_id"],)
    ).fetchone()
    assert batch["status"] == "completed"
    assert batch["imported_by"] == "tester"

    # Cek archive_raw
    raw_rows = conn.execute("SELECT * FROM archive_raw ORDER BY id_arsip;").fetchall()
    assert len(raw_rows) == 2
    assert raw_rows[0]["no_berkas"] == "01/2021"

    # Cek archive
    clean_rows = conn.execute("SELECT * FROM archive ORDER BY id;").fetchall()
    assert len(clean_rows) == 2
    assert clean_rows[0]["opd_id"] == 10
    assert clean_rows[1]["opd_id"] is None  # orphan OPD menjadi NULL

    # Cek data_issue
    issues = conn.execute("SELECT * FROM data_issue WHERE archive_id = 2;").fetchall()
    issue_types = {i["issue_type"] for i in issues}
    assert "orphan_opd" in issue_types
    assert "invalid_input_date" in issue_types

    # Cek archive_metadata
    meta = conn.execute("SELECT * FROM archive_metadata WHERE archive_id = 1;").fetchone()
    assert meta["spm_sequence"] == "123"
    assert meta["spm_type_code"] == "LS"
    assert meta["has_spm_label"] == 1

    conn.close()


def test_import_strict_verification_fails_on_synthetic(tmp_path: Path):
    sql_file = tmp_path / "synthetic.sql"
    sql_file.write_text(SYNTHETIC_SQL, encoding="latin-1")
    db_file = tmp_path / "synthetic.sqlite"

    with pytest.raises(ValueError) as exc_info:
        import_simanis_dump(
            dump_path=sql_file,
            db_path=db_file,
            verify_reference_counts=True,
        )
    assert "Angka acuan dump tidak sesuai" in str(exc_info.value)


@pytest.mark.skipif(not os.path.isfile(REAL_DUMP_PATH), reason="Dump SIMANIS riil tidak tersedia")
def test_import_real_dump_verifies_all_five_reference_counts(tmp_path: Path):
    db_file = tmp_path / "real_test.sqlite"
    summary = import_simanis_dump(
        dump_path=REAL_DUMP_PATH,
        db_path=db_file,
        verify_reference_counts=True,
    )
    assert summary["reference_counts_match"] is True
    actual = summary["actual_counts"]
    for key, expected_val in REFERENCE_COUNTS.items():
        assert actual[key] == expected_val
