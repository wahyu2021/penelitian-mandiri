"""Perangking dokumen berdasarkan skor gabungan per field."""
from typing import Dict, List, NamedTuple, Optional

from core.normalization import tokenize
from core.search.index import SearchIndex
from core.search.matchers.base import BaseMatcher

FIELD_SUMMARY = "summary"
FIELD_SPM = "spm"
FIELD_PARTY = "party"
FIELDS = (FIELD_SUMMARY, FIELD_SPM, FIELD_PARTY)


class SearchHit(NamedTuple):
    """Satu hasil pencarian."""

    id: int
    score: float


def equal_weights() -> Dict[str, float]:
    """Bobot sama rata untuk seluruh field."""
    return {field: 1.0 / len(FIELDS) for field in FIELDS}


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Validasi bobot dan skalakan agar berjumlah 1.

    Raises:
        ValueError: kunci tidak tepat FIELDS, ada nilai negatif, atau jumlah nol.
    """
    if set(weights) != set(FIELDS):
        raise ValueError(f"Bobot harus memuat tepat field {FIELDS}")
    if any(value < 0 for value in weights.values()):
        raise ValueError("Bobot tidak boleh negatif")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Jumlah bobot harus lebih dari nol")
    return {field: weights[field] / total for field in FIELDS}


class FieldRanker:
    """Skor dokumen = jumlah bobot * skor pencocok pada tiap field."""

    def __init__(
        self,
        index: SearchIndex,
        matcher: BaseMatcher,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._index = index
        self.matcher = matcher
        self.weights = normalize_weights(weights if weights is not None else equal_weights())

    def score_document(self, query_tokens: List[str], document) -> float:
        """Skor gabungan satu dokumen untuk token kueri."""
        field_tokens = {
            FIELD_SUMMARY: document.summary_tokens,
            FIELD_SPM: document.spm_tokens,
            FIELD_PARTY: document.party_tokens,
        }
        return sum(
            self.weights[field] * self.matcher.score_field(query_tokens, field_tokens[field])
            for field in FIELDS
        )

    def search(
        self,
        query: str,
        top_n: Optional[int] = 10,
        opd_id: Optional[int] = None,
        year: Optional[int] = None,
        status: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[SearchHit]:
        """Cari dan urutkan dokumen.

        Args:
            query: Kueri mentah (dinormalisasi dengan pipeline yang sama dengan dokumen).
            top_n: Batas hasil; None untuk semua.
            opd_id, year, status: Filter opsional.
            min_score: Hanya skor yang lebih besar dari nilai ini dikembalikan.

        Returns:
            SearchHit berurut skor turun; seri diurutkan id naik agar deterministik.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        hits = []
        for document in self._index.filtered(opd_id, year, status):
            score = self.score_document(query_tokens, document)
            if score > min_score:
                hits.append(SearchHit(document.id, score))
        hits.sort(key=lambda hit: (-hit.score, hit.id))
        return hits if top_n is None else hits[:top_n]
