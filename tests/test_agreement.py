import pytest

from core.evaluation.agreement import (
    binary_agreement_summary,
    categorical_agreement_summary,
    percentage_agreement,
)


def test_agreement_on_common_items_only():
    first = {1: True, 2: False, 3: True, 4: True}
    second = {1: True, 2: True, 3: True, 5: False}
    result = percentage_agreement(first, second)
    # butir bersama: 1, 2, 3 -> sepakat pada 1 dan 3
    assert result.n_compared == 3
    assert result.n_agreed == 2
    assert result.agreement_rate == pytest.approx(2 / 3)
    assert result.disagreements == (2,)


def test_perfect_and_zero_agreement():
    assert percentage_agreement({1: True}, {1: True}).agreement_rate == 1.0
    assert percentage_agreement({1: True}, {1: False}).agreement_rate == 0.0


def test_no_common_items_raises():
    with pytest.raises(ValueError):
        percentage_agreement({1: True}, {2: True})


def test_binary_agreement_hand_calculated():
    # a=2 (1,1), b=1 (1,0), c=0 (0,1), d=2 (0,0) -> n=5, Po=0.8
    # Pe = ((3*2) + (2*3)) / 25 = 12/25 = 0.48 -> kappa = (0.8 - 0.48) / 0.52 = 8/13
    pairs = [(1, 1), (1, 1), (1, 0), (0, 0), (0, 0)]
    q_types = ["topik", "topik", "sp2d", "sp2d", "sp2d"]
    result = binary_agreement_summary(pairs, n_expected=5, query_types=q_types)

    assert result["status"] == "complete"
    assert result["n_total"] == 5
    assert result["n_paired"] == 5
    assert result["n_agreed"] == 4
    assert result["percentage_agreement"] == pytest.approx(0.8)
    assert result["relevant_class_agreement"] == pytest.approx(4 / 5)
    assert result["cohen_kappa"] == pytest.approx(8 / 13)
    assert result["confusion_matrix"] == {
        "both_relevant": 2,
        "rater1_only_relevant": 1,
        "rater2_only_relevant": 0,
        "both_irrelevant": 2,
    }
    assert result["agreement_by_query_type"]["topik"] == {
        "n_samples": 2,
        "n_agreed": 2,
        "agreement": 1.0,
    }
    assert result["agreement_by_query_type"]["sp2d"]["n_agreed"] == 2
    assert result["agreement_by_query_type"]["sp2d"]["agreement"] == pytest.approx(2 / 3)


def test_binary_agreement_pending_when_empty_or_partial():
    empty_res = binary_agreement_summary([], n_expected=4)
    assert empty_res["status"] == "pending"
    assert empty_res["n_total"] == 4
    assert empty_res["n_paired"] == 0
    assert empty_res["cohen_kappa"] is None

    partial_res = binary_agreement_summary([(1, 1), (0, 0)], n_expected=5)
    assert partial_res["status"] == "pending"
    assert partial_res["n_total"] == 5
    assert partial_res["n_paired"] == 2
    assert partial_res["percentage_agreement"] is None
    assert partial_res["cohen_kappa"] is None
    assert any("2 dari 5" in note for note in partial_res["limitations"])


def test_binary_agreement_all_agree_kappa_undefined():
    res = binary_agreement_summary([(1, 1), (1, 1), (1, 1)], n_expected=3)
    assert res["status"] == "complete_kappa_undefined"
    assert res["n_agreed"] == 3
    assert res["percentage_agreement"] == 1.0
    assert res["cohen_kappa"] is None
    assert any("tidak terdefinisi" in note.lower() for note in res["limitations"])


def test_binary_agreement_imbalanced_adds_limitation_note():
    # 10 pasang: 9 keduanya relevan (1,1), 1 hanya penilai 1 (1,0) -> kelas 1 = 19/20 (95%)
    pairs = [(1, 1)] * 9 + [(1, 0)]
    res = binary_agreement_summary(pairs, n_expected=10)
    assert res["status"] == "complete"
    assert res["percentage_agreement"] == pytest.approx(0.9)
    # Penilai 2 hanya memilih kelas 1 -> Pe = 0.9, Po = 0.9 -> kappa = 0.0
    assert res["cohen_kappa"] == pytest.approx(0.0)
    assert any("tidak seimbang" in note.lower() for note in res["limitations"])


def test_categorical_agreement_hand_calculated():
    labels = ("benar", "salah", "terlewat", "tidak_ada_di_teks")
    # 4 pasang: (benar, benar) x2, (benar, salah) x1, (salah, salah) x1
    # R1: benar=3, salah=1 | R2: benar=2, salah=2 -> Pe = (3*2 + 1*2)/16 = 8/16 = 0.5
    # Po = 3/4 = 0.75 -> kappa = (0.75 - 0.5) / 0.5 = 0.5
    pairs = [("benar", "benar"), ("benar", "benar"), ("benar", "salah"), ("salah", "salah")]
    res = categorical_agreement_summary(pairs, labels=labels, n_expected=4)
    assert res["status"] == "complete"
    assert res["n_agreed"] == 3
    assert res["percentage_agreement"] == pytest.approx(0.75)
    assert res["cohen_kappa"] == pytest.approx(0.5)

    partial = categorical_agreement_summary(pairs[:2], labels=labels, n_expected=4)
    assert partial["status"] == "pending"
    assert partial["cohen_kappa"] is None
    assert partial["percentage_agreement"] is None
