# Bukti Implementasi dan Keterlacakan Sistem (`PM-25`)

Dokumen ini menjadi sumber acuan tunggal untuk menyelaraskan naskah laporan penelitian dengan kode sumber, pengujian otomatis, dan artefak evaluasi yang benar-benar ada di repositori per **24 November 2026** (commit terakhir sebelum dokumen ini: `ba90f81`).

---

## 1. Status Implementasi Fitur & Teknologi Aktual

### A. Tumpukan Teknologi Terpasang

| Lapisan | Teknologi & Versi Aktual | Sumber Bukti |
|---|---|---|
| Backend Web & Auth | Python 3.14, Flask `3.1.3`, Flask-Login `0.6.3`, Waitress `3.0.2` | [requirements-web.txt](file:///d:/Coding/PM/requirements-web.txt) |
| Mesin Pencarian Fuzzy | RapidFuzz `3.14.6` (`levenshtein`, `jaro_winkler`, `token_set`, `ngram`) + pembanding `SQL LIKE` | [core/search/](file:///d:/Coding/PM/core/search/matchers/__init__.py) |
| Penyimpanan Lokal | SQLite (`instance/app.sqlite`) tanpa ORM via `services/db.py` | [services/db.py](file:///d:/Coding/PM/services/db.py) |
| Frontend Web | React `19.3.1`, TypeScript `~7.0.2` (strict), Vite `^8.3.6`, React Router `^8.5.2` | [package.json](file:///d:/Coding/PM/frontend/package.json) |
| Antarmuka & Grafik | Tailwind CSS v4, `shadcn/ui` (Radix UI), Lucide React `^1.77.0`, Recharts, Zod `^4.6.7`, TanStack Query `^5.108.2` | [package.json](file:///d:/Coding/PM/frontend/package.json) |
| Kualitas Kode & Uji | `pytest`, Vitest `^5.1.1`, Testing Library, `oxlint`, `prettier` | [BACKLOG.md](file:///d:/Coding/PM/docs/BACKLOG.md) |

### B. Pemisahan Jalur Aplikasi

| Ruang & Rute | Fitur Terimplementasi | Izin Akses |
|---|---|---|
| `/app/dashboard` | Statistik nyata korpus, pencarian cepat, info impor terakhir, arsip terbaru | Admin & Petugas |
| `/app/search` | Pencarian fuzzy bawaan server (`levenshtein` / `app_setting`) + filter OPD, tahun, status | Admin & Petugas |
| `/app/archives/:id` | Detail arsip, teks asli, metadata ekstraksi, status `dugaan`, grid lokasi fisik | Admin & Petugas |
| `/app/imports` | Impor salinan `.sql` terkontrol (`PM_IMPORT_DIR`), cadangan otomatis, riwayat | Admin |
| `/app/users` | Manajemen akun (tambah, aktif/nonaktif, reset sandi) & filter log aktivitas | Admin |
| `/app/status` | Pemeriksaan status layanan API | Admin & Petugas |
| `/app/research` | Ringkasan alur penelitian & pintasan tugas | Admin (ringkasan), Petugas (2 tugas) |
| `/app/research/compare` | Perbandingan berdampingan 5 metode (`LIKE` + 4 fuzzy) untuk satu kueri | Admin |
| `/app/research/evaluation` | Grafik Recharts + tabel metrik, bobot tuning, rincian per kueri, status validasi | Admin |
| `/app/research/agreement` | Kesepakatan 2 penilai relevansi & audit ekstraksi (Percentage Agreement, Cohen's kappa) | Admin |
| `/app/research/testsets` | Unggah, validasi anti-kebocoran split `tuning`/`test`, penguncian SHA-256 | Admin |
| `/app/research/relevance-admin` | Penugasan 2 penilai buta, migrasi CSV lama tanpa timpa, ekspor CSV | Admin |
| `/app/research/relevance` | Penilaian relevansi buta per akun + status ragu & riwayat revisi | Admin / Petugas ditugaskan |
| `/app/research/extraction-audit` | Penilaian audit ekstraksi 5 field (`spm`, `sp2d`, `date`, `amount`, `party`) | Admin / Petugas ditugaskan |
| `/app/research/spm-types` | Konfirmasi manual kamus kode SPM dari `dugaan` ke `terkonfirmasi` | Admin |
| `/app/research/quality` | Cakupan ekstraksi 5 field, status dugaan SPM, & daftar `data_issue` | Admin |
| `/app/research/duplicates` | Tinjauan pasangan kandidat duplikat non-destruktif beserta riwayat keputusan | Admin |

### C. Jejak Verifikasi & Paket Rilis Terbaru

- **Uji Backend (`.\.venv\Scripts\python.exe -m pytest -q`):** `278 passed, 5 skipped` (divergen/skip hanya pada tes integrasi tertentu bila prasyarat lokal opsional tidak aktif).
- **Uji & Build Frontend (`frontend/`):** `oxlint src` (0 warning, 0 error pada 122 berkas), `tsc -b` lulus, `vitest run` (`16` berkas uji, `50` tes lulus), `prettier --check .` lulus, dan `vite build` menghasilkan bundel produksi offline tanpa CDN.
- **Paket Rilis Waitress Terbaru (`scripts/build_web_release.py`):**
  - Berkas: `output/releases/pm-web-20261124-080825.zip` (681.711 byte, 91 entri, tanpa `node_modules` atau data penelitian)
  - SHA-256: `e20df9a2a4bb8956fcb9b4cb12bfdff09ae96b3cd14041e678c8d22417a7ca6b`
- **Jejak Commit Utama (`PM-15` s.d. `PM-27`):** `3e52b1c` (`PM-15`), `2a9eb71` (`PM-16`), `a03b7d6` (`PM-17`), `8f270e0` (`PM-18`), `0e0dedb` (`PM-26`), `ef5ab45` (`PM-27`), `1cd9965` (`PM-21`), `e7959ca` (`PM-19`), `e3ea341` (beranda penelitian), `32946e8` / `c864d8b` / `0f54ac5` / `909585a` (`PM-20`), `8cae564` (instrumen `PM-22`), `8fadc48` (`PM-23`), `594aa70` / `ba90f81` (`PM-24`).

---

## 2. Hasil Eksperimen Terukur (`output/colab_bundle`) — Status `draft`

Angka pada bagian ini dihitung langsung dari artefak [run_meta.json](file:///d:/Coding/PM/output/colab_bundle/run_meta.json), [per_query_results.csv](file:///d:/Coding/PM/output/colab_bundle/per_query_results.csv), [tuning_results.csv](file:///d:/Coding/PM/output/colab_bundle/tuning_results.csv), dan [audit_summary.json](file:///d:/Coding/PM/output/colab_bundle/audit_summary.json). Status artefak tercatat sebagai **`draft`** karena diekspor dengan `tree_clean = false` (`commit_sha`: `2a5e3dc9b958f60e9134ea341b7bd59f487f6b96`, `exported_at`: `2026-11-09T02:56:48Z`) dan kesepakatan penilai kedua masih `pending_second_rater`.

- **Dataset & Set Uji:** `seed = 42`, `data_hash = ae5df7caf0da...`, `testset_hash = de6c3499eed2...`, total **112 varian kueri** (**56 kueri dasar**) terbagi atas **32 kueri tuning** (16 dasar) dan **80 kueri test** (40 dasar) dengan **0 kebocoran** lintas split dan `manifest.sha256` valid.
- **Validasi Realisme Kueri Sintetis (`run_meta.json`):** 24 sampel kueri (`21,4%`), dinilai realistis oleh penilai 1 (`100,0%`), penilai 2 (`95,8%`), dan disepakati kedua penilai (`95,8%`).

### A. Ringkasan Metrik pada Split Test (80 kueri)

| Metode & Konfigurasi | P@5 | R@10 | MRR@10 | Hit@5 | Median Latensi (ms) |
|---|---:|---:|---:|---:|---:|
| `like_baseline (baseline)` | 0,1425 | 0,3479 | 0,3667 | 37,5% | 1,6 |
| `levenshtein (equal)` | 0,2825 | 0,6830 | 0,6367 | 71,3% | 128,3 |
| `levenshtein (tuned)` | 0,4175 | 0,9185 | 0,9187 | 98,8% | 90,5 |
| `jaro_winkler (equal)` | 0,3375 | 0,8191 | 0,7133 | 77,5% | 117,6 |
| `jaro_winkler (tuned)` | 0,4350 | 0,9333 | 0,9583 | 98,8% | 90,8 |
| `token_set (equal)` | 0,3800 | 0,8153 | 0,8040 | 87,5% | 51,9 |
| `token_set (tuned)` | 0,4500 | 0,9347 | 0,9854 | 100,0% | 11,1 |
| `ngram (equal)` | 0,3900 | 0,8711 | 0,8407 | 90,0% | 465,9 |
| `ngram (tuned)` | 0,4300 | 0,9333 | 0,9625 | 98,8% | 100,1 |

### B. Bobot Optimal Hasil Grid Search pada Split Tuning (32 kueri, 66 kombinasi per matcher)

| Matcher | Bobot (Ringkasan / SPM / Pihak) | MRR@10 Tuning | P@5 Tuning | Unjudged@10 |
|---|---|---:|---:|---:|
| `levenshtein` | `0,7 / 0,1 / 0,2` | 0,9635 | 0,3875 | 0 |
| `jaro_winkler` | `0,8 / 0,1 / 0,1` | 1,0000 | 0,3875 | 0 |
| `token_set` | `0,6 / 0,2 / 0,2` | 1,0000 | 0,3875 | 0 |
| `ngram` | `0,6 / 0,3 / 0,1` | 1,0000 | 0,3875 | 0 |

### C. Audit Ekstraksi 100 Sampel (`audit_summary.json`, `extractor_version = v1.0.0`)

| Field | Benar | Salah | Tidak Ada di Teks | Terlewat | Ketepatan (Wilson CI 95%) | Keterambilan (Wilson CI 95%) |
|---|---:|---:|---:|---:|---|---|
| `spm` | 75 | 2 | 23 | 0 | 97,4% (91,0%–99,3%) | 100,0% (95,1%–100,0%) |
| `sp2d` | 24 | 2 | 74 | 0 | 92,3% (75,9%–97,9%) | 100,0% (86,2%–100,0%) |
| `date` | 71 | 0 | 21 | 8 | 100,0% (94,9%–100,0%) | 89,9% (81,3%–94,8%) |
| `amount` | 72 | 1 | 23 | 4 | 98,6% (92,6%–99,8%) | 94,7% (87,2%–97,9%) |
| `party` | 38 | 0 | 50 | 12 | 100,0% (90,8%–100,0%) | 76,0% (62,6%–85,7%) |

---

## 3. Data Lapangan yang Belum Lengkap (Dilarang Mengklaim Hasil Akhir)

1. **Kesepakatan Penilai Kedua (`PM-19`):** berkas [agreement_summary.json](file:///d:/Coding/PM/output/colab_bundle/agreement_summary.json) masih berstatus `pending_second_rater` (`n_samples: 120`, `cohen_kappa: null`). Metrik kesepakatan baru boleh dicantumkan sebagai hasil akhir setelah penilai kedua menyelesaikan penilaian di `/app/research/relevance` dan laporan dihitung ulang melalui `/app/research/agreement` atau `scripts/evaluate_relevance_agreement.py`.
2. **Uji Lapangan UAT & Skor SUS (`PM-22`):** instrumen tugas dan kalkulator sudah siap di [instrumen_uat_sus.md](file:///d:/Coding/PM/docs/instrumen_uat_sus.md) dan [evaluate_uat_sus.py](file:///d:/Coding/PM/scripts/evaluate_uat_sus.py), namun belum ada sesi peserta aktual. **Tidak ada angka SUS atau kelulusan UAT yang boleh ditulis sebelum CSV aktual diisi.**
3. **Naskah Laporan Eksternal (`D:\Dokumen Penelitian Mandiri`):** sesuai [AGENTS.md](file:///d:/Coding/PM/AGENTS.md), berkas Word di folder tersebut hanya boleh diubah apabila pengguna memintanya secara eksplisit setelah hasil `PM-19` dan `PM-22` terkumpul.
