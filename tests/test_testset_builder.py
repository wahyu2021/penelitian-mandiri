"""Uji unit untuk generator kueri sintetis, gangguan, pooling, dan pembagian set uji."""
from pathlib import Path

import pytest

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import create_matcher
from core.testset.noise import add_noise
from core.testset.pooling import build_query_pool
from core.testset.splitting import split_queries_stratified_anti_leak
from core.testset.synthetic_generator import generate_synthetic_query
from scripts.build_testset import build_testset_from_pool
from tests.conftest import make_record


def test_noise_functions():
    from rapidfuzz.distance import Levenshtein

    base = "pembayaran termin renovasi gedung jalan merdeka"
    noises = [
        "typo", "singkatan", "spasi_tanda_baca",
        "urutan_kata", "kata_hilang", "ejaan_varian",
    ]
    for noise in noises:
        noisy = add_noise(base, noise, seed=42)
        assert isinstance(noisy, str)
        assert len(noisy) > 0
        # Jarak edit wajib > 0 untuk semua jenis gangguan
        assert Levenshtein.distance(base, noisy) > 0

    # tanpa_gangguan wajib berjarak 0
    clean = add_noise(base, "tanpa_gangguan", seed=42)
    assert clean == base
    assert Levenshtein.distance(base, clean) == 0


def test_spm_noise_realistic_and_distance_greater_than_zero():
    """Uji gangguan nomor SPM realistis: jarak > 0 kecuali tanpa_gangguan, deterministik."""
    from rapidfuzz.distance import Levenshtein

    spm_samples = [
        "290/LS/Dinas/2000",
        "414/LS/Dinas/2002",
        "924/BT/Dinas/2002",
        "332/BT/Dinas/2006",
        "728/BT/Dinas/2004",
        "534/LS/Dinas/2002",
        "773/LS/Dinas/2009",
        "515/BT/Dinas/2005",
        "689/LS/Dinas/2007",
        "503/LS/SPM/SETWAN/2011",
        "133/PERTA/2008",
        "121/2/P",
    ]
    noises = [
        "typo", "singkatan", "spasi_tanda_baca",
        "urutan_kata", "kata_hilang", "ejaan_varian",
    ]

    for spm in spm_samples:
        # tanpa_gangguan wajib jarak 0
        assert add_noise(spm, "tanpa_gangguan", seed=42) == spm
        assert Levenshtein.distance(spm, add_noise(spm, "tanpa_gangguan", seed=42)) == 0

        for noise in noises:
            noisy = add_noise(spm, noise, seed=42)
            dist = Levenshtein.distance(spm, noisy)
            assert dist > 0, f"SPM '{spm}' dengan noise '{noise}' menghasilkan dist == 0!"
            # Deterministik: seed yang sama menghasilkan teks yang identik
            noisy2 = add_noise(spm, noise, seed=42)
            assert noisy == noisy2


def test_synthetic_query_generation():
    rec = make_record(
        archive_id=10,
        summary="Pembayaran termin I pembangunan jembatan sungai musi",
        spm_number="123/LS/DISKOMINFO/2021",
        party_name="CV Contoh Mandiri",
        year=2021,
    )
    q_topic = generate_synthetic_query(rec, "topik", seed=42)
    assert q_topic is not None
    assert q_topic["query_type"] == "topik"
    assert q_topic["origin_archive_id"] == 10

    q_spm = generate_synthetic_query(rec, "nomor_spm", seed=42)
    assert q_spm is not None
    assert "123" in q_spm["query_text"]

    q_party = generate_synthetic_query(rec, "pihak", seed=42)
    assert q_party is not None
    assert "Contoh" in q_party["query_text"]


