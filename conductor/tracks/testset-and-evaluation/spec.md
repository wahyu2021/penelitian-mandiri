# Specification: Testset & Scientific Evaluation (`testset-and-evaluation`)

## 1. Overview
Track ini membangun seluruh instrumen evaluasi temu kembali ilmiah dan keterulangan data untuk penelitian mandiri pada repositori lokal/privat:
1. Impor dump SQL e-Arsip SIMANIS ke database SQLite lokal (`instance/app.sqlite`) dengan verifikasi kelima angka acuan cocok.
2. Audit manual ekstraksi metadata pada 100 sampel berstrata dengan versi ekstraktor dibekukan, pelaporan akurasi per field dengan interval kepercayaan Wilson 95%, dan penilaian ulang 20 baris (jeda beberapa hari atau oleh arsiparis) untuk menghitung persentase kesepakatan.
3. Pedoman tertulis penilaian relevansi, termasuk aturan kesetaraan nomor SPM dan substansi isi yang sama.
4. Penyusunan set uji kueri (~40 kueri, min. 30) dengan uji pilot 5 kueri, *blind pooling* Top-10 dari 5 metode, ekspor spreadsheet untuk penilaian manual, impor kembali ke JSON set uji lengkap atribut, split berstrata ~30% tuning / ~70% test tanpa kebocoran SPM atau duplikat ringkasan, verifikasi sampel 20–30% oleh arsiparis, penilaian tambahan blind untuk unjudged di top-10, penyetelan bobot berbasis MRR@10 (tie-breaker P@5), dan evaluasi akhir via CLI dengan syarat working tree Git bersih.

## 2. Functional Requirements

### 2.1 Impor SQLite & Verifikasi Kelima Angka Acuan
- Lokasi basis data: `instance/app.sqlite`. `.gitignore` memastikan `instance/`, `*.db`, `*.sqlite`, `output/`, dan `.env` diabaikan Git.
- Skema tabel: `import_batch`, `archive_raw`, `archive`, `archive_metadata`, `opd`, `classification`, `spm_type`, `data_issue`.
- Verifikasi wajib kelima angka acuan dump cocok persis:
  1. Total arsip: 1.737 (1.590 In Aktif, 147 Statis).
  2. OPD yatim: 143 arsip.
  3. Dokumen pesan galat unggah: 11 berkas.
  4. Label 'No SPM': 1.344 berkas.
  5. Tanggal input `0000-00-00`: 147 berkas.
- CLI: `python -m scripts.import_dump --source <path_sql>` mencatat SHA-256 dump dan memverifikasi kelima angka acuan.

### 2.2 Audit Ekstraksi Metadata & Pembekuan Versi
- Versi ekstraktor dibekukan (`v1.0.0`). Cakupan (*coverage*) dihitung otomatis oleh skrip.
- 100 sampel acak berstrata (seed tetap 42) dengan strata: label "No SPM" (ada/tidak), status arsip (In Aktif / Statis), dan kode jenis SPM; jumlah per strata dicatat.
- Ekspor lembar audit ke `output/audit_extraction_sample.csv` (diabaikan Git).
- **Gerbang Manual:** Peneliti mengisi penilaian per field (`benar`, `salah`, `tidak_ada_di_teks`, plus penanda nilai terlewat di teks).
- Sampel audit dilarang dipakai untuk menyetel regex.
- Skrip kalkulasi akurasi:
  - Akurasi per field dengan interval kepercayaan Wilson 95%.
  - Penilaian ulang 20 baris (dengan jeda beberapa hari atau oleh arsiparis) untuk menghitung persentase kesepakatan (*percentage agreement*).
  - Seed dan versi ekstraktor tercatat di berkas hasil.

### 2.3 Pedoman Penilaian Relevansi Tertulis
- Dokumen [docs/pedoman_penilaian_relevansi.md](../../../docs/pedoman_penilaian_relevansi.md).
- Menetapkan kriteria objektif dokumen relevan vs tidak relevan untuk kueri topik, nomor SPM, pihak, dan campuran.
- **Aturan Kesetaraan:** Arsip dengan nomor SPM yang sama atau substansi/pekerjaan/pembayaran yang sama dinilai setara relevansinya (sama-sama relevan).

### 2.4 Penyusunan Set Uji, Blind Pooling & Penilaian Relevansi
- Target kueri: sekitar 40 kueri (minimum 30), bersumber dari kasus nyata arsiparis dan kueri sintetis dengan 6 jenis gangguan realistis (*typo*, singkatan, spasi/tanda baca, urutan kata, kata hilang, ejaan varian).
- **Aturan Kueri Nyata:** Bila kasus nyata dari arsiparis kurang dari 3, lanjutkan dengan kueri sintetis dan laporkan sebagai keterbatasan.
- **Pilot 5 kueri:** Dinilai terlebih dahulu untuk mengukur beban kerja dan jumlah dokumen unik per kueri. Merupakan bagian dari total kueri, dibagi berstrata, dan tidak dipakai untuk menyetel bobot.
- **Blind Pooling (Kedalaman 10):**
  - Gabungan Top-10 hasil dari 5 metode: LIKE (maks 10 urut id_arsip), Levenshtein, Jaro-Winkler, Token Set, N-gram Dice.
  - Arsip asal kueri sintetis selalu disertakan ke dalam pool.
  - Urutan pool diacak dengan seed tetap tanpa nama metode atau skor.
  - Ekspor ke `output/relevance_pool.csv` (diabaikan Git).
