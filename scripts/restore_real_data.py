"""Skrip untuk mengembalikan berkas CSV data nyata asli dari cadangan.

Gunakan skrip ini setelah izin resmi tertulis dari pihak dinas telah tercatat,
untuk mengembalikan berkas penilaian asli sebelum proses evaluasi akhir dilakukan.
"""
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
BACKUP_DIR = OUTPUT_DIR / ".real_data_backup"

TARGET_FILES = [
    "audit_extraction_sample.csv",
    "audit_agreement_sample.csv",
    "audit_strata_summary.json",
    "relevance_pool.csv",
    "relevance_pool_pilot_5.csv",
    "relevance_verification_sample.csv",
    ".candidate_queries.json",
]


def restore_real_data() -> None:
    """Pulihkan seluruh berkas asli dari folder cadangan."""
    if not BACKUP_DIR.is_dir():
        print(f"Folder cadangan {BACKUP_DIR} tidak ditemukan. Tidak ada data yang dapat dipulihkan.")
        return

    restored_count = 0
    for fname in TARGET_FILES:
        src = BACKUP_DIR / fname
        dst = OUTPUT_DIR / fname
        if src.is_file():
            shutil.copy2(src, dst)
            print(f"Dipulihkan: {fname} <- {src}")
            restored_count += 1
        else:
            print(f"Peringatan: Berkas cadangan {fname} tidak ditemukan di {BACKUP_DIR}")

    print(f"\nSelesai! {restored_count} berkas berhasil dipulihkan ke versi data nyata asli.")


if __name__ == "__main__":
    restore_real_data()
