# Panduan Penulisan Kode TypeScript, Prinsip DRY, dan shadcn/ui

Dokumen ini menjadi acuan standar kode frontend selama fase *refactor* dan
pengembangan lanjutan di [`frontend/`](../frontend/). Dokumen ini melengkapi
[arsitektur Flask–React](arsitektur_flask_react.md),
[kontrak API](api_contract.md), dan [`AGENTS.md`](../AGENTS.md).

**Stack aktif:** React 19, TypeScript (`strict`), Vite, React Router v8,
TanStack Query v5, Zod v4, Tailwind CSS v4, `shadcn/ui` (basis `radix-nova`),
Oxlint, Prettier, serta Vitest + Testing Library.

---

## 1. Batas Tanggung Jawab & Struktur Folder

- **React hanya untuk tampilan dan interaksi.** Semua autentikasi, otorisasi
  peran, validasi data utama, kueri SQLite, dan logika pencarian/ilmiah tetap
  berada di Flask, `services/`, dan `core/`.
- **Komponen UI tidak memanggil `fetch` secara langsung.** Seluruh komunikasi
  HTTP dan validasi respons berada di `frontend/src/lib/api/`.
- **Organisasi folder:**
  - `src/app/`: provider global dan konfigurasi router.
  - `src/components/ui/`: primitif UI resmi dari `shadcn/ui` (jangan edit
    sembarangan tanpa alasan jelas).
  - `src/components/shared/`: komposisi UI tingkat aplikasi yang dipakai lintas
    fitur (`PageHeader`, `ForbiddenCard`, `ErrorStateCard`, `EmptyState`).
  - `src/hooks/`: *custom hooks* lintas fitur (mis. penanganan sesi `401`).
  - `src/lib/`: utilitas murni (`format.ts`, `utils.ts`) dan klien API (`api/`).
  - `src/features/<fitur>/`: halaman, sub-komponen fitur, hook lokal, dan uji.

---

## 2. Best Practice TypeScript (`strict`)

### 2.1 Larangan `any` dan `as` yang Menutupi Risiko Tipe

- **Jangan gunakan `any`.** Untuk data luar yang belum tervalidasi (respons
  HTTP, JSON parse, catch error), gunakan `unknown` lalu validasi dengan Zod
  atau *type guard*.
- **Hindari type assertion (`value as TipeLain`)** sebagai jalan pintas, kecuali
  pada pengujian unit yang terkontrol atau setelah validasi runtime.

```ts
// Buruk: memaksa tipe tanpa validasi runtime
const data = (await response.json()) as AdminUser[]

// Baik: validasi batas masuk dengan Zod dan turunkan tipe otomatis
const usersSchema = z.object({
  data: z.object({ users: z.array(adminUserSchema) }),
})
export type AdminUser = z.infer<typeof adminUserSchema>

export async function listAdminUsers(): Promise<AdminUser[]> {
  const response = await fetch('/api/v1/admin/users', {
    credentials: 'same-origin',
    cache: 'no-store',
  })
  return usersSchema.parse(await readResponse(response)).data.users
}
```

### 2.2 Satu Sumber Kebenaran untuk Tipe (*Single Source of Truth*)

- Definisikan skema Zod **sekali** di `src/lib/api/<fitur>.ts`, lalu ekspor tipe
  TypeScript melalui `z.infer<typeof schema>`. Jangan menduplikasi `interface`
  manual yang sama di komponen fitur.
- Gunakan **literal union** atau **discriminated union** untuk nilai terbatas,
  misalnya `'admin' | 'petugas'` atau status UI (`'idle' | 'loading' | 'error'`).
- Gunakan `satisfies` saat mendefinisikan peta label/konfigurasi agar key tetap
  dicek oleh kompiler tanpa menghilangkan inferensi literal.

### 2.3 Fungsi Kecil, Awal Pengembalian (*Early Return*), dan Error Handling

- Pecah komponen atau fungsi yang panjang menjadi bagian kecil dengan satu
  tanggung jawab jelas.
- Tangani kasus *guard* (`!isAdmin`, loading, error) di awal komponen dengan
  *early return* agar JSX utama tetap dangkal dan mudah dibaca.
