# Backlog tiket — Flask API + React dan penelitian arsip

Sumber kebutuhan: [PRD](PRD.md), [arsitektur](arsitektur_flask_react.md),
[protokol set uji](protokol_testset_v2.md). Dokumen ini mencatat status tiap
tiket beserta bukti uji. Fondasi Flask/Jinja dan skrip CLI yang sudah ada
dipakai ulang, tetapi tidak otomatis membuat tiket migrasi berstatus selesai.

## Cara memakai backlog

**Koreksi lingkup 23 November 2026.** Pengembangan dipisah tegas menjadi dua
jalur agar fitur pengguna tidak bercampur dengan alat eksperimen:

- **Jalur Operasional (`/app`) — prioritas aktif:** fokus pada kebutuhan
  sehari-hari petugas dan admin (Dashboard, Pencarian fuzzy, Detail & Lokasi
  Arsip, Impor salinan data, Administrasi akun & log). Tidak boleh ada menu
  atau kontrol riset yang bocor ke ruang operasional.
- **Jalur Ruang Penelitian (`/app/research`) — ruang pribadi peneliti:**
  menampung perbandingan metode, audit ekstraksi, kamus SPM, set uji, dan
  penilaian relevansi. Penyelesaian alat penelitian tidak boleh menambah menu
  ke sidebar operasional; tautan tugas penilaian dibagikan peneliti kepada
  akun yang ditugaskan. Tiket penelitian lanjutan (`PM-19`, `PM-20`) ditunda
  sementara sampai produk operasional siap dan dikaji ulang kebutuhannya
  terhadap skrip CLI.

1. Kerjakan tiket menurut dependensinya. Ubah status menjadi `berjalan`,
   `tertahan`, atau `selesai` dengan tanggal, bukti uji, dan hash commit.
2. Satu tiket menghasilkan perubahan yang dapat ditinjau sendiri. Jika
   melebar, pecah menjadi tiket baru sebelum menulis kode. Uji relevan dan
   dokumentasi fitur disertakan dalam commit fitur yang sama.
3. Pengujian di setiap tiket adalah **fase wajib**, bukan pekerjaan opsional
   setelah semua fitur dibuat. Catat perintah uji dan hasilnya pada tiket.
4. Data penilaian petugas, CSV hasil, dump, database, `.env`, dan `dist/`
   tidak masuk Git. Catat lokasi/ID bukti tanpa menyalin data sensitif.
5. Perubahan pada folder laporan Word dilakukan hanya atas permintaan pengguna;
   tiket dokumentasi laporan di sini adalah gerbang sinkronisasi setelah kode
   dan hasil nyata tersedia.

### Status dan bukti per tiket

Gunakan satu baris seperti ini di bawah tiket saat dikerjakan:

`Status: belum dimulai | Uji: — | Commit: — | Catatan: —`

`selesai` berarti kriteria penerimaan terpenuhi, fase uji lulus, commit
tertinjau, dan hash dicatat. `tertahan` harus menyebut penyebab nyata dan
langkah yang masih bisa dikerjakan. Jangan menandai selesai berdasarkan
tampilan atau klaim dokumen saja.

## Aturan commit yang mudah dibaca

- Format subjek: `tipe(scope): hasil konkret [PM-XX]`, misalnya
  `feat(api): tambah sesi login JSON [PM-02]`. Gunakan `feat`, `fix`, `test`,
  `refactor`, `docs`, atau `chore`; scope contoh `api`, `frontend`, `research`,
  `build`, `docs`. Subjek menjelaskan perubahan, bukan kata umum seperti
  “update”, “final”, “misc”, atau “perbaikan lagi”.
- Satu commit memuat satu perubahan logis dan uji yang membuktikannya. Satu
  tiket kecil biasanya satu commit. Tiket besar boleh beberapa commit yang
  tetap dapat dibaca terpisah, misalnya `feat(api)` lalu `feat(frontend)`
  setelah tiket dipecah. Jangan mengumpulkan semua P0 menjadi satu commit.
- Sebelum staging, periksa `git status --short` dan `git diff`. Stage path
  terkait tiket secara eksplisit atau `git add -p`; hindari `git add .` pada
  working tree yang sudah berisi pekerjaan lain. Periksa
  `git diff --cached --stat`, `git diff --cached`, dan
  `git diff --cached --check` sebelum commit.
- Jalankan uji tiket, lalu uji regresi yang relevan. Jika gagal, perbaiki
  lebih dulu. Setelah commit, periksa `git show --stat --oneline HEAD` dan
  catat hash di tiket. Jangan menulis “tests pass” bila belum dijalankan.
- Jika perubahan membutuhkan migrasi data, jelaskan cara rollback di badan
  commit. Berkas keluaran, rahasia, database, dan data petugas tetap di luar
  commit. Jangan menulis ulang riwayat yang sudah dibagikan tanpa alasan jelas.
- **Working tree sekarang sudah memiliki perubahan dari pekerjaan sebelumnya,**
  termasuk penghapusan notebook yang tidak terkait tiket ini. PM-00 harus
  memilahnya dahulu; jangan memasukkan semuanya ke satu commit atau
  mengembalikan penghapusan itu tanpa keputusan berdasarkan konteks.

## Tiket fondasi

### PM-00 — Audit dan amankan baseline working tree

- **Dependensi:** tidak ada.
- **Selesai saat:** semua perubahan lama dipetakan ke fitur/dokumen; data
  pengguna dan penghapusan notebook ditandai terpisah; baseline kode dapat
  diuji. Rancangan teknis lama diperiksa terhadap protokol set uji dan CLI
  aktual agar angka/perintah historis tidak terbaca sebagai kondisi sekarang.
  Commit lama dibuat per perubahan logis bila memang siap.
- **Uji:** `git status --short`, `git diff --check`, uji Python yang relevan
  untuk kelompok perubahan; periksa ulang daftar staged sebelum tiap commit.
