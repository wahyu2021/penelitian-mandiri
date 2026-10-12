import pytest

from core.search.index import SearchIndex
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker, equal_weights, normalize_weights
from tests.conftest import make_record


def build_index():
    return SearchIndex.from_records([
        make_record(1, "renovasi pasar", spm_number=None, party_name=None, opd_id=6),
        make_record(2, "jembatan sungai", spm_number="123/LS/DISKOMINFO/2021",
                    party_name="CV Contoh Mandiri", opd_id=7),
        make_record(3, "renovasi pasar", spm_number=None, party_name=None, opd_id=6),
    ])


def summary_only():
    return {"summary": 1.0, "spm": 0.0, "party": 0.0}


def test_equal_weights_hand_calculated_score():
    ranker = FieldRanker(build_index(), create_matcher("levenshtein"))
    hits = ranker.search("pasr", top_n=None)
    # field ringkasan: max(sim(pasr, pasar)=0,8) ; spm & pihak kosong -> 0 ; bobot 1/3
    assert hits[0].score == pytest.approx(0.8 / 3)


def test_single_field_weight():
    ranker = FieldRanker(build_index(), create_matcher("levenshtein"), summary_only())
    assert ranker.search("pasr", top_n=None)[0].score == pytest.approx(0.8)


def test_spm_part_and_party_fields_are_searched():
    spm_ranker = FieldRanker(build_index(), create_matcher("levenshtein"),
                             {"summary": 0, "spm": 1, "party": 0})
    assert spm_ranker.search("123")[0].id == 2
    party_ranker = FieldRanker(build_index(), create_matcher("levenshtein"),
                               {"summary": 0, "spm": 0, "party": 1})
    top = party_ranker.search("contoh")[0]
    assert top.id == 2 and top.score == pytest.approx(1.0)


def test_ties_are_broken_by_id_ascending():
    ranker = FieldRanker(build_index(), create_matcher("levenshtein"), summary_only())
    ids = [hit.id for hit in ranker.search("renovasi pasar")]
    assert ids.index(1) < ids.index(3)


@pytest.mark.parametrize("name", FUZZY_METHOD_NAMES)
def test_exact_query_ranks_matching_document_first(name):
    ranker = FieldRanker(build_index(), create_matcher(name), summary_only())
    assert ranker.search("jembatan sungai")[0].id == 2


@pytest.mark.parametrize("name", FUZZY_METHOD_NAMES)
def test_typo_still_finds_document(name):
    ranker = FieldRanker(build_index(), create_matcher(name), summary_only())
    assert ranker.search("jembtan sungi")[0].id == 2


def test_filters_top_n_and_min_score():
    ranker = FieldRanker(build_index(), create_matcher("levenshtein"), summary_only())
    assert {hit.id for hit in ranker.search("pasar", top_n=None, opd_id=6)} <= {1, 3}
    assert len(ranker.search("pasar", top_n=1)) == 1
    assert ranker.search("pasar", min_score=1.0) == []


def test_empty_query_returns_nothing():
    ranker = FieldRanker(build_index(), create_matcher("levenshtein"))
    assert ranker.search("") == [] and ranker.search("!!!") == []


def test_normalize_weights():
    assert normalize_weights({"summary": 2, "spm": 1, "party": 1}) == {
        "summary": 0.5, "spm": 0.25, "party": 0.25}
    assert sum(equal_weights().values()) == pytest.approx(1.0)


@pytest.mark.parametrize("weights", [
    {"summary": 1, "spm": 1},
    {"summary": 1, "spm": 1, "party": -1},
    {"summary": 0, "spm": 0, "party": 0},
    {"summary": 1, "spm": 1, "party": 1, "extra": 1},
])
def test_invalid_weights_raise(weights):
    with pytest.raises(ValueError):
        normalize_weights(weights)
