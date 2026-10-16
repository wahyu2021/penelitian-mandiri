"""Perangking dokumen berdasarkan skor gabungan per field."""
from typing import Dict, List, NamedTuple, Optional, Sequence

from core.normalization import tokenize
from core.search.index import SearchDocument, SearchIndex
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
        query_aware: bool = False,
    ) -> None:
        self._index = index
        self.matcher = matcher
        self.weights = normalize_weights(weights if weights is not None else equal_weights())
        self.query_aware = query_aware

    def get_query_weights(self, query: str, query_tokens: Sequence[str]) -> Dict[str, float]:
        """Hitung bobot adaptif berdasarkan pola kueri jika query_aware aktif."""
        if not self.query_aware:
            return self.weights

        has_digit = any(c.isdigit() for c in query)
        has_slash = "/" in query
        is_spm_like = has_digit and (has_slash or len(query_tokens) <= 2)

        w = dict(self.weights)
        if not is_spm_like and w.get(FIELD_SPM, 0.0) > 0:
            spm_w = w[FIELD_SPM]
            w[FIELD_SPM] = 0.0
            rem = w.get(FIELD_SUMMARY, 0.0) + w.get(FIELD_PARTY, 0.0)
            if rem > 0:
                w[FIELD_SUMMARY] += spm_w * (w.get(FIELD_SUMMARY, 0.0) / rem)
                w[FIELD_PARTY] += spm_w * (w.get(FIELD_PARTY, 0.0) / rem)
            else:
                w[FIELD_SUMMARY] = 1.0
        return w

    def score_document(
        self,
        query_tokens: Sequence[str],
        document: SearchDocument,
        effective_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Skor gabungan satu dokumen untuk token kueri."""
        w = effective_weights if effective_weights is not None else self.weights
        field_tokens = {
            FIELD_SUMMARY: document.summary_tokens,
            FIELD_SPM: document.spm_tokens,
            FIELD_PARTY: document.party_tokens,
        }
        return sum(
            w[field] * self.matcher.score_field(query_tokens, field_tokens[field])
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
        query_aware: Optional[bool] = None,
    ) -> List[SearchHit]:
        """Cari dan urutkan dokumen.

        Args:
            query: Kueri mentah (dinormalisasi dengan pipeline yang sama dengan dokumen).
            top_n: Batas hasil; None untuk semua.
            opd_id, year, status: Filter opsional.
            min_score: Hanya skor yang lebih besar dari nilai ini dikembalikan.
            query_aware: Override perilaku adaptif per pemanggilan (opsional).

        Returns:
            SearchHit berurut skor turun; seri diurutkan id naik agar deterministik.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        is_qa = self.query_aware if query_aware is None else query_aware
        eff_weights = self.get_query_weights(query, query_tokens) if is_qa else self.weights

        hits = []
        for document in self._index.filtered(opd_id, year, status):
            score = self.score_document(query_tokens, document, effective_weights=eff_weights)
            if score > min_score:
                hits.append(SearchHit(document.id, score))
        hits.sort(key=lambda hit: (-hit.score, hit.id))
        return hits if top_n is None else hits[:top_n]

