"""Uji unit untuk modul metrik audit ekstraksi dan interval Wilson."""
import pytest

from core.evaluation.audit_metrics import (
    calculate_field_audit_metrics,
    calculate_percentage_agreement,
    wilson_score_interval,
)


def test_wilson_score_interval_hand_calculated():
    # Kasus sempurna: 10/10 -> p=1.0, lower ~ 0.722, upper = 1.0
    p, low, up = wilson_score_interval(10, 10)
    assert p == 1.0
    assert 0.70 < low < 0.75
    assert up == 1.0

    # Kasus nol: 0/10 -> p=0.0, lower = 0.0, upper ~ 0.278
    p, low, up = wilson_score_interval(0, 10)
    assert p == 0.0
    assert low == 0.0
    assert 0.25 < up < 0.30

    # Kasus seimbang: 50/100 -> p=0.5, simetris sekitar 0.5
    p, low, up = wilson_score_interval(50, 100)
    assert p == 0.5
    assert 0.40 < low < 0.45
    assert 0.55 < up < 0.60
    assert pytest.approx(0.5 - low, abs=1e-4) == pytest.approx(up - 0.5, abs=1e-4)


def test_wilson_invalid_inputs_raise():
    with pytest.raises(ValueError):
        wilson_score_interval(-1, 10)
    with pytest.raises(ValueError):
        wilson_score_interval(11, 10)
    assert wilson_score_interval(0, 0) == (0.0, 0.0, 0.0)


def test_calculate_field_audit_metrics_cases():
    verdicts = ["benar"] * 80 + ["salah"] * 10 + ["tidak_ada_di_teks"] * 10
    missed = [False] * 100

    metrics = calculate_field_audit_metrics(verdicts, missed)
    assert metrics["total_evaluated"] == 100
    assert metrics["n_benar"] == 80
    assert metrics["n_salah"] == 10
    assert metrics["n_tidak_ada_di_teks"] == 10
    assert metrics["n_extracted"] == 90
    assert metrics["accuracy_extracted"] == pytest.approx(80 / 90)

    # Bila ada missed (false negative)
    missed_flags = [False] * 90 + [True] * 5 + [False] * 5
    m2 = calculate_field_audit_metrics(verdicts, missed_flags)
    assert m2["n_missed"] == 5


def test_calculate_percentage_agreement_cases():
    a = ["benar", "benar", "salah", "tidak_ada_di_teks"]
    b = ["benar", "salah", "salah", "tidak_ada_di_teks"]
    # 3 cocok dari 4 -> 75%
    assert calculate_percentage_agreement(a, b) == 0.75

    # Semua cocok
    assert calculate_percentage_agreement(a, a) == 1.0


def test_calculate_percentage_agreement_mismatched_length_raises():
    with pytest.raises(ValueError):
        calculate_percentage_agreement(["benar"], ["benar", "salah"])
    with pytest.raises(ValueError):
        calculate_percentage_agreement([], [])
