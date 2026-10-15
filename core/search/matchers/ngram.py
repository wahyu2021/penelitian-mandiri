"""Pencocok n-gram karakter (koefisien Dice), ditulis sendiri.

RapidFuzz tidak menyediakan metrik ini.
"""
from collections import Counter

from core.search.matchers.base import BaseMatcher

PAD_CHAR = " "


def character_ngrams(token: str, n: int) -> Counter:
    """Hitung n-gram karakter (multiset) dari token dengan padding spasi.

    Padding `n-1` spasi di kedua sisi membuat awal dan akhir kata ikut berbobot.
    Contoh n=2: `ab` -> {" a", "ab", "b "}.
    """
    padded = PAD_CHAR * (n - 1) + token + PAD_CHAR * (n - 1)
    return Counter(padded[i:i + n] for i in range(len(padded) - n + 1))


class DiceNgramMatcher(BaseMatcher):
    """Dice = 2 * |irisan| / (|A| + |B|) atas multiset n-gram karakter."""

    name = "ngram"

    def __init__(self, n: int = 2) -> None:
        if n < 1:
            raise ValueError("n harus bernilai minimal 1")
        self.n = n
        super().__init__()

    def similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        left_grams = character_ngrams(left, self.n)
        right_grams = character_ngrams(right, self.n)
        overlap = sum((left_grams & right_grams).values())
        return 2.0 * overlap / (sum(left_grams.values()) + sum(right_grams.values()))


# Alias untuk kompatibilitas penamaan
NGramMatcher = DiceNgramMatcher

