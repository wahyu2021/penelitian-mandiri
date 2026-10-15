import json
from pathlib import Path

# Baca data resmi hasil evaluasi dan audit
audit_path = Path("output/extraction_audit_report.json")
eval_path = Path("output/final_evaluation_results.json")

with open(audit_path, "r", encoding="utf-8") as f:
    audit_data = json.load(f)

with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)

notebook_content = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Analisis & Evaluasi Hasil Penelitian Temu Kembali Arsip (Bab IV)\n",
                "\n",
                "**Judul Penelitian:** *Sistem Pencarian Arsip Menggunakan Fuzzy Matching dan Normalisasi Metadata Berbasis Website pada Dinas Perpustakaan dan Kearsipan Kota Palembang*\n",
                "\n",
                "---\n",
                "\n",
                "### Panduan Penggunaan di Google Colab\n",
                "Notebook ini dirancang **100% mandiri (*self-contained*)**:\n",
                "- Dapat dijalankan langsung di **Google Colab** tanpa perlu menginstal dependensi tambahan.\n",
                "- Dilengkapi data resmi hasil evaluasi tersemat (*embedded*) serta dukungan membaca berkas dari direktori lokal `output/` jika tersedia.\n",
                "- Cukup klik menu **Runtime** &rarr; **Run all** (atau tekan `Ctrl + F9`)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Inisialisasi Lingkungan & Pemuatan Data\n",
                "import json\n",
                "from pathlib import Path\n",
                "import matplotlib.pyplot as plt\n",
                "import pandas as pd\n",
                "try:\n",
                "    from IPython.display import display, HTML\n",
                "except ImportError:\n",
                "    def display(x): print(x)\n",
                "    def HTML(x): return x\n",
                "\n",
                "# Data Tersemat Resmi (Fallback jika berkas di output/ belum diunggah ke Colab)\n",
                f"EMBEDDED_AUDIT_DATA = json.loads({repr(json.dumps(audit_data))})\n",
                f"EMBEDDED_EVAL_DATA = json.loads({repr(json.dumps(eval_data))})\n",
                "\n",
                "# Cek keberadaan berkas lokal output/\n",
                "AUDIT_PATH = Path(\"output/extraction_audit_report.json\")\n",
                "if not AUDIT_PATH.exists() and Path(\"../output/extraction_audit_report.json\").exists():\n",
                "    AUDIT_PATH = Path(\"../output/extraction_audit_report.json\")\n",
                "\n",
                "EVAL_PATH = Path(\"output/final_evaluation_results.json\")\n",
                "if not EVAL_PATH.exists() and Path(\"../output/final_evaluation_results.json\").exists():\n",
                "    EVAL_PATH = Path(\"../output/final_evaluation_results.json\")\n",
                "\n",
                "if AUDIT_PATH.exists():\n",
                "    with open(AUDIT_PATH, \"r\", encoding=\"utf-8\") as f:\n",
                "        audit_json = json.load(f)\n",
                "    print(f\"[+] Memuat data audit dari berkas lokal: {AUDIT_PATH}\")\n",
                "else:\n",
                "    audit_json = EMBEDDED_AUDIT_DATA\n",
                "    print(\"[+] Memuat data audit dari memori tersemat (Colab Mode)\")\n",
                "\n",
                "if EVAL_PATH.exists():\n",
                "    with open(EVAL_PATH, \"r\", encoding=\"utf-8\") as f:\n",
                "        eval_json = json.load(f)\n",
                "    print(f\"[+] Memuat data evaluasi dari berkas lokal: {EVAL_PATH}\")\n",
                "else:\n",
                "    eval_json = EMBEDDED_EVAL_DATA\n",
                "    print(\"[+] Memuat data evaluasi dari memori tersemat (Colab Mode)\")\n",
                "\n",
                "manifest = eval_json.get(\"manifest\", {})\n",
                "print(f\"[*] Git Commit SHA  : {manifest.get('git_commit_sha')}\")\n",
                "print(f\"[*] Testset Hash    : {manifest.get('testset_sha256')}\")\n",
                "print(f\"[*] Jumlah Kueri Uji: {manifest.get('n_test_queries')} kueri test\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Audit Akurasi Ekstraksi Metadata (100 Sampel Berstrata)\n",
                "\n",
                "Evaluasi akurasi ekstraksi informasi dari ringkasan bebas dokumen pembayaran (`summary_raw`) terhadap 5 entitas metadata: **Nomor SPM, Nomor SP2D, Tanggal Dokumen, Nilai Rupiah, dan Nama Pihak (CV/PT)** beserta **Wilson Score 95% Confidence Interval**."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Tabel Akurasi Ekstraksi Metadata\n",
                "fields_dict = audit_json.get(\"fields\", {})\n",
                "field_labels = {\n",
                "    \"spm\": \"Nomor SPM\",\n",
                "    \"sp2d\": \"Nomor SP2D\",\n",
                "    \"date\": \"Tanggal Dokumen\",\n",
                "    \"amount\": \"Nilai Rupiah\",\n",
                "    \"party\": \"Nama Pihak (CV/PT)\",\n",
                "}\n",
                "\n",
                "audit_rows = []\n",
                "for fld, info in fields_dict.items():\n",
                "    p_ci = info.get(\"wilson_ci_ketepatan\", [0, 0])\n",
                "    r_ci = info.get(\"wilson_ci_keterambilan\", [0, 0])\n",
                "    audit_rows.append({\n",
                "        \"Field Metadata\": field_labels.get(fld, fld),\n",
                "        \"Benar\": info.get(\"n_benar\"),\n",
                "        \"Salah\": info.get(\"n_salah\"),\n",
                "        \"Terlewat\": info.get(\"n_terlewat\"),\n",
                "        \"Tidak Ada\": info.get(\"n_tidak_ada_di_teks\"),\n",
                "        \"Ketepatan / Precision (%)\": round(info.get(\"ketepatan\", 0) * 100, 2),\n",
                "        \"95% CI Ketepatan\": f\"[{p_ci[0]*100:.1f}%, {p_ci[1]*100:.1f}%]\",\n",
                "        \"Keterambilan / Recall (%)\": round(info.get(\"keterambilan\", 0) * 100, 2),\n",
                "        \"95% CI Keterambilan\": f\"[{r_ci[0]*100:.1f}%, {r_ci[1]*100:.1f}%]\",\n",
                "    })\n",
                "\n",
                "df_audit = pd.DataFrame(audit_rows)\n",
                "display(HTML(\"<h4>Tabel 1: Akurasi Ekstraksi Metadata per Field</h4>\"))\n",
                "display(df_audit)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualisasi Gambar 1: Akurasi Ekstraksi Metadata dengan Error Bar 95% CI\n",
                "f_keys = [\"spm\", \"sp2d\", \"date\", \"amount\", \"party\"]\n",
                "f_names = [field_labels[k] for k in f_keys]\n",
                "\n",
                "precisions = [fields_dict[k][\"ketepatan\"] * 100 for k in f_keys]\n",
                "recalls = [fields_dict[k][\"keterambilan\"] * 100 for k in f_keys]\n",
                "\n",
                "p_err_low = [max(0, precisions[i] - fields_dict[k][\"wilson_ci_ketepatan\"][0] * 100) for i, k in enumerate(f_keys)]\n",
                "p_err_up = [max(0, fields_dict[k][\"wilson_ci_ketepatan\"][1] * 100 - precisions[i]) for i, k in enumerate(f_keys)]\n",
                "\n",
                "r_err_low = [max(0, recalls[i] - fields_dict[k][\"wilson_ci_keterambilan\"][0] * 100) for i, k in enumerate(f_keys)]\n",
                "r_err_up = [max(0, fields_dict[k][\"wilson_ci_keterambilan\"][1] * 100 - recalls[i]) for i, k in enumerate(f_keys)]\n",
                "\n",
                "x = range(len(f_keys))\n",
                "width = 0.35\n",
                "\n",
                "fig, ax = plt.subplots(figsize=(9, 5), dpi=150)\n",
                "ax.bar([i - width/2 for i in x], precisions, width, yerr=[p_err_low, p_err_up], capsize=5, label=\"Ketepatan (Precision)\", color=\"#2563eb\", edgecolor=\"black\", linewidth=0.8)\n",
                "ax.bar([i + width/2 for i in x], recalls, width, yerr=[r_err_low, r_err_up], capsize=5, label=\"Keterambilan (Recall)\", color=\"#16a34a\", edgecolor=\"black\", linewidth=0.8)\n",
                "\n",
                "ax.set_ylabel(\"Nilai Persentase (%)\", fontsize=11, fontweight=\"bold\")\n",
                "ax.set_title(\"Figur 1: Akurasi Ekstraksi Metadata per Field (Wilson Score 95% CI)\", fontsize=12, fontweight=\"bold\", pad=12)\n",
                "ax.set_xticks(list(x))\n",
                "ax.set_xticklabels(f_names, fontsize=10)\n",
                "ax.set_ylim(0, 105)\n",
                "ax.grid(axis=\"y\", linestyle=\"--\", alpha=0.5)\n",
                "ax.legend(loc=\"lower right\", framealpha=0.9)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Hasil Temu Kembali Komparatif (Kelompok Test)\n",
                "\n",
                "Perbandingan efektivitas pencarian antara **LIKE Baseline (sistem pencarian bawaan e-Arsip SIMANIS)** melawan **empat metode Fuzzy Matching** (Levenshtein, Jaro-Winkler, Token-Set, dan N-Gram Dice) baik konfigurasi bobot sama rata (*Equal*) maupun bobot optimal (*Tuned*)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Tabel Metrik Temu Kembali Keseluruhan\n",
                "results = eval_json.get(\"results\", {})\n",
                "\n",
                "method_display_names = {\n",
                "    \"like_baseline\": \"LIKE Baseline (e-Arsip)\",\n",
                "    \"levenshtein_equal\": \"Levenshtein (Equal Weights)\",\n",
                "    \"jaro_winkler_equal\": \"Jaro-Winkler (Equal Weights)\",\n",
                "    \"token_set_equal\": \"Token-Set (Equal Weights)\",\n",
                "    \"ngram_equal\": \"N-Gram Dice (Equal Weights)\",\n",
                "    \"levenshtein_tuned\": \"Levenshtein (Tuned Weights)\",\n",
                "    \"jaro_winkler_tuned\": \"Jaro-Winkler (Tuned Weights)\",\n",
                "    \"token_set_tuned\": \"Token-Set (Tuned Weights)\",\n",
                "    \"ngram_tuned\": \"N-Gram Dice (Tuned Weights)\",\n",
                "}\n",
                "\n",
                "eval_rows = []\n",
                "for m_key, disp_name in method_display_names.items():\n",
                "    if m_key in results:\n",
                "        ov = results[m_key].get(\"overall\", {})\n",
                "        eval_rows.append({\n",
                "            \"Metode / Konfigurasi\": disp_name,\n",
                "            \"Nol Hasil\": ov.get(\"zero_result_queries\", 0),\n",
                "            \"Precision@5\": round(ov.get(\"precision_at_5\", 0), 4),\n",
                "            \"Recall@10\": round(ov.get(\"recall_at_10\", 0), 4),\n",
                "            \"MRR@10\": round(ov.get(\"mrr_at_10\", 0), 4),\n",
                "            \"Hit Rate@5\": round(ov.get(\"hit_rate_at_5\", 0), 4),\n",
                "            \"Hit Rate@10\": round(ov.get(\"hit_rate_at_10\", 0), 4),\n",
                "            \"Rata-rata Latensi (ms)\": round(ov.get(\"mean_latency_ms\", 0), 2),\n",
                "            \"P95 Latensi (ms)\": round(ov.get(\"p95_latency_ms\", 0), 2),\n",
                "        })\n",
                "\n",
                "df_eval = pd.DataFrame(eval_rows)\n",
                "display(HTML(\"<h4>Tabel 2: Perbandingan Komparatif Kinerja Temu Kembali Arsip</h4>\"))\n",
                "display(df_eval)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualisasi Gambar 2: Perbandingan Metrik Temu Kembali Utama\n",
                "methods_plot = [\n",
                "    (\"like_baseline\", \"LIKE Baseline\", \"#64748b\"),\n",
                "    (\"levenshtein_tuned\", \"Levenshtein (Tuned)\", \"#0284c7\"),\n",
                "    (\"jaro_winkler_tuned\", \"Jaro-Winkler (Tuned)\", \"#ea580c\"),\n",
                "    (\"token_set_tuned\", \"Token-Set (Tuned)\", \"#16a34a\"),\n",
                "    (\"ngram_tuned\", \"N-Gram (Tuned)\", \"#9333ea\"),\n",
                "]\n",
                "\n",
                "labels = [m[1] for m in methods_plot if m[0] in results]\n",
                "p5_vals = [results[m[0]][\"overall\"][\"precision_at_5\"] * 100 for m in methods_plot if m[0] in results]\n",
                "r10_vals = [results[m[0]][\"overall\"][\"recall_at_10\"] * 100 for m in methods_plot if m[0] in results]\n",
                "mrr_vals = [results[m[0]][\"overall\"][\"mrr_at_10\"] * 100 for m in methods_plot if m[0] in results]\n",
                "\n",
                "x = range(len(labels))\n",
                "width = 0.25\n",
                "\n",
                "fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)\n",
                "ax.bar([i - width for i in x], p5_vals, width, label=\"Precision@5 (%)\", color=\"#0284c7\", edgecolor=\"black\", linewidth=0.8)\n",
                "ax.bar(list(x), r10_vals, width, label=\"Recall@10 (%)\", color=\"#16a34a\", edgecolor=\"black\", linewidth=0.8)\n",
                "ax.bar([i + width for i in x], mrr_vals, width, label=\"MRR@10 (%)\", color=\"#ea580c\", edgecolor=\"black\", linewidth=0.8)\n",
                "\n",
                "ax.set_ylabel(\"Nilai (%)\", fontsize=11, fontweight=\"bold\")\n",
                "ax.set_title(\"Figur 2: Perbandingan Kinerja Temu Kembali Arsip (Kelompok Test)\", fontsize=12, fontweight=\"bold\", pad=12)\n",
                "ax.set_xticks(list(x))\n",
                "ax.set_xticklabels(labels, rotation=15, ha=\"right\", fontsize=10)\n",
                "ax.set_ylim(0, max(max(p5_vals), max(r10_vals), max(mrr_vals), 5) * 1.35)\n",
                "ax.grid(axis=\"y\", linestyle=\"--\", alpha=0.5)\n",
                "ax.legend(loc=\"upper right\", framealpha=0.9)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Ketahanan Terhadap Variasi Kesalahan Pengetikan (*Noise Robustness*)\n",
                "\n",
                "Pengujian ketahanan terhadap **6 ragam kesalahan pengetikan manusia nyata** (*typo*, singkatan, tanda baca/spasi, urutan kata terbalik, kata hilang, ejaan varian, dan kueri bersih tanpa gangguan)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Visualisasi Gambar 3: Ketahanan Terhadap 6 Jenis Gangguan\n",
                "like_bn = results.get(\"like_baseline\", {}).get(\"by_noise\", {})\n",
                "ts_bn = results.get(\"token_set_tuned\", {}).get(\"by_noise\", {})\n",
                "ng_bn = results.get(\"ngram_tuned\", {}).get(\"by_noise\", {})\n",
                "\n",
                "all_noises = sorted(set(list(like_bn.keys()) + list(ts_bn.keys()) + list(ng_bn.keys())))\n",
                "like_mrr = [like_bn.get(n, {}).get(\"mrr_at_10\", 0.0) * 100 for n in all_noises]\n",
                "ts_mrr = [ts_bn.get(n, {}).get(\"mrr_at_10\", 0.0) * 100 for n in all_noises]\n",
                "ng_mrr = [ng_bn.get(n, {}).get(\"mrr_at_10\", 0.0) * 100 for n in all_noises]\n",
                "\n",
                "x = range(len(all_noises))\n",
                "width = 0.25\n",
                "\n",
                "fig, ax = plt.subplots(figsize=(11, 5.5), dpi=150)\n",
                "ax.bar([i - width for i in x], like_mrr, width, label=\"LIKE Baseline\", color=\"#64748b\", edgecolor=\"black\", linewidth=0.8)\n",
                "ax.bar(list(x), ts_mrr, width, label=\"Token-Set (Tuned)\", color=\"#16a34a\", edgecolor=\"black\", linewidth=0.8)\n",
                "ax.bar([i + width for i in x], ng_mrr, width, label=\"N-Gram (Tuned)\", color=\"#9333ea\", edgecolor=\"black\", linewidth=0.8)\n",
                "\n",
                "ax.set_ylabel(\"MRR@10 (%)\", fontsize=11, fontweight=\"bold\")\n",
                "ax.set_title(\"Figur 3: Ketahanan Sistem Temu Kembali Terhadap Ragam Gangguan Kueri\", fontsize=12, fontweight=\"bold\", pad=12)\n",
                "ax.set_xticks(list(x))\n",
                "ax.set_xticklabels(all_noises, rotation=20, ha=\"right\", fontsize=10)\n",
                "ax.grid(axis=\"y\", linestyle=\"--\", alpha=0.5)\n",
                "ax.legend(loc=\"upper right\", framealpha=0.9)\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. Kesimpulan Kinerja Temu Kembali untuk Bab Pembahasan\n",
                "\n",
                "1. **Kegagalan Sistem Eksak Bawaan:** SQL `LIKE` mengalami kegagalan total (**Nol Hasil**) pada **64,3% kueri test** akibat tidak mampu menangani variasi ejaan, singkatan, dan tanda baca.\n",
                "2. **Keandalan Fuzzy Matching:** Seluruh metode fuzzy matching menghasilkan **Nol Hasil = 0%** (selalu mengembalikan kandidat dokumen arsip).\n",
                "3. **Metode Rekomendasi:** **Token-Set (Tuned)** memiliki efisiensi komputasi tertinggi dengan latensi rata-rata hanya **6,13 milidetik** (jauh di bawah batas interaksi web 100 ms), sehingga paling optimal untuk diterapkan pada website e-Arsip produksi."
            ]
        }
    ],
    "metadata": {
        "colab": {
            "name": "analisis_evaluasi.ipynb",
            "provenance": []
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_file = Path("notebooks/analisis_evaluasi.ipynb")
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(notebook_content, f, indent=1, ensure_ascii=False)

print(f"[+] Notebook berhasil diperbarui: {output_file}")
