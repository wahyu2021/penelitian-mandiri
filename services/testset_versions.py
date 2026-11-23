"""Snapshot set uji di SQLite, terpisah dari artefak sumber penelitian."""

import json
from collections import Counter
from datetime import datetime, timezone

from core.testset.versioning import summarize_queries, validate_testset


class VersionConflict(ValueError):
    """Versi terkunci, sudah ada, atau berbeda dari salinan yang ditinjau."""


def _overview(row, payload):
    queries = payload["queries"]
    sources = Counter(query["source"] for query in queries)
    return {
        "version": row["version"],
        "content_sha256": row["content_sha256"],
        "updated_at": row["updated_at"],
        "locked_at": row["locked_at"],
        "locked_by": row["locked_by"],
        **summarize_queries(queries),
        "sources": {source: sources[source] for source in ("sintetis", "arsiparis")},
    }


def list_versions(conn):
    return [
        _overview(row, json.loads(row["payload_json"]))
        for row in conn.execute("SELECT * FROM testset_version ORDER BY updated_at DESC, version")
    ]


def get_version(conn, version):
    row = conn.execute("SELECT * FROM testset_version WHERE version = ?", (version,)).fetchone()
    if row is None:
        raise LookupError("Versi set uji tidak ditemukan.")
    return row, json.loads(row["payload_json"])


def version_detail(conn, version):
    row, payload = get_version(conn, version)
    return {
        **_overview(row, payload),
        "queries": [
            {key: query[key] for key in (
                "query_id", "base_query_id", "query_text", "query_type", "source", "noise_type", "split"
            )}
            for query in payload["queries"]
        ],
    }


def _archive_metadata(conn):
    return {
        row["archive_id"]: dict(row)
        for row in conn.execute("SELECT archive_id, spm_number, party_normalized FROM archive_metadata")
    }


def _check_open(row, expected_hash):
    if row["locked_at"] is not None:
        raise VersionConflict("Versi sudah terkunci. Gunakan nama versi baru untuk perubahan.")
    if row["content_sha256"] != expected_hash:
        raise VersionConflict("Isi versi telah berubah. Muat ulang dan tinjau kembali.")


def _log(conn, user_id, action, version, digest, now):
    conn.execute(
        "INSERT INTO activity_log(user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (user_id, action, json.dumps({"version": version, "content_sha256": digest}), now),
    )


def save_version(conn, raw, user_id, *, version=None, expected_hash=None):
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if version is not None:
            row, _ = get_version(conn, version)
            _check_open(row, expected_hash)
        payload = validate_testset(raw, _archive_metadata(conn))
        name, digest = payload["version"], payload["content_sha256"]
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if version is None:
            cursor = conn.execute(
                """INSERT INTO testset_version
                   (version, payload_json, content_sha256, updated_by, updated_at)
                   VALUES (?, ?, ?, ?, ?) ON CONFLICT(version) DO NOTHING""",
                (name, serialized, digest, user_id, now),
            )
            if cursor.rowcount != 1:
                raise VersionConflict("Versi sudah terdaftar. Pilih versi terbuka untuk menggantinya.")
        else:
            if name != version:
                raise ValueError("Versi pada JSON harus sama dengan versi yang dipilih.")
            conn.execute(
                """UPDATE testset_version SET payload_json = ?, content_sha256 = ?,
                   updated_by = ?, updated_at = ? WHERE version = ?""",
                (serialized, digest, user_id, now, name),
            )
        _log(conn, user_id, "testset_saved", name, digest, now)
        row, _ = get_version(conn, name)
        return _overview(row, payload)


def lock_version(conn, version, expected_hash, user_id):
    now = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        row, payload = get_version(conn, version)
        _check_open(row, expected_hash)
        validate_testset(payload, _archive_metadata(conn))
        summary = _overview(row, payload)
        if not summary["n_tuning"] or not summary["n_test"]:
            raise ValueError("Split tuning dan test harus terisi sebelum versi dikunci.")
        conn.execute(
            "UPDATE testset_version SET locked_by = ?, locked_at = ? WHERE version = ?",
            (user_id, now, version),
        )
        _log(conn, user_id, "testset_locked", version, expected_hash, now)
        return {**summary, "locked_by": user_id, "locked_at": now}
