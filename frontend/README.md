# Frontend React proyek PM

Frontend ini adalah fondasi migrasi. Route `/login` memakai sesi JSON Flask;
route `/app/dashboard` menampilkan angka korpus dari `/api/v1/dashboard`,
`/app/status` memeriksa koneksi ke `/api/v1/health`, dan `/app/search`
menampilkan pencarian serta filter arsip setelah pengguna masuk. Hasil pencarian
membuka `/app/archives/{id}` untuk teks asli, metadata ekstraksi, dan lokasi.
Pemilihan metode pencarian dan halaman `/app/compare` hanya tersedia untuk
admin. Halaman perbandingan menampilkan urutan hasil lima metode dari API;
skor antarmetode tidak digunakan sebagai angka yang sebanding. Halaman
`/app/imports` memungkinkan admin memilih dump dari direktori server yang
diizinkan, memeriksa pratinjau, lalu melihat hasil dan riwayat impor.
Halaman `/app/extraction-audit` menilai lima bidang ekstraksi per sampel dan
menampilkan progres per akun; `/app/spm-types` memberi admin formulir konfirmasi
kode dugaan beserta sumbernya.

Navigasi utama berada di sidebar pada desktop dan dibuka dari tombol menu
pada tablet dan ponsel. Menu dikelompokkan menjadi Arsip, Evaluasi,
Pengelolaan Data, dan Sistem. Identitas dan tombol Keluar berada di bagian
Akun. Pilihan menu mengikuti peran pengguna. Admin dapat membuka
`/app/testsets` dari kelompok Evaluasi untuk mendaftarkan, meninjau,
mengunci, dan mengunduh versi set uji.
Penugasan dan migrasi CSV berada di `/app/relevance-admin`. Penilai membuka
`/app/relevance` untuk melihat tugas dan jawaban sendiri.

## Jalankan di laptop pengembang

Dari `D:\Coding\PM`, jalankan Flask/Waitress di port 8000. Lalu pada terminal
lain di folder `frontend/`:

```powershell
npm ci
npm run dev
```

Vite meneruskan `/api` ke `http://127.0.0.1:8000`. Node.js diperlukan untuk
pengembangan dan build frontend saja. Buat akun melalui perintah di README
proyek sebelum mencoba login. Untuk memeriksa frontend:

```powershell
npm run lint
npm run typecheck
npm test
npm run format:check
npm run build
```

Hasil `dist/` diabaikan Git. Untuk membuat ZIP rilis yang menyertakan aset ini,
jalankan `scripts/build_web_release.py` dari akar proyek. Panduan memasang dan
menjalankannya ada di `../docs/runbook_web_release.md`.

## Struktur dan komponen

- `src/app/`: provider dan router.
- `src/features/`: halaman dan hook per fitur.
- `src/lib/api/`: permintaan dan validasi respons API.
- `src/components/ui/`: komponen shadcn/ui dengan basis Radix, milik proyek.
- `src/index.css`: Tailwind dan token desain; font Inter disimpan lokal.

`components.json` mengunci basis `radix-nova`. Tambahkan komponen hanya saat
fitur memerlukannya, misalnya `npx shadcn add input`; tinjau diff hasil CLI
sebelum commit. Jangan memakai `add --all` atau menimpa penyesuaian lokal.

Kontrak HTTP ada di `../docs/api_contract.md` dan aturan kerja di
`../AGENTS.md`.
