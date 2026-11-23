# Kontrak HTTP API Flask untuk React

**Status:** fondasi PM-01 dan endpoint P0 PM-02 sampai PM-06 sudah
diimplementasikan. Dokumen ini diperbarui bersama
implementasi tiap tiket, bukan bukti bahwa endpoint target sudah tersedia.

## Versi, origin, dan bentuk respons

- Semua endpoint aplikasi memakai `/api/v1`. Frontend dan Flask berada pada
  origin yang sama saat produksi; Vite memakai proxy `/api` saat pengembangan.
- Respons sukses: `{"data": ...}`. Objek daftar menaruh `items` dan
  `pagination` di dalam `data`. Jangan mencampur HTML ke respons API.
- Respons gagal: `{"error": {"code": "kode_stabil", "message": "pesan"}}`.
  `message` aman untuk pengguna; detail teknis masuk log server.
- Tipe konten JSON adalah `application/json`. Metode yang salah mengembalikan
  405 dan header `Allow`; path `/api/*` yang tidak ada mengembalikan 404 JSON,
  bukan halaman login atau fallback React.

| HTTP | Makna | `error.code` |
|---|---|---|
| 400 | Parameter/format permintaan tidak valid | `bad_request` |
| 401 | Belum masuk atau sesi habis | `unauthorized` |
| 403 | Tidak berhak mengakses | `forbidden` |
| 404 | Sumber tidak ditemukan | `not_found` |
| 405 | Metode HTTP tidak tersedia | `method_not_allowed` |
| 409 | Konflik perubahan/versi data | `conflict` |
| 422 | Isi JSON lolos parse tetapi melanggar aturan field | `validation_error` |
| 500 | Kesalahan server | `server_error`; pesan umum tanpa rincian internal |

Contoh respons yang **sudah ada**:

```http
GET /api/v1/health
200 application/json
{"data":{"status":"ok"}}
```

Pemeriksaan health hanya memastikan HTTP aplikasi menjawab. Ia tidak
menyatakan database atau seluruh fitur penelitian siap.

### Sesi yang sudah tersedia (PM-02)

`GET /api/v1/session` dapat dipanggil sebelum login. Respons berisi
`{"data":{"authenticated":false,"user":null,"csrf_token":"..."}}`.
Setelah login, `user` hanya berisi `id`, `username`, dan `role` (`admin` atau
`petugas`). Token CSRF berasal dari sesi browser; jangan menyimpannya di
`localStorage`. Endpoint ini dan semua respons sesi memakai `Cache-Control:
no-store`.

`POST /api/v1/session` menerima JSON `{"username":"...","password":"..."}`
dan header `X-CSRF-Token` dari GET sesi. Respons berhasil berisi bentuk data
GET sesi dengan token CSRF **baru**. Kredensial salah atau akun nonaktif memberi
401 dengan pesan umum; JSON rusak memberi 400; field kosong/tipe salah memberi
422; token CSRF hilang/salah memberi 403.

`DELETE /api/v1/session` memerlukan sesi aktif dan header `X-CSRF-Token` terbaru.
Respons berhasil `{"data":{"authenticated":false}}`; cookie sesi dibersihkan.
Endpoint terlindungi memakai `require_api_user` untuk 401 atau
`require_api_role("admin")` untuk 403 bagi petugas. Kedua status selalu JSON,
tanpa redirect HTML.

### Dashboard yang sudah tersedia (PM-03)

`GET /api/v1/dashboard` memerlukan sesi `admin` atau `petugas`. Angka berasal
dari tabel `archive` pada salinan SQLite lokal. Contoh bentuk respons (angka mengikuti isi database, bukan nilai
tetap):

```json
{
  "data": {
    "counts": {"total": 0, "active": 0, "inactive": 0, "with_file": 0},
    "recent": []
  }
}
```

