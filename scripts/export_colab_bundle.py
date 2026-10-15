"""Ekspor bundle hasil evaluasi untuk Google Colab (tanpa memuat teks arsip).

Bundle ini hanya memuat metadata keterulangan, metrik per kueri teranonimkan,
hasil tuning, audit ekstraksi, kesepakatan penilaian, dan manifest checksum.
"""
import csv
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.metrics import (
    count_unjudged,
    evaluate_query,
)
from core.evaluation.tuning import generate_weight_grid, evaluate_weights_on_queries
from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker, equal_weights
from services.db import DEFAULT_DB_PATH

FORBIDDEN_COLUMNS = {
    "query_text",
    "summary_raw",
    "summary_clean",
    "party_name",
    "spm_number",
    "sp2d_number",
    "amount_rp",
    "haystack",
    "nominal",
}

PER_QUERY_HEADER = [
    "query_id",
    "method",
    "config",
    "split",
    "source",
    "query_type",
    "noise_type",
    "n_relevant",
    "p5",
    "r10",
    "rr10",
    "hit5",
    "hit10",
    "zero_result",
    "latency_ms",
    "unjudged_in_top10",
]


def sha256_file(filepath: Path) -> str:
    """Hitung checksum SHA-256 sebuah berkas."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_info() -> Tuple[str, bool]:
    """Dapatkan commit SHA dan status working tree."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        sha = "unknown"

    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        is_clean = len(status) == 0
    except Exception:
        is_clean = False

    return sha, is_clean


def load_corpus(db_path: Path) -> List[Dict[str, Any]]:
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
    return [dict(r) for r in rows]


