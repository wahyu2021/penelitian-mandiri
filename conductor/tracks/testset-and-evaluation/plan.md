# Implementation Plan: Testset & Scientific Evaluation

Track: `testset-and-evaluation`  
Metodologi: Berurutan Berbasis Gerbang Ilmiah (*Sequential Gated Execution*) — Cabang fitur: `feat/testset-and-evaluation`.

---

## Tahap 1: Skema Database & Impor SQL Dump ke SQLite

### 1.1 Skema Database SQLite Lokal (`instance/app.sqlite`)
- [x] Task: Definisikan skema SQLite di `services/db.py` untuk tabel `import_batch`, `archive_raw`, `archive`, `archive_metadata`, `opd`, `classification`, `spm_type`, dan `data_issue`.
    - [x] Buat fungsi inisialisasi tabel SQLite murni tanpa ketergantungan web framework.
    - [x] Pastikan `.gitignore` mengabaikan `instance/app.sqlite` dan `*.db`.

### 1.2 Modul Impor & Validasi Kelima Angka Acuan
- [x] Task: Implementasikan modul impor di `services/importer.py` dan CLI `scripts/import_dump.py`.
    - [x] Baca dump SQL melalui `core.sql_dump_parser.parse_sql_dump`.
    - [x] Simpan salinan mentah ke `archive_raw` dan data bersih ke `archive`.
    - [x] Jalankan normalisasi dan ekstraksi metadata ke `archive_metadata`.
    - [x] Lakukan verifikasi otomatis kelima angka acuan: 1.737 total arsip (1.590 In Aktif, 147 Statis), 143 OPD yatim, 11 galat dokumen, 1.344 label No SPM, 147 tanggal input 0000-00-00. Gagal impor jika ada angka yang tidak cocok.
    - [x] Catat SHA-256 file dump pada tabel `import_batch`.

### 1.3 Pengujian Unit Impor
- [x] Task: Tulis uji unit `tests/test_importer.py` memvalidasi parsing, penyimpanan data mentah dan bersih, serta penolakan bila angka acuan tidak sesuai.

### 1.4 Eksekusi Impor Riil & Verifikasi Angka Acuan
- [x] Task: Jalankan impor terhadap dump SIMANIS riil dan pastikan kelima angka acuan cocok persis.

---

## Tahap 2: Audit Ekstraksi Metadata & Pembekuan Versi

### 2.1 Pembekuan Versi Ekstraksi & Skrip Cakupan
- [x] Task: Tetapkan versi ekstraktor `v1.0.0` dan buat skrip `scripts/calculate_coverage.py` untuk menghitung persentase cakupan per field secara otomatis.

### 2.2 Penarikan 100 Sampel Acak Berstrata (Seed 42)
- [x] Task: Implementasikan generator sampel di `scripts/export_audit_sample.py`.
    - [x] Buat 100 sampel berstrata acak (seed 42) menurut strata: label No SPM, status arsip (In Aktif/Statis), dan jenis SPM. Catat kuota per strata.
    - [x] Ekspor lembar audit ke `output/audit_extraction_sample.csv` (diabaikan Git).
    - [x] Ekspor 20 sampel ganda untuk uji kesepakatan (*percentage agreement*).

### 2.3 Skrip Perhitungan Akurasi Wilson & Kesepakatan
- [x] Task: Implementasikan `core/evaluation/audit_metrics.py` dan CLI `scripts/evaluate_extraction_audit.py`.
    - [x] Hitung akurasi per field (`benar`, `salah`, `tidak_ada_di_teks`) ditambah penanda nilai terlewat (*false negative*).
    - [x] Hitung 95% interval kepercayaan Wilson score untuk tiap field.
    - [x] Hitung persentase kesepakatan pada 20 sampel ganda.
    - [x] Tulis uji unit di `tests/test_audit_metrics.py`.

### 2.4 Gerbang Manual: Pengisian Lembar Audit Ekstraksi
- [ ] Task: Gerbang Manual - Peneliti mengisi penilaian pada `output/audit_extraction_sample.csv` dan menjalankan skrip evaluasi audit sebelum melangkah ke penyusunan kueri.

---

## Tahap 3: Pedoman Relevansi, Penyusunan Kueri & Blind Pooling

### 3.1 Pedoman Penilaian Relevansi Tertulis
- [x] Task: Tulis dokumen [docs/pedoman_penilaian_relevansi.md](../../../docs/pedoman_penilaian_relevansi.md) yang merinci kriteria relevan/tidak relevan dan aturan kesetaraan nomor SPM/substansi isi sama.

### 3.2 Generator Kueri Sintetis Bergangguan
- [x] Task: Implementasikan generator kueri di `core/testset/synthetic_generator.py` dan `core/testset/noise.py`.
    - [x] Dukung 6 jenis gangguan realistis (*typo*, singkatan, spasi/tanda baca, urutan kata, kata hilang, ejaan varian).
    - [x] Catat ID arsip asal untuk kueri sintetis.

