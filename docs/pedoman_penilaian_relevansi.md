# Pedoman Penilaian Relevansi Temu Kembali Arsip

**Dokumen Acuan Metodologis Penelitian Mandiri**  
Sistem Pencarian Arsip Menggunakan Fuzzy Matching dan Normalisasi Metadata Berbasis Website pada Dinas Perpustakaan dan Kearsipan Kota Palembang.

---

## 1. Tujuan & Prinsip Dasar
Pedoman ini disusun sebagai acuan objektif dan tertulis bagi peneliti dan arsiparis dalam memberikan penilaian relevansi (*relevance judgment*) terhadap hasil temu kembali arsip. 

Prinsip utama:
1. **Objektif & Konsisten:** Penilaian didasarkan semata-mata pada kecocokan substansi kueri dengan informasi arsip, bukan berdasarkan urutan posisi atau preferensi subjektif.
2. **Penilaian Buta (*Blind Judgment*):** Penilai tidak diberitahu algoritma pencarian apa yang menghasilkan dokumen tersebut maupun skor kemiripannya (*scoreless & method-blind*) untuk mencegah bias algoritma.
3. **Skala Biner:** Menggunakan keputusan biner:
   - `1` = **Relevan**
   - `0` = **Tidak Relevan**

---

## 2. Aturan Kesetaraan Relevansi (*Relevance Equivalence Rule*)
Dalam konteks arsip keuangan pemerintah daerah (khususnya berkas SPM/SP2D), satu proyek atau kegiatan belanja modal/operasional sering kali terdiri dari beberapa berkas arsip fisik (misalnya termin I, termin II, atau kelengkapan berkas berbeda).

Oleh karena itu, diberlakukan **aturan kesetaraan mutlak**:
> **Arsip yang merujuk pada nomor SPM yang sama, ATAU memiliki substansi/uraian pekerjaan, pihak ketiga (rekanan), dan instansi yang sama dinilai SAMA-SAMA RELEVAN (1).**

Penilai dilarang menganggap satu berkas relevan dan berkas pasangannya tidak relevan hanya karena perbedaan nomor berkas atau tanggal penginputan, selama substansi kegiatan/SPM-nya identik.

---

## 3. Kriteria Penilaian Berdasarkan Jenis Kueri

### 3.1 Kueri Topik / Uraian Kegiatan (Misal: *"rehabilitasi pasar"*, *"pengadaan alat tulis"*)
- **Relevan (1):**
  - Arsip memuat uraian pekerjaan, kegiatan, atau belanja yang secara spesifik membahas topik yang dicari.
  - Sinonim wajar atau singkatan resmi yang semakna (misal: *"renovasi"* terhadap kueri *"rehabilitasi"* jika merujuk objek yang sama).
- **Tidak Relevan (0):**
  - Arsip hanya memuat kata yang sama secara kebetulan tetapi berbeda kegiatan (misal: kueri *"pasar"* mencocokkan *"pemasaran"* atau *"pasar hewan"* padahal kueri menargetkan *"pasar tradisional kuto"*).
  - Arsip dari sektor yang sepenuhnya berbeda.

### 3.2 Kueri Nomor SPM / Kode Surat (Misal: *"158/LS"*, *"037/SPM-LS/RSUD/2009"*, *"446/BT/5/P"*)
- **Relevan (1):**
  - Arsip memuat nomor SPM yang dicari secara persis atau varian penulisan dari nomor SPM tersebut (misal kueri *"037/SPM - LS"* cocok dengan arsip bernomor *"037/LS/RSUD/2009"*).
  - Arsip yang merupakan kelanjutan berkas dari SPM yang sama.
- **Tidak Relevan (0):**
  - Arsip dengan nomor urut atau tahun yang berbeda (misal kueri *"158"* tahun 2007 mencocokkan *"158"* tahun 2003 pada dinas yang berbeda).

### 3.3 Kueri Nama Pihak Ketiga / Rekanan (Misal: *"CV Contoh Mandiri"*, *"PT Maju Bersama"*)
- **Relevan (1):**
  - Seluruh arsip pembayaran/pekerjaan yang melibatkan badan usaha/pihak yang dicari, baik sebagai pelaksana pekerjaan maupun penerima hak bayar.
- **Tidak Relevan (0):**
  - Arsip yang melibatkan badan usaha lain meskipun memiliki kemiripan kata umum (misal kueri *"CV Mandiri Jaya"* tidak relevan untuk *"CV Mandiri Perkasa"*).

### 3.4 Kueri Campuran / Spesifik (Misal: *"CV Contoh Mandiri 2021"*, *"rehabilitasi pasar 1999"*)
- **Relevan (1):**
  - Arsip memenuhi kombinasi kedua entitas informasi (pihak + kurun waktu, atau kegiatan + tahun).
- **Tidak Relevan (0):**
  - Arsip hanya memenuhi satu unsur sementara unsur pembatas lainnya bertentangan (misal kegiatan cocok tetapi tahun pelaksanaan berbeda jauh).

---

## 4. Prosedur Penilaian Mandiri & Verifikasi Arsiparis

1. **Penarikan Pool Buta (*Blind Pooling*):**
   - Top-10 dokumen dari masing-masing 5 metode pencarian (LIKE, Levenshtein, Jaro-Winkler, Token Set, N-gram Dice) digabungkan menjadi satu pool per kueri.
   - Dokumen diacak urutannya menggunakan seed tetap, tanpa menampilkan nama algoritma maupun skor.
2. **Penilaian oleh Peneliti:**
   - Peneliti membaca teks ringkasan arsip dan mengisi kolom relevansi (`1` atau `0`) sesuai pedoman ini pada berkas spreadsheet/CSV.
3. **Verifikasi Sampel oleh Arsiparis:**
   - Arsiparis dinas memeriksa sampel acak sebesar **20% hingga 30%** dari total kueri yang telah dinilai.
   - Arsiparis memberikan penilaian independen tanpa melihat penilaian peneliti sebelumnya.
4. **Perhitungan Persentase Kesepakatan (*Percentage Agreement*):**
   - Dihitung persentase kecocokan penilaian:
     $$\text{Agreement} = \frac{\text{Jumlah kesepakatan identik}}{\text{Total sampel yang diverifikasi}} \times 100\%$$
   - Persentase kesepakatan wajib dilaporkan secara transparan pada naskah laporan penelitian mandiri.
5. **Penanganan Dokumen Tidak Terambil dalam Pool:**
   - Seluruh dokumen di luar pool diasumsikan **Tidak Relevan (0)** sesuai standar umum *Cranfield / TREC evaluation methodology*.
   - Dokumen di top-10 yang belum dinilai (*unjudged in top-10*) dicatat dan dinilai secara buta sebelum evaluasi akhir.
