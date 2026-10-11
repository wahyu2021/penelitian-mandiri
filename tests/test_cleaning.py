import pytest

from core.cleaning import (
    ISSUE_EMPTY_SUMMARY, ISSUE_INVALID_INPUT_DATE, ISSUE_INVALID_STATUS,
    ISSUE_INVALID_YEAR, ISSUE_MISSING_DOCUMENT, ISSUE_ORPHAN_CLASSIFICATION,
    ISSUE_ORPHAN_OPD, ISSUE_UPLOAD_ERROR_DOCUMENT, clean_archive_row,
    collapse_whitespace, parse_int, parse_iso_date,
)


def make_row(**overrides):
    row = {
        "id_arsip": "5", "opd_id": "6", "klasifikasi_id": "377", "no_berkas": " 1 ",
        "index_ar": "   ", "tahun": "1999", "input_tahun": "2017-09-28",
        "ringkasan": "Bayar  termin\n No. SPM:1/LS/5", "block": "A", "lokasi_rak": "R1",
        "lokasi_baris": "4", "no_box": "2", "tingkat_perkembangan": "Asli",
        "jumlah": "1 Berkas", "ket_berkas": "Asli", "ket_jra": "JRA",
        "stat_dokumen": "2", "dokumen": "a.pdf",
    }
    row.update(overrides)
    return row


def issue_types(issues):
    return {issue["issue_type"] for issue in issues}


def clean(row, opd=frozenset({6}), klas=frozenset({377})):
    return clean_archive_row(row, set(opd), set(klas))


def test_valid_row_has_no_issues():
    record, issues = clean(make_row())
    assert issues == []
    assert record["id"] == 5 and record["year"] == 1999 and record["status"] == 2
    assert record["summary_clean"] == "Bayar termin No. SPM:1/LS/5"
    assert record["quantity_label"] == "1 Berkas"
    assert record["document_filename"] == "a.pdf" and record["has_document"]


def test_orphan_opd_and_classification_are_flagged_not_hidden():
    record, issues = clean(make_row(opd_id="99", klasifikasi_id="1"))
    assert record["opd_id"] is None and record["opd_id_source"] == 99
    assert {ISSUE_ORPHAN_OPD, ISSUE_ORPHAN_CLASSIFICATION} <= issue_types(issues)


@pytest.mark.parametrize("value", ["0000-00-00", "", "2017-02-30", "bukan tanggal"])
def test_invalid_input_date(value):
    record, issues = clean(make_row(input_tahun=value))
    assert record["input_date"] is None
    assert ISSUE_INVALID_INPUT_DATE in issue_types(issues)


@pytest.mark.parametrize("value", ["", "abcd", "0", "3000"])
def test_invalid_year(value):
    record, issues = clean(make_row(tahun=value))
    assert record["year"] is None
    assert ISSUE_INVALID_YEAR in issue_types(issues)


def test_invalid_status_becomes_none_instead_of_default():
    record, issues = clean(make_row(stat_dokumen="9"))
    assert record["status"] is None
    assert ISSUE_INVALID_STATUS in issue_types(issues)


def test_empty_summary():
    _, issues = clean(make_row(ringkasan="  \n "))
    assert ISSUE_EMPTY_SUMMARY in issue_types(issues)


def test_missing_and_upload_error_documents_differ():
    record, issues = clean(make_row(dokumen=""))
    assert ISSUE_MISSING_DOCUMENT in issue_types(issues) and not record["has_document"]
    record, issues = clean(make_row(dokumen="<p>The uploaded file exceeds</p>"))
    assert issue_types(issues) == {ISSUE_UPLOAD_ERROR_DOCUMENT}
    assert record["document_filename"] is None


def test_invalid_id_raises():
    with pytest.raises(ValueError):
        clean(make_row(id_arsip="x"))


def test_helpers():
    assert collapse_whitespace(" a \n b ") == "a b"
    assert collapse_whitespace(None) == ""
    assert parse_int("-3") == -3 and parse_int("3.5") is None and parse_int(None) is None
    assert parse_iso_date("2020-02-29") == "2020-02-29"
    assert parse_iso_date("2021-02-29") is None
