"""Uji unit modul murni ringkasan run evaluasi [PM-20]."""

import pytest

from core.evaluation.run_summary import (
    determine_run_status,
    summarize_per_query_rows,
    summarize_tuning_grid,
)


def _row(qid, method, config, split, p5, r10, rr10, hit5, hit10, zero, lat, unj):
    return {
        "query_id": qid,
        "method": method,
        "config": config,
        "split": split,
        "source": "sintetis",
        "query_type": "topik",
        "noise_type": "tanpa_gangguan",
        "n_relevant": 2,
        "p5": str(p5),
        "r10": str(r10),
        "rr10": str(rr10),
        "hit5": str(hit5),
        "hit10": str(hit10),
        "zero_result": str(zero),
        "latency_ms": str(lat),
        "unjudged_in_top10": str(unj),
    }


def test_summarize_per_query_separates_tuning_and_test_hand_calculated():
    rows = [
        _row("Q1", "levenshtein", "tuned", "test", 0.4, 0.5, 1.0, 1, 1, 0, 10.0, 0),
        _row("Q2", "levenshtein", "tuned", "test", 0.2, 0.5, 0.5, 0, 1, 0, 30.0, 2),
        # Baris tuning harus diabaikan saat split='test'
        _row("QT1", "levenshtein", "tuned", "tuning", 0.8, 1.0, 1.0, 1, 1, 0, 5.0, 0),
    ]
    q_map = {"Q1": "B1", "Q2": "B2", "QT1": "B99"}

    test_summary = summarize_per_query_rows(rows, split="test", query_to_base_id=q_map)
    assert test_summary["n_rows"] == 2
    assert test_summary["n_queries"] == 2
    assert test_summary["split_leakage_count"] == 0
    m = test_summary["method_summary"][0]
    assert m["mean_p5"] == pytest.approx(0.3)
    assert m["mean_r10"] == pytest.approx(0.5)
    assert m["mrr_at_10"] == pytest.approx(0.75)
    assert m["hit_at_5_rate"] == pytest.approx(0.5)
    assert m["hit_at_10_rate"] == pytest.approx(1.0)
    assert m["mean_latency_ms"] == pytest.approx(20.0)
    assert m["median_latency_ms"] == pytest.approx(20.0)
    assert m["mean_unjudged_top10"] == pytest.approx(1.0)


def test_detects_base_query_leakage_between_splits():
    rows = [
        _row("Q1", "bm25", "equal", "test", 0.4, 0.5, 1.0, 1, 1, 0, 10.0, 0),
        _row("Q2", "bm25", "equal", "tuning", 0.4, 0.5, 1.0, 1, 1, 0, 10.0, 0),
    ]
    res = summarize_per_query_rows(rows, split="test", query_to_base_id={"Q1": "B001", "Q2": "B001"})
    assert res["split_leakage_count"] == 1
    assert res["leaked_base_ids"] == ["B001"]


def test_summarize_tuning_grid_picks_highest_mrr_then_p5_then_lowest_unjudged():
    grid = [
        {"matcher": "levenshtein", "summary_weight": "0.5", "spm_weight": "0.5", "party_weight": "0.0", "mrr_at_10": "0.6", "precision_at_5": "0.3", "unjudged_top10": "10"},
        {"matcher": "levenshtein", "summary_weight": "0.6", "spm_weight": "0.2", "party_weight": "0.2", "mrr_at_10": "0.6", "precision_at_5": "0.3", "unjudged_top10": "4"},
        {"matcher": "ngram", "summary_weight": "0.4", "spm_weight": "0.3", "party_weight": "0.3", "mrr_at_10": "0.7", "precision_at_5": "0.4", "unjudged_top10": "8"},
    ]
    best = summarize_tuning_grid(grid)
    assert len(best) == 2
    assert best[0]["matcher"] == "levenshtein"
    assert best[0]["summary_weight"] == pytest.approx(0.6)
    assert best[0]["unjudged_top10"] == 4
    assert best[0]["grid_size"] == 2
    assert best[1]["matcher"] == "ngram"


def test_determine_run_status_draft_pending_and_final():
    status, _ = determine_run_status(
        run_meta={"mode": "draft", "tree_clean": False},
        agreement_summary={"status": "complete"},
        manifest_valid=True,
        split_leakage_count=0,
    )
    assert status == "draft"

    status, _ = determine_run_status(
        run_meta={"mode": "final", "tree_clean": True},
        agreement_summary={"status": "pending_second_rater"},
        manifest_valid=True,
        split_leakage_count=0,
    )
    assert status == "pending"

    status, _ = determine_run_status(
        run_meta={"mode": "final", "tree_clean": True},
        agreement_summary={"status": "complete"},
        manifest_valid=True,
        split_leakage_count=1,
    )
    assert status == "draft"

    status, _ = determine_run_status(
        run_meta={"mode": "final", "tree_clean": True},
        agreement_summary={"status": "complete"},
        manifest_valid=True,
        split_leakage_count=0,
    )
    assert status == "final"
