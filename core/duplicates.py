"""Deteksi pasangan kandidat duplikat arsip secara deterministik dan murni [PM-24]."""

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

VALID_DECISIONS = frozenset({"duplikat", "bukan_duplikat", "perlu_cek"})
MAX_BLOCK_SIZE = 25

REASON_PRIORITY = {
    "same_spm": 3,
    "same_summary": 2,
    "same_amount_opd_year": 1,
}


def _tokens(text: str) -> set[str]:
    return {tok for tok in text.lower().split() if len(tok) >= 2}


def _jaccard(a: str, b: str) -> float:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return 0.0
    union = ta | tb
    if not union:
        return 0.0
    return len(ta & tb) / len(union)


def find_duplicate_candidates(
    records: Sequence[Mapping[str, Any]],
    *,
    max_pairs: int = 200,
) -> List[Dict[str, Any]]:
    """Kelompokkan dan urutkan pasangan kandidat duplikat tanpa memodifikasi data sumber."""
    if max_pairs < 1:
        raise ValueError("max_pairs harus minimal 1.")

    by_id: Dict[int, Mapping[str, Any]] = {}
    spm_blocks: Dict[str, List[int]] = defaultdict(list)
    summary_blocks: Dict[str, List[int]] = defaultdict(list)
    amount_blocks: Dict[Tuple[Any, Any, int], List[int]] = defaultdict(list)

    for rec in records:
        aid = int(rec["id"])
        by_id[aid] = rec

        spm = str(rec.get("spm_number") or "").strip().lower()
        if spm:
            spm_blocks[spm].append(aid)

        summary_norm = str(rec.get("summary_normalized") or "").strip().lower()
        if len(summary_norm) >= 15:
            summary_blocks[summary_norm].append(aid)

        amount = rec.get("amount_rp")
        opd_id = rec.get("opd_id")
        year = rec.get("year")
        if amount is not None and int(amount) > 0 and opd_id is not None and year is not None:
            amount_blocks[(int(opd_id), int(year), int(amount))].append(aid)

    best_by_pair: Dict[Tuple[int, int], Dict[str, Any]] = {}

    def _register(a_id: int, b_id: int, reason: str, similarity: float) -> None:
        if a_id == b_id:
            return
        left, right = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        existing = best_by_pair.get((left, right))
        if existing is not None:
            old_prio = REASON_PRIORITY[existing["reason"]]
            new_prio = REASON_PRIORITY[reason]
            if new_prio < old_prio or (new_prio == old_prio and similarity <= existing["similarity"]):
                return
        best_by_pair[(left, right)] = {
            "archive_a_id": left,
            "archive_b_id": right,
            "reason": reason,
            "similarity": round(similarity, 4),
        }

    for ids in spm_blocks.values():
        if 2 <= len(ids) <= MAX_BLOCK_SIZE:
            for a_id, b_id in combinations(sorted(ids), 2):
                _register(a_id, b_id, "same_spm", 1.0)

    for ids in summary_blocks.values():
        if 2 <= len(ids) <= MAX_BLOCK_SIZE:
            for a_id, b_id in combinations(sorted(ids), 2):
                _register(a_id, b_id, "same_summary", 1.0)

    for ids in amount_blocks.values():
        if 2 <= len(ids) <= MAX_BLOCK_SIZE:
            for a_id, b_id in combinations(sorted(ids), 2):
                sum_a = str(by_id[a_id].get("summary_normalized") or "")
                sum_b = str(by_id[b_id].get("summary_normalized") or "")
                score = _jaccard(sum_a, sum_b)
                if score >= 0.70:
                    _register(a_id, b_id, "same_amount_opd_year", score)

    candidates = sorted(
        best_by_pair.values(),
        key=lambda item: (-item["similarity"], -REASON_PRIORITY[item["reason"]], item["archive_a_id"], item["archive_b_id"]),
    )
    return candidates[:max_pairs]
