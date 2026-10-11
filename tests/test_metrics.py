import pytest

from core.evaluation.metrics import (
    aggregate_macro, count_unjudged, evaluate_query, first_relevant_rank,
    hit_rate_at_k, is_zero_result, precision_at_k, recall_at_k, reciprocal_rank,
)

# Kueri A: relevan {12, 15, 99}; 12 di peringkat 3, 15 di peringkat 6, 99 tidak terambil.
A_RETRIEVED = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
A_RELEVANT = {12, 15, 99}


def test_precision_hand_calculated():
    # top-5 = 10..14 -> satu relevan (12) -> 1/5
    assert precision_at_k(A_RETRIEVED, A_RELEVANT, 5) == pytest.approx(0.2)


def test_precision_denominator_stays_k_when_fewer_results():
    # dua hasil, keduanya relevan -> 2/5, bukan 2/2
    assert precision_at_k([4, 5], {4, 5}, 5) == pytest.approx(0.4)


def test_recall_hand_calculated():
    # 12 dan 15 ada di top-10, dari tiga relevan -> 2/3
    assert recall_at_k(A_RETRIEVED, A_RELEVANT, 10) == pytest.approx(2 / 3)
    assert recall_at_k([4, 5], {4, 5}, 10) == 1.0


def test_reciprocal_rank_hand_calculated():
    assert reciprocal_rank(A_RETRIEVED, A_RELEVANT) == pytest.approx(1 / 3)
    assert first_relevant_rank(A_RETRIEVED, A_RELEVANT) == 3
    assert reciprocal_rank([1, 2, 3], {7}) == 0.0
    assert first_relevant_rank([1, 2, 3], {7}) is None


def test_reciprocal_rank_respects_cutoff():
    retrieved = list(range(1, 12))  # relevan di peringkat 11
    assert reciprocal_rank(retrieved, {11}, k=10) == 0.0
    assert reciprocal_rank(retrieved, {11}, k=11) == pytest.approx(1 / 11)


def test_hit_rate():
    assert hit_rate_at_k(A_RETRIEVED, A_RELEVANT, 5) == 1.0
    assert hit_rate_at_k(A_RETRIEVED, {16}, 5) == 0.0
    assert hit_rate_at_k(A_RETRIEVED, {16}, 10) == 1.0


def test_zero_result_and_unjudged():
    assert is_zero_result([]) and not is_zero_result([1])
    assert count_unjudged([1, 2, 3, 4], judged={1, 3}) == 2
    assert count_unjudged(list(range(20)), judged=set(), k=10) == 10


def test_evaluate_query_collects_everything():
    metrics = evaluate_query(A_RETRIEVED, A_RELEVANT)
    assert metrics.n_relevant == 3 and metrics.n_retrieved == 10
    assert metrics.precision_at_5 == pytest.approx(0.2)
    assert metrics.recall_at_10 == pytest.approx(2 / 3)
    assert metrics.reciprocal_rank == pytest.approx(1 / 3)
    assert metrics.first_relevant_rank == 3
    assert (metrics.hit_at_5, metrics.hit_at_10) == (1.0, 1.0)
    assert metrics.zero_result is False


def test_macro_average_hand_calculated():
    results = [
        evaluate_query(A_RETRIEVED, A_RELEVANT),  # A
        evaluate_query([1, 2, 3], {7}),           # B: tidak ada yang relevan
        evaluate_query([], {4}),                  # C: nol hasil
        evaluate_query([4, 5], {4, 5}),           # D: sempurna tapi hanya dua hasil
    ]
    summary = aggregate_macro(results)
    assert summary["n_queries"] == 4
    assert summary["precision_at_5"] == pytest.approx((0.2 + 0 + 0 + 0.4) / 4)
    assert summary["recall_at_10"] == pytest.approx((2 / 3 + 0 + 0 + 1) / 4)
    assert summary["mrr_at_10"] == pytest.approx((1 / 3 + 0 + 0 + 1) / 4)
    assert summary["hit_rate_at_5"] == pytest.approx(0.5)
    assert summary["hit_rate_at_10"] == pytest.approx(0.5)
    assert summary["zero_result_queries"] == 1


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        recall_at_k([1], set(), 10)
    with pytest.raises(ValueError):
        evaluate_query([1, 1], {1})
    with pytest.raises(ValueError):
        precision_at_k([1], {1}, 0)
    with pytest.raises(ValueError):
        aggregate_macro([])
