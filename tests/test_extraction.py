from core.extraction import extract_metadata, parse_rupiah
from core.spm_types import CONFIDENCE_GUESS, describe_spm_type

FULL = (
    "Pembayaran termin ke I dan II atas pekerjaan pengadaan komputer dinas "
    "CV Contoh Mandiri No SPM : 123/LS/Diskominfo/2021 No SP2D : 4567/2021 "
    "tanggal : 14 desember 2021 Jumlah : Rp.250.000.000,-"
)


def test_full_example():
    meta = extract_metadata(FULL)
    assert meta["spm_number"] == "123/LS/DISKOMINFO/2021"
    assert meta["spm_sequence"] == "123"
    assert meta["spm_type_code"] == "LS"
    assert meta["spm_suffix"] == "DISKOMINFO/2021"
    assert meta["sp2d_number"] == "4567/2021"
    assert meta["document_date"] == "2021-12-14"
    assert meta["amount_rp"] == 250000000
    assert meta["party_name"] == "CV Contoh Mandiri"
    assert meta["has_spm_label"] is True


def test_newlines_and_spacing_variants():
    text = (
        "- Pembayaran renovasi ruang rapat serbaguna\n"
        " No. SPM:999/BT/5/P   \n"
        "Tanggal : 30 Maret 1999    Jumlah : Rp 150.000.000"
    )
    meta = extract_metadata(text)
    assert meta["spm_number"] == "999/BT/5/P"
    assert meta["document_date"] == "1999-03-30"
    assert meta["amount_rp"] == 150000000


def test_numeric_date():
    text = "No SPM : 1/LS/2 Tgl 05/11/2003 Jumlah : Rp 1.000"
    assert extract_metadata(text)["document_date"] == "2003-11-05"


def test_spm_type_variants_extraction():
    meta1 = extract_metadata("No SPM: 037/SPM - LS/Instansi/2009")
    assert meta1["spm_sequence"] == "37"
    assert meta1["spm_type_code"] == "LS"
    assert meta1["spm_suffix"] == "INSTANSI/2009"

    meta2 = extract_metadata("No SPM: 050/SPM/GU/Instansi/2010")
    assert meta2["spm_sequence"] == "50"
    assert meta2["spm_type_code"] == "GU"
    assert meta2["spm_suffix"] == "INSTANSI/2010"


def test_impossible_date_is_not_extracted():
    assert extract_metadata("No SPM : 1/LS/2 Tanggal : 31 Februari 2003")["document_date"] is None


def test_unreadable_fields_are_none_not_empty_string():
    meta = extract_metadata("Tes data")
    assert meta["has_spm_label"] is False
    assert all(meta[key] is None for key in (
        "spm_number", "sp2d_number", "document_date", "amount_rp", "party_name"))


def test_empty_input():
    assert extract_metadata("")["spm_number"] is None
    assert extract_metadata(None)["amount_rp"] is None


def test_parse_rupiah_cases():
    assert parse_rupiah("125.500.000,-") == 125500000
    assert parse_rupiah("50.250.125,-") == 50250125
    assert parse_rupiah("1.000.000,00") == 1000000
    assert parse_rupiah("150.000.000") == 150000000
    assert parse_rupiah("75.000.000,-") == 75000000
    assert parse_rupiah("") is None


def test_spm_type_is_always_guess():
    info = describe_spm_type("ls")
    assert info == {"code": "LS", "label": "Langsung (LS)", "confidence": CONFIDENCE_GUESS}
    assert describe_spm_type("ZZ")["label"] == "Tidak ada di kamus"
    assert describe_spm_type(None)["code"] is None
    assert "belum diketahui" in describe_spm_type("BT")["label"]