`active` berarti `status = 1`, `inactive` berarti `status = 2`, dan
`with_file` berarti `has_document = 1`. `total` mencakup semua status, termasuk
status 3. `recent` berisi maksimal enam arsip dengan ID tertinggi, berurutan
menurun; setiap item hanya mempunyai `id`, `year`, dan `summary_raw`. ID
tertinggi tidak selalu berarti tanggal dokumen terbaru. `year` dan
`summary_raw` dapat `null`. Database kosong memberi semua angka nol dan daftar
kosong. Respons memakai `Cache-Control: no-store`; kegagalan baca database
memberi 500 JSON tanpa rincian SQL.

### Pencarian yang sudah tersedia (PM-04)

`GET /api/v1/search` memerlukan sesi. `q` di-*trim*; kueri kosong memberi
`items: []` dan `total: 0`. Default `method` saat ini adalah `like`, sama
dengan baseline pencarian lama. Admin boleh memilih salah satu nama di
`services/web_search.py`; petugas tidak boleh memilih metode fuzzy dan
menerima 403 jika mencobanya. UI React menyembunyikan pemilihan metode bagi petugas.

Respons berbentuk `data: {query, method, items, pagination}`. Setiap item hanya
memuat `id`, `summary_raw`, `opd_name`, `year`, `spm_number`, `file_number`,
`has_document` (boolean), dan `score`; field yang tidak tersedia dapat `null`.
`pagination` memuat `limit`, `offset`, dan `total` hasil cocok sebelum pemotongan
halaman. Urutan `like` mengikuti ID naik; metode fuzzy mengikuti skor turun
dengan ID naik untuk skor seri. `score` adalah keluaran mesin pencarian, bukan
perhitungan baru di endpoint; LIKE memakai skor tetap 1.0.

`GET /api/v1/search/filters` menyediakan pilihan OPD dari salinan SQLite,
`default_method`, serta daftar `methods` berlabel untuk admin. Petugas menerima
`methods: []`; UI petugas tidak menampilkan pemilih metode. Keduanya memerlukan
sesi, memakai `Cache-Control: no-store`, dan tidak mengirim data arsip.

`opd_id` bilangan positif; `year` 1900–2100; `status` 1, 2, atau 3; `limit`
1–100 (default 20); `offset` bilangan nol atau lebih (default 0). Filter
kosong berarti tidak dipakai. `limit=` atau `offset=` kosong, angka tidak
valid, parameter ganda, kueri lebih dari 200 karakter, serta metode tidak
dikenal memberi 400. Data arsip tidak dikirim bila belum login (401). Respons
memakai `Cache-Control: no-store`; kegagalan membaca SQLite memberi 500 JSON
tanpa rincian internal.

### Detail arsip yang sudah tersedia (PM-05)

`GET /api/v1/archives/{id}` memerlukan sesi admin atau petugas. `{id}` harus
bilangan bulat positif; format salah memberi 400 dan ID yang tidak ditemukan
memberi 404. Respons `data` memuat `id`, `status`, `year`, `opd_name`,
`classification_label`, `file_number`, `index_label`, `summary_raw`,
`has_document` (boolean), `location`, dan `extraction`.

`location` berisi `block`, `rack`, `row`, dan `box_number`. `extraction`
berisi `spm_number`, `sp2d_number`, `document_date`, `amount_rp`, `party_name`,
serta `spm_type` (`code`, `label`, `confidence`) atau `null` bila tidak ada.
`confidence` dari kamus SPM ditampilkan apa adanya, termasuk `dugaan`;
hasil ekstraksi harus dibandingkan dengan `summary_raw` sebelum dipakai
sebagai bukti. Field yang tidak tersedia tetap `null`, bukan teks pengganti
buatan server. Nama berkas digital, catatan retensi, dan kolom internal lain
tidak dikirim. Respons memakai `Cache-Control: no-store` dan galat database
500 JSON tanpa rincian SQL. Frontend harus merender teks asli sebagai teks,
tanpa menyisipkannya sebagai HTML.

