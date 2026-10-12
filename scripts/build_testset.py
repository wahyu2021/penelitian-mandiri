"""Bangun dan kunci berkas set uji JSON dari hasil penilaian relevansi pool."""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from core.testset.splitting import compute_content_sha256, split_queries_stratified_anti_leak

DEFAULT_POOL_CSV = Path("output/relevance_pool.csv")
DEFAULT_OUTPUT_JSON = Path("data/testset/testset_v1.json")
TESTSET_VERSION = "v1.0.0"
SPLIT_SEED = 42


def build_testset_from_pool(
    pool_csv_path: Path,
    output_json_path: Path,
    tuning_ratio: float = 0.30,
    seed: int = SPLIT_SEED,
) -> Dict[str, object]:
    if not pool_csv_path.is_file():
        raise FileNotFoundError(f"Berkas pool tidak ditemukan: {pool_csv_path}")

    with open(pool_csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Berkas pool CSV kosong.")

    # Kelompokkan baris pool per query_id
    query_map: Dict[str, Dict[str, object]] = {}
    judgments_by_query: Dict[str, List[Dict[str, int]]] = defaultdict(list)

    unjudged_count = 0
    for r in rows:
        q_id = r["query_id"]
        if q_id not in query_map:
            query_map[q_id] = {
                "query_id": q_id,
                "query_text": r["query_text"],
                "query_type": r.get("query_type", "umum"),
                "source": r.get("source", "sintetis"),
                "noise_type": r.get("noise_type", "tanpa_gangguan"),
                "origin_archive_id": (
                    int(r["origin_archive_id"]) if r.get("origin_archive_id") else None
                ),
                "spm_number": r.get("spm_number") or None,
            }

        rel_raw = r.get("is_relevant", "").strip()
        is_rel = 1 if rel_raw in {"1", "true", "ya", "relevan"} else 0
        if rel_raw == "":
            unjudged_count += 1

        judgments_by_query[q_id].append({
            "archive_id": int(r["archive_id"]),
            "is_relevant": is_rel,
        })

    queries_list = list(query_map.values())

    # Lakukan stratified split anti-leak
    tuning_q, test_q = split_queries_stratified_anti_leak(
        queries=queries_list,
        tuning_ratio=tuning_ratio,
        seed=seed,
    )

    all_queries = []
    for q in queries_list:
        q_entry = dict(q)
        q_entry["judgments"] = judgments_by_query[q["query_id"]]
        q_entry.pop("spm_number", None)
        all_queries.append(q_entry)

    testset_data = {
        "version": TESTSET_VERSION,
        "seed": seed,
        "tuning_ratio": tuning_ratio,
        "n_queries": len(all_queries),
        "n_tuning": len(tuning_q),
        "n_test": len(test_q),
        "unjudged_rows_count": unjudged_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "queries": all_queries,
    }

    # Format representasi kanonikal untuk perhitungan hash
    canonical_repr = json.dumps(testset_data, sort_keys=True, indent=2, ensure_ascii=False)
    content_hash = compute_content_sha256(canonical_repr)
    testset_data["content_sha256"] = content_hash

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    final_json = json.dumps(testset_data, indent=2, ensure_ascii=False)
    output_json_path.write_text(final_json, encoding="utf-8")

    return {
        "output_path": str(output_json_path),
        "content_sha256": content_hash,
        "n_queries": len(all_queries),
        "n_tuning": len(tuning_q),
        "n_test": len(test_q),
        "unjudged_rows": unjudged_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impor penilaian pool CSV dan bangun berkas testset JSON terkunci."
    )
    parser.add_argument(
        "--pool-csv",
        default=str(DEFAULT_POOL_CSV),
        help="Path berkas CSV hasil penilaian pool.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path berkas JSON set uji tujuan.",
    )
    parser.add_argument(
        "--tuning-ratio",
        type=float,
        default=0.30,
        help="Proporsi kelompok tuning (default: 0.30).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SPLIT_SEED,
        help="Random seed untuk pembagian (default: 42).",
    )
    args = parser.parse_args()

    try:
        res = build_testset_from_pool(
            pool_csv_path=Path(args.pool_csv),
            output_json_path=Path(args.output_json),
            tuning_ratio=args.tuning_ratio,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"[GALAT] Gagal membangun testset JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[+] Berkas set uji berhasil dibangun:")
    print(f"    - Berkas Tujuan    : {res['output_path']}")
    print(f"    - Hash SHA-256     : {res['content_sha256']}")
    print(f"    - Total Kueri      : {res['n_queries']}")
    print(f"    - Kueri Tuning     : {res['n_tuning']} (~30%)")
    print(f"    - Kueri Test       : {res['n_test']} (~70%)")
    if res['unjudged_rows'] > 0:
        print(
            f"    - [Catatan] Terdapat {res['unjudged_rows']} baris belum dinilai "
            f"(diasumsikan tidak relevan 0)."
        )
    print()


if __name__ == "__main__":
    main()
