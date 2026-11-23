"""Kalkulator System Usability Scale (SUS) dan ringkasan hasil Black Box / UAT [PM-22]."""

from collections import defaultdict
from statistics import median, stdev
from typing import Any, Dict, List, Mapping, Sequence

VALID_UAT_STATUSES = frozenset({"lulus", "lulus_dengan_catatan", "gagal"})


def _parse_likert(value: Any, *, item_number: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Butir SUS ke-{item_number} tidak boleh bertipe boolean.")
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned.isdecimal():
            raise ValueError(f"Butir SUS ke-{item_number} harus bilangan bulat 1..5: {value!r}")
        parsed = int(cleaned)
    elif isinstance(value, int):
        parsed = value
    else:
        raise ValueError(f"Butir SUS ke-{item_number} harus bilangan bulat 1..5: {value!r}")

    if not 1 <= parsed <= 5:
        raise ValueError(f"Butir SUS ke-{item_number} berada di luar rentang 1..5: {parsed}")
    return parsed


def calculate_sus_score(responses: Sequence[Any]) -> float:
    """Hitung skor SUS individual (0..100) memakai rumus standar Brooke (1996).

    Butir ganjil (Q1, Q3, ..., Q9) berkontribusi (jawaban - 1).
    Butir genap (Q2, Q4, ..., Q10) berkontribusi (5 - jawaban).
    Total kontribusi 10 butir dikalikan 2,5.
    """
    if len(responses) != 10:
        raise ValueError(f"Kuesioner SUS wajib berisi tepat 10 butir (diterima {len(responses)}).")

    total_points = 0
    for idx, raw in enumerate(responses, start=1):
        val = _parse_likert(raw, item_number=idx)
        if idx % 2 == 1:
            total_points += val - 1
        else:
            total_points += 5 - val
    return round(total_points * 2.5, 2)


def summarize_sus_responses(respondents: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Ringkas hasil SUS lintas peserta dari jawaban aktual."""
    if not respondents:
        return {
            "status": "pending",
            "n_respondents": 0,
            "mean_sus": None,
            "median_sus": None,
            "min_sus": None,
            "max_sus": None,
            "std_sus": None,
            "scores": [],
            "limitations": ["Belum ada jawaban kuesioner SUS aktual dari peserta."],
        }

    seen_codes = set()
    scores: List[Dict[str, Any]] = []
    numeric_scores: List[float] = []

    for row in respondents:
        code = str(row.get("participant_code", "")).strip()
        if not code:
            raise ValueError("Setiap baris jawaban SUS wajib memuat participant_code.")
        if code in seen_codes:
            raise ValueError(f"Duplikasi participant_code pada data SUS: {code}")
        seen_codes.add(code)

        answers = [row.get(f"q{i}") for i in range(1, 11)]
        score = calculate_sus_score(answers)
        numeric_scores.append(score)
        scores.append(
            {
                "participant_code": code,
                "role": str(row.get("role", "")).strip() or "petugas",
                "sus_score": score,
            }
        )

    n = len(numeric_scores)
    limitations = [
        "Skor SUS dihitung dari jawaban aktual peserta memakai rumus Brooke (1996)."
    ]
    if n < 5:
        limitations.append(
            f"Ukuran sampel sangat kecil ({n} peserta); interpretasi terbatas pada uji lapangan internal."
        )

    return {
        "status": "complete",
        "n_respondents": n,
        "mean_sus": round(sum(numeric_scores) / n, 2),
        "median_sus": round(float(median(numeric_scores)), 2),
        "min_sus": min(numeric_scores),
        "max_sus": max(numeric_scores),
        "std_sus": round(float(stdev(numeric_scores)), 2) if n >= 2 else None,
        "scores": scores,
        "limitations": limitations,
    }


def summarize_uat_results(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Ringkas hasil uji Black Box / UAT per skenario tugas dan catat masalah."""
    if not rows:
        return {
            "status": "pending",
            "n_participants": 0,
            "n_executions": 0,
            "n_passed": 0,
            "n_passed_with_notes": 0,
            "n_failed": 0,
            "pass_rate": None,
            "by_task": [],
            "issues": [],
            "limitations": ["Belum ada catatan hasil pelaksanaan uji UAT aktual."],
        }

    participants = set()
    by_task: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"task_id": "", "task_name": "", "total": 0, "lulus": 0, "lulus_dengan_catatan": 0, "gagal": 0}
    )
    task_order: List[str] = []
    issues: List[Dict[str, str]] = []
    counts = {"lulus": 0, "lulus_dengan_catatan": 0, "gagal": 0}

    for idx, row in enumerate(rows, start=1):
        code = str(row.get("participant_code", "")).strip()
        task_id = str(row.get("task_id", "")).strip()
        task_name = str(row.get("task_name", "")).strip()
        status = str(row.get("status", "")).strip().lower()
        note = str(row.get("notes", "") or "").strip()

        if not code or not task_id:
            raise ValueError(f"Baris UAT ke-{idx} wajib memuat participant_code dan task_id.")
        if status not in VALID_UAT_STATUSES:
            raise ValueError(
                f"Status UAT tidak sah pada baris ke-{idx} ({task_id}): {status!r}. "
                f"Pilihan sah: {sorted(VALID_UAT_STATUSES)}"
            )

        participants.add(code)
        counts[status] += 1
        if task_id not in by_task:
            task_order.append(task_id)
            by_task[task_id]["task_id"] = task_id
            by_task[task_id]["task_name"] = task_name or task_id
        by_task[task_id]["total"] += 1
        by_task[task_id][status] += 1

        if status == "gagal" or (status == "lulus_dengan_catatan" and note):
            issues.append(
                {
                    "participant_code": code,
                    "task_id": task_id,
                    "status": status,
                    "notes": note,
                }
            )

    total = len(rows)
    n_ok = counts["lulus"] + counts["lulus_dengan_catatan"]
    return {
        "status": "complete",
        "n_participants": len(participants),
        "n_executions": total,
        "n_passed": counts["lulus"],
        "n_passed_with_notes": counts["lulus_dengan_catatan"],
        "n_failed": counts["gagal"],
        "pass_rate": round(n_ok / total, 4),
        "by_task": [by_task[tid] for tid in task_order],
        "issues": issues,
        "limitations": [
            "Ringkasan UAT mencerminkan hasil uji fungsional Black Box pada sesi peserta terdaftar."
        ],
    }
