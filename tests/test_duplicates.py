"""Uji unit deteksi kandidat duplikat murni [PM-24]."""

from core.duplicates import find_duplicate_candidates


def test_find_duplicate_candidates_empty_and_different():
    assert find_duplicate_candidates([]) == []
    assert (
        find_duplicate_candidates(
            [
                {"id": 1, "spm_number": "001/UP", "summary_normalized": "pengadaan alat kantor", "opd_id": 1, "year": 2024, "amount_rp": 1000},
                {"id": 2, "spm_number": "002/LS", "summary_normalized": "perbaikan jalan desa", "opd_id": 1, "year": 2024, "amount_rp": 2000},
            ]
        )
        == []
    )


def test_find_duplicate_candidates_by_spm_summary_and_amount():
    records = [
        {"id": 5, "spm_number": "001/UP/2024", "summary_normalized": "belanja alat tulis kantor dinas", "opd_id": 1, "year": 2024, "amount_rp": 500000},
        {"id": 2, "spm_number": "001/UP/2024", "summary_normalized": "belanja alat tulis", "opd_id": 1, "year": 2024, "amount_rp": 500000},
        {"id": 8, "spm_number": None, "summary_normalized": "pembayaran honorarium narasumber kegiatan", "opd_id": 2, "year": 2024, "amount_rp": 700000},
        {"id": 9, "spm_number": None, "summary_normalized": "pembayaran honorarium narasumber kegiatan", "opd_id": 2, "year": 2024, "amount_rp": 800000},
        {"id": 12, "spm_number": None, "summary_normalized": "pengadaan komputer dinas pendidikan kota", "opd_id": 3, "year": 2024, "amount_rp": 9000000},
        {"id": 15, "spm_number": None, "summary_normalized": "pengadaan komputer dinas pendidikan kabupaten", "opd_id": 3, "year": 2024, "amount_rp": 9000000},
    ]

    results = find_duplicate_candidates(records)
    pairs = {(item["archive_a_id"], item["archive_b_id"]): item for item in results}

    # Urutan kanonik (2, 5) dari SPM sama
    assert pairs[(2, 5)]["reason"] == "same_spm"
    assert pairs[(2, 5)]["similarity"] == 1.0
    # Ringkasan sama
    assert pairs[(8, 9)]["reason"] == "same_summary"
    # OPD, tahun, nominal sama dan Jaccard >= 0.70 (4/6 kata sama -> 0.6667? cek: 4 shared, 6 union!)
    # Periksa: {pengadaan, komputer, dinas, pendidikan, kota} vs {..., kabupaten} -> 4/6 = 0.667 < 0.70
    # Tambahkan 1 kata sama agar > 0.70 pada uji kedua di bawah.


def test_find_duplicate_candidates_amount_opd_year_threshold():
    records = [
        {"id": 10, "spm_number": None, "summary_normalized": "belanja pemeliharaan rutin kendaraan dinas operasional roda empat", "opd_id": 3, "year": 2024, "amount_rp": 9000000},
        {"id": 20, "spm_number": None, "summary_normalized": "belanja pemeliharaan rutin kendaraan dinas operasional roda dua", "opd_id": 3, "year": 2024, "amount_rp": 9000000},
    ]
    res = find_duplicate_candidates(records)
    assert len(res) == 1
    assert res[0]["archive_a_id"] == 10
    assert res[0]["archive_b_id"] == 20
    assert res[0]["reason"] == "same_amount_opd_year"
    assert res[0]["similarity"] >= 0.70
