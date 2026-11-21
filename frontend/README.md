# Frontend React proyek PM

Frontend ini adalah fondasi migrasi. Route `/login` memakai sesi JSON Flask;
route `/app/dashboard` menampilkan angka korpus dari `/api/v1/dashboard`,
`/app/status` memeriksa koneksi ke `/api/v1/health`, dan `/app/search`
menampilkan pencarian serta filter arsip setelah pengguna masuk. Pemilihan
metode pencarian pada halaman React hanya tersedia untuk admin. Detail arsip
dan perbandingan metode React masih menunggu tiket berikutnya. Aplikasi
Flask/Jinja tetap menjadi antarmuka kerja sampai paritas fitur terbukti.

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

Hasil `dist/` diabaikan Git. Pengemasan aset bersama Flask/Waitress adalah
tiket PM-13; belum selesai saat README ini ditulis.

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
