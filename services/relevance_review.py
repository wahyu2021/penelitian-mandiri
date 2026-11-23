"""Penugasan, keputusan per penilai, dan riwayat untuk penilaian buta."""

import json
import random
from datetime import datetime, timezone

from services.relevance_csv import export_rows, legacy_answer, read_legacy, read_sample
from services.testset_versions import get_version, list_versions

EMPTY = (None, False, "")


class ReviewConflict(ValueError):
    """Status penilaian berubah atau operasi tidak lagi dapat dilakukan."""


class ReviewForbidden(PermissionError):
    """Akun belum ditugaskan untuk penilaian ini."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _log(conn, actor, action, detail, now):
    conn.execute(
        "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (actor, action, json.dumps(detail), now),
    )


def _prepare_sample(conn, version, content):
    locked, payload = get_version(conn, version)
    if locked["locked_at"] is None:
        raise ReviewConflict("Kunci versi set uji sebelum menyiapkan sampel.")
    queries = {query["query_id"]: query for query in payload["queries"]}
    archives = {
        row["id"]: row for row in conn.execute("SELECT id, summary_raw, summary_clean FROM archive")
    }
    base_texts = {}
    pairs = {}
    aliases = []
    for order, ((query_id, archive_id), row) in enumerate(read_sample(content).items(), 1):
        query = queries.get(query_id)
        if not query or row["query_text"] != query["query_text"] or row["query_type"] != query["query_type"]:
            raise ValueError(f"Kueri pada baris sampel {order} tidak cocok dengan set uji.")
        if query["judgments"] and archive_id not in {item["archive_id"] for item in query["judgments"]}:
            raise ValueError(f"Pasangan pada baris sampel {order} berada di luar pool set uji.")
        archive = archives.get(archive_id)
        raw = archive["summary_raw"] if archive else None
        text = row["base_query_text"].strip()
        if not text or not raw or not raw.strip() or row["summary_raw"] != raw:
            raise ValueError(f"Kueri dasar atau ringkasan asli pada baris sampel {order} tidak cocok.")
        base_id = query["base_query_id"].casefold()
        if base_texts.setdefault(base_id, text) != text:
            raise ValueError("Varian dari kueri dasar yang sama memiliki teks dasar berbeda.")
        pair = (base_id, archive_id)
        pairs[pair] = (base_id, text, query["query_type"], archive_id, raw, archive["summary_clean"])
        aliases.append((query_id, archive_id, pair, order))
    return pairs, aliases


def create_review(conn, version, first, second, content, actor):
    now = _now()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM relevance_review WHERE version = ?", (version,)).fetchone():
            raise ReviewConflict("Versi ini sudah memiliki tugas penilaian.")
        accounts = {
            row["id"]: row["role"]
            for row in conn.execute(
                "SELECT id, role FROM user WHERE is_active = 1 AND id IN (?, ?)", (first, second)
            )
        }
        if first == second or first not in accounts or accounts.get(second) != "petugas":
            raise ValueError("Pilih dua akun aktif berbeda. Penilai kedua harus berperan Petugas.")
        pairs, aliases = _prepare_sample(conn, version, content)
        conn.execute("INSERT INTO relevance_review VALUES (?, ?, ?)", (version, actor, now))
        conn.executemany(
            "INSERT INTO relevance_reviewer(version, slot, user_id) VALUES (?, ?, ?)",
            [(version, 1, first), (version, 2, second)],
        )
        order = list(pairs)
        random.SystemRandom().shuffle(order)
        ids = {}
        for pair in order:
            cursor = conn.execute(
                """INSERT INTO relevance_pair
                   (version, base_query_id, base_query_text, query_type, archive_id, summary_raw, summary_clean)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (version, *pairs[pair]),
            )
            ids[pair] = cursor.lastrowid
        conn.executemany(
            """INSERT INTO relevance_sample_row(version, query_id, archive_id, pair_id, sample_order)
               VALUES (?, ?, ?, ?, ?)""",
            [(version, query, archive, ids[pair], index) for query, archive, pair, index in aliases],
        )
        _log(conn, actor, "relevance_review_created", {"version": version, "reviewers": [first, second]}, now)
    return {"version": version, "pairs": len(pairs), "sample_rows": len(aliases)}


def _counts(conn, version, slot):
    row = conn.execute(
        """SELECT COUNT(*) AS total, COUNT(j.is_relevant) AS rated
           FROM relevance_pair p LEFT JOIN relevance_judgment j
           ON j.version = p.version AND j.pair_id = p.id AND j.slot = ?
           WHERE p.version = ?""", (slot, version),
    ).fetchone()
    return dict(row)


