"""Skrip CLI untuk mengimpor berkas dump SQL e-Arsip SIMANIS ke SQLite lokal."""
import argparse
import os
import sys
from pathlib import Path

from services.importer import REFERENCE_COUNTS, import_simanis_dump

DEFAULT_SOURCE = os.environ.get(
    "SIMANIS_DUMP_PATH",
    r"D:\Coding\earsip\alsys_arsip(1).sql",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impor dump SQL e-Arsip SIMANIS ke database SQLite lokal."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Path berkas dump SQL (default dari env atau path lokal).",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path berkas basis data SQLite tujuan (default: instance/app.sqlite).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Lewati verifikasi ketat kelima angka acuan.",
    )
    parser.add_argument(
        "--imported-by",
        default="admin",
        help="Identitas pengimpor yang dicatat pada batch_import.",
    )

    args = parser.parse_args()
    source_path = Path(args.source)

    if not source_path.is_file():
        print(f"[GALAT] Berkas dump tidak ditemukan: {source_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Memulai impor dump SQL: {source_path}")
    try:
        summary = import_simanis_dump(
            dump_path=source_path,
            db_path=args.db,
            verify_reference_counts=not args.no_verify,
            imported_by=args.imported_by,
        )
    except Exception as exc:
        print(f"[GALAT] Gagal mengimpor dump: {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n[+] Impor berhasil diselesaikan!")
    print(f"    - ID Batch Impor   : {summary['batch_id']}")
    print(f"    - Hash SHA-256     : {summary['source_sha256']}")
    print(f"    - Total Arsip      : {summary['raw_count']} baris")
    print(f"    - Arsip Bersih     : {summary['clean_count']} baris")
    print(f"    - Masalah Data     : {summary['issue_count']} isu")

    print("\n[*] Pemeriksaan Kelima Angka Acuan:")
    actual = summary["actual_counts"]
    for key, expected_val in REFERENCE_COUNTS.items():
        act_val = actual.get(key, 0)
        status = "COCOK" if act_val == expected_val else "TIDAK COCOK"
        print(f"    - {key:<24}: {act_val} (Acuan: {expected_val}) [{status}]")

    print("\n[+] Seluruh data tersimpan aman pada SQLite lokal.\n")


if __name__ == "__main__":
    main()
