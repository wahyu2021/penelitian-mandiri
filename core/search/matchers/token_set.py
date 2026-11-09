"""Pencocok token set (RapidFuzz)."""
from typing import Sequence

from rapidfuzz import fuzz

from core.search.matchers.base import BaseMatcher

_PERCENT = 100.0


class TokenSetMatcher(BaseMatcher):
    """Skor `token_set_ratio` atas seluruh token field sekaligus.

    Perilaku bawaan RapidFuzz: bila token kueri merupakan himpunan bagian dari
    token field, skor 1,0 tanpa memedulikan urutan atau token tambahan.
    Untuk skor parsial (< 1,0), dikombinasikan dengan rata-rata kemiripan
    terbaik per token kueri sebagai pemutus seri.
    """

    name = "token_set"

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        l_clean = left.replace("/", " ")
        r_clean = right.replace("/", " ")
        set_sim = float(fuzz.token_set_ratio(l_clean, r_clean)) / _PERCENT
        if set_sim >= 1.0 or set_sim < 0.55:
            return set_sim
        l_sub = l_clean.split()
        r_sub = r_clean.split()
        if not l_sub or not r_sub:
            return set_sim
        tok_sim = sum(
            max(float(fuzz.ratio(qt, ft)) for ft in r_sub)
            for qt in l_sub
        ) / (len(l_sub) * _PERCENT)
        return 0.65 * set_sim + 0.35 * tok_sim

    def score_field(self, query_tokens: Sequence[str], field_tokens: Sequence[str]) -> float:
        if not query_tokens or not field_tokens:
            return 0.0
        return self._cached_similarity(" ".join(query_tokens), " ".join(field_tokens))
