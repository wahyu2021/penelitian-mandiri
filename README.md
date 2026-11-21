# Panduan Singkat Folder PM

## Arah pengembangan

Arsitektur yang dipilih untuk pengembangan berikutnya adalah **Flask JSON API +
React/TypeScript**. Rancangan, pilihan library, struktur folder, kontrak API,
dan urutan migrasi ada di [docs/arsitektur_flask_react.md](docs/arsitektur_flask_react.md).
Kebutuhan produk, prioritas, serta kriteria penerimaan ada di
[docs/PRD.md](docs/PRD.md).
Urutan tiket, uji per tiket, dan aturan commit ada di
[docs/BACKLOG.md](docs/BACKLOG.md).
Aturan yang wajib dibaca AI sebelum mengubah kode ada di [AGENTS.md](AGENTS.md).
Fondasi React/Vite kini ada di [`frontend/`](frontend/) sebagai halaman status
yang memeriksa `/api/v1/health`. API sesi JSON sudah tersedia, tetapi login,
dashboard, pencarian, dan detail React
belum tersedia; langkah menjalankan aplikasi di bawah ini menjelaskan versi
Flask/Jinja yang sekarang dipakai untuk alur kerja.

Node.js nantinya dipakai di laptop untuk Vite dan build frontend. Paket produksi
akan berisi aset hasil build dan berjalan dengan Python/Waitress tanpa Node.js,
npm, CDN, atau proses PHP. Prosedur pengemasan akan ditambahkan pada PM-13.

Untuk menjalankan pratinjau fondasi React, lihat
[`frontend/README.md`](frontend/README.md). Paket produksi Flask + aset React
masih menunggu tiket PM-13.

## Aplikasi web lokal (dasar Fase 1)

Aplikasi utama kini menyediakan login, dashboard korpus, pencarian LIKE dan empat metode fuzzy,
perbandingan hasil untuk admin, serta detail arsip. Halaman impor, audit, set uji,
evaluasi, dan administrasi pengguna pada `rancangan_aplikasi.md` masih harus dibangun
sebelum UAT/SUS untuk keseluruhan aplikasi.

Antarmuka saat ini memakai CSS lokal di `static/css/app.css` dan pilihan ikon Lucide 1.77.0
di `templates/icons/lucide_sprite.svg` (lisensi di `static/vendor/lucide/LICENSE`).
Tidak ada CDN, Node.js, atau proses kompilasi aset saat aplikasi saat ini dijalankan.
Route Flask dipisah ke modul `webapp/`, mesin pencarian ke `services/web_search.py`,
dan `app.py`/`wsgi.py` hanya menjadi titik masuk.

Jalankan dari folder `D:\Coding\PM`:

```powershell
.\.venv\Scripts\flask.exe --app app user create --username admin --role admin
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 wsgi:app
```

Jika menyiapkan lingkungan Python khusus web, instal hanya `requirements-web.txt`.
Paket notebook/analisis seperti pandas dan scipy tidak diperlukan untuk halaman web
yang sudah tersedia. Perintah `report export-bundle` tetap memakai lingkungan
penelitian lengkap dari `requirements.txt`.

Perintah pertama meminta kata sandi secara interaktif (minimal 10 karakter). Kemudian
buka `http://127.0.0.1:8000`. Untuk akun petugas, ulangi perintah pertama dengan
`--role petugas` dan nama pengguna lain. Basis data bawaan adalah `instance/app.sqlite`;
atur `PM_DB_PATH` jika memakai basis data lokal lain. Server sengaja dibatasi pada
komputer sendiri. Jika `PM_SECRET_KEY` tidak diatur, sesi login akan berakhir saat
server dimulai ulang.
Untuk instalasi melalui HTTPS, atur `PM_COOKIE_SECURE=1` dan gunakan
`PM_SECRET_KEY` acak yang tetap antar-restart. Saat uji HTTP lokal, jangan aktifkan
cookie Secure karena browser tidak akan mengirimnya lewat HTTP.

### Jika server dinas memakai XAMPP lama

XAMPP/PHP tidak menjalankan aplikasi Flask secara langsung. Untuk uji penelitian,
jalankan aplikasi dari laptop atau komputer uji yang memiliki Python dan Waitress,
dengan izin pengelola jaringan/data. Jangan mengubah konfigurasi server SIMANIS yang
sedang dipakai sebelum kebutuhan dan kebijakan Diskominfo/dinas dikonfirmasi.
Jika kelak diizinkan memasang di lingkungan dinas, Flask dapat berjalan sebagai
layanan terpisah di port internal; pengelola server menentukan apakah Apache XAMPP
dijadikan reverse proxy, bagaimana TLS, akun layanan, firewall, pencadangan, dan log
diatur. Keputusan itu memerlukan inventaris OS, versi Python yang diperbolehkan,
hak instalasi, serta kebijakan keamanan setempat. Node.js tetap tidak diperlukan
di server karena aset web sudah siap pakai.

Perhitungan kesepakatan relevansi setelah 120 penilaian terisi:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_relevance_agreement.py
.\.venv\Scripts\flask.exe --app app report export-bundle
```

Bundle menghitung ulang dari CSV penilaian terkini. Jika penilaian masih kosong atau
sebagian, status tetap `pending_second_rater`; jangan menyajikan metrik kesepakatan
sebagai hasil akhir. Catatan penilai pada `output/query_realism_validation_sample.csv`
harus diklarifikasi kepada penilainya jika janggal, terutama Q062; jangan mengganti
catatan asli tanpa jejak koreksi.

## File yang digunakan

- `notebooks/paket_pipeline_analisis_sampai_presentasi.zip`: paket untuk menjalankan analisis secara mandiri. Ekstrak ZIP, lalu buka notebook di dalamnya.
- Notebook kerja berada di dalam ZIP; berkas notebook di akar `notebooks/`
  saat ini tidak ada dalam working tree dan belum diputuskan untuk dikembalikan.
- `scripts/build_colab_bundle_notebook.py`: pembangkit sumber notebook aktif.
- `data/testset/`: set uji dan bobot hasil tuning yang digunakan evaluasi.
- `output/colab_bundle/`: enam berkas agregat yang dibaca notebook.
- `output/relevance_pool.csv` dan `output/audit_extraction_sample.csv`: penilaian sumber. Simpan beserta cadangan di `output/.real_data_backup/` dan `output/.labeler_backups/`.

## Berkas lama

- `legacy/`: notebook dan pembangkit notebook generasi lama, disimpan sebagai riwayat.
- `output/legacy_2026-11-09/`: hasil evaluasi lama, salinan paket yang pernah diekstrak, dan grafik lama. Hasil di sini tidak dipakai pipeline aktif.

Jika ZIP diekstrak di `notebooks/`, folder `notebooks/paket_pipeline_analisis_sampai_presentasi/` akan muncul sebagai salinan kerja lokal yang diabaikan Git. ZIP tetap menjadi berkas distribusi utama.
