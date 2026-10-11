# Implementation Plan: Core Domain Logic & Multi-Method Search

Track: `core-domain-and-search`  
Metodologi: Bertahap (Staged Execution) — Setiap tahap wajib selesai dan **semua uji lulus** sebelum beralih ke tahap berikutnya.

---

## Tahap 1: Parser Dump, Pembersihan Data, Normalisasi & Ekstraksi Metadata

### 1.1 Persiapan Lingkungan & Scaffolding
- [x] Buat file dependensi runtime terkunci `requirements.txt` dan `.env.example`.
- [x] Buat struktur paket `core/` dan `tests/` dengan file `__init__.py`.

### 1.2 Modul Parser SQL Dump (`core/sql_dump_parser.py`)
- [x] Implementasikan fungsi `parse_sql_dump(filepath)` untuk membaca `apptb_arsip`, `apptb_opd`, dan `apptb_klasifikasi`.
- [x] Tambahkan pemblokiran tegas untuk tabel `apptb_user`, `apptb_log`, dan `apptb_arsip1`.
- [x] Implementasikan perhitungan hash SHA-256 file dump input.
- [x] Tulis unit test `tests/test_sql_dump_parser.py` untuk menguji parsing string, handling escape, dan pengabaian tabel sensitif.

### 1.3 Modul Pembersihan & Validasi Data (`core/cleaning.py`)
- [x] Implementasikan fungsi `clean_archive_record()` untuk normalisasi nilai dan identifikasi anomali data.
- [x] Validasi tanggal input nol (`0000-00-00`), rentang tahun wajar, status dokumen (1, 2, 3), dan deteksi OPD yatim.
- [x] Pisahkan kuantitas berkas fisik (`quantity_label`) dari nilai uang rupiah.
- [x] Tulis unit test `tests/test_cleaning.py` untuk memvalidasi seluruh jenis issue data.

### 1.4 Modul Normalisasi & Tokenisasi (`core/normalization.py`)
- [x] Implementasikan `normalize_text()` dengan Unicode NFKC, *case-folding*, dan kamus singkatan kearsipan.
- [x] Lindungi nomor kode bergaris miring (misal: `158/LS/Dishub/2007`) agar tetap utuh sebagai satu kesatuan token.
- [x] Implementasikan fungsi `tokenize()` yang konsisten untuk dokumen dan kueri.
- [x] Tulis unit test `tests/test_normalization.py` dengan variasi singkatan, kode slash, dan tanda baca.

### 1.5 Modul Ekstraksi Metadata & Kamus Jenis SPM (`core/extraction.py` & `core/spm_types.py`)
- [x] Implementasikan kamus `core/spm_types.py` dengan seluruh kode awal berstatus tegas **"dugaan"**.
- [x] Implementasikan `extract_metadata()` berbasis regex untuk No. SPM, No. SP2D, Tanggal, Nominal Rp, dan Pihak (CV/PT).
- [x] Hitung statistik kelengkapan sebagai **cakupan ekstraksi (coverage)**, tanpa klaim akurasi sebelum audit.
- [x] Tulis unit test `tests/test_extraction.py` menguji berbagai pola penulisan teks ringkasan.

### 1.6 Gerbang Verifikasi Tahap 1
- [x] Jalankan uji integrasi terhadap file dump riil `D:\Coding\earsip\alsys_arsip(1).sql`.
- [x] Verifikasi angka acuan: 1.737 record (1.590 In Aktif, 147 Statis), 143 OPD yatim, 11 galat dokumen, 1.344 label No SPM, 147 tanggal 0000-00-00. Laporkan deviasi jika ada.
- [x] Jalankan `pytest tests/` dan pastikan **semua uji lulus**.

---

## Tahap 2: Baseline Pencarian LIKE & Empat Algoritma Fuzzy Matching

