# PRD — Sistem Pencarian Arsip SIMANIS

**Status:** dokumen kebutuhan produk untuk pengembangan dan penelitian; bukan bukti
bahwa seluruh fitur telah selesai.

**Diperbarui:** 21 November 2026.
**Dokumen terkait:** [arsitektur Flask–React](arsitektur_flask_react.md),
[kontrak API](api_contract.md),
[rancangan aplikasi](../rancangan_aplikasi.md),
[backlog tiket](BACKLOG.md),
[protokol set uji](protokol_testset_v2.md), dan
[pedoman relevansi](pedoman_penilaian_relevansi.md).

## 1. Masalah dan tujuan

Petugas perlu menemukan arsip ketika informasi pemohon tidak lengkap, memiliki
variasi ejaan, salah ketik, atau hanya memuat potongan nomor surat. Pada salinan
data SIMANIS, atribut penting juga tertanam dalam teks ringkasan yang tidak
seragam. Penelitian ini membangun aplikasi pencarian pada **salinan data**, lalu
mengukur apakah normalisasi metadata dan fuzzy matching membantu temu kembali
dibanding pembanding LIKE yang didefinisikan dalam protokol penelitian.

Tujuan produk:

1. Petugas dapat mencari, memeriksa kecocokan, dan menemukan informasi lokasi
   arsip tanpa harus memahami algoritma pencarian.
2. Peneliti/admin dapat mengaudit ekstraksi dan mengevaluasi metode secara
   terlacak, termasuk kasus ketika metode baru tidak lebih baik.
3. Penilaian relevansi oleh petugas dapat dilakukan secara paperless dan buta
   terhadap nama metode, skor, peringkat, serta arsip asal.
4. Aplikasi uji dapat berjalan di intranet dengan Python/Waitress dan aset
   frontend lokal, tanpa bergantung pada Node.js atau internet saat digunakan.

## 2. Pengguna, peran, dan batas sistem

| Pengguna | Kebutuhan utama | Hak akses target |
|---|---|---|
| Petugas arsip | Mencari dan melihat arsip serta lokasi fisiknya; membantu audit/penilaian | Pencarian bawaan, detail, formulir penilaian yang ditugaskan |
| Admin/peneliti | Menyiapkan salinan data dan set uji; menguji serta mengekspor hasil | Semua fungsi petugas, perbandingan metode, impor, konfigurasi, evaluasi, akun, log |
| Pengelola TI dinas | Menilai kemungkinan menjalankan aplikasi di lingkungan dinas | Tidak diasumsikan sebagai pengguna aplikasi penelitian; persetujuan dan persyaratan instalasi ditentukan bersama |

Jumlah peserta UAT/SUS mengikuti petugas yang benar-benar menggunakan SIMANIS
dan bersedia ikut uji; perkiraan sekitar lima orang **bukan** hasil rekrutmen.
Tidak ada koneksi tulis ke SIMANIS produksi. Sistem tidak mengubah SOP layanan,
tidak menghapus arsip, dan tidak menjanjikan siap produksi dinas sebelum
persyaratan TI serta keamanan diperiksa.

## 3. Status yang benar pada saat PRD dibuat

| Komponen | Status |
|---|---|
| Pipeline normalisasi, ekstraksi, pencarian, dan evaluasi CLI/notebook | Ada di proyek; hasil ilmiah mengikuti artefak dan protokol aktif |
| Web utama: login, dashboard, pencarian, perbandingan admin, detail arsip | Ada dalam Flask/Jinja sebagai fondasi; belum setara semua halaman rancangan |
| Aplikasi pelabelan relevansi internal | Ada di `scripts/relevance_labeler_app.py`; terpisah dari web utama |
| Flask JSON API `/api/v1` dan frontend React | API P0 untuk sesi, dashboard, pencarian, detail, dan perbandingan admin sudah ada; login/dashboard/status/pencarian React sudah ada, sedangkan halaman detail/perbandingan React masih target |
| Impor, audit, set uji, evaluasi, dan administrasi melalui web utama | Target; jangan ditandai selesai berdasarkan adanya skrip CLI |
| Verifikasi penilai kedua, kesepakatan audit, UAT/SUS petugas | Menunggu pengumpulan/penilaian nyata; tidak boleh diberi hasil contoh |

Set uji aktif memuat **112 varian kueri sintetis** dari **56 kueri dasar**:
32 varian tuning dan 80 varian test. Status dan angka ini adalah deskripsi
berkas `data/testset/testset_v1.json`, bukan klaim validitas eksternal.
Kueri nyata dari petugas belum tersedia; keterbatasan ini harus ditampilkan
di hasil penelitian.

## 4. Lingkup dan prioritas

### P0 — Alur pencarian dan fondasi migrasi

- Flask menyajikan endpoint JSON versi `/api/v1` untuk sesi, dashboard,
  pencarian, detail, dan perbandingan admin. Semua memakai `services/` dan
  `core/` yang sama dengan CLI.
