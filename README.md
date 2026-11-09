# Panduan Singkat Folder PM

## File yang digunakan

- `notebooks/paket_pipeline_analisis_sampai_presentasi.zip`: paket untuk menjalankan analisis secara mandiri. Ekstrak ZIP, lalu buka notebook di dalamnya.
- `notebooks/pipeline_analisis_sampai_presentasi.ipynb`: notebook kerja dengan hasil eksekusi terakhir.
- `scripts/build_colab_bundle_notebook.py`: pembangkit sumber notebook aktif.
- `data/testset/`: set uji dan bobot hasil tuning yang digunakan evaluasi.
- `output/colab_bundle/`: enam berkas agregat yang dibaca notebook.
- `output/relevance_pool.csv` dan `output/audit_extraction_sample.csv`: penilaian sumber. Simpan beserta cadangan di `output/.real_data_backup/` dan `output/.labeler_backups/`.

## Berkas lama

- `legacy/`: notebook dan pembangkit notebook generasi lama, disimpan sebagai riwayat.
- `output/legacy_2026-11-09/`: hasil evaluasi lama, salinan paket yang pernah diekstrak, dan grafik lama. Hasil di sini tidak dipakai pipeline aktif.

Jika ZIP diekstrak di `notebooks/`, folder `notebooks/paket_pipeline_analisis_sampai_presentasi/` akan muncul sebagai salinan kerja lokal yang diabaikan Git. ZIP tetap menjadi berkas distribusi utama.