### Perbandingan metode yang sudah tersedia (PM-06)

`GET /api/v1/search/compare` hanya untuk admin; tanpa sesi memberi 401,
petugas memberi 403. `q` wajib diisi setelah di-*trim* dan maksimal 200
karakter. Filter opsional `opd_id` (positif), `year` (1900–2100), dan `status`
(1–3) dipakai sama untuk seluruh metode. `limit` berlaku **per metode**,
default 10 dan maksimum 20. Kueri/filter/batas tidak valid atau ganda memberi
400 JSON.

Respons `data` memuat `query`, `limit`, `filters`, `methods`, dan `score_note`.
`methods` adalah daftar dalam urutan tetap: LIKE (pembanding), Levenshtein,
Jaro-Winkler, Token Set, dan N-gram Dice. Setiap metode memuat `name`, `label`,
serta `items` berisi `id`, `summary_raw`, dan `score` asli. Jika tidak ada
hasil, kelima metode tetap muncul dengan `items: []`. Skor antar metode tidak
selalu sebanding; bandingkan urutan dan arsip yang muncul, bukan nilai skor
mentah lintas metode. Respons memakai `Cache-Control: no-store`; kegagalan
database memberi 500 JSON tanpa rincian SQL.

## Endpoint dan pemilik tiket

| Metode dan path | Pemakai | Data yang diharapkan | Tiket |
|---|---|---|---|
| `GET /api/v1/session` | publik | `authenticated`, `user` atau `null`, `csrf_token`; tersedia | PM-02 |
| `POST /api/v1/session` | publik | akun yang masuk; cookie sesi; tersedia | PM-02 |
| `DELETE /api/v1/session` | masuk | sesi diakhiri; tersedia | PM-02 |
| `GET /api/v1/dashboard` | admin, petugas | `counts` dan enam arsip ber-ID tertinggi; tersedia | PM-03 |
| `GET /api/v1/search` | admin, petugas | `items`, `pagination`, metode yang dipakai; tersedia | PM-04 |
| `GET /api/v1/search/filters` | admin, petugas | pilihan OPD dan metode sesuai peran; tersedia | PM-10 |
| `GET /api/v1/archives/{id}` | admin, petugas | detail, metadata, status dugaan, lokasi; tersedia | PM-05 |
| `GET /api/v1/search/compare` | admin | hasil per metode untuk kueri sama; tersedia | PM-06 |
| `GET /api/v1/imports` | admin | berkas yang diizinkan, mode verifikasi, 20 riwayat batch terakhir; tersedia | PM-15 |
| `GET /api/v1/imports/preview?source=...` | admin | hash, ukuran, dan jumlah arsip/OPD/klasifikasi; tersedia | PM-15 |
| `POST /api/v1/imports` | admin | impor dengan `source`, `source_sha256`, dan header CSRF; cadangan serta ringkasan hasil; tersedia | PM-15 |
| `GET /api/v1/extraction-audit?index=0` | admin, petugas ditugaskan | sampel acuan, verdict akun, progres, metrik sementara/final; tersedia | PM-16 |
| `PATCH /api/v1/extraction-audit/{archive_id}/fields/{field}` | admin, petugas ditugaskan | `verdict`, `note`, `fingerprint` dan header CSRF; tersedia | PM-16 |
| `GET /api/v1/extraction-audit/export` | admin, petugas ditugaskan | CSV akun sendiri setelah seluruh sel lengkap; tersedia | PM-16 |
| `GET /api/v1/extraction-audit/reviewers` | admin | daftar petugas dan penugasan; tersedia | PM-16 |
| `PUT/DELETE /api/v1/extraction-audit/reviewers/{id}` | admin | tugaskan/cabut petugas, header CSRF; tersedia | PM-16 |
| `GET /api/v1/spm-types` | admin | kode, status, sumber, dan jumlah arsip; tersedia | PM-16 |
| `POST /api/v1/spm-types/{code}/confirm` | admin | `label`, `source_note`, dan header CSRF; tersedia | PM-16 |
| `GET /api/v1/testsets`, `GET /api/v1/testsets/{version}` | admin | versi, status, jumlah kueri dasar/varian per split, asal, SHA-256, daftar kueri pada detail | PM-17 |
| `POST /api/v1/testsets`, `PUT /api/v1/testsets/{version}` | admin | objek JSON set uji (maksimal 4 MiB), header CSRF, serta `If-Match` untuk penggantian | PM-17 |
| `POST /api/v1/testsets/{version}/lock` | admin | header CSRF dan `If-Match` berisi SHA-256 dalam tanda kutip ganda | PM-17 |
| `GET /api/v1/testsets/{version}/export` | admin | lampiran JSON versi terkunci dengan `content_sha256` yang dapat diverifikasi CLI | PM-17 |
| `GET /api/v1/relevance-admin` | admin | akun aktif, pilihan versi terkunci, dan progres penugasan | PM-18 |
| `POST /api/v1/relevance-admin/{version}?first={id}&second={id}` | admin | dua akun berbeda dan badan CSV sampel UTF-8, maksimal 8 MiB | PM-18 |
| `POST /api/v1/relevance-admin/{version}/{slot}/migration` | admin | badan CSV jawaban lama dan jumlah pasangan yang diimpor/dipertahankan | PM-18 |
| `GET /api/v1/relevance-admin/{version}/{slot}/export` | admin | CSV slot 1 atau 2 setelah kedua penyerahan | PM-18 |
| `GET /api/v1/relevance-reviews` | akun masuk | versi tugas milik akun | PM-18 |
| `GET /api/v1/relevance-reviews/{version}?index=0` | penilai yang ditugaskan | satu pasangan serta jawaban dan progres akun sendiri, indeks opsional | PM-18 |
| `PUT /api/v1/relevance-reviews/{version}/{pair}` | penilai yang ditugaskan | simpan `is_relevant` (0, 1, atau null), `ragu`, `notes` dan `revision` | PM-18 |
| `POST /api/v1/relevance-reviews/{version}/submit` | penilai yang ditugaskan | kunci jawaban sendiri setelah semua pasangan dinilai | PM-18 |

