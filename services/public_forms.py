"""Layanan formulir kuesioner publik & tautan kunci 1 perangkat [PM-28]."""

import csv
import hashlib
import io
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from core.evaluation.sus import calculate_sus_score, summarize_sus_responses

VALID_FORM_KINDS = frozenset({"sus", "custom"})
VALID_QUESTION_TYPES = frozenset({"scale", "choice", "text", "textarea"})
VALID_ROLES = frozenset({"petugas", "admin"})

SUS_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "q1", "type": "scale", "label": "Saya merasa akan sering menggunakan sistem pencarian arsip ini.", "required": True},
    {"id": "q2", "type": "scale", "label": "Saya merasa sistem ini terlalu rumit padahal bisa lebih sederhana.", "required": True},
    {"id": "q3", "type": "scale", "label": "Saya merasa sistem ini mudah digunakan.", "required": True},
    {"id": "q4", "type": "scale", "label": "Saya merasa memerlukan bantuan teknisi untuk dapat menggunakan sistem ini.", "required": True},
    {"id": "q5", "type": "scale", "label": "Saya merasa berbagai fitur di sistem ini terintegrasi dengan baik.", "required": True},
    {"id": "q6", "type": "scale", "label": "Saya merasa terlalu banyak hal yang tidak konsisten pada sistem ini.", "required": True},
    {"id": "q7", "type": "scale", "label": "Saya membayangkan sebagian besar petugas dapat mempelajari sistem ini dengan cepat.", "required": True},
    {"id": "q8", "type": "scale", "label": "Saya merasa sistem ini merepotkan untuk digunakan.", "required": True},
    {"id": "q9", "type": "scale", "label": "Saya merasa percaya diri saat menggunakan sistem ini.", "required": True},
    {"id": "q10", "type": "scale", "label": "Saya perlu mempelajari banyak hal terlebih dahulu sebelum dapat memakai sistem ini dengan lancar.", "required": True},
    {"id": "notes", "type": "textarea", "label": "Catatan atau kendala penggunaan (opsional)", "required": False},
]


class LinkRevokedError(ValueError):
    """Tautan sudah dicabut oleh admin."""


class LinkConflictError(ValueError):
    """Tautan sudah pernah dikirim dan tidak dapat dikirim ulang."""


