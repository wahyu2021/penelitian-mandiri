"""CLI untuk penyetelan bobot field perangkingan pada kelompok tuning."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

from core.evaluation.tuning import tune_weights_grid_search
from core.search.index import SearchIndex
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from services.db import DEFAULT_DB_PATH

DEFAULT_TESTSET_PATH = Path("data/testset/testset_v1.json")
DEFAULT_OUTPUT_PATH = Path("data/testset/tuned_weights.json")
DEFAULT_ADDITIONAL_JUDGMENTS_PATH = Path("data/testset/additional_judgments_v1.json")


def load_corpus(db_path: Path) -> List[Dict[str, object]]:
    """Muat korpus arsip dari database SQLite."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    query = """
    SELECT
        a.id, a.opd_id, a.year, a.status, a.summary_clean, a.summary_raw,
        m.spm_number, m.party_name, o.name AS opd_name,
        a.file_number, c.name AS classification_label, a.index_label,
        a.location_block, a.location_rack, a.location_row, a.box_number,
        a.has_document
    FROM archive a
    LEFT JOIN archive_metadata m ON a.id = m.archive_id
    LEFT JOIN opd o ON a.opd_id = o.id
    LEFT JOIN classification c ON a.classification_id = c.id
    ORDER BY a.id ASC;
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_additional_judgments(
    path: Path,
) -> Optional[Dict[str, Dict[int, int]]]:
    """Muat penilaian tambahan jika berkas tersedia."""
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, Dict[int, int]] = {}
    for q_id, judgments in data.get("judgments_by_query", {}).items():
        result[str(q_id)] = {
            int(aid): int(rel) for aid, rel in judgments.items()
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jalankan grid search penyetelan bobot field pada kueri tuning."
    )
    parser.add_argument(
        "--testset",
        default=str(DEFAULT_TESTSET_PATH),
        help="Path berkas set uji JSON (default: data/testset/testset_v1.json)",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path database SQLite (default: instance/app.sqlite)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path penyimpanan hasil bobot optimal (default: data/testset/tuned_weights.json)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.1,
        help="Grid search step (default: 0.1)",
    )
    parser.add_argument(
        "--matcher",
        choices=["all", *FUZZY_METHOD_NAMES],
        default="all",
        help="Pencocok yang disetel (default: all)",
    )
    parser.add_argument(
        "--additional-judgments",
        default=str(DEFAULT_ADDITIONAL_JUDGMENTS_PATH),
        help="Path berkas penilaian tambahan opsional",
    )
    args = parser.parse_args()

    testset_file = Path(args.testset)
    if not testset_file.is_file():
        print(f"[GALAT] Berkas set uji tidak ditemukan: {testset_file}", file=sys.stderr)
        sys.exit(1)

    db_file = Path(args.db_path)
    if not db_file.is_file():
        print(f"[GALAT] Database tidak ditemukan: {db_file}", file=sys.stderr)
        sys.exit(1)

    with open(testset_file, "r", encoding="utf-8") as f:
        testset = json.load(f)

    # Isolasi ketat anti-data leakage: Hanya kueri kelompok tuning yang diproses.
    # Kueri kelompok 'test' sama sekali tidak boleh dibaca atau diakses saat tuning.
    all_raw_queries = testset.get("queries", [])
    tuning_queries = [q for q in all_raw_queries if q.get("split") == "tuning"]
    n_test_detected = sum(1 for q in all_raw_queries if q.get("split") == "test")
    del all_raw_queries  # Musnahkan kueri test dari ruang memori proses tuning

    if not tuning_queries:
        print("[GALAT] Tidak ada kueri dengan split 'tuning' dalam set uji.", file=sys.stderr)
        sys.exit(1)

    print(f"[+] Memuat korpus dari database: {db_file}")
    records = load_corpus(db_file)
    index = SearchIndex.from_records(records)
    print(f"    Total arsip terindeks: {len(records)}")
    print(f"    Total kueri tuning   : {len(tuning_queries)}")

    additional_judgments = load_additional_judgments(Path(args.additional_judgments))
    if additional_judgments:
        print(f"    Penilaian tambahan   : {len(additional_judgments)} kueri termuat")

    target_matchers = (
        FUZZY_METHOD_NAMES if args.matcher == "all" else [args.matcher]
    )

    tuning_summary: Dict[str, object] = {
        "testset_version": testset.get("version"),
        "testset_hash": testset.get("content_sha256"),
        "grid_step": args.step,
        "n_tuning_queries": len(tuning_queries),
        "results_by_matcher": {},
    }

    print("\n" + "=" * 80)
    print("HASIL PENYETELAN BOBOT (GRID SEARCH PADA KELOMPOK TUNING)")
    print("=" * 80)
    fmt = "{:<15} | {:<24} | {:<16} | {:<16}"
    header_str = fmt.format(
        "Metode", "Bobot Opt (Sum,SPM,Ptk)", "MRR@10 (Eq->Opt)", "P@5 (Eq->Opt)"
    )
    print(header_str)
    print("-" * 80)

    for m_name in target_matchers:
        matcher = create_matcher(m_name)
        res = tune_weights_grid_search(
            index=index,
            matcher=matcher,
            tuning_queries=tuning_queries,
            step=args.step,
            additional_judgments=additional_judgments,
        )
        tuning_summary["results_by_matcher"][m_name] = res

        bw = res["best_weights"]
        w_str = f"({bw['summary']:.1f}, {bw['spm']:.1f}, {bw['party']:.1f})"
        mrr_str = f"{res['equal_weights_mrr_at_10']:.4f} -> {res['best_mrr_at_10']:.4f}"
        p5_str = f"{res['equal_weights_precision_at_5']:.4f} -> {res['best_precision_at_5']:.4f}"
        print(fmt.format(m_name, w_str, mrr_str, p5_str))

    print("=" * 80)

    # Simpan hasil bobot ke berkas tujuan
    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(tuning_summary, f, indent=2, ensure_ascii=False)

    print(f"\n[+] Konfigurasi bobot optimal tersimpan di: {out_file}\n")


if __name__ == "__main__":
    main()
