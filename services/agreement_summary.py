"""Ringkasan kesepakatan penilai relevansi dan audit ekstraksi dari basis data web."""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.evaluation.agreement import (
    binary_agreement_summary,
    categorical_agreement_summary,
)
from core.evaluation.audit_metrics import VALID_VERDICTS
from services.audit_review import FIELDS


def _pending_relevance_payload(
    *,
    n_total: int,
    n_paired: int,
    limitations: List[str],
) -> Dict[str, Any]:
    return {
        "status": "pending",
        "n_total": n_total,
        "n_paired": n_paired,
        "n_agreed": None,
        "percentage_agreement": None,
        "relevant_class_agreement": None,
        "cohen_kappa": None,
        "confusion_matrix": None,
        "agreement_by_query_type": {},
        "limitations": limitations,
    }


def summarize_relevance_agreement(
    connection: sqlite3.Connection,
    *,
    version: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Hitung ringkasan kesepakatan dua penilai relevansi per versi tugas penilaian web."""
    if version is not None:
        reviews = connection.execute(
            "SELECT version, created_at FROM relevance_review WHERE version = ?",
            (version,),
        ).fetchall()
    else:
        reviews = connection.execute(
            "SELECT version, created_at FROM relevance_review ORDER BY created_at DESC, version DESC"
        ).fetchall()

    results: List[Dict[str, Any]] = []
    for review in reviews:
        ver = review["version"]
        n_unique_pairs = int(
            connection.execute(
                "SELECT COUNT(*) FROM relevance_pair WHERE version = ?",
                (ver,),
            ).fetchone()[0]
        )
        n_sample_rows = int(
            connection.execute(
                "SELECT COUNT(*) FROM relevance_sample_row WHERE version = ?",
                (ver,),
            ).fetchone()[0]
        )
        reviewer_rows = connection.execute(
            """
            SELECT rr.slot, rr.user_id, u.username, rr.submitted_at,
                   (SELECT COUNT(*) FROM relevance_judgment rj
                    WHERE rj.version = rr.version AND rj.slot = rr.slot AND rj.is_relevant IS NOT NULL) AS rated_count
            FROM relevance_reviewer rr
            JOIN user u ON u.id = rr.user_id
            WHERE rr.version = ?
            ORDER BY rr.slot
            """,
            (ver,),
        ).fetchall()

        reviewers = [
            {
                "slot": int(row["slot"]),
                "user_id": int(row["user_id"]),
                "username": row["username"],
                "submitted_at": row["submitted_at"],
                "rated": int(row["rated_count"]),
                "total": n_unique_pairs,
            }
            for row in reviewer_rows
        ]
        by_slot = {item["slot"]: item for item in reviewers}
        slot1 = by_slot.get(1)
        slot2 = by_slot.get(2)

        paired_rows = connection.execute(
            """
            SELECT p.id, p.query_type, j1.is_relevant AS r1, j2.is_relevant AS r2
            FROM relevance_pair p
            JOIN relevance_judgment j1
              ON j1.version = p.version AND j1.pair_id = p.id AND j1.slot = 1 AND j1.is_relevant IS NOT NULL
            JOIN relevance_judgment j2
              ON j2.version = p.version AND j2.pair_id = p.id AND j2.slot = 2 AND j2.is_relevant IS NOT NULL
            WHERE p.version = ?
            ORDER BY p.id
            """,
            (ver,),
        ).fetchall()

        limitations: List[str] = []
        ready = (
            slot1 is not None
            and slot2 is not None
            and n_unique_pairs > 0
            and len(paired_rows) == n_unique_pairs
            and slot1["submitted_at"] is not None
            and slot2["submitted_at"] is not None
        )

        if not ready:
            if slot1 is None or slot2 is None:
                limitations.append("Kedua slot penilai relevansi harus terisi sebelum kesepakatan dihitung.")
            elif len(paired_rows) < n_unique_pairs:
                limitations.append(
                    f"Penilaian belum lengkap: baru {len(paired_rows)} dari {n_unique_pairs} "
                    "pasangan unik dinilai kedua pihak."
                )
            elif slot1["submitted_at"] is None or slot2["submitted_at"] is None:
                limitations.append(
                    "Seluruh pasangan telah terisi, tetapi salah satu atau kedua penilai belum "
                    "menyerahkan penilaian final; status tetap tertunda."
                )
            else:
                limitations.append("Belum ada pasangan sampel pada versi ini.")
            summary = _pending_relevance_payload(
                n_total=n_unique_pairs,
                n_paired=len(paired_rows),
                limitations=limitations,
            )
        else:
            pairs = [(int(row["r1"]), int(row["r2"])) for row in paired_rows]
            query_types = [row["query_type"] for row in paired_rows]
            summary = binary_agreement_summary(
                pairs,
                n_expected=n_unique_pairs,
                query_types=query_types,
            )

        if n_sample_rows != n_unique_pairs:
            summary["limitations"] = list(summary["limitations"]) + [
                f"Ringkasan web dihitung pada {n_unique_pairs} pasangan kueri dasar-arsip unik "
                f"(CSV sampel memiliki {n_sample_rows} baris termasuk varian)."
            ]

        results.append(
            {
                "version": ver,
                "created_at": review["created_at"],
                "n_sample_rows": n_sample_rows,
                "reviewers": reviewers,
                **summary,
            }
        )
    return results


def _audit_candidate_reviewers(connection: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT u.id AS user_id, u.username, u.role,
               EXISTS (
                   SELECT 1 FROM extraction_audit_assignment a WHERE a.user_id = u.id
               ) AS is_assigned,
               COUNT(CASE WHEN j.verdict IS NOT NULL THEN 1 END) AS rated_cells
        FROM user u
        LEFT JOIN extraction_audit_judgment j ON j.user_id = u.id
        WHERE u.id IN (
            SELECT user_id FROM extraction_audit_assignment
            UNION
            SELECT DISTINCT user_id FROM extraction_audit_judgment
        )
        GROUP BY u.id, u.username, u.role
        ORDER BY rated_cells DESC, u.username ASC
        """
    ).fetchall()
    return [
        {
            "user_id": int(row["user_id"]),
            "username": row["username"],
            "role": row["role"],
            "is_assigned": bool(row["is_assigned"]),
            "rated_cells": int(row["rated_cells"]),
        }
        for row in rows
    ]


