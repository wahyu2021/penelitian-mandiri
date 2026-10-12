# Technology Stack: Sistem Pencarian Arsip pada e-Arsip (SIMANIS)

## 1. Bahasa Pemrograman & Runtime
- **Bahasa:** Python 3.14.5 (diuji pada lingkungan pengembangan aktif).
- **Format Sintaks:** Standar industri Python (PEP 8), *strict type hints* pada fungsi domain `core/`, *docstrings* ringkas berbahasa Indonesia.

## 2. Web Framework & Backend Architecture
- **Web Framework:** **Flask 3.1.3**
  - Pola arsitektur modular menggunakan *Application Factory* (`create_app`) dan *Blueprints* (`auth`, `main`, `search`, `archives`, `admin`, `testset`, `evaluation`).
  - Pemisahan tegas: Lapisan logika domain (`core/`) berupa Python murni tanpa ketergantungan pada Flask maupun ORM basis data, menjamin kemudahan pengujian independen.
- **ORM & Basis Data:**
  - **Flask-SQLAlchemy 3.1.1** (SQLAlchemy 2.1.4).
  - Basis Data: **SQLite 3** (file tunggal lokal `instance/app.sqlite`).
  - **Tanpa MySQL Driver:** Sistem sengaja tidak menyertakan driver `mysqlclient` atau `PyMySQL` untuk memastikan tidak ada koneksi langsung ke server produksi SIMANIS.
- **Autentikasi & Keamanan Web:**
  - **Flask-Login 0.6.3:** Pengelolaan sesi login dua peran (*Admin* dan *Petugas*).
  - **Flask-WTF 1.3.0 & WTForms 3.2.2:** Validasi form dan proteksi CSRF (*Cross-Site Request Forgery*).
  - **Werkzeug 3.1.9:** Hashing kata sandi menggunakan algoritma modern *scrypt*.
- **Konfigurasi Lingkungan:** **python-dotenv 1.2.4** membaca konfigurasi lokal dari `.env`.
- **Server WSGI (Uji Jaringan Lokal):** **Waitress 3.0.2** (dipilih karena ringan, stabil, dan berjalan secara native di lingkungan Windows tanpa dependensi compiler eksternal).

## 3. Komputasi Temu Kembali, Fuzzy Matching & Normalisasi
- **Fuzzy Matching Library:** **RapidFuzz 3.14.6**
  - Jarak Levenshtein: `rapidfuzz.distance.Levenshtein.normalized_similarity`
  - Jarak Jaro-Winkler: `rapidfuzz.distance.JaroWinkler.normalized_similarity`
  - Token Set Matching: `rapidfuzz.fuzz.token_set_ratio`
- **Metrik N-Gram Kustom:** **Dice Character N-Gram Coefficient**
  - Ditulis sendiri dalam modul `core/search/matchers/ngram.py` menggunakan Python murni ber-padding karakter, karena RapidFuzz tidak menyediakannya secara bawaan.
  - Diuji secara ketat menggunakan *pytest* dengan nilai acuan hitung tangan (*hand-calculated ground truth*).
- **Pengolahan & Evaluasi Data:** **pandas 3.0.6**
  - Digunakan untuk agregasi evaluasi kueri, perankingan, split dataset, dan kalkulasi metrik temu kembali (*Precision@5, Recall@10, MRR@10, Hit Rate@5/10, zero-result queries*).
- **Uji Signifikansi Statistik (Opsional):** **SciPy 1.18.1**
  - Digunakan secara selektif untuk uji Wilcoxon *signed-rank test* berpasangan antara metode terbaik vs baseline LIKE setelah seluruh metrik utama selesai dihitung.

- **Visualisasi Laporan Ilmiah & Ekspor Grafik:** **Matplotlib 3.11.2**
  - Digunakan pada skrip ekspor untuk menghasilkan figur cetak publikasi 300 DPI (`output/figures/`).
- **Analisis & Eksplorasi Interaktif:** **Jupyter Notebook & nbstripout 0.9.1**
  - Notebook interaktif di `notebooks/analisis_evaluasi.ipynb` hanya membaca artefak `output/` tanpa komputasi ulang. Filter `nbstripout` memastikan sel keluaran bersih sebelum komit ke repositori.

## 4. Antarmuka Pengguna & Frontend (Tanpa CDN)
- **CSS Framework:** **Bootstrap 5.3.3** (file lokal di `static/vendor/bootstrap/`, Lisensi MIT).
- **Template Engine:** **Jinja2 3.1.6** dengan template inheritance (`base.html`, komponen reusable, dan *partials*).
- **Visualisasi Grafik:** **Chart.js 4.4.7** (file lokal di `static/vendor/chartjs/`, Lisensi MIT).
- **Tipografi:** **Inter Font Family v3.19** (file font lokal `.woff2` di `static/vendor/fonts/`, Lisensi SIL Open Font License 1.1).
- **Zero CDN Policy:** Semua aset antarmuka dilayani langsung oleh server lokal, menjamin aplikasi berfungsi tanpa jaringan internet. Berkas lisensi tiap aset disertakan di folder masing-masing.

## 5. Pengujian & Jaminan Mutu Kode (QA)
- **Unit & Integration Testing:** **pytest 9.1.1**
  - Pengujian modul ekstraksi regex (SPM, SP2D, tanggal, nominal Rp, pihak).
  - Pengujian normalisasi teks, pembersihan data, dan kamus singkatan.
  - Pengujian algoritma matching (Levenshtein, Jaro-Winkler, Token Set, Dice N-gram, LIKE baseline).
  - Pengujian perhitungan metrik evaluasi (P@5, R@10, MRR@10, Hit Rate).

## 6. Daftar Versi Dependensi Langsung Terkunci (requirements.txt)
*(Daftar dependensi langsung berikut diambil dari lingkungan virtual teruji dan akan diverifikasi ulang pada instalasi bersih venv)*
```text
Flask==3.1.3
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.3.0
matplotlib==3.11.2
nbstripout==0.9.1
pandas==3.0.6
pytest==9.1.1
python-dotenv==1.2.4
RapidFuzz==3.14.6
scipy==1.18.1
SQLAlchemy==2.1.4
waitress==3.0.2
Werkzeug==3.1.9
WTForms==3.2.2
```

## 7. Lingkungan Pengembangan & Pengujian Perangkat Keras
- **Prosesor:** AMD Ryzen 5 6600H (6 Cores, 12 Threads, clock dasar 3.3 GHz, boost s.d. 4.5 GHz).
- **Memori RAM:** 16 GB DDR5.
- **Penyimpanan:** NVMe PCIe SSD.
- **Sistem Operasi:** Microsoft Windows 11 (64-bit).
- **Terminal & Shell:** PowerShell 7.
- **Version Control:** Git 2.54+ (repositori lokal/privat).
