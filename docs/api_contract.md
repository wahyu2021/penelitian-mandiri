# Kontrak HTTP API Flask untuk React

**Status:** fondasi PM-01 diimplementasikan; endpoint bisnis di tabel bawah
adalah kontrak target untuk PM-02 sampai PM-06. Dokumen ini diperbarui bersama
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

## Endpoint target dan pemilik tiket

| Metode dan path | Pemakai | Data yang diharapkan | Tiket |
|---|---|---|---|
| `GET /api/v1/session` | publik | `authenticated`, `user` atau `null`, `csrf_token` | PM-02 |
| `POST /api/v1/session` | publik | akun yang masuk; cookie sesi | PM-02 |
| `DELETE /api/v1/session` | masuk | sesi diakhiri | PM-02 |
| `GET /api/v1/dashboard` | admin, petugas | `counts` dan daftar ringkas terbaru | PM-03 |
| `GET /api/v1/search` | admin, petugas | `items`, `pagination`, metode yang dipakai | PM-04 |
| `GET /api/v1/archives/{id}` | admin, petugas | detail, metadata, status dugaan, lokasi | PM-05 |
| `GET /api/v1/search/compare` | admin | hasil per metode untuk kueri sama | PM-06 |

Penamaan field rinci ditambahkan ke dokumen ini dan diuji sebelum frontend
fitur terkait dibangun. Endpoint yang belum ada tidak boleh dijadikan contoh
respons berhasil dalam README atau laporan.

## Parameter dan validasi target

- `q`: teks kueri yang di-*trim*; maksimal 200 karakter. Permintaan tanpa
  kueri dapat menghasilkan daftar kosong dengan penjelasan, bukan pencarian
  seluruh korpus tanpa batas.
- `opd_id`, `year`, `status`: filter opsional. Nilai numerik dan rentang/status
  diverifikasi di Flask. Nilai tidak valid menghasilkan 400.
- `method`: petugas memakai metode bawaan dari konfigurasi server; hanya admin
  dapat memilih metode atau membuka perbandingan. Nama metode yang tidak dikenal
  menghasilkan 400, pilihan tanpa hak menghasilkan 403.
- Daftar memakai `limit` (default 20, maksimum 100) dan `offset` (default 0).
  `pagination` mencantumkan nilai efektif dan `total`; `limit`/`offset` yang
  tidak valid menghasilkan 400. PM-04 harus memastikan penghitungan total
  selaras dengan filter dan tidak mengubah urutan ranking.
- ID arsip harus berupa bilangan bulat positif; arsip yang tidak ada
  menghasilkan 404. Data kosong dikirim sebagai `null` atau string kosong
  sesuai kontrak field, tanpa nilai rekaan.

## Sesi dan operasi tulis target

- `GET /session` menyediakan token CSRF untuk sesi browser, termasuk sebelum
  login. `POST`/`PATCH`/`PUT`/`DELETE` memakai header `X-CSRF-Token`.
- Cookie sesi `HttpOnly`, `SameSite=Lax`, dan `Secure` saat HTTPS. Respons
  sesi/data sensitif memakai `Cache-Control: no-store`. Jangan simpan kredensial
  atau token sesi di `localStorage`.
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
