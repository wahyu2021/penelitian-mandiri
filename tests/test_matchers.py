import pytest

from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.matchers.jaro_winkler import JaroWinklerMatcher
from core.search.matchers.levenshtein import LevenshteinMatcher
from core.search.matchers.ngram import DiceNgramMatcher, character_ngrams
from core.search.matchers.token_set import TokenSetMatcher


def test_levenshtein_hand_calculated():
    matcher = LevenshteinMatcher()
    # kitten -> sitting: jarak 3, panjang terpanjang 7 -> 1 - 3/7
    assert matcher.similarity("kitten", "sitting") == pytest.approx(4 / 7)
    # pasr -> pasar: jarak 1, panjang terpanjang 5 -> 0,8
    assert matcher.similarity("pasr", "pasar") == pytest.approx(0.8)
    assert matcher.similarity("pasar", "pasar") == 1.0


def test_jaro_winkler_known_value():
    # Nilai klasik martha/marhta = 0,9611
    assert JaroWinklerMatcher().similarity("martha", "marhta") == pytest.approx(0.9611, abs=1e-3)


def test_character_ngrams_with_padding():
    assert character_ngrams("ab", 2) == {" a": 1, "ab": 1, "b ": 1}
    assert sum(character_ngrams("ab", 3).values()) == 4  # "  a"," ab","ab ","b  "


def test_dice_hand_calculated():
    matcher = DiceNgramMatcher(n=2)
    assert matcher.similarity("ab", "ab") == 1.0
    # {" a","ab","b "} vs {" a","ac","c "}: irisan 1 -> 2*1/6
    assert matcher.similarity("ab", "ac") == pytest.approx(1 / 3)
    # night/nacht: irisan {" n","ht","t "} = 3 dari 6 dan 6 -> 2*3/12
    assert matcher.similarity("night", "nacht") == pytest.approx(0.5)
    # multiset: aaa vs aa -> irisan 3 dari 4 dan 3 -> 6/7
    assert matcher.similarity("aaa", "aa") == pytest.approx(6 / 7)


def test_dice_rejects_invalid_n():
    with pytest.raises(ValueError):
        DiceNgramMatcher(n=0)


@pytest.mark.parametrize("name", FUZZY_METHOD_NAMES)
def test_empty_strings_score_zero(name):
    matcher = create_matcher(name)
    assert matcher.similarity("", "abc") == 0.0
    assert matcher.similarity("abc", "") == 0.0
    assert matcher.score_field([], ["abc"]) == 0.0
    assert matcher.score_field(["abc"], []) == 0.0


def test_score_field_averages_best_match_per_query_token():
    matcher = LevenshteinMatcher()
    # pasr -> 0,8 terhadap pasar; kuto -> 1,0; rata-rata 0,9
    assert matcher.score_field(["pasr", "kuto"], ["pasar", "kuto"]) == pytest.approx(0.9)


def test_token_set_ignores_order_and_extra_tokens():
    matcher = TokenSetMatcher()
    field = ["rehabilitasi", "pasar", "kuto"]
    assert matcher.score_field(["pasar", "kuto"], field) == 1.0
    assert matcher.score_field(["kuto", "pasar"], field) == 1.0
    assert matcher.score_field(["jembatan"], field) < 0.5


def test_registry():
    assert FUZZY_METHOD_NAMES == ("levenshtein", "jaro_winkler", "token_set", "ngram")
    assert create_matcher("ngram", n=3).n == 3
    with pytest.raises(ValueError):
        create_matcher("tidak_ada")