### 2.1 Pembanding Pencarian LIKE SIMANIS (`core/search/like_baseline.py`)
- [ ] Implementasikan kelas `LikeBaselineSearch` yang meniru persis filter DataTables SIMANIS:
  - Tokenisasi kueri per spasi.
  - Setiap kata harus muncul sebagai substring (case-insensitive) pada gabungan kolom tampilan.
  - Urutan hasil berdasarkan `id_arsip ASC`.
- [ ] Tulis unit test `tests/test_like_baseline.py`.

### 2.2 Algoritma Pencocokan Fuzzy (`core/search/matchers/`)
- [ ] Implementasikan antarmuka abstrak `BaseMatcher` di `core/search/matchers/base.py`.
- [ ] Implementasikan `LevenshteinMatcher` menggunakan RapidFuzz.
- [ ] Implementasikan `JaroWinklerMatcher` menggunakan RapidFuzz.
- [ ] Implementasikan `TokenSetMatcher` menggunakan RapidFuzz.
- [ ] Implementasikan `DiceNgramMatcher` (Dice Character N-Gram kustom dengan padding) dalam Python murni.
- [ ] Tulis unit test `tests/test_matchers.py` memverifikasi skor setiap matcher terhadap pasangan string teruji.

### 2.3 Indeks Memori & Pembobotan Field (`core/search/index.py` & `core/search/ranker.py`)
- [ ] Implementasikan `SearchIndex` untuk menampung korpus dokumen, kosakata, dan representasi token per field.
- [ ] Implementasikan `FieldRanker` untuk menggabungkan skor kemiripan (*ringkasan, SPM, pihak*) dengan bobot terkonfigurasi.
- [ ] Tulis unit test `tests/test_search_index.py` dan `tests/test_ranker.py`.

### 2.4 Gerbang Verifikasi Tahap 2
- [ ] Jalankan pencarian uji coba terhadap kelima metode untuk kueri umum dan kueri bertipe.
- [ ] Jalankan `pytest tests/` dan pastikan **semua uji lulus**.

---

## Tahap 3: Metrik Evaluasi Ilmiah & Rekapitulasi Komputasi

### 3.1 Modul Metrik Temu Kembali (`core/evaluation/metrics.py`)
- [ ] Implementasikan fungsi `precision_at_k(retrieved_ids, relevant_ids, k=5)`.
- [ ] Implementasikan fungsi `recall_at_k(retrieved_ids, relevant_ids, k=10)`.
- [ ] Implementasikan fungsi `reciprocal_rank(retrieved_ids, relevant_ids, max_k=10)`.
- [ ] Implementasikan fungsi `hit_rate_at_k(retrieved_ids, relevant_ids, k)`.
- [ ] Implementasikan fungsi `macro_average_metrics(query_results)`.
- [ ] Implementasikan perhitungan jumlah kueri nol hasil (*zero-result queries*).

### 3.2 Modul Agreement Validation (`core/evaluation/agreement.py`)
- [ ] Implementasikan fungsi penghitungan persentase kesepakatan (*percentage agreement*) antara peneliti dan arsiparis pada sampel 20–30%.

### 3.3 Verifikasi Uji Unit Metrik
- [ ] Tulis unit test `tests/test_metrics.py` memverifikasi P@5, R@10, MRR@10, Hit Rate, dan zero-result terhadap kumpulan contoh hitung tangan (*hand-calculated test fixtures*).
- [ ] Tulis unit test `tests/test_agreement.py` memverifikasi kalkulasi percentage agreement.

### 3.4 Gerbang Verifikasi Tahap 3 & Penyelesaian Track
- [ ] Jalankan suite uji lengkap: `pytest tests/ -v`.
- [ ] Pastikan **semua uji lulus** tanpa kegagalan.
- [ ] Buat dokumentasi ringkasan penyelesaian track di `docs/core_domain_summary.md`.
- [ ] Commit hasil implementasi secara atomik ke Git dengan pesan konvensional.