### 3.3 Gerbang Manual: Pengumpulan Kueri Kasus Nyata Arsiparis
- [ ] Task: Gerbang Manual - Kumpulkan kueri kasus nyata dari arsiparis (jika < 3, teruskan dengan kueri sintetis dan catat sebagai keterbatasan metodologis).

### 3.4 Modul Blind Pooling Top-10 & Ekspor Penilaian
- [x] Task: Implementasikan modul pooling di `core/testset/pooling.py` dan `scripts/create_relevance_pool.py`.
    - [x] Ambil Top-10 dari 5 metode pencarian (LIKE, Levenshtein, Jaro-Winkler, Token Set, N-gram).
    - [x] Masukkan arsip asal kueri sintetis ke dalam pool.
    - [x] Acak urutan dokumen per kueri (seed tetap 42) tanpa label metode atau skor.
    - [x] Ekspor ke `output/relevance_pool.csv` (diabaikan Git).

### 3.5 Gerbang Manual: Penilaian Pilot 5 Kueri
- [ ] Task: Gerbang Manual - Nilai 5 kueri pilot terlebih dahulu untuk mengukur rata-rata dokumen unik dan beban waktu penilaian.

### 3.6 Gerbang Manual: Penilaian Relevansi Penuh & Verifikasi Arsiparis
- [ ] Task: Gerbang Manual - Peneliti menyelesaikan penilaian relevansi seluruh kueri dan arsiparis memverifikasi sampel 20–30% untuk menghitung persentase kesepakatan.

### 3.7 Impor Hasil Penilaian, Anti-Leak Stratified Split & Penguncian JSON
- [x] Task: Implementasikan `scripts/build_testset.py` untuk mengimpor penilaian kembali ke `data/testset/testset_v1.json`.
    - [x] Struktur JSON lengkap: `query_id`, `query_text`, `source`, `query_type`, `noise_type`, `split`, daftar `archive_id` dan `is_relevant`.
    - [x] Lakukan stratified split ~30% tuning / ~70% test (seed 42).
    - [x] Pastikan kueri dari arsip yang sama, SPM yang sama, atau ringkasan sangat mirip (kandidat duplikat) masuk split yang sama agar tidak ada kebocoran data.
    - [x] Hitung hash SHA-256 berkas JSON dan kunci.
    - [x] Tulis uji unit di `tests/test_testset_builder.py`.

---

## Tahap 4: Penyetelan Bobot, Penilaian Tambahan & Evaluasi Temu Kembali CLI

### 4.1 Modul Penyetelan Bobot (Tuning Phase)
- [x] Task: Implementasikan `core/evaluation/tuning.py` dan CLI `scripts/tune_weights.py`.
    - [x] Jalankan grid search bobot field (*summary, spm, party*) hanya pada kelompok tuning (~30%).
    - [x] Pilih kombinasi bobot terbaik berdasarkan MRR@10 tertinggi (jika seri, gunakan P@5).
    - [x] Simpan bobot optimal dan laporkan perbandingan terhadap bobot sama rata.

### 4.2 Pemeriksaan & Penilaian Tambahan Dokumen Belum Dinilai di Top-10
- [x] Task: Implementasikan `scripts/check_unjudged.py`.
    - [x] Periksa kemunculan dokumen belum dinilai di Top-10 setelah bobot diterapkan.
    - [x] Jika ada, lakukan penilaian buta tambahan dan simpan di `data/testset/additional_judgments_v1.json` dengan hash sendiri tanpa mengubah `testset_v1.json`.
    - [x] Laporkan jumlah `unjudged_in_top10` (dokumen belum dinilai diasumsikan tidak relevan).

### 4.3 Evaluasi Akhir CLI pada Kelompok Test
- [x] Task: Implementasikan `core/evaluation/evaluator.py` dan CLI `scripts/evaluate.py`.
    - [x] Eksekusi evaluasi akhir satu kali pada kelompok test (~70%).
    - [x] Tolak eksekusi jika *working tree Git kotor* (uncommitted changes).
    - [x] Catat parameter reproducibility otomatis: seed, hash dump, hash testset, commit SHA, rata-rata latensi, status working tree.
    - [x] Hitung P@5, R@10, MRR@10, Hit Rate@5, Hit Rate@10, zero-result queries, dan unjudged in top-10.
    - [x] Pisahkan pelaporan kasus nyata arsiparis vs kueri sintetis; rincikan per jenis/gangguan sebagai gambaran.
    - [x] Ekspor rekapitulasi ke `output/final_evaluation_report.md`.

### 4.4 Pengujian Komprehensif & Penggabungan Cabang
- [x] Task: Tulis uji unit di `tests/test_tuning.py` dan `tests/test_evaluator.py`.
- [x] Task: Jalankan seluruh uji unit `pytest tests/` dan pastikan semua lulus.
- [ ] Task: Gabungkan cabang fitur `feat/testset-and-evaluation` ke `main` dengan pesan commit konvensional.
