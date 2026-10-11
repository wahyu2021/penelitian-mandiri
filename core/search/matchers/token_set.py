"""Pencocok token set (RapidFuzz)."""
from typing import Sequence

from rapidfuzz import fuzz

from core.search.matchers.base import BaseMatcher

_PERCENT = 100.0


class TokenSetMatcher(BaseMatcher):
    """Skor `token_set_ratio` atas seluruh token field sekaligus.

    Perilaku bawaan RapidFuzz: bila token kueri merupakan himpunan bagian dari
    token field, skor 1,0 tanpa memedulikan urutan atau token tambahan.
    """

    name = "token_set"

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return float(fuzz.token_set_ratio(left, right)) / _PERCENT

    def score_field(self, query_tokens: Sequence[str], field_tokens: Sequence[str]) -> float:
        if not query_tokens or not field_tokens:
            return 0.0
        return self._cached_similarity(" ".join(query_tokens), " ".join(field_tokens))