- Selalu gunakan `ApiError` saat menangkap galat HTTP sehingga UI menampilkan
  pesan ramah pengguna, bukan detail stack trace atau pesan teknis mentah.

---

## 3. Prinsip DRY (*Don't Repeat Yourself*) & Modularitas

### 3.1 Aturan Praktis Ekstraksi

- **Ekstrak ketika pola berulang 2–3 kali dengan niat yang sama**, terutama untuk
  logika sesi, pemformatan data, pemanggilan API, dan pola kartu error/kosong.
- **Jangan memaksakan abstraksi tunggal** jika dua komponen hanya kebetulan
  mirip tampilan tetapi memiliki alur bisnis berbeda (menumpuk banyak prop
  boolean seperti `isCompact`, `hideTitle`, `modeA`). Lebih baik komposisi
  komponen kecil melalui `children`.

### 3.2 Target Refactor Prioritas di Proyek Ini

Audit kode saat ini menunjukkan pengulangan berikut yang harus dirapikan pada
fase *refactor*:

1. **Hook penanganan sesi `401` (`src/hooks/useUnauthorizedRedirect.ts`):**
   - *Saat ini:* blok `useEffect` yang memeriksa `error instanceof ApiError && error.status === 401`,
     menghapus cache `sessionKey`, dan memanggil `navigate('/login', { replace: true })`
     disalin berulang di `DashboardPage`, `SearchPage`, `ArchiveDetailPage`,
     `ComparePage`, `UsersPage`, dan halaman penelitian.
   - *Target:* ekstrak ke satu hook bersama, misalnya
     `useUnauthorizedRedirect(errors: unknown[])`.
2. **Helper format lokal (`src/lib/format.ts`):**
   - *Saat ini:* `new Intl.NumberFormat('id-ID')`, format Rupiah, dan
     `new Intl.DateTimeFormat('id-ID', ...)` didefinisikan ulang di
     `DashboardPage`, `ArchiveDetailPage`, `UsersPage`, dan halaman lain.
   - *Target:* satukan di `src/lib/format.ts` (`formatNumber`, `formatCurrencyIdr`,
     `formatDateTimeId`) agar konsisten di seluruh aplikasi.
3. **Helper klien HTTP (`src/lib/api/client.ts` atau di `session.ts`):**
   - *Saat ini:* setiap fungsi di `src/lib/api/*.ts` mengulang opsi
     `credentials: 'same-origin'`, `cache: 'no-store'`, header `Content-Type`,
     header `X-CSRF-Token`, serta pemanggilan `schema.parse(await readResponse(res))`.
   - *Target:* sediakan `apiGet(url, schema)` dan `apiMutate(url, method, schema, options)`
     yang terketik generik (`<T>(url: string, schema: z.ZodType<T>) => Promise<T>`).
4. **Komponen umpan balik & header bersama (`src/components/shared/`):**
   - *Saat ini:* pola header halaman, kartu `403 · Akses ditolak`, dan kartu
     galat dengan tombol `Coba lagi` ditulis ulang di hampir tiap fitur.
   - *Target:* ekstrak `PageHeader`, `ForbiddenCard`, dan `ErrorStateCard` yang
     dibangun di atas komponen `shadcn/ui`.
5. **Pecah komponen halaman berukuran besar:**
   - Contoh: `UsersPage.tsx` (>500 baris) sebaiknya dipecah menjadi sub-komponen
     fitur di `src/features/admin/`: `CreateUserCard.tsx`, `UsersTableCard.tsx`,
     dan `ActivityLogCard.tsx`, sehingga `UsersPage.tsx` cukup mengoordinasikan
     halaman.

---

## 4. Wajib Menggunakan Komponen `shadcn/ui` (Basis `radix-nova`)

### 4.1 Aturan Utama: Jangan Membuat Primitif UI Sendiri

- **Dilarang menulis ulang komponen UI dasar secara manual** (seperti badge/pill,
  banner alert, tabel bergaya, label form, dialog modal, dropdown, pemisah, atau
  tombol kustom dengan banyak class Tailwind mentah) apabila komponen tersebut
  tersedia di `shadcn/ui`.
- Komponen di `src/components/ui/` adalah milik proyek berbasis **`radix-nova`**
  (`frontend/components.json`). Jangan mencampur library komponen lain atau basis
  non-Radix.

