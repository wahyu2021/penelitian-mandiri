from core.search.index import SearchIndex
from core.search.like_baseline import MATCH_SCORE, LikeBaselineSearch
from tests.conftest import make_record


def build_search():
    index = SearchIndex.from_records([
        make_record(3, "Renovasi Pasar Baru", opd_id=6, classification_label="Umum"),
        make_record(1, "Pasar Km 5 renovasi", opd_id=7, classification_label="Umum"),
        make_record(2, "Jembatan sungai", opd_id=6, classification_label="Umum"),
    ])
    return LikeBaselineSearch(index)


def ids(hits):
    return [hit.id for hit in hits]


def test_all_terms_must_match_and_order_is_id_ascending():
    assert ids(build_search().search("renovasi pasar")) == [1, 3]


def test_case_insensitive_substring():
    assert ids(build_search().search("PASA")) == [1, 3]


def test_typo_finds_nothing():
    assert build_search().search("pasr") == []


def test_term_in_other_displayed_column_matches():
    assert ids(build_search().search("komunikasi 1999 jembatan")) == [2]


def test_empty_query_returns_nothing():
    assert build_search().search("") == []
    assert build_search().search("   ") == []


def test_filters_and_top_n():
    search = build_search()
    assert ids(search.search("pasar", opd_id=7)) == [1]
    assert ids(search.search("pasar", top_n=1)) == [1]
    assert ids(search.search("pasar", top_n=None)) == [1, 3]


def test_score_is_constant_match_marker():
    assert {hit.score for hit in build_search().search("pasar")} == {MATCH_SCORE}
