# Arsitektur target: Flask API + React

**Status (21 November 2026): fondasi API PM-01, sesi PM-02, dashboard PM-03,
pencarian PM-04, detail PM-05, React PM-07, login PM-08, dan dashboard PM-09 sudah dibuat;
halaman bisnis dan pengemasan produksi masih target.** Web utama saat ini
memakai route Flask/Jinja di `webapp/` dan `templates/`.
`scripts/relevance_labeler_app.py` adalah alat pelabelan internal yang terpisah.
Dokumen ini menetapkan arah implementasi berikutnya; jangan mengutipnya di Bab IV
sebagai hasil yang sudah selesai.

## Bentuk sistem

```text
Browser ── React SPA (aset statis hasil Vite build)
   │          │
   └─ /api/* ─┴─ Flask/Waitress ─ services/ ─ SQLite lokal
                                  │
                                  └─ core/ (normalisasi, ekstraksi, pencarian, evaluasi)
```

- Saat pengembangan: Vite di laptop dengan proxy `/api` ke Flask. Node.js hanya
  menjalankan Vite, lint, dan build pada mesin pengembang.
- Saat digunakan: satu layanan Python/Waitress menyajikan API dan berkas
  `frontend/dist/`. Paket rilis wajib menyertakan hasil `npm run build`.
  Server dinas tidak perlu Node.js, npm, CDN, maupun PHP untuk aplikasi ini.
- XAMPP lama bukan runtime Flask. Penempatan di server dinas harus dibahas dengan
  pengelola TI; jangan mengubah konfigurasi SIMANIS atau mengasumsikan akses
  instalasi. Untuk uji penelitian, gunakan komputer uji terpisah yang diizinkan.
- SQLite tetap memakai salinan data penelitian; tidak ada koneksi tulis ke SIMANIS.

## Library yang dipilih

| Kebutuhan | Pilihan | Aturan penggunaan |
|---|---|---|
| UI dan tipe | React, TypeScript `strict`, Vite | SPA statis tanpa SSR; Vite hanya alat build |
| Navigasi | `react-router` mode deklaratif | Route klien; Flask menyediakan fallback SPA kecuali `/api/*` |
| Data server | `@tanstack/react-query` | Cache/invalidation respons API; jangan menduplikasi ke global store |
| Form | `react-hook-form`, `zod`, `@hookform/resolvers` | Validasi UI; backend tetap memvalidasi semua input |
| Gaya | Tailwind CSS v4 + `@tailwindcss/vite` | Token warna/ruang/tipe di CSS; class statis; CSS kustom untuk pola berulang |
| Komponen UI | shadcn/ui dengan basis Radix yang dipilih eksplisit | Tambah komponen yang dibutuhkan saja ke `frontend/src/components/ui/`; kode hasil generator menjadi milik proyek |
| Ikon | `lucide-react` | Ikon konsisten; tombol ikon wajib punya nama aksesibel |
| Grafik | Recharts | Hanya halaman evaluasi yang benar-benar punya data; tabel tetap tersedia |
| Pengujian frontend | Vitest + Testing Library | Uji perilaku penting; Playwright untuk alur lintas browser jika diperlukan |
| Pemeriksaan kode | Oxlint + Prettier | Jalankan lint, `tsc -b`, uji, dan build sebelum rilis |

Saat inisialisasi shadcn/ui, pilih basis Radix secara eksplisit dan simpan
`components.json` agar hasil generator konsisten. Jangan mencampur komponen
berbasis Radix dan Base UI tanpa keputusan migrasi tertulis. Periksa diff
setiap penambahan atau pembaruan komponen; jangan memakai `add --all` atau
menimpa komponen yang sudah disesuaikan tanpa review.

Versi dependency dipilih saat instalasi, direkam di `package.json` dan
`package-lock.json`, lalu diperbarui secara sadar. Jangan menulis nomor versi
yang belum diverifikasi dalam laporan. Tidak perlu Redux, Axios, Bootstrap,
Chart.js, atau komponen UI besar selama kebutuhan di atas sudah tertangani.