Operasi tulis PM-18 mewajibkan `X-CSRF-Token`. Payload contoh untuk pasangan
baru adalah `{"is_relevant":null,"ragu":true,"notes":"","revision":0}`.
Catatan atau ragu tanpa keputusan tidak menambah progres. Revisi lama
menghasilkan 409 dan isian terbaru tetap tersimpan. Tampilan penilai hanya
memuat kueri dasar, jenis kueri, teks mentah, dan jawaban akun aktif.
Varian dari kebutuhan informasi yang sama disatukan pada pasangan kueri
dasar–arsip dan dipetakan kembali ke identitas CSV saat ekspor.

Versi baru terbuka saat didaftarkan. Field `locked_at` dan `locked_by` bernilai
`null` sampai admin mengunci versi. Simpan dan kunci dicatat di log aktivitas.
Perubahan pada versi terkunci, konflik hash, dan unduhan versi terbuka
menghasilkan 409. JSON tidak valid menghasilkan 400, berkas terlalu besar
menghasilkan 413, dan validasi struktur, hash, atau split yang gagal menghasilkan
422. Hash mengikuti serialisasi kanonis CLI dan tidak mencakup metadata web.
Validasi split mencakup kueri dasar, arsip asal, SPM dan pihak dari metadata
yang tersedia, serta kelompok duplikat yang dicantumkan dalam JSON. Status kunci
menandai snapshot yang dapat ditelusuri. Validasi ilmiah desain, realisme, dan
kesepakatan penilai tetap mengikuti protokol penelitian.

