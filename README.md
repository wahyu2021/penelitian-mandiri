# Panduan Singkat Folder PM

## Arah pengembangan

Antarmuka web utama memakai **Flask JSON API + React/TypeScript**. Rancangan,
pilihan library, struktur folder, kontrak API,
dan urutan migrasi ada di [docs/arsitektur_flask_react.md](docs/arsitektur_flask_react.md).
Kebutuhan produk, prioritas, serta kriteria penerimaan ada di
[docs/PRD.md](docs/PRD.md).
Urutan tiket, uji per tiket, dan aturan commit ada di
[docs/BACKLOG.md](docs/BACKLOG.md).
Aturan yang wajib dibaca AI sebelum mengubah kode ada di [AGENTS.md](AGENTS.md).
Fondasi React/Vite kini ada di [`frontend/`](frontend/) dengan login, dashboard
yang memakai angka dari `/api/v1/dashboard`, halaman status layanan,
pencarian arsip di `/app/search`, detail di `/app/archives/{id}`, serta
perbandingan metode khusus admin di `/app/compare`. Langkah menjalankan
aplikasi di bawah ini menjelaskan versi React yang sekarang dipakai.

Node.js dipakai di laptop untuk Vite dan build frontend. Paket rilis memuat
aset hasil build dan berjalan dengan Python/Waitress tanpa Node.js, npm, CDN,
atau proses PHP. Lihat [runbook rilis web](docs/runbook_web_release.md) untuk
instalasi, variabel lingkungan, pencadangan, dan rollback.

Untuk pengembangan React dengan Vite, lihat [`frontend/README.md`](frontend/README.md).

## Paket React lokal tanpa Node.js saat berjalan

Dari folder `D:\Coding\PM` pada laptop pengembang:

```powershell
.\.venv\Scripts\python.exe scripts\build_web_release.py
```

Perintah ini menjalankan `npm ci` dan build bersih, lalu membuat ZIP di
`output/releases/`. Ekstrak ZIP di komputer uji yang disetujui; jalankan
Waitress dari folder `pm-web` dengan `PM_DB_PATH` ke
salinan SQLite **di luar folder rilis**, dan `PM_SECRET_KEY` yang tetap.
Buka `http://127.0.0.1:8000/login` untuk antarmuka React. Langkah lengkap
dan pemulihan ada di [runbook](docs/runbook_web_release.md).

## Menjalankan aplikasi web

Aplikasi utama kini menyediakan login, dashboard korpus, pencarian LIKE dan empat metode fuzzy,
perbandingan hasil untuk admin, detail arsip, dan impor salinan dump melalui web.
Halaman audit, set uji, evaluasi, dan administrasi pengguna pada `rancangan_aplikasi.md` masih harus dibangun
sebelum UAT/SUS untuk keseluruhan aplikasi.

Route API berada di `webapp/api/`, mesin pencarian di `services/web_search.py`,
dan `app.py`/`wsgi.py` menjadi titik masuk. UI Jinja lama dihapus setelah uji
paritas PM-14; rumus dan mesin pencarian tidak berubah.

Jalankan dari folder `D:\Coding\PM`:

```powershell
.\.venv\Scripts\flask.exe --app app user create --username admin --role admin
.\.venv\Scripts\python.exe scripts\build_web_release.py
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 wsgi:app
```

Jika menyiapkan lingkungan Python khusus web, instal hanya `requirements-web.txt`.
Paket notebook/analisis seperti pandas dan scipy tidak diperlukan untuk halaman web
yang sudah tersedia. Perintah `report export-bundle` tetap memakai lingkungan
penelitian lengkap dari `requirements.txt`.

Perintah pertama meminta kata sandi secara interaktif (minimal 10 karakter).
Perintah kedua membuat aset React dan ZIP rilis; untuk pengembangan lokal,
`npm run build` dari `frontend/` juga cukup. Jika build belum ada, route API
tetap dapat diuji tetapi halaman web tidak tersedia. Kemudian buka
`http://127.0.0.1:8000/login`. Untuk akun petugas, ulangi perintah pertama dengan
`--role petugas` dan nama pengguna lain. Basis data bawaan adalah `instance/app.sqlite`;
atur `PM_DB_PATH` jika memakai basis data lokal lain. Server sengaja dibatasi pada
komputer sendiri. Jika `PM_SECRET_KEY` tidak diatur, sesi login akan berakhir saat
server dimulai ulang.
Untuk instalasi melalui HTTPS, atur `PM_COOKIE_SECURE=1` dan gunakan
`PM_SECRET_KEY` acak yang tetap antar-restart. Saat uji HTTP lokal, jangan aktifkan
cookie Secure karena browser tidak akan mengirimnya lewat HTTP.

### Impor salinan dump oleh admin

Tempatkan berkas `.sql` yang diizinkan pada direktori khusus di komputer uji,
di luar folder rilis. Atur `PM_IMPORT_DIR` ke path absolut direktori itu dan,
bila perlu, `PM_IMPORT_BACKUP_DIR` ke direktori cadangan terpisah. Jika variabel
cadangan tidak diatur, cadangan dibuat di folder `backups` di samping SQLite.
Buka `/app/imports` sebagai admin, pilih berkas, periksa pratinjau dan hash,
lalu jalankan impor. Aplikasi tidak menerima unggahan atau path bebas dari browser.
Verifikasi angka acuan dump aktif secara default; pengelola dapat mengatur
`PM_IMPORT_VERIFY_REFERENCE_COUNTS=0` hanya saat menggunakan salinan lain yang
sudah diperiksa. Impor ulang mengganti data arsip lokal, tetapi mempertahankan
akun, log aktivitas, dan riwayat batch. Cadangan SQLite dibuat lebih dulu.

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
