"""CLI Evaluasi Temu Kembali Akhir pada Kelompok Test dengan Jaminan Keterulangan Ilmiah."""
import argparse
import json
import platform
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.evaluator import run_comparative_evaluation
from core.search.index import SearchIndex
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from services.db import DEFAULT_DB_PATH

DEFAULT_TESTSET_PATH = Path("data/testset/testset_v1.json")
DEFAULT_TUNED_WEIGHTS_PATH = Path("data/testset/tuned_weights.json")
DEFAULT_ADDITIONAL_JUDGMENTS_PATH = Path("data/testset/additional_judgments_v1.json")
DEFAULT_REPORT_PATH = Path("output/final_evaluation_report.md")
DEFAULT_OUTPUT_JSON_PATH = Path("output/final_evaluation_results.json")


def get_git_info() -> Tuple[str, str, bool]:
    """Dapatkan (commit_sha, branch_name, is_clean) dari repositori Git."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        sha = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        branch = "unknown"

    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip()
        is_clean = len(status) == 0
    except Exception:
        is_clean = False

    return sha, branch, is_clean


def load_corpus(db_path: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Muat korpus arsip dan hash dump dari SQLite."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Cek hash dump dari import_batch
    dump_hash = None
    try:
        row = conn.execute(
            "SELECT file_hash_sha256 FROM import_batch ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row:
            dump_hash = row["file_hash_sha256"]
    except Exception:
        pass

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
    return [dict(r) for r in rows], dump_hash


def load_additional_judgments(path: Path) -> Dict[str, Dict[int, int]]:
    """Muat berkas penilaian tambahan jika tersedia."""
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


def build_markdown_report(
    eval_results: Dict[str, Any],
    manifest: Dict[str, Any],
    tuned_weights_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Susun laporan ilmiah evaluasi akhir lengkap dalam format Markdown."""
    lines: List[str] = []

    lines.append("# Laporan Evaluasi Ilmiah Temu Kembali Arsip")
    lines.append("")
    lines.append(
        "Penelitian: **Sistem Pencarian Arsip Menggunakan Fuzzy Matching dan "
        "Normalisasi Metadata Berbasis Website pada Dinas Perpustakaan dan "
        "Kearsipan Kota Palembang**"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Parameter Keterulangan
    lines.append("## 1. Parameter Keterulangan Ilmiah (Reproducibility Manifest)")
    lines.append("")
    lines.append(f"- **Waktu Evaluasi (UTC)**: `{manifest['timestamp']}`")
    lines.append(f"- **Git Commit SHA**: `{manifest['git_commit_sha']}`")
    lines.append(f"- **Git Branch**: `{manifest['git_branch']}`")
    tree_status = "Clean (Bersih)" if manifest["is_clean"] else "Dirty (Diizinkan manual)"
    lines.append(f"- **Status Working Tree**: `{tree_status}`")
    lines.append(f"- **Hash SHA-256 Dump SQL**: `{manifest['dump_sha256']}`")
    lines.append(f"- **Hash SHA-256 Set Uji**: `{manifest['testset_sha256']}`")
    lines.append(f"- **Versi Set Uji**: `{manifest['testset_version']}`")
    lines.append(f"- **Random Seed Split**: `{manifest['seed']}`")
    env_str = f"Python {manifest['python_version']} ({manifest['platform']})"
    lines.append(f"- **Lingkungan Eksekusi**: `{env_str}`")
    lines.append(f"- **Jumlah Kueri Uji (Test Split)**: `{manifest['n_test_queries']}`")
    ragu_cnt = manifest.get("total_ragu", 0)
    lines.append(f"- **Jumlah Baris Ragu**: `{ragu_cnt}`")
    lines.append("")

    # 2. Tabel Metrik Keseluruhan
    lines.append("## 2. Metrik Temu Kembali Keseluruhan (Overall Test Split)")
    lines.append("")
    lines.append(
        "Perbandingan kinerja antara **LIKE Baseline** (pencarian bawaan e-Arsip SIMANIS), "
        "empat metode **Fuzzy Matching dengan Bobot Sama Rata** (*Equal Weights*), "
        "dan empat metode **Fuzzy Matching dengan Bobot Hasil Penyetelan** (*Tuned Weights*)."
    )
    lines.append("")

    header = (
        "| Metode / Konfigurasi | P@5 | R@10 | MRR@10 | Hit@5 | Hit@10 | Nol Hasil | "
        "Belum Dinilai | Rata2 Latensi (ms) | P95 Latensi (ms) |\n"
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    )
    lines.append(header)

    def row_fmt(name: str, res: Dict[str, Any]) -> str:
        ov = res["overall"]
        return (
            f"| **{name}** | {ov['precision_at_5']:.4f} | {ov['recall_at_10']:.4f} | "
            f"{ov['mrr_at_10']:.4f} | {ov['hit_rate_at_5']:.4f} | {ov['hit_rate_at_10']:.4f} | "
            f"{ov['zero_result_queries']} | {ov['unjudged_in_top10']} | "
            f"{ov['mean_latency_ms']:.2f} | {ov['p95_latency_ms']:.2f} |"
        )

    # LIKE
    if "like_baseline" in eval_results:
        lines.append(row_fmt("LIKE Baseline (e-Arsip)", eval_results["like_baseline"]))

    # Fuzzy Equal
    for m in FUZZY_METHOD_NAMES:
        k = f"{m}_equal"
        if k in eval_results:
            lines.append(row_fmt(f"{m.replace('_', '-').title()} (Equal)", eval_results[k]))

    # Fuzzy Tuned
    for m in FUZZY_METHOD_NAMES:
        k = f"{m}_tuned"
        if k in eval_results:
            lines.append(row_fmt(f"{m.replace('_', '-').title()} (Tuned)", eval_results[k]))

    lines.append("")

    # 3. Analisis Peningkatan Bobot Tuned vs Equal
    lines.append("## 3. Evaluasi Dampak Penyetelan Bobot Field (Equal vs Tuned)")
    lines.append(
        "| Metode Fuzzy | Bobot Optimal (Ringkasan, SPM, Pihak) | "
        "Selisih MRR@10 | Selisih P@5 | Selisih R@10 |"
    )
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    for m in FUZZY_METHOD_NAMES:
        eq_res = eval_results.get(f"{m}_equal", {}).get("overall", {})
        tu_res = eval_results.get(f"{m}_tuned", {}).get("overall", {})
        w_desc = "-"
        if tuned_weights_info and m in tuned_weights_info:
            bw = tuned_weights_info[m].get("best_weights", {})
            s_val, m_val, p_val = bw.get("summary", 0), bw.get("spm", 0), bw.get("party", 0)
            w_desc = f"({s_val:.1f}, {m_val:.1f}, {p_val:.1f})"

        diff_mrr = tu_res.get("mrr_at_10", 0) - eq_res.get("mrr_at_10", 0)
        diff_p5 = tu_res.get("precision_at_5", 0) - eq_res.get("precision_at_5", 0)
        diff_r10 = tu_res.get("recall_at_10", 0) - eq_res.get("recall_at_10", 0)

        lines.append(
            f"| **{m.replace('_', '-').title()}** | `{w_desc}` | "
            f"{diff_mrr:+.4f} | {diff_p5:+.4f} | {diff_r10:+.4f} |"
        )

    lines.append("")

    # 4. Analisis Berdasarkan Sumber Kueri (Nyata vs Sintetis)
    lines.append("## 4. Performa Berdasarkan Sumber Kueri (Kasus Nyata vs Sintetis)")
    lines.append("")
    lines.append("| Metode | Sumber Kueri | Jumlah Kueri | P@5 | R@10 | MRR@10 | Hit@5 |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |")

    for key in ["like_baseline", "token_set_tuned", "ngram_tuned"]:
        if key not in eval_results:
            continue
        bs = eval_results[key]["by_source"]
        for src, metrics in sorted(bs.items()):
            label = key.replace("_", " ").title()
            lines.append(
                f"| {label} | `{src}` | {metrics['n_queries']} | "
                f"{metrics['precision_at_5']:.4f} | {metrics['recall_at_10']:.4f} | "
                f"{metrics['mrr_at_10']:.4f} | {metrics['hit_rate_at_5']:.4f} |"
            )

    lines.append("")

    # 5. Analisis Ketahanan Terhadap Gangguan (Noise Robustness)
    lines.append("## 5. Ketahanan Terhadap Gangguan Pengetikan (*Noise Robustness*)")
    lines.append("")
    lines.append(
        "Pengujian ketahanan terhadap 6 ragam kesalahan pengetikan manusia nyata "
        "(*typo*, singkatan, tanda baca/spasi, urutan kata terbalik, kata hilang, ejaan varian):"
    )
    lines.append("")
    lines.append(
        "| Jenis Gangguan | LIKE Baseline MRR@10 | Token-Set (Tuned) MRR@10 | "
        "N-gram (Tuned) MRR@10 | Selisih Keunggulan |"
    )
    lines.append("| :--- | :---: | :---: | :---: | :---: |")

    like_bn = eval_results.get("like_baseline", {}).get("by_noise", {})
    ts_bn = eval_results.get("token_set_tuned", {}).get("by_noise", {})
    ng_bn = eval_results.get("ngram_tuned", {}).get("by_noise", {})

    all_noises = sorted(set(list(like_bn.keys()) + list(ts_bn.keys()) + list(ng_bn.keys())))
    for n in all_noises:
        l_mrr = like_bn.get(n, {}).get("mrr_at_10", 0.0)
        t_mrr = ts_bn.get(n, {}).get("mrr_at_10", 0.0)
        n_mrr = ng_bn.get(n, {}).get("mrr_at_10", 0.0)
        best_fuzz = max(t_mrr, n_mrr)
        diff = best_fuzz - l_mrr
        lines.append(
            f"| `{n}` | {l_mrr:.4f} | {t_mrr:.4f} | {n_mrr:.4f} | **{diff:+.4f}** |"
        )

    lines.append("")
    lines.append("---")
    lines.append(
        "*Laporan ini dihasilkan secara otomatis oleh sistem evaluasi "
        "keterulangan berbasis CLI.*"
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jalankan evaluasi temu kembali akhir pada kelompok test."
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
        help="Path berkas bobot optimal hasil penyetelan",
    )
    parser.add_argument(
        "--additional-judgments",
        default=str(DEFAULT_ADDITIONAL_JUDGMENTS_PATH),
        help="Path berkas penilaian tambahan opsional",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Path penyimpanan laporan Markdown evaluasi akhir",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON_PATH),
        help="Path penyimpanan hasil evaluasi mentah JSON",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Izinkan evaluasi dijalankan meskipun working tree Git tidak bersih (untuk testing)",
    )
    parser.add_argument(
        "--split",
        choices=["test", "tuning", "all"],
        default="test",
        help="Himpunan kueri yang dievaluasi (default: test)",
    )
    args = parser.parse_args()

    # 1. Validasi integritas working tree Git
    commit_sha, branch_name, is_clean = get_git_info()
    if not is_clean and not args.allow_dirty:
        print(
            "\n[GALAT KRITIKAL] Evaluasi akhir ditolak:\n"
            "Working tree Git tidak bersih (terdapat uncommitted changes).\n"
            "Komit atau simpan perubahan terlebih dahulu untuk memastikan "
            "integritas dan keterulangan (reproducibility) hasil penelitian.\n"
            "(Gunakan flag --allow-dirty hanya jika sedang dalam pengujian otomatis sementara).\n",
            file=sys.stderr,
        )
        sys.exit(1)

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

    # Filter kueri menurut argumen --split
    if args.split == "all":
        target_queries = testset.get("queries", [])
    else:
        target_queries = [
            q for q in testset.get("queries", []) if q.get("split") == args.split
        ]

    if not target_queries:
        print(f"[GALAT] Tidak ada kueri untuk split '{args.split}'.", file=sys.stderr)
        sys.exit(1)

    # Muat korpus dan SearchIndex
    corpus, dump_hash = load_corpus(db_file)
    index = SearchIndex.from_records(corpus)

    # Muat pencocok
    matchers = {m_name: create_matcher(m_name) for m_name in FUZZY_METHOD_NAMES}

    # Muat bobot tuned jika ada
    tw_file = Path(args.tuned_weights)
    tuned_weights_by_matcher: Dict[str, Dict[str, float]] = {}
    tw_data_full: Optional[Dict[str, Any]] = None
    if tw_file.is_file():
        with open(tw_file, "r", encoding="utf-8") as f:
            tw_data_full = json.load(f)
            rbm = tw_data_full.get("results_by_matcher", {})
            for m_name, res in rbm.items():
                tuned_weights_by_matcher[m_name] = res.get("best_weights", {})

    add_judgments = load_additional_judgments(Path(args.additional_judgments))

    print("\n" + "=" * 80)
    print("MENJALANKAN EVALUASI ILMIAH TEMU KEMBALI AKHIR")
    print("=" * 80)
    print(f"Commit SHA      : {commit_sha}")
    print(f"Working Tree    : {'Clean' if is_clean else 'Dirty (Diizinkan)'}")
    print(f"Kelompok Uji    : {args.split} ({len(target_queries)} kueri)")
    print(f"Total Arsip     : {len(corpus)}")
    print("=" * 80 + "\n")

    eval_results = run_comparative_evaluation(
        index=index,
        queries=target_queries,
        matchers=matchers,
        tuned_weights_by_matcher=tuned_weights_by_matcher,
        additional_judgments=add_judgments,
        top_n=10,
    )

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit_sha": commit_sha,
        "git_branch": branch_name,
        "is_clean": is_clean,
        "dump_sha256": dump_hash or "not_recorded",
        "testset_sha256": testset.get("content_sha256", "unknown"),
        "testset_version": testset.get("version", "v1.0.0"),
        "seed": testset.get("seed", 42),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "n_test_queries": len(target_queries),
        "total_ragu": testset.get("total_ragu_count", 0),
    }

    report_md = build_markdown_report(
        eval_results=eval_results,
        manifest=manifest,
        tuned_weights_info=(
            tw_data_full.get("results_by_matcher") if tw_data_full else None
        ),
    )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(
            {"manifest": manifest, "results": eval_results},
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"[+] Evaluasi selesai!")
    print(f"    - Laporan Markdown tersimpan di : {report_path}")
    print(f"    - Berkas Mentah JSON tersimpan di: {out_json}\n")


if __name__ == "__main__":
    main()