- React + TypeScript menyajikan login, dashboard, pencarian, detail arsip, dan
  perbandingan admin pada desktop, tablet, serta ponsel.
- Hasil build Vite disajikan oleh Flask/Waitress. Paket uji tetap berfungsi
  tanpa proses Node.js, CDN, atau internet.
- Alur Flask/Jinja yang sudah ada tetap dapat dipakai sampai paritas P0 terbukti.

### P1 — Kelengkapan penelitian dan pengelolaan

- Admin dapat menyiapkan impor salinan data, memeriksa audit ekstraksi,
  mengelola set uji/penilaian, menjalankan evaluasi, melihat run, dan mengunduh
  artefak yang sudah dihasilkan sistem. Modul yang belum mempunyai backend
  tidak ditampilkan seolah berfungsi.
- Petugas dapat menilai pasangan kueri–arsip tanpa nama metode atau skor.
  Penilaian kedua disimpan terpisah agar kesepakatan dihitung dari keputusan
  independen, bukan menimpa penilaian pertama.
- Admin dapat mengelola akun lokal dan melihat log tindakan yang relevan.

### P2 — Pengembangan lanjutan

- Daftar masalah mutu data dan kandidat duplikat untuk ditinjau manusia.
  Penanda kandidat tidak otomatis menghapus atau menyatukan arsip.
- Grafik evaluasi atau mutu data hanya muncul jika datanya tersedia dan
  menyertakan tabel angka sebagai alternatif.

## 5. Kebutuhan fungsional dan kriteria penerimaan

### FR-01 — Masuk dan peran

- Pengguna masuk dengan akun lokal. Kata sandi tidak disimpan dalam teks biasa.
- Sesi yang tidak sah menghasilkan **401 JSON** pada API; akun tanpa hak
  menghasilkan **403 JSON**. React menampilkan pesan yang tepat.
- Peran ditegakkan di backend pada setiap endpoint. Operasi tulis memerlukan
  CSRF; keluar mengakhiri sesi. Login gagal tidak mengungkap keberadaan akun.

### FR-02 — Dashboard

- Petugas melihat jumlah arsip dan status data yang dihitung dari salinan
  database. Setiap angka menyebut konteksnya; tidak ada statistik contoh.
- Keadaan database kosong atau gagal dibuka ditampilkan jelas tanpa crash UI.

### FR-03 — Pencarian

- Pengguna memasukkan kueri dan dapat menyaring OPD, tahun, serta status bila
  datanya ada. Masukan kosong, terlalu panjang, atau filter tidak valid ditangani.
- Petugas memakai metode bawaan yang dikonfigurasi; admin dapat memilih metode
  untuk analisis. Kebijakan pilihan metode harus sama di UI dan API.
- Hasil menampilkan ringkasan, metadata yang tersedia, lokasi, dan penjelasan
  skor bila relevan. Field yang tidak berhasil diekstrak ditandai, bukan diisi
  nilai rekaan. Teks yang cocok disorot tanpa menyisipkan HTML mentah.
- Nol hasil memberi saran pencarian ulang. Hasil panjang dibatasi/paginasi
  secara eksplisit; navigasi keyboard dan sentuhan tetap berfungsi.

### FR-04 — Detail dan lokasi arsip

- Detail memperlihatkan teks ringkasan asli, atribut hasil ekstraksi, status
  dugaan/terkonfirmasi, serta informasi lokasi fisik yang tersedia.
- ID yang tidak ada menghasilkan 404. Informasi yang kosong diberi label yang
  jelas; tidak diasumsikan berkas digital atau lokasi fisik pasti tersedia.

### FR-05 — Perbandingan dan evaluasi

- Hanya admin dapat membandingkan hasil beberapa metode untuk kueri yang sama.
- UI evaluasi membaca run dan artefak yang benar-benar ada; menampilkan versi
  data/set uji, konfigurasi, waktu, dan status validasi.
- Tuning tidak membaca test split. Evaluasi akhir mengikuti protokol set uji
  yang aktif; nilai metrik dan ketidakpastiannya dihitung skrip, bukan frontend.

### FR-06 — Audit dan penilaian paperless

- Penilai melihat kueri dasar/kebutuhan informasi dan teks arsip yang diperlukan
  menurut rubrik. Nama metode, skor, peringkat, dan penanda arsip asal disembunyikan.
- Setiap keputusan relevan/tidak relevan memiliki identitas penilai, waktu,
  versi set uji, dan riwayat koreksi. Keputusan ragu dapat dicatat.
- Progres dihitung dari data yang tersimpan; penyegaran halaman tidak
  menghilangkan jawaban. Penilai kedua tidak melihat jawaban penilai pertama.
- Ringkasan kesepakatan hanya berstatus final bila seluruh sampel kedua terisi.
  Saat belum lengkap, UI dan ekspor menampilkan status tertunda.

### FR-07 — Impor dan keamanan data

- Impor hanya membaca berkas dump yang dipilih admin dari lokasi yang
  diizinkan; parser tidak memasukkan tabel akun/log produksi.
