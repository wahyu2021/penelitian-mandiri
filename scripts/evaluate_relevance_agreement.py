"""Hitung kesepakatan relevansi peneliti dan petugas pada pasangan yang sama."""
import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.agreement import binary_agreement_summary

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

    with open(main_csv_path, "r", encoding="utf-8-sig", newline="") as f:
        main_rows = list(csv.DictReader(f))

    with open(verif_csv_path, "r", encoding="utf-8-sig", newline="") as f:
        verif_rows = list(csv.DictReader(f))

    if not verif_rows:
        raise ValueError("Berkas sampel verifikasi arsiparis kosong.")

    # Petakan penilaian peneliti: (query_id, archive_id) -> (is_relevant, query_type)
    researcher_map: Dict[str, Dict[str, str]] = {}
    for r in main_rows:
        key = f"{r['query_id']}_{r['archive_id']}"
        if key in researcher_map:
            raise ValueError(f"Pasangan kueri-arsip ganda pada berkas utama: {key}")
        researcher_map[key] = {
            "is_relevant": (r.get("is_relevant") or "").strip(),
            "query_type": r.get("query_type", "umum"),
        }

    ratings_researcher: List[str] = []
    ratings_archivist: List[str] = []
    query_types_list: List[str] = []

    seen_verification = set()
    for idx, r in enumerate(verif_rows, start=1):
        key = f"{r['query_id']}_{r['archive_id']}"
        if key in seen_verification:
            raise ValueError(f"Pasangan kueri-arsip ganda pada sampel verifikasi: {key}")
        seen_verification.add(key)
        val_arch = (r.get("is_relevant") or "").strip()
        if not val_arch:
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

        if val_res not in {"0", "1"} or val_arch not in {"0", "1"}:
            raise ValueError(f"Nilai relevansi harus 0 atau 1 pada pasangan {key}")

        ratings_researcher.append(val_res)
        ratings_archivist.append(val_arch)
        query_types_list.append(q_type)

    summary = binary_agreement_summary(
        list(zip(ratings_researcher, ratings_archivist)),
        n_expected=len(ratings_researcher),
        query_types=query_types_list,
    )
    matrix = summary["confusion_matrix"]
    notes = (
        "Kappa tidak terdefinisi karena kedua penilai hanya memakai satu kelas."
        if summary["cohen_kappa"] is None
        else "Dihitung dari penilaian biner 0/1 pada pasangan kueri-arsip yang sama."
    )

    return {
        "status": summary["status"],
        "n_samples": summary["n_paired"],
        "n_verification_samples": summary["n_paired"],
        "n_agreed": summary["n_agreed"],
        "percentage_agreement": summary["percentage_agreement"],
        "overall_percentage_agreement": summary["percentage_agreement"],
        "relevant_class_agreement": summary["relevant_class_agreement"],
        "cohen_kappa": summary["cohen_kappa"],
        "confusion_matrix": {
            "both_relevant": matrix["both_relevant"],
            "researcher_only_relevant": matrix["rater1_only_relevant"],
            "archivist_only_relevant": matrix["rater2_only_relevant"],
            "both_irrelevant": matrix["both_irrelevant"],
        },
        "notes": notes,
        "limitations": summary["limitations"],
        "agreement_by_query_type": summary["agreement_by_query_type"],
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
    print(f"Kesepakatan Kelas Relevan : {report['relevant_class_agreement']}")
    print(f"Cohen's Kappa             : {report['cohen_kappa']}")
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
