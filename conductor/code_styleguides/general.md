# General Code & Engineering Standards: Sistem Pencarian Arsip SIMANIS

Panduan umum rekayasa perangkat lunak, kebersihan kode, dan manajemen versi (Git).

## 1. Kebijakan Integritas Ilmiah & Komputasi
- **Larangan Keras Nilai Statis (Anti-Hardcoded Metrics):**
  - Seluruh angka metrik evaluasi (P@5, R@10, MRR@10, Hit Rate, zero-result), akurasi ekstraksi metadata, dan statistik dataset wajib dihasilkan melalui kalkulasi komputasi kode.
  - Dilarang keras menuliskan angka metrik mentah secara statis di dalam docstring, kode sumber, template presentasi, maupun file markdown laporan.
- **Keterlacakan Hasil (Reproducibility):**
  - Setiap eksekusi evaluasi wajib merekam parameter seed, hash SHA-256 data sumber, commit Git aktif, dan waktu eksekusi pada tabel `evaluation_run`.

## 2. Prinsip Rekayasa Kode (Clean Code)
- **Single Responsibility:** Setiap modul, kelas, dan fungsi hanya bertanggung jawab atas satu tujuan logis yang spesifik.
- **Don't Repeat Yourself (DRY):** Ekstrak pola berulang (seperti normalisasi teks, tokenisasi, atau sanitasi input) ke dalam fungsi utilitas bersama.
- **Pemberian Nama yang Deskriptif:**
  - Nama variabel dan fungsi harus menjelaskan peruntukannya secara gamblang. Hindari singkatan ambigu seperti `temp`, `data2`, `x`, `res` (kecuali indeks loop lokal pendek).
  - Gunakan Bahasa Inggris untuk seluruh pengenal kode (*classes, functions, variables*).
  - Gunakan Bahasa Indonesia untuk komentar dan dokumentasi penjelasan logika (*docstrings*).
- **Larangan Kode Placeholder:** Jangan pernah meninggalkan fungsi kosong, komentar `// TODO`, atau data tiruan tanpa implementasi fungsional nyata.

## 3. Manajemen Versi & Standar Git
- **Commit Atomik:** Satu commit hanya memuat satu perubahan logis yang koheren.
- **Format Conventional Commits (Bahasa Indonesia):**
  - `feat:` penambahan fitur baru (misal: `feat: tambah modul ekstraksi metadata spm`)
  - `fix:` perbaikan bug/kesalahan (misal: `fix: perbaiki penanganan tanggal kosong 0000-00-00`)
  - `test:` penambahan atau pembaruan unit test (misal: `test: tambah uji hitung tangan mrr dan dice`)
  - `refactor:` restrukturisasi kode tanpa mengubah fungsionalitas (misal: `refactor: pisahkan matcher levenshtein ke modul tersendiri`)
  - `docs:` pembaruan dokumentasi atau panduan (misal: `docs: perbarui spesifikasi tech stack`)
  - `chore:` pemeliharaan konfigurasi dan dependensi (misal: `chore: perbarui kunci versi requirements.txt`)
- **Kebersihan Repositori:**
  - File rahasia (`.env`), database lokal (`instance/*.sqlite`), dump SQL mentah (`*.sql`), dan file hasil olahan (`*.csv`, `output/`) dilarang keras di-commit ke Git dan wajib diabaikan via `.gitignore`.
