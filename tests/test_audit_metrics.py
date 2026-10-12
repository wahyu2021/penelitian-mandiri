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

    res = evaluate_audit_data(rows_a, rows_b, rater_type="intra-rater")
    assert res["n_evaluated"] == 2
    assert res["fields"]["spm"]["n_benar"] == 1
    assert res["agreement"]["spm"] == 1.0
    assert res["agreement"]["party"] == 0.5  # 1 cocok dari 2
    assert res["agreement_type"] == "intra-rater"
    assert "Intra-rater" in res["agreement_type_label"]


def test_validate_audit_row_integrity_excel_simulation(tmp_path):
    """Uji bahwa berkas yang diedit dan disimpan ulang dari Excel tetap lolos verifikasi."""
    import json
    from scripts.evaluate_extraction_audit import read_audit_file

    manifest_file = tmp_path / "manifest.json"
    manifest_data = {
        "extractor_version": "v1.0.0",
        "reference_records": {
            "101": {
                "sample_id": 1,
                "summary_raw": "SPM 101/LS pengadaan alat kantor",
                "extracted_spm": "101/LS",
                "extracted_sp2d": "501/SP2D",
                "extracted_date": "2011-04-12",
                "extracted_amount": "208750000",
                "extracted_party": "CV MAJU",
            },
            "102": {
                "sample_id": 2,
                "summary_raw": "SPM 102/GU honorarium tim",
                "extracted_spm": "102/GU",
                "extracted_sp2d": "",
                "extracted_date": "2012-05-10",
                "extracted_amount": "15000000",
                "extracted_party": "",
            },
        },
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Simulasikan berkas yang disimpan Excel:
    # 1. Diawali UTF-8 BOM (\ufeff)
    # 2. Menggunakan newline CRLF (\r\n)
    # 3. Baris di-sort terbalik (102 sebelum 101)
    # 4. Kolom dibungkus tanda kutip
    # 5. Kolom verdict_* terisi
    excel_csv_content = (
        "\ufeff"
        '"sample_id","archive_id","archive_status","summary_raw",'
        '"extracted_spm","verdict_spm","extracted_sp2d","verdict_sp2d",'
        '"extracted_date","verdict_date","extracted_amount","verdict_amount",'
        '"extracted_party","verdict_party"\r\n'
        '"2","102","Aktif","SPM 102/GU honorarium tim",'
        '"102/GU","benar","","tidak_ada_di_teks",'
        '"2012-05-10","benar","15000000","benar",'
        '"","tidak_ada_di_teks"\r\n'
        '"1","101","Aktif","SPM 101/LS pengadaan alat kantor",'
        '"101/LS","benar","501/SP2D","benar",'
        '"2011-04-12","benar","208750000","benar",'
        '"CV MAJU","benar"\r\n'
    )
    csv_file = tmp_path / "audit_saved_by_excel.csv"
    csv_file.write_bytes(excel_csv_content.encode("utf-8"))

    rows = read_audit_file(csv_file)
    assert len(rows) == 2

    res = evaluate_audit_data(rows, manifest_path=manifest_file, rater_type="inter-rater")
    assert res["n_evaluated"] == 2
    assert res["fields"]["spm"]["n_benar"] == 2
    assert res["agreement_type"] == "inter-rater"


def test_validate_audit_row_integrity_tampering_detected(tmp_path):
    """Uji bahwa modifikasi tidak sengaja pada extracted_* terdeteksi dan ditolak."""
    import json

    manifest_file = tmp_path / "manifest.json"
    manifest_data = {
        "extractor_version": "v1.0.0",
        "reference_records": {
            "101": {
                "sample_id": 1,
                "summary_raw": "SPM 101/LS pengadaan alat kantor",
                "extracted_spm": "101/LS",
                "extracted_sp2d": "501/SP2D",
                "extracted_date": "2011-04-12",
                "extracted_amount": "208750000",
                "extracted_party": "CV MAJU",
            }
        },
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    # Baris di mana extracted_spm diubah secara tidak sengaja oleh pengguna di spreadsheet
    tampered_rows = [
        {
            "sample_id": "1",
            "archive_id": "101",
            "summary_raw": "SPM 101/LS pengadaan alat kantor",
            "extracted_spm": "101/DIUBAH",  # Tidak cocok dengan referensi
            "verdict_spm": "benar",
            "extracted_sp2d": "501/SP2D",
            "verdict_sp2d": "benar",
            "extracted_date": "2011-04-12",
            "verdict_date": "benar",
            "extracted_amount": "208750000",
            "verdict_amount": "benar",
            "extracted_party": "CV MAJU",
            "verdict_party": "benar",
        }
    ]

    with pytest.raises(ValueError, match="Integritas data terlanggar pada arsip ID 101"):
        evaluate_audit_data(tampered_rows, manifest_path=manifest_file)