class DeviceClaimError(PermissionError):
    """Tautan sudah diklaim oleh perangkat lain."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _log(conn: sqlite3.Connection, actor_id: int, action: str, detail: Dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (actor_id, action, json.dumps(detail), now),
    )


def _normalize_questions(form_kind: str, raw_questions: Optional[Sequence[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if form_kind == "sus":
        return list(SUS_QUESTIONS)
    if not raw_questions or not isinstance(raw_questions, list):
        raise ValueError("Kuesioner kustom wajib memiliki minimal satu pertanyaan.")
    if len(raw_questions) > 50:
        raise ValueError("Jumlah pertanyaan maksimal 50.")

    normalized: List[Dict[str, Any]] = []
    seen_ids = set()
    for idx, q in enumerate(raw_questions, start=1):
        if not isinstance(q, dict):
            raise ValueError(f"Format pertanyaan ke-{idx} tidak valid.")
        q_id = str(q.get("id") or f"p{idx}").strip()
        if not q_id or q_id in seen_ids:
            q_id = f"p{idx}"
        seen_ids.add(q_id)
        q_type = str(q.get("type") or "").strip().lower()
        if q_type not in VALID_QUESTION_TYPES:
            raise ValueError(f"Jenis pertanyaan ke-{idx} tidak sah: {q_type!r}.")
        label = str(q.get("label") or "").strip()
        if not 3 <= len(label) <= 400:
            raise ValueError(f"Teks pertanyaan ke-{idx} wajib 3–400 karakter.")
        required = bool(q.get("required", True))
        item: Dict[str, Any] = {"id": q_id, "type": q_type, "label": label, "required": required}
        if q_type == "choice":
            raw_opts = q.get("options")
            if not isinstance(raw_opts, list):
                raise ValueError(f"Pertanyaan pilihan ke-{idx} wajib memiliki daftar opsi.")
            options = [str(opt).strip() for opt in raw_opts if str(opt).strip()]
            if len(options) < 2:
                raise ValueError(f"Pertanyaan pilihan ke-{idx} wajib memiliki minimal 2 pilihan.")
            item["options"] = options
        normalized.append(item)
    return normalized


def create_form(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str,
    form_kind: str,
    questions: Optional[Sequence[Dict[str, Any]]],
    actor_id: int,
) -> Dict[str, Any]:
    """Buat formulir kuesioner SUS atau kustom baru."""
    cleaned_kind = (form_kind or "").strip().lower()
    if cleaned_kind not in VALID_FORM_KINDS:
        raise ValueError("Jenis formulir harus 'sus' atau 'custom'.")
    cleaned_title = (title or "").strip()
    if not 3 <= len(cleaned_title) <= 160:
        raise ValueError("Judul formulir wajib 3–160 karakter.")
    cleaned_desc = (description or "").strip()
    if len(cleaned_desc) > 1000:
        raise ValueError("Deskripsi formulir maksimal 1000 karakter.")

    normalized_questions = _normalize_questions(cleaned_kind, questions)
    slug = f"{cleaned_kind}-{secrets.token_hex(4)}"
    now = _now()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO survey_form (slug, title, description, form_kind, questions_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                cleaned_title,
                cleaned_desc,
                cleaned_kind,
                json.dumps(normalized_questions, ensure_ascii=False),
                actor_id,
                now,
            ),
        )
        form_id = int(cursor.lastrowid)
        _log(conn, actor_id, "public_form_created", {"form_id": form_id, "kind": cleaned_kind}, now)

    return {
        "id": form_id,
        "slug": slug,
        "title": cleaned_title,
        "description": cleaned_desc,
        "form_kind": cleaned_kind,
        "questions": normalized_questions,
        "created_at": now,
    }


def list_forms(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT f.id, f.slug, f.title, f.description, f.form_kind, f.created_at,
               (SELECT COUNT(*) FROM public_form_link l WHERE l.form_id = f.id) AS total_links,
               (SELECT COUNT(*) FROM survey_response r WHERE r.form_id = f.id) AS total_responses
        FROM survey_form f
        ORDER BY f.id DESC
        """
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "slug": str(row["slug"]),
            "title": str(row["title"]),
            "description": str(row["description"]),
            "form_kind": str(row["form_kind"]),
            "created_at": str(row["created_at"]),
            "total_links": int(row["total_links"]),
            "total_responses": int(row["total_responses"]),
        }
        for row in rows
    ]


def _link_status(row: sqlite3.Row) -> str:
    if row["revoked_at"] is not None:
        return "revoked"
    if row["submitted_at"] is not None:
        return "submitted"
    if row["claimed_device_hash"] is not None:
        return "claimed"
    return "unopened"


