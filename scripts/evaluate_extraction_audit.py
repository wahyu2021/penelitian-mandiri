"""Evaluasi hasil audit manual ekstraksi metadata dari berkas CSV penilaian."""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

from core.evaluation.audit_metrics import (
    calculate_field_audit_metrics,
    calculate_percentage_agreement,
)

FIELDS = ["spm", "sp2d", "date", "amount", "party"]
FIELD_LABELS = {
    "spm": "Nomor SPM",
    "sp2d": "Nomor SP2D",
    "date": "Tanggal Dokumen",
    "amount": "Nilai Rupiah",
    "party": "Nama Pihak (CV/PT)",
}


def read_audit_file(csv_path: Path) -> List[Dict[str, str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Berkas audit tidak ditemukan: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def evaluate_audit_csv(
    audit_rows: List[Dict[str, str]],
    agreement_rows: List[Dict[str, str]] = None,
) -> Dict[str, object]:
    results = {}
    unfilled = 0

    for fld in FIELDS:
        verdicts = []
        missed_flags = []
        for r in audit_rows:
            v = r.get(f"verdict_{fld}", "").strip()
            if not v:
                unfilled += 1
            verdicts.append(v or "tidak_ada_di_teks")
            missed = bool(r.get(f"missed_{fld}", "").strip())
            missed_flags.append(missed)

        field_res = calculate_field_audit_metrics(verdicts, missed_flags)
        results[fld] = field_res

    agreement_res = {}
    if agreement_rows:
        # Cocokkan berdasarkan archive_id
        map_b = {r["archive_id"]: r for r in agreement_rows}
        for fld in FIELDS:
            a_ratings = []
            b_ratings = []
            for r in audit_rows:
                arch_id = r["archive_id"]
                if arch_id in map_b:
                    a_val = r.get(f"verdict_{fld}", "").strip() or "none"
                    b_val = map_b[arch_id].get(f"verdict_{fld}", "").strip() or "none"
                    a_ratings.append(a_val)
                    b_ratings.append(b_val)
            if a_ratings:
                agreement_res[fld] = calculate_percentage_agreement(a_ratings, b_ratings)

    return {
        "fields": results,
        "agreement": agreement_res,
        "unfilled_count": unfilled,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hitung akurasi audit ekstraksi dan persentase kesepakatan."
    )
    parser.add_argument(
        "--audit-csv",
        default="output/audit_extraction_sample.csv",
        help="Path berkas CSV audit utama yang telah dinilai.",
    )
    parser.add_argument(
        "--agreement-csv",
        default="output/audit_agreement_sample.csv",
        help="Path berkas CSV penilaian ganda untuk uji kesepakatan.",
    )
    parser.add_argument(
        "--export-json",
        default="output/extraction_audit_report.json",
        help="Path ekspor ringkasan hasil audit format JSON.",
    )
    args = parser.parse_args()

    audit_path = Path(args.audit_csv)
    agree_path = Path(args.agreement_csv)

    try:
        audit_rows = read_audit_file(audit_path)
    except Exception as exc:
        print(f"[GALAT] Gagal membaca berkas audit: {exc}", file=sys.stderr)
        sys.exit(1)

    agree_rows = None
    if agree_path.is_file():
        agree_rows = read_audit_file(agree_path)

    report = evaluate_audit_csv(audit_rows, agree_rows)

    if report["unfilled_count"] > 0:
        print(
            f"[PERINGATAN] Terdapat {report['unfilled_count']} sel verdict kosong. "
            f"Baris kosong diasumsikan 'tidak_ada_di_teks'.\n"
        )

    print("=" * 80)
    print("HASIL AUDIT AKURASI EKSTRAKSI METADATA (100 SAMPEL BERSTRATA)")
    print("=" * 80)
    print(
        f"{'Field':<18} | {'Benar':<6} | {'Salah':<6} | {'Miss':<5} | "
        f"{'Akurasi (%)':<12} | {'95% CI Wilson':<16}"
    )
    print("-" * 80)

    for fld in FIELDS:
        res = report["fields"][fld]
        pct = res["accuracy_extracted"] * 100.0
        low_ci = res["wilson_ci_extracted"][0] * 100.0
        high_ci = res["wilson_ci_extracted"][1] * 100.0
        ci_str = f"[{low_ci:>5.1f}%, {high_ci:>5.1f}%]"

        print(
            f"{FIELD_LABELS[fld]:<18} | {res['n_benar']:<6} | {res['n_salah']:<6} | "
            f"{res['n_missed']:<5} | {pct:>6.2f} %     | {ci_str:<16}"
        )

    if report["agreement"]:
        print("-" * 80)
        print("PERSENTASE KESEPAKATAN (PERCENTAGE AGREEMENT - 20 SAMPEL GANDA):")
        for fld in FIELDS:
            agr_pct = report["agreement"][fld] * 100.0
            print(f"  - {FIELD_LABELS[fld]:<20}: {agr_pct:>6.2f} %")
        macro_agr = sum(report["agreement"].values()) / len(report["agreement"]) * 100.0
        print(f"  * Rata-rata Makro    : {macro_agr:>6.2f} %")

    print("=" * 80)

    # Simpan hasil JSON
    export_path = Path(args.export_json)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[+] Ringkasan audit disimpan ke: {export_path}\n")


if __name__ == "__main__":
    main()
