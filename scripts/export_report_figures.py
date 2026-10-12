"""Ekspor grafik resolusi tinggi (300 DPI PNG) dan tabel skripsi dari berkas output evaluasi."""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt

DEFAULT_EVAL_JSON = Path("output/final_evaluation_results.json")
DEFAULT_AUDIT_JSON = Path("output/extraction_audit_report.json")
DEFAULT_FIGURES_DIR = Path("output/figures")


def export_audit_figure(audit_data: Dict[str, Any], output_path: Path) -> None:
    """Ekspor grafik batang akurasi ekstraksi metadata dengan Wilson 95% CI (300 DPI)."""
    fields = ["spm", "sp2d", "date", "amount", "party"]
    labels = ["No SPM", "No SP2D", "Tanggal", "Rupiah", "Pihak"]

    precisions = []
    recalls = []
    p_err_low = []
    p_err_up = []
    r_err_low = []
    r_err_up = []

    for fld in fields:
        f_res = audit_data.get("fields", {}).get(fld, {})
        p = f_res.get("ketepatan", 0.0) * 100.0
        r = f_res.get("keterambilan", 0.0) * 100.0
        precisions.append(p)
        recalls.append(r)

        p_ci = f_res.get("wilson_ci_ketepatan", (0, 0))
        p_err_low.append(max(0, p - p_ci[0] * 100))
        p_err_up.append(max(0, p_ci[1] * 100 - p))

        r_ci = f_res.get("wilson_ci_keterambilan", (0, 0))
        r_err_low.append(max(0, r - r_ci[0] * 100))
        r_err_up.append(max(0, r_ci[1] * 100 - r))

    x = range(len(fields))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    ax.bar(
        [i - width / 2 for i in x],
        precisions,
        width,
        yerr=[p_err_low, p_err_up],
        capsize=4,
        label="Ketepatan (Precision)",
        color="#1f77b4",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.bar(
        [i + width / 2 for i in x],
        recalls,
        width,
        yerr=[r_err_low, r_err_up],
        capsize=4,
        label="Keterambilan (Recall)",
        color="#2ca02c",
        edgecolor="black",
        linewidth=0.8,
    )

    ax.set_ylabel("Nilai Persentase (%)")
    ax.set_title("Akurasi Ekstraksi Metadata per Field (Wilson Score 95% CI)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="lower right")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def export_retrieval_comparison_figure(
    eval_results: Dict[str, Any], output_path: Path
) -> None:
    """Ekspor grafik batang perbandingan metrik temu kembali utama (300 DPI)."""
    methods = [
        ("like_baseline", "LIKE (e-Arsip)", "#7f7f7f"),
        ("levenshtein_tuned", "Levenshtein (Tuned)", "#1f77b4"),
        ("jaro_winkler_tuned", "Jaro-Winkler (Tuned)", "#ff7f0e"),
        ("token_set_tuned", "Token Set (Tuned)", "#2ca02c"),
        ("ngram_tuned", "N-gram (Tuned)", "#9467bd"),
    ]

    method_labels = []
    p5_vals = []
    r10_vals = []
    mrr_vals = []

    for key, label, _ in methods:
        if key in eval_results:
            ov = eval_results[key].get("overall", {})
            method_labels.append(label)
            p5_vals.append(ov.get("precision_at_5", 0.0) * 100.0)
            r10_vals.append(ov.get("recall_at_10", 0.0) * 100.0)
            mrr_vals.append(ov.get("mrr_at_10", 0.0) * 100.0)

    if not method_labels:
        return

    x = range(len(method_labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    ax.bar(
        [i - width for i in x],
        p5_vals,
        width,
        label="Precision@5 (%)",
        color="#1f77b4",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.bar(
        list(x),
        r10_vals,
        width,
        label="Recall@10 (%)",
        color="#2ca02c",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.bar(
        [i + width for i in x],
        mrr_vals,
        width,
        label="MRR@10 (%)",
        color="#ff7f0e",
        edgecolor="black",
        linewidth=0.8,
    )

    ax.set_ylabel("Nilai (%)")
    ax.set_title("Perbandingan Kinerja Temu Kembali Arsip (Kelompok Test)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(method_labels, rotation=15, ha="right")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper left")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def export_noise_robustness_figure(
    eval_results: Dict[str, Any], output_path: Path
) -> None:
    """Ekspor grafik ketahanan terhadap 6 variasi gangguan (300 DPI)."""
    like_res = eval_results.get("like_baseline", {}).get("by_noise", {})
    ts_res = eval_results.get("token_set_tuned", {}).get("by_noise", {})
    ng_res = eval_results.get("ngram_tuned", {}).get("by_noise", {})

    all_noises = sorted(set(list(like_res.keys()) + list(ts_res.keys()) + list(ng_res.keys())))
    if not all_noises:
        return

    like_mrr = [like_res.get(n, {}).get("mrr_at_10", 0.0) * 100 for n in all_noises]
    ts_mrr = [ts_res.get(n, {}).get("mrr_at_10", 0.0) * 100 for n in all_noises]
    ng_mrr = [ng_res.get(n, {}).get("mrr_at_10", 0.0) * 100 for n in all_noises]

    x = range(len(all_noises))
    width = 0.25

    fig, ax = plt.subplots(figsize=(11, 5.5), dpi=300)
    ax.bar(
        [i - width for i in x],
        like_mrr,
        width,
        label="LIKE Baseline",
        color="#7f7f7f",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.bar(
        list(x),
        ts_mrr,
        width,
        label="Token Set (Tuned)",
        color="#2ca02c",
        edgecolor="black",
        linewidth=0.8,
    )
    ax.bar(
        [i + width for i in x],
        ng_mrr,
        width,
        label="N-gram Dice (Tuned)",
        color="#9467bd",
        edgecolor="black",
        linewidth=0.8,
    )

    clean_labels = [n.replace("_", " ").title() for n in all_noises]
    ax.set_ylabel("MRR@10 (%)")
    ax.set_title("Analisis Ketahanan Terhadap Variasi Kesalahan Pengetikan (Noise Robustness)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(clean_labels, rotation=20, ha="right")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.legend(loc="upper right")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def export_all_figures(
    eval_json_path: Path,
    audit_json_path: Path,
    output_dir: Path,
) -> None:
    """Ekspor seluruh figur untuk laporan Bab IV."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if audit_json_path.is_file():
        with open(audit_json_path, "r", encoding="utf-8") as f:
            audit_data = json.load(f)
        fig1_path = output_dir / "fig_1_akurasi_ekstraksi_wilson.png"
        export_audit_figure(audit_data, fig1_path)
        print(f"[+] Figur 1 (Akurasi Ekstraksi) disimpan ke: {fig1_path}")

    if eval_json_path.is_file():
        with open(eval_json_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f).get("results", {})
        fig2_path = output_dir / "fig_2_perbandingan_temu_kembali.png"
        export_retrieval_comparison_figure(eval_data, fig2_path)
        print(f"[+] Figur 2 (Perbandingan Temu Kembali) disimpan ke: {fig2_path}")

        fig3_path = output_dir / "fig_3_ketahanan_gangguan_noise.png"
        export_noise_robustness_figure(eval_data, fig3_path)
        print(f"[+] Figur 3 (Ketahanan Gangguan) disimpan ke: {fig3_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ekspor grafik beresolusi tinggi (300 DPI) untuk Bab IV laporan penelitian."
    )
    parser.add_argument(
        "--eval-json",
        default=str(DEFAULT_EVAL_JSON),
        help="Path berkas JSON hasil evaluasi akhir temu kembali.",
    )
    parser.add_argument(
        "--audit-json",
        default=str(DEFAULT_AUDIT_JSON),
        help="Path berkas JSON hasil audit ekstraksi metadata.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_FIGURES_DIR),
        help="Direktori penyimpanan file grafik PNG (default: output/figures).",
    )
    args = parser.parse_args()

    export_all_figures(
        eval_json_path=Path(args.eval_json),
        audit_json_path=Path(args.audit_json),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
