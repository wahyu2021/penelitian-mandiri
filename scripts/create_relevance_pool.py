"""Skrip CLI untuk menjalankan blind pooling dan mengekspor lembar penilaian relevansi."""
import argparse
import csv
import json
import random
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import create_matcher
from core.testset.pooling import build_query_pool
from core.testset.synthetic_generator import generate_synthetic_query
from services.db import DEFAULT_DB_PATH

FUZZY_METHODS = ["levenshtein", "jaro_winkler", "token_set", "ngram"]
POOLING_SEED = 42

POOL_FIELDNAMES = [
    "query_id", "query_text", "query_type", "source", "noise_type",
    "pool_order", "archive_id", "summary_raw", "spm_number", "party_name",
    "is_relevant", "ragu", "auditor_notes",
]


def load_corpus(db_path: Path) -> List[Dict[str, object]]:
    """Muat seluruh data arsip dari basis data SQLite."""
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
        if len(queries) >= count:
            break
        q_type = types[len(queries) % len(types)]
        noise = noises[len(queries) % len(noises)]

        q_dict = generate_synthetic_query(
            archive_record=rec,
            query_type=q_type,
            noise_type=noise,
            seed=POOLING_SEED + len(queries),
        )
        if q_dict and q_dict["query_text"] not in seen_texts:
            seen_texts.add(q_dict["query_text"])
            q_id = f"Q{len(queries) + 1:03d}"
            q_dict["query_id"] = q_id
            queries.append(q_dict)

    return queries


def load_archivist_queries(file_path: Path, start_idx: int = 41) -> List[Dict[str, object]]:
    """Muat kueri kasus nyata dari arsiparis (format JSON atau CSV)."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Berkas kueri arsiparis tidak ditemukan: {file_path}")

    queries: List[Dict[str, object]] = []
    if file_path.suffix.lower() == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for idx, item in enumerate(data, start=start_idx):
            q_text = str(item.get("query_text", "")).strip()
            if q_text:
                queries.append({
                    "query_id": item.get("query_id") or f"QA{idx:03d}",
                    "query_text": q_text,
                    "query_type": item.get("query_type", "topik"),
                    "source": "arsiparis",
                    "noise_type": "tanpa_gangguan",
                    "origin_archive_id": item.get("origin_archive_id"),
                })
    else:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=start_idx):
                q_text = str(row.get("query_text", "")).strip()
                if q_text:
                    queries.append({
                        "query_id": row.get("query_id") or f"QA{idx:03d}",
                        "query_text": q_text,
                        "query_type": row.get("query_type", "topik"),
                        "source": "arsiparis",
                        "noise_type": "tanpa_gangguan",
                        "origin_archive_id": (
                            int(row["origin_archive_id"])
                            if row.get("origin_archive_id") else None
                        ),
                    })
    return queries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jalankan blind pooling dari 5 metode pencarian dan ekspor ke CSV."
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
        help="Path berkas JSON kueri input opsional.",
    )
    parser.add_argument(
        "--batch-archivist",
        default=None,
        help="Path berkas kueri kasus nyata dari arsiparis (Batch 2).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=40,
        help="Target jumlah kueri sintetis (default: 40).",
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

    # Tambahkan batch kueri nyata arsiparis jika ada
    if args.batch_archivist:
        arch_queries = load_archivist_queries(
            Path(args.batch_archivist), start_idx=len(queries) + 1
        )
        print(f"[*] Menambahkan {len(arch_queries)} kueri kasus nyata dari arsiparis...")
        queries.extend(arch_queries)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Simpan manifest query internal (untuk referensi anti-leak split)
    (out_dir / ".candidate_queries.json").write_text(
        json.dumps(queries, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    pool_rows = []
    total_docs = 0
    seen_pairs: Set[Tuple[str, int]] = set()

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

        p_order = 1
        for doc_id in pooled_ids:
            pair = (q["query_id"], doc_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
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
                "is_relevant": "",  # Wajib diisi manual (1/0)
                "ragu": "",         # Opsional (1 jika ragu)
                "auditor_notes": "",
            })
            p_order += 1

    # Ekspor berkas pool lengkap
    csv_path = out_dir / "relevance_pool.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POOL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(pool_rows)

    # Ekspor berkas pilot 5 kueri pertama
    pilot_queries = {q["query_id"] for q in queries[:5]}
    pilot_rows = [r for r in pool_rows if r["query_id"] in pilot_queries]
    pilot_csv_path = out_dir / "relevance_pool_pilot_5.csv"
    with open(pilot_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POOL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(pilot_rows)

    avg_pool = total_docs / len(queries) if queries else 0
    print("\n[+] Blind pooling selesai:")
    print(f"    - Total Kueri      : {len(queries)}")
    print(f"    - Total Pasangan   : {len(pool_rows)} baris penilaian")
    print(f"    - Rata-rata Pool   : {avg_pool:.1f} dokumen per kueri")
    print(f"    - Berkas Pool Penuh: {csv_path}")
    print(f"    - Berkas Pilot (5) : {pilot_csv_path}")
    print("\n[Petunjuk]")
    print("1. Nilai terlebih dahulu 5 kueri pilot pada relevance_pool_pilot_5.csv.")
    print("2. Kolom 'is_relevant' diisi 1 (Relevan) atau 0 (Tidak Relevan).")
    print("3. Kolom 'ragu' diisi 1 jika ambigu (kosongkan jika yakin).")
    print("4. Aturan kesetaraan: berkas dengan nomor SPM atau pekerjaan sama = 1.\n")


if __name__ == "__main__":
    main()
