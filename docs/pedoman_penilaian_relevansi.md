# Pedoman Penilaian Relevansi Temu Kembali Arsip

**Dokumen Acuan Metodologis Penelitian Mandiri**  
Sistem Pencarian Arsip Menggunakan Fuzzy Matching dan Normalisasi Metadata Berbasis Website pada Dinas Perpustakaan dan Kearsipan Kota Palembang.

---

## 1. Tujuan & Prinsip Dasar
Pedoman ini disusun sebagai acuan objektif dan tertulis bagi peneliti dan arsiparis dalam memberikan
penilaian relevansi (*relevance judgment*) terhadap hasil temu kembali arsip.

Prinsip utama:
1. **Objektif & Berbasis Teks Asli:** Penilaian didasarkan semata-mata pada teks ringkasan asli (`summary_raw`), **bukan** pada kolom hasil ekstraksi komputer atau metadata turunan.
2. **Penilaian Buta (*Blind Judgment*):** Penilai tidak diberitahu metode pencarian apa yang menghasilkan dokumen tersebut, tidak ada skor kemiripan, peringkat, maupun penanda arsip asal (*scoreless & method-blind*) untuk mencegah bias algoritma.
3. **Skala Keputusan:**
   - **`is_relevant = 1`** : Relevan.
   - **`is_relevant = 0`** : Tidak Relevan.
   - **`ragu = 1`** : Kolom opsional (isi `1` jika penilai ragu/ambigu terhadap substansi arsip; kosongkan jika yakin).

---

## 2. Kriteria Relevansi Berdasarkan Jenis Kueri

Penilaian wajib mengikuti kriteria ketat berikut sesuai jenis kueri:

### 2.1 Kueri Nomor SPM (`nomor_spm`)
- **Relevan (1):**
  - Hanya arsip yang merujuk pada **nomor SPM yang sama persis** dengan yang dicari (termasuk variasi format tanda baca/spasi dan salinan berkas duplikat dari SPM yang sama).
- **Tidak Relevan (0):**
  - Arsip dengan nomor SPM yang berbeda, meskipun berasal dari OPD/dinas yang sama atau tahun yang sama.

### 2.2 Kueri Topik / Pekerjaan (`topik`)
- **Relevan (1):**
  - Arsip yang memuat **pekerjaan atau transaksi pembayaran yang sama** secara spesifik sebagaimana ditargetkan oleh kata kunci kueri.
  - Sinonim wajar atau variasi ejaan resmi yang merujuk pada objek pekerjaan yang sama.
- **Tidak Relevan (0):**
  - Arsip pekerjaan lain meskipun memiliki kesamaan kata umum.
  - **Catatan Khusus Termin Pembayaran:** Jangan menyamakan termin yang berbeda jika kueri secara eksplisit menyebut termin tertentu (misal kueri *"termin I"* tidak relevan untuk arsip *"termin II"*). Pembayaran dianggap sama jika merujuk pada paket pekerjaan dan termin yang dimaksud kueri.

### 2.3 Kueri Nama Pihak Ketiga (`pihak`)
- **Relevan (1):**
  - Seluruh arsip pekerjaan atau pembayaran yang melibatkan **pihak ketiga / rekanan yang sama** (badan usaha CV/PT atau instansi yang sama).
- **Tidak Relevan (0):**
  - Arsip yang melibatkan badan usaha atau pihak lain, meskipun terdapat kata umum yang mirip (misal *"CV Mandiri Jaya"* tidak relevan untuk *"CV Mandiri Perkasa"*).

### 2.4 Kueri Campuran (`campuran`)
- **Relevan (1):**
  - Wajib **memenuhi kedua unsur secara bersamaan** (misal pihak + tahun, atau pekerjaan + tahun, atau pihak + pekerjaan).
- **Tidak Relevan (0):**
  - Arsip yang hanya memenuhi salah satu unsur tetapi bertentangan pada unsur lainnya.

---

## 3. Penanganan Berkas Penilaian & Sampel Pilot

1. **Berkas Penilaian Utama:**
   - Seluruh penilaian dilakukan pada berkas utama: [`output/relevance_pool.csv`](file:///D:/Coding/PM/output/relevance_pool.csv).
2. **Berkas Pilot (5 Kueri Pertama):**
   - Berkas [`output/relevance_pool_pilot_5.csv`](file:///D:/Coding/PM/output/relevance_pool_pilot_5.csv) adalah potongan 5 kueri pertama dari berkas utama yang digunakan untuk mengukur waktu penilaian per baris dan kalibrasi awal.
   - **Konsistensi Penilaian:** Skrip pembangun set uji akan menolak proses jika terdapat ketidakkonsistenan penilaian antara berkas pilot dan berkas utama.
3. **Kolom Penanda Keraguan (`ragu`):**
   - Jika penilai merasa deskripsi ringkasan terlalu minim atau ambigu, isi `ragu` dengan `1`.
   - Jumlah baris ragu dilaporkan secara transparan pada ringkasan set uji dan laporan akhir.

---

## 4. Verifikasi Independen oleh Arsiparis

1. **Sampel Verifikasi Berstrata (100–150 Baris):**
   - Sebanyak 100 hingga 150 baris ditarik secara acak berstrata dari seluruh jenis kueri (`nomor_spm`, `topik`, `pihak`, `campuran`) ke dalam berkas [`output/relevance_verification_sample.csv`](file:///D:/Coding/PM/output/relevance_verification_sample.csv).
2. **Penilaian Independen Buta:**
   - Arsiparis mengisi kolom `is_relevant` secara independen tanpa melihat jawaban peneliti.
3. **Perhitungan Persentase Kesepakatan (*Percentage Agreement*):**
   - Skrip menghitung persentase kesepakatan antar-penilai:
     $$\text{Agreement} = \frac{\text{Jumlah kesepakatan identik}}{\text{Total baris verifikasi}} \times 100\%$$
   - Hasil kesepakatan dicatat sebagai bukti reliabilitas set uji dalam laporan ilmiah.
