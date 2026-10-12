"""Modul penyetelan bobot field (tuning phase) dengan grid search."""
import math
from typing import Dict, List, Optional, Sequence, Tuple

from core.evaluation.metrics import precision_at_k, reciprocal_rank
from core.search.index import SearchIndex
from core.search.matchers.base import BaseMatcher
from core.search.ranker import (
    FIELD_PARTY,
    FIELD_SPM,
    FIELD_SUMMARY,
    FIELDS,
    FieldRanker,
    equal_weights,
)


def generate_weight_grid(step: float = 0.1) -> List[Dict[str, float]]:
    """Bangun daftar kombinasi bobot field pada rentang [0.0, 1.0] dengan total 1.0.

    Args:
        step: Ukuran langkah diskretisasi (default: 0.1).

    Returns:
        Daftar kamus bobot field yang dinormalisasi berjumlah 1.0.
    """
    if step <= 0.0 or step > 1.0:
        raise ValueError("Step harus berada di antara (0.0, 1.0]")

    n_steps = int(round(1.0 / step))
    grid: List[Dict[str, float]] = []

    for i in range(n_steps + 1):
        for j in range(n_steps + 1 - i):
            k = n_steps - i - j
            w_sum = round(i * step, 4)
            w_spm = round(j * step, 4)
            w_pty = round(k * step, 4)
            # Pastikan tidak ada bobot negatif dan total tepat 1.0
            if math.isclose(w_sum + w_spm + w_pty, 1.0, abs_tol=1e-5):
                grid.append({
                    FIELD_SUMMARY: w_sum,
                    FIELD_SPM: w_spm,
                    FIELD_PARTY: w_pty,
                })

    return grid


def evaluate_weights_on_queries(
    index: SearchIndex,
    matcher: BaseMatcher,
    weights: Dict[str, float],
    queries: Sequence[Dict[str, object]],
    top_n: int = 10,
    additional_judgments: Optional[Dict[str, Dict[int, int]]] = None,
) -> Tuple[float, float, int]:
    """Evaluasi satu konfigurasi bobot pada himpunan kueri.

    Args:
        index: SearchIndex dokumen arsip.
        matcher: Pencocok kemiripan string.
        weights: Konfigurasi bobot field.
        queries: Daftar kamus kueri set uji.
        top_n: Kedalaman perangkingan (default: 10).
        additional_judgments: Kamus opsional {query_id: {archive_id: is_relevant}}.

    Returns:
        Triplet (macro_mrr_at_10, macro_p_at_5, total_unjudged_in_top10).
    """
    if not queries:
        return 0.0, 0.0, 0

    ranker = FieldRanker(index, matcher, weights=weights)
    mrr_list: List[float] = []
    p5_list: List[float] = []
    total_unjudged = 0

    for q in queries:
        q_id = str(q.get("query_id", ""))
        q_text = str(q.get("query_text", ""))
        hits = ranker.search(q_text, top_n=top_n)
        retrieved_ids = [h.id for h in hits]

        # Gabungkan penilaian dari berkas utama dan penilaian tambahan jika ada
        judgments = q.get("judgments", [])
        judged_map: Dict[int, int] = {
            int(j["archive_id"]): int(j["is_relevant"]) for j in judgments
        }
        if additional_judgments and q_id in additional_judgments:
            judged_map.update(additional_judgments[q_id])

        # Dokumen relevan
        relevant_ids = {aid for aid, rel in judged_map.items() if rel == 1}

        # Hitung dokumen belum dinilai di Top-10
        unjudged_count = sum(1 for aid in retrieved_ids[:top_n] if aid not in judged_map)
        total_unjudged += unjudged_count

        if not relevant_ids:
            # Bila kueri tidak memiliki dokumen relevan yang dinilai
            mrr_list.append(0.0)
            p5_list.append(0.0)
            continue

        # Precision@5
        p5 = precision_at_k(retrieved_ids, relevant_ids, k=min(5, top_n))
        p5_list.append(p5)

        # Reciprocal Rank@10
        rr = reciprocal_rank(retrieved_ids, relevant_ids, k=top_n)
        mrr_list.append(rr)

    macro_mrr = sum(mrr_list) / len(mrr_list) if mrr_list else 0.0
    macro_p5 = sum(p5_list) / len(p5_list) if p5_list else 0.0

    return macro_mrr, macro_p5, total_unjudged