### 4.2 Inventaris Komponen `shadcn/ui` Saat Ini & Target Pemakaian

Saat ini di `frontend/src/components/ui/` baru tersedia 5 komponen:
`button.tsx`, `card.tsx`, `input.tsx`, `native-select.tsx`, dan `skeleton.tsx`.

Pada fase *refactor*, ganti pola HTML/Tailwind manual dengan komponen `shadcn/ui`
resmi berikut:

| Pola manual yang harus diganti | Komponen `shadcn/ui` resmi | Contoh pemakaian di proyek |
|---|---|---|
| `<span className="rounded-md bg-...">Aktif</span>` / status badge | `badge` (`Badge` + varian) | Status `Aktif`/`Nonaktif` di `UsersPage`, status & berkas digital di `ArchiveDetailPage`, badge `Dugaan` SPM |
| `<p role="alert" className="rounded-lg border ...">` / pesan sukses hijau | `alert` (`Alert`, `AlertTitle`, `AlertDescription`) | Notifikasi sukses/galat di `UsersPage`, `ImportPage`, `LoginPage`, peringatan jenis SPM `dugaan` |
| `<label className="text-sm font-medium">` berulang di form | `label` (`Label`) | Seluruh input pada `SearchForm`, `UsersPage`, `LoginPage`, `CompareForm` |
| `<table className="w-full ..."><thead>...<tbody>...` | `table` (`Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`) | Daftar akun & log aktivitas di `UsersPage`, riwayat impor di `ImportPage`, tabel di ruang penelitian |
| Dialog manual dari `radix-ui` di `AppShell.tsx` / konfirmasi | `dialog` atau `sheet` | Drawer navigasi mobile di `AppShell.tsx`, dialog konfirmasi aksi sensitif |
| Garis pemisah manual `border-t` / `divide-y` antar bagian | `separator` (`Separator`) | Pemisah antar grup menu sidebar atau seksi detail |

### 4.3 Prosedur Menambah Komponen `shadcn/ui`

1. Jalankan dari folder `frontend/`:
   ```powershell
   npx shadcn add badge alert label table
   ```
2. **Jangan pernah menjalankan `npx shadcn add --all`.** Pasang hanya komponen
   yang benar-benar digunakan.
3. Periksa `git diff` pada berkas baru di `src/components/ui/` sebelum commit;
   pastikan tidak menimpa penyesuaian lokal yang sudah ada dan lolos
   `npm run lint`, `npm run typecheck`, serta `npm run build` tanpa peringatan.
4. Gunakan varian `cva` (`class-variance-authority`) dan helper `cn()` dari
   `@/lib/utils` jika perlu menambah varian baru pada komponen `ui/`.

---

## 5. Aksesibilitas, Keamanan UI, & Pengujian

- **Semantic HTML & Aksesibilitas:** gunakan `<main>`, `<header>`, `<nav>`,
  `<section>`, `<dl>/<dt>/<dd>` untuk pasangan label-nilai, serta pastikan
  setiap input memiliki `<Label htmlFor="...">`. Tombol ikon wajib punya
  `aria-label`, dan indikator status harus memuat teks (bukan warna saja).
- **Responsivitas:** desain *mobile-first*; tabel lebar wajib dibungkus
  kontainer bergulir (`Table` bawaan shadcn sudah membungkus dengan
  `overflow-x-auto`) agar tidak menyebabkan *horizontal overflow* pada layar 390 px.
- **Keamanan tampilan:** rendernya teks arsip, ringkasan, dan detail log selalu
  sebagai teks React murni. **Dilarang menggunakan `dangerouslySetInnerHTML`**
  atau menyimpan sesi/token di `localStorage`.
- **Pengujian perilaku:** uji dengan Vitest + Testing Library melalui role dan
  label aksesibel (`getByRole`, `getByLabelText`, `findByText`), bukan memilih
  class CSS internal atau struktur DOM rapuh.

---

## 6. Gerbang Kualitas Wajib Sebelum Commit Refactor

Setiap langkah *refactor* dianggap selesai hanya jika seluruh perintah berikut
lulus dari `frontend/` (dan `pytest` lulus dari akar proyek):

```powershell
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
```

Dan dari akar proyek `D:\Coding\PM`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