def summarize_audit_agreement(
    connection: sqlite3.Connection,
    *,
    rater1_id: Optional[int] = None,
    rater2_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Hitung ringkasan kesepakatan audit ekstraksi antara dua penilai untuk 5 field."""
    dataset_row = connection.execute(
        "SELECT fingerprint, sample_count, source_filename, created_at FROM extraction_audit_dataset WHERE id = 1"
    ).fetchone()
    if dataset_row is None:
        return {
            "status": "pending",
            "dataset": None,
            "reviewers": [],
            "selected_raters": [],
            "overall": None,
            "fields": [],
            "limitations": ["Sampel audit ekstraksi belum dimuat atau belum ada penilaian tersimpan."],
        }

    dataset = {
        "fingerprint": dataset_row["fingerprint"],
        "sample_count": int(dataset_row["sample_count"]),
        "source_filename": dataset_row["source_filename"],
        "created_at": dataset_row["created_at"],
        "total_cells": int(dataset_row["sample_count"]) * len(FIELDS),
    }
    sample_count = dataset["sample_count"]
    candidates = _audit_candidate_reviewers(connection)
    by_id = {item["user_id"]: item for item in candidates}

    if (rater1_id is None) != (rater2_id is None):
        raise ValueError("Pilih kedua penilai audit atau kosongkan keduanya untuk pemilihan otomatis.")

    if rater1_id is not None and rater2_id is not None:
        if rater1_id == rater2_id:
            raise ValueError("Dua penilai audit yang dibandingkan harus berbeda.")
        if rater1_id not in by_id or rater2_id not in by_id:
            raise ValueError("Penilai audit yang dipilih tidak memiliki penugasan atau penilaian.")
        selected = [by_id[rater1_id], by_id[rater2_id]]
    elif len(candidates) >= 2:
        selected = candidates[:2]
    else:
        selected = candidates

    if len(selected) < 2:
        return {
            "status": "pending",
            "dataset": dataset,
            "reviewers": candidates,
            "selected_raters": selected,
            "overall": categorical_agreement_summary(
                [], labels=sorted(VALID_VERDICTS), n_expected=dataset["total_cells"]
            ),
            "fields": [
                {
                    "field": field,
                    **categorical_agreement_summary(
                        [], labels=sorted(VALID_VERDICTS), n_expected=sample_count
                    ),
                }
                for field in FIELDS
            ],
            "limitations": [
                "Kesepakatan audit ekstraksi memerlukan minimal dua penilai berbeda; "
                f"saat ini baru tersedia {len(selected)} penilai."
            ],
        }

    first_id = selected[0]["user_id"]
    second_id = selected[1]["user_id"]
    paired_rows = connection.execute(
        """
        SELECT j1.archive_id, j1.field_name, j1.verdict AS v1, j2.verdict AS v2
        FROM extraction_audit_judgment j1
        JOIN extraction_audit_judgment j2
          ON j2.archive_id = j1.archive_id
         AND j2.field_name = j1.field_name
         AND j2.user_id = ?
        WHERE j1.user_id = ?
          AND j1.verdict IS NOT NULL
          AND j2.verdict IS NOT NULL
        ORDER BY j1.archive_id, j1.field_name
        """,
        (second_id, first_id),
    ).fetchall()

    labels = sorted(VALID_VERDICTS)
    all_pairs = [(row["v1"], row["v2"]) for row in paired_rows]
    overall = categorical_agreement_summary(
        all_pairs,
        labels=labels,
        n_expected=dataset["total_cells"],
    )

    fields_summary: List[Dict[str, Any]] = []
    for field in FIELDS:
        field_pairs = [(row["v1"], row["v2"]) for row in paired_rows if row["field_name"] == field]
        field_summary = categorical_agreement_summary(
            field_pairs,
            labels=labels,
            n_expected=sample_count,
        )
        fields_summary.append({"field": field, **field_summary})

    return {
        "status": overall["status"],
        "dataset": dataset,
        "reviewers": candidates,
        "selected_raters": selected,
        "overall": overall,
        "fields": fields_summary,
        "limitations": overall["limitations"],
    }


def build_agreement_report(
    connection: sqlite3.Connection,
    *,
    version: Optional[str] = None,
    rater1_id: Optional[int] = None,
    rater2_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Susun laporan lengkap kesepakatan relevansi dan audit ekstraksi."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "relevance": summarize_relevance_agreement(connection, version=version),
        "audit": summarize_audit_agreement(
            connection,
            rater1_id=rater1_id,
            rater2_id=rater2_id,
        ),
    }
