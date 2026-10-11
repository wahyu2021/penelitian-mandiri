# Ringkasan Track: core-domain-and-search

Dokumen ini tidak memuat angka hasil pengukuran. Angka apa pun untuk laporan harus
berasal dari ekspor skrip (lihat `conductor/workflow.md`).

## Modul

| Modul | Fungsi |
|---|---|
| `core/sql_dump_parser.py` | Membaca dump MySQL. Hanya `apptb_arsip`, `apptb_opd`, `apptb_klasifikasi` yang diizinkan; tabel lain (termasuk `apptb_user`, `apptb_log`, `apptb_arsip1`) dilewati tanpa di-parse. Mencatat SHA-256 berkas. |
| `core/cleaning.py` | Membersihkan baris arsip. Nilai tak valid menjadi `None` dan dicatat sebagai masalah data, tidak diganti nilai bawaan. |
| `core/normalization.py` | Normalisasi dan tokenisasi yang sama untuk dokumen dan kueri. Kode bergaris miring dijaga utuh. |
| `core/extraction.py` | Ekstraksi SPM, SP2D, tanggal, nominal, pihak. Nilai yang gagal terbaca bernilai `None`. |
| `core/spm_types.py` | Kamus jenis SPM, seluruhnya berstatus `dugaan`. |
| `core/search/` | Baseline LIKE, empat pencocok fuzzy, indeks memori, perangking field berbobot. |
| `core/evaluation/` | Metrik per kueri, agregasi makro, persentase kesepakatan penilai. |

## Keputusan desain yang perlu masuk laporan
- **Kolom `jumlah` sumber** berisi banyak berkas (mis. "1 Berkas"), bukan uang. Nominal rupiah berasal dari ekstraksi ringkasan dan disimpan terpisah (`quantity_label` vs `amount_rp`).
- **Kamus SPM:** arti LS/UP/GU/TU memakai istilah umum keuangan daerah; arti BT/BS/PK belum diketahui dan sengaja tidak ditebak. Semua berstatus `dugaan`.
- **Pembanding LIKE** meniru pencarian DataTables e-Arsip: kueri dipecah per spasi, semua kata harus cocok sebagai potongan teks pada gabungan kolom tampil, urutan `id_arsip` naik. Penyederhanaan: frasa berkutip tidak ditiru; kueri kosong tidak mengembalikan hasil; nomor urut baris tabel tidak ikut dicari.
- **Skor field fuzzy:** rata-rata, atas token kueri, dari kemiripan terbaik token tersebut terhadap token field. Token set memakai seluruh string field sekaligus dan bernilai 1,0 bila token kueri adalah himpunan bagian token field (perilaku bawaan RapidFuzz).
- **Field SPM** diindeks sebagai kode utuh ditambah tiap bagiannya agar kueri sebagian tetap bisa cocok.
- **N-gram Dice** ditulis sendiri karena RapidFuzz tidak menyediakannya; padding spasi `n-1` di kedua sisi.
- **Tanpa ambang skor** pada pencarian fuzzy secara bawaan (`min_score=0`); kueri nol hasil hanya terjadi bila seluruh skor nol.
- **Urutan deterministik:** skor turun, seri diurutkan `id` naik.
- **Metrik:** penyebut Precision@k tetap k walau hasil kurang dari k; kueri tanpa dokumen relevan ditolak (`ValueError`) karena Recall tidak terdefinisi.

## Cara memverifikasi
```
.venv\Scripts\python.exe -m pytest tests -q
```
Uji angka acuan (`tests/test_reference_counts.py`) memerlukan dump SQL. Tentukan lokasinya lewat
variabel lingkungan `SIMANIS_DUMP_PATH` atau letakkan di `data/raw/`. Tanpa dump, uji tersebut dilewati
(dilaporkan sebagai *skipped*, bukan lulus).

## Belum dikerjakan (di luar track ini)
- Aturan kesetaraan relevansi (arsip dengan SPM atau isi sama dianggap sama-sama relevan) saat penilaian.
- Penyetelan bobot, set uji, pooling, split, dan penguncian versi.
- Audit ekstraksi manual; sebelum itu hanya cakupan ekstraksi yang boleh dilaporkan, bukan akurasi.
- Lapisan basis data, antarmuka web, login, dan CLI evaluasi.
