import pytest

from core.evaluation.agreement import percentage_agreement


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
