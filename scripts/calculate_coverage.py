"""Hitung persentase cakupan (coverage) ekstraksi metadata dari database SQLite.

Skrip ini hanya melaporkan cakupan (keberadaan nilai yang berhasil diekstrak),
bukan akurasi. Akurasi hanya diperoleh melalui audit manual.
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Union

from services.db import DEFAULT_DB_PATH

EXTRACTOR_VERSION = "v1.0.0"


def calculate_extraction_coverage(
    db_path: Union[str, Path] = DEFAULT_DB_PATH,
) -> Dict[str, object]:
    """Hitung statistik cakupan ekstraksi metadata pada basis data.

    Args:
        db_path: Path berkas SQLite.

    Returns:
        Kamus statistik cakupan per field dan metadata batch.
    """
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Basis data tidak ditemukan: {path}")

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    total_records = conn.execute("SELECT COUNT(*) FROM archive;").fetchone()[0]
    if total_records == 0:
        conn.close()
        raise ValueError("Tabel archive kosong. Jalankan impor dump terlebih dahulu.")

    fields = [
        "spm_number",
        "spm_sequence",
        "spm_type_code",
        "spm_suffix",
        "sp2d_number",
        "document_date",
        "amount_rp",
        "party_name",
        "has_spm_label",
    ]

    stats: Dict[str, Dict[str, Union[int, float]]] = {}
    for f in fields:
        if f == "has_spm_label":
            count = conn.execute(
                "SELECT COUNT(*) FROM archive_metadata WHERE has_spm_label = 1;"
            ).fetchone()[0]
        else:
            count = conn.execute(
                f"SELECT COUNT(*) FROM archive_metadata WHERE {f} IS NOT NULL AND {f} != '';"
            ).fetchone()[0]
        percentage = (count / total_records) * 100.0
        stats[f] = {"count": count, "percentage": round(percentage, 2)}

    # Cakupan SPM bersyarat: dari dokumen yang memiliki label 'No SPM'
    labelled_count = stats["has_spm_label"]["count"]
    if labelled_count > 0:
        spm_extracted_on_label = conn.execute(
            """
            SELECT COUNT(*) FROM archive_metadata
            WHERE has_spm_label = 1 AND spm_number IS NOT NULL AND spm_number != '';
            """
        ).fetchone()[0]
        cond_pct = (spm_extracted_on_label / labelled_count) * 100.0
    else:
        spm_extracted_on_label = 0
        cond_pct = 0.0

    conn.close()
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "total_records": total_records,
        "field_coverage": stats,
        "spm_coverage_given_label": {
            "labelled_total": labelled_count,
            "extracted_count": spm_extracted_on_label,
            "percentage": round(cond_pct, 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hitung statistik cakupan (coverage) ekstraksi metadata."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path berkas basis data SQLite (default: instance/app.sqlite).",
    )
    args = parser.parse_args()

    try:
        report = calculate_extraction_coverage(args.db)
    except Exception as exc:
        print(f"[GALAT] Gagal menghitung cakupan: {exc}", file=sys.stderr)
        sys.exit(1)

    total = report["total_records"]
    print("=" * 65)
    print(f"LAPORAN CAKUPAN EKSTRAKSI METADATA (Versi: {report['extractor_version']})")
    print(f"Total Arsip pada Basis Data: {total} record")
    print("=" * 65)
    print(f"{'Nama Kolom Metadata':<25} | {'Jumlah Terisi':<14} | {'Cakupan (%)':<12}")
    print("-" * 65)

    labels = {
        "has_spm_label": "Label 'No SPM' ada",
        "spm_number": "Nomor SPM (Lengkap)",
        "spm_sequence": "Nomor Urut SPM",
        "spm_type_code": "Kode Jenis SPM",
        "spm_suffix": "Bagian Akhir SPM",
        "sp2d_number": "Nomor SP2D",
        "document_date": "Tanggal Dokumen",
        "amount_rp": "Nilai Rupiah (Rp)",
        "party_name": "Nama Pihak (CV/PT)",
    }

    cov = report["field_coverage"]
    for key, label in labels.items():
        data = cov[key]
        print(f"{label:<25} | {data['count']:<14} | {data['percentage']:>6.2f} %")

    cond = report["spm_coverage_given_label"]
    print("-" * 65)
    print(
        f"Cakupan SPM jika label ada: {cond['extracted_count']}/{cond['labelled_total']} "
        f"({cond['percentage']:.2f} %)"
    )
    print("=" * 65)
    print("[Catatan] Angka di atas menunjukkan cakupan, bukan akurasi.")
    print("          Akurasi hanya dihitung melalui audit sampel manual.\n")


if __name__ == "__main__":
    main()
