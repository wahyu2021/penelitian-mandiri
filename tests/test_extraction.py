from core.extraction import extract_metadata, parse_rupiah
from core.spm_types import CONFIDENCE_GUESS, describe_spm_type

FULL = (
    "Pembayaran termin ke I dan II atas pekerjaan pengecetan terminal alang-alang lebar "
    "CV Arti Mandiri No SPM : 158/LS/Dishub/2007 No SP2D : 4858/2007 "
    "tanggal : 14 desember 2007 Jumlah : Rp.228.399.000,-"
)


def test_full_example():
    meta = extract_metadata(FULL)
    assert meta["spm_number"] == "158/LS/DISHUB/2007"
    assert meta["spm_sequence"] == "158"
    assert meta["spm_type_code"] == "LS"
    assert meta["spm_suffix"] == "DISHUB/2007"
    assert meta["sp2d_number"] == "4858/2007"
    assert meta["document_date"] == "2007-12-14"
    assert meta["amount_rp"] == 228399000
    assert meta["party_name"] == "CV Arti Mandiri"
    assert meta["has_spm_label"] is True


def test_newlines_and_spacing_variants():
    text = "- Pembayaran atas rehabilitasi Pasar Kuto\n No. SPM:446/BT/5/P   \nTanggal : 30 Maret 1999    Jumlah : Rp 172.900.000"
    meta = extract_metadata(text)
    assert meta["spm_number"] == "446/BT/5/P"
    assert meta["document_date"] == "1999-03-30"
    assert meta["amount_rp"] == 172900000


def test_numeric_date():
    assert extract_metadata("No SPM : 1/LS/2 Tgl 05/11/2003 Jumlah : Rp 1.000")["document_date"] == "2003-11-05"


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
    assert parse_rupiah("228.399.000,-") == 228399000
    assert parse_rupiah("52.381.486,-") == 52381486
    assert parse_rupiah("1.000.000,00") == 1000000
    assert parse_rupiah("172.900.000") == 172900000
    assert parse_rupiah("74.500.000,-") == 74500000
    assert parse_rupiah("") is None


def test_spm_type_is_always_guess():
    info = describe_spm_type("ls")
    assert info == {"code": "LS", "label": "Langsung (LS)", "confidence": CONFIDENCE_GUESS}
    assert describe_spm_type("ZZ")["label"] == "Tidak ada di kamus"
    assert describe_spm_type(None)["code"] is None
    assert "belum diketahui" in describe_spm_type("BT")["label"]
