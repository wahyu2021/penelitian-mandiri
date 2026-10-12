"""Skrip CLI untuk memeriksa dan menangani dokumen belum dinilai di Top-10."""
import argparse
import csv
import hashlib
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker, equal_weights
from services.db import DEFAULT_DB_PATH

DEFAULT_TESTSET_PATH = Path("data/testset/testset_v1.json")
DEFAULT_TUNED_WEIGHTS_PATH = Path("data/testset/tuned_weights.json")
DEFAULT_ADDITIONAL_JUDGMENTS_PATH = Path("data/testset/additional_judgments_v1.json")
DEFAULT_UNJUDGED_CSV_PATH = Path("output/unjudged_top10_review.csv")


def load_corpus(db_path: Path) -> Tuple[List[Dict[str, object]], Dict[int, Dict[str, object]]]:
    """Muat korpus arsip dari SQLite."""
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
    corpus = [dict(r) for r in rows]
    corpus_map = {int(r["id"]): r for r in corpus}
    return corpus, corpus_map


def load_additional_judgments(path: Path) -> Dict[str, Dict[int, int]]:
    """Muat berkas penilaian tambahan jika ada."""
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, Dict[int, int]] = {}
    for q_id, judgments in data.get("judgments_by_query", {}).items():
        result[str(q_id)] = {
            int(aid): int(rel) for aid, rel in judgments.items()
        }
    return result


def find_unjudged_in_top10(
    index: SearchIndex,
    corpus_map: Dict[int, Dict[str, object]],
    queries: List[Dict[str, object]],
    tuned_weights_data: Optional[Dict[str, object]] = None,
    additional_judgments: Optional[Dict[str, Dict[int, int]]] = None,
    top_n: int = 10,
) -> List[Dict[str, object]]:
    """Cari dokumen di Top-10 hasil pencarian yang belum pernah dinilai."""
    additional_judgments = additional_judgments or {}
    results_by_matcher = (
        tuned_weights_data.get("results_by_matcher", {})
        if tuned_weights_data
        else {}
    )

    unjudged_entries: List[Dict[str, object]] = []
    seen_pairs: Set[Tuple[str, int]] = set()

    like_search = LikeBaselineSearch(index)

    for q in queries:
        q_id = str(q.get("query_id", ""))
        q_text = str(q.get("query_text", ""))

        # Kumpulkan seluruh ID dokumen yang sudah dinilai
        judged_ids = {int(j["archive_id"]) for j in q.get("judgments", [])}
        if q_id in additional_judgments:
            judged_ids.update(additional_judgments[q_id].keys())

        # 1. Periksa LIKE baseline
        like_hits = like_search.search(q_text, top_n=top_n)
        for h in like_hits:
            if h.id not in judged_ids:
                pair = (q_id, h.id)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    meta = corpus_map.get(h.id, {})
                    unjudged_entries.append({
                        "query_id": q_id,
                        "query_text": q_text,
                        "archive_id": h.id,
                        "method": "like",
                        "summary_raw": meta.get("summary_raw", ""),
                        "spm_number": meta.get("spm_number", ""),
                        "party_name": meta.get("party_name", ""),
                    })

        # 2. Periksa setiap fuzzy matcher (dengan bobot tuned jika ada, atau equal weights)
        for m_name in FUZZY_METHOD_NAMES:
            matcher = create_matcher(m_name)
            weights = equal_weights()
            if m_name in results_by_matcher:
                weights = results_by_matcher[m_name].get("best_weights", weights)

            ranker = FieldRanker(index, matcher, weights=weights)
            hits = ranker.search(q_text, top_n=top_n)
            for h in hits:
                if h.id not in judged_ids:
                    pair = (q_id, h.id)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        meta = corpus_map.get(h.id, {})
                        unjudged_entries.append({
                            "query_id": q_id,
                            "query_text": q_text,
                            "archive_id": h.id,
                            "method": m_name,
                            "summary_raw": meta.get("summary_raw", ""),
                            "spm_number": meta.get("spm_number", ""),
                            "party_name": meta.get("party_name", ""),
                        })

    return unjudged_entries


