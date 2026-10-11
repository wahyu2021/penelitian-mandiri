# HTML, CSS & Client Script Style Guide: Sistem Pencarian Arsip SIMANIS

Panduan standar untuk template Jinja2, Bootstrap 5 kustom, dan skrip JavaScript sisi klien.

## 1. Keamanan & Sanitasi Template Jinja2
- **Autoescape Wajib Aktif:** Mesin render Jinja2 wajib menjalankan *autoescape* secara default pada seluruh file `.html`.
- **Restriksi Filter `|safe`:**
  - Penggunaan filter `|safe` dilarang keras, kecuali untuk satu pengecualian tertulis: perenderan tag `<mark>` pada penyorotan teks hasil pencarian.
- **Protokol Penyorotan Teks (Text Highlight Sanitization):**
  - Data teks ringkasan dari database dinas pernah memuat karakter khusus atau sisa fragmen HTML.
  - Sebelum menyisipkan penanda `<mark>`, teks ringkasan wajib di-*escape* terlebih dahulu menggunakan `html.escape()` atau fungsi utilitas sanitasi, baru kemudian token kueri yang cocok dibungkus oleh `<mark class="search-highlight">...</mark>`.
- **Tanpa Inline Style:** Dilarang menggunakan atribut `style="..."` pada elemen HTML. Semua styling wajib menggunakan kelas utilitas Bootstrap 5 atau kelas kustom di `static/css/app.css`.

## 2. Struktur CSS & Variabel Desain Token
- **Design Tokens via CSS Variables:**
  - Seluruh palet warna primer (*navy/slate*), warna semantik (*success, warning, danger, info*), spasi (kelipatan 4px/8px), dan *border-radius* didefinisikan dalam `:root` di `static/css/app.css`.
  - Gunakan variabel CSS untuk mempermudah konsistensi tema (misalnya `var(--color-primary)`, `var(--border-radius-base)`).
- **Struktur Template:**
  - Terapkan hierarki template inheritance: `base.html` sebagai layout utama, disusul blok spesifik (`content`, `scripts`, `styles`).
  - Elemen berulang (seperti kartu arsip, badge status, pagination) diekstrak menjadi komponen Jinja2 (*macros* atau *partials*).

## 3. Aksesibilitas (WCAG AA) & Form Standards
- **Label Form Eksplisit:** Setiap kontrol input, select, dan textarea wajib memiliki pasangan `<label for="id_elemen">` yang jelas.
- **Focus Ring Keyboard:** Jangan pernah menghapus `outline: none` tanpa menyediakan pengganti focus ring yang kontras (fokus visual yang jelas pada tombol dan kolom teks saat tombol `Tab` ditekan).
- **Prinsip Non-Color Dependency:**
  - Status dokumen (*In Aktif, Statis, Musnah*) dan badge *"Dugaan"* tidak boleh hanya dibedakan berdasarkan warna latar badge.
  - Wajib menyertakan teks keterangan yang jelas atau ikon pendukung bersama warna semantik.
- **Kontras Minimum:** Memenuhi rasio kontras 4.5:1 untuk teks normal dan 3:1 untuk teks besar serta komponen antarmuka.

## 4. Aturan JavaScript Sisi Klien (Client Scripts)
- **Skrip Minimalis & Terisolasi:**
  - JavaScript hanya digunakan untuk peningkatan progresif (*progressive enhancement*): inisialisasi grafik Chart.js, aktivasi tooltip Bootstrap, pengosongan filter form, dan penyalinan teks.
  - Dilarang menambahkan framework frontend berat (React, Vue, dsb.).
- **Tanpa Ketergantungan Eksternal:** Seluruh skrip pustaka (Bootstrap JS, Chart.js) wajib dimuat dari path lokal `static/vendor/` tanpa memanggil URL CDN luar.
- **Kode Bersih:** Hindari variabel global; bungkus logika dalam event listener `DOMContentLoaded` dan gunakan sintaks JavaScript modern (ES6+).
