# Instrumen Uji Lapangan, UAT/Black Box, dan Kuesioner SUS (`PM-22`)

Dokumen ini menjadi pedoman persiapan, daftar tugas uji, kuesioner System Usability Scale (SUS), dan aturan pencatatan untuk evaluasi penerimaan pengguna (petugas arsip dan admin) pada aplikasi **SIMANIS**.

## 1. Aturan Privasi & Kejujuran Hasil

- **Tidak ada angka contoh yang diperlakukan sebagai hasil.** Seluruh ringkasan harus dihitung dari sesi uji lapangan nyata melalui skrip [evaluate_uat_sus.py](file:///d:/Coding/PM/scripts/evaluate_uat_sus.py).
- **Data pribadi tetap di luar Git.** Gunakan kode peserta anonim (`P01`, `P02`, `A01`, dst.). Jangan mencatat nama lengkap, NIP, nomor telepon, atau alamat surel di berkas hasil maupun di repositori.
- Simpan berkas CSV jawaban mentah di folder lokal yang diabaikan Git (mis. `output/uat_sus/`).

## 2. Daftar Periksa Persiapan Sebelum Sesi

1. Pastikan skema SQLite lokal terbaru sudah siap:
   ```powershell
   .\.venv\Scripts\python.exe -m flask --app wsgi db upgrade
   ```
2. Pastikan aset produksi React (`frontend/dist/`) telah terbangun agar sesi dapat berjalan offline di intranet/laptop uji tanpa Node.js.
3. Siapkan akun uji terpisah (`petugas` dan `admin`) melalui CLI `flask --app wsgi user create` atau halaman admin `/app/users`.
4. Hasilkan template CSV kosong sebelum sesi dimulai:
   ```powershell
   .\.venv\Scripts\python.exe scripts/evaluate_uat_sus.py --init-templates --output-dir output/uat_sus
   ```

## 3. Skenario Tugas Uji Fungsional (Black Box / UAT)

Catat status setiap tugas sebagai `lulus`, `lulus_dengan_catatan`, atau `gagal`, beserta durasi (detik) dan catatan kendala.

### A. Skenario Petugas (`/app`)

| ID | Tugas | Langkah Ringkas | Hasil Diharapkan |
|---|---|---|---|
| `T01` | Login akun petugas | Masuk di `/login` dengan akun petugas | Masuk ke `/app/dashboard`; menu sidebar hanya menampilkan menu operasional (`Dashboard`, `Pencarian`) tanpa menu Admin maupun menu Ruang Penelitian |
| `T02` | Dashboard & info pembaruan | Periksa ringkasan jumlah arsip, tanggal pembaruan data, dan daftar arsip terbaru | Angka statistik tampil dari data nyata; tautan arsip terbaru mengarah ke detail arsip |
| `T03` | Pencarian cepat & pencarian penuh | Ketik kata kunci (termasuk salah ketik ringan/typo) dari Dashboard atau `/app/search` | Hasil pencarian fuzzy tampil tanpa dropdown algoritma penelitian; filter OPD/tahun/status bekerja dengan baik |
| `T04` | Detail arsip & lokasi fisik | Buka salah satu arsip dari hasil pencarian (`/app/archives/:id`) | Menampilkan teks asli dokumen, metadata SPM/SP2D/nominal/pihak, serta grid lokasi fisik (blok, rak, baris, boks) secara jelas |
| `T05` | Pembatasan akses rute admin | Coba akses langsung `/app/imports`, `/app/users`, atau `/app/research/evaluation` | Sistem menolak akses (tampilan dilarang / 403) tanpa membocorkan data admin |
| `T06` | Keluar sesi | Klik tombol `Keluar` di sidebar lalu coba tekan tombol Back / akses `/app/search` | Sesi berakhir dan pengguna diarahkan kembali ke `/login` |
| `T07` | Tugas penilaian penelitian (bila ditugaskan) | Buka `/app/research/relevance` atau `/app/research/extraction-audit` | Penilai hanya melihat ringkasan asli dan form isiannya sendiri, tanpa bocoran skor metode atau jawaban penilai lain |

### B. Skenario Admin (`/app` & `/app/research`)

| ID | Tugas | Langkah Ringkas | Hasil Diharapkan |
|---|---|---|---|
| `A01` | Kelola akun & log aktivitas | Buka `/app/users`, buat akun uji baru, reset sandi, periksa log aktivitas | Akun tersimpan, kata sandi tidak tampil di respons/log, dan akun sendiri tidak dapat dinonaktifkan |
| `A02` | Impor salinan terkontrol | Buka `/app/imports`, pilih file dump dari folder resmi, tinjau pratinjau | Pratinjau dan riwayat impor tampil sesuai data nyata |
| `A03` | Ringkasan penelitian & kesepakatan | Buka `/app/research` dan `/app/research/agreement` | Status validasi set uji, penilaian dua penilai, dan audit ekstraksi tampil; tetap bertanda tertunda jika belum lengkap |
| `A04` | Hasil evaluasi & perbandingan | Buka `/app/research/evaluation` dan `/app/research/compare` | Grafik dan tabel metrik tampil dengan split `Test`/`Tuning` terpisah serta dapat diekspor ke CSV/JSON |

## 4. Kuesioner System Usability Scale (SUS — 10 Butir)

Peserta mengisi setelah menyelesaikan seluruh skenario tugas. Skala: **1 = Sangat tidak setuju**, **2 = Tidak setuju**, **3 = Netral**, **4 = Setuju**, **5 = Sangat setuju**.

1. Saya merasa akan sering menggunakan sistem pencarian arsip ini.
2. Saya merasa sistem ini terlalu rumit padahal bisa lebih sederhana. *(butir negatif)*
3. Saya merasa sistem ini mudah digunakan.
4. Saya merasa memerlukan bantuan teknisi untuk dapat menggunakan sistem ini. *(butir negatif)*
5. Saya merasa berbagai fitur di sistem ini terintegrasi dengan baik.
6. Saya merasa terlalu banyak hal yang tidak konsisten pada sistem ini. *(butir negatif)*
7. Saya membayangkan sebagian besar petugas dapat mempelajari sistem ini dengan cepat.
8. Saya merasa sistem ini merepotkan untuk digunakan. *(butir negatif)*
9. Saya merasa percaya diri saat menggunakan sistem ini.
10. Saya perlu mempelajari banyak hal terlebih dahulu sebelum dapat memakai sistem ini dengan lancar. *(butir negatif)*

### Perhitungan & Rekap Otomatis

Rumus Brooke (1996):

$$\text{SUS} = 2{,}5 \times \left(\sum_{i \in \{1,3,5,7,9\}} (q_i - 1) + \sum_{j \in \{2,4,6,8,10\}} (5 - q_j)\right)$$

Setelah `output/uat_sus/uat_results.csv` dan `output/uat_sus/sus_responses.csv` diisi sesuai kode peserta anonim, jalankan:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_uat_sus.py `
  --uat-csv output/uat_sus/uat_results.csv `
  --sus-csv output/uat_sus/sus_responses.csv `
  --output-json output/uat_sus/uat_sus_summary.json
```

## 5. Batas Interpretasi Hasil

- Hasil UAT dan SUS hanya menggambarkan pengalaman peserta pada sesi uji lapangan aktual dengan dataset uji yang tersedia saat itu, bukan pembuktian statistik berskala populasi besar.
- Kegagalan tugas (`status = gagal`) wajib ditindaklanjuti menjadi catatan masalah atau perbaikan kode sebelum klaim kelayakan operasional ditulis pada laporan akhir (`PM-25`).
