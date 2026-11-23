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
