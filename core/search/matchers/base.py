"""Antarmuka dasar pencocokan fuzzy."""
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Sequence

CACHE_SIZE = 200_000


class BaseMatcher(ABC):
    """Pencocok kemiripan teks bernilai 0..1.

    Skor per field = rata-rata, atas token kueri, dari kemiripan terbaik
    token tersebut terhadap token field. Subclass cukup mengimplementasikan
    `similarity`; `TokenSetMatcher` menimpa `score_field`.
    """

    name: str = ""

    def __init__(self) -> None:
        self._cached_similarity = lru_cache(maxsize=CACHE_SIZE)(self.similarity)

    @abstractmethod
    def similarity(self, left: str, right: str) -> float:
        """Kemiripan dua token, 0..1. String kosong selalu 0."""

    def score_field(self, query_tokens: Sequence[str], field_tokens: Sequence[str]) -> float:
        """Skor kemiripan kueri terhadap satu field dokumen.

        Args:
            query_tokens: Token kueri ternormalisasi.
            field_tokens: Token field dokumen ternormalisasi.

        Returns:
            Nilai 0..1; 0 bila kueri atau field kosong.
        """
        if not query_tokens or not field_tokens:
            return 0.0
        total = 0.0
        for query_token in query_tokens:
            total += max(self._cached_similarity(query_token, token) for token in field_tokens)
        return total / len(query_tokens)
