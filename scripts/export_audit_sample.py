"""Ekspor 100 sampel berstrata acak (seed 42) untuk audit manual ekstraksi metadata."""
import argparse
import csv
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from services.db import DEFAULT_DB_PATH

AUDIT_SAMPLE_SIZE = 100
AGREEMENT_SAMPLE_SIZE = 20
SAMPLE_SEED = 42
EXTRACTOR_VERSION = "v1.0.0"


def generate_stratified_sample(
    db_path: Path,
    sample_size: int = AUDIT_SAMPLE_SIZE,
    seed: int = SAMPLE_SEED,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Tarik sampel acak berstrata dari basis data arsip.

    Strata:
    1. Keberadaan label No SPM (1 vs 0)
    2. Status arsip (1: In Aktif, 2: Statis)
    3. Kode jenis SPM (LS, UP, GU, TU, BT, BS, PK, LAINNYA, NONE)
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = """
    SELECT
        a.id AS archive_id,
        a.status AS archive_status,
        a.summary_raw,
        m.has_spm_label,
        m.spm_number,
        m.spm_sequence,
        m.spm_type_code,
        m.spm_suffix,
        m.sp2d_number,
        m.document_date,
        m.amount_rp,
        m.party_name
    FROM archive a
    JOIN archive_metadata m ON a.id = m.archive_id
    ORDER BY a.id ASC;
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    total_pop = len(rows)
    if total_pop == 0:
        raise ValueError("Basis data kosong. Silakan impor data terlebih dahulu.")

    # Kelompokkan ke strata
    strata_map: Dict[str, List[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        label_str = "SPM_LABEL_YA" if r["has_spm_label"] else "SPM_LABEL_TIDAK"
        status_str = "IN_AKTIF" if r["archive_status"] == 1 else "STATIS"
        spm_type = str(r["spm_type_code"]).upper() if r["spm_type_code"] else "NONE"
        if spm_type not in {"LS", "UP", "GU", "TU", "BT", "BS", "PK", "NONE"}:
            spm_type = "LAINNYA"
        stratum_key = f"{label_str}|{status_str}|{spm_type}"
        strata_map[stratum_key].append(r)

    rng = random.Random(seed)
    sampled_rows: List[sqlite3.Row] = []
    strata_report: Dict[str, Dict[str, int]] = {}

    # Alokasi proporsional dengan pembulatan
    allocated_quotas: Dict[str, int] = {}
    remainders: List[Tuple[float, str]] = []
    for s_key, s_items in strata_map.items():
        quota_float = (len(s_items) / total_pop) * sample_size
        quota_int = int(quota_float)
        allocated_quotas[s_key] = quota_int
        remainders.append((quota_float - quota_int, s_key))

    # Tambahkan sisa kuota ke nilai pecahan terbesar
    missing = sample_size - sum(allocated_quotas.values())
    remainders.sort(reverse=True, key=lambda x: x[0])
    for i in range(missing):
        allocated_quotas[remainders[i][1]] += 1

    # Ambil sampel acak per strata
    for s_key, s_items in strata_map.items():
        k = allocated_quotas[s_key]
        shuffled = list(s_items)
        rng.shuffle(shuffled)
        sampled_rows.extend(shuffled[:k])
        strata_report[s_key] = {
            "populasi": len(s_items),
            "kuota_sampel": k,
        }

    # Acak urutan seluruh sampel akhir dengan seed
    rng.shuffle(sampled_rows)

    records: List[Dict[str, object]] = []
    for idx, r in enumerate(sampled_rows, start=1):
        records.append({
            "sample_id": idx,
            "archive_id": r["archive_id"],
            "archive_status": r["archive_status"],
            "summary_raw": r["summary_raw"],
            "extracted_spm": r["spm_number"] or "",
            "extracted_sp2d": r["sp2d_number"] or "",
            "extracted_date": r["document_date"] or "",
            "extracted_amount": r["amount_rp"] or "",
            "extracted_party": r["party_name"] or "",
        })

    metadata = {
        "extractor_version": EXTRACTOR_VERSION,
        "seed": seed,
        "total_population": total_pop,
        "sample_size": sample_size,
        "strata_detail": strata_report,
    }
    return records, metadata


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ekspor sampel audit acak berstrata untuk evaluasi ekstraksi."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path berkas database SQLite.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Direktori penyimpanan berkas output (diabaikan Git).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SAMPLE_SEED,
        help="Nilai random seed (default: 42).",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        sample_records, meta = generate_stratified_sample(
            db_path=Path(args.db),
            sample_size=AUDIT_SAMPLE_SIZE,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"[GALAT] Gagal membuat sampel audit: {exc}", file=sys.stderr)
        sys.exit(1)

    # 1. Simpan berkas audit utama 100 baris
    audit_csv_path = out_dir / "audit_extraction_sample.csv"
    fieldnames = [
        "sample_id", "archive_id", "archive_status", "summary_raw",
        "extracted_spm", "verdict_spm", "missed_spm",
        "extracted_sp2d", "verdict_sp2d", "missed_sp2d",
        "extracted_date", "verdict_date", "missed_date",
        "extracted_amount", "verdict_amount", "missed_amount",
        "extracted_party", "verdict_party", "missed_party",
        "auditor_notes",
    ]

    with open(audit_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in sample_records:
            row = dict(rec)
            for fld in ["verdict_spm", "missed_spm", "verdict_sp2d", "missed_sp2d",
                        "verdict_date", "missed_date", "verdict_amount", "missed_amount",
                        "verdict_party", "missed_party", "auditor_notes"]:
                row[fld] = ""
            writer.writerow(row)

    # 2. Simpan sampel 20 baris ganda untuk uji kesepakatan (percentage agreement)
    agreement_csv_path = out_dir / "audit_agreement_sample.csv"
    rng = random.Random(args.seed + 999)
    agreement_pool = list(sample_records)
    rng.shuffle(agreement_pool)
    agreement_records = agreement_pool[:AGREEMENT_SAMPLE_SIZE]

    with open(agreement_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, rec in enumerate(agreement_records, start=1):
            row = dict(rec)
            row["sample_id"] = idx
            for fld in ["verdict_spm", "missed_spm", "verdict_sp2d", "missed_sp2d",
                        "verdict_date", "missed_date", "verdict_amount", "missed_amount",
                        "verdict_party", "missed_party", "auditor_notes"]:
                row[fld] = ""
            writer.writerow(row)

    # 3. Simpan ringkasan strata
    meta_json_path = out_dir / "audit_strata_summary.json"
    meta_json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[+] Penarikan sampel audit ekstraksi berhasil!")
    print(f"    - Ekstraktor Versi : {meta['extractor_version']}")
    print(f"    - Random Seed      : {meta['seed']}")
    print(f"    - Total Populasi   : {meta['total_population']} arsip")
    print(f"    - Sampel Utama     : {len(sample_records)} baris -> {audit_csv_path}")
    print(f"    - Sampel Kesepakatan: {len(agreement_records)} baris -> {agreement_csv_path}")
    print(f"    - Metadata Strata  : {meta_json_path}")
    print("\n[Instruksi Manual]")
    print("Isi kolom verdict_* dengan salah satu nilai:")
    print("  'benar'             : Ekstraksi tepat.")
    print("  'salah'             : Ekstraksi salah/keliru.")
    print("  'tidak_ada_di_teks' : Teks memang tidak memuat field ini.")
    print("Jika ada nilai di teks tetapi tidak terekstrak, isi kolom missed_*.\n")


if __name__ == "__main__":
    main()
