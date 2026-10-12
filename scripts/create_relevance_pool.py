"""Skrip CLI untuk menjalankan blind pooling dan mengekspor lembar penilaian relevansi."""
import argparse
import csv
import json
import random
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import create_matcher
from core.testset.pooling import build_query_pool
from core.testset.synthetic_generator import generate_synthetic_query
from services.db import DEFAULT_DB_PATH

FUZZY_METHODS = ["levenshtein", "jaro_winkler", "token_set", "ngram"]
POOLING_SEED = 42


def load_corpus(db_path: Path) -> List[Dict[str, object]]:
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


def generate_candidate_queries(
    corpus: List[Dict[str, object]], count: int = 40
) -> List[Dict[str, object]]:
    """Bangun daftar kueri kandidat sintetis beragam jenis dan gangguan."""
    rng = random.Random(POOLING_SEED)
    types = ["topik", "nomor_spm", "pihak", "campuran"]
    noises = [
        "tanpa_gangguan", "typo", "singkatan",
        "spasi_tanda_baca", "urutan_kata", "kata_hilang", "ejaan_varian",
    ]

    shuffled_corpus = list(corpus)
    rng.shuffle(shuffled_corpus)

    queries: List[Dict[str, object]] = []
    seen_texts = set()

    for rec in shuffled_corpus:
        q_type = types[len(queries) % len(types)]
        n_type = noises[len(queries) % len(noises)]
        gen = generate_synthetic_query(rec, q_type, n_type, seed=POOLING_SEED + len(queries))
        if gen and gen["query_text"] not in seen_texts:
            seen_texts.add(gen["query_text"])
            q_id = f"Q{len(queries) + 1:03d}"
            gen["query_id"] = q_id
            queries.append(gen)
            if len(queries) >= count:
                break

    return queries


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Jalankan blind pooling hasil temu kembali dan ekspor lembar penilaian relevansi."
        )
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help="Path database SQLite lokal.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Direktori ekspor file CSV penilaian.",
    )
    parser.add_argument(
        "--queries-json",
        default=None,
        help="Path berkas JSON kueri input opsional (jika ada kueri arsiparis).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=40,
        help="Target jumlah kueri jika digenerate otomatis (default: 40).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=10,
        help="Kedalaman pool per metode (default: 10).",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.is_file():
        print(f"[GALAT] Database tidak ditemukan: {db_path}", file=sys.stderr)
        sys.exit(1)

    print("[*] Memuat korpus dokumen dari SQLite...")
    corpus = load_corpus(db_path)
    corpus_by_id = {int(r["id"]): r for r in corpus}

    print("[*] Membangun search index dan matchers...")
    index = SearchIndex.from_records(corpus)
    like_search = LikeBaselineSearch(index)
    matchers = {m: create_matcher(m) for m in FUZZY_METHODS}

    queries: List[Dict[str, object]] = []
    if args.queries_json and Path(args.queries_json).is_file():
        print(f"[*] Memuat kueri dari berkas: {args.queries_json}")
        queries = json.loads(Path(args.queries_json).read_text(encoding="utf-8"))
    else:
        print(f"[*] Menghasilkan {args.count} kueri uji beragam jenis dan gangguan...")
        queries = generate_candidate_queries(corpus, count=args.count)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pool_rows = []
    total_docs = 0

    print(f"[*] Menjalankan blind pooling (kedalaman {args.depth}) untuk {len(queries)} kueri...")
    for idx, q in enumerate(queries, start=1):
        q_text = str(q["query_text"])
        orig_id = q.get("origin_archive_id")
        pooled_ids = build_query_pool(
            query_text=q_text,
            index=index,
            matchers=matchers,
            like_search=like_search,
            origin_archive_id=int(orig_id) if orig_id is not None else None,
            pool_depth=args.depth,
            seed=POOLING_SEED + idx,
        )
        total_docs += len(pooled_ids)

        for p_order, doc_id in enumerate(pooled_ids, start=1):
            doc = corpus_by_id.get(doc_id, {})
            pool_rows.append({
                "query_id": q["query_id"],
                "query_text": q_text,
                "query_type": q.get("query_type", "umum"),
                "source": q.get("source", "sintetis"),
                "noise_type": q.get("noise_type", "tanpa_gangguan"),
                "pool_order": p_order,
                "archive_id": doc_id,
                "summary_raw": doc.get("summary_raw", ""),
                "spm_number": doc.get("spm_number", ""),
                "party_name": doc.get("party_name", ""),
                "is_relevant": "",  # Diisi 1 (relevan) atau 0 (tidak relevan) oleh penilai
                "auditor_notes": "",
            })

    # Ekspor berkas pool lengkap
    csv_path = out_dir / "relevance_pool.csv"
    fieldnames = [
        "query_id", "query_text", "query_type", "source", "noise_type",
        "pool_order", "archive_id", "summary_raw", "spm_number", "party_name",
        "is_relevant", "auditor_notes",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pool_rows)

    # Ekspor berkas pilot 5 kueri pertama
    pilot_queries = {q["query_id"] for q in queries[:5]}
    pilot_rows = [r for r in pool_rows if r["query_id"] in pilot_queries]
    pilot_csv_path = out_dir / "relevance_pool_pilot_5.csv"
    with open(pilot_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pilot_rows)

    avg_pool = total_docs / len(queries) if queries else 0
    print("\n[+] Blind pooling selesai:")
    print(f"    - Total Kueri      : {len(queries)}")
    print(f"    - Total Pasangan   : {len(pool_rows)} baris penilaian")
    print(f"    - Rata-rata Pool   : {avg_pool:.1f} dokumen per kueri")
    print(f"    - Berkas Pool Penuh: {csv_path}")
    print(f"    - Berkas Pilot (5) : {pilot_csv_path}")
    print("\n[Instruksi]")
    print("1. Nilai terlebih dahulu 5 kueri pilot pada relevance_pool_pilot_5.csv.")
    print("2. Kolom 'is_relevant' diisi 1 (Relevan) atau 0 (Tidak Relevan).")
    print("3. Terapkan aturan kesetaraan: berkas dengan nomor SPM atau substansi sama = 1.\n")


if __name__ == "__main__":
    main()
