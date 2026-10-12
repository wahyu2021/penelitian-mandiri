"""Evaluator temu kembali untuk uji komparatif, analisis berstrata, dan diagnostik."""
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from core.evaluation.metrics import (
    MetricSummary,
    QueryMetrics,
    aggregate_macro,
    count_unjudged,
    evaluate_query,
)
from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers.base import BaseMatcher
from core.search.ranker import FieldRanker, equal_weights


class SearchEvaluator:
    """Evaluator untuk menjalankan pengujian temu kembali pada sekumpulan kueri."""

    def __init__(
        self,
        index: SearchIndex,
        additional_judgments: Optional[Dict[str, Dict[int, int]]] = None,
    ) -> None:
        self.index = index
        self.additional_judgments = additional_judgments or {}

    def _resolve_judgments(
        self, query: Dict[str, Any]
    ) -> Dict[int, int]:
        """Ambil kamus {archive_id: is_relevant} dari kueri dan penilaian tambahan."""
        q_id = str(query.get("query_id", ""))
        judged: Dict[int, int] = {
            int(j["archive_id"]): int(j["is_relevant"])
            for j in query.get("judgments", [])
        }
        if q_id in self.additional_judgments:
            judged.update(self.additional_judgments[q_id])
        return judged

    def evaluate_searcher(
        self,
        searcher_name: str,
        search_fn: Any,
        queries: Sequence[Dict[str, Any]],
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """Evaluasi satu fungsi/metode pencarian pada daftar kueri.

        Returns:
            Kamus berisi metrik makro, latensi, dan rincian per kategori kueri.
        """
        if not queries:
            raise ValueError("Daftar kueri tidak boleh kosong")

        query_metrics_list: List[QueryMetrics] = []
        latencies_ms: List[float] = []
        unjudged_counts: List[int] = []

        # Rekap per kelompok diagnostik
        by_source_metrics: Dict[str, List[QueryMetrics]] = defaultdict(list)
        by_type_metrics: Dict[str, List[QueryMetrics]] = defaultdict(list)
        by_noise_metrics: Dict[str, List[QueryMetrics]] = defaultdict(list)

        for q in queries:
            q_text = str(q.get("query_text", ""))
            source = str(q.get("source", "sintetis"))
            q_type = str(q.get("query_type", "umum"))
            noise = str(q.get("noise_type", "tanpa_gangguan"))

            judged_map = self._resolve_judgments(q)
            relevant_ids = {aid for aid, rel in judged_map.items() if rel == 1}

            # Ukur latensi pencarian
            t0 = time.perf_counter()
            hits = search_fn(q_text, top_n=top_n)
            t1 = time.perf_counter()
            latency = (t1 - t0) * 1000.0
            latencies_ms.append(latency)

            retrieved_ids = [h.id for h in hits]
            unjudged = count_unjudged(retrieved_ids, set(judged_map.keys()), k=top_n)
            unjudged_counts.append(unjudged)

            if not relevant_ids:
                # Kueri tanpa relevan dinilai: precision=0, recall=0, mrr=0
                qm = QueryMetrics(
                    n_relevant=0,
                    n_retrieved=len(retrieved_ids),
                    precision_at_5=0.0,
                    recall_at_10=0.0,
                    reciprocal_rank=0.0,
                    first_relevant_rank=None,
                    hit_at_5=0.0,
                    hit_at_10=0.0,
                    zero_result=len(retrieved_ids) == 0,
                )
            else:
                qm = evaluate_query(retrieved_ids, relevant_ids)

            query_metrics_list.append(qm)
            by_source_metrics[source].append(qm)
            by_type_metrics[q_type].append(qm)
            by_noise_metrics[noise].append(qm)

        # Agregasi makro keseluruhan
        overall_summary = aggregate_macro(query_metrics_list)
        overall_summary["unjudged_in_top10"] = sum(unjudged_counts)
        overall_summary["mean_latency_ms"] = sum(latencies_ms) / len(latencies_ms)
        sorted_latencies = sorted(latencies_ms)
        p95_idx = int(0.95 * len(sorted_latencies))
        p95_val = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        overall_summary["p95_latency_ms"] = p95_val

        # Agregasi per kategori
        by_source = {k: aggregate_macro(v) for k, v in by_source_metrics.items() if v}
        by_type = {k: aggregate_macro(v) for k, v in by_type_metrics.items() if v}
        by_noise = {k: aggregate_macro(v) for k, v in by_noise_metrics.items() if v}

        return {
            "searcher_name": searcher_name,
            "overall": overall_summary,
            "by_source": by_source,
            "by_type": by_type,
            "by_noise": by_noise,
        }


def run_comparative_evaluation(
    index: SearchIndex,
    queries: Sequence[Dict[str, Any]],
    matchers: Dict[str, BaseMatcher],
    tuned_weights_by_matcher: Optional[Dict[str, Dict[str, float]]] = None,
    additional_judgments: Optional[Dict[str, Dict[int, int]]] = None,
    top_n: int = 10,
) -> Dict[str, Any]:
    """Jalankan evaluasi komparatif lengkap: LIKE baseline vs Fuzzy Equal vs Fuzzy Tuned."""
    evaluator = SearchEvaluator(index, additional_judgments)
    tuned_weights_by_matcher = tuned_weights_by_matcher or {}

    results: Dict[str, Any] = {}

    # 1. LIKE baseline
    like_search = LikeBaselineSearch(index)
    results["like_baseline"] = evaluator.evaluate_searcher(
        searcher_name="like_baseline",
        search_fn=lambda q, top_n=top_n: like_search.search(q, top_n=top_n),
        queries=queries,
        top_n=top_n,
    )

    # 2. Fuzzy matchers dengan Bobot Sama Rata (Equal Weights)
    eq_w = equal_weights()
    for m_name, matcher in matchers.items():
        ranker_eq = FieldRanker(index, matcher, weights=eq_w)
        key = f"{m_name}_equal"
        results[key] = evaluator.evaluate_searcher(
            searcher_name=key,
            search_fn=lambda q, top_n=top_n, r=ranker_eq: r.search(q, top_n=top_n),
            queries=queries,
            top_n=top_n,
        )

    # 3. Fuzzy matchers dengan Bobot Tuned
    for m_name, matcher in matchers.items():
        tw = tuned_weights_by_matcher.get(m_name, eq_w)
        ranker_tuned = FieldRanker(index, matcher, weights=tw)
        key = f"{m_name}_tuned"
        results[key] = evaluator.evaluate_searcher(
            searcher_name=key,
            search_fn=lambda q, top_n=top_n, r=ranker_tuned: r.search(q, top_n=top_n),
            queries=queries,
            top_n=top_n,
        )

    return results
