# Project Index: Sistem Pencarian Arsip pada e-Arsip (SIMANIS)

> **Project Overview**: Sistem Pencarian Arsip Berbasis Website untuk Dinas Perpustakaan dan Kearsipan Kota Palembang yang mengintegrasikan ekstraksi & normalisasi metadata dari ringkasan teks bebas serta perbandingan algoritma fuzzy matching (Levenshtein, Jaro-Winkler, Token Set, dan N-Gram) berbobot field terhadap baseline pencarian eksak/LIKE bawaan sistem, dengan modul evaluasi temu kembali komputasional ilmiah.

**Kebutuhan produk dan kriteria penerimaan:** [`../docs/PRD.md`](../docs/PRD.md).
**Pelaksanaan per tiket dan bukti uji:** [`../docs/BACKLOG.md`](../docs/BACKLOG.md).

## Architecture & Technology Stack
- **Bahasa & Runtime:** Python 3.14.5 (diuji pada mesin AMD Ryzen 5 6600H, RAM 16 GB, Windows 11).
- **Backend & Web:** Flask application factory; target endpoint JSON `/api/v1`. UI saat ini masih Jinja2 selama migrasi.
- **Basis Data:** SQLite 3 lokal lewat `services/db.py`/`sqlite3` (tanpa koneksi MySQL produksi).
- **Autentikasi & Keamanan:** Flask-Login, hash kata sandi Werkzeug, cookie sesi, CSRF pada operasi tulis, otorisasi peran di server.
- **Fuzzy Matching & Temu Kembali:** RapidFuzz 3.14.6, Custom Pure-Python Dice Character N-Gram, Pandas 3.0.6, SciPy 1.18.1 (uji Wilcoxon opsional).
- **Server WSGI Lokal:** Waitress 3.0.2 (server lokal Windows mandiri).
- **Frontend target (Zero CDN):** React + TypeScript + Vite, React Router, TanStack Query, Tailwind CSS, shadcn/ui berbasis Radix, Lucide React, dan Recharts untuk grafik evaluasi.
- **Deploy target:** Node.js hanya untuk build di laptop; Flask/Waitress melayani aset statis dan API di intranet.
- **Jaminan Kualitas (QA):** pytest 9.1.1 dengan pengujian ketat fungsi domain `core/` dan acuan hitung tangan.

## Development Workflow & Quality Gates
- **Aturan AI dan arsitektur:** [`../AGENTS.md`](../AGENTS.md) dan [`../docs/arsitektur_flask_react.md`](../docs/arsitektur_flask_react.md).
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
| [testset-and-evaluation](tracks/testset-and-evaluation/) | Testset & Scientific Evaluation | Infrastruktur tersedia; verifikasi petugas tertunda | Impor dan evaluasi CLI tersedia. Verifikasi penilai kedua, kesepakatan audit, dan pengujian pengguna belum menjadi hasil final. |

---

- [ ] **Track: testset-and-evaluation — infrastruktur ada, validasi petugas belum lengkap**
*Link: [./tracks/testset-and-evaluation/](./tracks/testset-and-evaluation/)*