- **Gerbang Manual Penilaian:** Peneliti menilai relevansi via spreadsheet.
- **Verifikasi Arsiparis:** Arsiparis memverifikasi sampel 20–30% penilaian relevansi dan persentase kesepakatannya dilaporkan.
- **Impor & Struktur JSON Set Uji (`data/testset/testset_v1.json`):**
  - Memuat atribut lengkap: `query_id`, `query_text`, `source` (arsiparis/sintetis), `query_type` (topik/nomor_spm/pihak/campuran), `noise_type`, `split` (tuning/test), serta daftar penilaian (`archive_id`, `is_relevant`).
  - Disimpan pada repositori lokal/privat.
- **Pemisahan Kueri (Stratified Split ~30/70):**
  - Seed tetap 42. Dibagi berstrata menurut sumber dan tipe kueri.
  - **Pencegahan Kebocoran Data:** Kueri dari arsip yang sama, SPM yang sama, atau ringkasan sangat mirip (kandidat duplikat) wajib masuk kelompok (split) yang sama.
  - Berkas dikunci permanen dengan hash SHA-256.

### 2.5 Penyetelan Bobot & Evaluasi Temu Kembali CLI
- **Penyetelan Bobot (Tuning Phase):**
  - *Grid search* bobot field (*summary, spm, party*) hanya dilakukan pada kelompok *tuning* (~30%). Dilarang menyentuh kelompok *test*.
  - **Kriteria Pemilihan Bobot:** MRR@10 sebagai kriteria utama; jika seri, gunakan P@5.
- **Penilaian Tambahan Dokumen Belum Dinilai (*Unjudged in Top-10*):**
  - Sebelum evaluasi akhir, periksa apakah ada dokumen di top-10 yang belum pernah dinilai (`unjudged_in_top10`).
  - Bila ada, nilai secara buta dan simpan di berkas tambahan terpisah (`data/testset/additional_judgments_v1.json`) dengan hash sendiri tanpa mengubah berkas set uji yang terkunci.
  - Jumlah dokumen yang belum dinilai tetap dilaporkan di setiap run (dokumen belum dinilai diasumsikan tidak relevan).
- **Evaluasi Akhir (Final Evaluation):**
  - Dijalankan satu kali pada kelompok *test* (~70%).
  - CLI: `python -m scripts.evaluate --testset data/testset/testset_v1.json --mode final`.
  - **Syarat Wajib:** *Working tree Git bersih* (uncommitted changes ditolak).
  - Parameter tercatat otomatis di tiap run: seed, hash data, hash testset, commit SHA, rata-rata latensi komputasi, status working tree.
  - Aturan Pengulangan: Evaluasi akhir diulang hanya untuk memperbaiki galat teknis pelaksanaan dengan alasan tercatat; penyetelan ulang bobot dilarang keras memakai kelompok test; bila perlu, buat versi set uji baru (`testset_v2.json`).
  - Metrik: P@5, R@10, MRR@10, Hit Rate@5, Hit Rate@10, zero-result queries, dan unjudged in top-10.
  - Pelaporan: Bobot sama rata vs bobot tuning; hasil kueri kasus nyata arsiparis dilaporkan terpisah dari kueri sintetis; rincian per jenis kueri dan gangguan disajikan sebagai gambaran (bukan kesimpulan).

## 3. Acceptance Criteria
- [ ] Database `instance/app.sqlite` terisi dan kelima angka acuan cocok persis.
- [ ] Skrip audit menghasilkan 100 sampel berstrata (seed 42), mengekspor lembar audit, dan menghitung akurasi per field dengan interval Wilson + kesepakatan 20 baris.
- [ ] Berkas pedoman penilaian relevansi tertulis tersedia di `docs/`.
- [ ] Alur set uji menghasilkan `data/testset/testset_v1.json` yang memuat ~40 kueri lengkap atribut, hasil pooling, verifikasi arsiparis 20–30%, dan split tanpa kebocoran data.
- [ ] Mekanisme penilaian tambahan untuk unjudged dokumen di top-10 tersimpan di berkas terpisah dengan hash sendiri.
- [ ] CLI penyetelan bobot (MRR@10 utama, tie-breaker P@5) dan evaluasi akhir berfungsi penuh, menolak working tree kotor, dan mengekspor metrik ke `output/`.
- [ ] Seluruh uji unit baru dan lama lulus di cabang `feat/testset-and-evaluation`.
- [ ] `.gitignore` mengabaikan `instance/`, `*.db`, `*.sqlite`, `output/`, dan `.env`. Tidak ada bagian file yang terduplikasi.
