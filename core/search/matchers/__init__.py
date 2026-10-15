"""Registri pencocok fuzzy."""
from typing import Dict, Tuple

from core.search.matchers.base import BaseMatcher
from core.search.matchers.jaro_winkler import JaroWinklerMatcher
from core.search.matchers.levenshtein import LevenshteinMatcher
from core.search.matchers.ngram import DiceNgramMatcher, NGramMatcher
from core.search.matchers.token_set import TokenSetMatcher

_MATCHER_CLASSES: Dict[str, type] = {
    LevenshteinMatcher.name: LevenshteinMatcher,
    JaroWinklerMatcher.name: JaroWinklerMatcher,
    TokenSetMatcher.name: TokenSetMatcher,
    DiceNgramMatcher.name: DiceNgramMatcher,
}

FUZZY_METHOD_NAMES: Tuple[str, ...] = tuple(_MATCHER_CLASSES)


def create_matcher(name: str, **options: int) -> BaseMatcher:
    """Buat pencocok menurut nama.

    Args:
        name: Salah satu dari FUZZY_METHOD_NAMES.
        **options: Opsi konstruktor (mis. `n` untuk ngram).

    Raises:
        ValueError: nama tidak dikenal.
    """
    if name not in _MATCHER_CLASSES:
        raise ValueError(f"Metode tidak dikenal: {name!r}. Pilihan: {FUZZY_METHOD_NAMES}")
    return _MATCHER_CLASSES[name](**options)
