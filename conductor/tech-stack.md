# Tech stack proyek PM

Dokumen ini membedakan **implementasi sekarang** dan **arsitektur target**.
Rincian keputusan ada di `../docs/arsitektur_flask_react.md`; aturan kerja AI
ada di `../AGENTS.md`.

## Saat ini

- Python 3.14, Flask 3.1, Flask-Login, RapidFuzz, SQLite melalui `services/db.py`,
  dan Waitress. Versi tepat dependensi web tercantum di `requirements-web.txt`.
- `core/` memuat logika ilmiah; `services/` menghubungkan domain dan database;
  `webapp/` memuat route Flask. `app.py` dan `wsgi.py` adalah entry point.
- Antarmuka web utama masih dirender oleh Jinja2 di `templates/` dengan CSS di
  `static/`. Ini implementasi sementara, bukan React yang sudah selesai.
- Analisis notebook memakai dependensi terpisah di `requirements.txt`. Paket
  analisis tidak perlu dipasang pada server web kecuali fitur yang memerlukannya
  benar-benar dijalankan di sana.
- Akses database menggunakan `sqlite3` saat ini. Jangan menulis bahwa aplikasi
  memakai Flask-SQLAlchemy/SQLAlchemy dalam dokumentasi hasil implementasi.

## Target migrasi

- Backend: Flask JSON API dengan prefiks `/api/v1`; sesi login cookie, proteksi
  CSRF, otorisasi peran di server, dan kontrak galat JSON yang konsisten.
- Frontend: React + TypeScript `strict`, Vite, `react-router`, TanStack Query,
  React Hook Form + Zod, Tailwind CSS v4, shadcn/ui berbasis Radix,
  `lucide-react`, dan Recharts hanya untuk grafik evaluasi.
- Kualitas frontend: ESLint, Prettier, `tsc`, Vitest/Testing Library. Gunakan
  Playwright bila diperlukan untuk alur end-to-end penting.
- Node.js dan npm dipakai pada laptop pengembang untuk instalasi, server Vite,
  pemeriksaan, dan build. `npm run build` menghasilkan aset statis yang dikemas
  bersama aplikasi Flask. Produksi menjalankan Python/Waitress saja.
- Tidak ada CDN atau panggilan cloud saat aplikasi berjalan. XAMPP/PHP yang
  mungkin ada di server dinas bukan dependensi aplikasi ini.

## Penguncian versi

Python web: `requirements-web.txt`; Python analisis: `requirements.txt`;
frontend setelah dibuat: `frontend/package.json` dan `frontend/package-lock.json`.
Hindari menyalin daftar versi dari lingkungan lain tanpa verifikasi instalasi.

## Referensi library

- [Vite: build produksi](https://vite.dev/guide/build)
- [React Router: mode deklaratif](https://reactrouter.com/start/declarative/installation)
- [TanStack Query: data server](https://tanstack.com/query/latest/docs/framework/react/overview)
- [Tailwind CSS: plugin Vite](https://tailwindcss.com/docs/installation/using-vite)
- [shadcn/ui: instalasi Vite](https://ui.shadcn.com/docs/installation/vite)
