import json
from pathlib import Path

colab_notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 🚀 Sistem Pencarian Arsip: Fuzzy Matching & Normalisasi Metadata\n",
    "**End-to-End Pipeline: Analisis Data, Komputasi Algoritma, Evaluasi Metrik IR & Presentasi Interaktif**\n",
    "\n",
    "---\n",
    "Notebook ini dirancang khusus untuk berjalan di **Google Colab**. Seluruh tahapan memanggil langsung modul dari repositori `wahyu2021/penelitian-mandiri`."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Tahap 1: Setup Environment Google Colab & Clone Repository\n",
    "Mengunduh kode terbaru dari GitHub dan menginstal seluruh pustaka yang dibutuhkan (`requirements.txt`)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import sys\n",
    "\n",
    "# 1. Clone repository jika belum ada di environment Colab\n",
    "REPO_URL = 'https://github.com/wahyu2021/penelitian-mandiri.git'\n",
    "REPO_DIR = '/content/penelitian-mandiri'\n",
    "\n",
    "if not os.path.exists(REPO_DIR):\n",
    "    !git clone {REPO_URL} {REPO_DIR}\n",
    "else:\n",
    "    print('Repo sudah ada, menarik update terbaru...')\n",
    "    !git -C {REPO_DIR} pull\n",
    "\n",
    "# 2. Pindah ke direktori repo dan tambahkan ke sys.path\n",
    "%cd {REPO_DIR}\n",
    "if REPO_DIR not in sys.path:\n",
    "    sys.path.insert(0, REPO_DIR)\n",
    "\n",
    "# 3. Install dependencies\n",
    "!pip install -q -r requirements.txt\n",
    "print('✅ Setup environment selesai! Direktori aktif:', os.getcwd())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 1.1 (Opsional) Mount Google Drive untuk Data Mentah / SQL Dump\n",
    "Jika Anda menyimpan file *dump* SQL atau CSV asli di Google Drive (karena di GitHub data dianonimkan/tidak di-*push*), jalankan sel ini untuk memulihkan data asli menggunakan `scripts/restore_real_data.py` atau `scripts/import_dump.py`."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "USE_GOOGLE_DRIVE = False  #@param {type:\"boolean\"}\n",
    "DRIVE_DATA_PATH = \"/content/drive/MyDrive/penelitian-mandiri/data\" #@param {type:\"string\"}\n",
    "\n",
    "if USE_GOOGLE_DRIVE:\n",
    "    from google.colab import drive\n",
    "    drive.mount('/content/drive')\n",
    "    print(f'Google Drive terhubung. Silakan sesuaikan path data: {DRIVE_DATA_PATH}')\n",
    "else:\n",
    "    print('Menggunakan dataset & testset bawaan repositori (data/testset/testset_v1.json).')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## Tahap 2: Analisis Pra-Pemrosesan, Normalisasi & Ekstraksi Metadata\n",
    "Pada tahap ini kita mendemonstrasikan bagaimana teks arsip yang tidak terstruktur/kotor dibersihkan (`cleaning.py`), dinormalisasi (`normalization.py`), dan diekstraksi metadatanya (`extraction.py`)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "from IPython.display import display, Markdown\n",
    "from core import cleaning, normalization, extraction, spm_types\n",
    "\n",
    "# Contoh sampel teks deskripsi arsip mentah (dengan singkatan, typo, dan format tidak baku)\n",
    "sampel_mentah = [\n",
    "    \"BYR SPM-LS BLJ MODAL PENGADAAN LAPTOP DINAS PERPUSTAKAAN THN 2025 NO. 0012/SPM-LS/DISPUSIP/2025\",\n",
    "    \"GU - Ganti Uang Persediaan kegiatan pemeliharaan gedung kantor kearsipan plg\",\n",
    "    \"SP2D / SPM TU Belanja Barang dan Jasa Alat Tulis Kantor (ATK) Triwulan III\"\n",
    "]\n",
    "\n",
    "print('=== 1. Modul Pra-Pemrosesan yang Tersedia ===')\n",
    "print('Cleaning     :', [f for f in dir(cleaning) if not f.startswith('_')])\n",
    "print('Normalization:', [f for f in dir(normalization) if not f.startswith('_')])\n",
    "print('Extraction   :', [f for f in dir(extraction) if not f.startswith('_')])\n",
    "\n",
    "# Menampilkan hasil audit ekstraksi metadata\n",
    "print('\\n=== 2. Evaluasi Audit Ekstraksi Metadata ===')\n",
    "!python scripts/evaluate_extraction_audit.py"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## Tahap 3: Eksplorasi Testset, Skenario Noise & Bobot Tuning\n",
    "Melihat distribusi kueri pengujian pada `data/testset/testset_v1.json` serta parameter bobot optimal pada `data/testset/tuned_weights.json`."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import json\n",
    "\n",
    "with open('data/testset/testset_v1.json', 'r', encoding='utf-8') as f:\n",
    "    testset = json.load(f)\n",
    "\n",
    "with open('data/testset/tuned_weights.json', 'r', encoding='utf-8') as f:\n",
    "    weights = json.load(f)\n",
    "\n",
    "display(Markdown('### 📊 Parameter & Bobot Hasil Tuning (`tuned_weights.json`)'))\n",
    "df_weights = pd.json_normalize(weights).T.rename(columns={0: 'Nilai / Bobot'})\n",
    "display(df_weights)\n",
    "\n",
    "display(Markdown('### 📁 Ringkasan Testset (`testset_v1.json`)'))\n",
    "if isinstance(testset, dict):\n",
    "    for k, v in testset.items():\n",
    "        print(f'- {k}: {len(v) if isinstance(v, (list, dict)) else v}')\n",
    "elif isinstance(testset, list):\n",
    "    print(f'Total entri testset: {len(testset)}')\n",
    "    display(pd.DataFrame(testset).head(5))"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## Tahap 4: Komputasi Pencarian, Tuning Bobot & Evaluasi Metrik IR\n",
    "Menjalankan komputasi perbandingan antara **Baseline SQL `LIKE`** dengan algoritma **Fuzzy Matching** (*Levenshtein, Jaro-Winkler, N-Gram, Token Set Ratio*) serta mengukur kesepakatan penilai (*Inter-Annotator Agreement*)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('======================================================')\n",
    "print('1. EVALUASI METRIK TEMU KEMBALI INFORMASI (IR METRICS)')\n",
    "print('======================================================')\n",
    "!python scripts/evaluate.py\n",
    "\n",
    "print('\\n======================================================')\n",
    "print('2. EVALUASI KESEPAKATAN ANOTATOR (AGREEMENT)')\n",
    "print('======================================================')\n",
    "!python scripts/evaluate_relevance_agreement.py\n",
    "\n",
    "print('\\n======================================================')\n",
    "print('3. ANALISIS COVERAGE & UNJUDGED DOCUMENTS')\n",
    "print('======================================================')\n",
    "!python scripts/calculate_coverage.py\n",
    "!python scripts/check_unjudged.py"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### 4.1 (Opsional) Menjalankan Ulang Hyperparameter / Weight Tuning\n",
    "Jika Anda ingin mendemonstrasikan proses pencarian bobot terbaik secara langsung di depan penguji/audiens, jalankan sel berikut."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "RUN_TUNING = False #@param {type:\"boolean\"}\n",
    "if RUN_TUNING:\n",
    "    !python scripts/tune_weights.py\n",
    "else:\n",
    "    print('Tuning dilewati (menggunakan bobot optimal yang sudah tersimpan di data/testset/tuned_weights.json).')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## Tahap 5: Visualisasi Grafik untuk Laporan & Presentasi\n",
    "Mengeksekusi `scripts/export_report_figures.py` dan menampilkan seluruh grafik hasil eksperimen langsung di layar Google Colab."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import glob\n",
    "from IPython.display import Image, display\n",
    "\n",
    "# Jalankan script pembuat grafik\n",
    "!python scripts/export_report_figures.py\n",
    "\n",
    "# Cari dan tampilkan semua gambar (.png / .jpg / .pdf) yang baru saja dibuat\n",
    "image_files = sorted(glob.glob('output/figures/*.png') + glob.glob('**/*.png', recursive=True))\n",
    "image_files = list(dict.fromkeys(image_files))\n",
    "if image_files:\n",
    "    print(f'Ditemukan {len(image_files)} grafik visualisasi:')\n",
    "    for img_path in image_files:\n",
    "        if 'figures' in img_path:\n",
    "            display(Markdown(f'#### 📈 `{img_path}`'))\n",
    "            display(Image(filename=img_path))\n",
    "else:\n",
    "    print('Belum ada file .png yang ditemukan. Pastikan export_report_figures.py menyimpan output ke format gambar.')"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "---\n",
    "## Tahap 6: Live Demo Interaktif (Untuk Presentasi / Sidang)\n",
    "Gunakan panel *form* di sebelah kanan sel ini saat presentasi untuk menguji kueri pencarian secara langsung (misalnya kueri dengan *typo*, urutan kata terbalik, atau singkatan) dan melihat perbandingan skor tiap algoritma *Fuzzy Matcher*."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "#@title 🔍 Simulasi Perbandingan Algoritma Fuzzy Matching Secara Real-Time { run: \"auto\" }\n",
    "KUERI_PENCARIAN = \"belanja modal pengadaan komputer dinas perpustakaan\" #@param {type:\"string\"}\n",
    "TEKS_ARSIP_TARGET = \"SPM-LS BLJ MODAL PENGADAAN LAPTOP DAN PC DINAS PERPUSTAKAAN DAN KEARSIPAN KOTA PALEMBANG\" #@param {type:\"string\"}\n",
    "\n",
    "from core.search.matchers.levenshtein import LevenshteinMatcher\n",
    "from core.search.matchers.jaro_winkler import JaroWinklerMatcher\n",
    "from core.search.matchers.ngram import NGramMatcher\n",
    "from core.search.matchers.token_set import TokenSetMatcher\n",
    "\n",
    "# Uji kemiripan menggunakan masing-masing matcher di folder core/search/matchers/\n",
    "matchers = [\n",
    "    ('Levenshtein', LevenshteinMatcher()),\n",
    "    ('Jaro-Winkler', JaroWinklerMatcher()),\n",
    "    ('N-Gram', NGramMatcher()),\n",
    "    ('Token Set', TokenSetMatcher()),\n",
    "]\n",
    "\n",
    "hasil_demo = []\n",
    "for nama, m in matchers:\n",
    "    for method_name in ['similarity', 'score', 'match', 'compute']:\n",
    "        if hasattr(m, method_name):\n",
    "            skor = getattr(m, method_name)(KUERI_PENCARIAN.lower(), TEKS_ARSIP_TARGET.lower())\n",
    "            hasil_demo.append({'Algoritma Matcher': nama, 'Skor Kemiripan': round(float(skor), 4)})\n",
    "            break\n",
    "\n",
    "df_demo = pd.DataFrame(hasil_demo)\n",
    "display(Markdown(f'**Kueri:** `{KUERI_PENCARIAN}`  \\n**Target Arsip:** `{TEKS_ARSIP_TARGET}`'))\n",
    "display(df_demo)"
   ]
  }
 ],
 "metadata": {
  "colab": {
   "name": "Colab_Analisis_Komputasi_Presentasi.ipynb",
   "provenance": []
  },
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.12"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 0
}

# Simpan di root dan di folder notebooks/
for out_path in ["Colab_Analisis_Komputasi_Presentasi.ipynb", "notebooks/Colab_Analisis_Komputasi_Presentasi.ipynb"]:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(colab_notebook, f, indent=2, ensure_ascii=False)
    print(f"[+] File '{out_path}' berhasil dibuat!")
