"""Metrik temu kembali per kueri dan rata-rata makro.

Definisi (k adalah batas peringkat):
- Precision@k = dokumen relevan di k teratas / k (penyebut tetap k).
- Recall@k    = dokumen relevan di k teratas / seluruh dokumen relevan.
- RR          = 1 / peringkat relevan pertama dalam k teratas, 0 bila tidak ada.
- Hit rate@k  = 1 bila ada minimal satu relevan di k teratas, selain itu 0.
- Kueri nol hasil = pencarian tidak mengembalikan dokumen apa pun.
Rata-rata dihitung makro, yaitu tiap kueri berbobot sama.
"""
from dataclasses import dataclass
from typing import Collection, Dict, Optional, Sequence, Union

PRECISION_K = 5
RECALL_K = 10
MRR_K = 10
HIT_RATE_KS = (5, 10)

MetricSummary = Dict[str, Union[int, float]]


def _validate(retrieved: Sequence[int], relevant: Collection[int], k: int) -> None:
    if k < 1:
        raise ValueError("k harus bernilai minimal 1")
    if not relevant:
        raise ValueError("Kueri harus punya minimal satu dokumen relevan")
    if len(set(retrieved)) != len(retrieved):
        raise ValueError("Daftar hasil memuat dokumen ganda")


def _relevant_hits(retrieved: Sequence[int], relevant: Collection[int], k: int) -> int:
    return sum(1 for doc_id in retrieved[:k] if doc_id in relevant)


def precision_at_k(retrieved: Sequence[int], relevant: Collection[int], k: int = PRECISION_K) -> float:
    """Precision@k dengan penyebut k meski hasil kurang dari k."""
    _validate(retrieved, relevant, k)
    return _relevant_hits(retrieved, relevant, k) / k


def recall_at_k(retrieved: Sequence[int], relevant: Collection[int], k: int = RECALL_K) -> float:
    """Recall@k terhadap seluruh dokumen relevan."""
    _validate(retrieved, relevant, k)
    return _relevant_hits(retrieved, relevant, k) / len(relevant)


def first_relevant_rank(
    retrieved: Sequence[int], relevant: Collection[int], k: int = MRR_K
) -> Optional[int]:
    """Peringkat (mulai 1) dokumen relevan pertama dalam k teratas; None bila tidak ada."""
    _validate(retrieved, relevant, k)
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant:
            return rank
    return None


def reciprocal_rank(retrieved: Sequence[int], relevant: Collection[int], k: int = MRR_K) -> float:
    """Reciprocal rank dalam k teratas; 0 bila tidak ada dokumen relevan."""
    rank = first_relevant_rank(retrieved, relevant, k)
    return 0.0 if rank is None else 1.0 / rank


def hit_rate_at_k(retrieved: Sequence[int], relevant: Collection[int], k: int) -> float:
    """1,0 bila ada dokumen relevan di k teratas, selain itu 0,0."""
    _validate(retrieved, relevant, k)
    return 1.0 if _relevant_hits(retrieved, relevant, k) > 0 else 0.0


def is_zero_result(retrieved: Sequence[int]) -> bool:
    """True bila pencarian tidak mengembalikan dokumen apa pun."""
    return len(retrieved) == 0


def count_unjudged(
    retrieved: Sequence[int], judged: Collection[int], k: int = RECALL_K
) -> int:
    """Banyak dokumen di k teratas yang belum pernah dinilai relevansinya."""
    return sum(1 for doc_id in retrieved[:k] if doc_id not in judged)


@dataclass(frozen=True)
class QueryMetrics:
    """Seluruh metrik satu kueri."""

    n_relevant: int
    n_retrieved: int
    precision_at_5: float
    recall_at_10: float
    reciprocal_rank: float
    first_relevant_rank: Optional[int]
    hit_at_5: float
    hit_at_10: float
    zero_result: bool


def evaluate_query(retrieved: Sequence[int], relevant: Collection[int]) -> QueryMetrics:
    """Hitung semua metrik satu kueri.

    Args:
        retrieved: ID dokumen hasil, urut dari peringkat 1, tanpa duplikat.
        relevant: ID dokumen relevan (minimal satu).

    Raises:
        ValueError: tidak ada dokumen relevan atau hasil memuat duplikat.
    """
    return QueryMetrics(
        n_relevant=len(relevant),
        n_retrieved=len(retrieved),
        precision_at_5=precision_at_k(retrieved, relevant, PRECISION_K),
        recall_at_10=recall_at_k(retrieved, relevant, RECALL_K),
        reciprocal_rank=reciprocal_rank(retrieved, relevant, MRR_K),
        first_relevant_rank=first_relevant_rank(retrieved, relevant, MRR_K),
        hit_at_5=hit_rate_at_k(retrieved, relevant, HIT_RATE_KS[0]),
        hit_at_10=hit_rate_at_k(retrieved, relevant, HIT_RATE_KS[1]),
        zero_result=is_zero_result(retrieved),
    )


def aggregate_macro(results: Sequence[QueryMetrics]) -> MetricSummary:
    """Rata-rata makro seluruh kueri.

    Returns:
        Kamus `n_queries`, `precision_at_5`, `recall_at_10`, `mrr_at_10`,
        `hit_rate_at_5`, `hit_rate_at_10`, `zero_result_queries`.

    Raises:
        ValueError: daftar kueri kosong.
    """
    if not results:
        raise ValueError("Tidak ada kueri untuk diagregasi")
    count = len(results)
    return {
        "n_queries": count,
        "precision_at_5": sum(r.precision_at_5 for r in results) / count,
        "recall_at_10": sum(r.recall_at_10 for r in results) / count,
        "mrr_at_10": sum(r.reciprocal_rank for r in results) / count,
        "hit_rate_at_5": sum(r.hit_at_5 for r in results) / count,
        "hit_rate_at_10": sum(r.hit_at_10 for r in results) / count,
        "zero_result_queries": sum(1 for r in results if r.zero_result),
    }
