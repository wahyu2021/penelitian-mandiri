"""Ekspor sampel acak berstrata 100-150 baris untuk verifikasi relevansi oleh arsiparis."""
import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.testset.synthetic_generator import generate_synthetic_query

DEFAULT_POOL_CSV = Path("output/relevance_pool.csv")
DEFAULT_OUTPUT_CSV = Path("output/relevance_verification_sample.csv")
DEFAULT_CORPUS_CSV = Path("data/corpus_arsip.csv")
DEFAULT_QUERIES_JSON = Path("output/.candidate_queries.json")
DEFAULT_SAMPLE_SIZE = 120
SAMPLE_SEED = 42

VERIFICATION_FIELDNAMES = [
    "sample_id", "query_id", "base_query_text", "query_text", "query_type", "source", "noise_type",
    "archive_id", "summary_raw", "spm_number", "party_name",
    "is_relevant", "ragu", "archivist_notes",
]


def export_verification_sample(
    pool_csv_path: Path,
    output_csv_path: Path,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = SAMPLE_SEED,
    corpus_csv_path: Path = DEFAULT_CORPUS_CSV,
    candidates_path: Optional[Path] = DEFAULT_QUERIES_JSON,
) -> int:
    """Ekspor sampel berstrata acak dari pool untuk diverifikasi independen oleh arsiparis."""
    if not pool_csv_path.is_file():
        raise FileNotFoundError(f"Berkas pool tidak ditemukan: {pool_csv_path}")

    with open(pool_csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError("Berkas pool CSV kosong.")

    # Pool lama dapat hanya memuat summary_clean. Penilai tetap perlu teks asli.
    raw_by_id: Dict[str, Dict[str, str]] = {}
    need_corpus = any(not r.get("summary_raw", "").strip() for r in rows)
    if candidates_path and candidates_path.is_file():
        need_corpus = True
    if need_corpus:
        if not corpus_csv_path.is_file():
            raise FileNotFoundError(f"Teks asli arsip tidak tersedia: {corpus_csv_path}")
        with open(corpus_csv_path, "r", encoding="utf-8-sig", newline="") as f:
            raw_by_id = {r["id"]: r for r in csv.DictReader(f)}

    base_by_query: Dict[str, str] = {}
    if candidates_path and candidates_path.is_file():
        with open(candidates_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
        for candidate in candidates:
            origin = raw_by_id.get(str(candidate.get("origin_archive_id", "")))
            if origin is None:
                raise ValueError(f"Arsip asal tidak tersedia untuk {candidate['query_id']}")
            generated = generate_synthetic_query(origin, candidate["query_type"])
            if not generated or not generated.get("base_text"):
                raise ValueError(f"Kueri dasar tidak dapat dibentuk untuk {candidate['query_id']}")
            base_by_query[candidate["query_id"]] = str(generated["base_text"])

    # Kelompokkan baris berdasarkan query_type
    strata: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        q_type = r.get("query_type", "umum")
        strata[q_type].append(r)

    rng = random.Random(seed)
    sampled_rows: List[Dict[str, str]] = []
    quota_per_type = sample_size // len(strata) if strata else sample_size

    for q_type, group in sorted(strata.items()):
        picked = rng.sample(group, min(len(group), quota_per_type))
        sampled_rows.extend(picked)

    # Bila ada sisa karena pembagian kuota
    if len(sampled_rows) < sample_size:
        picked_keys = {(r["query_id"], r["archive_id"]) for r in sampled_rows}
        unpicked = [
            r for r in rows if (r["query_id"], r["archive_id"]) not in picked_keys
        ]
        needed = sample_size - len(sampled_rows)
        sampled_rows.extend(rng.sample(unpicked, min(len(unpicked), needed)))

    rng.shuffle(sampled_rows)

    output_rows: List[Dict[str, object]] = []
    for idx, r in enumerate(sampled_rows, start=1):
        raw_summary = r.get("summary_raw", "").strip()
        if not raw_summary:
            archive = raw_by_id.get(str(r["archive_id"]))
            if not archive or not archive.get("summary_raw", "").strip():
                raise ValueError(
                    f"Ringkasan asli tidak tersedia untuk arsip {r['archive_id']}"
                )
            if r.get("summary_clean") and archive.get("summary_clean") != r["summary_clean"]:
                raise ValueError(
                    f"Ringkasan arsip {r['archive_id']} tidak cocok dengan korpus"
                )
            raw_summary = archive["summary_raw"]
        output_rows.append({
            "sample_id": idx,
            "query_id": r["query_id"],
            "base_query_text": base_by_query.get(r["query_id"], r["query_text"]),
            "query_text": r["query_text"],
            "query_type": r.get("query_type", "umum"),
            "source": r.get("source", "sintetis"),
            "noise_type": r.get("noise_type", "tanpa_gangguan"),
            "archive_id": r["archive_id"],
            "summary_raw": raw_summary,
            "spm_number": r.get("spm_number", ""),
            "party_name": r.get("party_name", ""),
            "is_relevant": "",  # Dikosongkan untuk diisi murni oleh arsiparis
            "ragu": "",
            "archivist_notes": "",
        })

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VERIFICATION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(sampled_rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ekspor sampel 100-150 baris untuk verifikasi relevansi oleh arsiparis."
    )
    parser.add_argument(
        "--pool-csv",
        default=str(DEFAULT_POOL_CSV),
        help="Path berkas CSV pool utama.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Path berkas CSV sampel verifikasi arsiparis.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help="Ukuran sampel (default: 120 baris).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SAMPLE_SEED,
        help="Random seed penarikan sampel (default: 42).",
    )
    parser.add_argument(
        "--corpus-csv", default=str(DEFAULT_CORPUS_CSV),
        help="Sumber ringkasan asli jika pool hanya memuat summary_clean.",
    )
    parser.add_argument(
        "--candidates-json", default=str(DEFAULT_QUERIES_JSON),
        help="Metadata kueri untuk menampilkan kebutuhan informasi kueri dasar.",
    )
    args = parser.parse_args()

    try:
        n_picked = export_verification_sample(
            pool_csv_path=Path(args.pool_csv),
            output_csv_path=Path(args.output_csv),
            sample_size=args.sample_size,
            seed=args.seed,
            corpus_csv_path=Path(args.corpus_csv),
            candidates_path=Path(args.candidates_json),
        )
    except Exception as exc:
        print(f"[GALAT] Gagal mengekspor sampel verifikasi: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[+] Berkas sampel verifikasi arsiparis berhasil dibuat:")
    print(f"    - Berkas Tujuan : {args.output_csv}")
    print(f"    - Jumlah Sampel : {n_picked} baris (mencakup seluruh jenis kueri)")
    print(f"    - Random Seed   : {args.seed}")
    print("\n[Instruksi Arsiparis]")
    print("1. Buka berkas dengan Excel/Spreadsheet.")
    print("2. Nilai kolom 'is_relevant' dengan 1 (Relevan) atau 0 (Tidak Relevan).")
    print("3. Kolom 'ragu' diisi 1 jika informasi ambigu (kosongkan jika yakin).")
    print("4. Setelah diisi, hitung kesepakatan dengan skrip evaluate_relevance_agreement.\n")


if __name__ == "__main__":
    main()
