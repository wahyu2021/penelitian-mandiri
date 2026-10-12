from core.normalization import normalize_code, normalize_text, tokenize


def test_lowercase_and_punctuation_become_separators():
    assert normalize_text("Pembayaran, Termin ke-I (satu)!") == "pembayaran termin ke i satu"


def test_code_with_slashes_stays_one_token():
    assert tokenize("No. SPM : 123/LS/Diskominfo/2021") == ["no", "spm", "123/ls/diskominfo/2021"]


def test_spaces_around_slash_inside_code_are_removed():
    assert tokenize("999 / BT/10 / A") == ["999/bt/10/a"]


def test_abbreviations_expand_and_can_be_disabled():
    assert normalize_text("Kec. Kemuning Jl. Merdeka") == "kecamatan kemuning jalan merdeka"
    assert normalize_text("Kec. Kemuning", expand_abbreviations=False) == "kec kemuning"


def test_month_spelling_variants_are_unified():
    assert tokenize("Nopember Pebruari") == ["november", "februari"]


def test_empty_and_none():
    assert normalize_text("") == "" and normalize_text(None) == "" and tokenize("  ") == []


def test_query_and_document_use_same_pipeline():
    assert normalize_text("CV. Contoh  Mandiri") == normalize_text("cv contoh mandiri")


def test_normalize_code():
    assert normalize_code(" 999 / bt/10 /a. ") == "999/BT/10/A"
    assert normalize_code("") == ""


def test_slash_without_digits_splits_into_separate_tokens():
    assert tokenize("tenaga ahli/tukang dan alat/bahan") == [
        "tenaga", "ahli", "tukang", "dan", "alat", "bahan"
    ]
    # Sedangkan kode yang memuat digit tetap utuh
    assert tokenize("dokumen 999/bt/10/a dan sk/2021") == [
        "dokumen", "999/bt/10/a", "dan", "sk/2021"
    ]
