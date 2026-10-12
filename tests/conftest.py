"""Fixture dan helper bersama untuk seluruh pengujian unit."""
import pytest


def make_record(archive_id=1, summary="Bayar termin renovasi gedung", **overrides):
    """Buat record data arsip sintetis untuk pengujian search index."""
    record = {
        "id": archive_id,
        "opd_id": 6,
        "year": 1999,
        "status": 2,
        "summary_clean": summary,
        "spm_number": "123/LS/DISKOMINFO/2021",
        "party_name": "CV Contoh Mandiri",
        "opd_name": "Dinas Komunikasi",
        "classification_label": "Umum",
        "file_number": "1",
        "index_label": "",
        "location_block": "A",
        "location_rack": "",
        "location_row": "",
        "box_number": "",
        "has_document": False,
    }
    record.update(overrides)
    return record


@pytest.fixture
def sample_record_factory():
    """Fixture factory pembuat record arsip sintetis."""
    return make_record