def test_build_query_pool_includes_origin_doc():
    records = [
        make_record(1, "Renovasi pasar baru"),
        make_record(2, "Pembangunan jembatan sungai"),
        make_record(3, "Pengadaan komputer kantor"),
    ]
    index = SearchIndex.from_records(records)
    like_search = LikeBaselineSearch(index)
    matchers = {"levenshtein": create_matcher("levenshtein")}

    # Kueri mencari "pasar", origin doc ID = 3 (yang tidak cocok dengan "pasar")
    pool = build_query_pool(
        query_text="pasar",
        index=index,
        matchers=matchers,
        like_search=like_search,
        origin_archive_id=3,
        pool_depth=2,
        seed=42,
    )

    assert 3 in pool  # origin doc wajib masuk pool!
    assert len(pool) == len(set(pool))  # tidak ada duplikat


def test_anti_leak_splitting_keeps_same_spm_in_same_split():
    queries = [
        {
            "query_id": "Q1", "spm_number": "123/LS/2021", "origin_archive_id": 1,
            "source": "sintetis", "query_type": "topik",
        },
        {
            "query_id": "Q2", "spm_number": "123/LS/2021", "origin_archive_id": 2,
            "source": "sintetis", "query_type": "nomor_spm",
        },
        {
            "query_id": "Q3", "spm_number": "456/GU/2021", "origin_archive_id": 3,
            "source": "sintetis", "query_type": "topik",
        },
        {
            "query_id": "Q4", "spm_number": "789/TU/2021", "origin_archive_id": 4,
            "source": "sintetis", "query_type": "pihak",
        },
        {
            "query_id": "Q5", "spm_number": "999/UP/2021", "origin_archive_id": 5,
            "source": "sintetis", "query_type": "campuran",
        },
    ]

    tuning_q, test_q = split_queries_stratified_anti_leak(queries, tuning_ratio=0.4, seed=42)

    tuning_ids = {q["query_id"] for q in tuning_q}
    test_ids = {q["query_id"] for q in test_q}

    # Q1 dan Q2 berbagi SPM yang sama, wajib berada di split yang sama!
    assert ("Q1" in tuning_ids and "Q2" in tuning_ids) or ("Q1" in test_ids and "Q2" in test_ids)
    assert len(tuning_q) + len(test_q) == 5


def test_build_testset_from_pool(tmp_path: Path):
    csv_file = tmp_path / "pool.csv"
    json_file = tmp_path / "testset.json"

    header = (
        "query_id,query_text,query_type,source,noise_type,pool_order,"
        "archive_id,summary_raw,spm_number,party_name,is_relevant,auditor_notes\n"
    )
    row1 = "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,Renovasi gedung,123/LS,CV Contoh,1,\n"
    row2 = "Q001,gedung,topik,sintetis,tanpa_gangguan,2,11,Pengecatan kantor,456/GU,CV Maju,0,\n"
    row3 = "Q002,laptop,topik,sintetis,typo,1,12,Pengadaan laptop,789/UP,PT Jaya,1,\n"
    csv_content = header + row1 + row2 + row3
    csv_file.write_text(csv_content, encoding="utf-8-sig")

    res = build_testset_from_pool(csv_file, json_file, tuning_ratio=0.5, seed=42)
    assert res["n_queries"] == 2
    assert json_file.is_file()
    assert len(res["content_sha256"]) == 64
    import json
    saved = json.loads(json_file.read_text(encoding="utf-8"))
    assert set(q["split"] for q in saved["queries"]) == {"tuning", "test"}