def get_form_detail(conn: sqlite3.Connection, form_id: int) -> Dict[str, Any]:
    form_row = conn.execute(
        "SELECT id, slug, title, description, form_kind, questions_json, created_at FROM survey_form WHERE id = ?",
        (form_id,),
    ).fetchone()
    if form_row is None:
        raise LookupError("Formulir tidak ditemukan.")

    questions = json.loads(form_row["questions_json"])
    link_rows = conn.execute(
        """
        SELECT id, token_preview, participant_code, participant_role, lock_single_device,
               claimed_device_hash, claimed_at, submitted_at, revoked_at, created_at
        FROM public_form_link
        WHERE form_id = ?
        ORDER BY id DESC
        """,
        (form_id,),
    ).fetchall()

    links = [
        {
            "id": int(r["id"]),
            "token_preview": str(r["token_preview"]),
            "participant_code": str(r["participant_code"]),
            "participant_role": str(r["participant_role"]),
            "lock_single_device": bool(r["lock_single_device"]),
            "status": _link_status(r),
            "claimed_at": r["claimed_at"],
            "submitted_at": r["submitted_at"],
            "revoked_at": r["revoked_at"],
            "created_at": str(r["created_at"]),
        }
        for r in link_rows
    ]

    resp_rows = conn.execute(
        """
        SELECT id, link_id, participant_code, participant_role, answers_json, sus_score, submitted_at
        FROM survey_response
        WHERE form_id = ?
        ORDER BY id DESC
        """,
        (form_id,),
    ).fetchall()

    responses: List[Dict[str, Any]] = []
    sus_inputs: List[Dict[str, Any]] = []
    for r in resp_rows:
        answers = json.loads(r["answers_json"])
        responses.append(
            {
                "id": int(r["id"]),
                "link_id": int(r["link_id"]),
                "participant_code": str(r["participant_code"]),
                "participant_role": str(r["participant_role"]),
                "answers": answers,
                "sus_score": float(r["sus_score"]) if r["sus_score"] is not None else None,
                "submitted_at": str(r["submitted_at"]),
            }
        )
        if form_row["form_kind"] == "sus":
            sus_inputs.append(
                {
                    "participant_code": str(r["participant_code"]),
                    "role": str(r["participant_role"]),
                    **{f"q{i}": answers.get(f"q{i}") for i in range(1, 11)},
                }
            )

    sus_summary = summarize_sus_responses(sus_inputs) if form_row["form_kind"] == "sus" else None
    return {
        "form": {
            "id": int(form_row["id"]),
            "slug": str(form_row["slug"]),
            "title": str(form_row["title"]),
            "description": str(form_row["description"]),
            "form_kind": str(form_row["form_kind"]),
            "questions": questions,
            "created_at": str(form_row["created_at"]),
        },
        "links": links,
        "responses": responses,
        "sus_summary": sus_summary,
    }