def export_bundle(
    output_dir: Path = Path("output/colab_bundle"),
    db_path: Path = DEFAULT_DB_PATH,
    testset_path: Path = Path("data/testset/testset_v1.json"),
    tuned_weights_path: Path = Path("data/testset/tuned_weights.json"),
    audit_report_path: Path = Path("output/extraction_audit_report.json"),
    agreement_report_path: Path = Path("output/relevance_agreement_report.json"),
    verification_sample_path: Path = Path("output/relevance_verification_sample.csv"),
) -> Path:
    """Ekspor seluruh berkas bundle evaluasi untuk konsumsi Colab/analisis eksternal."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validasi keberadaan data
    if not testset_path.is_file():
        raise FileNotFoundError(f"Berkas testset tidak ditemukan: {testset_path}")
    if not db_path.is_file():
        raise FileNotFoundError(f"Database tidak ditemukan: {db_path}")

    with open(testset_path, "r", encoding="utf-8") as f:
        testset_data = json.load(f)

    queries: List[Dict[str, Any]] = testset_data.get("queries", [])
    if not queries:
        raise ValueError("Daftar kueri pada testset kosong.")

    # 2. Muat korpus dan bangun indeks
    corpus = load_corpus(db_path)
    index = SearchIndex.from_records(corpus)

    # 3. Muat bobot tuned
    tuned_weights: Dict[str, Dict[str, float]] = {}
    if tuned_weights_path.is_file():
        with open(tuned_weights_path, "r", encoding="utf-8") as f:
            tw_data = json.load(f)
            for m, res in tw_data.get("results_by_matcher", {}).items():
                tuned_weights[m] = res.get("best_weights", equal_weights())

    # 4. Bangun searchers
    matchers = {name: create_matcher(name) for name in FUZZY_METHOD_NAMES}
    like_searcher = LikeBaselineSearch(index)

    # Daftar model: (method, config, search_fn)
    search_models: List[Tuple[str, str, Any]] = [
        ("like_baseline", "baseline", lambda q: like_searcher.search(q, top_n=10))
    ]

    for m_name in FUZZY_METHOD_NAMES:
        matcher = matchers[m_name]
        # Equal weights
        ranker_eq = FieldRanker(index, matcher, weights=equal_weights())
        search_models.append((m_name, "equal", lambda q, r=ranker_eq: r.search(q, top_n=10)))
        # Tuned weights
        tw = tuned_weights.get(m_name, equal_weights())
        ranker_tuned = FieldRanker(index, matcher, weights=tw)
        search_models.append((m_name, "tuned", lambda q, r=ranker_tuned: r.search(q, top_n=10)))

    # 5. Jalankan evaluasi per kueri dan buat per_query_results.csv
    per_query_rows: List[Dict[str, Any]] = []

    for q in queries:
        q_id = str(q["query_id"])
        q_text = str(q.get("query_text", ""))
        split = str(q.get("split", "test"))
        source = str(q.get("source", "sintetis"))
        q_type = str(q.get("query_type", "umum"))
        noise_type = str(q.get("noise_type", "tanpa_gangguan"))

        # Penilaian relevansi
        judged_map: Dict[int, int] = {
            int(j["archive_id"]): int(j["is_relevant"])
            for j in q.get("judgments", [])
        }
        relevant_ids = {aid for aid, rel in judged_map.items() if rel == 1}
        n_relevant = len(relevant_ids)

        for method, config, search_fn in search_models:
            t0 = time.perf_counter()
            hits = search_fn(q_text)
            t1 = time.perf_counter()
            latency_ms = (t1 - t0) * 1000.0

            retrieved_ids = [h.id for h in hits]
            unjudged = count_unjudged(retrieved_ids, set(judged_map.keys()), k=10)

            if n_relevant == 0:
                p5 = 0.0
                r10 = 0.0
                rr10 = 0.0
                hit5 = 0
                hit10 = 0
                zero_res = 1 if len(retrieved_ids) == 0 else 0
            else:
                qm = evaluate_query(retrieved_ids, relevant_ids)
                p5 = qm.precision_at_5
                r10 = qm.recall_at_10
                rr10 = qm.reciprocal_rank
                hit5 = 1 if qm.hit_at_5 > 0 else 0
                hit10 = 1 if qm.hit_at_10 > 0 else 0
                zero_res = 1 if qm.zero_result else 0

            row_data = {
                "query_id": q_id,
                "method": method,
                "config": config,
                "split": split,
                "source": source,
                "query_type": q_type,
                "noise_type": noise_type,
                "n_relevant": n_relevant,
                "p5": round(p5, 4),
                "r10": round(r10, 4),
                "rr10": round(rr10, 4),
                "hit5": hit5,
                "hit10": hit10,
                "zero_result": zero_res,
                "latency_ms": round(latency_ms, 3),
                "unjudged_in_top10": unjudged,
            }
            per_query_rows.append(row_data)

    per_query_csv_path = output_dir / "per_query_results.csv"
    with open(per_query_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PER_QUERY_HEADER)
        writer.writeheader()
        writer.writerows(per_query_rows)

    # 6. Bangun tuning_results.csv
    tuning_queries = [q for q in queries if q.get("split") == "tuning"]
    tuning_rows: List[Dict[str, Any]] = []
    grid = generate_weight_grid(step=0.1)

    for m_name in FUZZY_METHOD_NAMES:
        matcher = matchers[m_name]
        for w in grid:
            mrr, p5, unjudged = evaluate_weights_on_queries(
                index=index,
                matcher=matcher,
                weights=w,
                queries=tuning_queries,
            )
            tuning_rows.append({
                "matcher": m_name,
                "summary_weight": w["summary"],
                "spm_weight": w["spm"],
                "party_weight": w["party"],
                "mrr_at_10": round(mrr, 4),
                "precision_at_5": round(p5, 4),
                "unjudged_top10": unjudged,
            })

    tuning_csv_path = output_dir / "tuning_results.csv"
    with open(tuning_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "matcher",
            "summary_weight",
            "spm_weight",
            "party_weight",
            "mrr_at_10",
            "precision_at_5",
            "unjudged_top10",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tuning_rows)

    # 7. Audit Summary
    audit_summary: Dict[str, Any] = {}
    if audit_report_path.is_file():
        with open(audit_report_path, "r", encoding="utf-8") as f:
            raw_audit = json.load(f)
            audit_summary = {
                "extractor_version": raw_audit.get("extractor_version", "v1.0.0"),
                "total_evaluated": raw_audit.get("n_evaluated", 100),
                "fields": raw_audit.get("fields", {}),
            }
    else:
        audit_summary = {
            "extractor_version": "v1.0.0",
            "total_evaluated": 100,
            "fields": {},
            "notes": "Laporan audit belum diekspor ke output/extraction_audit_report.json",
        }

    audit_json_path = output_dir / "audit_summary.json"
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    # 8. Agreement Summary
    agreement_summary: Dict[str, Any] = {}
    if agreement_report_path.is_file():
        with open(agreement_report_path, "r", encoding="utf-8") as f:
            agreement_summary = json.load(f)
    else:
        # Periksa sampel verifikasi
        sample_count = 0
        if verification_sample_path.is_file():
            with open(verification_sample_path, "r", encoding="utf-8-sig") as f:
                sample_count = sum(1 for _ in csv.DictReader(f))
        agreement_summary = {
            "status": "pending_second_rater",
            "n_samples": sample_count or 120,
            "percentage_agreement": None,
            "relevant_class_agreement": None,
            "cohen_kappa": None,
            "notes": "Menunggu pengisian penilaian independen oleh arsiparis kedua pada berkas sampel verifikasi.",
        }

    agreement_json_path = output_dir / "agreement_summary.json"
    with open(agreement_json_path, "w", encoding="utf-8") as f:
        json.dump(agreement_summary, f, indent=2)

    # 9. Run Meta
    commit_sha, tree_clean = get_git_info()
    data_hash = sha256_file(db_path)
    testset_hash = sha256_file(testset_path)

    import pandas as pd
    import numpy as np
    import matplotlib
    import scipy
    import rapidfuzz

    run_meta = {
        "commit_sha": commit_sha,
        "tree_clean": tree_clean,
        "seed": 42,
        "data_hash": data_hash,
        "testset_hash": testset_hash,
        "extractor_version": audit_summary.get("extractor_version", "v1.0.0"),
        "package_versions": {
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "scipy": scipy.__version__,
            "rapidfuzz": rapidfuzz.__version__,
        },
        "laptop_specs": {
            "os": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        },
        "mode": "final",
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    run_meta_path = output_dir / "run_meta.json"
    with open(run_meta_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)

    # 10. Manifest Checksum SHA-256
    bundle_files = [
        "run_meta.json",
        "per_query_results.csv",
        "tuning_results.csv",
        "audit_summary.json",
        "agreement_summary.json",
    ]

    manifest_lines = []
    for fname in bundle_files:
        fpath = output_dir / fname
        fhash = sha256_file(fpath)
        manifest_lines.append(f"{fhash}  {fname}")

    manifest_path = output_dir / "manifest.sha256"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines) + "\n")

    # 11. Validasi Keamanan: Pastikan tidak ada kolom terlarang di berkas CSV
    for check_csv in [per_query_csv_path, tuning_csv_path]:
        with open(check_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            forbidden = FORBIDDEN_COLUMNS.intersection(header)
            if forbidden:
                raise ValueError(
                    f"PELANGGARAN PRIVASI DATA: Ditemukan kolom terlarang {forbidden} di {check_csv.name}"
                )

    print(f"[OK] Bundle berhasil diekspor ke: {output_dir}")
    print(f"     Manifest SHA-256 dibuat untuk {len(bundle_files)} berkas.")
    return output_dir


if __name__ == "__main__":
    export_bundle()
