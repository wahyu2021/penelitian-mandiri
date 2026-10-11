"""Pencocok Jaro-Winkler (RapidFuzz)."""
from rapidfuzz.distance import JaroWinkler

from core.search.matchers.base import BaseMatcher


class JaroWinklerMatcher(BaseMatcher):
    """Kemiripan Jaro-Winkler dengan bobot awalan bawaan RapidFuzz (0,1)."""

    name = "jaro_winkler"

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return float(JaroWinkler.normalized_similarity(left, right))
