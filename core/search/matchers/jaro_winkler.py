"""Pencocok Jaro-Winkler (RapidFuzz)."""
from typing import Sequence

from rapidfuzz.distance import JaroWinkler

from core.search.matchers.base import BaseMatcher


class JaroWinklerMatcher(BaseMatcher):
    """Kemiripan Jaro-Winkler dengan bobot awalan bawaan RapidFuzz (0,1)."""

    name = "jaro_winkler"

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return float(JaroWinkler.normalized_similarity(left, right))

    def score_field(self, query_tokens: Sequence[str], field_tokens: Sequence[str]) -> float:
        if not query_tokens or not field_tokens:
            return 0.0
        total = 0.0
        for query_token in query_tokens:
            best = max(self._cached_similarity(query_token, token) for token in field_tokens)
            total += best if best >= 0.78 else 0.0
        return total / len(query_tokens)
