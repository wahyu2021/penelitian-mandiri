"""Bangun dan kunci berkas set uji JSON dari hasil penilaian relevansi pool."""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.testset.splitting import compute_content_sha256, split_queries_stratified_anti_leak

DEFAULT_POOL_CSV = Path("output/relevance_pool.csv")
DEFAULT_PILOT_CSV = Path("output/relevance_pool_pilot_5.csv")
DEFAULT_ADDITIONAL_POOL_CSV = Path("output/relevance_additional_pool.csv")
DEFAULT_OUTPUT_JSON = Path("data/testset/testset_v1.json")
DEFAULT_CANDIDATE_META = Path("output/.candidate_queries.json")
TESTSET_VERSION = "v1.0.0"
SPLIT_SEED = 42


def sync_and_validate_pilot(
    pool_rows: List[Dict[str, str]],
    pilot_csv_path: Optional[Path] = None,
) -> Tuple[int, int]:
    """Validasi konsistensi dan gabungkan penilaian dari pilot ke berkas utama jika belum terisi.

    Returns:
        Tuple (jumlah_baris_diperiksa, jumlah_baris_disinkronkan).
    """
    if not pilot_csv_path or not pilot_csv_path.is_file():
        return 0, 0

    with open(pilot_csv_path, "r", encoding="utf-8-sig") as f:
        pilot_rows = list(csv.DictReader(f))

    # Petakan baris utama: (query_id, archive_id) -> indeks baris di pool_rows
    main_row_map = {
        (r["query_id"], int(r["archive_id"])): r
        for r in pool_rows
    }

    checked = 0
    synced = 0
    for pr in pilot_rows:
        p_rel = pr.get("is_relevant", "").strip()
        if p_rel != "":
            p_val = 1 if p_rel in {"1", "true", "ya", "relevan"} else 0
            key = (pr["query_id"], int(pr["archive_id"]))
            if key in main_row_map:
                main_row = main_row_map[key]
                m_rel = main_row.get("is_relevant", "").strip()
                if m_rel == "":
                    # Gabungkan otomatis nilai dari pilot ke berkas utama
                    main_row["is_relevant"] = str(p_val)
                    if not main_row.get("ragu", "").strip() and pr.get("ragu", "").strip():
                        main_row["ragu"] = pr["ragu"].strip()
                    if not main_row.get("auditor_notes", "").strip():
                        main_row["auditor_notes"] = pr.get("auditor_notes", "").strip()
                    synced += 1
                else:
                    m_val = 1 if m_rel in {"1", "true", "ya", "relevan"} else 0
                    if p_val != m_val:
                        raise ValueError(
                            f"Ketidakkonsistenan penilaian terdeteksi:\n"
                            f"Kueri {key[0]}, Arsip ID {key[1]} dinilai '{p_val}' pada pilot "
                            f"tetapi '{m_val}' pada berkas utama pool.\n"
                            f"Mohon selaraskan penilaian kedua berkas."
                        )
                checked += 1

    return checked, synced


