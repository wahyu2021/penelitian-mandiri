"""Uji unit untuk modul penyetelan bobot field (core.evaluation.tuning)."""
import pytest

from core.evaluation.tuning import (
    evaluate_weights_on_queries,
    generate_weight_grid,
    tune_weights_grid_search,
)
from core.search.index import SearchIndex
from core.search.matchers import create_matcher
from tests.conftest import make_record


def test_generate_weight_grid():
    grid = generate_weight_grid(step=0.1)
    # Kombinasi (10 + 2 choose 2) = 66
    assert len(grid) == 66
    for w in grid:
        assert set(w.keys()) == {"summary", "spm", "party"}
        assert round(w["summary"] + w["spm"] + w["party"], 4) == 1.0
        assert all(0.0 <= val <= 1.0 for val in w.values())

    with pytest.raises(ValueError):
        generate_weight_grid(step=0.0)
    with pytest.raises(ValueError):
        generate_weight_grid(step=1.5)


def test_evaluate_weights_and_tuning():
    records = [
        make_record(
            1, summary="Renovasi kantor bappeda", spm_number="100/LS/2021", party_name="PT A"
        ),
        make_record(
            2, summary="Pembangunan jembatan", spm_number="200/GU/2021", party_name="PT B"
        ),
        make_record(
            3, summary="Pengadaan mobil dinas", spm_number="300/TU/2021", party_name="PT C"
        ),
    ]
    index = SearchIndex.from_records(records)
    matcher = create_matcher("token_set")

    # Kueri tuning: mencari "renovasi"
    # Dokumen 1 relevan
    queries = [
        {
            "query_id": "Q1",
            "query_text": "renovasi",
            "split": "tuning",
            "judgments": [
                {"archive_id": 1, "is_relevant": 1},
                {"archive_id": 2, "is_relevant": 0},
            ],
        }
    ]

    # Evaluasi dengan bobot summary tinggi vs 0
    weights_good = {"summary": 1.0, "spm": 0.0, "party": 0.0}
    mrr_good, p5_good, unjudged_good = evaluate_weights_on_queries(
        index, matcher, weights_good, queries
    )
    assert mrr_good > 0.0
    assert p5_good > 0.0

    # Grid search tuning
    res = tune_weights_grid_search(index, matcher, queries, step=0.2)
    assert res["matcher_name"] == "token_set"
    assert res["n_tuning_queries"] == 1
    assert "best_weights" in res
    assert res["best_mrr_at_10"] >= res["equal_weights_mrr_at_10"]


def test_tuning_rejects_non_tuning_split():
    records = [make_record(1, "Dokumen arsip uji")]
    index = SearchIndex.from_records(records)
    matcher = create_matcher("levenshtein")

    queries = [
        {
            "query_id": "Q_LEAK",
            "query_text": "arsip",
            "split": "test",  # Dilarang!
            "judgments": [{"archive_id": 1, "is_relevant": 1}],
        }
    ]

    with pytest.raises(ValueError, match="Terdapat kueri bukan kelompok tuning"):
        tune_weights_grid_search(index, matcher, queries)


def test_additional_judgments_integration():
    records = [
        make_record(1, summary="Pengadaan komputer"),
        make_record(2, summary="Pengadaan laptop"),
    ]
    index = SearchIndex.from_records(records)
    matcher = create_matcher("token_set")

    queries = [
        {
            "query_id": "Q1",
            "query_text": "komputer",
            "split": "tuning",
            "judgments": [{"archive_id": 1, "is_relevant": 1}],
        }
    ]

    # Sebelum additional judgments, doc 2 unjudged
    weights = {"summary": 0.5, "spm": 0.3, "party": 0.2}
    _, _, unjudged_before = evaluate_weights_on_queries(index, matcher, weights, queries)

    # Tambahkan penilaian doc 2 sebagai tidak relevan
    add_j = {"Q1": {2: 0}}
    _, _, unjudged_after = evaluate_weights_on_queries(
        index, matcher, weights, queries, additional_judgments=add_j
    )

    assert unjudged_after <= unjudged_before