- Kegagalan impor tidak merusak salinan sebelumnya. Jejak sumber, hash, waktu,
  versi parser, dan jumlah baris dicatat. Database dicadangkan sebelum impor ulang.
- Tidak ada endpoint untuk menghapus arsip fisik atau menulis ke SIMANIS.

## 6. Kebutuhan nonfungsional

| Bidang | Kriteria penerimaan |
|---|---|
| Keamanan | Cookie sesi HttpOnly/SameSite, Secure pada HTTPS; CSRF pada operasi tulis; SQL terparameterisasi; izin diperiksa server; galat tanpa stack trace/data rahasia |
| Privasi | Dump, SQLite, CSV penilaian, dan `.env` tidak masuk Git atau aset frontend; respons API memuat data minimum yang diperlukan |
| Portabilitas | Paket build berjalan di komputer Windows uji dengan Python/Waitress tanpa Node.js atau akses CDN; XAMPP/PHP bukan syarat runtime |
| Aksesibilitas | Label formulir, fokus terlihat, kontras memadai, status tidak hanya berupa warna, interaksi keyboard dan target sentuh yang dapat digunakan |
| Responsif | Alur utama diuji di desktop, tablet, dan ponsel; tabel lebar boleh bergulir di kontainernya, bukan merusak tata letak halaman |
| Keandalan | Error, loading, kosong, sesi habis, dan pemulihan dari gangguan jaringan memiliki tampilan jelas; perubahan data penting dapat diaudit |
| Kinerja | Latensi pencarian dan render diukur pada perangkat uji yang dicatat; tidak membuat klaim kecepatan tanpa pengukuran |
| Reproduksibilitas | Evaluasi menyimpan seed, versi/hashes data dan set uji, konfigurasi, kode, serta status working tree sebagaimana protokol aktif |

## 7. Arsitektur dan pilihan library

Flask adalah pemilik API, sesi, izin, validasi, SQLite, dan logika domain melalui
`services/` serta `core/`. React hanya menangani tampilan dan interaksi.
Frontend ditulis dengan TypeScript `strict`, dibangun oleh Vite, dan memakai
React Router, TanStack Query, React Hook Form + Zod, Tailwind CSS,
shadcn/ui (basis Radix) untuk komponen bersama, Lucide React, serta Recharts untuk grafik yang
benar-benar ada. Daftar alasan, struktur kode, dan kontrak HTTP rinci berada
di [dokumen arsitektur](arsitektur_flask_react.md). AI mengikuti
[`AGENTS.md`](../AGENTS.md) dan panduan gaya kode proyek.

## 8. Ukuran keberhasilan penelitian dan produk

- **Temu kembali:** P@5, R@10, MRR@10, Hit@10, hasil nol, dan latensi
  dilaporkan untuk split test sesuai protokol. Perbandingan dengan LIKE
  disajikan apa adanya, termasuk interval ketidakpastian dan kegagalan.
- **Ekstraksi:** cakupan serta ketepatan per atribut dihitung dari audit yang
  terisi, dengan batasan sampel dijelaskan.
- **Kesepakatan penilai:** persentase kesepakatan dan Cohen's kappa dihitung
  setelah sampel kedua lengkap; angka kosong tidak diubah menjadi nol.
- **Kegunaan:** Black Box/UAT dan SUS dilakukan pada aplikasi yang benar-benar
  dipakai petugas; jumlah peserta, tugas, jawaban, dan skor dicatat apa adanya.
- **Kesiapan paket:** alur P0 berfungsi dari hasil build melalui Waitress tanpa
  Node.js atau internet saat runtime.

Tidak ada target skor SUS, akurasi, atau peningkatan MRR yang ditetapkan untuk
"meluluskan" penelitian. Keberhasilan penelitian berarti metode dan hasil
dapat diperiksa, termasuk hasil yang tidak mendukung hipotesis.

## 9. Gerbang rilis dan pekerjaan yang menunggu pihak luar

1. **Fondasi P0:** kontrak API dan uji status/izin, alur React utama, build,
   pengemasan aset, dan uji offline pada ukuran layar utama lulus.
2. **Evaluasi ilmiah:** seluruh keputusan relevansi yang dibutuhkan dan audit
   yang disyaratkan protokol tersedia; run final ditautkan ke data dan kode.
3. **Uji petugas:** rubrik disepakati, penilai kedua bekerja independen,
   tugas UAT/SUS dijalankan, lalu hasilnya dihitung tanpa nilai contoh.
4. **Penempatan di dinas:** pengelola TI mengonfirmasi lingkungan, izin,
   kebijakan jaringan, dan data sebelum instalasi. PRD ini tidak menganggap
   XAMPP lama dapat langsung menjalankan Flask.

Hal yang perlu dikonfirmasi saat bertemu petugas: jumlah petugas pengguna
SIMANIS yang akan ikut uji; contoh kueri kasus nyata yang boleh dicatat;
kesesuaian rubrik relevansi; serta format bukti/hasil yang dapat disimpan.
Persyaratan server dan akses jaringan dibahas terpisah dengan pengelola TI.
