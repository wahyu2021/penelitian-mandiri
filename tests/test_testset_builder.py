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
    base = "pembayaran termin renovasi gedung jalan merdeka"
    noises = [
        "typo", "singkatan", "spasi_tanda_baca",
        "urutan_kata", "kata_hilang", "ejaan_varian",
    ]
    for noise in noises:
        noisy = add_noise(base, noise, seed=42)
        assert isinstance(noisy, str)
        assert len(noisy) > 0


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
