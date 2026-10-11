# Python Code Style Guide: Sistem Pencarian Arsip SIMANIS

Dokumen ini memadukan prinsip Google Python Style Guide (PEP 8) dengan aturan spesifik proyek penelitian kearsipan ini.

## 1. Aturan Khusus Proyek (Mandatory Rules)
- **Bahasa & Lokalisasi:**
  - Sintaks, nama modul, kelas, fungsi, dan variabel wajib menggunakan **Bahasa Inggris** (standar industri).
  - Komentar kode dan *docstrings* menggunakan **Bahasa Indonesia** yang ringkas, jelas, dan hanya untuk logika non-trivial.
- **Isolasi Logika Domain (`core/`):**
  - Modul di dalam `core/` adalah Python murni. Dilarang keras mengimpor pustaka `Flask`, `flask_sqlalchemy`, atau dependensi web lainnya ke dalam `core/`.
  - Akses basis data dan integrasi web hanya diizinkan di lapisan `app/models/` dan `app/services/`.
- **Anti-Hardcode Angka Metrik:**
  - Dilarang keras mengetik manual angka metrik, persentase akurasi, atau nilai statistik di dalam kode, template, maupun docstring (misalnya dilarang menulis klaim "akurasi 100%"). Semua angka wajib dihasilkan dari komputasi skrip.
- **Jaminan Pengujian (Test-Driven):**
  - Setiap fungsi pembersihan, normalisasi, ekstraksi, matching, dan metrik di `core/` wajib memiliki uji otomatis menggunakan `pytest`.
  - Fungsi metrik temu kembali (*Precision@5, Recall@10, MRR@10, Hit Rate*) wajib diuji terhadap contoh nilai acuan hitung tangan (*hand-calculated ground truth*).
- **Keamanan & Rahasia:**
  - Dilarang menaruh kunci rahasia (*SECRET_KEY*), kata sandi, atau data riil dinas di dalam kode. Konfigurasi wajib dibaca dari `.env` dengan contoh tanpa rahasia di `.env.example`.
- **Alat Bantu Format:**
  - *Ruff* atau *Black* dapat digunakan sebagai alat bantu pengembangan lokal, namun tidak dimasukkan ke dalam file dependensi runtime `requirements.txt`.

## 2. Standar Bahasa & Sintaks Python
- **Type Annotations:** Terapkan *type hints* secara ketat pada seluruh fungsi publik di lapisan `core/` dan `services/`.
- **Line Length:** Maksimum 100 karakter untuk keterbacaan yang seimbang di monitor modern.
- **Indentation:** 4 spasi per level indentasi. Jangan gunakan tab.
- **Docstrings:** Gunakan format `"""triple double quotes"""` dengan struktur:
  - Ringkasan satu baris.
  - `Args:` penjelasan parameter.
  - `Returns:` penjelasan nilai kembalian.
- **Naming Conventions:**
  - Variabel & Fungsi: `snake_case` (e.g., `calculate_mrr`, `normalized_query`).
  - Kelas: `PascalCase` (e.g., `SearchIndex`, `LevenshteinMatcher`).
  - Konstanta: `ALL_CAPS_WITH_UNDERSCORES` (e.g., `DEFAULT_POOL_DEPTH`).
  - Fungsi internal / privat: Awali dengan garis bawah tunggal (`_internal_helper`).
