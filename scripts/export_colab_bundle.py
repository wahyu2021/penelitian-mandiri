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
import click
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
from core.evaluation.tuning import evaluate_weights_on_queries, tune_weights_grid_search
from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker, equal_weights
from services.db import DEFAULT_DB_PATH
from scripts.evaluate_extraction_audit import evaluate_audit_data, read_audit_file
from scripts.evaluate_relevance_agreement import evaluate_relevance_agreement

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


def build_audit_summary(
    audit_csv_path: Path,
    audit_report_path: Path,
    audit_manifest_path: Path,
) -> Dict[str, Any]:
    """Hitung audit dari CSV penilaian terkini, bukan dari salinan laporan lama."""
    if not audit_csv_path.is_file():
        raise FileNotFoundError(f"CSV penilaian audit tidak ditemukan: {audit_csv_path}")
    current_audit = evaluate_audit_data(
        audit_rows=read_audit_file(audit_csv_path),
        manifest_path=audit_manifest_path if audit_manifest_path.is_file() else None,
    )
    if audit_report_path.is_file():
        with open(audit_report_path, "r", encoding="utf-8") as f:
            saved_audit = json.load(f)
        if json.dumps(saved_audit.get("fields"), sort_keys=True) != json.dumps(
            current_audit["fields"], sort_keys=True
        ):
            click.echo("[PERINGATAN] Laporan audit JSON berbeda dari CSV terkini; bundle memakai hitungan CSV terbaru.")
    return {
        "extractor_version": current_audit["extractor_version"],
        "total_evaluated": current_audit["n_evaluated"],
        "fields": current_audit["fields"],
        "audit_csv_sha256": sha256_file(audit_csv_path),
    }


