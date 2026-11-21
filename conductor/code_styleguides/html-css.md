# Panduan antarmuka React, TypeScript, HTML, dan CSS

Dokumen ini menggantikan aturan lama yang mewajibkan Jinja2/Bootstrap dan
melarang React. Rancangan target: `../../docs/arsitektur_flask_react.md`.

## Struktur dan batas data

- Kode baru berada di `frontend/src/`; kelompokkan menurut fitur (`features/`),
  lalu letakkan komponen bersama yang benar-benar dipakai ulang di
  `components/ui/`. Jangan membuat satu berkas besar untuk seluruh aplikasi.
- Komponen merender data dan interaksi; klien HTTP di `lib/api/`; hook query dan
  mutation di fitur terkait. Jangan memanggil `fetch` langsung dari JSX.
- TypeScript `strict`; tipe API tidak boleh diasumsikan dari bentuk JSON mentah.
  Definisikan kontrak dan validasi pada batas respons. Hindari `any`, assertion
  non-null tanpa alasan, dan state turunan yang bisa dihitung dari props/query.
- TanStack Query untuk data server. Gunakan state React biasa untuk dialog,
  input lokal, dan kontrol presentasi. Jangan menambah Redux/Zustand hanya
  untuk menyalin cache server.
- React Router mode deklaratif mengelola navigasi. Status 401 membawa pengguna
  ke login dan mempertahankan tujuan semula secara aman; 403 menampilkan akses
  ditolak. Proteksi route klien tidak menggantikan otorisasi API.

## Library dan tampilan

- Tailwind CSS v4 dipakai lewat plugin Vite. Warna, tipografi, ruang, radius,
  dan fokus didefinisikan sebagai token; hindari kelas arbitrer berulang.
  Pakai CSS biasa untuk pola kompleks yang lebih jelas daripada daftar utilitas.
- Gunakan komponen shadcn/ui yang dibutuhkan saja di `components/ui/` dengan
  basis Radix yang konsisten. Kode hasil generator milik proyek: baca diff,
  uji perubahan, dan jangan menimpa penyesuaian lokal tanpa review. Form standar
  gunakan elemen HTML asli. Ikon gunakan `lucide-react`, dengan ukuran/stroke
  konsisten dan label aksesibel pada tombol yang hanya berisi ikon.
- Gunakan Recharts untuk grafik evaluasi yang memiliki data sah. Sertakan
  label, satuan, legenda yang jelas, dan tabel data alternatif. Jangan
  menggambar grafik dari angka contoh atau hardcode metrik.
- Desain profesional dan ringkas: palet netral, satu warna aksen, hierarki
  tipografi jelas, ruang cukup, tanpa dekorasi/gradien berlebihan. Status
  ilmiah seperti “dugaan” atau “belum diverifikasi” terlihat jelas.

## Keamanan dan aksesibilitas

- Render teks arsip sebagai teks React. Dilarang memakai
  `dangerouslySetInnerHTML` untuk data arsip atau hasil API. Untuk sorotan,
  pecah teks menjadi node teks dan elemen `<mark>`.
- Setiap input memiliki label, pesan galat terkait, dan fokus keyboard yang
  terlihat. Gunakan tombol/link sesuai maknanya. Status tidak disampaikan
  dengan warna saja. Pastikan kontras dan ukuran target sentuh memadai.
- Layout harus tetap dapat dipakai pada desktop, tablet, dan ponsel. Jangan
  mengunci tinggi seluruh halaman agar bebas scroll; tabel lebar boleh memakai
  scroll horizontal pada kontainernya, dengan kolom penting tetap terbaca.
- Tampilkan keadaan loading, kosong, gagal, dan berhasil. Pesan API kepada
  pengguna tidak boleh memuat stack trace atau data rahasia.

## Pemeriksaan

Jalankan lint, pemeriksaan tipe, uji perilaku yang relevan, dan build produksi.
Uji alur login, pencarian, detail, serta pembatasan peran pada ukuran desktop,
tablet, dan ponsel. Aset final tidak boleh membutuhkan CDN.