def tune_weights_grid_search(
    index: SearchIndex,
    matcher: BaseMatcher,
    tuning_queries: Sequence[Dict[str, object]],
    step: float = 0.1,
    additional_judgments: Optional[Dict[str, Dict[int, int]]] = None,
) -> Dict[str, object]:
    """Jalankan grid search penyetelan bobot field hanya pada kueri tuning.

    Aturan Ilmiah:
    - Kriteria utama: MRR@10 tertinggi.
    - Pemutus seri (tie-breaker): Precision@5 tertinggi.
    - Pemutus seri kedua: Jarak Euclidean terkecil ke bobot sama rata.
    """
    if not tuning_queries:
        raise ValueError("Daftar kueri tuning kosong.")

    # Validasi bahwa seluruh kueri benar berlabel tuning
    invalid_splits = [
        q.get("query_id") for q in tuning_queries if q.get("split") != "tuning"
    ]
    if invalid_splits:
        raise ValueError(
            f"Terdapat kueri bukan kelompok tuning yang disertakan: {invalid_splits}"
        )

    # 1. Evaluasi bobot dasar (equal weights)
    eq_w = equal_weights()
    eq_mrr, eq_p5, eq_unjudged = evaluate_weights_on_queries(
        index=index,
        matcher=matcher,
        weights=eq_w,
        queries=tuning_queries,
        additional_judgments=additional_judgments,
    )

    # 2. Grid search
    grid = generate_weight_grid(step=step)

    best_w = eq_w
    best_mrr = eq_mrr
    best_p5 = eq_p5
    best_unjudged = eq_unjudged
    all_results: List[Dict[str, object]] = []

    def dist_to_equal(w: Dict[str, float]) -> float:
        return sum((w[f] - (1.0 / 3.0)) ** 2 for f in FIELDS)

    for candidate in grid:
        mrr, p5, unjudged = evaluate_weights_on_queries(
            index=index,
            matcher=matcher,
            weights=candidate,
            queries=tuning_queries,
            additional_judgments=additional_judgments,
        )
        record = {
            "weights": candidate,
            "mrr_at_10": round(mrr, 4),
            "precision_at_5": round(p5, 4),
            "unjudged_top10": unjudged,
        }
        all_results.append(record)

        # Seleksi kandidat terbaik
        is_better = False
        if mrr > best_mrr + 1e-6:
            is_better = True
        elif math.isclose(mrr, best_mrr, abs_tol=1e-6):
            if p5 > best_p5 + 1e-6:
                is_better = True
            elif math.isclose(p5, best_p5, abs_tol=1e-6):
                # Seri: pilih yang paling dekat dengan equal weights
                if dist_to_equal(candidate) < dist_to_equal(best_w) - 1e-6:
                    is_better = True

        if is_better:
            best_w = candidate
            best_mrr = mrr
            best_p5 = p5
            best_unjudged = unjudged

    return {
        "matcher_name": matcher.name,
        "n_tuning_queries": len(tuning_queries),
        "best_weights": best_w,
        "best_mrr_at_10": round(best_mrr, 4),
        "best_precision_at_5": round(best_p5, 4),
        "best_unjudged_top10": best_unjudged,
        "equal_weights": eq_w,
        "equal_weights_mrr_at_10": round(eq_mrr, 4),
        "equal_weights_precision_at_5": round(eq_p5, 4),
        "equal_weights_unjudged_top10": eq_unjudged,
        "grid_step": step,
        "total_combinations": len(grid),
    }