def export_unjudged_review_csv(
    entries: List[Dict[str, object]],
    output_path: Path,
    seed: int = 42,
) -> None:
    """Ekspor dokumen belum dinilai dalam urutan acak/buta untuk dinilai peneliti."""
    rng = random.Random(seed)
    shuffled = list(entries)
    rng.shuffle(shuffled)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "query_id", "query_text", "archive_id", "summary_raw",
        "spm_number", "party_name", "is_relevant", "auditor_notes",
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(shuffled, start=1):
            writer.writerow({
                "query_id": row["query_id"],
                "query_text": row["query_text"],
                "archive_id": row["archive_id"],
                "summary_raw": row["summary_raw"],
                "spm_number": row["spm_number"],
                "party_name": row["party_name"],
                "is_relevant": "",
                "auditor_notes": "",
            })


def import_additional_judgments_from_csv(
    csv_path: Path,
    output_json_path: Path,
) -> Dict[str, object]:
    """Impor penilaian tambahan dari CSV dan kunci dengan SHA-256."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Berkas CSV tidak ditemukan: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    judgments_by_query: Dict[str, Dict[str, int]] = defaultdict(dict)
    for r in rows:
        q_id = r["query_id"]
        aid = str(r["archive_id"])
        rel_raw = r.get("is_relevant", "").strip()
        is_rel = 1 if rel_raw in {"1", "true", "ya", "relevan"} else 0
        judgments_by_query[q_id][aid] = is_rel

    payload = {
        "version": "v1.0.0-additional",
        "n_additional_judgments": sum(len(v) for v in judgments_by_query.values()),
        "judgments_by_query": judgments_by_query,
    }
    repr_str = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)
    content_hash = hashlib.sha256(repr_str.encode("utf-8")).hexdigest()
    payload["content_sha256"] = content_hash

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Periksa keberadaan dokumen belum dinilai di Top-10 seluruh metode."
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
        "--tuned-weights",
        default=str(DEFAULT_TUNED_WEIGHTS_PATH),
        help="Path berkas bobot optimal opsional",
    )
    parser.add_argument(
        "--additional-judgments",
        default=str(DEFAULT_ADDITIONAL_JUDGMENTS_PATH),
        help="Path berkas penilaian tambahan opsional",
    )
    parser.add_argument(
        "--export-csv",
        default=str(DEFAULT_UNJUDGED_CSV_PATH),
        help="Path ekspor CSV jika ditemukan dokumen belum dinilai",
    )
    parser.add_argument(
        "--import-from-csv",
        help="Jika diisi, impor file CSV penilaian tambahan ke JSON additional_judgments",
    )
    args = parser.parse_args()

    if args.import_from_csv:
        in_csv = Path(args.import_from_csv)
        out_json = Path(args.additional_judgments)
        print(f"[+] Mengimpor penilaian tambahan dari: {in_csv}")
        res = import_additional_judgments_from_csv(in_csv, out_json)
        print(f"    Berhasil menyimpan {res['n_additional_judgments']} penilaian.")
        print(f"    Hash SHA-256: {res['content_sha256']}")
        return

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

    tuned_weights_data = None
    tw_path = Path(args.tuned_weights)
    if tw_path.is_file():
        with open(tw_path, "r", encoding="utf-8") as f:
            tuned_weights_data = json.load(f)

    add_judgments = load_additional_judgments(Path(args.additional_judgments))

    corpus, corpus_map = load_corpus(db_file)
    index = SearchIndex.from_records(corpus)

    queries = testset.get("queries", [])
    print(f"[+] Memeriksa dokumen di Top-10 untuk {len(queries)} kueri...")
    unjudged = find_unjudged_in_top10(
        index=index,
        corpus_map=corpus_map,
        queries=queries,
        tuned_weights_data=tuned_weights_data,
        additional_judgments=add_judgments,
        top_n=10,
    )

    if not unjudged:
        print("[+] Sempurna! Tidak ditemukan dokumen belum dinilai di Top-10.")
        print("    Semua dokumen yang masuk perangkingan Top-10 telah dinilai relevansinya.")
    else:
        print(f"[!] Ditemukan {len(unjudged)} entri dokumen belum dinilai di Top-10!")
        export_csv_path = Path(args.export_csv)
        export_unjudged_review_csv(unjudged, export_csv_path)
        print(f"    Lembar penilaian diekspor ke: {export_csv_path}")
        print("    Sesuai standar IR Cranfield, dokumen belum dinilai diasumsikan")
        print("    tidak relevan (0), atau dinilai manual dan diimpor dengan:")
        print(f"    python -m scripts.check_unjudged --import-from-csv {export_csv_path}")


if __name__ == "__main__":
    main()