def build_agreement_summary(
    main_csv_path: Path,
    verification_sample_path: Path,
    saved_report_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Pakai CSV penilaian terkini; laporan JSON lama hanya untuk cek selisih."""
    if not verification_sample_path.is_file():
        return {
            "status": "pending_second_rater", "n_samples": 0, "n_completed": 0,
            "percentage_agreement": None, "relevant_class_agreement": None,
            "cohen_kappa": None, "notes": "Sampel verifikasi belum tersedia.",
        }
    with open(verification_sample_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    n_completed = sum((row.get("is_relevant") or "").strip() in {"0", "1"} for row in rows)
    if any((row.get("is_relevant") or "").strip() not in {"", "0", "1"} for row in rows):
        raise ValueError("Sampel verifikasi memuat nilai relevansi selain 0/1")
    if not rows or n_completed < len(rows):
        return {
            "status": "pending_second_rater", "n_samples": len(rows),
            "n_completed": n_completed, "percentage_agreement": None,
            "relevant_class_agreement": None, "cohen_kappa": None,
            "notes": "Menunggu seluruh penilaian independen pada sampel verifikasi.",
        }
    current = evaluate_relevance_agreement(main_csv_path, verification_sample_path)
    current["n_completed"] = n_completed
    if saved_report_path and saved_report_path.is_file():
        with open(saved_report_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if any(saved.get(key) != current.get(key) for key in (
            "percentage_agreement", "relevant_class_agreement", "cohen_kappa"
        )):
            click.echo("[PERINGATAN] Laporan kesepakatan JSON berbeda dari CSV terkini; bundle memakai hitungan CSV terbaru.")
    return current


def export_bundle(
    output_dir: Path = Path("output/colab_bundle"),
    db_path: Path = DEFAULT_DB_PATH,
    testset_path: Path = Path("data/testset/testset_v1.json"),
    tuned_weights_path: Path = Path("data/testset/tuned_weights.json"),
    audit_report_path: Path = Path("output/extraction_audit_report.json"),
    audit_csv_path: Path = Path("output/audit_extraction_sample.csv"),
    audit_manifest_path: Path = Path("output/audit_strata_summary.json"),
    agreement_report_path: Path = Path("output/relevance_agreement_report.json"),
    verification_sample_path: Path = Path("output/relevance_verification_sample.csv"),
    main_judgment_path: Path = Path("output/relevance_pool.csv"),
    reuse_tuning_csv: bool = False,
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
    click.echo("\n[1/5] Memuat korpus dan membangun indeks pencarian...")
    t_start = time.perf_counter()
    corpus = load_corpus(db_path)
    index = SearchIndex.from_records(corpus)
    t_idx = time.perf_counter() - t_start
    click.echo(f"      -> {len(index.documents):,} dokumen berhasil diindeks ({t_idx:.2f} detik).")

    # 3. Muat bobot tuned
    tuned_weights: Dict[str, Dict[str, float]] = {}
    cached_grid_by_matcher: Dict[str, List[Dict[str, Any]]] = {}
    if tuned_weights_path.is_file():
        with open(tuned_weights_path, "r", encoding="utf-8") as f:
            tw_data = json.load(f)
            if tw_data.get("testset_hash") != testset_data.get("content_sha256"):
                raise ValueError(
                    "Bobot tuning berasal dari set uji berbeda. Jalankan scripts/tune_weights.py kembali."
                )
            for m, res in tw_data.get("results_by_matcher", {}).items():
                tuned_weights[m] = res.get("best_weights", equal_weights())
                if "grid_results" in res:
                    cached_grid_by_matcher[m] = res["grid_results"]

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

    click.echo(f"[2/5] Mengevaluasi {len(queries)} kueri uji pada {len(search_models)} model pencarian:")
    with click.progressbar(queries, label="      Progress Evaluasi Kueri") as bar:
        for q in bar:
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
    tuning_csv_path = output_dir / "tuning_results.csv"
    if reuse_tuning_csv and tuning_csv_path.is_file():
        click.echo("[3/5] Menggunakan berkas tuning_results.csv yang sudah ada (reuse_tuning_csv=True).")
    elif all(m in cached_grid_by_matcher for m in FUZZY_METHOD_NAMES):
        click.echo("[3/5] Menyalin hasil grid search dari data/testset/tuned_weights.json ke tuning_results.csv...")
        tuning_rows: List[Dict[str, Any]] = []
        for m_name in FUZZY_METHOD_NAMES:
            for g_rec in cached_grid_by_matcher[m_name]:
                w = g_rec["weights"]
                tuning_rows.append({
                    "matcher": m_name,
                    "summary_weight": w["summary"],
                    "spm_weight": w["spm"],
                    "party_weight": w["party"],
                    "mrr_at_10": g_rec["mrr_at_10"],
                    "precision_at_5": g_rec["precision_at_5"],
                    "unjudged_top10": g_rec["unjudged_top10"],
                })
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
    else:
        tuning_queries = [q for q in queries if q.get("split") == "tuning"]
        tuning_rows: List[Dict[str, Any]] = []

        click.echo("[3/5] Menjalankan grid search penyetelan bobot cepat (pra-komputasi per field):")
        for m_name in FUZZY_METHOD_NAMES:
            matcher = matchers[m_name]
            res = tune_weights_grid_search(
                index=index,
                matcher=matcher,
                tuning_queries=tuning_queries,
                step=0.1,
            )
            for g_rec in res["grid_results"]:
                w = g_rec["weights"]
                tuning_rows.append({
                    "matcher": m_name,
                    "summary_weight": w["summary"],
                    "spm_weight": w["spm"],
                    "party_weight": w["party"],
                    "mrr_at_10": g_rec["mrr_at_10"],
                    "precision_at_5": g_rec["precision_at_5"],
                    "unjudged_top10": g_rec["unjudged_top10"],
                })

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

    click.echo("[4/5] Mengumpulkan audit ekstraksi dan ringkasan kesepakatan reliabilitas...")

    # 7. Audit Summary
    audit_summary = build_audit_summary(
        audit_csv_path, audit_report_path, audit_manifest_path
    )

    audit_json_path = output_dir / "audit_summary.json"
    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    # 8. Agreement Summary
    agreement_summary = build_agreement_summary(
        main_judgment_path, verification_sample_path, agreement_report_path
    )

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

    query_to_base_id = {
        str(q["query_id"]): str(q.get("base_query_id") or q["query_id"])
        for q in queries
    }
    n_base_queries = testset_data.get("n_base_queries") or len(set(query_to_base_id.values()))
    n_tuning_base = testset_data.get("n_tuning_base_queries") or len(
        {query_to_base_id[str(q["query_id"])] for q in queries if q.get("split") == "tuning"}
    )
    n_test_base = testset_data.get("n_test_base_queries") or len(
        {query_to_base_id[str(q["query_id"])] for q in queries if q.get("split") == "test"}
    )

    realism_csv_path = Path("output/query_realism_validation_sample.csv")
    realism_summary: Dict[str, Any] = {}
    if realism_csv_path.is_file():
        with open(realism_csv_path, "r", encoding="utf-8-sig") as f:
            r_rows = list(csv.DictReader(f))
        if r_rows:
            r1_ok = sum(1 for r in r_rows if str(r.get("rater_1_realistic", "")).strip() == "1")
            r2_ok = sum(1 for r in r_rows if str(r.get("rater_2_realistic", "")).strip() == "1")
            both_ok = sum(
                1
                for r in r_rows
                if str(r.get("rater_1_realistic", "")).strip() == "1"
                and str(r.get("rater_2_realistic", "")).strip() == "1"
            )
            realism_summary = {
                "n_samples": len(r_rows),
                "sample_ratio_pct": round(len(r_rows) / len(queries) * 100.0, 1),
                "rater_1_realistic_pct": round(r1_ok / len(r_rows) * 100.0, 1),
                "rater_2_realistic_pct": round(r2_ok / len(r_rows) * 100.0, 1),
                "both_raters_realistic_pct": round(both_ok / len(r_rows) * 100.0, 1),
            }

    test_queries_only = [q for q in queries if q.get("split") == "test"]
    summary_only_test_metrics: Dict[str, Dict[str, float]] = {}
    w_sum_only = {"summary": 1.0, "spm": 0.0, "party": 0.0}
    for m_name in FUZZY_METHOD_NAMES:
        mrr_s, p5_s, _ = evaluate_weights_on_queries(
            index=index,
            matcher=matchers[m_name],
            weights=w_sum_only,
            queries=test_queries_only,
        )
        summary_only_test_metrics[m_name] = {
            "mrr_at_10": round(mrr_s, 4),
            "precision_at_5": round(p5_s, 4),
        }

    run_meta = {
        "commit_sha": commit_sha,
        "tree_clean": tree_clean,
        "seed": 42,
        "data_hash": data_hash,
        "testset_hash": testset_hash,
        "n_queries": len(queries),
        "n_tuning_queries": testset_data.get("n_tuning", 32),
        "n_test_queries": testset_data.get("n_test", 80),
        "n_base_queries": n_base_queries,
        "n_tuning_base_queries": n_tuning_base,
        "n_test_base_queries": n_test_base,
        "query_to_base_id": query_to_base_id,
        "realism_validation": realism_summary,
        "summary_only_test_metrics": summary_only_test_metrics,
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
        "mode": "final" if tree_clean else "draft",
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