def admin_overview(conn):
    reviews = {}
    for row in conn.execute(
        """SELECT r.version, r.slot, r.user_id, r.submitted_at, u.username,
                  (SELECT COUNT(*) FROM relevance_sample_row s WHERE s.version = r.version) AS sample_rows
           FROM relevance_reviewer r JOIN user u ON u.id = r.user_id
           ORDER BY r.version, r.slot"""
    ):
        item = reviews.setdefault(row["version"], {
            "version": row["version"], "sample_rows": row["sample_rows"], "reviewers": [],
        })
        reviewer = {key: row[key] for key in ("slot", "user_id", "submitted_at", "username")}
        item["reviewers"].append({**reviewer, **_counts(conn, row["version"], row["slot"])})
    return {
        "accounts": [dict(row) for row in conn.execute(
            "SELECT id, username, role FROM user WHERE is_active = 1 ORDER BY username"
        )],
        "available_versions": [row["version"] for row in list_versions(conn)
                               if row["locked_at"] and row["version"] not in reviews],
        "reviews": list(reviews.values()),
    }


def assigned_reviews(conn, user_id):
    return [dict(row) for row in conn.execute(
        "SELECT version FROM relevance_reviewer WHERE user_id = ? ORDER BY version", (user_id,)
    )]


def _assignment(conn, version, user_id):
    row = conn.execute(
        "SELECT slot, submitted_at FROM relevance_reviewer WHERE version = ? AND user_id = ?",
        (version, user_id),
    ).fetchone()
    if not row:
        raise ReviewForbidden("Akun ini belum ditugaskan pada versi tersebut.")
    return row


def reviewer_item(conn, version, user_id, index=None):
    with conn:
        conn.execute("BEGIN")
        reviewer = _assignment(conn, version, user_id)
        rows = conn.execute(
            """SELECT p.id, p.base_query_text, p.query_type, p.summary_raw,
                      j.is_relevant, COALESCE(j.ragu, 0) AS ragu,
                      COALESCE(j.notes, '') AS notes, COALESCE(j.revision, 0) AS revision
               FROM relevance_pair p LEFT JOIN relevance_judgment j
               ON j.version = p.version AND j.pair_id = p.id AND j.slot = ?
               WHERE p.version = ? ORDER BY p.id""",
            (reviewer["slot"], version),
        ).fetchall()
        if index is None:
            index = next((i for i, row in enumerate(rows) if row["is_relevant"] is None), 0)
        if not 0 <= index < len(rows):
            raise LookupError("Nomor pasangan tidak ditemukan.")
        item = dict(rows[index])
        item["ragu"] = bool(item["ragu"])
        return {
            "index": index, "total": len(rows), "rated": sum(row["is_relevant"] is not None for row in rows),
            "submitted_at": reviewer["submitted_at"], "item": item,
        }


def _answer(conn, pair_id, slot):
    row = conn.execute(
        "SELECT is_relevant, ragu, notes, revision FROM relevance_judgment WHERE pair_id = ? AND slot = ?",
        (pair_id, slot),
    ).fetchone()
    if row is None:
        return EMPTY, 0
    return (row["is_relevant"], bool(row["ragu"]), row["notes"]), row["revision"]


