# Pedoman Audit Ekstraksi Metadata & Petunjuk Pengisian

**Dokumen Standar Operasional Prosedur Evaluasi Ekstraksi Metadata**  
Sistem Pencarian Arsip Berbasis Website pada Dinas Perpustakaan dan Kearsipan Kota Palembang.

---

## 1. Ruang Lingkup & Tujuan
Audit ekstraksi metadata bertujuan mengukur performa modul pembersih dan ekstraktor metadata
berbasis ekspresi reguler (versi `v1.0.0`) terhadap 5 field metadata:
1. `spm`: Nomor Surat Perintah Membayar (SPM).
2. `sp2d`: Nomor Surat Perintah Pencairan Dana (SP2D).
3. `date`: Tanggal dokumen (format YYYY-MM-DD).
4. `amount`: Nilai nominal rupiah (angka bulat murni).
5. `party`: Nama pihak ketiga, rekanan, atau kontraktor (CV/PT/dsb.).

Audit dilakukan pada:
- **Sampel Utama:** 100 baris acak berstrata (`output/audit_extraction_sample.csv`).
- **Sampel Kesepakatan (Reliabilitas Antar-Penilai):** 20 baris (`output/audit_agreement_sample.csv`).

---

## 2. Definisi Baku Nilai Penilaian (Verdict)

Setiap sel penilaian (`verdict_<field>`) **wajib** diisi dengan salah satu dari 4 pilihan kata baku berikut:

| Nilai Verdict | Definisi Operasional | Kategori Teoretis |
| :--- | :--- | :--- |
| **`benar`** | Hasil ekstraksi komputer sama persis dengan informasi yang ada pada teks ringkasan setelah spasi ganda dirapikan dan perbedaan huruf besar-kecil disamakan. | True Positive (TP) |
| **`salah`** | Komputer mengekstrak suatu nilai, namun nilai tersebut keliru, terpotong salah, menangkap teks yang bukan haknya, atau teks ringkasan sebenarnya tidak memuat field tersebut tetapi komputer salah mengekstraknya. | False Positive (FP) |
| **`terlewat`** | Teks ringkasan memuat informasi field tersebut secara jelas, namun komputer menghasilkan nilai kosong (gagal mengekstrak). | False Negative (FN) |
| **`tidak_ada_di_teks`** | Teks ringkasan memang tidak memuat informasi field tersebut, dan komputer juga menghasilkan nilai kosong. | True Negative (TN) |

> [!IMPORTANT]
> **Aturan Sel Kosong:**  
> Seluruh baris dan seluruh kolom `verdict_*` **wajib diisi**. Sel yang dibiarkan kosong
> diartikan sebagai *belum dinilai* dan akan **ditolak secara otomatis** oleh skrip evaluasi.

---

## 3. Matriks Keputusan Berdasarkan Kondisi

Untuk mempermudah penilai, gunakan matriks berikut saat memeriksa satu sel:

| Kondisi Informasi di Teks Ringkasan | Kondisi Hasil Ekstraksi Komputer | Nilai yang Harus Diketik |
| :--- | :--- | :--- |
| Ada di teks | Ada, dan isinya sama persis | **`benar`** |
| Ada di teks | Ada, tetapi salah/terpotong | **`salah`** |
| Ada di teks | Kosong (tidak terekstrak) | **`terlewat`** |
| Tidak ada di teks | Kosong | **`tidak_ada_di_teks`** |
| Tidak ada di teks | Ada (halusinasi/salah tangkap) | **`salah`** |

---

## 4. Petunjuk Teknis Pengisian pada Aplikasi Spreadsheet (Excel / LibreOffice)

1. **Format Sel Wajib Tipe Teks (*Text*):**
   - Sebelum mulai mengedit, pastikan semua kolom bertipe data **Teks (Text)**.
   - Jangan biarkan Excel mengubah format tanggal (misal `2008-10-15` berubah jadi `15/10/2008`)
     atau menghapus angka nol di depan nomor surat.
2. **Jangan Mengubah Kolom Asli:**
   - Kolom `sample_id`, `archive_id`, `summary_raw`, dan seluruh kolom `extracted_*`
     **dilarang keras diubah**. Skrip evaluasi memvalidasi integritas data asli melalui hash.
3. **Penyimpanan Berkas:**
   - Simpan berkas dengan format **CSV UTF-8 (Comma delimited) (*.csv)**.
   - Jangan gunakan format XLSX atau pemisah titik-koma (*semicolon* `;`).

---

## 5. Prosedur Perhitungan Metrik

Setelah lembar audit diisi lengkap, jalankan perintah:
```powershell
python -m scripts.evaluate_extraction_audit
```

Skrip akan melaporkan dua metrik utama untuk tiap field:
1. **Ketepatan (*Precision*):**
   $$\text{Ketepatan} = \frac{\text{benar}}{\text{benar} + \text{salah}}$$
   Mengukur seberapa andal hasil ekstraksi saat komputer mengeluarkan nilai.
2. **Keterambilan (*Recall*):**
   $$\text{Keterambilan} = \frac{\text{benar}}{\text{benar} + \text{terlewat}}$$
   Mengukur seberapa banyak informasi yang berhasil diambil dari seluruh data yang ada di teks.
3. **Interval Kepercayaan Wilson 95%:**
   Dihitung untuk ketepatan dan keterambilan untuk menjamin validitas statistik sampel.
4. **Persentase Kesepakatan (*Percentage Agreement*):**
   Dihitung pada 20 baris sampel ganda antara penilai 1 dan penilai 2.
