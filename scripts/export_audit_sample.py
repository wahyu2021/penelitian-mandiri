"""Ekspor 100 sampel berstrata acak (seed 42) untuk audit manual ekstraksi metadata."""
import argparse
import csv
import hashlib
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.db import DEFAULT_DB_PATH

AUDIT_SAMPLE_SIZE = 100
AGREEMENT_SAMPLE_SIZE = 20
SAMPLE_SEED = 42
EXTRACTOR_VERSION = "v1.0.0"

AUDIT_FIELDNAMES = [
    "sample_id", "archive_id", "archive_status", "summary_raw",
    "extracted_spm", "verdict_spm",
    "extracted_sp2d", "verdict_sp2d",
    "extracted_date", "verdict_date",
    "extracted_amount", "verdict_amount",
    "extracted_party", "verdict_party",
    "auditor_notes",
]


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
    strata: Dict[Tuple[int, int, str], List[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        key = (
            int(r["has_spm_label"]),
            int(r["archive_status"]),
            str(r["spm_type_code"] or "NONE"),
        )
        strata[key].append(r)

    # Hitung kuota sampel proporsional per stratum
    rng = random.Random(seed)
    sampled_rows: List[sqlite3.Row] = []
    strata_report: List[Dict[str, object]] = []

    remaining_needed = sample_size
    sorted_strata_keys = sorted(strata.keys(), key=lambda k: len(strata[k]), reverse=True)

    for key in sorted_strata_keys:
        group = strata[key]
        n_group = len(group)
        quota = int(round((n_group / total_pop) * sample_size))
        if quota == 0 and n_group > 0 and remaining_needed > 0:
            quota = 1
        quota = min(quota, n_group, remaining_needed)
        remaining_needed -= quota

        picked = rng.sample(group, quota)
        sampled_rows.extend(picked)
        strata_report.append({
            "has_spm_label": key[0],
            "archive_status": key[1],
            "spm_type_code": key[2],
            "population_count": n_group,
            "sample_quota": quota,
        })

    # Jika masih ada sisa karena pembulatan, ambil dari sisa populasi
    if len(sampled_rows) < sample_size:
        picked_ids = {r["archive_id"] for r in sampled_rows}
        unpicked = [r for r in rows if r["archive_id"] not in picked_ids]
        needed = sample_size - len(sampled_rows)
        sampled_rows.extend(rng.sample(unpicked, needed))

    # Acak urutan sampel akhir agar nomor urut tidak mengelompokkan strata
    rng.shuffle(sampled_rows)

    records: List[Dict[str, object]] = []
    for idx, r in enumerate(sampled_rows, start=1):
        records.append({
            "sample_id": idx,
            "archive_id": r["archive_id"],
            "archive_status": r["archive_status"],
            "summary_raw": r["summary_raw"] or "",
            "extracted_spm": r["spm_number"] or "",
            "extracted_sp2d": r["sp2d_number"] or "",
            "extracted_date": r["document_date"] or "",
            "extracted_amount": str(r["amount_rp"]) if r["amount_rp"] is not None else "",
            "extracted_party": r["party_name"] or "",
        })

    # Hitung hash data ekstraksi untuk verifikasi anti-tamper
    extracted_canonical = json.dumps(
        [
            {
                "archive_id": rec["archive_id"],
                "summary_raw": rec["summary_raw"],
                "spm": rec["extracted_spm"],
                "sp2d": rec["extracted_sp2d"],
                "date": rec["extracted_date"],
                "amount": rec["extracted_amount"],
                "party": rec["extracted_party"],
            }
            for rec in records
        ],
        sort_keys=True,
    )
    extracted_sha256 = hashlib.sha256(extracted_canonical.encode("utf-8")).hexdigest()

    metadata = {
        "extractor_version": EXTRACTOR_VERSION,
        "seed": seed,
        "total_population": total_pop,
        "sample_size": sample_size,
        "extracted_data_sha256": extracted_sha256,
        "sample_archive_ids": [rec["archive_id"] for rec in records],
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

    # 1. Simpan berkas audit utama 100 baris (verdict kosong, tanpa missed)
    audit_csv_path = out_dir / "audit_extraction_sample.csv"
    verdict_fields = [
        "verdict_spm", "verdict_sp2d", "verdict_date",
        "verdict_amount", "verdict_party", "auditor_notes",
    ]

    with open(audit_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDNAMES)
        writer.writeheader()
        for rec in sample_records:
            row = dict(rec)
            for fld in verdict_fields:
                row[fld] = ""
            writer.writerow(row)

    # 2. Simpan sampel 20 baris ganda untuk uji kesepakatan penilai kedua
    # Penilai kedua menilai tanpa melihat jawaban penilai pertama
    agreement_csv_path = out_dir / "audit_agreement_sample.csv"
    rng = random.Random(args.seed + 999)
    agreement_pool = list(sample_records)
    rng.shuffle(agreement_pool)
    agreement_records = agreement_pool[:AGREEMENT_SAMPLE_SIZE]

    with open(agreement_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDNAMES)
        writer.writeheader()
        for idx, rec in enumerate(agreement_records, start=1):
            row = dict(rec)
            row["sample_id"] = idx
            for fld in verdict_fields:
                row[fld] = ""
            writer.writerow(row)

    # 3. Simpan manifest metadata strata dan hash verifikasi
    meta_json_path = out_dir / "audit_strata_summary.json"
    meta_json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[+] Penarikan sampel audit ekstraksi berhasil!")
    print(f"    - Ekstraktor Versi  : {meta['extractor_version']}")
    print(f"    - Random Seed       : {meta['seed']}")
    print(f"    - Total Populasi    : {meta['total_population']} arsip")
    print(f"    - Sampel Utama      : {len(sample_records)} baris -> {audit_csv_path}")
    print(f"    - Sampel Kesepakatan: {len(agreement_records)} baris -> {agreement_csv_path}")
    print(f"    - Metadata & Hash   : {meta_json_path}")
    print("\n[Petunjuk Pengisian]")
    print("Isi setiap kolom verdict_* dengan salah satu dari 4 kata baku:")
    print("  'benar'             : Ekstraksi tepat sesuai teks.")
    print("  'salah'             : Ekstraksi ada tetapi keliru/terpotong/berlebih.")
    print("  'terlewat'          : Teks memuat data tetapi ekstraksi kosong.")
    print("  'tidak_ada_di_teks' : Teks tidak memuat data dan ekstraksi kosong.")
    print("Peringatan: Seluruh sel wajib diisi. Sel kosong akan ditolak oleh skrip evaluasi.\n")


if __name__ == "__main__":
    main()
