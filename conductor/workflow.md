# Development Workflow & Scientific Evaluation Gates

## 1. Strategi Percabangan Git (Branching Strategy)
- **Cabang Utama (`main`):** Selalu dalam kondisi stabil, bersih, dan seluruh pengujian otomatis lulus.
- **Cabang Fitur Singkat (`feat/...` atau `fix/...`):**
  - Dibuat dari `main` untuk satu unit tugas spesifik (misal: `feat/metadata-extraction`, `feat/fuzzy-matchers`).
  - Penggabungan (*merge*) ke `main` hanya boleh dilakukan setelah rangkaian pengujian `pytest` lulus tanpa galat (100% green).
- **Format Pesan Commit:** Mengikuti format Conventional Commits ringkas berbahasa Indonesia (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`). Satu commit mewakili satu perubahan logis koheren (atomik).

## 2. Gerbang Mutu Perangkat Lunak (Quality Gates)
- **Pengecekan Wajib Sebelum Merge:**
  - `pytest tests/` wajib berjalan dan berhasil tanpa peringatan kritis.
  - Setiap fungsi publik baru di lapisan `core/` wajib disertai berkas uji unit terkait.
  - Fungsi kalkulasi metrik temu kembali (*Precision@5, Recall@10, MRR@10, Hit Rate*) wajib diverifikasi menggunakan kasus uji dengan nilai acuan hitung tangan (*hand-calculated ground truth*).
- **Definisi Selesai (Definition of Done - DoD):**
  Sebuah fitur dinyatakan selesai jika memenuhi 5 kriteria:
  1. Kode terimplementasi bersih sesuai pedoman gaya kode tanpa *placeholder*.
  2. Seluruh uji unit otomatis `pytest` lulus.
  3. Catatan keputusan desain/arsitektur terdokumentasi singkat di folder `docs/` sebagai bahan laporan penelitian mandiri.
  4. Diagram pendukung (ERD, flowchart) dan tangkapan layar antarmuka tersimpan rapi.
  5. Tidak ada angka metrik atau klaim yang diketik manual di kode, template, maupun dokumen; semua nilai harus dihasilkan oleh skrip.

## 3. Pemetaan Tahapan Waterfall ke Laporan Penelitian Mandiri (Bab IV)
Proses pengembangan mengikuti metodologi sekuensial yang terpetakan ke sub-bab laporan (penomoran sub-bab menyesuaikan template institusi dan arahan dosen pembimbing):
- **Tahap 1: Analisis Kebutuhan & Data:** Profiling data `apptb_arsip`, identifikasi anomali data (orphan OPD, tanggal kosong, format teks bebas), perumusan batasan fungsional.
- **Tahap 2: Perancangan Sistem & Algoritma:** Skema basis data SQLite, flowchart alur ekstraksi regex, formulasi matematis fungsi kemiripan (Levenshtein, Jaro-Winkler, Token Set, Dice N-gram), dan perancangan antarmuka Bootstrap 5.
- **Tahap 3: Implementasi Modul:** Realisasi modul parser, pembersih data, ekstraktor metadata, modul fuzzy search, dan antarmuka web Flask.
- **Tahap 4: Pengujian & Evaluasi Ilmiah:** Pelaksanaan audit ekstraksi, eksekusi set uji kueri, perbandingan metrik temu kembali terhadap baseline LIKE, dan pengujian pengguna (UAT/SUS).

## 4. Titik Pemeriksaan Administratif & Kolaborasi
- **Izin Pemakaian Data:** Dokumentasi persetujuan pemakaian salinan data dari Kepala Bidang tercatat secara administratif sebelum pelaksanaan pengujian sistem dengan petugas dinas.
- **Penjadwalan Kasus Nyata:** Pengumpulan kueri kasus nyata dari arsiparis dijadwalkan lebih awal agar set uji mencerminkan variasi pencarian aktual di lapangan.

## 5. Gerbang Urutan Evaluasi Ilmiah (Scientific Evaluation Sequence)
Untuk menjaga integritas metodologi penelitian, langkah evaluasi wajib mengikuti urutan ketat berikut:
1. **Gerbang 1 - Audit Ekstraksi Metadata:** Sampel data teracak dinilai secara manual oleh peneliti/arsiparis. Persentase akurasi dihitung murni oleh skrip sebelum beralih ke modul evaluasi kueri.
2. **Gerbang 2 - Penyusunan & Penguncian Set Uji:**
   - Kueri kasus nyata dari arsiparis dikumpulkan, ditambah kueri sintetis bergangguan realistis (total target 30–50 kueri).
   - Dilakukan *blind pooling* (gabungan top kandidat tanpa label metode) dan penilaian relevansi berpanduan aturan tertulis (dokumen dengan SPM atau substansi isi sama dinilai setara relevan).
   - Set uji dibagi (*stratified split*) dengan proporsi sekitar **30% tuning** dan **70% test** dari total kueri yang terkumpul.
   - Versi set uji **dikunci permanen** (dihitung hash SHA-256 isinya) dan tidak boleh dimodifikasi lagi.
3. **Gerbang 3 - Penyetelan Bobot (Tuning Phase):** Eksplorasi bobot field (*grid search*) hanya diperbolehkan menggunakan kueri pada kelompok *tuning*.
4. **Gerbang 4 - Pembekuan Konfigurasi & Evaluasi Akhir:**
   - Konfigurasi bobot optimal tiap metode dibekukan (*frozen*).
   - Evaluasi akhir dijalankan satu kali pada kelompok *test*.
   - **Ketat:** Penyetelan ulang bobot dilarang keras menggunakan kelompok *test*. Jika perbaikan kueri diperlukan, harus diterbitkan versi set uji baru (`testset_v2`).
   - Evaluasi akhir hanya boleh diulang untuk memperbaiki galat teknis pelaksanaan dengan alasan ilmiah yang tercatat.

## 6. Keterulangan (Reproducibility) & Integritas Angka
- **Pencatatan Parameter Eksperimen:** Setiap baris hasil evaluasi (`evaluation_run`) secara otomatis mencatat:
  - Nilai *random seed*.
  - Hash SHA-256 data arsip sumber.
  - Hash SHA-256 berkas set uji yang dikunci.
  - *Git commit hash* aktif saat evaluasi dijalankan.
  - Status *working tree* Git (bersih atau kotor). **Evaluasi akhir wajib ditolak jika working tree kotor (ada uncommitted changes).**
  - Waktu latensi rata-rata komputasi per kueri.
- **Ekspor Skrip Satu Perintah:** Seluruh tabel rekapitulasi, grafik, dan lampiran angka untuk naskah laporan diekspor otomatis via perintah CLI (`flask report export`) ke folder `output/`. Tidak ada angka yang diketik manual ke laporan.
- **Prosedur Pencadangan (Backup):** File database SQLite dan file set uji dicadangkan secara manual di luar folder Git sebelum eksekusi impor ulang maupun pengujian akhir. Data sensitif dinas dipastikan tidak pernah masuk ke repositori Git.

## 7. Manajemen Prioritas & Jadwal
- **Prioritas Utama (Fase 1):** Penyelesaian fondasi inti: impor data, ekstraksi metadata, pencarian multi-metode, audit ekstraksi, modul evaluasi kueri CLI/UI, dan ekspor laporan ilmiah.
- **Fitur Sekunder (Fase 2):** Modul penanda duplikasi arsip dan dashboard visualisasi kualitas data hanya dikerjakan apabila seluruh instrumen Fase 1 dan evaluasi ilmiah telah tuntas serta waktu memungkinkan.
- **Siklus Konsultasi:** Evaluasi kemajuan dilakukan melalui laporan kemajuan mingguan untuk menyelaraskan luaran dengan arahan dosen pembimbing penelitian mandiri.
