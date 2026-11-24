"""Layanan tinjauan kandidat duplikat non-destruktif [PM-24]."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.duplicates import VALID_DECISIONS, find_duplicate_candidates

VALID_STATUS_FILTERS = frozenset({"unreviewed", "duplikat", "bukan_duplikat", "perlu_cek"})
VALID_REASONS = frozenset({"same_spm", "same_summary", "same_amount_opd_year"})


def _canonical_pair(a_id: int, b_id: int) -> tuple[int, int]:
    if a_id == b_id or a_id < 1 or b_id < 1:
        raise ValueError("Pasangan arsip harus terdiri atas dua ID valid yang berbeda.")
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def _format_archive_side(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": int(row["id"]),
        "year": int(row["year"]) if row["year"] is not None else None,
        "opd_name": str(row["opd_name"] or ""),
        "summary_raw": str(row["summary_raw"] or ""),
        "spm_number": row["spm_number"],
        "sp2d_number": row["sp2d_number"],
        "document_date": row["document_date"],
        "amount_rp": int(row["amount_rp"]) if row["amount_rp"] is not None else None,
        "party_name": row["party_name"],
        "location": {
            "block": row["location_block"],
            "rack": row["location_rack"],
            "row": row["location_row"],
            "box": row["box_number"],
        },
    }


def list_duplicate_candidates(
    connection: sqlite3.Connection,
    *,
    reason: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
    """Muat daftar pasangan kandidat duplikat beserta keputusan dan riwayat peninjauan."""
    if page < 1 or not 1 <= per_page <= 100:
        raise ValueError("Parameter paginasi page/per_page tidak valid.")
    if reason is not None and reason not in VALID_REASONS:
        raise ValueError("Parameter reason tidak valid.")
    if status is not None and status not in VALID_STATUS_FILTERS:
        raise ValueError("Parameter status tinjauan tidak valid.")

    archive_rows = connection.execute(
        """
        SELECT
            a.id,
            a.opd_id,
            a.year,
            a.summary_raw,
            a.summary_normalized,
            a.location_block,
            a.location_rack,
            a.location_row,
            a.box_number,
            COALESCE(o.name, '') AS opd_name,
            m.spm_number,
            m.sp2d_number,
            m.document_date,
            m.amount_rp,
            m.party_name
        FROM archive a
        LEFT JOIN opd o ON o.id = a.opd_id
        LEFT JOIN archive_metadata m ON m.archive_id = a.id
        ORDER BY a.id ASC
        """
    ).fetchall()

    by_id = {int(row["id"]): row for row in archive_rows}
    candidates = find_duplicate_candidates([dict(row) for row in archive_rows], max_pairs=200)

    reviews_rows = connection.execute(
        """
        SELECT dr.archive_a_id, dr.archive_b_id, dr.decision, dr.notes, dr.reviewed_at,
               u.username AS reviewed_by_username
        FROM duplicate_review dr
        JOIN user u ON u.id = dr.reviewed_by
        """
    ).fetchall()
    review_map = {(int(r["archive_a_id"]), int(r["archive_b_id"])): r for r in reviews_rows}

    history_rows = connection.execute(
        """
        SELECT h.archive_a_id, h.archive_b_id, h.old_decision, h.new_decision,
               h.notes, h.changed_at, u.username AS actor_username
        FROM duplicate_review_history h
        JOIN user u ON u.id = h.actor_id
        ORDER BY h.id DESC
        """
    ).fetchall()
    history_map: Dict[tuple[int, int], List[Dict[str, Any]]] = {}
    for h in history_rows:
        key = (int(h["archive_a_id"]), int(h["archive_b_id"]))
        bucket = history_map.setdefault(key, [])
        if len(bucket) < 5:
            bucket.append(
                {
                    "old_decision": h["old_decision"],
                    "new_decision": h["new_decision"],
                    "notes": h["notes"],
                    "actor_username": h["actor_username"],
                    "changed_at": h["changed_at"],
                }
            )

    summary_counts = {
        "total_candidates": len(candidates),
        "unreviewed": 0,
        "duplikat": 0,
        "bukan_duplikat": 0,
        "perlu_cek": 0,
    }

    enriched: List[Dict[str, Any]] = []
    for cand in candidates:
        key = (cand["archive_a_id"], cand["archive_b_id"])
        rev = review_map.get(key)
        decision = str(rev["decision"]) if rev else None
        if decision is None:
            summary_counts["unreviewed"] += 1
        elif decision in summary_counts:
            summary_counts[decision] += 1

        if reason and cand["reason"] != reason:
            continue
        if status == "unreviewed" and decision is not None:
            continue
        if status and status != "unreviewed" and decision != status:
            continue

        enriched.append(
            {
                "archive_a_id": cand["archive_a_id"],
                "archive_b_id": cand["archive_b_id"],
                "reason": cand["reason"],
                "similarity": cand["similarity"],
                "decision": decision,
                "notes": str(rev["notes"]) if rev else "",
                "reviewed_by": rev["reviewed_by_username"] if rev else None,
                "reviewed_at": rev["reviewed_at"] if rev else None,
                "history": history_map.get(key, []),
                "archive_a": _format_archive_side(by_id[cand["archive_a_id"]]),
                "archive_b": _format_archive_side(by_id[cand["archive_b_id"]]),
            }
        )

    total_filtered = len(enriched)
    pages = max(1, (total_filtered + per_page - 1) // per_page)
    safe_page = min(page, pages)
    start = (safe_page - 1) * per_page

    return {
        "summary": summary_counts,
        "items": enriched[start : start + per_page],
        "total": total_filtered,
        "page": safe_page,
        "per_page": per_page,
        "pages": pages,
    }


def save_duplicate_decision(
    connection: sqlite3.Connection,
    *,
    archive_a_id: int,
    archive_b_id: int,
    decision: str,
    notes: str,
    actor_id: int,
) -> Dict[str, Any]:
    """Simpan atau perbarui keputusan tinjauan pasangan duplikat beserta jejak audit."""
    left, right = _canonical_pair(archive_a_id, archive_b_id)
    cleaned_decision = (decision or "").strip().lower()
    if cleaned_decision not in VALID_DECISIONS:
        raise ValueError(f"Keputusan harus salah satu dari: {sorted(VALID_DECISIONS)}")
    cleaned_notes = (notes or "").strip()
    if len(cleaned_notes) > 1000:
        raise ValueError("Catatan maksimal 1000 karakter.")

    existing_archives = connection.execute(
        "SELECT id FROM archive WHERE id IN (?, ?)",
        (left, right),
    ).fetchall()
    if len(existing_archives) != 2:
        raise LookupError("Salah satu atau kedua arsip tidak ditemukan.")

    now = datetime.now(timezone.utc).isoformat()
    with connection:
        prev = connection.execute(
            "SELECT decision FROM duplicate_review WHERE archive_a_id = ? AND archive_b_id = ?",
            (left, right),
        ).fetchone()
        old_decision = prev["decision"] if prev else None

        connection.execute(
            """
            INSERT INTO duplicate_review (archive_a_id, archive_b_id, decision, notes, reviewed_by, reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(archive_a_id, archive_b_id) DO UPDATE SET
                decision = excluded.decision,
                notes = excluded.notes,
                reviewed_by = excluded.reviewed_by,
                reviewed_at = excluded.reviewed_at
            """,
            (left, right, cleaned_decision, cleaned_notes, actor_id, now),
        )
        connection.execute(
            """
            INSERT INTO duplicate_review_history
                (archive_a_id, archive_b_id, old_decision, new_decision, notes, actor_id, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (left, right, old_decision, cleaned_decision, cleaned_notes, actor_id, now),
        )
        connection.execute(
            "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (
                actor_id,
                "duplicate_decision_saved",
                json.dumps({"archive_a_id": left, "archive_b_id": right, "decision": cleaned_decision}),
                now,
            ),
        )

    actor_row = connection.execute("SELECT username FROM user WHERE id = ?", (actor_id,)).fetchone()
    return {
        "archive_a_id": left,
        "archive_b_id": right,
        "decision": cleaned_decision,
        "notes": cleaned_notes,
        "reviewed_by": actor_row["username"] if actor_row else None,
        "reviewed_at": now,
    }
