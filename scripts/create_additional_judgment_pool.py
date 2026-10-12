"""Deteksi dan ekspor dokumen top-10 yang belum dinilai (unjudged) pasca-tuning bobot."""
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.search.index import SearchIndex
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker
from services.db import DEFAULT_DB_PATH

DEFAULT_TESTSET_PATH = Path("data/testset/testset_v1.json")
DEFAULT_TUNED_WEIGHTS_PATH = Path("data/testset/tuned_weights.json")
DEFAULT_ADDITIONAL_POOL_CSV = Path("output/relevance_additional_pool.csv")
DEFAULT_MANIFEST_PATH = Path("output/relevance_additional_manifest.json")

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


def find_unjudged_top_k(
    queries: List[Dict[str, object]],
    index: SearchIndex,
    corpus_by_id: Dict[int, Dict[str, object]],
    weights_by_matcher: Dict[str, Dict[str, float]],
    top_k: int = 10,
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Temukan dokumen top-k hasil pencarian berbobot yang belum ada di penilaian awal."""
    unjudged_rows: List[Dict[str, object]] = []
    seen_pairs: Set[Tuple[str, int]] = set()
    manifest_records: Dict[str, object] = {}

    for q in queries:
        q_id = str(q["query_id"])
        q_text = str(q["query_text"])
        judged_ids = {
            int(j["archive_id"])
            for j in q.get("judgments", [])
            if j.get("is_relevant") is not None
        }

        # Jalankan pencarian dengan setiap matcher menggunakan bobot hasil tuning
        for m_name in FUZZY_METHOD_NAMES:
            w = weights_by_matcher.get(m_name, {"summary": 0.5, "spm": 0.3, "party": 0.2})
            matcher = create_matcher(m_name)
            ranker = FieldRanker(index=index, matcher=matcher, weights=w)
            hits = ranker.search(query=q_text, top_n=top_k)

            for hit in hits:
                aid = int(hit.id)
                if aid not in judged_ids:
                    pair = (q_id, aid)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)

                    doc = corpus_by_id.get(aid, {})
                    row_entry = {
                        "query_id": q_id,
                        "query_text": q_text,
                        "query_type": q.get("query_type", "umum"),
                        "source": q.get("source", "sintetis"),
                        "noise_type": q.get("noise_type", "tanpa_gangguan"),
                        "pool_order": len(unjudged_rows) + 1,
                        "archive_id": aid,
                        "summary_raw": doc.get("summary_raw", ""),
                        "spm_number": doc.get("spm_number", ""),
                        "party_name": doc.get("party_name", ""),
                        "is_relevant": "",  # Wajib diisi manual (1/0)
                        "ragu": "",
                        "auditor_notes": "",
                    }
                    unjudged_rows.append(row_entry)

                    pair_key = f"{q_id}:{aid}"
                    canonical_str = (
                        f"{q_id}|{aid}|{doc.get('summary_raw', '')}|"
                        f"{doc.get('spm_number', '')}|{doc.get('party_name', '')}"
                    )
                    manifest_records[pair_key] = {
                        "query_id": q_id,
                        "archive_id": aid,
                        "row_hash": hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16],
                    }

    manifest_data = {
        "n_unjudged": len(unjudged_rows),
        "n_affected_queries": len({r["query_id"] for r in unjudged_rows}),
        "pairs_manifest": manifest_records,
    }
    return unjudged_rows, manifest_data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deteksi dan ekspor dokumen top-10 yang belum dinilai pasca-tuning bobot."
    )
    parser.add_argument(
        "--testset",
        default=str(DEFAULT_TESTSET_PATH),
        help="Path berkas testset JSON terkunci (default: data/testset/testset_v1.json)",
    )
    parser.add_argument(
        "--weights",
        default=str(DEFAULT_TUNED_WEIGHTS_PATH),
        help="Path berkas bobot optimal hasil tuning (default: data/testset/tuned_weights.json)",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path basis data SQLite (default: instance/app.sqlite)",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_ADDITIONAL_POOL_CSV),
        help=(
            "Path ekspor CSV pool penilaian tambahan "
            "(default: output/relevance_additional_pool.csv)"
        ),
    )
    parser.add_argument(
        "--output-manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help=(
            "Path manifest hash integritas "
            "(default: output/relevance_additional_manifest.json)"
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Batas peringkat temu kembali teratas yang diperiksa (default: 10)",
    )
    args = parser.parse_args()

    testset_path = Path(args.testset)
    if not testset_path.is_file():
        print(f"[GALAT] Berkas set uji tidak ditemukan: {testset_path}", file=sys.stderr)
        print("Pastikan Anda telah menjalankan scripts/build_testset.py terlebih dahulu.")
        sys.exit(1)

    db_path = Path(args.db_path)
    if not db_path.is_file():
        print(f"[GALAT] Basis data tidak ditemukan: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Memuat set uji dari: {testset_path}")
    testset_data = json.loads(testset_path.read_text(encoding="utf-8"))
    queries = testset_data.get("queries", [])

    print(f"[*] Memuat korpus dari basis data: {db_path}")
    corpus = load_corpus(db_path)
    corpus_by_id = {int(doc["id"]): doc for doc in corpus}
    index = SearchIndex.from_records(corpus)

    # Muat bobot hasil tuning jika tersedia
    weights_path = Path(args.weights)
    weights_by_matcher: Dict[str, Dict[str, float]] = {}
    if weights_path.is_file():
        try:
            w_data = json.loads(weights_path.read_text(encoding="utf-8"))
            for m_name, res in w_data.get("results_by_matcher", {}).items():
                if "best_weights" in res:
                    weights_by_matcher[m_name] = res["best_weights"]
            print(f"[+] Bobot optimal berhasil dimuat dari: {weights_path}")
        except Exception:
            print("[!] Gagal mem-parse berkas bobot, menggunakan bobot default.")
    else:
        print("[*] Berkas tuned_weights.json tidak ditemukan, menggunakan bobot default.")

    print(f"[*] Memeriksa dokumen top-{args.top_k} untuk {len(queries)} kueri...")
    unjudged_rows, manifest = find_unjudged_top_k(
        queries=queries,
        index=index,
        corpus_by_id=corpus_by_id,
        weights_by_matcher=weights_by_matcher,
        top_k=args.top_k,
    )

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_manifest = Path(args.output_manifest)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POOL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(unjudged_rows)

    out_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    if not unjudged_rows:
        print("\n[+] Sempurna: Seluruh dokumen top-10 telah memiliki penilaian di pool awal!")
        print("    Tidak ada dokumen unjudged yang perlu dinilai.")
        print("    Anda dapat langsung melanjutkan ke evaluasi akhir (scripts/evaluate.py).\n")
    else:
        print(
            f"\n[+] Ditemukan {len(unjudged_rows)} pasangan dokumen unjudged "
            f"di top-{args.top_k}:"
        )
        print(f"    - Berkas Pool Tambahan : {out_csv}")
        print(f"    - Berkas Manifest Hash : {out_manifest}")
        print(f"    - Jumlah Kueri Terimbas: {manifest['n_affected_queries']}")
        print("\n[Petunjuk Tindak Lanjut]")
        print("1. Buka berkas relevance_additional_pool.csv di Excel/Spreadsheet.")
        print("2. Nilai kolom 'is_relevant' dengan 1 (Relevan) atau 0 (Tidak Relevan).")
        print("3. Setelah diisi, impor kembali dengan perintah:")
        print(
            "   python scripts/build_testset.py "
            "--additional-pool output/relevance_additional_pool.csv"
        )
        print("4. Commit perubahan hingga working tree bersih sebelum evaluasi akhir.\n")


if __name__ == "__main__":
    main()
