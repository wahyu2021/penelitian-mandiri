"""Uji unit untuk skrip create_additional_judgment_pool (deteksi dokumen unjudged top-k)."""
from pathlib import Path

from core.search.index import SearchIndex
from scripts.create_additional_judgment_pool import find_unjudged_top_k
from tests.conftest import make_record


def test_find_unjudged_top_k_cases():
    records = [
        make_record(1, summary="Renovasi gedung dinas pendidikan"),
        make_record(2, summary="Pembangunan gedung dinas kesehatan"),
        make_record(3, summary="Pengadaan mebel kantor bappeda"),
        make_record(4, summary="Pemeliharaan gedung arsip"),
    ]
    index = SearchIndex.from_records(records)
    corpus_by_id = {int(r["id"]): r for r in records}

    # Kueri mencari "gedung"
    # Pada pool awal, hanya arsip 1 dan 2 yang dinilai.
    # Arsip 4 ("Pemeliharaan gedung arsip") belum pernah dinilai dan masuk top-k!
    queries = [
        {
            "query_id": "Q_GEDUNG",
            "query_text": "gedung",
            "query_type": "topik",
            "source": "sintetis",
            "noise_type": "tanpa_gangguan",
            "judgments": [
                {"archive_id": 1, "is_relevant": 1},
                {"archive_id": 2, "is_relevant": 1},
            ],
        }
    ]

    weights_by_matcher = {
        "levenshtein": {"summary": 1.0, "spm": 0.0, "party": 0.0},
        "token_set": {"summary": 1.0, "spm": 0.0, "party": 0.0},
    }

    unjudged_rows, manifest = find_unjudged_top_k(
        queries=queries,
        index=index,
        corpus_by_id=corpus_by_id,
        weights_by_matcher=weights_by_matcher,
        top_k=10,
    )

    # Arsip 4 harus terdeteksi sebagai unjudged
    unjudged_aids = {r["archive_id"] for r in unjudged_rows}
    assert 4 in unjudged_aids
    assert 1 not in unjudged_aids  # Sudah dinilai
    assert 2 not in unjudged_aids  # Sudah dinilai
    assert manifest["n_unjudged"] == len(unjudged_rows)

    # Pastikan format baris blind murni (tanpa metode, skor, rank)
    first_row = unjudged_rows[0]
    assert "score" not in first_row
    assert "method" not in first_row
    assert "rank" not in first_row
    assert first_row["is_relevant"] == ""  # Wajib kosong
