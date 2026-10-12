"""Uji unit untuk modul metrik audit ekstraksi dan interval Wilson."""
import pytest

from core.evaluation.audit_metrics import (
    calculate_field_audit_metrics,
    calculate_percentage_agreement,
    wilson_score_interval,
)
from scripts.evaluate_extraction_audit import evaluate_audit_data


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
    # 80 benar, 10 salah, 5 terlewat, 5 tidak_ada_di_teks
    verdicts = (
        ["benar"] * 80 + ["salah"] * 10 + ["terlewat"] * 5 + ["tidak_ada_di_teks"] * 5
    )

    metrics = calculate_field_audit_metrics(verdicts)
    assert metrics["total_evaluated"] == 100
    assert metrics["n_benar"] == 80
    assert metrics["n_salah"] == 10
    assert metrics["n_terlewat"] == 5
    assert metrics["n_tidak_ada_di_teks"] == 5

    # Ketepatan (precision) = benar / (benar + salah) = 80 / 90
    assert metrics["n_extracted"] == 90
    assert metrics["ketepatan"] == pytest.approx(80 / 90)

    # Keterambilan (recall) = benar / (benar + terlewat) = 80 / 85
    assert metrics["n_in_text"] == 85
    assert metrics["keterambilan"] == pytest.approx(80 / 85)

    low_k, up_k = metrics["wilson_ci_ketepatan"]
    assert 0.0 <= low_k <= metrics["ketepatan"] <= up_k <= 1.0


def test_calculate_field_audit_metrics_empty_or_invalid_raises():
    with pytest.raises(ValueError, match="kosong"):
        calculate_field_audit_metrics(["benar", ""])
    with pytest.raises(ValueError, match="kosong"):
        calculate_field_audit_metrics(["benar", None])
    with pytest.raises(ValueError, match="nilai tidak sah"):
        calculate_field_audit_metrics(["benar", "ragu_ragu"])


def test_calculate_percentage_agreement_cases():
    a = ["benar", "benar", "salah", "tidak_ada_di_teks", "terlewat"]
    b = ["benar", "salah", "salah", "tidak_ada_di_teks", "terlewat"]
    # 4 cocok dari 5 -> 80%
    assert calculate_percentage_agreement(a, b) == 0.80
    # Semua cocok
    assert calculate_percentage_agreement(a, a) == 1.0


def test_evaluate_audit_data_integration():
    rows_a = [
        {
            "archive_id": "1",
            "verdict_spm": "benar",
            "verdict_sp2d": "tidak_ada_di_teks",
            "verdict_date": "benar",
            "verdict_amount": "salah",
            "verdict_party": "terlewat",
        },
        {
            "archive_id": "2",
            "verdict_spm": "terlewat",
            "verdict_sp2d": "benar",
            "verdict_date": "benar",
            "verdict_amount": "benar",
            "verdict_party": "tidak_ada_di_teks",
        },
    ]
    rows_b = [
        {
            "archive_id": "1",
            "verdict_spm": "benar",
            "verdict_sp2d": "tidak_ada_di_teks",
            "verdict_date": "benar",
            "verdict_amount": "salah",
            "verdict_party": "salah",  # Beda dengan rows_a (terlewat vs salah)
        },
        {
            "archive_id": "2",
            "verdict_spm": "terlewat",
            "verdict_sp2d": "benar",
            "verdict_date": "benar",
            "verdict_amount": "benar",
            "verdict_party": "tidak_ada_di_teks",
        },
    ]

    res = evaluate_audit_data(rows_a, rows_b)
    assert res["n_evaluated"] == 2
    assert res["fields"]["spm"]["n_benar"] == 1
    assert res["agreement"]["spm"] == 1.0
    assert res["agreement"]["party"] == 0.5  # 1 cocok dari 2