def create_public_link(
    conn: sqlite3.Connection,
    *,
    form_id: int,
    participant_code: str,
    participant_role: str,
    lock_single_device: bool,
    actor_id: int,
) -> Dict[str, Any]:
    """Terbitkan token unik baru untuk 1 peserta anonim."""
    form_row = conn.execute("SELECT id FROM survey_form WHERE id = ?", (form_id,)).fetchone()
    if form_row is None:
        raise LookupError("Formulir tidak ditemukan.")

    code = (participant_code or "").strip()
    if not 1 <= len(code) <= 40:
        raise ValueError("Kode peserta wajib 1–40 karakter (gunakan kode anonim, mis. P01).")
    role = (participant_role or "petugas").strip().lower()
    if role not in VALID_ROLES:
        raise ValueError("Peran peserta harus 'petugas' atau 'admin'.")

    raw_token = secrets.token_urlsafe(24)
    token_hash = _sha256(raw_token)
    preview = f"{raw_token[:6]}...{raw_token[-4:]}"
    now = _now()

    with conn:
        cursor = conn.execute(
            """
            INSERT INTO public_form_link (
                form_id, token_hash, token_preview, participant_code, participant_role,
                lock_single_device, created_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (form_id, token_hash, preview, code, role, 1 if lock_single_device else 0, actor_id, now),
        )
        link_id = int(cursor.lastrowid)
        _log(conn, actor_id, "public_form_link_created", {"form_id": form_id, "link_id": link_id, "participant_code": code}, now)

    return {
        "id": link_id,
        "form_id": form_id,
        "token": raw_token,
        "token_preview": preview,
        "public_path": f"/f/{raw_token}",
        "participant_code": code,
        "participant_role": role,
        "lock_single_device": bool(lock_single_device),
        "status": "unopened",
        "created_at": now,
    }


def reset_link_device(conn: sqlite3.Connection, *, link_id: int, actor_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT id, participant_code FROM public_form_link WHERE id = ?", (link_id,)).fetchone()
    if row is None:
        raise LookupError("Tautan tidak ditemukan.")
    now = _now()
    with conn:
        conn.execute(
            "UPDATE public_form_link SET claimed_device_hash = NULL, claimed_at = NULL WHERE id = ?",
            (link_id,),
        )
        _log(conn, actor_id, "public_form_link_device_reset", {"link_id": link_id}, now)
    return {"id": link_id, "reset": True}


def revoke_link(conn: sqlite3.Connection, *, link_id: int, actor_id: int) -> Dict[str, Any]:
    row = conn.execute("SELECT id, revoked_at FROM public_form_link WHERE id = ?", (link_id,)).fetchone()
    if row is None:
        raise LookupError("Tautan tidak ditemukan.")
    now = row["revoked_at"] or _now()
    if row["revoked_at"] is None:
        with conn:
            conn.execute("UPDATE public_form_link SET revoked_at = ? WHERE id = ?", (now, link_id))
            _log(conn, actor_id, "public_form_link_revoked", {"link_id": link_id}, now)
    return {"id": link_id, "revoked_at": now}


def device_cookie_name(link_id: int) -> str:
    return f"pm_form_device_{link_id}"


def verify_or_claim_device(
    conn: sqlite3.Connection,
    *,
    table: str,
    link_id: int,
    cookie_key: str,
    existing_claim: Optional[str],
    lock_single_device: bool,
    device_cookies: Dict[str, str],
) -> Optional[str]:
    """Klaim perangkat pertama secara atomik atau verifikasi cookie perangkat yang sama."""
    if table not in ("public_form_link", "public_task_link"):
        raise ValueError("Tabel tautan tidak valid.")
    if not lock_single_device:
        return None
    presented_secret = device_cookies.get(cookie_key)
    if existing_claim is None:
        new_device_secret = secrets.token_urlsafe(24)
        now = _now()
        with conn:
            updated = conn.execute(
                f"""
                UPDATE {table}
                SET claimed_device_hash = ?, claimed_at = ?
                WHERE id = ? AND claimed_device_hash IS NULL AND revoked_at IS NULL
                """,
                (_sha256(new_device_secret), now, link_id),
            )
            if updated.rowcount != 1:
                raise DeviceClaimError("Tautan baru saja dibuka oleh perangkat lain.")
        return new_device_secret
    if not presented_secret or not secrets.compare_digest(_sha256(presented_secret), str(existing_claim)):
        raise DeviceClaimError(
            "Tautan ini sudah dikunci pada perangkat pertama. Minta admin mereset kunci jika perlu."
        )
    return None


def resolve_public_link(
    conn: sqlite3.Connection,
    *,
    raw_token: str,
    device_cookies: Dict[str, str],
) -> Dict[str, Any]:
    """Periksa token publik, klaim perangkat pertama via cookie HttpOnly, atau tolak perangkat lain."""
    token_hash = _sha256(raw_token.strip())
    row = conn.execute(
        """
        SELECT l.id AS link_id, l.form_id, l.participant_code, l.participant_role,
               l.lock_single_device, l.claimed_device_hash, l.submitted_at, l.revoked_at,
               f.title, f.description, f.form_kind, f.questions_json
        FROM public_form_link l
        JOIN survey_form f ON f.id = l.form_id
        WHERE l.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    if row is None:
        raise LookupError("Tautan kuesioner tidak ditemukan atau tidak sah.")
    if row["revoked_at"] is not None:
        raise LinkRevokedError("Tautan kuesioner ini telah dicabut oleh peneliti.")

    link_id = int(row["link_id"])
    cookie_key = device_cookie_name(link_id)
    new_device_secret = verify_or_claim_device(
        conn,
        table="public_form_link",
        link_id=link_id,
        cookie_key=cookie_key,
        existing_claim=row["claimed_device_hash"],
        lock_single_device=bool(row["lock_single_device"]),
        device_cookies=device_cookies,
    )

    return {
        "link_id": link_id,
        "cookie_name": cookie_key,
        "new_device_secret": new_device_secret,
        "already_submitted": row["submitted_at"] is not None,
        "submitted_at": row["submitted_at"],
        "participant_code": str(row["participant_code"]),
        "participant_role": str(row["participant_role"]),
        "lock_single_device": bool(row["lock_single_device"]),
        "form": {
            "id": int(row["form_id"]),
            "title": str(row["title"]),
            "description": str(row["description"]),
            "form_kind": str(row["form_kind"]),
            "questions": json.loads(row["questions_json"]),
        },
    }


def _validate_answers(questions: Sequence[Dict[str, Any]], raw_answers: Any) -> Dict[str, Any]:
    if not isinstance(raw_answers, dict):
        raise ValueError("Format jawaban tidak valid.")
    cleaned: Dict[str, Any] = {}
    for q in questions:
        qid = q["id"]
        qtype = q["type"]
        required = bool(q.get("required", False))
        val = raw_answers.get(qid)

        if qtype == "scale":
            if val is None or val == "":
                if required:
                    raise ValueError(f"Pertanyaan '{q['label']}' wajib diisi (skala 1–5).")
                cleaned[qid] = None
                continue
            if isinstance(val, bool) or not isinstance(val, int) or not 1 <= val <= 5:
                raise ValueError(f"Jawaban skala untuk '{q['label']}' harus bilangan bulat 1–5.")
            cleaned[qid] = val
        elif qtype == "choice":
            text_val = str(val or "").strip()
            if not text_val:
                if required:
                    raise ValueError(f"Pertanyaan '{q['label']}' wajib dipilih.")
                cleaned[qid] = ""
                continue
            if text_val not in q.get("options", []):
                raise ValueError(f"Pilihan untuk '{q['label']}' tidak tersedia.")
            cleaned[qid] = text_val
        else:
            text_val = str(val or "").strip()
            if required and not text_val:
                raise ValueError(f"Pertanyaan '{q['label']}' wajib diisi.")
            if len(text_val) > 2000:
                raise ValueError(f"Jawaban untuk '{q['label']}' maksimal 2000 karakter.")
            cleaned[qid] = text_val
    return cleaned


def submit_public_form(
    conn: sqlite3.Connection,
    *,
    raw_token: str,
    device_cookies: Dict[str, str],
    raw_answers: Any,
) -> Dict[str, Any]:
    """Validasi token, perangkat, dan jawaban lalu simpan respons satu kali."""
    resolved = resolve_public_link(conn, raw_token=raw_token, device_cookies=device_cookies)
    if resolved["already_submitted"]:
        raise LinkConflictError("Jawaban untuk tautan ini sudah pernah dikirim.")

    questions = resolved["form"]["questions"]
    cleaned_answers = _validate_answers(questions, raw_answers)

    sus_score: Optional[float] = None
    if resolved["form"]["form_kind"] == "sus":
        sus_score = calculate_sus_score([cleaned_answers[f"q{i}"] for i in range(1, 11)])

    now = _now()
    link_id = resolved["link_id"]
    with conn:
        updated = conn.execute(
            "UPDATE public_form_link SET submitted_at = ? WHERE id = ? AND submitted_at IS NULL AND revoked_at IS NULL",
            (now, link_id),
        )
        if updated.rowcount != 1:
            raise LinkConflictError("Jawaban untuk tautan ini sudah pernah dikirim.")
        conn.execute(
            """
            INSERT INTO survey_response (
                form_id, link_id, participant_code, participant_role, answers_json, sus_score, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved["form"]["id"],
                link_id,
                resolved["participant_code"],
                resolved["participant_role"],
                json.dumps(cleaned_answers, ensure_ascii=False),
                sus_score,
                now,
            ),
        )

    return {
        "submitted": True,
        "submitted_at": now,
        "participant_code": resolved["participant_code"],
        "sus_score": sus_score,
        "cookie_name": resolved["cookie_name"],
        "new_device_secret": resolved["new_device_secret"],
    }


def export_form_responses_csv(conn: sqlite3.Connection, form_id: int) -> str:
    detail = get_form_detail(conn, form_id)
    questions = detail["form"]["questions"]
    q_ids = [q["id"] for q in questions]
    fieldnames = ["participant_code", "role", *q_ids]
    if detail["form"]["form_kind"] == "sus":
        fieldnames.append("sus_score")
    fieldnames.append("submitted_at")

    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for resp in detail["responses"]:
        row: Dict[str, Any] = {
            "participant_code": resp["participant_code"],
            "role": resp["participant_role"],
            "submitted_at": resp["submitted_at"],
        }
        for qid in q_ids:
            row[qid] = resp["answers"].get(qid, "")
        if detail["form"]["form_kind"] == "sus":
            row["sus_score"] = resp["sus_score"]
        writer.writerow(row)
    return buf.getvalue()