Audit PM-16 membaca CSV sampel serta manifest acuan yang dikonfigurasi melalui
`PM_AUDIT_SAMPLE_CSV` dan `PM_AUDIT_MANIFEST`. Verdict sumber diabaikan; setiap
akun menyimpan penilaiannya sendiri dalam SQLite. `verdict: null` berarti belum
dinilai, bukan benar atau salah. `fingerprint` mencegah simpan saat sampel acuan
berubah. Hanya `benar`, `salah`, `terlewat`, dan `tidak_ada_di_teks` yang diterima.
Ringkasan parsial diberi status `sementara`, ekspor ditolak dengan 409 sampai
seluruh lima bidang pada setiap sampel lengkap. Konfirmasi SPM hanya menerima
kode `dugaan` dan mencatat admin, waktu, label, serta sumbernya.

Penamaan field rinci di atas diuji sebelum frontend fitur terkait dibangun.
Endpoint lain yang belum ada tidak boleh dijadikan contoh respons berhasil
dalam README atau laporan.

## Parameter dan validasi pencarian

- `q`: teks kueri yang di-*trim*; maksimal 200 karakter. Permintaan tanpa
  kueri dapat menghasilkan daftar kosong dengan penjelasan, bukan pencarian
  seluruh korpus tanpa batas.
- `opd_id`, `year`, `status`: filter opsional. Nilai numerik dan rentang/status
  diverifikasi di Flask. Nilai tidak valid menghasilkan 400.
- `method`: petugas memakai metode bawaan `like` saat ini; hanya admin
  dapat memilih metode atau membuka perbandingan. Nama metode yang tidak dikenal
  menghasilkan 400, pilihan tanpa hak menghasilkan 403.
- Daftar memakai `limit` (default 20, maksimum 100) dan `offset` (default 0).
  `pagination` mencantumkan nilai efektif dan `total`; `limit`/`offset` yang
  tidak valid menghasilkan 400. Total dihitung dari hasil dengan filter yang
  sama sebelum pagination, tanpa mengubah urutan ranking.
- ID arsip harus berupa bilangan bulat positif; arsip yang tidak ada
  menghasilkan 404. Data kosong dikirim sebagai `null` atau string kosong
  sesuai kontrak field, tanpa nilai rekaan.

## Sesi dan operasi tulis target

- `GET /session` menyediakan token CSRF untuk sesi browser, termasuk sebelum
  login. Endpoint tulis yang sudah dibuat memakai header `X-CSRF-Token`;
  endpoint tulis berikutnya wajib mengikuti aturan yang sama.
- Cookie sesi `HttpOnly`, `SameSite=Lax`, dan `Secure` saat HTTPS. Respons
  sesi/data sensitif memakai `Cache-Control: no-store`. Jangan simpan kredensial
  atau token sesi di `localStorage`.
- Atur `PM_SECRET_KEY` tetap dan acak pada instalasi agar sesi tidak terputus
  saat layanan dimulai ulang. Atur `PM_COOKIE_SECURE=1` bila browser mengakses
  aplikasi lewat HTTPS; cookie Secure hanya dikirim lewat koneksi HTTPS.
- Semua izin diperiksa oleh backend. 401 berarti masuk ulang diperlukan;
  403 berarti akun aktif tetapi perannya tidak cukup.
- Validasi UI membantu pengguna, tetapi Flask tetap memvalidasi semua input
  serta memakai SQL terparameterisasi. Respons tidak memuat kolom dari dump
  yang tidak diperlukan untuk halaman.

## Perubahan kontrak

Setiap tiket endpoint menambah contoh payload sukses/gagal, uji kontrak, dan
catatan perubahan di sini. Perubahan yang memutus frontend memerlukan versi
baru atau migrasi kedua sisi dalam tiket yang sama. Jangan mengubah bentuk
respons diam-diam demi mempercepat implementasi UI.