## Struktur target

```text
PM/
├─ app.py, wsgi.py                # entry point Flask/Waitress
├─ webapp/                         # factory, auth, API blueprints, SPA fallback
├─ services/                       # SQLite dan orkestrasi domain
├─ core/                           # aturan penelitian Python murni
├─ frontend/
│  ├─ src/
│  │  ├─ app/                    # router, providers, layout
│  │  ├─ features/               # auth, dashboard, search, archives, evaluation
│  │  ├─ components/ui/          # komponen bersama yang kecil
│  │  ├─ lib/api/                # fetch client, kontrak respons, error
│  │  └─ styles/                 # token dan CSS global
│  ├─ public/                    # aset publik lokal
│  ├─ dist/                      # keluaran build; masuk paket rilis
│  ├─ package.json
│  ├─ components.json            # konfigurasi generator shadcn/ui
│  └─ package-lock.json
├─ tests/                         # pytest API/domain
└─ docs/                          # protokol ilmiah dan keputusan arsitektur
```

`frontend/dist/` dan `frontend/node_modules/` tidak menjadi sumber kode dan
diabaikan Git. Prosedur pengemasan rilis harus membangun ulang `dist/`, menguji
asetnya, lalu menyertakannya bersama kode Python. Jangan menyatakan rilis siap
sebelum prosedur tersebut tersedia dan lulus.

## Kontrak dan keamanan API

Kontrak respons dan status endpoint yang sedang diimplementasikan ada di
[api_contract.md](api_contract.md). Bagian di bawah menetapkan batas arsitektur.

- Semua endpoint data memakai prefiks `/api/v1`. Endpoint yang direncanakan:
  `GET /session`, `POST /session`, `DELETE /session`, `GET /dashboard`,
  `GET /search`, `GET /archives/{id}`, dan endpoint admin/evaluasi sesuai fitur.
  Penamaan final ditetapkan dalam uji kontrak ketika diimplementasikan.
- Respons JSON memiliki bentuk konsisten: `data` untuk berhasil;
  `error: {code, message}` untuk gagal. Gunakan HTTP 400/401/403/404/422
  sesuai kasus. Jangan kirim HTML login untuk permintaan API yang tidak sah.
- Cookie sesi `HttpOnly`, `SameSite=Lax`, dan `Secure` bila HTTPS. Kirim token
  CSRF lewat endpoint sesi dan header pada POST/PATCH/PUT/DELETE. Batasi origin
  ke origin aplikasi; jangan membuka CORS umum atau menyimpan token di localStorage.
- Filter, batas hasil, dan ukuran halaman diverifikasi di server. Semua akses
  database memakai parameter SQL. Keluaran JSON tidak memuat data sensitif di
  luar keperluan tampilan. Peran admin/petugas ditegakkan di endpoint.
- Browser menampilkan loading, kosong, gagal, dan kedaluwarsa sesi secara jelas.
  Teks arsip dirender sebagai teks React; hindari `dangerouslySetInnerHTML`.
  Penyorotan kata memakai pemecahan token menjadi elemen `<mark>` yang aman.

## Urutan migrasi dan bukti selesai

1. Catat route, data, dan izin yang sudah berjalan di Flask/Jinja; buat uji API
   untuk autentikasi, pencarian, detail arsip, dan peran.
2. Tambah endpoint JSON yang memakai `services/` dan `core/` yang sama. UI Jinja
   tetap tersedia selama migrasi agar alur yang sudah ada dapat diverifikasi.
3. Bangun React per fitur, dimulai login, dashboard, pencarian, detail arsip.
   Lanjutkan modul admin hanya bila backend-nya sudah ada.
4. Tambah fallback SPA dan kemasan aset lokal; uji langsung lewat Waitress
   tanpa Node.js serta tanpa internet pada desktop, tablet, dan ponsel.
5. Setelah paritas dan uji lulus, hapus template/aset lama yang tidak dipakai
   melalui perubahan terpisah. Perbarui diagram, tabel perangkat lunak, dan
   screenshot laporan berdasarkan implementasi akhir.
