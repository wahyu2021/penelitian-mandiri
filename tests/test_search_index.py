from core.search.index import SearchIndex, build_document, matches_filters, spm_search_tokens


def make_record(archive_id=1, summary="Bayar termin Pasar Kuto", **overrides):
    record = {
        "id": archive_id, "opd_id": 6, "year": 1999, "status": 2,
        "summary_clean": summary, "spm_number": "158/LS/DISHUB/2007",
        "party_name": "CV Arti Mandiri", "opd_name": "Dinas Perdagangan",
        "classification_label": "Pasar", "file_number": "1", "index_label": "",
        "location_block": "A", "location_rack": "", "location_row": "",
        "box_number": "", "has_document": False,
    }
    record.update(overrides)
    return record


def test_spm_tokens_include_whole_code_and_parts():
    assert spm_search_tokens("158/LS/DISHUB/2007") == (
        "158/ls/dishub/2007", "158", "ls", "dishub", "2007")
    assert spm_search_tokens(None) == ()
    assert spm_search_tokens("") == ()


def test_build_document_tokens():
    document = build_document(make_record())
    assert document.id == 1
    assert document.summary_tokens == ("bayar", "termin", "pasar", "kuto")
    assert document.party_tokens == ("cv", "arti", "mandiri")


def test_haystack_covers_displayed_columns_in_lowercase():
    haystack = build_document(make_record()).haystack
    for expected in ("dinas perdagangan", "1999", "bayar termin pasar kuto", "belum ada file"):
        assert expected in haystack
    assert haystack == haystack.lower()
    assert "download" in build_document(make_record(has_document=True)).haystack


def test_missing_optional_values_do_not_break_build():
    document = build_document({
        "id": 9, "opd_id": None, "year": None, "status": None,
        "summary_clean": "", "spm_number": None, "party_name": None})
    assert document.summary_tokens == () and document.spm_tokens == ()


def test_filters():
    document = build_document(make_record())
    assert matches_filters(document)
    assert matches_filters(document, opd_id=6, year=1999, status=2)
    assert not matches_filters(document, opd_id=7)
    assert not matches_filters(document, year=2000)
    assert not matches_filters(document, status=1)


def test_index_filtered_and_len():
    index = SearchIndex.from_records([
        make_record(1), make_record(2, opd_id=7), make_record(3, year=2001)])
    assert len(index) == 3
    assert [d.id for d in index.filtered(opd_id=7)] == [2]
    assert [d.id for d in index.filtered(year=2001)] == [3]
