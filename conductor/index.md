# Project Index: Sistem Pencarian Arsip pada e-Arsip (SIMANIS)

> **Project Overview**: Sistem Pencarian Arsip Berbasis Website untuk Dinas Perpustakaan dan Kearsipan Kota Palembang yang mengintegrasikan ekstraksi & normalisasi metadata dari ringkasan teks bebas serta perbandingan algoritma fuzzy matching (Levenshtein, Jaro-Winkler, Token Set, dan N-Gram) berbobot field terhadap baseline pencarian eksak/LIKE bawaan sistem, dengan modul evaluasi temu kembali komputasional ilmiah.

## Architecture & Technology Stack
- **Bahasa & Runtime:** Python 3.14.5 (diuji pada mesin AMD Ryzen 5 6600H, RAM 16 GB, Windows 11).
- **Backend & Web:** Flask 3.1.3 (Application Factory + Blueprints), Jinja2 3.1.6 template engine.
- **Basis Data:** SQLite 3 lokal via Flask-SQLAlchemy 3.1.1 (tanpa driver MySQL produksi, salinan terisolasi).
- **Autentikasi & Keamanan:** Flask-Login 0.6.3, Werkzeug 3.1.9 (scrypt hashing), Flask-WTF 1.3.0 (proteksi CSRF).
- **Fuzzy Matching & Temu Kembali:** RapidFuzz 3.14.6, Custom Pure-Python Dice Character N-Gram, Pandas 3.0.6, SciPy 1.18.1 (uji Wilcoxon opsional).
- **Server WSGI Lokal:** Waitress 3.0.2 (server lokal Windows mandiri).
- **Frontend (Zero CDN):** Bootstrap 5.3.3, Chart.js 4.4.7, Inter Font Family v3.19 (seluruh aset disimpan lokal di `static/vendor/`).
- **Jaminan Kualitas (QA):** pytest 9.1.1 dengan pengujian ketat fungsi domain `core/` dan acuan hitung tangan.

## Development Workflow & Quality Gates
- **Metodologi:** Waterfall (Analisis Kebutuhan, Perancangan, Implementasi, Evaluasi) terpetakan ke Bab IV Laporan Penelitian Mandiri.
- **Percabangan Git:** `main` (stabil) dan cabang fitur singkat (`feat/...`). Penggabungan wajib lulus `pytest` 100%.
- **Gerbang Evaluasi Berurutan:** Audit ekstraksi manual → Penguncian set uji teracak (30% tuning, 70% test) → Penyetelan bobot (hanya tuning) → Pembekuan konfigurasi → Evaluasi akhir satu kali pada test set (wajib working tree Git bersih).
- **Integritas Komputasi:** Seluruh angka metrik, akurasi, dan laporan diekspor murni via skrip CLI (`output/`). Dilarang mengetik manual angka metrik di kode maupun naskah.

## Design & UX Guidelines
- **Gaya Visual:** Pemerintahan Modern (tema terang, aksen navy/slate, kontras WCAG AA 4.5:1 / 3:1).
- **Pencarian Ramah Pengguna:** Penyorotan kata cocok dengan sanitasi HTML aman, tooltip skor kemiripan, penanganan nol hasil informatif.
- **Pemisahan Peran:** Dropdown pemilih algoritma dan perbandingan hanya dapat diakses Admin; Petugas menggunakan metode bawaan terkonfigurasi.
- **Status Transparan:** Teks dan ikon indikator untuk status arsip (In Aktif, Statis, Musnah) dan badge *"Dugaan"* pada jenis SPM.

## Tracks
> Tracks organize work into high-level features or milestones.

| ID | Title | Status | Description |
| :--- | :--- | :--- | :--- |
| [core-domain-and-search](tracks/core-domain-and-search/) | Core Domain Logic & Multi-Method Search | Completed | Fondasi domain logika Python murni: parser SQL dump aman, ekstraksi metadata terstruktur, algoritma pencocokan fuzzy multi-metode dan baseline LIKE SIMANIS, serta metrik temu kembali ilmiah. |
