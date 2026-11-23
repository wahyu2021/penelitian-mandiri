"""Layanan pembaca artefak run evaluasi (output/colab_bundle) dengan verifikasi manifest."""

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.evaluation.run_summary import (
    VALID_SPLITS,
    determine_run_status,
    summarize_per_query_rows,
    summarize_tuning_grid,
)

FORBIDDEN_COLUMNS = frozenset(
    {
        "query_text",
        "summary_raw",
        "summary_clean",
        "party_name",
        "spm_number",
        "sp2d_number",
        "amount_rp",
        "haystack",
        "nominal",
    }
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_manifest(bundle_dir: Path, required_files: Tuple[str, ...]) -> Dict[str, Any]:
    manifest_path = bundle_dir / "manifest.sha256"
    if not manifest_path.is_file():
        return {"valid": False, "checked_files": 0, "reason": "Berkas manifest.sha256 tidak ditemukan."}

    entries: Dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        parts = cleaned.split(None, 1)
        if len(parts) != 2:
            return {"valid": False, "checked_files": 0, "reason": "Format baris manifest.sha256 tidak sah."}
        checksum, filename = parts[0].strip().lower(), parts[1].strip()
        entries[filename] = checksum

    if not all(fname in entries for fname in required_files):
        return {
            "valid": False,
            "checked_files": len(entries),
            "reason": "Daftar berkas di manifest.sha256 tidak lengkap.",
        }

    for fname, expected in entries.items():
        target = (bundle_dir / fname).resolve()
        try:
            target.relative_to(bundle_dir.resolve())
        except ValueError:
            return {"valid": False, "checked_files": 0, "reason": "Path manifest di luar direktori bundle."}
        if not target.is_file():
            return {"valid": False, "checked_files": 0, "reason": f"Berkas {fname} di manifest hilang."}
        if _sha256_file(target) != expected:
            return {"valid": False, "checked_files": 0, "reason": f"Checksum {fname} tidak cocok."}

    return {"valid": True, "checked_files": len(entries), "reason": "Semua checksum manifest valid."}


def _read_safe_csv(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"Header CSV kosong pada {csv_path.name}.")
        forbidden = FORBIDDEN_COLUMNS.intersection(reader.fieldnames)
        if forbidden:
            raise ValueError(
                f"Berkas {csv_path.name} memuat kolom teks arsip terlarang: {sorted(forbidden)}"
            )
        return [dict(row) for row in reader]


def _empty_payload(split: str, reason: str) -> Dict[str, Any]:
    return {
        "available": False,
        "status": "empty",
        "status_reasons": [reason],
        "split": split,
        "provenance": None,
        "manifest": {"valid": False, "checked_files": 0, "reason": reason},
        "split_counts": {
            "n_queries": 0,
            "n_tuning_queries": 0,
            "n_test_queries": 0,
            "n_base_queries": 0,
            "n_tuning_base_queries": 0,
            "n_test_base_queries": 0,
            "split_leakage_count": 0,
            "leaked_base_ids": [],
        },
        "agreement": None,
        "method_summary": [],
        "tuning_best": [],
        "filters": {"methods": [], "configs": [], "query_types": [], "noise_types": [], "sources": []},
        "per_query": {"items": [], "total": 0, "page": 1, "per_page": 25, "pages": 1},
    }


def _load_bundle_raw(bundle_dir: Path) -> Optional[Dict[str, Any]]:
    meta_path = bundle_dir / "run_meta.json"
    per_query_path = bundle_dir / "per_query_results.csv"
    if not bundle_dir.is_dir() or not meta_path.is_file() or not per_query_path.is_file():
        return None

    run_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    per_query_rows = _read_safe_csv(per_query_path)

    tuning_path = bundle_dir / "tuning_results.csv"
    tuning_rows = _read_safe_csv(tuning_path) if tuning_path.is_file() else []

    agreement_path = bundle_dir / "agreement_summary.json"
    agreement_summary = (
        json.loads(agreement_path.read_text(encoding="utf-8"))
        if agreement_path.is_file()
        else None
    )

    manifest = _verify_manifest(bundle_dir, ("run_meta.json", "per_query_results.csv"))
    return {
        "run_meta": run_meta,
        "per_query_rows": per_query_rows,
        "tuning_rows": tuning_rows,
        "agreement_summary": agreement_summary,
        "manifest": manifest,
    }


def load_evaluation_run(
    bundle_dir: Path,
    *,
    split: str = "test",
    method: Optional[str] = None,
    config: Optional[str] = None,
    query_type: Optional[str] = None,
    noise_type: Optional[str] = None,
    source: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
) -> Dict[str, Any]:
    """Muat ringkasan run evaluasi beserta tabel agregat, bobot tuning, dan baris per kueri."""
    if split not in VALID_SPLITS:
        raise ValueError("Parameter split harus bernilai 'test' atau 'tuning'.")
    if page < 1 or not 1 <= per_page <= 100:
        raise ValueError("Parameter paginasi page/per_page tidak valid.")

    loaded = _load_bundle_raw(bundle_dir)
    if loaded is None:
        return _empty_payload(
            split,
            "Belum ada artefak run evaluasi pada direktori bundle. Jalankan ekspor bundle terlebih dahulu.",
        )

    run_meta = loaded["run_meta"]
    raw_rows = loaded["per_query_rows"]
    tuning_rows = loaded["tuning_rows"]
    agreement_summary = loaded["agreement_summary"]
    manifest = loaded["manifest"]

    query_to_base_id = run_meta.get("query_to_base_id")
    summary = summarize_per_query_rows(
        raw_rows,
        split=split,
        query_to_base_id=query_to_base_id if isinstance(query_to_base_id, dict) else None,
    )
    tuning_best = summarize_tuning_grid(tuning_rows) if tuning_rows else []

    status, status_reasons = determine_run_status(
        run_meta=run_meta,
        agreement_summary=agreement_summary,
        manifest_valid=bool(manifest["valid"]),
        split_leakage_count=int(summary["split_leakage_count"]),
    )

    split_rows = [row for row in raw_rows if str(row.get("split", "")).strip() == split]
    available_filters = {
        "methods": sorted({str(r["method"]) for r in split_rows if r.get("method")}),
        "configs": sorted({str(r["config"]) for r in split_rows if r.get("config")}),
        "query_types": sorted({str(r["query_type"]) for r in split_rows if r.get("query_type")}),
        "noise_types": sorted({str(r["noise_type"]) for r in split_rows if r.get("noise_type")}),
        "sources": sorted({str(r["source"]) for r in split_rows if r.get("source")}),
    }

    filtered_items: List[Dict[str, Any]] = []
    for row in split_rows:
        if method and row.get("method") != method:
            continue
        if config and row.get("config") != config:
            continue
        if query_type and row.get("query_type") != query_type:
            continue
        if noise_type and row.get("noise_type") != noise_type:
            continue
        if source and row.get("source") != source:
            continue
        filtered_items.append(
            {
                "query_id": str(row["query_id"]),
                "method": str(row["method"]),
                "config": str(row["config"]),
                "split": str(row["split"]),
                "source": str(row.get("source", "")),
                "query_type": str(row.get("query_type", "")),
                "noise_type": str(row.get("noise_type", "")),
                "n_relevant": int(float(row["n_relevant"])),
                "p5": float(row["p5"]),
                "r10": float(row["r10"]),
                "rr10": float(row["rr10"]),
                "hit5": int(float(row["hit5"])),
                "hit10": int(float(row["hit10"])),
                "zero_result": int(float(row["zero_result"])),
                "latency_ms": float(row["latency_ms"]),
                "unjudged_in_top10": int(float(row["unjudged_in_top10"])),
            }
        )

    total_filtered = len(filtered_items)
    total_pages = max(1, (total_filtered + per_page - 1) // per_page)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * per_page
    paged_items = filtered_items[start : start + per_page]

    return {
        "available": True,
        "status": status,
        "status_reasons": status_reasons,
        "split": split,
        "provenance": {
            "commit_sha": str(run_meta.get("commit_sha", "unknown")),
            "tree_clean": bool(run_meta.get("tree_clean", False)),
            "mode": str(run_meta.get("mode", "draft")),
            "seed": run_meta.get("seed"),
            "data_hash": str(run_meta.get("data_hash", "")),
            "testset_hash": str(run_meta.get("testset_hash", "")),
            "extractor_version": str(run_meta.get("extractor_version", "")),
            "exported_at": str(run_meta.get("exported_at", "")),
        },
        "manifest": manifest,
        "split_counts": {
            "n_queries": int(run_meta.get("n_queries", 0)),
            "n_tuning_queries": int(run_meta.get("n_tuning_queries", 0)),
            "n_test_queries": int(run_meta.get("n_test_queries", 0)),
            "n_base_queries": int(run_meta.get("n_base_queries", 0)),
            "n_tuning_base_queries": int(run_meta.get("n_tuning_base_queries", 0)),
            "n_test_base_queries": int(run_meta.get("n_test_base_queries", 0)),
            "split_leakage_count": summary["split_leakage_count"],
            "leaked_base_ids": summary["leaked_base_ids"],
        },
        "agreement": agreement_summary,
        "method_summary": summary["method_summary"],
        "tuning_best": tuning_best,
        "filters": available_filters,
        "per_query": {
            "items": paged_items,
            "total": total_filtered,
            "page": safe_page,
            "per_page": per_page,
            "pages": total_pages,
        },
    }


def export_evaluation_csv(bundle_dir: Path, *, split: str = "test") -> str:
    """Ekspor baris per-kueri pada split terpilih dalam format CSV."""
    payload = load_evaluation_run(bundle_dir, split=split, page=1, per_page=100)
    if not payload["available"]:
        raise FileNotFoundError("Artefak evaluasi belum tersedia untuk diekspor.")

    raw_rows = _read_safe_csv(bundle_dir / "per_query_results.csv")
    split_rows = [row for row in raw_rows if str(row.get("split", "")).strip() == split]
    if not split_rows:
        raise ValueError(f"Tidak ada baris hasil pada split '{split}'.")

    fieldnames = list(split_rows[0].keys())
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(split_rows)
    return buffer.getvalue()
