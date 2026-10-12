"""Hitung persentase kesepakatan (percentage agreement) relevansi antara peneliti dan arsiparis."""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.audit_metrics import calculate_percentage_agreement

DEFAULT_MAIN_CSV = Path("output/relevance_pool.csv")
DEFAULT_VERIF_CSV = Path("output/relevance_verification_sample.csv")
DEFAULT_OUTPUT_JSON = Path("output/relevance_agreement_report.json")


def evaluate_relevance_agreement(
    main_csv_path: Path,
    verif_csv_path: Path,
) -> Dict[str, object]:
    """Hitung kesepakatan penilaian relevansi antara peneliti dan arsiparis."""
    if not main_csv_path.is_file():
        raise FileNotFoundError(f"Berkas penilaian utama tidak ditemukan: {main_csv_path}")
    if not verif_csv_path.is_file():
        raise FileNotFoundError(f"Berkas sampel verifikasi tidak ditemukan: {verif_csv_path}")

    with open(main_csv_path, "r", encoding="utf-8-sig") as f:
        main_rows = list(csv.DictReader(f))

    with open(verif_csv_path, "r", encoding="utf-8-sig") as f:
        verif_rows = list(csv.DictReader(f))

    if not verif_rows:
        raise ValueError("Berkas sampel verifikasi arsiparis kosong.")

    # Petakan penilaian peneliti: (query_id, archive_id) -> (is_relevant, query_type)
    researcher_map: Dict[str, Dict[str, str]] = {}
    for r in main_rows:
        key = f"{r['query_id']}_{r['archive_id']}"
        researcher_map[key] = {
            "is_relevant": r.get("is_relevant", "").strip(),
            "query_type": r.get("query_type", "umum"),
        }

    ratings_researcher: List[str] = []
    ratings_archivist: List[str] = []
    by_type_researcher: Dict[str, List[str]] = defaultdict(list)
    by_type_archivist: Dict[str, List[str]] = defaultdict(list)

    unfilled_count = 0
    for idx, r in enumerate(verif_rows, start=1):
        key = f"{r['query_id']}_{r['archive_id']}"
        val_arch = r.get("is_relevant", "").strip()
        if not val_arch:
            unfilled_count += 1
            raise ValueError(
                f"Baris verifikasi ke-{idx} (query={r['query_id']}, arsip={r['archive_id']}) "
                f"belum dinilai oleh arsiparis. Seluruh baris wajib dinilai."
            )

        if key not in researcher_map or not researcher_map[key]["is_relevant"]:
            raise ValueError(
                f"Baris verifikasi ke-{idx} (query={r['query_id']}, arsip={r['archive_id']}) "
                f"belum dinilai pada berkas utama peneliti."
            )

        val_res = researcher_map[key]["is_relevant"]
        q_type = r.get("query_type", researcher_map[key]["query_type"])

        # Standarkan nilai 1 atau 0
        norm_res = "1" if val_res in {"1", "true", "ya", "relevan"} else "0"
        norm_arch = "1" if val_arch in {"1", "true", "ya", "relevan"} else "0"

        ratings_researcher.append(norm_res)
        ratings_archivist.append(norm_arch)
        by_type_researcher[q_type].append(norm_res)
        by_type_archivist[q_type].append(norm_arch)

    overall_agreement = calculate_percentage_agreement(ratings_researcher, ratings_archivist)

    agreement_by_type = {}
    for q_type, r_list in by_type_researcher.items():
        a_list = by_type_archivist[q_type]
        agreement_by_type[q_type] = {
            "n_samples": len(r_list),
            "agreement": calculate_percentage_agreement(r_list, a_list),
        }

    return {
        "n_verification_samples": len(ratings_researcher),
        "overall_percentage_agreement": overall_agreement,
        "agreement_by_query_type": agreement_by_type,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hitung persentase kesepakatan penilaian relevansi peneliti vs arsiparis."
    )
    parser.add_argument(
        "--main-csv",
        default=str(DEFAULT_MAIN_CSV),
        help="Path berkas CSV penilaian pool utama peneliti.",
    )
    parser.add_argument(
        "--verif-csv",
        default=str(DEFAULT_VERIF_CSV),
        help="Path berkas CSV sampel verifikasi arsiparis.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path ekspor laporan hasil kesepakatan JSON.",
    )
    args = parser.parse_args()

    try:
        report = evaluate_relevance_agreement(
            main_csv_path=Path(args.main_csv),
            verif_csv_path=Path(args.verif_csv),
        )
    except Exception as exc:
        print(f"[GALAT] {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("HASIL UJI KESEPAKATAN RELEVANSI (PENELITI VS ARSIPARIS)")
    print("=" * 70)
    total_samples = report["n_verification_samples"]
    ov_pct = report["overall_percentage_agreement"] * 100.0
    print(f"Total Sampel Diverifikasi : {total_samples} baris")
    print(f"Kesepakatan Keseluruhan   : {ov_pct:>6.2f} %")
    print("-" * 70)
    print("Rincian per Jenis Kueri:")
    for q_type, detail in sorted(report["agreement_by_query_type"].items()):
        pct = detail["agreement"] * 100.0
        print(f"  - {q_type:<15} ({detail['n_samples']:>3} baris) : {pct:>6.2f} %")
    print("=" * 70)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[+] Laporan kesepakatan disimpan ke: {out_json}\n")


if __name__ == "__main__":
    main()
