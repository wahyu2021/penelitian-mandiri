"""Uji gerbang Tahap 1: hasil impor harus cocok dengan angka acuan spesifikasi.

Dump tidak masuk Git. Tentukan lokasinya lewat variabel lingkungan
SIMANIS_DUMP_PATH, atau letakkan di data/raw/alsys_arsip(1).sql.
"""
import os
from collections import Counter

import pytest

from core.cleaning import (
    ISSUE_INVALID_INPUT_DATE, ISSUE_ORPHAN_OPD, ISSUE_UPLOAD_ERROR_DOCUMENT,
    clean_archive_row,
)
from core.extraction import extract_metadata
from core.sql_dump_parser import parse_sql_dump

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "raw", "alsys_arsip(1).sql",
)
DUMP_PATH = os.environ.get("SIMANIS_DUMP_PATH", DEFAULT_PATH)

# Angka acuan dari spesifikasi track (bukan hasil evaluasi).
EXPECTED_TOTAL = 1737
EXPECTED_BY_STATUS = {1: 1590, 2: 147}
EXPECTED_ORPHAN_OPD = 143
EXPECTED_UPLOAD_ERROR = 11
EXPECTED_SPM_LABEL = 1344
EXPECTED_ZERO_INPUT_DATE = 147

pytestmark = pytest.mark.skipif(
    not os.path.isfile(DUMP_PATH), reason="Dump SQL tidak tersedia")


@pytest.fixture(scope="module")
def imported():
    dump = parse_sql_dump(DUMP_PATH)
    opd_ids = {int(row["id_opd"]) for row in dump["opd"]}
    class_ids = {int(row["id_klasifikasi"]) for row in dump["klasifikasi"]}
    records, issues = [], []
    for raw in dump["arsip"]:
        record, row_issues = clean_archive_row(raw, opd_ids, class_ids)
        records.append(record)
        issues.extend(row_issues)
    return records, issues


def test_total_records(imported):
    assert len(imported[0]) == EXPECTED_TOTAL


def test_status_breakdown(imported):
    assert dict(Counter(r["status"] for r in imported[0])) == EXPECTED_BY_STATUS


def test_issue_counts(imported):
    counts = Counter(i["issue_type"] for i in imported[1])
    assert counts[ISSUE_ORPHAN_OPD] == EXPECTED_ORPHAN_OPD
    assert counts[ISSUE_UPLOAD_ERROR_DOCUMENT] == EXPECTED_UPLOAD_ERROR
    assert counts[ISSUE_INVALID_INPUT_DATE] == EXPECTED_ZERO_INPUT_DATE


def test_spm_label_count(imported):
    labelled = sum(
        1 for r in imported[0] if extract_metadata(r["summary_clean"])["has_spm_label"])
    assert labelled == EXPECTED_SPM_LABEL


def test_ids_unique(imported):
    ids = [r["id"] for r in imported[0]]
    assert len(ids) == len(set(ids))
