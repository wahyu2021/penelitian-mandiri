# Initial Concept

Sistem Pencarian Arsip Menggunakan Fuzzy Matching dan Normalisasi Metadata Berbasis Website pada Dinas Perpustakaan dan Kearsipan Kota Palembang.

# Product Guide: Sistem Pencarian Arsip pada e-Arsip (SIMANIS)

## 1. Visi dan Gambaran Umum
Sistem Pencarian Arsip Berbasis Website yang dirancang untuk meneliti dan mengatasi permasalahan temu kembali informasi pada data e-Arsip (SIMANIS) Dinas Perpustakaan dan Kearsipan Kota Palembang. Sistem ini mengintegrasikan **ekstraksi & normalisasi metadata** dari teks ringkasan bebas serta **pencarian fuzzy matching multi-metode** (Levenshtein, Jaro-Winkler, Token Set, dan N-Gram) yang toleran terhadap salah ketik (typo), variasi ejaan, dan singkatan, dibandingkan terhadap metode pencarian eksak/LIKE bawaan sistem yang berjalan.

## 2. Pengguna Sasaran dan Peran (Role)
1. **Admin (Pengelola Sistem / Peneliti):**
   - Mengelola impor salinan data SQL dump.
   - Mengelola set uji kueri dan melakukan penyetelan bobot field.
   - Melakukan penilaian relevansi kueri dengan panduan aturan tertulis (arsip dengan nomor SPM atau substansi isi yang sama dianggap sama-sama relevan).
   - Menjalankan evaluasi komputasi temu kembali dan ekspor laporan.
   - Mengelola akun pengguna dan kamus referensi jenis SPM.
2. **Petugas / Arsiparis:**
   - Memberikan target kasus nyata dari pengalaman temu kembali arsip di lapangan.
   - Memverifikasi sampel penilaian relevansi (20-30% sampel) untuk menghitung persentase kesepakatan (*percentage agreement*).
   - Melakukan pencarian arsip multi-metode dengan filter OPD dan Tahun.
   - Melihat detail arsip dan hasil ekstraksi metadata terstruktur.
   - Melakukan audit akurasi ekstraksi metadata pada sampel yang ditentukan.
   - Berpartisipasi dalam pengujian kegunaan sistem (UAT dan kuesioner SUS).

## 3. Fitur Utama
### Fase 1 (Fokus Utama Penelitian):
- **Impor & Normalisasi Data:** Parser SQL dump aman (tanpa membaca tabel `apptb_user` dan `apptb_log`), pembersihan format data, penanganan tanggal/tahun tidak valid, dan pemisahan kuantitas berkas fisik vs nominal rupiah.
- **Ekstraksi Metadata Terstruktur:** Ekstraksi otomatis No. SPM, No. SP2D, Tanggal Dokumen, Nominal Rupiah, dan Pihak (CV/PT) dari teks ringkasan, dilengkapi modul audit manual berpenghitungan akurasi otomatis oleh skrip.
- **Pencarian Multi-Metode:** Dukungan 4 algoritma fuzzy (Levenshtein, Jaro-Winkler, Token Set, Character N-Gram Dice) berbobot field dinamis serta pembanding LIKE (meniru DataTables SIMANIS).
- **Modul Evaluasi Ilmiah:** Penyetelan bobot (rencana 15 kueri tuning) dan pengujian akhir (rencana 35 kueri test, total target 30–50 kueri) dengan metrik P@5, R@10, MRR@10, Hit Rate@5/10, dan jumlah kueri nol hasil, dilaporkan per jenis kueri dan per jenis gangguan. Uji signifikansi statistik (Wilcoxon) bersifat opsional setelah metrik utama selesai.
- **Otentikasi & Keamanan:** Login dengan kata sandi ter-hash (scrypt/werkzeug), proteksi CSRF, dan kontrol akses berbasis peran.

### Fase 2 (Pengembangan Lanjutan):
- **Deteksi Duplikasi Arsip:** Penandaan pasangan arsip kandidat duplikat (belum dicek, duplikat, bukan duplikat) tanpa operasi hapus.
- **Dashboard Kualitas Data:** Visualisasi Chart.js untuk anomali data (orphan OPD, tanggal 0000-00-00, kelengkapan berkas fisik).

## 4. Tolok Ukur Keberhasilan & Evaluasi
1. **Terukurnya Efektivitas Temu Kembali:** Terukurnya perbedaan efektivitas pencarian fuzzy dibanding baseline LIKE pada kueri realistis dan kueri bergangguan, dilaporkan apa adanya (termasuk kasus di mana metode tidak lebih unggul).
2. **Transparansi Hasil:** Seluruh metrik dilaporkan tanpa manipulasi dan dihitung murni secara komputasi oleh skrip.
3. **Validasi Ekstraksi:** Akurasi ekstraksi tervalidasi melalui sampel audit teracak dengan pencatatan seed untuk replikasi.
4. **Evaluasi Pengguna Deskriptif:** Evaluasi kegunaan sistem melibatkan seluruh petugas pengguna (kurang dari 5 orang) melalui UAT dan SUS, dilaporkan secara deskriptif tanpa generalisasi statistik luas.

## 5. Batasan Operasional & Keamanan
- **Arsitektur Mandiri (Standalone):** Menggunakan basis data SQLite lokal dari salinan dump, dan tidak melakukan koneksi atau penulisan ke MySQL produksi dinas.
- **Ruang Lingkup Uji Coba:** Aplikasi tidak diklaim siap operasional penuh dinas, karena penelitian dibatasi pada pengujian dengan salinan data.
- **Anti-Hardcode:** Semua angka metrik dan laporan dihasilkan langsung oleh eksekusi skrip.
- **Integritas Data:** Tidak ada operasi hapus arsip fisik atau baris data di seluruh sistem.
- **Kerahasiaan Data Dinas:** Dump SQL, basis data SQLite, dan file CSV hasil olahan diabaikan oleh Git (.gitignore). Repositori disimpan secara lokal atau privat.
- **Kamus SPM Objektif:** Seluruh jenis SPM ditandai berstatus "dugaan" sampai dikonfirmasi dinas.
- **Replikabilitas Penelitian:** Nilai seed acak, hash SHA-256 data sumber, dan commit kode dicatat pada setiap batch impor dan pengujian.
- **Lingkungan Eksekusi:** Selama penelitian aplikasi berjalan di laptop lokal. Kesiapan dijalankan via server WSGI Waitress di jaringan lokal dinas hanya diterapkan setelah persetujuan pengelola.
