# Protokol Set Uji v2 — Desain Gangguan Terkontrol

**Status:** dibekukan sebelum kueri v2 dibangkitkan (lihat riwayat git berkas ini).
**Pengganti:** set uji v1 (tag git `testset-v1`), yang dinilai cacat desain. Rinciannya ada di Bagian 7.

---

## 1. Unit analisis

- **Kueri dasar (*base query*)** = satu kebutuhan informasi yang diturunkan dari satu arsip asal.
- **Varian** = kueri dasar yang diberi tepat satu jenis gangguan, atau tanpa gangguan.
- Semua varian dari satu kueri dasar **berbagi satu set penilaian relevansi**, karena kebutuhan informasinya sama.
- Uji statistik memakai **kueri dasar** sebagai unit independen. Skor kueri dasar = rata-rata skor seluruh variannya.

## 2. Komposisi

| Parameter | Nilai |
|---|---|
| Jumlah kueri dasar | 40 (10 per jenis: `topik`, `nomor_spm`, `pihak`, `campuran`) |
| Varian per kueri dasar | 7: `tanpa_gangguan`, `typo`, `singkatan`, `spasi_tanda_baca`, `urutan_kata`, `kata_hilang`, `ejaan_varian` |
| Pengecualian | `urutan_kata` **tidak berlaku** untuk `nomor_spm` (menukar bagian nomor surat tidak realistis), sehingga total varian = 40 × 7 − 10 = **270** |
| Split | Per kueri dasar, berstrata jenis: **3 tuning + 7 test per jenis** (12 tuning / 28 test) |
| Seed | 42 |

## 3. Aturan pembentukan kueri dasar

1. **Spesifisitas:** kueri dasar bersih cocok dengan **1 sampai 5 arsip** pada korpus (termasuk arsip asal).
   - `topik` / `campuran`: semua token bermakna kueri muncul pada ringkasan arsip (dan tahun cocok untuk `campuran` bertahun).
   - `nomor_spm`: nomor SPM ternormalisasi sama persis.
   - `pihak`: nama pihak ternormalisasi sama persis.
2. **`topik`:** 3–5 kata objek pekerjaan yang berurutan dari ringkasan arsip asal. Bagian yang dibuang:
   - kepala klasifikasi (`SPM Pembangunan 2002 -`);
   - frasa pembayaran (`Pembayaran termin ke I dan II atas pekerjaan`, `uang muka`, dsb.);
   - nama pihak (CV/PT);
   - ekor administratif (`No SPM`, `No SP2D`, `Tanggal`, `Jumlah`, `Rp`);
   - kata fungsi (`atas`, `dan`, `di`, `pada`, `untuk`, `keperluan`, `kota`, `palembang`, `plg`, …).
3. **`campuran`:** 2–3 kata objek pekerjaan + tahun arsip. Tidak boleh ada token ganda.
4. **`nomor_spm` / `pihak`:** nilai hasil ekstraksi metadata arsip asal, apa adanya.
5. **Anti-kebocoran:** dua kueri dasar tidak boleh berbagi arsip asal, nomor SPM, maupun nama pihak.

## 4. Aturan validitas varian (diperiksa otomatis)

| Gangguan | Syarat lolos |
|---|---|
| `typo` | Jumlah token sama; tepat 1 token berubah dengan jarak Damerau-Levenshtein 1 |
| `singkatan` | Jumlah token sama; tepat 1 token dipendekkan (singkatan kamus atau pemotongan awalan) |
| `spasi_tanda_baca` | Huruf/angka identik dengan kueri dasar; hanya spasi atau tanda baca yang berubah |
| `urutan_kata` | Multiset token sama; urutan berbeda |
| `kata_hilang` | Token = token kueri dasar dikurangi tepat 1 token (atau 1 bagian nomor SPM) |
| `ejaan_varian` | Jumlah token sama; tepat 1 token diganti varian ejaan (kamus ejaan atau pertukaran vokal u/o, e/i) |
| Semua | Teks varian ≠ teks kueri dasar |

Varian yang gagal dibangkitkan ulang dengan seed berikutnya (maksimal 25 kali). Jika tetap gagal, kueri dasar **ditolak** dan diganti kandidat berikutnya dari urutan acak yang sama. Semua penolakan dicatat di laporan pembangkitan.

## 5. Penilaian relevansi

- **Pool ronde 1:** gabungan top-10 dari LIKE dan 4 metode fuzzy (bobot seragam) atas **seluruh varian** kueri dasar, ditambah arsip asal, lalu diacak tanpa label metode dan skor.
- **Pool ronde 2:** top-10 konfigurasi bobot hasil tuning yang belum dinilai. Target: **unjudged@10 = 0**.
- **Penilaian buta:** penilai melihat kueri dasar dan deskripsi kebutuhan informasi, tanpa nama metode, skor, peringkat, atau penanda arsip asal.
- **Rubrik:** mengikuti [pedoman_penilaian_relevansi.md](pedoman_penilaian_relevansi.md) Bagian 2.1–2.4, dengan satu perubahan:
  - Relevansi ditentukan oleh **kebutuhan informasi kueri dasar**, bukan oleh teks varian bergangguan. Aturan *wildcard* `kata_hilang` (Bagian 2.5) **tidak berlaku** di v2.
- **Kesepakatan antarpenilai:** pegawai dinas menilai ulang secara independen ±20% pasangan (sampel acak berstrata jenis kueri). Dilaporkan sebagai persentase kesepakatan dan Cohen's Kappa.

## 6. Analisis yang direncanakan

1. **Kinerja utama (test, n = 28 kueri dasar):** MRR@10, P@5, R@10, Hit@10, latensi, dengan bootstrap 95% CI (2.000 iterasi).
2. **Hipotesis utama:** model terbaik dipilih **hanya dari split tuning**, lalu dibandingkan dengan LIKE memakai Wilcoxon signed-rank dua sisi (α = 0,05). Pembanding eksploratori 4 metode dikoreksi Holm.
3. **Ketahanan terhadap gangguan:** ΔMRR@10 = MRR(varian) − MRR(tanpa_gangguan) dari kueri dasar yang sama, per metode × gangguan, dengan bootstrap 95% CI. Analisis ini deskriptif dan tidak dikoreksi untuk inferensi.
4. **Rincian jenis kueri × gangguan:** setiap sel n = 7 kueri dasar (deskriptif).

## 7. Alasan penggantian v1

| Masalah v1 | Dampak |
|---|---|
| Topik diambil dari 4 token pertama ringkasan, yaitu kepala klasifikasi `SPM Pembangunan YYYY` | Kueri cocok dengan 55–138 arsip, padahal yang relevan hanya 1 |
| `campuran` = topik + tahun, padahal topik sudah memuat tahun | Token ganda (`2002 2002`) |
| Jenis kueri dan gangguan dipasangkan dengan `idx % 4` dan `idx % 7` | Efek gangguan tercampur dengan tingkat kesulitan jenis kueri |
| Gangguan tidak diverifikasi | Salah ketik bawaan arsip (`terminj`) dilabeli sebagai gangguan buatan |
| `urutan_kata` menukar bagian nomor SPM | Kueri tidak realistis |
| Pool hanya berisi LIKE + bobot seragam | Hingga 10/10 hasil top-10 konfigurasi tuned belum dinilai |
