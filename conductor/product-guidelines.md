# Product Guidelines: Sistem Pencarian Arsip pada e-Arsip (SIMANIS)

## 1. Gaya Penulisan & Nada Komunikasi (Tone of Voice)
- **Resmi & Lugas:** Menggunakan Bahasa Indonesia baku sesuai kaidah tata naskah dinas kearsipan Pemerintah Kota Palembang. Pesan disusun ringkas, sopan, dan langsung ke inti.
- **Konsistensi Istilah Kearsipan:** Mengikuti terminologi yang sudah dipakai pada aplikasi e-Arsip eksisting (*In Aktif, Statis, Musnah, Nomor Berkas, Kode Klasifikasi, OPD*).
- **Pemisahan Konteks Istilah:** 
  - Istilah metrik ilmiah (*Precision@5, Recall@10, MRR@10, Hit Rate, Dice Coefficient*) dipertahankan dalam bahasa aslinya dan hanya ditampilkan pada halaman Admin/Evaluasi.
  - Istilah khusus bagi pengguna umum (seperti skor kemiripan atau badge "Dugaan") wajib dilengkapi *tooltip* penjelasan singkat.
- **Label & Aksi:** Label tombol menggunakan kata kerja operasional yang konsisten (*Cari, Terapkan Filter, Reset, Simpan, Unduh, Nilai*).
- **Pesan Galat & Keamanan:**
  - Form login menggunakan pesan netral saat autentikasi gagal (*"Nama pengguna atau kata sandi salah"*) untuk mencegah *user enumeration*.
  - Galat sistem (403, 404, 500) disajikan dalam bahasa ramah pengguna tanpa memaparkan pesan galat teknis atau *stack trace*.

## 2. Standar Desain Visual & Tema
- **Gaya Visual "Pemerintahan Modern":** Desain antarmuka bersih, berwibawa, dan profesional dengan palet warna biru dinas (*navy/slate*) dan aksen semantik fungsional.
- **Tipografi:** Menggunakan font modern **Inter** yang dihosting secara lokal.
- **Satu Tema Terang (Light Mode Only):** Menggunakan Bootstrap 5 yang dikustomisasi melalui CSS variables terstruktur. Mode gelap (*dark mode*) berada di luar lingkup penelitian.
- **Sistem Spasi & Bentuk:** Menerapkan kelipatan 4px/8px secara konsisten untuk padding dan margin; border-radius seragam pada kartu dan tombol.
- **Hierarki Informasi & Status:**
  - Status arsip (*In Aktif, Statis, Musnah*) dan badge *"Dugaan"* untuk jenis SPM menggunakan warna semantik yang wajib disertai teks atau ikon indikator (tidak mengandalkan warna semata demi aksesibilitas).
  - Prioritas polesan visual diutamakan pada halaman **Pencarian** dan **Detail Arsip**. Halaman administrasi dititikberatkan pada kejelasan tabel dan efisiensi fungsional.

## 3. Prinsip Pengalaman Pengguna (UX) Pencarian & Evaluasi
- **Penyorotan Relevansi:** Kata/token kueri yang cocok disorot (*highlight*) secara visual pada cuplikan ringkasan dokumen hasil pencarian.
- **Transparansi Hasil:** Setiap item hasil pencarian menampilkan:
  - Skor kemiripan beserta *tooltip* penjelas.
  - Jumlah total hasil dan pembatasan yang aktif (misalnya *"Menampilkan 10 hasil teratas"*).
  - Metadata hasil ekstraksi (No. SPM, Tanggal, Nominal Rp, Pihak); field yang gagal diekstrak ditandai secara eksplisit dengan label *"tidak terbaca"*.
- **Pencarian Cepat:** Form pencarian dapat dikirim langsung dengan tombol `Enter`, dan filter (OPD/Tahun) memiliki tombol *"Reset/Kosongkan"* yang mudah diakses.
- **Umpan Balik Nol Hasil:** Ketika pencarian tidak menghasilkan dokumen, tampilkan pesan informatif yang menyarankan langkah perbaikan (periksa ejaan, kurangi kata kunci, atau kosongkan filter OPD/tahun).
- **Pemisahan Kontrol Metode:**
  - Petugas/Arsiparis selalu menggunakan metode pencarian bawaan yang ditetapkan oleh Admin. Sebelum evaluasi akhir selesai, metode bawaan ini bersifat sementara.
  - Dropdown pemilih metode (*Levenshtein, Jaro-Winkler, Token Set, N-Gram, LIKE*) dan halaman perbandingan top-10 antarmetode hanya dapat diakses oleh Admin.
- **Protokol Blind Pooling:** Halaman penilaian relevansi menyajikan kumpulan dokumen secara teracak tanpa menampilkan nama algoritma maupun skor nilai, guna menjamin objektivitas evaluasi.

## 4. Aksesibilitas, Keandalan & Lingkungan Operasional
- **Tanpa Ketergantungan Eksternal Saat Berjalan:** Seluruh file CSS, JavaScript (Bootstrap 5, Chart.js), dan font web disimpan secara lokal di direktori `static/vendor/`. Sistem dapat berfungsi penuh pada jaringan intranet dinas tanpa akses internet.
- **Aksesibilitas Prioritas (WCAG AA):** Difokuskan pada halaman Login, Pencarian, dan Detail Arsip:
  - Kontras warna teks normal dan latar belakang memenuhi rasio minimum 4.5:1, serta rasio minimum 3:1 untuk teks besar dan komponen antarmuka aktif.
  - Navigasi keyboard penuh dengan *focus ring* yang terlihat jelas pada kolom isian dan tombol interaktif.
  - Label form eksplisit pada seluruh kontrol masukan.
- **Keandalan Transaksi Data:** Proses impor SQL dump dijalankan dalam satu transaksi basis data atomik; jika terjadi kegagalan format, sistem membatalkan seluruh perubahan (*rollback*) tanpa merusak data lama.
- **Pencatatan Performa:** Waktu latensi rata-rata komputasi per kueri (dalam milidetik) dicatat pada setiap eksekusi evaluasi temu kembali.
- **Prosedur Pencadangan (Backup):** File database SQLite (`instance/app.sqlite`) dan file set uji dicadangkan secara manual ke folder terpisah di luar Git sebelum pelaksanaan impor ulang maupun evaluasi akhir.
- **Target Kompatibilitas:** Dioptimalkan untuk peramban desktop modern (**Google Chrome** dan **Microsoft Edge** versi terbaru) pada resolusi monitor minimum 1280x720 piksel. Antarmuka ponsel pintar (*mobile smartphone*) dan audit pembaca layar (*screen reader*) formal berada di luar cakupan penelitian.