def _write_answer(conn, version, pair, slot, current, previous, revision, actor, source, now):
    conn.execute(
        """INSERT INTO relevance_judgment(version, pair_id, slot, is_relevant, ragu, notes, revision, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (pair_id, slot) DO UPDATE SET
             is_relevant = excluded.is_relevant, ragu = excluded.ragu, notes = excluded.notes,
             revision = excluded.revision, updated_at = excluded.updated_at""",
        (version, pair, slot, *current, revision + 1, now),
    )
    conn.execute(
        """INSERT INTO relevance_judgment_change
           (pair_id, slot, actor_id, source, previous_json, current_json, changed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (pair, slot, actor, source, json.dumps(previous), json.dumps(current), now),
    )


def save_answer(conn, version, pair, user_id, expected_revision, current):
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        reviewer = _assignment(conn, version, user_id)
        if reviewer["submitted_at"]:
            raise ReviewConflict("Penilaian sudah diserahkan.")
        if not conn.execute("SELECT 1 FROM relevance_pair WHERE id = ? AND version = ?", (pair, version)).fetchone():
            raise LookupError("Pasangan tidak ditemukan.")
        previous, revision = _answer(conn, pair, reviewer["slot"])
        if revision != expected_revision:
            raise ReviewConflict("Isian berubah di sesi lain. Muat ulang pasangan dan periksa isian terbaru.")
        if previous != current:
            _write_answer(conn, version, pair, reviewer["slot"], current, previous, revision,
                          user_id, "web", _now())
            revision += 1
        return {"revision": revision, **_counts(conn, version, reviewer["slot"])}


def submit_review(conn, version, user_id):
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        reviewer = _assignment(conn, version, user_id)
        if reviewer["submitted_at"]:
            return {"submitted_at": reviewer["submitted_at"]}
        counts = _counts(conn, version, reviewer["slot"])
        if counts["rated"] != counts["total"]:
            raise ReviewConflict("Nilai semua pasangan sebelum menyerahkan jawaban.")
        now = _now()
        conn.execute(
            "UPDATE relevance_reviewer SET submitted_at = ? WHERE version = ? AND slot = ?",
            (now, version, reviewer["slot"]),
        )
        _log(conn, user_id, "relevance_review_submitted", {"version": version, "slot": reviewer["slot"]}, now)
        return {"submitted_at": now}


def _sample_aliases(conn, version):
    return conn.execute(
        """SELECT s.*, p.base_query_id, p.base_query_text, p.query_type, p.summary_raw, p.summary_clean
           FROM relevance_sample_row s JOIN relevance_pair p ON p.id = s.pair_id
           WHERE s.version = ? ORDER BY s.sample_order""", (version,),
    ).fetchall()


def migrate_legacy(conn, version, slot, content, actor):
    rows = read_legacy(content, slot)
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        reviewer = conn.execute(
            "SELECT submitted_at FROM relevance_reviewer WHERE version = ? AND slot = ?", (version, slot)
        ).fetchone()
        if not reviewer:
            raise LookupError("Penugasan tidak ditemukan.")
        if reviewer["submitted_at"]:
            raise ReviewConflict("Jawaban penilai sudah diserahkan.")
        _, payload = get_version(conn, version)
        queries = {query["query_id"]: query for query in payload["queries"]}
        answers = {}
        matched = 0
        for sample in _sample_aliases(conn, version):
            row = rows.get((sample["query_id"], sample["archive_id"]))
            if row is None:
                continue
            matched += 1
            query = queries[sample["query_id"]]
            if (row["query_text"] != query["query_text"] or row["query_type"] != sample["query_type"]
                    or (row.get("summary_raw") and row["summary_raw"] != sample["summary_raw"])
                    or (row.get("summary_clean") and sample["summary_clean"]
                        and row["summary_clean"] != sample["summary_clean"])
                    or (row.get("base_query_text") and row["base_query_text"].strip() != sample["base_query_text"])):
                raise ValueError("Isi CSV lama tidak cocok dengan sampel untuk pasangan yang sama.")
            answer = legacy_answer(row, slot)
            if answer == EMPTY:
                continue
            pair = sample["pair_id"]
            if answers.setdefault(pair, answer) != answer:
                raise ValueError("Varian pada CSV lama memiliki jawaban berbeda untuk pasangan yang sama.")
        if not matched:
            raise ValueError("CSV lama tidak memuat pasangan dari sampel ini.")
        inserted = preserved = 0
        now = _now()
        for pair, current in answers.items():
            previous, revision = _answer(conn, pair, slot)
            if revision:
                preserved += 1
            else:
                _write_answer(conn, version, pair, slot, current, previous, revision, actor, "legacy", now)
                inserted += 1
        result = {"inserted": inserted, "preserved": preserved, "matched_rows": matched,
                  "outside_rows": len(rows) - matched}
        _log(conn, actor, "relevance_legacy_imported", {"version": version, "slot": slot, **result}, now)
        return result


def export_review(conn, version, slot):
    reviewers = conn.execute(
        "SELECT submitted_at FROM relevance_reviewer WHERE version = ?", (version,)
    ).fetchall()
    if not reviewers:
        raise LookupError("Penugasan tidak ditemukan.")
    if len(reviewers) != 2 or any(not row["submitted_at"] for row in reviewers):
        raise ReviewConflict("CSV tersedia setelah kedua penilai menyerahkan jawaban.")
    _, payload = get_version(conn, version)
    queries = {query["query_id"]: query for query in payload["queries"]}
    rows = []
    for sample in _sample_aliases(conn, version):
        query = queries[sample["query_id"]]
        (decision, doubt, notes), _ = _answer(conn, sample["pair_id"], slot)
        rows.append({
            "sample_id": sample["sample_order"], "query_id": query["query_id"],
            "base_query_id": query["base_query_id"], "base_query_text": sample["base_query_text"],
            "query_text": query["query_text"], "query_type": query["query_type"],
            "source": query["source"], "noise_type": query["noise_type"],
            "archive_id": sample["archive_id"], "summary_raw": sample["summary_raw"],
            "is_relevant": decision, "ragu": int(doubt),
            "auditor_notes": notes if slot == 1 else "",
            "archivist_notes": notes if slot == 2 else "",
            "reviewer_slot": slot,
        })
    return export_rows(rows)