def build_testset_from_pool(
    pool_csv_path: Path,
    output_json_path: Path,
    pilot_csv_path: Optional[Path] = None,
    candidate_meta_path: Optional[Path] = None,
    additional_pool_csv_path: Optional[Path] = None,
    tuning_ratio: float = 0.30,
    seed: int = SPLIT_SEED,
) -> Dict[str, object]:
    """Bangun berkas set uji terbagi anti-leak dan terkunci dari CSV penilaian."""
    if not pool_csv_path.is_file():
        raise FileNotFoundError(f"Berkas pool tidak ditemukan: {pool_csv_path}")

    with open(pool_csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError("Berkas pool CSV kosong.")

    # Validasi dan sinkronkan penilaian dari berkas pilot (jika pilot diisi)
    _, synced_count = sync_and_validate_pilot(rows, pilot_csv_path)

    # Muat metadata kueri internal jika ada (untuk origin_archive_id dan spm)
    candidate_meta_map: Dict[str, Dict[str, object]] = {}
    if candidate_meta_path and candidate_meta_path.is_file():
        meta_list = json.loads(candidate_meta_path.read_text(encoding="utf-8"))
        candidate_meta_map = {q["query_id"]: q for q in meta_list}

    # Kelompokkan baris pool per query_id
    query_map: Dict[str, Dict[str, object]] = {}
    judgments_by_query: Dict[str, List[Dict[str, int]]] = defaultdict(list)

    unjudged_count = 0
    total_ragu = 0

    for r in rows:
        q_id = r["query_id"]
        if q_id not in query_map:
            meta = candidate_meta_map.get(q_id, {})
            orig_id = meta.get("origin_archive_id") or r.get("origin_archive_id")
            spm = meta.get("spm_number") or r.get("spm_number")

            query_map[q_id] = {
                "query_id": q_id,
                "query_text": r["query_text"],
                "query_type": r.get("query_type", "umum"),
                "source": r.get("source", "sintetis"),
                "noise_type": r.get("noise_type", "tanpa_gangguan"),
                "origin_archive_id": int(orig_id) if orig_id else None,
                "spm_number": str(spm) if spm else None,
            }

        rel_raw = r.get("is_relevant", "").strip()
        is_rel = 1 if rel_raw in {"1", "true", "ya", "relevan"} else 0
        if rel_raw == "":
            unjudged_count += 1

        ragu_raw = r.get("ragu", "").strip()
        is_ragu = 1 if ragu_raw in {"1", "ya", "true"} else 0
        if is_ragu:
            total_ragu += 1

        judgments_by_query[q_id].append({
            "archive_id": int(r["archive_id"]),
            "is_relevant": is_rel,
            "ragu": is_ragu,
        })

    # Tambahkan penilaian tambahan dokumen unjudged pasca-tuning jika ada
    additional_count = 0
    if additional_pool_csv_path and additional_pool_csv_path.is_file():
        with open(additional_pool_csv_path, "r", encoding="utf-8-sig") as f:
            add_rows = list(csv.DictReader(f))
        for ar in add_rows:
            q_id = ar.get("query_id")
            if not q_id or q_id not in query_map:
                continue
            rel_raw = ar.get("is_relevant", "").strip()
            if rel_raw == "":
                continue
            is_rel = 1 if rel_raw in {"1", "true", "ya", "relevan"} else 0
            ragu_raw = ar.get("ragu", "").strip()
            is_ragu = 1 if ragu_raw in {"1", "ya", "true"} else 0
            aid = int(ar["archive_id"])

            existing_aids = {j["archive_id"] for j in judgments_by_query[q_id]}
            if aid not in existing_aids:
                judgments_by_query[q_id].append({
                    "archive_id": aid,
                    "is_relevant": is_rel,
                    "ragu": is_ragu,
                })
                additional_count += 1
                if is_ragu:
                    total_ragu += 1

    queries_list = list(query_map.values())

    # Lakukan stratified split anti-leak
    tuning_q, test_q = split_queries_stratified_anti_leak(
        queries=queries_list,
        tuning_ratio=tuning_ratio,
        seed=seed,
    )
    tuning_ids = {q["query_id"] for q in tuning_q}

    all_queries = []
    for q in queries_list:
        q_entry = dict(q)
        q_entry["split"] = "tuning" if q["query_id"] in tuning_ids else "test"
        q_entry["judgments"] = judgments_by_query[q["query_id"]]
        q_entry["ragu_count"] = sum(j["ragu"] for j in q_entry["judgments"])
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
        "total_ragu_count": total_ragu,
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
        "total_ragu": total_ragu,
        "synced_from_pilot": synced_count,
        "additional_judged_count": additional_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impor penilaian pool CSV dan bangun berkas testset JSON terkunci."
    )
    parser.add_argument(
        "--pool-csv",
        default=str(DEFAULT_POOL_CSV),
        help="Path berkas CSV hasil penilaian pool utama.",
    )
    parser.add_argument(
        "--pilot-csv",
        default=str(DEFAULT_PILOT_CSV),
        help="Path berkas CSV penilaian pilot untuk cek konsistensi / sinkronisasi.",
    )
    parser.add_argument(
        "--additional-pool",
        default=str(DEFAULT_ADDITIONAL_POOL_CSV),
        help="Path berkas CSV penilaian tambahan pasca-tuning.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path berkas JSON set uji tujuan.",
    )
    parser.add_argument(
        "--candidate-meta",
        default=str(DEFAULT_CANDIDATE_META),
        help="Path berkas metadata kueri kandidat internal.",
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

    pilot_path = Path(args.pilot_csv) if Path(args.pilot_csv).is_file() else None
    meta_path = Path(args.candidate_meta) if Path(args.candidate_meta).is_file() else None
    add_path = (
        Path(args.additional_pool) if Path(args.additional_pool).is_file() else None
    )

    try:
        res = build_testset_from_pool(
            pool_csv_path=Path(args.pool_csv),
            output_json_path=Path(args.output_json),
            pilot_csv_path=pilot_path,
            candidate_meta_path=meta_path,
            additional_pool_csv_path=add_path,
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
    print(f"    - Baris Ragu       : {res['total_ragu']}")
    if res.get("synced_from_pilot", 0) > 0:
        print(f"    - Dari Pilot       : {res['synced_from_pilot']} baris tersinkron otomatis")
    if res.get("additional_judged_count", 0) > 0:
        print(f"    - Tambahan Pasca-Tune: {res['additional_judged_count']} baris terintegrasi")
    if res['unjudged_rows'] > 0:
        print(
            f"    - [Catatan] Terdapat {res['unjudged_rows']} baris belum dinilai "
            f"(diasumsikan tidak relevan 0)."
        )
    print()


if __name__ == "__main__":
    main()

