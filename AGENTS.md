# Aturan kerja AI untuk proyek PM

Baca `README.md`, `docs/PRD.md`, `docs/BACKLOG.md`,
`docs/arsitektur_flask_react.md`, dan dokumen terkait di
`conductor/` sebelum mengubah aplikasi. Instruksi pengguna pada percakapan
berlaku lebih tinggi daripada dokumen ini.

## Kebenaran proyek

- Pisahkan **sudah terimplementasi**, **target**, dan **hasil penelitian yang belum
  terverifikasi**. Jangan menyebut fitur React/API selesai sebelum kode dan uji ada.
- Jangan mengubah berkas di `D:\Dokumen Penelitian Mandiri` untuk pekerjaan kode
  kecuali pengguna memintanya. Jangan menyentuh data asli, penilaian petugas,
  database lokal, atau notebook yang terhapus di working tree tanpa kebutuhan jelas.
- Jangan membuat angka metrik, jawaban penilai, skor SUS, atau klaim kesepakatan.
  Ambil angka dari hasil komputasi yang dapat dilacak ke data dan versi set uji.

## Batas arsitektur

- Backend: Flask application factory di `webapp/`, endpoint JSON di bawah `/api`.
  `services/` menghubungkan HTTP, SQLite, dan `core/`. `core/` tetap bebas Flask,
  React, dan akses basis data.
- Frontend target: React + TypeScript + Vite di `frontend/`. Node.js hanya untuk
  pengembangan/build. Flask/Waitress menyajikan hasil build statis saat produksi.
  Aplikasi produksi harus berfungsi di intranet tanpa CDN atau proses Node.js.
- SQLite lokal di `instance/` memakai `services/db.py` yang ada. Jangan menambah
  ORM, MySQL, layanan cloud, atau state manager baru tanpa kebutuhan terukur.
- React tidak boleh mengakses SQLite atau menghitung ulang logika ilmiah. Semua
  autentikasi, otorisasi, validasi input, dan hasil pencarian berasal dari Flask.
- Gunakan sesi cookie HttpOnly dan proteksi CSRF pada operasi yang mengubah data.
  Otorisasi peran wajib dicek di server, bukan hanya menyembunyikan tombol.

## Library dan kualitas kode

- Pilihan library dan alasan pemakaiannya ada di `docs/arsitektur_flask_react.md`.
  Pasang dependency hanya saat fitur yang memerlukannya dibuat; catat di manifest
  dan lockfile. Jangan memuat library dari CDN.
- Komponen `frontend/src/components/ui/` berasal dari shadcn/ui dengan basis
  Radix yang konsisten. Tambahkan hanya yang diperlukan; periksa kode hasil
  generator dan jangan menjalankan `add --all` atau menimpa perubahan lokal.
- TypeScript `strict`; jangan memakai `any` untuk melewati kesalahan tipe.
  Validasi respons API pada batas masuk data. Komponen UI tidak memanggil `fetch`
  langsung; pakai client dan hook fitur yang terpisah.
- Satu sumber untuk setiap konsep: aturan domain di `core/`, akses data di
  `services/`, kontrak HTTP di `webapp/`, token desain di frontend. Hindari
  menyalin logika yang sama ke beberapa lapisan.
- Gunakan elemen HTML semantik, label formulir, fokus keyboard yang terlihat,
  status berbentuk teks, dan layout responsif desktop/tablet/ponsel. Jangan
  memaksa semua konten muat dalam satu layar; area tabel boleh bergulir.
- Perubahan API harus disertai uji kontrak/status/otorisasi yang relevan.
  Perubahan domain ilmiah memerlukan uji acuan yang dihitung tangan. Perubahan UI
  diuji untuk alur utama, keadaan loading/kosong/error, dan build produksi.
- Jangan menjalankan `git reset`, menghapus berkas pengguna, atau menimpa
  perubahan working tree yang sudah ada. Periksa `git status` sebelum dan sesudah.
- Untuk pekerjaan dalam backlog, sebut ID tiket, ikuti fase uji dan batas
  commit di `docs/BACKLOG.md`, lalu catat bukti uji serta hash commit sebelum
  menandai tiket selesai. Jangan mencampur perubahan dari tiket lain.

## Selesai bila

Kode, dokumentasi, dan perintah menjalankan aplikasi saling sesuai; uji yang
relevan lulus; aset produksi dapat dijalankan dengan Python/Waitress tanpa Node.js;
dan batasan atau pekerjaan yang belum selesai dilaporkan apa adanya.
