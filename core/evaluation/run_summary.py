"""Ringkasan run evaluasi IR murni (agregasi per metode, tuning, anti-kebocoran, status)."""

from collections import defaultdict
from statistics import median
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

VALID_SPLITS = ("test", "tuning")


def _to_float(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nilai numerik tidak valid untuk kolom '{field}': {value!r}") from exc


def _to_int(value: Any, *, field: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Nilai bulat tidak valid untuk kolom '{field}': {value!r}") from exc


def detect_split_leakage(
    rows: Sequence[Mapping[str, Any]],
    query_to_base_id: Optional[Mapping[str, str]] = None,
) -> List[str]:
    """Deteksi base_query_id yang muncul di split tuning sekaligus test."""
    if not query_to_base_id:
        return []
    bases_by_split: Dict[str, set[str]] = {"tuning": set(), "test": set()}
    for row in rows:
        split = str(row.get("split", "")).strip()
        if split not in bases_by_split:
            continue
        qid = str(row.get("query_id", "")).strip()
        base_id = query_to_base_id.get(qid)
        if base_id:
            bases_by_split[split].add(str(base_id))
    return sorted(bases_by_split["tuning"] & bases_by_split["test"])


def summarize_per_query_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    split: str,
    query_to_base_id: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Agregasi metrik per metode-konfigurasi secara ketat pada satu split ('test' atau 'tuning')."""
    if split not in VALID_SPLITS:
        raise ValueError(f"Split harus salah satu dari {VALID_SPLITS}.")

    leaked_base_ids = detect_split_leakage(rows, query_to_base_id)
    filtered_rows = [row for row in rows if str(row.get("split", "")).strip() == split]

    grouped: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    order: List[Tuple[str, str]] = []
    for row in filtered_rows:
        method = str(row.get("method", "")).strip()
        config = str(row.get("config", "")).strip()
        if not method or not config:
            raise ValueError("Setiap baris per_query harus memuat kolom method dan config.")
        key = (method, config)
        if key not in grouped:
            order.append(key)
        grouped[key].append(row)

    method_summary: List[Dict[str, Any]] = []
    for method, config in order:
        items = grouped[(method, config)]
        n = len(items)
        p5_vals = [_to_float(item["p5"], field="p5") for item in items]
        r10_vals = [_to_float(item["r10"], field="r10") for item in items]
        rr10_vals = [_to_float(item["rr10"], field="rr10") for item in items]
        hit5_vals = [_to_int(item["hit5"], field="hit5") for item in items]
        hit10_vals = [_to_int(item["hit10"], field="hit10") for item in items]
        zero_vals = [_to_int(item["zero_result"], field="zero_result") for item in items]
        lat_vals = [_to_float(item["latency_ms"], field="latency_ms") for item in items]
        unj_vals = [_to_float(item["unjudged_in_top10"], field="unjudged_in_top10") for item in items]

        method_summary.append(
            {
                "method": method,
                "config": config,
                "label": f"{method} ({config})",
                "n_queries": n,
                "mean_p5": round(sum(p5_vals) / n, 4),
                "mean_r10": round(sum(r10_vals) / n, 4),
                "mrr_at_10": round(sum(rr10_vals) / n, 4),
                "hit_at_5_rate": round(sum(hit5_vals) / n, 4),
                "hit_at_10_rate": round(sum(hit10_vals) / n, 4),
                "zero_result_rate": round(sum(zero_vals) / n, 4),
                "mean_latency_ms": round(sum(lat_vals) / n, 3),
                "median_latency_ms": round(float(median(lat_vals)), 3),
                "mean_unjudged_top10": round(sum(unj_vals) / n, 2),
            }
        )

    return {
        "split": split,
        "n_rows": len(filtered_rows),
        "n_queries": len({str(row["query_id"]) for row in filtered_rows}),
        "split_leakage_count": len(leaked_base_ids),
        "leaked_base_ids": leaked_base_ids,
        "method_summary": method_summary,
    }


def summarize_tuning_grid(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Ambil kombinasi bobot terbaik hasil grid search untuk setiap matcher."""
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    order: List[str] = []
    for row in rows:
        matcher = str(row.get("matcher", "")).strip()
        if not matcher:
            raise ValueError("Baris tuning_results wajib memuat kolom matcher.")
        if matcher not in grouped:
            order.append(matcher)
        grouped[matcher].append(
            {
                "matcher": matcher,
                "summary_weight": round(_to_float(row["summary_weight"], field="summary_weight"), 2),
                "spm_weight": round(_to_float(row["spm_weight"], field="spm_weight"), 2),
                "party_weight": round(_to_float(row["party_weight"], field="party_weight"), 2),
                "mrr_at_10": round(_to_float(row["mrr_at_10"], field="mrr_at_10"), 4),
                "precision_at_5": round(_to_float(row["precision_at_5"], field="precision_at_5"), 4),
                "unjudged_top10": _to_int(row["unjudged_top10"], field="unjudged_top10"),
            }
        )

    results: List[Dict[str, Any]] = []
    for matcher in order:
        candidates = grouped[matcher]
        best = max(
            candidates,
            key=lambda item: (item["mrr_at_10"], item["precision_at_5"], -item["unjudged_top10"]),
        )
        results.append({**best, "grid_size": len(candidates)})
    return results


def determine_run_status(
    *,
    run_meta: Mapping[str, Any],
    agreement_summary: Optional[Mapping[str, Any]],
    manifest_valid: bool,
    split_leakage_count: int,
) -> Tuple[str, List[str]]:
    """Tentukan status artefak run ('draft', 'pending', atau 'final') beserta alasannya."""
    draft_reasons: List[str] = []
    if not manifest_valid:
        draft_reasons.append(
            "Checksum SHA-256 berkas hasil tidak cocok atau manifest.sha256 tidak lengkap."
        )
    if split_leakage_count > 0:
        draft_reasons.append(
            f"Terdeteksi {split_leakage_count} kueri dasar yang muncul di split tuning maupun test."
        )
    if run_meta.get("mode") != "final":
        draft_reasons.append("Mode artefak run tercatat sebagai 'draft' pada run_meta.json.")
    if not bool(run_meta.get("tree_clean")):
        draft_reasons.append(
            "Status Git saat run diekspor belum bersih (tree_clean = false); ekspor ulang pada commit bersih untuk status final."
        )
    if draft_reasons:
        return "draft", draft_reasons

    agr_status = str((agreement_summary or {}).get("status", "")).strip()
    if agr_status not in ("complete", "complete_kappa_undefined"):
        return "pending", [
            "Penilaian kesepakatan dua penilai (PM-19) pada artefak run ini masih berstatus tertunda; "
            "metrik eksperimen tetap tertampil namun klaim validasi akhir menunggu penilaian lengkap."
        ]

    return "final", [
        "Manifest SHA-256 valid, commit Git bersih, tuning dan test terpisah, serta kesepakatan penilai lengkap."
    ]
