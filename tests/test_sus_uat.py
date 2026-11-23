"""Uji hitung tangan SUS, ringkasan UAT, dan skrip evaluasi PM-22."""

import csv

import pytest

from core.evaluation.sus import (
    calculate_sus_score,
    summarize_sus_responses,
    summarize_uat_results,
)
from scripts.evaluate_uat_sus import evaluate_field_study, write_empty_templates


def test_calculate_sus_score_hand_calculated():
    # Skor maksimal: ganjil=5, genap=1 -> (4*5 + 4*5) * 2.5 = 100.0
    assert calculate_sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0
    # Skor minimal: ganjil=1, genap=5 -> 0.0
    assert calculate_sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0
    # Semua netral (3) atau semua 5 -> (2*5 + 2*5)*2.5 = 50.0 dan (4*5 + 0)*2.5 = 50.0
    assert calculate_sus_score([3] * 10) == 50.0
    assert calculate_sus_score([5] * 10) == 50.0
    # Campuran hitung tangan: [4,2,5,2,4,2,4,1,5,2]
    # Ganjil (x-1): 3+4+3+3+4 = 17; Genap (5-x): 3+3+3+4+3 = 16 -> total=33 -> 33*2.5 = 82.5
    assert calculate_sus_score([4, 2, 5, 2, 4, 2, 4, 1, 5, 2]) == 82.5


def test_calculate_sus_score_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_sus_score([5, 1, 5])
    with pytest.raises(ValueError):
        calculate_sus_score([6, 1, 5, 1, 5, 1, 5, 1, 5, 1])
    with pytest.raises(ValueError):
        calculate_sus_score([True, 1, 5, 1, 5, 1, 5, 1, 5, 1])


def test_summarize_sus_empty_and_multiple_respondents():
    empty = summarize_sus_responses([])
    assert empty["status"] == "pending"
    assert empty["mean_sus"] is None

    res = summarize_sus_responses(
        [
            {"participant_code": "P01", "role": "petugas", **{f"q{i}": 5 if i % 2 else 1 for i in range(1, 11)}},
            {"participant_code": "P02", "role": "petugas", **{f"q{i}": 3 for i in range(1, 11)}},
        ]
    )
    assert res["status"] == "complete"
    assert res["n_respondents"] == 2
    assert res["mean_sus"] == 75.0
    assert res["median_sus"] == 75.0
    assert res["min_sus"] == 50.0
    assert res["max_sus"] == 100.0
    assert res["std_sus"] is not None
    assert any("ukuran sampel" in note.lower() for note in res["limitations"])


def test_summarize_uat_and_cli_mismatch_check(tmp_path):
    templates = write_empty_templates(tmp_path)
    assert templates["uat_template"].is_file()
    assert templates["sus_template"].is_file()

    # Belum diisi -> status pending
    pending = evaluate_field_study(templates["uat_template"], templates["sus_template"])
    assert pending["status"] == "pending"

    uat_csv = tmp_path / "uat.csv"
    with uat_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["participant_code", "role", "task_id", "task_name", "status", "duration_seconds", "notes"])
        writer.writerow(["P01", "petugas", "T01", "Login", "lulus", 20, ""])
        writer.writerow(["P01", "petugas", "T03", "Pencarian", "lulus_dengan_catatan", 45, "Butuh label lebih jelas"])
        writer.writerow(["P02", "petugas", "T01", "Login", "gagal", 60, "Lupa sandi"])

    sus_csv = tmp_path / "sus.csv"
    with sus_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["participant_code", "role", *[f"q{i}" for i in range(1, 11)], "notes"])
        writer.writerow(["P01", "petugas", 4, 2, 5, 2, 4, 2, 4, 1, 5, 2, ""])

    report = evaluate_field_study(uat_csv, sus_csv)
    assert report["status"] == "complete"
    assert report["uat"]["n_participants"] == 2
    assert report["uat"]["n_failed"] == 1
    assert report["uat"]["pass_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert len(report["uat"]["issues"]) == 2
    assert report["sus"]["mean_sus"] == 82.5
    assert any("P02" in w for w in report["participant_mismatch_warnings"])


def test_summarize_uat_rejects_unknown_status():
    with pytest.raises(ValueError, match="Status UAT tidak sah"):
        summarize_uat_results([{"participant_code": "P01", "task_id": "T01", "status": "ok"}])
