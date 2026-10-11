"""Pencocok Levenshtein ternormalisasi (RapidFuzz)."""
from rapidfuzz.distance import Levenshtein

from core.search.matchers.base import BaseMatcher


class LevenshteinMatcher(BaseMatcher):
    """Kemiripan = 1 - jarak Levenshtein / panjang string terpanjang."""

    name = "levenshtein"

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return float(Levenshtein.normalized_similarity(left, right))
