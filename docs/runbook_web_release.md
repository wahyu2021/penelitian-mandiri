# Runbook rilis web Flask + React (PM-13/PM-14)

Runbook ini untuk **komputer uji yang disetujui**. Paket ZIP memuat kode Python
dan aset React hasil build.
Paket tidak memuat basis data, dump SQL, hasil penelitian, akun, rahasia,
`node_modules`, atau lingkungan Python. Node.js diperlukan pada laptop pembangun
paket, tetapi **tidak** pada komputer yang menjalankan Waitress.

## 1. Bangun paket pada laptop pengembang

Dari `D:\Coding\PM` dengan Python web dan Node.js/npm tersedia:

```powershell
.\.venv\Scripts\python.exe scripts\build_web_release.py
```

Skrip menjalankan `npm ci` dan `npm run build`, memeriksa aset yang dirujuk
`index.html`, lalu membuat `output/releases/pm-web-YYYYMMDD-HHMMSS.zip`.
Gunakan `--output D:\lokasi\pm-web.zip` bila perlu lokasi lain. Simpan hasil
`Get-FileHash <lokasi-zip> -Algorithm SHA256` bersama catatan versi yang diuji.
`release-manifest.json` di dalam ZIP mencatat SHA-256 tiap berkas paket.

## 2. Siapkan komputer uji

1. Pastikan OS dan versi Python yang diizinkan pengelola TI dapat menjalankan
   versi pada `requirements-web.txt`. Ekstrak ZIP ke folder baru, misalnya
   `D:\PMWeb\rilis-001\pm-web`; jangan menimpa rilis yang sedang dipakai.
2. Sediakan paket Python dari sumber yang disetujui. Jika komputer uji tidak
   memiliki akses internet, siapkan *wheelhouse* yang cocok dengan OS, arsitektur,
   dan versi Python komputer tersebut. Dari folder `pm-web` jalankan:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --no-index --find-links D:\wheelhouse -r requirements-web.txt
   ```

   Bila instalasi dari indeks paket disetujui, gunakan `pip install -r
   requirements-web.txt`. Proses aplikasi setelah instalasi tidak membutuhkan
   internet, CDN, npm, atau proses Node.js.
3. Tempatkan salinan SQLite penelitian di folder data terpisah dari rilis,
   misalnya `D:\PMData\app.sqlite`, dengan izin baca/tulis hanya untuk akun
   layanan yang disetujui. Jangan menyalin basis data ke ZIP rilis.
4. Siapkan variabel lingkungan proses. Nilai rahasia di bawah adalah petunjuk;
   simpan nilai sebenarnya di konfigurasi lokal yang dibatasi, bukan di Git atau
   dokumen laporan.

   | Variabel | Isi |
   |---|---|
   | `PM_SERVE_REACT` | Opsional; otomatis `1` jika build React tersedia. `0` hanya untuk uji API tanpa UI |
   | `PM_DB_PATH` | Path absolut SQLite salinan penelitian, di luar folder rilis |
   | `PM_SECRET_KEY` | Nilai acak panjang yang tetap antar-restart; wajib untuk sesi stabil |
   | `PM_COOKIE_SECURE` | `1` hanya bila browser mengakses melalui HTTPS; `0` untuk HTTP lokal |
   | `PM_IMPORT_DIR` | Direktori absolut berisi dump `.sql` yang diizinkan; wajib untuk fitur impor web |
   | `PM_IMPORT_BACKUP_DIR` | Direktori absolut cadangan SQLite, di luar folder rilis; default `backups` di samping SQLite |
   | `PM_IMPORT_VERIFY_REFERENCE_COUNTS` | `1` secara default; `0` hanya untuk snapshot lain yang telah diperiksa |

   Contoh untuk terminal uji lokal:

   ```powershell
   $env:PM_DB_PATH = 'D:\PMData\app.sqlite'
   $env:PM_SECRET_KEY = '<nilai-rahasia-lokal-yang-tetap>'
   $env:PM_COOKIE_SECURE = '0'
   .\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 wsgi:app
   ```

   Untuk akses intranet, pengelola TI menentukan alamat bind, firewall,
   reverse proxy, TLS, akun layanan, dan kebijakan log. Jangan memakai
   `--listen=0.0.0.0` tanpa keputusan tersebut. XAMPP/PHP bukan runtime aplikasi.

## 3. Verifikasi sebelum dipakai petugas

- Buka `/login`, masuk dengan akun uji pada salinan data, lalu buka langsung
  dan muat ulang `/app/dashboard`, `/app/search`, `/app/archives/{id}`, dan
  `/app/compare` sebagai admin. Petugas tidak melihat menu perbandingan.
- Pastikan `/api/v1/health` menghasilkan JSON dan `/api/v2/tidak-ada`
  menghasilkan 404 JSON. `/assets/nama-yang-tidak-ada.js` harus 404, bukan HTML
  React. Periksa JS, CSS, dan font di `/assets/` termuat dari server lokal.
- Putuskan sambungan internet pada komputer uji yang sudah terpasang dependensi,
  lalu ulangi login–cari–detail–banding. Koneksi lokal ke Waitress tetap diperlukan.
  Catat perangkat, browser, tanggal, dan hasil uji; jangan menyalin data arsip
  asli ke catatan terbuka.
- Sebagai admin, buka `/app/imports`; pastikan hanya berkas dalam `PM_IMPORT_DIR`
  yang terlihat. Periksa hash dan jumlah pada pratinjau. Uji impor pada salinan
  SQLite terpisah terlebih dahulu; pastikan cadangan, riwayat, dan log tindakan
  tercatat. Jangan menunjuk `PM_DB_PATH` ke basis data SIMANIS asli.

## 4. Cadangan dan pemulihan

Sebelum mengganti rilis atau basis data, hentikan Waitress. Salin file SQLite
beserta berkas `-wal`/`-shm` jika ada ke lokasi cadangan terbatas; lebih aman
gunakan mekanisme backup SQLite saat layanan masih aktif. Simpan juga ZIP rilis
sebelumnya dan nilai `PM_SECRET_KEY` yang sama. PM-13 tidak mengubah skema data.

Jika rilis baru bermasalah: hentikan Waitress, jalankan kembali folder rilis
sebelumnya dengan `PM_DB_PATH` dan `PM_SECRET_KEY` yang sama, lalu periksa
`/api/v1/health` dan alur login. Pulihkan cadangan database **hanya** bila
database ikut berubah atau rusak; jangan menimpa penilaian baru tanpa
keputusan pemilik data. UI Jinja tidak tersedia lagi di rilis PM-14; untuk
memulihkan UI sebelumnya, jalankan folder rilis PM-13. Perintah riset
`report export-bundle` tidak dikemas dalam
paket web minimal; jalankan dari lingkungan penelitian lengkap.
