import json
import os
from pathlib import Path

notebook_structure = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Analisis, Komputasi, dan Evaluasi Sistem Pencarian Arsip\n",
                "**Metode:** Fuzzy Matching & Normalisasi Metadata\n",
                "---\n",
                "Notebook ini mencakup keseluruhan *pipeline* penelitian mulai dari persiapan data, normalisasi metadata, komputasi algoritma *fuzzy matching*, optimasi bobot (*tuning*), evaluasi metrik *Information Retrieval*, hingga visualisasi hasil untuk presentasi."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Konfigurasi Lingkungan & Impor Modul\n",
                "Menambahkan direktori utama (*root*) ke dalam `sys.path` agar seluruh modul pada paket `core`, `services`, dan `scripts` dapat diakses langsung dari notebook."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys\n",
                "import os\n",
                "import json\n",
                "from pathlib import Path\n",
                "import pandas as pd\n",
                "import numpy as np\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "\n",
                "# Pastikan root project masuk ke sys.path\n",
                "PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n",
                "if str(PROJECT_ROOT) not in sys.path:\n",
                "    sys.path.insert(0, str(PROJECT_ROOT))\n",
                "\n",
                "print(f'Project Root: {PROJECT_ROOT}')\n",
                "sns.set_theme(style='whitegrid', palette='muted')\n",
                "plt.rcParams['figure.figsize'] = (10, 6)"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Tahap Pra-Pemrosesan: Cleaning, Normalisasi & Ekstraksi Metadata\n",
                "Menguji dan menampilkan cara kerja fungsi pembersihan teks, normalisasi metadata, dan ekstraksi entitas dari data arsip."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import core.cleaning as cleaning\n",
                "import core.normalization as normalization\n",
                "import core.extraction as extraction\n",
                "\n",
                "# Menampilkan daftar fungsi yang tersedia pada modul pra-pemrosesan\n",
                "print('Fungsi Cleaning:', [f for f in dir(cleaning) if not f.startswith('_')])\n",
                "print('Fungsi Normalization:', [f for f in dir(normalization) if not f.startswith('_')])\n",
                "print('Fungsi Extraction:', [f for f in dir(extraction) if not f.startswith('_')])"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "### 2.1 Evaluasi Audit Ekstraksi Metadata\n",
                "Menjalankan perhitungan akurasi/kualitas hasil ekstraksi dan normalisasi metadata."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from core.evaluation import audit_metrics\n",
                "# Memanggil skrip evaluasi audit ekstraksi jika tersedia\n",
                "try:\n",
                "    from scripts import evaluate_extraction_audit\n",
                "    print('Modul evaluate_extraction_audit siap dijalankan.')\n",
                "except Exception as e:\n",
                "    print(f'Info: {e}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Pemuatan Testset & Bobot Hasil Tuning\n",
                "Memuat dataset pengujian (`testset_v1.json`) dan konfigurasi bobot optimal (`tuned_weights.json`)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "TESTSET_PATH = PROJECT_ROOT / 'data' / 'testset' / 'testset_v1.json'\n",
                "WEIGHTS_PATH = PROJECT_ROOT / 'data' / 'testset' / 'tuned_weights.json'\n",
                "\n",
                "with open(TESTSET_PATH, 'r', encoding='utf-8') as f:\n",
                "    testset_data = json.load(f)\n",
                "\n",
                "with open(WEIGHTS_PATH, 'r', encoding='utf-8') as f:\n",
                "    tuned_weights = json.load(f)\n",
                "\n",
                "print('=== Konfigurasi Tuned Weights ===')\n",
                "display(pd.Series(tuned_weights).to_frame(name='Bobot / Parameter'))\n",
                "\n",
                "if isinstance(testset_data, dict):\n",
                "    print('\\nKunci utama pada testset_v1.json:', list(testset_data.keys()))\n",
                "elif isinstance(testset_data, list):\n",
                "    print(f'\\nJumlah item pada testset_v1.json: {len(testset_data)}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. Komputasi Algoritma Pencarian (Baseline vs Fuzzy Matchers)\n",
                "Membandingkan mekanisme pencarian *exact/substring* (`LIKE` baseline) dengan 4 algoritma *Fuzzy Matching*:\n",
                "1. **Levenshtein Distance**\n",
                "2. **Jaro-Winkler Similarity**\n",
                "3. **N-Gram Similarity**\n",
                "4. **Token Set Ratio**"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from core.search import index, ranker, like_baseline\n",
                "from core.search.matchers import levenshtein, jaro_winkler, ngram, token_set\n",
                "\n",
                "print('Modul pencarian dan matcher berhasil dimuat:')\n",
                "for mod in [like_baseline, levenshtein, jaro_winkler, ngram, token_set, ranker]:\n",
                "    print(f'- {mod.__name__}: {[x for x in dir(mod) if not x.startswith(\"_\")]}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 5. Komputasi Evaluasi Kinerja & Kesepakatan Relevansi\n",
                "Menjalankan evaluasi komprehensif pada seluruh kueri uji untuk mendapatkan skor performa masing-masing algoritma serta menguji konsistensi anotasi (*Inter-Annotator Agreement*)."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from core.evaluation import evaluator, metrics, agreement, tuning\n",
                "\n",
                "# Menjalankan skrip evaluasi utama dan menampilkan hasilnya di output sel\n",
                "%run -i \"{PROJECT_ROOT / 'scripts' / 'evaluate.py'}\""
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Menjalankan evaluasi kesepakatan relevansi (Inter-Annotator Agreement)\n",
                "try:\n",
                "    %run -i \"{PROJECT_ROOT / 'scripts' / 'evaluate_relevance_agreement.py'}\"\n",
                "except Exception as e:\n",
                "    print(f'Catatan eksekusi agreement: {e}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 6. Presentasi & Visualisasi Hasil Eksperimen\n",
                "Membangkitkan grafik perbandingan metrik evaluasi dan menyimpannya sebagai gambar siap pakai untuk laporan maupun slide presentasi."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Menjalankan pembuatan grafik laporan dan menampilkannya secara inline\n",
                "%matplotlib inline\n",
                "try:\n",
                "    %run -i \"{PROJECT_ROOT / 'scripts' / 'export_report_figures.py'}\"\n",
                "except Exception as e:\n",
                "    print(f'Catatan visualisasi: {e}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 7. Ringkasan Eksekutif & Simulasi Interaktif (Demo Presentasi)\n",
                "Sel ini dapat digunakan saat presentasi untuk mendemonstrasikan secara langsung (*live demo*) perbedaan hasil pencarian antara metode konvensional (`LIKE`) dan sistem pencarian berbasis *Fuzzy Matching* + Normalisasi Metadata."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Silakan ubah variabel kueri di bawah ini saat live demo presentasi\n",
                "QUERY_UJI = 'spm belanja modal dinas'  # Contoh kueri dengan variasi/typo\n",
                "TOP_K = 5\n",
                "\n",
                "print(f'Simulasi Pencarian untuk Kueri: \"{QUERY_UJI}\" (Top-{TOP_K})')\n",
                "# Tambahkan pemanggilan fungsi search_index / ranker Anda di bawah ini sesuai objek indeks yang aktif"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.11.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_dir = Path("notebooks")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "pipeline_analisis_sampai_presentasi.ipynb"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook_structure, f, indent=2, ensure_ascii=False)

print(f"Berhasil membuat notebook di: {output_path}")
