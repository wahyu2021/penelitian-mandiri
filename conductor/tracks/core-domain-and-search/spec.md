# Track Specification: Core Domain Logic & Multi-Method Search

## 1. Ringkasan & Tujuan
Track ini bertujuan membangun seluruh fondasi domain logika bisnis (`core/`) untuk sistem pencarian arsip e-Arsip (SIMANIS). Seluruh modul pada track ini ditulis dalam **Python 3.14 murni tanpa ketergantungan pada Flask maupun SQLAlchemy**, menjamin portabilitas, kecepatan komputasi, dan kemudahan pengujian independen melalui `pytest`.

Pengembangan dilakukan secara bertahap (staged execution) di mana setiap tahap wajib menyelesaikan implementasi dan memastikan **semua uji lulus** sebelum melangkah ke tahap selanjutnya.

---

## 2. Kebutuhan Fungsional & Tahapan Pengerjaan

### Tahap 1: Parser SQL Dump, Pembersihan Data, Normalisasi, & Ekstraksi Metadata
1. **Parser SQL Dump Aman (`core/sql_dump_parser.py`):**
   - Hanya membaca tabel target: `apptb_arsip`, `apptb_opd`, dan `apptb_klasifikasi`.
   - **Tegas mengecualikan dan mengabaikan:** `apptb_user`, `apptb_log`, dan tabel uji sementara `apptb_arsip1`.
   - Menghitung hash SHA-256 berkas input untuk penjaminan integritas data eksperimen.
2. **Pembersihan & Audit Anomali Data (`core/cleaning.py`):**
   - Menangani format tanggal tidak valid (`0000-00-00`), tahun di luar batas wajar, dan status dokumen.
   - Mengidentifikasi issue kualitas data: OPD yatim (*orphan OPD*), klasifikasi yatim, ringkasan kosong, dan pesan galat unggah berkas.
   - Memisahkan kuantitas fisik berkas (`quantity_label`, misal: "1 Berkas") dari nominal nilai uang rupiah.
3. **Normalisasi Teks & Tokenisasi (`core/normalization.py`):**
   - Normalisasi Unicode NFKC, *case-folding* (huruf kecil), dan perapian spasi berlebih.
   - Melindungi format kode bergaris miring (seperti nomor surat/SPM: `158/LS/Dishub/2007`) agar tidak terpecah menjadi token terpisah.
   - Menerapkan kamus singkatan kearsipan daerah secara konsisten.
4. **Ekstraksi Metadata Terstruktur (`core/extraction.py`):**
   - Ekstraksi No. SPM, No. SP2D, Tanggal Dokumen, Nominal Rupiah, dan Pihak (CV/PT).
   - Katalog referensi jenis SPM (`core/spm_types.py`) berlabel status **"dugaan"** hingga dikonfirmasi resmi oleh dinas.
   - Melaporkan statistik sebagai **cakupan ekstraksi (coverage)**, bukan akurasi. Tidak ada klaim akurasi sebelum audit manual selesai.

### Tahap 2: Baseline Pencarian LIKE & Empat Algoritma Fuzzy Matching
1. **Pembanding Baseline LIKE (`core/search/like_baseline.py`):**
   - Meniru persis mekanisme pencarian DataTables pada e-Arsip SIMANIS eksisting: kueri dipecah per spasi, setiap kata harus cocok sebagai substring (case-insensitive) pada gabungan kolom yang tampil di antarmuka, dan hasil diurutkan berdasarkan `id_arsip ASC`.
2. **Mesin Indeks Pencarian Memori (`core/search/index.py`):**
   - Mengindeks korpus dokumen di memori, membangun kosakata token, dan memfasilitasi pencarian multi-field (ringkasan, SPM, pihak).
3. **Empat Algoritma Pencocokan Fuzzy (`core/search/matchers/`):**
   - `levenshtein.py`: Normalisasi jarak Levenshtein via RapidFuzz.
   - `jaro_winkler.py`: Jarak Jaro-Winkler via RapidFuzz.
   - `token_set.py`: Token Set Ratio via RapidFuzz.
   - `ngram.py`: Koefisien Dice Character N-Gram ber-padding karakter (ditulis sendiri dalam Python murni dan diverifikasi dengan pytest).
4. **Pembobotan & Perankingan Field (`core/search/ranker.py`):**
   - Menggabungkan skor kemiripan per field (*ringkasan, nomor SPM, nama pihak*) dengan bobot yang dapat dikonfigurasi (bobot sama rata dan bobot hasil penyetelan).

### Tahap 3: Metrik Evaluasi Ilmiah & Rekapitulasi Komputasi
1. **Formulasi Metrik Temu Kembali (`core/evaluation/metrics.py`):**
   - `precision_at_k`: Precision@5 (rasio dokumen relevan dalam 5 peringkat teratas).
   - `recall_at_k`: Recall@10 (rasio dokumen relevan yang ditemukan dalam 10 teratas terhadap seluruh dokumen relevan).
   - `reciprocal_rank`: Reciprocal Rank (1/rank dokumen relevan pertama; bernilai 0 jika tidak ada).
   - `mean_reciprocal_rank`: MRR@10 (rata-rata makro RR).
   - `hit_rate_at_k`: Hit Rate@5 dan Hit Rate@10 (bernilai 1 jika ada minimal 1 dokumen relevan di top-K, 0 jika tidak).
   - `zero_result_queries`: Jumlah kueri yang menghasilkan nol dokumen pada hasil pencarian.
2. **Jaminan Perhitungan:**
   - Seluruh fungsi metrik diverifikasi menggunakan contoh hitung tangan (*hand-calculated test fixtures*) pada unit test.
   - Penanganan pembagian dengan nol (*zero division*) yang aman secara matematis.

---

## 3. Kriteria Penerimaan (Acceptance Criteria)

### Kriteria Verifikasi Angka Acuan Data Sumber (Ground Truth):
Hasil parsing dan pembersihan terhadap salinan file dump `alsys_arsip(1).sql` wajib memverifikasi angka-angka acuan berikut:
1. **Total Record Arsip:** Tepat **1.737 record** (terdiri atas **1.590 In Aktif** status 1 dan **147 Statis** status 2).
2. **OPD Yatim (Orphan OPD):** Tepat **143 record** (OPD ID yang tidak terdaftar di master `apptb_opd`).
3. **Pesan Galat Dokumen:** Tepat **11 record** di mana kolom dokumen memuat pesan galat unggah sistem (misal `<p>Anda tidak memilih berkas...`).
4. **Label "No SPM":** Tepat **1.344 record** ringkasan yang memuat label teks `No SPM`.
5. **Tanggal Input Nol:** Tepat **147 record** yang memiliki tanggal input `0000-00-00`.
6. **Pelaporan Deviasi:** Setiap ketidakcocokan dari angka acuan di atas wajib dilaporkan secara eksplisit dan dicatat alasannya.

### Kriteria Mutu Teknis & Kode:
1. **Semua Uji Lulus:** Seluruh unit test pada suite `tests/` lulus (`pytest` mengembalikan exit code 0).
2. **Bebas Impor Framework:** Tidak ada satu pun baris kode di `core/` yang mengimpor `flask`, `flask_sqlalchemy`, atau dependensi web.
3. **Anti-Hardcode:** Tidak ada angka metrik atau klaim akurasi yang diketik manual di kode maupun docstring.
4. **Pelaporan Jujur:** Cakupan ekstraksi dilaporkan sebagai cakupan (*coverage*), bukan akurasi.
