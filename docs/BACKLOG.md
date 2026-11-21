# Backlog tiket — Flask API + React dan penelitian arsip

Sumber kebutuhan: [PRD](PRD.md), [arsitektur](arsitektur_flask_react.md),
[protokol set uji](protokol_testset_v2.md). Dokumen ini adalah daftar kerja,
bukan laporan fitur yang sudah selesai. **Status awal seluruh tiket di bawah:
belum dimulai.** Fondasi Flask/Jinja dan skrip CLI yang sudah ada dipakai ulang,
tetapi tidak otomatis membuat tiket migrasi berstatus selesai.

## Cara memakai backlog

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
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-11 — Detail arsip React

- **Dependensi:** PM-05, PM-08. **PRD:** FR-04.
- **Selesai saat:** detail memperlihatkan teks asli, metadata, lokasi, dan
  label kekosongan/dugaan; navigasi kembali ke hasil pencarian tetap jelas.
- **Uji:** data penuh/sebagian kosong, 404, 401, tampilan ponsel/tablet,
  keyboard, lint, tipe, build.
- **Commit:** `feat(frontend): tampilkan detail dan lokasi arsip [PM-11]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-12 — Perbandingan metode React

- **Dependensi:** PM-06, PM-08. **PRD:** FR-05.
- **Selesai saat:** admin dapat membandingkan hasil metode dengan label dan
  urutan jelas; petugas mendapat 403 dan tidak melihat menu admin.
- **Uji:** hasil kosong/berisi/error, peran admin/petugas, tabel pada layar
  sempit, lint, tipe, build.
- **Commit:** `feat(frontend): tampilkan perbandingan metode [PM-12]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

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
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-14 — Uji paritas dan rapikan UI Jinja lama

- **Dependensi:** PM-13. **PRD:** gerbang P0.
- **Selesai saat:** alur P0 React setara atau lebih baik dari Jinja; route,
  template, CSS, dan ikon lama yang tidak terpakai dihapus secara terukur;
  README memuat cara menjalankan versi baru.
- **Uji:** regresi Flask dan frontend, alur login–cari–detail–banding,
  desktop/tablet/ponsel, keyboard; bandingkan hasil pencarian sebelum/sesudah.
- **Commit:** `refactor(web): hapus antarmuka Jinja yang terganti [PM-14]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

## Tiket fitur penelitian dan pengelolaan

### PM-15 — Impor salinan data melalui web

- **Dependensi:** PM-02, PM-08. **PRD:** FR-07.
- **Selesai saat:** admin memilih dump dari lokasi yang diizinkan, melihat
  pratinjau/hasil dan riwayat; impor gagal tidak merusak data lama; tabel
  akun/log produksi tidak ikut diimpor.
- **Uji:** dump valid/rusak, rollback, kontrol path, peran, audit log, serta
  verifikasi cadangan; uji UI sukses/gagal; lint/tipe/build.
- **Commit:** `feat(import): tambah impor salinan terkontrol [PM-15]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-16 — Audit ekstraksi dan kamus SPM

- **Dependensi:** PM-02, PM-08. **PRD:** FR-06.
- **Selesai saat:** admin/petugas yang ditugaskan dapat menilai sampel;
  progres dan hasil dihitung dari isian nyata; kode SPM `dugaan` hanya berubah
  setelah konfirmasi tercatat.
- **Uji:** simpan/reload, isian parsial, peran, nilai kosong tidak menjadi
  benar/salah, kesesuaian angka dengan skrip audit; lint/tipe/build.
- **Commit:** `feat(audit): tambah penilaian ekstraksi web [PM-16]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-17 — Kelola versi set uji melalui web

- **Dependensi:** PM-02, PM-08. **PRD:** FR-05/FR-06.
- **Selesai saat:** admin dapat melihat versi/kueri/split dan status kunci;
  perubahan pada versi terkunci ditolak; asal sintetis/nyata terlihat jelas.
- **Uji:** versi terbuka/terkunci, split anti-kebocoran, peran, hash/ekspor,
  dan konsistensi dengan protokol v2; lint/tipe/build.
- **Commit:** `feat(testset): tampilkan dan kunci versi kueri [PM-17]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-18 — Penilaian relevansi paperless dua penilai

- **Dependensi:** PM-17, PM-08. **PRD:** FR-06.
- **Selesai saat:** pool buta, penugasan penilai, autosave/penyimpanan aman,
  progres, ragu, dan jejak koreksi tersedia; penilai kedua tidak melihat
  jawaban pertama; aplikasi labeler lama dapat diekspor/migrasi tanpa
  menimpa jawaban yang sudah ada.
- **Uji:** kebutaan data pada API/DOM, dua sesi penilai, reload, konflik
  perubahan, jawaban parsial, ekspor, tablet/ponsel; lint/tipe/build.