- **Commit:** beberapa commit terpisah bila diperlukan, misalnya
  `feat(web): tambah fondasi aplikasi Flask [PM-00]` dan
  `docs(project): selaraskan arsitektur dan PRD [PM-00]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: `pytest -q` 156 lulus, 5 dilewati; uji kelompok riset/pelabel/web lulus | Commit: `bcde733`, `602abfd`, `b985fba`, dan commit dokumentasi PM-00 | Catatan: penghapusan `notebooks/pipeline_analisis_sampai_presentasi.ipynb` tetap di luar staging karena belum diputuskan.

### PM-01 — Tetapkan kontrak dan fondasi Flask API

- **Dependensi:** PM-00. **PRD:** FR-01–FR-05.
- **Selesai saat:** blueprint `/api/v1` dan format `data`/`error` konsisten;
  `/api/*` yang tidak dikenal tidak jatuh ke halaman React; aturan status,
  validasi, dan pagination ditulis dalam kontrak API yang dapat ditinjau
  (`docs/api_contract.yaml` atau dokumen setara). Route Jinja tetap berjalan.
- **Uji:** Flask test client untuk 400/404/500 JSON, bentuk respons,
  dan route Jinja lama; `pytest tests/`.
- **Commit:** `feat(api): siapkan kontrak JSON berversi [PM-01]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: `pytest -q` 160 lulus, 5 dilewati; kontrak API + web 9 lulus | Commit: commit PM-01 pada riwayat Git | Catatan: PM-01 hanya menyediakan health dan penanganan galat; endpoint bisnis tetap target PM-03–PM-06.

### PM-02 — Sesi API, CSRF, dan izin peran

- **Dependensi:** PM-01. **PRD:** FR-01.
- **Selesai saat:** endpoint sesi masuk/keluar/status tersedia; cookie dan
  CSRF ditangani; 401 berbeda dari 403; admin/petugas dibatasi di server.
- **Uji:** login berhasil/gagal, sesi habis, CSRF hilang/salah, akses petugas
  ke endpoint admin, logout, dan atribut cookie lewat Flask test client.
- **Commit:** `feat(api): tambah sesi dan otorisasi peran [PM-02]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 15 uji sesi/kontrak/web lulus; `pytest -q` 166 lulus, 5 dilewati | Commit: commit PM-02 pada riwayat Git | Catatan: `PM_SECRET_KEY` tetap diperlukan saat layanan dimulai ulang; `PM_COOKIE_SECURE=1` untuk akses HTTPS.

### PM-03 — Dashboard API dari data nyata

- **Dependensi:** PM-01, PM-02. **PRD:** FR-02.
- **Selesai saat:** endpoint ringkasan membaca statistik dari salinan SQLite
  dengan sumber angka tunggal dan tidak memuat nilai contoh.
- **Uji:** fixture database berisi data, database kosong, 401, dan kegagalan
  akses database; bandingkan angka API dengan query sumber.
- **Commit:** `feat(api): sediakan ringkasan dashboard [PM-03]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 10 uji dashboard/web lulus; `pytest -q` 171 lulus, 5 dilewati | Commit: commit PM-03 pada riwayat Git | Catatan: API dan Jinja berbagi fungsi `services/dashboard.py`; data terbaru berarti ID tertinggi, bukan tanggal dokumen terbaru.

### PM-04 — Pencarian API dan pembatasan metode

- **Dependensi:** PM-01, PM-02. **PRD:** FR-03.
- **Selesai saat:** endpoint pencarian memakai `services/web_search.py`;
  kueri/filter/limit divalidasi; petugas memakai metode bawaan dan admin boleh
  memilih metode untuk analisis; hasil memuat metadata minimum.
- **Uji:** kueri tepat/typo/kosong, filter valid/tidak valid, nol hasil,
  limit, 401, dan penolakan metode admin bagi petugas; uji domain tetap lulus.
- **Commit:** `feat(api): sediakan pencarian arsip terfilter [PM-04]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 22 uji API pencarian/web lulus; `pytest -q` 190 lulus, 5 dilewati | Commit: commit PM-04 pada riwayat Git | Catatan: metode bawaan sementara `like`; pilihan fuzzy hanya admin. Total pagination berasal dari daftar hasil berurutan yang sama.

### PM-05 — Detail arsip API

- **Dependensi:** PM-01, PM-02. **PRD:** FR-04.
- **Selesai saat:** endpoint detail menampilkan teks asli, hasil ekstraksi,
  status dugaan, serta lokasi yang tersedia tanpa mengarang nilai kosong.
- **Uji:** arsip lengkap/sebagian kosong, ID tidak ada, 401, dan sanitasi
  bentuk respons; `pytest tests/`.
- **Commit:** `feat(api): sediakan detail dan lokasi arsip [PM-05]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 10 uji API detail/web lulus; `pytest -q` 195 lulus, 5 dilewati | Commit: commit PM-05 pada riwayat Git | Catatan: API dan Jinja berbagi query detail; API hanya mengirim field tampilan dan nilai kosong tetap `null`.

### PM-06 — Perbandingan metode khusus admin

- **Dependensi:** PM-04. **PRD:** FR-05.
- **Selesai saat:** satu kueri menghasilkan daftar metode dengan batas hasil
  dan label yang jelas; endpoint hanya dapat dipakai admin.
- **Uji:** hasil tiap metode dengan fixture tetap; 401/403; kueri tidak valid;
  angka skor tidak dihitung ulang di HTTP layer.
- **Commit:** `feat(api): tambah perbandingan metode admin [PM-06]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 40 uji pencarian API/web lulus; `pytest -q` 211 lulus, 5 dilewati | Commit: commit PM-06 pada riwayat Git | Catatan: batas 1–20 hasil per metode; skor dikirim apa adanya dan tidak dibandingkan antar metode.

## Tiket frontend React

### PM-07 — Siapkan React, TypeScript, Vite, dan shadcn/ui

- **Dependensi:** PM-00. **PRD:** P0, kebutuhan portabilitas/aksesibilitas.
- **Selesai saat:** `frontend/` punya TypeScript strict, alias `@/`, Tailwind,
  `components.json` dengan basis Radix yang dipilih eksplisit, token tema,
  `package-lock.json`, router/provider, dan komponen shadcn/ui minimum saja.
  Tidak ada CDN. Kode di `components/ui/` hasil generator direview.
- **Uji:** `npm ci`, lint, pemeriksaan tipe, uji render komponen dasar, dan
  `npm run build`; cek bundle tidak meminta CDN.
- **Commit:** `chore(frontend): siapkan React dan shadcn UI [PM-07]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: `npm ci`, lint, typecheck, 2 uji render/API, format check, build lulus; audit dependensi produksi 0 temuan | Commit: commit PM-07 pada riwayat Git | Catatan: CLI shadcn hanya dependensi pengembangan; audit penuh masih melaporkan 4 temuan tingkat sedang pada rantai CLI dan perlu dipantau saat pembaruan.

### PM-08 — Login React dan kerangka navigasi

- **Dependensi:** PM-02, PM-07. **PRD:** FR-01.
- **Selesai saat:** login/logout, pemulihan sesi, route terlindungi, navigasi
  peran, serta keadaan 401/403/loading/error bekerja tanpa menyimpan sesi di
  localStorage. Tampilan dapat dipakai dengan keyboard dan layar kecil.
- **Uji:** Testing Library untuk alur sesi dan galat; uji browser login/logout,
  reload, keyboard, ponsel/tablet; lint, tipe, build.
- **Commit:** `feat(frontend): tambah login dan navigasi [PM-08]`.
- **Jejak:** Status: sebagian selesai (21 November 2026) | Uji: 6 uji frontend lulus saat commit; login/status/logout berhasil di browser desktop; login dan navigasi dashboard diperiksa pada ponsel | Commit: commit login PM-08 pada riwayat Git | Catatan: login/logout, pemulihan sesi, route terlindungi, dan kerangka navigasi sudah ada; menu bisnis per peran serta uji keyboard/reload menyeluruh menunggu fitur PM-10–PM-12 sebelum tiket ditutup.

### PM-09 — Dashboard React

- **Dependensi:** PM-03, PM-08. **PRD:** FR-02.
- **Selesai saat:** kartu statistik mengambil API, memberi konteks angka,
  serta menangani data kosong/loading/error tanpa nilai contoh.
- **Uji:** respons berisi angka/empty/error; cek layout desktop/tablet/ponsel;
  lint, tipe, build.
- **Commit:** `feat(frontend): tampilkan dashboard korpus [PM-09]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 10 uji frontend lulus; lint, tipe, format, build lulus; browser desktop/tablet 768 px/ponsel 390 px tanpa gulir horizontal | Commit: commit PM-09 pada riwayat Git | Catatan: angka dibaca dari API PM-03; daftar terbaru berdasarkan ID arsip dan belum membuka detail React yang menunggu PM-11.

### PM-10 — Pencarian React

- **Dependensi:** PM-04, PM-08. **PRD:** FR-03.
- **Selesai saat:** kueri, filter, hasil, batas hasil, penjelasan skor, nol
  hasil, dan sorotan teks aman bekerja. Petugas tidak melihat pemilih metode
  admin. URL dapat dibagikan tanpa membocorkan data sesi.
- **Uji:** Testing Library untuk pencarian/filter/empty/error; browser dengan
  typo, keyboard, ponsel/tablet; pemeriksaan sorotan tanpa HTML mentah.
- **Commit:** `feat(frontend): tambah alur pencarian arsip [PM-10]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 15 uji frontend lulus; lint, tipe, format, build lulus; browser typo/Enter pada desktop dan viewport tablet 768 px/ponsel 390 px tanpa gulir horizontal; `pytest -q` 214 lulus, 5 dilewati | Commit: `5769e3b`, `6b2fcba`, `f4f09c4` | Catatan: opsi filter dibaca dari API, sorotan teks aman tanpa HTML mentah, metode hanya dapat dipilih admin, dan URL hanya menyimpan parameter pencarian. Detail arsip dikerjakan pada PM-11.

### PM-11 — Detail arsip React

- **Dependensi:** PM-05, PM-08. **PRD:** FR-04.
- **Selesai saat:** detail memperlihatkan teks asli, metadata, lokasi, dan
  label kekosongan/dugaan; navigasi kembali ke hasil pencarian tetap jelas.
- **Uji:** data penuh/sebagian kosong, 404, 401, tampilan ponsel/tablet,
  keyboard, lint, tipe, build.
- **Commit:** `feat(frontend): tampilkan detail dan lokasi arsip [PM-11]`.
- **Jejak:** Status: selesai (21 November 2026) | Uji: 20 uji frontend lulus; lint, tipe, format, build lulus; 5 uji API detail lulus; browser desktop/tablet 768 px/ponsel 390 px tanpa gulir horizontal, navigasi cari–detail–kembali berhasil | Commit: `6ae9dc2` | Catatan: teks asli dirender aman, field kosong jelas, status dugaan diberi penjelasan, dan parameter pencarian tetap ada pada tautan kembali.

### PM-12 — Perbandingan metode React

- **Dependensi:** PM-06, PM-08. **PRD:** FR-05.
- **Selesai saat:** admin dapat membandingkan hasil metode dengan label dan
  urutan jelas; petugas mendapat 403 dan tidak melihat menu admin.
- **Uji:** hasil kosong/berisi/error, peran admin/petugas, tabel pada layar
  sempit, lint, tipe, build.
- **Commit:** `feat(frontend): tampilkan perbandingan metode [PM-12]`.
- **Jejak:** Status: selesai (22 November 2026) | Uji: 26 uji frontend lulus; lint, tipe, format, build lulus; 38 uji API pencarian/perbandingan lulus; browser desktop/tablet 768 px/ponsel 390 px tanpa gulir horizontal; admin melihat lima metode dan petugas mendapat 403 pada alamat langsung | Commit: `8fcf970` | Catatan: urutan dan skor diambil dari API, tabel per metode memiliki penjelasan skor lintas metode, dan URL hanya menyimpan parameter kueri/filter.

## Tiket kemasan dan paritas

### PM-13 — Kemas build React untuk Flask/Waitress

- **Dependensi:** PM-08–PM-12. **PRD:** P0, portabilitas.
- **Selesai saat:** Flask melayani `frontend/dist/`, fallback SPA tidak
  menelan `/api/*`, aset ber-hash termuat, dan skrip rilis menyertakan build
  tanpa `node_modules/` maupun data penelitian. Runbook instalasi, variabel
  lingkungan, pencadangan, dan rollback ditulis untuk komputer uji.
- **Uji:** build bersih dari `npm ci`, jalankan Waitress tanpa proses Node,
  buka direct URL/reload route SPA, cek 404 API dan aset, uji offline.
- **Commit:** `feat(build): kemas React untuk Waitress [PM-13]`.
- **Jejak:** Status: selesai (22 November 2026) | Uji: `npm ci` dari cache offline (0 temuan audit), build/lint/tipe/format dan 26 uji frontend lulus; `pytest -q` 226 lulus, 5 dilewati; ZIP 75 entri dengan SHA-256 manifest valid, tanpa data/`node_modules`; Waitress dari ZIP diekstrak tanpa Node melayani login–cari–detail–banding, reload route React, aset ber-hash, 404 aset, dan API JSON | Commit: `499088b` | Catatan: rilis uji `output/releases/pm-web-20261122-102412.zip` (SHA-256 `B67F8D1A0E21B08E5D8E4581E712BA4566B43B6C489F8FC8CBFBDE8963D8AA34`); flag `PM_SERVE_REACT=1` mengaktifkan React, Jinja lama tetap tersedia untuk PM-14.

### PM-14 — Uji paritas dan rapikan UI Jinja lama

- **Dependensi:** PM-13. **PRD:** gerbang P0.
- **Selesai saat:** alur P0 React setara atau lebih baik dari Jinja; route,
  template, CSS, dan ikon lama yang tidak terpakai dihapus secara terukur;
  README memuat cara menjalankan versi baru.
- **Uji:** regresi Flask dan frontend, alur login–cari–detail–banding,
  desktop/tablet/ponsel, keyboard; bandingkan hasil pencarian sebelum/sesudah.
- **Commit:** `refactor(web): hapus antarmuka Jinja yang terganti [PM-14]`.
- **Jejak:** Status: selesai (22 November 2026) | Uji: baseline Jinja/API pada 4 kueri-metode menghasilkan urutan ID sama; `pytest -q` 226 lulus, 5 dilewati; lint, tipe, 26 uji frontend, build Vite lulus; ZIP 62 entri dengan manifest SHA-256 valid, tanpa aset Jinja atau data; smoke ZIP tanpa Node melewati login–dashboard–cari–detail–banding, route SPA dan galat JSON; browser lokal melewati alur yang sama, Enter pada pencarian, dan halaman perbandingan tanpa overflow pada viewport 390/820/1440 px | Commit: `8b1f008` | Catatan: ZIP `output/releases/pm-web-20261122-105559.zip` (SHA-256 `76d32d6d86f1422ed9142b49d0c50bd63b7e6722ddc428366b909a64fd22ffa3`); UI lama dihapus, `PM_SERVE_REACT` otomatis aktif jika build ada.

## Jalur Operasional — Fokus Petugas & Admin (Prioritas Aktif)

### PM-15 — Impor salinan data melalui web

- **Dependensi:** PM-02, PM-08. **PRD:** FR-07.
- **Selesai saat:** admin memilih dump dari lokasi yang diizinkan, melihat
  pratinjau/hasil dan riwayat; impor gagal tidak merusak data lama; tabel
  akun/log produksi tidak ikut diimpor.
- **Uji:** dump valid/rusak, rollback, kontrol path, peran, audit log, serta
  verifikasi cadangan; uji UI sukses/gagal; lint/tipe/build.
- **Commit:** `feat(import): tambah impor salinan terkontrol [PM-15]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: dump valid/rusak, hash berubah, path traversal, peran, CSRF, rollback saat angka acuan tidak cocok dan ID duplikat, cadangan berisi data lama, akun/log dan riwayat tetap ada; `pytest -q` 231 lulus, 5 dilewati; lint/tipe/format, 29 uji frontend dan build lulus; smoke ZIP hasil ekstraksi tanpa Node melewati impor dan pembaruan arsip; UI browser berhasil pada data contoh dan tidak overflow di viewport 390/820/1440 px | Commit: `3e52b1c` | Catatan: ZIP `output/releases/pm-web-20261123-174759.zip` (SHA-256 `c124e7783bc153f6e89fc2048467a675ff89f3fc65ef827cd6b42ead4cf8fdb8`); default verifikasi angka acuan aktif; sumber hanya dari `PM_IMPORT_DIR`, maksimal 100 MB.

### PM-26 — Finalisasi pemisahan ruang operasional (`/app`) dan ruang penelitian (`/app/research`)

- **Dependensi:** PM-14, PM-18. **PRD:** pemisahan operasional dan penelitian.
- **Selesai saat:** sidebar dan rute `/app` hanya menampilkan menu operasional
  petugas/admin (Dashboard, Pencarian, Detail Arsip, Impor, dan Akun setelah
  PM-21); seluruh alat penelitian terisolasi di `/app/research` dengan sidebar
  tersendiri; menu `Status` tidak berdiri sebagai halaman menu terpisah di
  sidebar operasional (disederhanakan atau dihilangkan dari navigasi utama);
  tidak ada tautan riset di sidebar operasional; rute lama dialihkan aman ke
  `/app/research/*`.
- **Uji:** uji rute dan peran frontend, uji redirect rute lama, cek tampilan
  desktop/tablet/ponsel, lint/tipe/build.
- **Commit:** `refactor(frontend): pisahkan ruang operasional dan penelitian [PM-26]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: `npm run lint`, `npm run typecheck`, `npm test` (37 uji frontend pada 10 berkas lulus), `npm run format:check`, `npm run build` lulus; `python -m pytest -q` 245 lulus, 5 dilewati | Commit: `0e0dedb` | Catatan: ruang `/app` dan `/app/research` terpisah dengan sidebar masing-masing, menu `Status` dihapus dari sidebar operasional (`/app/status` tetap dapat dibuka langsung), dan redirect rute lama mempertahankan query string.

### PM-27 — Matangkan alur Pencarian fuzzy, Dashboard, dan Detail untuk Petugas

- **Dependensi:** PM-26. **PRD:** FR-02, FR-03, FR-04.
- **Selesai saat:** pencarian operasional menggunakan metode fuzzy bawaan yang
  dikonfigurasi di server (bukan lagi default `like`) dan tidak menampilkan
  dropdown pemilihan algoritma riset di halaman pencarian operasional;
  Dashboard menampilkan tautan langsung dari arsip terbaru ke detail arsip
  (`/app/archives/:id`), akses cepat ke pencarian, serta info pembaruan
  data/impor terakhir dari data nyata; Detail arsip menonjolkan lokasi fisik,
  metadata hasil ekstraksi, dan status secara ringkas dan mudah dipindai
  petugas.
- **Uji:** uji API konfigurasi metode bawaan dan respons dashboard, uji
  frontend Dashboard/Pencarian/Detail, cek desktop/tablet/ponsel,
  lint/tipe/build.
- **Commit:** `feat(app): matangkan pencarian fuzzy dan dashboard petugas [PM-27]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: `npm run lint`, `npm run typecheck`, `npm test` (38 uji frontend pada 10 berkas lulus), `npm run format:check`, `npm run build` lulus; `python -m pytest -q` 246 lulus, 5 dilewati | Commit: `ef5ab45` | Catatan: pencarian operasional memakai `levenshtein` sebagai bawaan server atau nilai `app_setting.default_search_method`, dropdown pemilih algoritma dihapus dari `/app/search`, Dashboard menampilkan pencarian cepat, info impor terakhir, dan tautan langsung ke detail arsip, serta Detail Arsip menonjolkan status, berkas digital, dan grid lokasi fisik.

### PM-21 — Administrasi akun dan log aktivitas

- **Dependensi:** PM-02, PM-26. **PRD:** FR-01, P1.
- **Selesai saat:** admin dapat menambah/nonaktifkan/reset akun; tidak dapat
  menonaktifkan dirinya sendiri; tindakan penting masuk log; petugas tidak
  dapat membuka endpoint atau UI admin.
- **Uji:** tiap operasi sukses/gagal, self-disable, 401/403, CSRF, log,
  dan tidak ada kata sandi di respons/log; lint/tipe/build.
- **Commit:** `feat(admin): tambah akun dan log aktivitas [PM-21]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: `npm run lint`, `npm run typecheck`, `npm test` (40 uji frontend pada 11 berkas lulus), `npm run format:check`, `npm run build` lulus; `python -m pytest -q` 250 lulus, 5 dilewati | Commit: `1cd9965` | Catatan: halaman admin `/app/users` (menu `Akun & Log`) dan endpoint `/api/v1/admin/users` serta `/api/v1/admin/activity` mendukung tambah akun, aktif/nonaktif (menolak self-disable 409), reset kata sandi, filter log aktivitas, penolakan petugas/anonim (403/401), CSRF, dan tanpa kebocoran kata sandi di respons maupun log.

## Jalur Ruang Penelitian (`/app/research` — Ruang Pribadi Peneliti)

### PM-16 — Audit ekstraksi dan kamus SPM

- **Dependensi:** PM-02, PM-08. **PRD:** FR-06.
- **Selesai saat:** admin/petugas yang ditugaskan dapat menilai sampel;
  progres dan hasil dihitung dari isian nyata; kode SPM `dugaan` hanya berubah
  setelah konfirmasi tercatat.
- **Uji:** simpan/reload, isian parsial, peran, nilai kosong tidak menjadi
  benar/salah, kesesuaian angka dengan skrip audit; lint/tipe/build.
- **Commit:** `feat(audit): tambah penilaian ekstraksi web [PM-16]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: simpan/reload, koreksi dan hapus verdict, isian parsial dan kosong, isolasi per penilai, penugasan/peran/CSRF, integritas manifest, paritas CSV ekspor dengan skrip audit, konfirmasi SPM dengan bukti; `pytest -q` 235 lulus, 5 dilewati; 32 uji frontend lulus; lint/tipe/format/build lulus; manifest ZIP diverifikasi | Commit: `2a9eb71` | Catatan: ZIP `output/releases/pm-web-pm16.zip` (SHA-256 `3fd5399fe9e81dd59aaf1ad98ed6a3e7a72625ec9ff80f373412cac55a995e98`); sampel dan manifest audit disediakan terpisah melalui `PM_AUDIT_SAMPLE_CSV`/`PM_AUDIT_MANIFEST`; penilaian web baru per akun tidak menyalin verdict dari CSV sumber.

### PM-17 — Kelola versi set uji melalui web

- **Dependensi:** PM-02, PM-08. **PRD:** FR-05/FR-06.
- **Selesai saat:** admin dapat melihat versi/kueri/split dan status kunci;
  perubahan pada versi terkunci ditolak; asal sintetis/nyata terlihat jelas.
- **Uji:** versi terbuka/terkunci, split anti-kebocoran, peran, hash/ekspor,
  dan konsistensi dengan protokol v2; lint/tipe/build.
- **Commit:** `feat(testset): tampilkan dan kunci versi kueri [PM-17]`.
- **Jejak:** Selesai 23 November 2026 | Uji peran/CSRF, ganti draf, konflik hash, kunci, penolakan perubahan, validasi split, dan ekspor kompatibel CLI | 243 uji Python lulus, 5 dilewati, serta 34 uji frontend lulus | Lint, tipe, format, build, manifest ZIP, dan smoke paket ekstraksi lulus dengan set uji penelitian (112 varian, 56 kueri dasar) | Commit `a03b7d6` | Rilis `output/releases/pm-web-pm17.zip`, SHA-256 `72342db3b3435137c3174a3f496d43ae66042edbf9bda766583ce30d20987a02`.

### PM-18 — Penilaian relevansi paperless dua penilai

- **Dependensi:** PM-17, PM-08. **PRD:** FR-06.
- **Selesai saat:** pool buta, penugasan penilai, autosave/penyimpanan aman,
  progres, ragu, dan jejak koreksi tersedia; penilai kedua tidak melihat
  jawaban pertama; aplikasi labeler lama dapat diekspor/migrasi tanpa
  menimpa jawaban yang sudah ada.
- **Uji:** kebutaan data pada API/DOM, dua sesi penilai, reload, konflik
  perubahan, jawaban parsial, ekspor, tablet/ponsel; lint/tipe/build.
- **Commit:** `feat(judgment): tambah penilaian buta dua penilai [PM-18]`.
- **Jejak:** Selesai 23 November 2026 | Uji dua sesi, data buta API/DOM, isian parsial, konflik revisi, koreksi, migrasi tanpa timpa, penguncian penyerahan dan ekspor kompatibel dengan skrip | 245 uji Python lulus, 5 dilewati, 36 uji frontend lulus, lint/tipe/format/build lulus | Chrome headless pada 390 dan 820 px tanpa gulir horizontal, simpan serta reload berhasil | Smoke ZIP dengan data penelitian memverifikasi 119 pasangan unik dari 120 baris, 119 jawaban peneliti dapat diimpor, penilai kedua 0 | Commit `8f270e0` | Rilis `output/releases/pm-web-pm18.zip`, SHA-256 `599ef4f2e460c94d94f817cd81e4164a3e333a986a7d2ad0b01251c36131e4bc`.

### PM-19 — Ringkasan kesepakatan dan status validasi

- **Dependensi:** PM-18. **PRD:** FR-06, ukuran keberhasilan.
- **Selesai saat:** kesepakatan relevansi/audit dihitung dari pasangan isian;
  status tetap tertunda jika sampel belum lengkap; ekspor menyertakan
  penyebut, jumlah kesepakatan, kappa, dan keterbatasan yang sesuai.
- **Uji:** contoh hitung tangan, semua setuju, tak seimbang, kosong,
  sebagian terisi, serta kesesuaian CLI/UI; lint/tipe/build.
- **Commit:** `feat(research): laporkan kesepakatan penilai [PM-19]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: contoh hitung tangan biner & multikelas, semua setuju (`complete_kappa_undefined`), tidak seimbang, kosong, parsial, penundaan sebelum submit, kesesuaian CLI/UI, 401/403/400, ekspor JSON; `python -m pytest -q` 259 lulus, 5 dilewati; `npm run lint`, `npm run typecheck`, `npm test` (42 uji frontend pada 12 berkas lulus), `npm run format:check`, dan `npm run build` lulus | Commit: `e7959ca` | Catatan: fungsi murni di `core/evaluation/agreement.py` dipakai bersama oleh `scripts/evaluate_relevance_agreement.py` dan halaman admin `/app/research/agreement`; halaman dan API kesepakatan hanya terbuka untuk admin.

### PM-20 — Evaluasi dan bukti run di web

- **Dependensi:** PM-17, PM-08. Status final tetap menunggu PM-19.
  **PRD:** FR-05.
- **Selesai saat:** admin melihat run, versi data, parameter, hasil per
  kueri/metode, dan ekspor; UI menandai draft/pending/final sesuai artefak;
  tuning/test tetap terpisah. Grafik hanya dari data yang tersedia.
- **Uji:** run kosong/draft/final, izin admin, angka cocok dengan ekspor CLI,
  uji anti-kebocoran dan tabel alternatif grafik; lint/tipe/build.
- **Commit:** `feat(evaluation): tampilkan run dan metrik terlacak [PM-20]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: contoh hitung tangan agregasi per metode/split, deteksi kebocoran `base_query_id` tuning vs test, pemilihan bobot grid search, status `empty`/`draft`/`pending`/`final`, penolakan kolom sensitif, 401/403/400, ekspor JSON/CSV per split; `python -m pytest -q` 266 lulus, 5 dilewati; `npm run lint`, `npm run typecheck`, `npm test` (46 uji frontend pada 14 berkas lulus), `npm run format:check`, dan `npm run build` lulus | Commit: `32946e8` | Catatan: grafik perbandingan metode memakai `recharts` di `/app/research/evaluation` (lazy-loaded) disertai tabel alternatif aksesibel lengkap; artefak run tetap dibaca dari `PM_EVALUATION_BUNDLE_DIR` (`output/colab_bundle`) dan ditandai `draft` bila `tree_clean = false` atau `pending` bila kesepakatan PM-19 pada artefak belum lengkap.

## Uji Lapangan, Lanjutan Opsional (P2), dan Laporan

### PM-22 — Uji lapangan, UAT, dan SUS

- **Dependensi:** PM-26, PM-27, PM-21 (cakupan operasional). **PRD:** gerbang
  uji petugas.
- **Selesai saat:** daftar tugas uji, peserta aktual, hasil Black Box/UAT,
  kuesioner SUS, dan batas interpretasi tercatat; tidak ada angka contoh
  diperlakukan sebagai hasil. Instrumen tugas dan formulir disiapkan sebelum
  sesi dengan petugas. Data pribadi disimpan di luar Git.
- **Uji/verifikasi:** cocokkan jumlah formulir dengan peserta, hitung ulang
  skor SUS dari jawaban, periksa kegagalan tugas serta masalah yang perlu
  tiket bug, dan pastikan naskah hanya memakai hasil nyata.
- **Commit:** `docs(research): catat metode dan bukti uji petugas [PM-22]`
  hanya untuk ringkasan yang boleh masuk Git; data mentah tetap di luar Git.
- **Jejak:** Status: sedang berjalan — instrumen siap (23 November 2026) | Uji: contoh hitung tangan SUS (100/0/50/82,5), penolakan input tidak sah, ringkasan kosong vs multi-peserta, ringkasan UAT, deteksi selisih peserta UAT/SUS, dan pembuatan template CSV (`tests/test_sus_uat.py`); `python -m pytest -q` 271 lulus, 5 dilewati | Commit: — | Catatan: instrumen tugas `T01`–`T07` & `A01`–`A04` (`docs/instrumen_uat_sus.md`), kalkulator (`core/evaluation/sus.py`), dan skrip (`scripts/evaluate_uat_sus.py`) telah siap; menunggu pelaksanaan sesi petugas aktual dan pengisian berkas CSV di luar Git.

### PM-23 — Tinjauan kualitas metadata

- **Dependensi:** PM-14. **PRD:** P2.
- **Selesai saat:** daftar masalah dan filter kualitas tampil dari data nyata,
  status dugaan jelas, grafik bila ada memiliki tabel alternatif.
- **Uji:** kategori dengan data/kosong, filter, izin, konsistensi hitungan,
  ponsel/tablet, lint/tipe/build.
- **Commit:** `feat(quality): tampilkan masalah metadata [PM-23]`.
- **Jejak:** Status: selesai (23 November 2026) | Uji: keadaan kosong/terisi, konsistensi hitungan cakupan 5 field dan kategori `data_issue`, filter jenis masalah/field/status SPM, paginasi & pilihan jumlah baris, izin admin (401/403), penolakan parameter 400; `python -m pytest -q` 273 lulus, 5 dilewati; `npm run lint`, `npm run typecheck`, `npm test` (48 uji frontend pada 15 berkas lulus), `npm run format:check`, dan `npm run build` lulus | Commit: `8fadc48` | Catatan: halaman admin `/app/research/quality` (lazy-loaded) menampilkan cakupan metadata via grafik batang `recharts` + tabel alternatif aksesibel serta menegaskan pemisahan kode SPM `dugaan`.

### PM-24 — Tinjauan kandidat duplikat

- **Dependensi:** PM-14. **PRD:** P2.
- **Selesai saat:** pasangan kandidat dibandingkan berdampingan dan dapat
  diberi keputusan dengan jejak penilai; tidak ada operasi hapus/gabung otomatis.
- **Uji:** kandidat sama/berbeda, keputusan dan koreksi, izin, daftar kosong,
  tidak ada perubahan arsip sumber, ponsel/tablet, lint/tipe/build.
- **Commit:** `feat(duplicates): tambah tinjauan kandidat [PM-24]`.
- **Jejak:** Status: selesai (24 November 2026) | Uji: deteksi kandidat sama/berbeda (`same_spm`, `same_summary`, `same_amount_opd_year`), daftar kosong, simpan dan koreksi keputusan dengan riwayat audit + `activity_log`, CSRF/401/403/422, serta verifikasi tabel `archive`/`archive_metadata` tetap utuh; `python -m pytest -q` 278 lulus, 5 dilewati; `npm run lint`, `npm run typecheck`, `npm test` (50 uji frontend pada 16 berkas lulus), `npm run format:check`, dan `npm run build` lulus | Commit: `594aa70` | Catatan: halaman admin `/app/research/duplicates` (lazy-loaded) bersifat non-destruktif dan tidak melakukan operasi hapus maupun gabung arsip otomatis.

### PM-25 — Selaraskan bukti implementasi untuk laporan

- **Dependensi:** PM-14, PM-19, PM-20, PM-22; PM-23/24 bila digunakan.
- **Selesai saat:** daftar teknologi, diagram, screenshot, jumlah kueri,
  metrik, batasan sintetis, kesepakatan, dan SUS cocok dengan kode/artefak
  final. Bab V tidak lagi memuat isi dari penelitian lain. Perubahan berkas
  laporan dilakukan hanya bila pengguna memintanya.
- **Uji/verifikasi:** telusuri tiap klaim ke commit, run, tabel sumber,
  formulir, atau screenshot; audit angka dan placeholder; cek Bab I–V
  konsisten dan hasil tidak melampaui bukti.
- **Commit:** `docs(research): selaraskan bukti implementasi [PM-25]` untuk
  catatan proyek yang aman masuk Git; berkas Word di folder lain tidak
  dimasukkan ke commit PM.
- **Jejak:** Status: sedang berjalan — bukti proyek tersinkron (24 November 2026) | Uji: angka dan hash ditelusuri langsung ke `output/colab_bundle/` (`run_meta.json`, `per_query_results.csv`, `tuning_results.csv`, `audit_summary.json`), rilis `output/releases/pm-web-20261124-080825.zip` (SHA-256 `e20df9a2a4bb8956fcb9b4cb12bfdff09ae96b3cd14041e678c8d22417a7ca6b`), `pytest -q` 278 lulus / 5 dilewati, dan 50 uji frontend lulus | Commit: — | Catatan: daftar teknologi, rute, metrik `draft`, dan status keterbatasan dicatat pada `docs/bukti_implementasi.md` serta `README.md`; pembaruan naskah Bab I–V menunggu kelengkapan data aktual `PM-19` (penilai kedua) dan `PM-22` (UAT/SUS) serta permintaan pengguna.

## Pengumpulan Data Paperless Berbasis Tautan (Token 1-Perangkat)

### PM-28 — Formulir kuesioner publik & tautan kunci 1 perangkat (SUS & kuesioner kustom)

- **Dependensi:** PM-22, PM-08. **PRD:** pengumpulan data UAT/SUS tanpa login.
- **Rancangan keamanan & mekanisme akses:**
  - Setiap tautan memakai token acak panjang (`secrets.token_urlsafe(24)`) yang
    terikat ke **1 peserta anonim** (mis. `P01`–`P05`) tanpa meminta nama,
    NIP, maupun akun login.
  - Saat tautan pertama kali dibuka oleh peserta, server mengklaimnya ke
    perangkat tersebut dengan menanam cookie `HttpOnly` berisi rahasia klaim
    yang hash-nya (`SHA-256`) disimpan di SQLite (*device-claim binding*),
    sehingga tetap stabil saat IP seluler berpindah jaringan namun menolak
    perangkat/browser lain (`403 — Tautan sudah diklaim perangkat lain`).
  - Admin dapat melihat status tiap tautan (*Belum dibuka / Terkunci di
    perangkat / Sudah dikirim / Dicabut*), menjalankan **Reset kunci
    perangkat** jika peserta terhapus cookie-nya, atau **Cabut tautan** kapan
    saja. Tautan otomatis selesai setelah 1 kali kirim.
- **Selesai saat:**
  - Admin di `/app/research/forms` dapat membuat formulir dari **Template SUS
    10 Butir + Catatan UAT** atau membuat **kuesioner kustom** (pertanyaan skala
    1–5, pilihan ganda, atau teks), lalu men-*generate* tautan publik berulang
    (satu tautan per responden).
  - Peserta membuka `/f/:token` pada tampilan publik bersih *mobile-first*
    tanpa sidebar maupun login, mengisi jawaban, dan mengirim sekali.
  - Rekap jawaban tampil langsung di halaman admin, skor SUS dihitung otomatis
    memakai `core/evaluation/sus.py`, serta tersedia ekspor CSV/JSON anonim.
- **Uji:** klaim perangkat pertama, penolakan perangkat kedua (`403`), reset
  kunci perangkat oleh admin, pencabutan tautan, validasi kuesioner & kirim
  sekali (tolak kirim ulang), perhitungan ulang SUS, izin admin (`401`/`403`)
  vs akses publik token, serta tampilan responsif ponsel/desktop;
  lint/tipe/build.
- **Commit:** `feat(forms): tambah kuesioner publik dan tautan kunci perangkat [PM-28]`.
- **Jejak:** Status: selesai (24 November 2026) | Uji: `.\.venv\Scripts\python.exe -m pytest -q` (`280 passed, 5 skipped`), `npm run lint` (`oxlint src`: 0 warnings, 0 errors pada 129 berkas), `npm run typecheck`, `npm test` (53 uji pada 17 berkas lulus), `npm run format:check`, dan `npm run build` | Commit: `348d782` | Catatan: tabel baru (`survey_form`, `public_form_link`, `survey_response`) ditambahkan secara non-destruktif; jalankan `flask --app wsgi db upgrade` pada server produksi sebelum membuka fitur ini.

### PM-29 — Tautan 1-perangkat untuk penilaian relevansi & audit ekstraksi

- **Dependensi:** PM-28, PM-18, PM-16. **PRD:** FR-06 (akses penilai eksternal tanpa akun login).
- **Rancangan keamanan & mekanisme akses:**
  - Memperluas mekanisme token acak + kunci 1 perangkat (*device-claim cookie
    `HttpOnly`*) dari PM-28 agar admin dapat menerbitkan tautan langsung bagi
    penilai untuk tugas **Penilaian relevansi** atau **Audit ekstraksi 5 field**
    yang menampilkan data arsip/ringkasan asli.
  - Setiap tautan terikat ketat ke **1 slot penilai relevansi** (khususnya
    Penilai 2) atau **1 akun/kode penilai audit ekstraksi**; tetap menjaga
    kebutaan data (penilai tidak melihat skor metode, tipe noise, maupun
    jawaban penilai lain).
  - Mendukung autosave/simpan parsial dan koreksi selama dalam sesi klaim
    perangkat yang sama, mencatat seluruh perubahan ke riwayat audit atas nama
    penilai/token terkait, dan **otomatis kedaluwarsa/hangus** setelah penilai
    menekan tombol penyerahan final.
- **Selesai saat:** admin dapat menerbitkan, memantau, mereset klaim
  perangkat, atau mencabut tautan penilai relevansi & audit ekstraksi dari
  `/app/research`; penilai mengisi penuh melalui `/f/:token` pada ponsel maupun
  laptop tanpa login; ekspor CSV/perhitungan kesepakatan (`PM-19`) membaca
  jawaban tersebut secara identik dengan pengisian via akun login.
- **Uji:** klaim perangkat pertama, blokir perangkat lain (`403`), isolasi/kebutaan
  data pada API & DOM, simpan parsial + koreksi + penyerahan final mengunci
  tautan, reset & cabut tautan oleh admin, izin & CSRF, serta paritas ekspor
  dan kesepakatan PM-19; lint/tipe/build.
- **Commit:** `feat(research): tambah tautan satu perangkat untuk relevansi dan audit [PM-29]`.
- **Jejak:** Status: selesai (24 November 2026) | Uji: `.\.venv\Scripts\python.exe -m pytest -q` (`283 passed, 5 skipped`), `npm run lint` (`oxlint src`: 0 warnings, 0 errors pada 135 berkas), `npm run typecheck`, `npm test` (57 uji pada 18 berkas lulus), `npm run format:check`, dan `npm run build` | Commit: `2c6c448` | Catatan: tabel `public_task_link` ditambahkan secara non-destruktif; jalankan `flask --app wsgi db upgrade` di server produksi dan bangun ulang paket rilis jika men-deploy pembaruan PM-28/PM-29.

## Pemetaan cakupan PRD

| Kebutuhan | Tiket |
|---|---|
| FR-01 sesi dan peran | PM-01, PM-02, PM-08, PM-21 |
| FR-02 dashboard | PM-03, PM-09, PM-27 |
| FR-03 pencarian | PM-04, PM-10, PM-27 |
| FR-04 detail dan lokasi | PM-05, PM-11, PM-27 |
| FR-05 perbandingan/evaluasi | PM-06, PM-12, PM-17, PM-20 |
| FR-06 audit dan penilaian | PM-16, PM-18, PM-19 |
| FR-07 impor dan keamanan data | PM-15 |
| Pemisahan ruang operasional & penelitian | PM-26 |
| Portabilitas, aksesibilitas, responsif | PM-07–PM-14, diperiksa lagi di tiap fitur UI |
| UAT/SUS dan laporan | PM-22, PM-25 |
| Pengumpulan data paperless (tautan 1-perangkat) | PM-28, PM-29 |

**Urutan aktif fokus pengguna operasional:** `PM-26 → PM-27 → PM-21 → PM-22`.
Tiket ruang penelitian (`PM-19`, `PM-20`) dan P2 (`PM-23`, `PM-24`) dipisahkan
serta ditunda hingga jalur operasional siap dan kebutuhan UI webnya ditinjau
ulang terhadap skrip CLI.