def test_build_testset_pilot_consistency_and_ragu(tmp_path: Path):
    from scripts.evaluate_relevance_agreement import evaluate_relevance_agreement

    main_csv = tmp_path / "pool.csv"
    pilot_csv = tmp_path / "pilot.csv"
    json_file = tmp_path / "testset.json"

    header = (
        "query_id,query_text,query_type,source,noise_type,pool_order,"
        "archive_id,summary_raw,spm_number,party_name,is_relevant,ragu,auditor_notes\n"
    )
    row1_main = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,"
        "Renovasi gedung,123/LS,CV Contoh,1,0,\n"
    )
    row2_main = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,2,11,"
        "Pengecatan kantor,456/GU,CV Maju,0,1,\n"
    )
    main_csv.write_text(header + row1_main + row2_main, encoding="utf-8-sig")

    # 1. Pilot konsisten
    row1_pilot = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,"
        "Renovasi gedung,123/LS,CV Contoh,1,0,\n"
    )
    pilot_csv.write_text(header + row1_pilot, encoding="utf-8-sig")

    res = build_testset_from_pool(
        main_csv, json_file, pilot_csv_path=pilot_csv, tuning_ratio=0.5
    )
    assert res["total_ragu"] == 1

    # 2. Pilot tidak konsisten (Q001, archive 10 diubah jadi 0 di pilot)
    bad_pilot = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,"
        "Renovasi gedung,123/LS,CV Contoh,0,0,\n"
    )
    pilot_csv.write_text(header + bad_pilot, encoding="utf-8-sig")

    with pytest.raises(ValueError, match="Ketidakkonsistenan penilaian terdeteksi"):
        build_testset_from_pool(main_csv, json_file, pilot_csv_path=pilot_csv)

    # 3. Uji evaluasi kesepakatan arsiparis
    verif_csv = tmp_path / "verif.csv"
    verif_header = (
        "sample_id,query_id,query_text,query_type,source,noise_type,"
        "archive_id,summary_raw,spm_number,party_name,is_relevant,ragu,archivist_notes\n"
    )
    verif_row = (
        "1,Q001,gedung,topik,sintetis,tanpa_gangguan,10,"
        "Renovasi gedung,123/LS,CV Contoh,1,0,\n"
    )
    verif_csv.write_text(verif_header + verif_row, encoding="utf-8-sig")

    rep = evaluate_relevance_agreement(main_csv, verif_csv)
    assert rep["overall_percentage_agreement"] == 1.0


def test_sync_pilot_and_additional_pool_integration(tmp_path: Path):
    """Uji sinkronisasi otomatis dari pilot jika belum terisi dan integrasi additional pool."""
    import json

    main_csv = tmp_path / "pool_main.csv"
    pilot_csv = tmp_path / "pool_pilot.csv"
    add_csv = tmp_path / "pool_add.csv"
    json_file = tmp_path / "testset_synced.json"

    header = (
        "query_id,query_text,query_type,source,noise_type,pool_order,"
        "archive_id,summary_raw,spm_number,party_name,is_relevant,ragu,auditor_notes\n"
    )
    # Di berkas utama, is_relevant sengaja kosong (belum sempat dinilai)
    row_main = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,"
        "Renovasi gedung,123/LS,CV Contoh,,,catatan\n"
    )
    main_csv.write_text(header + row_main, encoding="utf-8-sig")

    # Di berkas pilot, sudah dinilai relevan (1)
    row_pilot = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,10,"
        "Renovasi gedung,123/LS,CV Contoh,1,0,pilot_note\n"
    )
    pilot_csv.write_text(header + row_pilot, encoding="utf-8-sig")

    # Di berkas additional pool, arsip baru (99) dinilai
    row_add = (
        "Q001,gedung,topik,sintetis,tanpa_gangguan,1,99,"
        "Pembangunan aula,789/LS,CV Berkah,1,1,additional_doc\n"
    )
    add_csv.write_text(header + row_add, encoding="utf-8-sig")

    res = build_testset_from_pool(
        pool_csv_path=main_csv,
        output_json_path=json_file,
        pilot_csv_path=pilot_csv,
        additional_pool_csv_path=add_csv,
    )

    assert res["synced_from_pilot"] == 1
    assert res["additional_judged_count"] == 1

    saved = json.loads(json_file.read_text(encoding="utf-8"))
    q1 = saved["queries"][0]
    aid_map = {j["archive_id"]: j["is_relevant"] for j in q1["judgments"]}
    assert aid_map[10] == 1  # Tersinkron dari pilot
    assert aid_map[99] == 1  # Terintegrasi dari additional pool

