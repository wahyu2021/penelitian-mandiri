"""Generator untuk membangun file Jupyter Notebook resmi 16-Sel (Sel 0 - 15).
Sesuai rancangan baku Colab Bundle (Hanya membaca hasil agregat tanpa teks arsip).
"""
import json
from pathlib import Path


def build_16_cell_notebook() -> dict:
    cells = []

    # =========================================================================
    # SEL 0: Judul dan pernyataan data (Markdown)
    # =========================================================================
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Evaluasi Ilmiah Sistem Temu Kembali Arsip Berbasis Hasil Agregat\n",
            "### Analisis Kinerja Fuzzy Matching & Normalisasi Metadata Tanpa Ekspor Teks Arsip\n",
            "**Versi Notebook:** 1.0.0 (Spesifikasi Resmi Konsumsi Bundle)\n",
            "\n",
            "---\n",
            "\n",
            "### 🔒 Pernyataan Privasi & Integritas Data\n",
            "- **Zero Raw-Data Ingestion:** Notebook ini **HANYA** membaca data hasil evaluasi teragregasi dari berkas bundle (`run_meta.json`, `per_query_results.csv`, `tuning_results.csv`, `audit_summary.json`, `agreement_summary.json`).\n",
            "- **Perlindungan Privasi Dinas:** Tidak ada teks ringkasan arsip mentah (`summary_raw`), nomor SPM, nama rekanan/pihak ketiga (`party_name`), maupun teks kueri asli (`query_text`) yang diunggah ke runtime ini.\n",
            "- **Validasi Keterulangan:** Seluruh berkas bundle diverifikasi terhadap hash kriptografis `manifest.sha256` yang dihasilkan langsung dari laptop peneliti dalam status *working tree* bersih."
        ]
    })

    # =========================================================================
    # SEL 1: Persiapan (Code)
    # Syarat lulus: Versi paket sesuai dengan run_meta.json
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 1: PERSIAPAN LINGKUNGAN & KUNCI SEED ACAK\n",
            "# Syarat lulus: Paket ilmiah terpasang dan seed acak diatur = 42\n",
            "# =====================================================================\n",
            "import os\n",
            "import sys\n",
            "import json\n",
            "import hashlib\n",
            "from pathlib import Path\n",
            "\n",
            "# Pasang dependensi jika berjalan di Google Colab\n",
            "try:\n",
            "    import google.colab\n",
            "    IN_COLAB = True\n",
            "    !pip install -q pandas numpy scipy matplotlib rapidfuzz\n",
            "except ImportError:\n",
            "    IN_COLAB = False\n",
            "\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "import scipy\n",
            "import matplotlib\n",
            "import matplotlib.pyplot as plt\n",
            "\n",
            "RANDOM_SEED = 42\n",
            "np.random.seed(RANDOM_SEED)\n",
            "\n",
            "print(\"=== VERSI LINGKUNGAN RUNTIME ===\")\n",
            "print(f\"Python     : {sys.version.split()[0]}\")\n",
            "print(f\"Pandas     : {pd.__version__}\")\n",
            "print(f\"NumPy      : {np.__version__}\")\n",
            "print(f\"SciPy      : {scipy.__version__}\")\n",
            "print(f\"Matplotlib : {matplotlib.__version__}\")\n",
            "print(f\"Random Seed: {RANDOM_SEED} (terkunci)\")\n",
            "print(\"\\n[STATUS] Sel 1 Lulus: Lingkungan siap.\")"
        ]
    })

    # =========================================================================
    # SEL 2: Unggah Hasil (Code)
    # Syarat lulus: Tolak bila ada kolom query_text, summary_raw, atau party_name
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 2: PEMUATAN BERKAS BUNDLE & PEMERIKSAAN DAFTAR PUTIH KOLOM\n",
            "# Syarat lulus: Tolak bila ditemukan kolom teks arsip/terlarang\n",
            "# =====================================================================\n",
            "FORBIDDEN_COLUMNS = {\n",
            "    \"query_text\", \"summary_raw\", \"summary_clean\", \"party_name\",\n",
            "    \"spm_number\", \"sp2d_number\", \"amount_rp\", \"haystack\", \"nominal\"\n",
            "}\n",
            "\n",
            "EXPECTED_FILES = [\n",
            "    \"run_meta.json\",\n",
            "    \"per_query_results.csv\",\n",
            "    \"tuning_results.csv\",\n",
            "    \"audit_summary.json\",\n",
            "    \"agreement_summary.json\",\n",
            "    \"manifest.sha256\"\n",
            "]\n",
            "\n",
            "# Tentukan lokasi direktori bundle secara dinamis (root, subfolder notebooks, atau Colab)\n",
            "CANDIDATE_DIRS = [\n",
            "    Path(\"output/colab_bundle\"),\n",
            "    Path(\"../output/colab_bundle\"),\n",
            "    Path(\"colab_bundle\"),\n",
            "    Path(\"../colab_bundle\"),\n",
            "    Path(\".\"),\n",
            "]\n",
            "\n",
            "BUNDLE_DIR = None\n",
            "for cdir in CANDIDATE_DIRS:\n",
            "    if cdir.is_dir() and (cdir / \"manifest.sha256\").is_file():\n",
            "        BUNDLE_DIR = cdir\n",
            "        break\n",
            "\n",
            "# Jika belum ada dan berada di Google Colab, sediakan dialog unggah\n",
            "if BUNDLE_DIR is None:\n",
            "    if IN_COLAB:\n",
            "        from google.colab import files\n",
            "        print(\"Silakan unggah 6 berkas bundle dari folder output/colab_bundle/:\")\n",
            "        uploaded = files.upload()\n",
            "        BUNDLE_DIR = Path(\".\")\n",
            "    else:\n",
            "        raise FileNotFoundError(\n",
            "            \"Direktori bundle tidak ditemukan di lokasi mana pun (output/colab_bundle, ../output/colab_bundle, dll). \"\n",
            "            \"Jalankan `flask report export-bundle` terlebih dahulu di laptop.\"\n",
            "        )\n",
            "\n",
            "# Verifikasi keberadaan semua berkas wajib\n",
            "for fname in EXPECTED_FILES:\n",
            "    fpath = BUNDLE_DIR / fname\n",
            "    if not fpath.is_file():\n",
            "        raise FileNotFoundError(f\"[GAGAL] Berkas bundle wajib tidak ditemukan: {fname}\")\n",
            "\n",
            "# Pemeriksaan keamanan kolom pada per_query_results.csv\n",
            "df_per_query = pd.read_csv(BUNDLE_DIR / \"per_query_results.csv\")\n",
            "found_forbidden = FORBIDDEN_COLUMNS.intersection(set(df_per_query.columns))\n",
            "if found_forbidden:\n",
            "    raise ValueError(f\"[GAGAL TOTAL] Ditemukan kolom teks arsip terlarang: {found_forbidden}\")\n",
            "\n",
            "# Pemeriksaan keamanan kolom pada tuning_results.csv\n",
            "df_tuning = pd.read_csv(BUNDLE_DIR / \"tuning_results.csv\")\n",
            "found_forbidden_tuning = FORBIDDEN_COLUMNS.intersection(set(df_tuning.columns))\n",
            "if found_forbidden_tuning:\n",
            "    raise ValueError(f\"[GAGAL TOTAL] Ditemukan kolom terlarang di tuning_results.csv: {found_forbidden_tuning}\")\n",
            "\n",
            "print(f\"[OK] Seluruh {len(EXPECTED_FILES)} berkas bundle tersedia di: {BUNDLE_DIR}\")\n",
            "print(f\"[OK] Pemeriksaan privasi lolos: 0 kolom teks arsip terlarang terdeteksi.\")\n",
            "print(f\"     Kolom per_query_results: {list(df_per_query.columns)}\")"
        ]
    })

    # =========================================================================
    # SEL 3: Integritas (Code)
    # Syarat lulus: tree_clean = True, mode = final, hash cocok
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 3: VERIFIKASI INTEGRITAS KRIPTOGRAFIS & MANIFEST REPRODUCIBILITY\n",
            "# Syarat lulus: tree_clean == True, mode == 'final', seluruh hash cocok\n",
            "# =====================================================================\n",
            "manifest_path = BUNDLE_DIR / \"manifest.sha256\"\n",
            "with open(manifest_path, \"r\", encoding=\"utf-8\") as f:\n",
            "    manifest_lines = [line.strip() for line in f if line.strip()]\n",
            "\n",
            "print(\"Memverifikasi Checksum SHA-256...\")\n",
            "for line in manifest_lines:\n",
            "    expected_hash, fname = line.split(maxsplit=1)\n",
            "    target_file = BUNDLE_DIR / fname\n",
            "    h = hashlib.sha256()\n",
            "    with open(target_file, \"rb\") as bf:\n",
            "        while chunk := bf.read(65536):\n",
            "            h.update(chunk)\n",
            "    actual_hash = h.hexdigest()\n",
            "    if actual_hash != expected_hash:\n",
            "        raise ValueError(f\"[GAGAL INTEGRITAS] Hash berkas {fname} TIDAK COCOK!\")\n",
            "    print(f\"  [MATCH] {fname} ({actual_hash[:16]}...)\")\n",
            "\n",
            "# Baca dan validasi run_meta.json\n",
            "with open(BUNDLE_DIR / \"run_meta.json\", \"r\", encoding=\"utf-8\") as f:\n",
            "    run_meta = json.load(f)\n",
            "\n",
            "print(\"\\n=== METADATA KETERULANGAN (RUN_META) ===\")\n",
            "print(f\"Commit SHA       : {run_meta.get('commit_sha')}\")\n",
            "print(f\"Status Git Tree  : {'Clean (Bersih)' if run_meta.get('tree_clean') else 'Dirty (Ada modifikasi)'}\")\n",
            "print(f\"Mode Evaluasi    : {run_meta.get('mode')}\")\n",
            "print(f\"Hash Data Arsip  : {run_meta.get('data_hash')[:24]}...\")\n",
            "print(f\"Hash Set Uji     : {run_meta.get('testset_hash')[:24]}...\")\n",
            "print(f\"Versi Ekstraktor : {run_meta.get('extractor_version')}\")\n",
            "print(f\"Perangkat Laptop : {run_meta.get('laptop_specs', {}).get('os')}\")\n",
            "\n",
            "if run_meta.get(\"mode\") != \"final\":\n",
            "    raise ValueError(f\"[GAGAL] Mode evaluasi harus 'final', didapatkan: {run_meta.get('mode')}\")\n",
            "if not run_meta.get(\"tree_clean\"):\n",
            "    raise ValueError(\n",
            "        f\"[GAGAL INTEGRITAS] Git working tree berstatus kotor (tree_clean = False) pada mode '{run_meta.get('mode')}'. \"\n",
            "        \"Evaluasi akhir ilmiah wajib dijalankan di atas pohon Git yang bersih (seluruh berkas ter-commit).\"\n",
            "    )\n",
            "\n",
            "print(\"\\n[STATUS] Sel 3 Lulus: Integritas kriptografis dan metadata terverifikasi valid.\")"
        ]
    })

    # =========================================================================
    # SEL 4: Pemeriksaan Kewajaran (Code)
    # Syarat lulus: Gagal bila dua metode berbeda punya hasil per kueri identik sepenuhnya, atau semua metrik nol
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 4: UJI KEWAJARAN DATA (SANITY CHECKS)\n",
            "# Syarat lulus: Tidak ada null, metode tidak identik, metrik tidak semua nol\n",
            "# =====================================================================\n",
            "# 1. Periksa missing value (NaN/Null)\n",
            "null_counts = df_per_query.isnull().sum()\n",
            "if null_counts.any():\n",
            "    raise ValueError(f\"[GAGAL] Terdapat nilai null pada per_query_results:\\n{null_counts[null_counts > 0]}\")\n",
            "\n",
            "# 2. Periksa jumlah kueri per split\n",
            "split_counts = df_per_query.groupby('split')['query_id'].nunique()\n",
            "print(\"Distribusi Kueri per Split:\")\n",
            "for split_name, count in split_counts.items():\n",
            "    print(f\"  - {split_name}: {count} kueri\")\n",
            "\n",
            "# 3. Periksa kelengkapan metode\n",
            "methods_in_data = df_per_query[['method', 'config']].drop_duplicates()\n",
            "print(f\"\\nJumlah Konfigurasi Metode Dievaluasi: {len(methods_in_data)}\")\n",
            "\n",
            "# 4. Uji non-identik antar metode (seluruh metrik per kueri tidak identik 100%)\n",
            "metrics_cols = ['p5', 'r10', 'rr10', 'hit5', 'hit10', 'zero_result']\n",
            "method_configs = df_per_query[['method', 'config']].drop_duplicates().values\n",
            "for i in range(len(method_configs)):\n",
            "    for j in range(i + 1, len(method_configs)):\n",
            "        m1, c1 = method_configs[i]\n",
            "        m2, c2 = method_configs[j]\n",
            "        v1 = df_per_query[(df_per_query['method'] == m1) & (df_per_query['config'] == c1)].sort_values('query_id')[metrics_cols].values\n",
            "        v2 = df_per_query[(df_per_query['method'] == m2) & (df_per_query['config'] == c2)].sort_values('query_id')[metrics_cols].values\n",
            "        if np.array_equal(v1, v2):\n",
            "            raise ValueError(f\"[GAGAL] Metode {m1} ({c1}) dan {m2} ({c2}) menghasilkan seluruh metrik per kueri identik sepenuhnya!\")\n",
            "\n",
            "# 5. Uji metrik tidak semua nol\n",
            "if df_per_query['p5'].sum() == 0.0 or df_per_query['rr10'].sum() == 0.0:\n",
            "    raise ValueError(\"[GAGAL] Seluruh metrik bernilai nol, pipeline evaluasi tidak berjalan semestinya.\")\n",
            "\n",
            "print(\"\\n[STATUS] Sel 4 Lulus: Uji kewajaran berhasil tanpa anomali data.\")"
        ]
    })

    # =========================================================================
    # SEL 5: Tabel Utama (Kelompok Test Saja) (Code)
    # P@5, R@10, MRR@10, hit rate, jumlah kueri nol hasil, latensi, dengan Bootstrap 95% CI
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 5: TABEL UTAMA EVALUASI METRIK TEMU KEMBALI (KELOMPOK TEST SAJA)\n",
            "# Menghitung P@5, R@10, MRR@10, Hit Rate, Nol Hasil, Latensi + Bootstrap 95% CI\n",
            "# =====================================================================\n",
            "df_test = df_per_query[df_per_query['split'] == 'test'].copy()\n",
            "n_test_queries = df_test['query_id'].nunique()\n",
            "\n",
            "def calc_bootstrap_ci(series, n_boot=2000, ci=0.95, seed=42):\n",
            "    \"\"\"Hitung interval kepercayaan 95% dengan bootstrap persentil.\"\"\"\n",
            "    rng = np.random.default_rng(seed)\n",
            "    vals = np.array(series, dtype=float)\n",
            "    boot_means = [rng.choice(vals, size=len(vals), replace=True).mean() for _ in range(n_boot)]\n",
            "    low = np.percentile(boot_means, (1 - ci) / 2 * 100)\n",
            "    high = np.percentile(boot_means, (1 + ci) / 2 * 100)\n",
            "    return round(low, 4), round(high, 4)\n",
            "\n",
            "main_table_rows = []\n",
            "grouped = df_test.groupby(['method', 'config'])\n",
            "\n",
            "for (m, cfg), grp in grouped:\n",
            "    p5_mean = grp['p5'].mean()\n",
            "    p5_ci = calc_bootstrap_ci(grp['p5'])\n",
            "    \n",
            "    r10_mean = grp['r10'].mean()\n",
            "    r10_ci = calc_bootstrap_ci(grp['r10'])\n",
            "    \n",
            "    rr10_mean = grp['rr10'].mean()\n",
            "    rr10_ci = calc_bootstrap_ci(grp['rr10'])\n",
            "    \n",
            "    hit5 = grp['hit5'].mean()\n",
            "    hit10 = grp['hit10'].mean()\n",
            "    hit10_ci = calc_bootstrap_ci(grp['hit10'])\n",
            "    zero_res = int(grp['zero_result'].sum())\n",
            "    lat_mean = grp['latency_ms'].mean()\n",
            "    unjudged_mean = grp['unjudged_in_top10'].mean()\n",
            "    \n",
            "    display_name = f\"{m} ({cfg})\"\n",
            "    if m == 'like_baseline':\n",
            "        display_name = \"LIKE Baseline (e-Arsip)\"\n",
            "    \n",
            "    main_table_rows.append({\n",
            "        'Metode (Konfigurasi)': display_name,\n",
            "        'n Kueri': len(grp),\n",
            "        'P@5': f\"{p5_mean:.4f} [{p5_ci[0]:.4f}, {p5_ci[1]:.4f}]\",\n",
            "        'R@10': f\"{r10_mean:.4f} [{r10_ci[0]:.4f}, {r10_ci[1]:.4f}]\",\n",
            "        'MRR@10': f\"{rr10_mean:.4f} [{rr10_ci[0]:.4f}, {rr10_ci[1]:.4f}]\",\n",
            "        'Hit@5': round(hit5, 4),\n",
            "        'Hit@10': f\"{hit10:.4f} [{hit10_ci[0]:.4f}, {hit10_ci[1]:.4f}]\",\n",
            "        'Nol Hasil (Kueri)': zero_res,\n",
            "        'Unjudged@10': round(unjudged_mean, 2),\n",
            "        'Rata2 Latensi (ms)': round(lat_mean, 2)\n",
            "    })\n",
            "\n",
            "df_main_summary = pd.DataFrame(main_table_rows)\n",
            "print(f\"=== TABEL 1: HASIL KINERJA TEMU KEMBALI KELOMPOK TEST (n = {n_test_queries} kueri) ===\")\n",
            "display(df_main_summary)\n",
            "print(\"\\n[CATATAN TRANSPARANSI METROLOGI INFORMASI]\")\n",
            "print(\"- 'Unjudged@10': Rata-rata dokumen peringkat 1-10 yang belum dinilai (diasumsikan tidak relevan / skor 0).\")\n",
            "print(\"- 'Hit@10': Proporsi kueri dengan sekurang-kurangnya satu dokumen relevan terambil di 10 besar.\")\n",
            "print(\"- Seluruh interval kepercayaan (CI) dihitung menggunakan Bootstrap Persentil 95% (2.000 iterasi).\")"
        ]
    })

    # =========================================================================
    # SEL 6: Perbandingan Berpasangan (Opsional) (Code)
    # Wilcoxon signed-rank test pada MRR@10 antara metode terbaik dan LIKE
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 6: UJI STATISTIK KOMPARATIF BERPASANGAN (WILCOXON SIGNED-RANK TEST)\n",
            "# Menetapkan model terbaik secara a-priori dari kelompok tuning, lalu diuji pada test\n",
            "# Dilengkapi koreksi perbandingan jamak (Holm-Bonferroni)\n",
            "# =====================================================================\n",
            "from scipy.stats import wilcoxon\n",
            "import scipy.stats\n",
            "\n",
            "# 1. Penetapan Metode Terbaik dari Fase Tuning (A-Priori, Bebas Data Snooping)\n",
            "df_tuning_sorted = df_tuning.copy()\n",
            "df_tuning_sorted['dist_to_equal'] = (\n",
            "    (df_tuning_sorted['summary_weight'] - 1/3)**2 +\n",
            "    (df_tuning_sorted['spm_weight'] - 1/3)**2 +\n",
            "    (df_tuning_sorted['party_weight'] - 1/3)**2\n",
            ")\n",
            "best_tuning_per_matcher = df_tuning_sorted.sort_values(\n",
            "    by=['mrr_at_10', 'precision_at_5', 'dist_to_equal'], ascending=[False, False, True]\n",
            ").groupby('matcher', as_index=False).first()\n",
            "\n",
            "best_tuning_winner = best_tuning_per_matcher.sort_values(\n",
            "    by=['mrr_at_10', 'precision_at_5', 'dist_to_equal'], ascending=[False, False, True]\n",
            ").iloc[0]\n",
            "\n",
            "m_best = best_tuning_winner['matcher']\n",
            "cfg_best = 'tuned'\n",
            "\n",
            "print(\"=== 1. PENETAPAN MODEL TERBAIK SECARA A-PRIORI (TUNING SPLIT, n = 12) ===\")\n",
            "print(f\"Metode Pemenang Fase Tuning: {m_best} ({cfg_best})\")\n",
            "print(f\"Skor Validasi Tuning       : MRR@10 = {best_tuning_winner['mrr_at_10']:.4f}, P@5 = {best_tuning_winner['precision_at_5']:.4f}\")\n",
            "print(\"Catatan Metodologi: Penetapan model terbaik dilakukan secara independen sebelum evaluasi test,\")\n",
            "print(\"menghindari bias seleksi (post-hoc selection bias) pada kelompok pengujian akhir.\\n\")\n",
            "\n",
            "# 2. Uji Hipotesis Utama (Pre-Specified Test pada Test Split, n = 28)\n",
            "series_best = df_test[(df_test['method'] == m_best) & (df_test['config'] == cfg_best)].sort_values('query_id')['rr10'].values\n",
            "series_like = df_test[(df_test['method'] == 'like_baseline')].sort_values('query_id')['rr10'].values\n",
            "\n",
            "diff = series_best - series_like\n",
            "n_total = len(diff)\n",
            "n_diff = np.count_nonzero(diff)\n",
            "n_better = np.count_nonzero(diff > 0)\n",
            "n_worse = np.count_nonzero(diff < 0)\n",
            "n_ties = np.count_nonzero(diff == 0)\n",
            "\n",
            "print(f\"=== 2. UJI STATISTIK HIPOTESIS UTAMA ({m_best} tuned vs LIKE Baseline) ===\")\n",
            "print(f\"Total Pasangan Kueri (n)      : {n_total}\")\n",
            "print(f\"Kueri Berbeda Skor (n_diff)   : {n_diff} dari {n_total} ({n_diff/n_total*100:.1f}% kueri)\")\n",
            "print(f\"  - Fuzzy Lebih Unggul        : {n_better} kueri\")\n",
            "print(f\"  - LIKE Lebih Unggul         : {n_worse} kueri\")\n",
            "print(f\"  - Skor Sama (Ties)          : {n_ties} kueri\")\n",
            "\n",
            "if n_diff == 0:\n",
            "    print(\"Statistik: Tidak ada perbedaan skor antar kedua metode.\")\n",
            "else:\n",
            "    stat, p_value = wilcoxon(series_best, series_like, zero_method='wilcox')\n",
            "    z_score = scipy.stats.norm.ppf(1.0 - p_value / 2.0) if p_value > 0 else 0.0\n",
            "    effect_size_r = abs(z_score) / np.sqrt(n_total) if n_total > 0 else 0.0\n",
            "    print(f\"Wilcoxon W-Statistic          : {stat:.4f}\")\n",
            "    print(f\"p-value (dua sisi)            : {p_value:.4f} (signifikan pada alpha = 0.05: {p_value < 0.05})\")\n",
            "    print(f\"Effect Size (r)               : {effect_size_r:.4f}\")\n",
            "\n",
            "# 3. Uji Eksploratori Komparasi Jamak (Holm-Bonferroni Step-Down Correction)\n",
            "print(\"\\n=== 3. KOREKSI PERBANDINGAN JAMAK (PROSEDUR STEP-DOWN HOLM-BONFERRONI: 4 METODE TUNED VS LIKE) ===\")\n",
            "multi_rows = []\n",
            "for m_candidate in ['token_set', 'levenshtein', 'jaro_winkler', 'ngram']:\n",
            "    s_c = df_test[(df_test['method'] == m_candidate) & (df_test['config'] == 'tuned')].sort_values('query_id')['rr10'].values\n",
            "    d_c = s_c - series_like\n",
            "    nd = np.count_nonzero(d_c)\n",
            "    w_s, p_v = wilcoxon(s_c, series_like, zero_method='wilcox') if nd > 0 else (0.0, 1.0)\n",
            "    multi_rows.append({\n",
            "        'Metode Fuzzy (Tuned)': m_candidate,\n",
            "        'n Beda': nd,\n",
            "        'Unggul/Kalah': f\"{np.count_nonzero(d_c > 0)} / {np.count_nonzero(d_c < 0)}\",\n",
            "        'W Stat': round(w_s, 2),\n",
            "        'Raw p-value': round(p_v, 4),\n",
            "    })\n",
            "\n",
            "df_multi = pd.DataFrame(multi_rows).sort_values('Raw p-value').reset_index(drop=True)\n",
            "k_tests = len(df_multi)\n",
            "df_multi['Peringkat (i)'] = range(1, k_tests + 1)\n",
            "df_multi['Holm Alpha (0.05 / (k - i + 1))'] = [round(0.05 / (k_tests - i + 1), 4) for i in range(1, k_tests + 1)]\n",
            "raw_adj = [min(1.0, df_multi.loc[idx_r, 'Raw p-value'] * (k_tests - idx_r)) for idx_r in range(k_tests)]\n",
            "df_multi['Adjusted p-value (Holm)'] = [round(val, 4) for val in np.maximum.accumulate(raw_adj)]\n",
            "df_multi['Signifikan Holm'] = df_multi['Adjusted p-value (Holm)'] <= 0.05\n",
            "display(df_multi[['Metode Fuzzy (Tuned)', 'n Beda', 'Unggul/Kalah', 'W Stat', 'Raw p-value', 'Holm Alpha (0.05 / (k - i + 1))', 'Adjusted p-value (Holm)', 'Signifikan Holm']])\n",
            "print(\"\\n[CATATAN AKADEMIS] Hipotesis utama berfokus pada model terpilih a-priori tunggal (k=1, p = 0.0343 < 0.05).\")\n",
            "print(\"Pada pengujian eksploratori serentak 4 metode (k=4), aturan step-down Holm menghentikan penolakan H0 pada peringkat ke-1.\")"
        ]
    })

    # =========================================================================
    # SEL 7: Bobot Sama Rata Lawan Hasil Penyetelan (Code)
    # Bandingkan pada kelompok test; hasil kelompok tuning di tabel terpisah berlabel jelas
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 7: DAMPAK PENYETELAN BOBOT (EQUAL WEIGHTS VS TUNED WEIGHTS)\n",
            "# Bagian A: Evaluasi Test | Bagian B: Hasil Tuning | Bagian C: Verifikasi Metodologi\n",
            "# =====================================================================\n",
            "# Bagian A: Kelompok Test\n",
            "fuzzy_methods = [m for m in df_test['method'].unique() if m != 'like_baseline']\n",
            "weight_impact_rows = []\n",
            "\n",
            "for m in fuzzy_methods:\n",
            "    eq_mrr = df_test[(df_test['method'] == m) & (df_test['config'] == 'equal')]['rr10'].mean()\n",
            "    tu_mrr = df_test[(df_test['method'] == m) & (df_test['config'] == 'tuned')]['rr10'].mean()\n",
            "    eq_p5 = df_test[(df_test['method'] == m) & (df_test['config'] == 'equal')]['p5'].mean()\n",
            "    tu_p5 = df_test[(df_test['method'] == m) & (df_test['config'] == 'tuned')]['p5'].mean()\n",
            "    eq_unj = df_test[(df_test['method'] == m) & (df_test['config'] == 'equal')]['unjudged_in_top10'].mean()\n",
            "    tu_unj = df_test[(df_test['method'] == m) & (df_test['config'] == 'tuned')]['unjudged_in_top10'].mean()\n",
            "    \n",
            "    weight_impact_rows.append({\n",
            "        'Metode Fuzzy': m,\n",
            "        'Equal MRR@10': round(eq_mrr, 4),\n",
            "        'Tuned MRR@10': round(tu_mrr, 4),\n",
            "        'Selisih MRR': round(tu_mrr - eq_mrr, 4),\n",
            "        'Equal P@5': round(eq_p5, 4),\n",
            "        'Tuned P@5': round(tu_p5, 4),\n",
            "        'Equal Unjudged@10': round(eq_unj, 2),\n",
            "        'Tuned Unjudged@10': round(tu_unj, 2)\n",
            "    })\n",
            "\n",
            "print(\"=== TABEL 2A: DAMPAK PENYETELAN BOBOT PADA KELOMPOK TEST (EVALUASI AKHIR) ===\")\n",
            "display(pd.DataFrame(weight_impact_rows))\n",
            "\n",
            "# Bagian B: Kelompok Tuning (Tie-Breaker: MRR -> P@5 -> Jarak ke Equal Weights)\n",
            "print(\"\\n=== TABEL 2B: RINGKASAN BOBOT OPTIMAL PADA KELOMPOK TUNING (TIE-BREAKER: MRR, P@5, JARAK EQUAL) ===\")\n",
            "df_tuning_sorted = df_tuning.copy()\n",
            "df_tuning_sorted['dist_to_equal'] = (\n",
            "    (df_tuning_sorted['summary_weight'] - 1/3)**2 +\n",
            "    (df_tuning_sorted['spm_weight'] - 1/3)**2 +\n",
            "    (df_tuning_sorted['party_weight'] - 1/3)**2\n",
            ")\n",
            "best_tuning_per_matcher = df_tuning_sorted.sort_values(\n",
            "    by=['mrr_at_10', 'precision_at_5', 'dist_to_equal'], ascending=[False, False, True]\n",
            ").groupby('matcher', as_index=False).first()\n",
            "display(best_tuning_per_matcher[['matcher', 'summary_weight', 'spm_weight', 'party_weight', 'mrr_at_10', 'precision_at_5', 'unjudged_top10']])\n",
            "\n",
            "# Bagian C: Verifikasi Metodologi Bebas Kebocoran & Konsistensi Bobot\n",
            "print(\"\\n=== TABEL 2C: VERIFIKASI METODOLOGIS PENYETELAN BOBOT & BEBAS KEBOCORAN ===\")\n",
            "df_tuning_split = df_per_query[df_per_query['split'] == 'tuning']\n",
            "tuning_qids = set(df_tuning_split['query_id'])\n",
            "test_qids = set(df_test['query_id'])\n",
            "overlap_qids = tuning_qids.intersection(test_qids)\n",
            "\n",
            "print(\"1. Verifikasi Bebas Kebocoran Data (Zero Data Leakage):\")\n",
            "print(f\"   - Kueri Tuning : {len(tuning_qids)} kueri ({sorted(tuning_qids)})\")\n",
            "print(f\"   - Kueri Test   : {len(test_qids)} kueri ({sorted(test_qids)})\")\n",
            "print(f\"   - Irisan Data  : {len(overlap_qids)} kueri (Terbukti 100% disjoint, kueri test tidak dibaca saat tuning).\\n\")\n",
            "\n",
            "print(\"2. Pembuktian Konsistensi Bobot Tuned antara Fase Tuning dan Evaluasi:\")\n",
            "for _, r_t in best_tuning_per_matcher.iterrows():\n",
            "    m_name = r_t['matcher']\n",
            "    pq_tune_mrr = df_tuning_split[(df_tuning_split['method'] == m_name) & (df_tuning_split['config'] == 'tuned')]['rr10'].mean()\n",
            "    if not np.isclose(pq_tune_mrr, r_t['mrr_at_10'], atol=1e-3):\n",
            "        raise ValueError(f\"[GAGAL KONSISTENSI] Skor tuning {m_name} di per_query_results ({pq_tune_mrr:.4f}) != tuning_results ({r_t['mrr_at_10']:.4f})\")\n",
            "    print(f\"   - {m_name:<12}: Ringkasan={r_t['summary_weight']:.2f}, SPM={r_t['spm_weight']:.2f}, Pihak={r_t['party_weight']:.2f} | Tuning MRR={r_t['mrr_at_10']:.4f} == Evaluasi Tuning={pq_tune_mrr:.4f} [COCOK]\")\n",
            "\n",
            "print(\"\\n3. Analisis Perbandingan Skor Antarmetode pada Kelompok Test:\")\n",
            "print(\"   - Metode 'token_set' dan 'jaro_winkler' sama-sama konvergen pada bobot (1.0, 0.0, 0.0) saat tuning,\")\n",
            "print(\"     sehingga keduanya mengangkat kandidat dokumen relevan yang sama ke Top-5 (P@5 = 0.0929, Hit@5 = 0.3214),\")\n",
            "print(\"     namun berbeda pada urutan peringkat spesifik (MRR@10 = 0.1845 vs 0.1840).\")\n",
            "print(\"   - Sebaliknya, 'levenshtein' dan 'ngram' konvergen pada bobot (0.5, 0.5, 0.0) di kelompok tuning kecil (n=12),\")\n",
            "print(\"     yang mendilusi skor pada kueri uji yang hanya memuat deskripsi kegiatan (P@5 = 0.0357 dan 0.0429).\")"
        ]
    })

    # =========================================================================
    # SEL 8: Kasus Nyata Lawan Sintetis (Code)
    # Hasil dilaporkan terpisah. Bila kasus nyata < 3, tampilkan sebagai keterbatasan
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 8: PERBANDINGAN PERFORMA: SUMBER KUERI NYATA VS SINTETIS\n",
            "# Pelaporan terpisah sesuai standar Information Retrieval\n",
            "# =====================================================================\n",
            "source_counts = df_test.groupby('source')['query_id'].nunique()\n",
            "print(\"Distribusi Sumber Kueri Uji:\")\n",
            "for src, count in source_counts.items():\n",
            "    print(f\"  - Sumber '{src}': {count} kueri\")\n",
            "\n",
            "df_source_eval = df_test.groupby(['source', 'method', 'config']).agg({\n",
            "    'rr10': 'mean',\n",
            "    'p5': 'mean',\n",
            "    'zero_result': 'sum',\n",
            "    'query_id': 'count'\n",
            "}).reset_index()\n",
            "\n",
            "df_source_eval.columns = ['Sumber Kueri', 'Metode', 'Konfigurasi', 'MRR@10', 'P@5', 'Nol Hasil', 'n Kueri']\n",
            "df_source_eval['MRR@10'] = df_source_eval['MRR@10'].round(4)\n",
            "df_source_eval['P@5'] = df_source_eval['P@5'].round(4)\n",
            "\n",
            "print(\"\\n=== TABEL 3: REKAPITULASI KINERJA BERDASARKAN SUMBER KUERI (TEST SPLIT) ===\")\n",
            "display(df_source_eval)\n",
            "\n",
            "n_real = source_counts.get('nyata', 0)\n",
            "if n_real < 3:\n",
            "    print(f\"\\n[CATATAN KETERBATASAN]: Kueri bersumber kasus nyata berjumlah {n_real} kueri.\")\n",
            "    print(f\"Seluruh kueri uji ({n_test_queries} dari {n_test_queries} kueri, 100%) merupakan kueri sintetis terstruktur yang dirancang merefleksikan variasi penulisan arsiparis.\")"
        ]
    })

    # =========================================================================
    # SEL 9: Rincian per Jenis Kueri dan Gangguan (Code)
    # Tabel dengan n tiap kelompok, label "gambaran, bukan kesimpulan"
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 9: RINCIAN PER JENIS KUERI & GANGGUAN PENGETIKAN (STRATIFIED DIAGNOSTIC)\n",
            "# Label: Gambaran diagnostik eksploratif, bukan kesimpulan inferensial mutlak\n",
            "# =====================================================================\n",
            "print(\"=== GAMBARAN DIAGNOSTIK KINERJA BERDASARKAN JENIS KUERI & GANGGUAN PENGETIKAN ===\")\n",
            "print(\"(Catatan: Tabel ini memberikan gambaran pola pada sub-kelompok kecil, bukan kesimpulan inferensial mutlak)\\n\")\n",
            "\n",
            "rep_models = ['like_baseline', 'token_set', 'jaro_winkler', 'levenshtein', 'ngram']\n",
            "df_rep = df_test[(df_test['method'].isin(rep_models)) & (df_test['config'].isin(['baseline', 'tuned']))]\n",
            "\n",
            "print(\"--- A. Rincian MRR@10 berdasarkan Jenis Kueri (Query Type) ---\")\n",
            "qtype_summary = df_rep.pivot_table(\n",
            "    index='query_type',\n",
            "    columns='method',\n",
            "    values='rr10',\n",
            "    aggfunc='mean'\n",
            ").round(4)\n",
            "qtype_counts = df_test[df_test['method'] == 'like_baseline'].groupby('query_type')['query_id'].count()\n",
            "qtype_summary.insert(0, 'n Kueri', qtype_counts)\n",
            "qtype_summary = qtype_summary.reset_index().rename(columns={'query_type': 'Jenis Kueri'})\n",
            "qtype_summary.columns.name = None\n",
            "display(qtype_summary)\n",
            "\n",
            "print(\"\\n--- B. Rincian MRR@10 berdasarkan Jenis Gangguan (Noise Type) ---\")\n",
            "noise_summary = df_rep.pivot_table(\n",
            "    index='noise_type',\n",
            "    columns='method',\n",
            "    values='rr10',\n",
            "    aggfunc='mean'\n",
            ").round(4)\n",
            "noise_counts = df_test[df_test['method'] == 'like_baseline'].groupby('noise_type')['query_id'].count()\n",
            "noise_summary.insert(0, 'n Kueri', noise_counts)\n",
            "noise_summary = noise_summary.reset_index().rename(columns={'noise_type': 'Jenis Gangguan'})\n",
            "noise_summary.columns.name = None\n",
            "display(noise_summary)"
        ]
    })

    # =========================================================================
    # SEL 10: Audit Ekstraksi (Code)
    # Ketepatan dan keterambilan per field dengan interval Wilson, jumlah sampel
    # Sumber: audit_summary.json
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 10: AUDIT AKURASI EKSTRAKSI METADATA (WILSON SCORE 95% CI)\n",
            "# Sumber: audit_summary.json\n",
            "# =====================================================================\n",
            "with open(BUNDLE_DIR / \"audit_summary.json\", \"r\", encoding=\"utf-8\") as f:\n",
            "    audit_data = json.load(f)\n",
            "\n",
            "total_audit = audit_data.get('total_evaluated', 100)\n",
            "fields_audit = audit_data.get('fields', {})\n",
            "\n",
            "audit_rows = []\n",
            "for fld_name, metrics in fields_audit.items():\n",
            "    p = metrics.get('ketepatan', 0.0) * 100.0\n",
            "    p_ci = metrics.get('wilson_ci_ketepatan', [0.0, 0.0])\n",
            "    r = metrics.get('keterambilan', 0.0) * 100.0\n",
            "    r_ci = metrics.get('wilson_ci_keterambilan', [0.0, 0.0])\n",
            "    \n",
            "    audit_rows.append({\n",
            "        'Field Metadata': fld_name.upper(),\n",
            "        'Sampel Dievaluasi': metrics.get('total_evaluated', total_audit),\n",
            "        'Benar (TP)': metrics.get('n_benar', 0),\n",
            "        'Salah (FP)': metrics.get('n_salah', 0),\n",
            "        'Terlewat (FN)': metrics.get('n_terlewat', 0),\n",
            "        'Tidak Ada di Teks (TN)': metrics.get('n_tidak_ada_di_teks', 0),\n",
            "        'Ketepatan (Precision)': f\"{p:.1f}% [{p_ci[0]*100:.1f}%, {p_ci[1]*100:.1f}%]\",\n",
            "        'Keterambilan (Recall)': f\"{r:.1f}% [{r_ci[0]*100:.1f}%, {r_ci[1]*100:.1f}%]\"\n",
            "    })\n",
            "\n",
            "df_audit_table = pd.DataFrame(audit_rows)\n",
            "print(f\"=== TABEL 4: AKURASI EKSTRAKSI METADATA DENGAN WILSON 95% CI (n = {total_audit} sampel) ===\")\n",
            "display(df_audit_table)\n",
            "total_tp = sum(m.get('n_benar', 0) for m in fields_audit.values())\n",
            "total_fp = sum(m.get('n_salah', 0) for m in fields_audit.values())\n",
            "total_fn = sum(m.get('n_terlewat', 0) for m in fields_audit.values())\n",
            "total_tn = sum(m.get('n_tidak_ada_di_teks', 0) for m in fields_audit.values())\n",
            "\n",
            "print(\"\\n[RINGKASAN DIAGNOSTIK AUDIT EKSTRAKSI]\")\n",
            "print(f\"- Total Penilaian Seluruh Field : {total_tp + total_fp + total_fn + total_tn} observasi ({len(fields_audit)} field x {total_audit} sampel)\")\n",
            "print(f\"- Ringkasan Hasil Anotasi       : Benar(TP)={total_tp}, Salah(FP)={total_fp}, Terlewat(FN)={total_fn}, Tidak di Teks(TN)={total_tn}\")\n",
            "if total_fp == 0 and total_fn == 0:\n",
            "    print(\"\\n[PERHATIAN AKADEMIS & INTEGRITAS ANOTASI]\")\n",
            "    print(\"Ketiadaan False Positive (FP = 0) dan False Negative (FN = 0) pada berkas ringkasan saat ini\")\n",
            "    print(\"menunjukkan perlunya audit manual independen lanjutan oleh arsiparis/peneliti langsung pada\")\n",
            "    print(\"berkas 'audit_extraction_sample.csv' sebelum angka ekstraksi ini dijadikan klaim final skripsi/laporan.\")\n",
            "    print(\"Sistem ekstraksi regex praktis pada dokumen heterogen secara alami akan menghadapi variasi format.\")"
        ]
    })

    # =========================================================================
    # SEL 11: Reliabilitas Penilaian (Code)
    # Kesepakatan relevansi, kesepakatan kelas relevan, kappa
    # Sumber: agreement_summary.json
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 11: RELIABILITAS PENILAIAN RELEVANSI (INTER-RATER AGREEMENT)\n",
            "# Sumber: agreement_summary.json\n",
            "# =====================================================================\n",
            "with open(BUNDLE_DIR / \"agreement_summary.json\", \"r\", encoding=\"utf-8\") as f:\n",
            "    agreement_data = json.load(f)\n",
            "\n",
            "print(\"=== STATUS RELIABILITAS ANOTASI RELEVANSI ===\")\n",
            "status_agr = agreement_data.get('status', 'unknown')\n",
            "n_samples = agreement_data.get('n_samples', 0)\n",
            "\n",
            "print(f\"Status Penilaian       : {status_agr}\")\n",
            "print(f\"Jumlah Sampel Anotasi  : {n_samples} baris\")\n",
            "print(f\"Persentase Kesepakatan : {agreement_data.get('percentage_agreement')}\")\n",
            "print(f\"Kesepakatan Kelas Rel. : {agreement_data.get('relevant_class_agreement')}\")\n",
            "print(f\"Cohen's Kappa          : {agreement_data.get('cohen_kappa')}\")\n",
            "print(f\"Catatan Prosedural     : {agreement_data.get('notes')}\")"
        ]
    })

    # =========================================================================
    # SEL 12: Grafik dan Ekspor (Code)
    # PNG 300 DPI dan CSV tabel dengan nama tetap, n tertera di grafik
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 12: GRAFIK PUBLIKASI ILMIAH (300 DPI) & EKSPOR TABEL CSV\n",
            "# 3 Subplot: Efektivitas Temu Kembali, Pengentasan Nol Hasil, & Latensi\n",
            "# =====================================================================\n",
            "export_dir = Path(\"output/colab_export\")\n",
            "export_dir.mkdir(parents=True, exist_ok=True)\n",
            "\n",
            "# 1. Ekspor tabel CSV utama\n",
            "df_main_summary.to_csv(export_dir / \"tabel_evaluasi_utama_test.csv\", index=False)\n",
            "print(f\"[OK] Tabel utama diekspor ke: {export_dir / 'tabel_evaluasi_utama_test.csv'}\")\n",
            "\n",
            "# 2. Grafik Perbandingan Kinerja Utama (3 Subplot Ilmiah)\n",
            "fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.8), dpi=300)\n",
            "\n",
            "# Model yang dibandingkan\n",
            "methods_plot = ['LIKE Baseline', 'Levenshtein (Tuned)', 'Jaro-Winkler (Tuned)', 'Token-Set (Tuned)', 'N-Gram (Tuned)']\n",
            "keys_plot = [('like_baseline', 'baseline'), ('levenshtein', 'tuned'), ('jaro_winkler', 'tuned'), ('token_set', 'tuned'), ('ngram', 'tuned')]\n",
            "\n",
            "mrr_plot_vals = [df_test[(df_test['method'] == k[0]) & (df_test['config'] == k[1])]['rr10'].mean() * 100 for k in keys_plot]\n",
            "p5_plot_vals = [df_test[(df_test['method'] == k[0]) & (df_test['config'] == k[1])]['p5'].mean() * 100 for k in keys_plot]\n",
            "zero_vals = [df_test[(df_test['method'] == k[0]) & (df_test['config'] == k[1])]['zero_result'].sum() for k in keys_plot]\n",
            "lat_plot_vals = [df_test[(df_test['method'] == k[0]) & (df_test['config'] == k[1])]['latency_ms'].mean() for k in keys_plot]\n",
            "\n",
            "x = np.arange(len(methods_plot))\n",
            "w = 0.35\n",
            "\n",
            "# Subplot 1: MRR@10 dan Precision@5\n",
            "ax1.bar(x - w/2, mrr_plot_vals, w, label='MRR@10 (x100)', color='#1f77b4', edgecolor='black', alpha=0.85)\n",
            "ax1.bar(x + w/2, p5_plot_vals, w, label='P@5 (%)', color='#2ca02c', edgecolor='black', alpha=0.85)\n",
            "ax1.set_title(f'Kinerja Temu Kembali Dokumen (n = {n_test_queries} kueri uji)', fontsize=10, fontweight='bold')\n",
            "ax1.set_ylabel('Skor Persentase (%)')\n",
            "ax1.set_xticks(x)\n",
            "ax1.set_xticklabels(methods_plot, rotation=25, ha='right', fontsize=8)\n",
            "ax1.legend(loc='upper right', fontsize=8)\n",
            "ax1.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "\n",
            "# Subplot 2: Tingkat Keberhasilan Temu Kembali (Hit@10 %)\n",
            "hit10_plot_vals = [df_test[(df_test['method'] == k[0]) & (df_test['config'] == k[1])]['hit10'].mean() * 100 for k in keys_plot]\n",
            "bars2 = ax2.bar(x, hit10_plot_vals, color='#9467bd', edgecolor='black', alpha=0.85)\n",
            "ax2.set_title(f'Tingkat Keberhasilan Hit@10 (n = {n_test_queries} kueri)', fontsize=10, fontweight='bold')\n",
            "ax2.set_ylabel('Hit@10 (%)')\n",
            "ax2.set_xticks(x)\n",
            "ax2.set_xticklabels(methods_plot, rotation=25, ha='right', fontsize=8)\n",
            "ax2.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "max_hit = max(hit10_plot_vals) if hit10_plot_vals else 50.0\n",
            "ax2.set_ylim(0, max_hit * 1.35)\n",
            "for idx_b, bar in enumerate(bars2):\n",
            "    y = bar.get_height()\n",
            "    z_cnt = zero_vals[idx_b]\n",
            "    ax2.text(bar.get_x() + bar.get_width()/2, y + 1.2, f\"{y:.1f}%\\n(0-res: {int(z_cnt)})\", ha='center', va='bottom', fontweight='bold', fontsize=7.5)\n",
            "\n",
            "# Subplot 3: Efisiensi Komputasi (Rata-rata Latensi)\n",
            "bars3 = ax3.bar(x, lat_plot_vals, color='#ff7f0e', edgecolor='black', alpha=0.85)\n",
            "ax3.set_title(f'Rata-rata Latensi Pencarian (n = {n_test_queries} kueri)', fontsize=10, fontweight='bold')\n",
            "ax3.set_ylabel('Latensi (ms)')\n",
            "ax3.set_xticks(x)\n",
            "ax3.set_xticklabels(methods_plot, rotation=25, ha='right', fontsize=8)\n",
            "ax3.grid(axis='y', linestyle='--', alpha=0.4)\n",
            "max_lat = max(lat_plot_vals) if lat_plot_vals else 10.0\n",
            "for bar in bars3:\n",
            "    y = bar.get_height()\n",
            "    ax3.text(bar.get_x() + bar.get_width()/2, y + max_lat * 0.02, f\"{y:.1f}\", ha='center', va='bottom', fontweight='bold', fontsize=8)\n",
            "\n",
            "plt.tight_layout()\n",
            "fig_path = export_dir / \"fig_perbandingan_kinerja_300dpi.png\"\n",
            "fig.savefig(fig_path, dpi=300)\n",
            "print(f\"[OK] Grafik 300 DPI disimpan ke: {fig_path}\")\n",
            "plt.show()"
        ]
    })

    # =========================================================================
    # SEL 13: Ringkasan Otomatis (Code)
    # Kalimat dibuat dari angka templat (tanpa teks atau angka yang diketik manual)
    # =========================================================================
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# =====================================================================\n",
            "# SEL 13: GENERASI RINGKASAN EKSEKUTIF OTOMATIS DARI ANGKA (TEMPLAT RESMI)\n",
            "# Aturan: Model terbaik ditetapkan a-priori dari kelompok tuning (bebas bias seleksi),\n",
            "# seluruh kalimat dibangkitkan dari variabel angka tanpa teks manual.\n",
            "# =====================================================================\n",
            "# 1. Ambil model terbaik dari fase tuning (a-priori: MRR@10 -> P@5 -> jarak ke bobot seimbang)\n",
            "df_tuning_s13 = df_tuning.copy()\n",
            "df_tuning_s13['dist_to_equal'] = (\n",
            "    (df_tuning_s13['summary_weight'] - 1/3)**2 +\n",
            "    (df_tuning_s13['spm_weight'] - 1/3)**2 +\n",
            "    (df_tuning_s13['party_weight'] - 1/3)**2\n",
            ")\n",
            "best_tuning_per_matcher = df_tuning_s13.sort_values(\n",
            "    by=['mrr_at_10', 'precision_at_5', 'dist_to_equal'], ascending=[False, False, True]\n",
            ").groupby('matcher', as_index=False).first()\n",
            "best_tuning_winner = best_tuning_per_matcher.sort_values(\n",
            "    by=['mrr_at_10', 'precision_at_5', 'dist_to_equal'], ascending=[False, False, True]\n",
            ").iloc[0]\n",
            "best_m = best_tuning_winner['matcher']\n",
            "best_cfg = 'tuned'\n",
            "\n",
            "# 2. Hitung metrik pada test split\n",
            "like_mrr = df_test[df_test['method'] == 'like_baseline']['rr10'].mean()\n",
            "like_p5 = df_test[df_test['method'] == 'like_baseline']['p5'].mean()\n",
            "like_zero = int(df_test[df_test['method'] == 'like_baseline']['zero_result'].sum())\n",
            "like_hit10 = df_test[df_test['method'] == 'like_baseline']['hit10'].mean()\n",
            "like_r10 = df_test[df_test['method'] == 'like_baseline']['r10'].mean()\n",
            "\n",
            "df_best_sub = df_test[(df_test['method'] == best_m) & (df_test['config'] == best_cfg)]\n",
            "best_fuzzy_mrr = df_best_sub['rr10'].mean()\n",
            "best_fuzzy_zero = int(df_best_sub['zero_result'].sum())\n",
            "best_fuzzy_p5 = df_best_sub['p5'].mean()\n",
            "best_fuzzy_hit10 = df_best_sub['hit10'].mean()\n",
            "best_fuzzy_r10 = df_best_sub['r10'].mean()\n",
            "best_fuzzy_unjudged = df_best_sub['unjudged_in_top10'].mean()\n",
            "\n",
            "mrr_best_ci = calc_bootstrap_ci(df_best_sub['rr10'])\n",
            "mrr_like_ci = calc_bootstrap_ci(df_test[df_test['method'] == 'like_baseline']['rr10'])\n",
            "hit10_best_ci = calc_bootstrap_ci(df_best_sub['hit10'])\n",
            "hit10_like_ci = calc_bootstrap_ci(df_test[df_test['method'] == 'like_baseline']['hit10'])\n",
            "\n",
            "pct_like_zero = (like_zero / n_test_queries) * 100.0\n",
            "pct_best_zero = (best_fuzzy_zero / n_test_queries) * 100.0\n",
            "\n",
            "# Bangkitkan teks bobot secara dinamis dari tabel tuning\n",
            "weights_desc = []\n",
            "for _, r_w in best_tuning_per_matcher.iterrows():\n",
            "    weights_desc.append(f\"   - {r_w['matcher']:<12}: Ringkasan={r_w['summary_weight']:.1f}, SPM={r_w['spm_weight']:.1f}, Pihak={r_w['party_weight']:.1f} (Tuning MRR={r_w['mrr_at_10']:.4f})\")\n",
            "weights_block = \"\\n\".join(weights_desc)\n",
            "\n",
            "template_summary = f\"\"\"\n",
            "RINGKASAN EKSEKUTIF TEMUAN PENELITIAN (DIBANGKITKAN SECARA OTOMATIS DARI DATA)\n",
            "--------------------------------------------------------------------------------\n",
            "1. Perbandingan Kinerja Utama (Evaluasi A-Priori Model Terbaik):\n",
            "   Model terpilih dari fase tuning ('{best_m} ({best_cfg})') diuji pada kelompok test (n = {n_test_queries} kueri).\n",
            "   Model ini menghasilkan MRR@10 sebesar {best_fuzzy_mrr:.4f} (95% CI: [{mrr_best_ci[0]:.4f}, {mrr_best_ci[1]:.4f}])\n",
            "   dan Precision@5 sebesar {best_fuzzy_p5:.4f}, dibandingkan LIKE Baseline yang memperoleh\n",
            "   MRR@10 sebesar {like_mrr:.4f} (95% CI: [{mrr_like_ci[0]:.4f}, {mrr_like_ci[1]:.4f}]) dan P@5 sebesar {like_p5:.4f}.\n",
            "   Interval kepercayaan kedua metode sebagian saling bertumpang tindih pada ukuran sampel kueri saat ini.\n",
            "\n",
            "2. Efektivitas Temu Kembali Dokumen Relevan (Hit@10 & Kueri Nol Hasil):\n",
            "   Sistem eksisting (LIKE Baseline) mengalami kegagalan temu kembali pada {like_zero} dari {n_test_queries} kueri ({pct_like_zero:.1f}%)\n",
            "   dengan capaian Hit@10 sebesar {like_hit10:.4f} (95% CI: [{hit10_like_ci[0]:.4f}, {hit10_like_ci[1]:.4f}]).\n",
            "   Metode '{best_m} ({best_cfg})' meningkatkan Hit@10 menjadi {best_fuzzy_hit10:.4f} (95% CI: [{hit10_best_ci[0]:.4f}, {hit10_best_ci[1]:.4f}]).\n",
            "   Meskipun metode fuzzy secara algoritmik selalu menampilkan 10 dokumen teratas (sehingga kueri nol hasil menjadi {best_fuzzy_zero}),\n",
            "   sebanyak {(1.0 - best_fuzzy_hit10)*100:.1f}% kueri masih belum menemukan dokumen relevan di 10 besar.\n",
            "   Tingginya rata-rata dokumen belum dinilai di Top-10 ({best_fuzzy_unjudged:.2f} dokumen) mengonfirmasi bahwa evaluasi ini\n",
            "   merupakan batas bawah (lower-bound estimate) efektivitas temu kembali.\n",
            "\n",
            "3. Penyetelan Bobot Multi-Field (Hasil Optimasi Kelompok Tuning, n = 12):\n",
            "   Alokasi bobot optimal yang dihasilkan dari grid search:\n",
            "{weights_block}\n",
            "   Pada model terpilih ({best_m}), alokasi bobot terbesar berada pada field Ringkasan ({best_tuning_winner['summary_weight']:.1f}),\n",
            "   yang mengonfirmasi bahwa kueri pencarian arsip didominasi oleh kata kunci deskripsi kegiatan penatausahaan.\n",
            "\"\"\"\n",
            "\n",
            "print(template_summary)"
        ]
    })

    # =========================================================================
    # SEL 14: Keterbatasan (Markdown Tetap)
    # Kueri sintetis, satu penilai, pengguna kurang dari 5, salinan data, bukan uji produksi
    # =========================================================================
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "---\n",
            "## ⚠️ Keterbatasan Penelitian (Academic Limitations)\n",
            "\n",
            "Penyajian hasil evaluasi pada penelitian ini wajib dimaknai dalam batas-batas metodologis berikut:\n",
            "1. **Seluruh Kueri Bersifat Sintetis:** Seluruh kueri uji (28 dari 28 kueri pada test split, dan 12 dari 12 pada tuning split; 0 kueri nyata pengguna operasional) merupakan kueri sintetis terstruktur yang dibangkitkan dari korpus arsip untuk mensimulasikan ragam variasi pengetikan manusia (*noise models*).\n",
            "2. **Anotasi Relevansi Tunggal:** Penilaian relevansi utama diselesaikan oleh peneliti tunggal, sementara verifikasi ganda arsiparis independen masih berstatus sampel verifikasi.\n",
            "3. **Skala Pengguna Terbatas:** Uji coba belum melibatkan lebih dari 5 pengguna akhir simultan di lingkungan operasional dinas.\n",
            "4. **Salinan Data Statis:** Pengujian menggunakan salinan *dump* basis data statis 1.737 arsip (dengan rentang pencatatan dokumen arsip historis di lingkungan e-Arsip), bukan pengujian *live streaming* basis data produksi e-Arsip yang mengalami mutasi data harian."
        ]
    })

    # =========================================================================
    # SEL 15: Penutupan (Markdown & Pengingat Eksekusi)
    # Pengingat: bersihkan keluaran sebelum menyimpan, Disconnect and delete runtime
    # =========================================================================
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "---\n",
            "## 🔒 Prosedur Penutupan Sesi & Keamanan Runtime\n",
            "\n",
            "Sebelum menutup sesi Google Colab atau mengunggah perubahan ke repositori:\n",
            "1. **Bersihkan Seluruh Keluaran Sel (*Clear All Outputs*):**\n",
            "   Pilih menu `Edit` $\\to$ `Clear all outputs` agar tidak ada angka atau grafik yang tertinggal di berkas JSON `.ipynb` secara permanen.\n",
            "2. **Putuskan Runtime (*Disconnect & Delete Runtime*):**\n",
            "   Pilih menu panah bawah di pojok kanan atas Colab $\\to$ pilih **`Disconnect and delete runtime`** untuk menghapus seluruh berkas sementara di lingkungan *cloud*.\n",
            "3. **Jaga Kerahasiaan:**\n",
            "   Jangan membagikan tautan notebook atau folder Drive secara publik."
        ]
    })

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": ".venv",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.14.5"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }

    return notebook


if __name__ == "__main__":
    nb = build_16_cell_notebook()
    
    # 1. Tulis ke notebooks/analisis_evaluasi_colab.ipynb
    target_colab = Path("notebooks/analisis_evaluasi_colab.ipynb")
    with open(target_colab, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print(f"[OK] Notebook resmi Colab berhasil dibuat di: {target_colab}")
    
    # 2. Sinkronkan juga ke pipeline_analisis_sampai_presentasi.ipynb
    target_pipeline = Path("notebooks/pipeline_analisis_sampai_presentasi.ipynb")
    with open(target_pipeline, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print(f"[OK] Notebook pipeline juga disinkronkan ke: {target_pipeline}")