- **Commit:** `feat(judgment): tambah penilaian buta dua penilai [PM-18]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-19 — Ringkasan kesepakatan dan status validasi

- **Dependensi:** PM-18. **PRD:** FR-06, ukuran keberhasilan.
- **Selesai saat:** kesepakatan relevansi/audit dihitung dari pasangan isian;
  status tetap tertunda jika sampel belum lengkap; ekspor menyertakan
  penyebut, jumlah kesepakatan, kappa, dan keterbatasan yang sesuai.
- **Uji:** contoh hitung tangan, semua setuju, tak seimbang, kosong,
  sebagian terisi, serta kesesuaian CLI/UI; lint/tipe/build.
- **Commit:** `feat(research): laporkan kesepakatan penilai [PM-19]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-20 — Evaluasi dan bukti run di web

- **Dependensi:** PM-17, PM-08. Status final tetap menunggu PM-19.
  **PRD:** FR-05.
- **Selesai saat:** admin melihat run, versi data, parameter, hasil per
  kueri/metode, dan ekspor; UI menandai draft/pending/final sesuai artefak;
  tuning/test tetap terpisah. Grafik hanya dari data yang tersedia.
- **Uji:** run kosong/draft/final, izin admin, angka cocok dengan ekspor CLI,
  uji anti-kebocoran dan tabel alternatif grafik; lint/tipe/build.
- **Commit:** `feat(evaluation): tampilkan run dan metrik terlacak [PM-20]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-21 — Administrasi akun dan log aktivitas

- **Dependensi:** PM-02, PM-08. **PRD:** FR-01, P1.
- **Selesai saat:** admin dapat menambah/nonaktifkan/reset akun; tidak dapat
  menonaktifkan dirinya sendiri; tindakan penting masuk log; petugas tidak
  dapat membuka endpoint atau UI admin.
- **Uji:** tiap operasi sukses/gagal, self-disable, 401/403, CSRF, log,
  dan tidak ada kata sandi di respons/log; lint/tipe/build.
- **Commit:** `feat(admin): tambah akun dan log aktivitas [PM-21]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-22 — Uji lapangan, UAT, dan SUS

- **Dependensi:** PM-14 dan fitur yang menjadi cakupan uji. **PRD:** gerbang
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
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

## Tiket lanjutan dan laporan

### PM-23 — Tinjauan kualitas metadata

- **Dependensi:** PM-14. **PRD:** P2.
- **Selesai saat:** daftar masalah dan filter kualitas tampil dari data nyata,
  status dugaan jelas, grafik bila ada memiliki tabel alternatif.
- **Uji:** kategori dengan data/kosong, filter, izin, konsistensi hitungan,
  ponsel/tablet, lint/tipe/build.
- **Commit:** `feat(quality): tampilkan masalah metadata [PM-23]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

### PM-24 — Tinjauan kandidat duplikat

- **Dependensi:** PM-14. **PRD:** P2.
- **Selesai saat:** pasangan kandidat dibandingkan berdampingan dan dapat
  diberi keputusan dengan jejak penilai; tidak ada operasi hapus/gabung otomatis.
- **Uji:** kandidat sama/berbeda, keputusan dan koreksi, izin, daftar kosong,
  tidak ada perubahan arsip sumber, ponsel/tablet, lint/tipe/build.
- **Commit:** `feat(duplicates): tambah tinjauan kandidat [PM-24]`.
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

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
- **Jejak:** Status: belum dimulai | Uji: — | Commit: — | Catatan: —

## Pemetaan cakupan PRD

| Kebutuhan | Tiket |
|---|---|
| FR-01 sesi dan peran | PM-01, PM-02, PM-08, PM-21 |
| FR-02 dashboard | PM-03, PM-09 |
| FR-03 pencarian | PM-04, PM-10 |
| FR-04 detail dan lokasi | PM-05, PM-11 |
| FR-05 perbandingan/evaluasi | PM-06, PM-12, PM-17, PM-20 |
| FR-06 audit dan penilaian | PM-16, PM-18, PM-19 |
| FR-07 impor dan keamanan data | PM-15 |
| Portabilitas, aksesibilitas, responsif | PM-07–PM-14, diperiksa lagi di tiap fitur UI |
| UAT/SUS dan laporan | PM-22, PM-25 |

**Urutan minimum untuk aplikasi React yang dapat diuji:** PM-00 → PM-01/02/07
→ PM-03/04/05/06 → PM-08/09/10/11/12 → PM-13 → PM-14. Tiket P1 dapat
dikerjakan bertahap setelah fondasi API dan UI tersedia; P2 tetap opsional
hingga kebutuhan utama dan bukti penelitian lengkap.
