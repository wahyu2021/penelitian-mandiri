"""Validasi struktur set uji dan sidik jari yang kompatibel dengan CLI."""

import json
import re
from collections import Counter

from core.normalization import normalize_code, normalize_text
from core.testset.splitting import compute_content_sha256, find_connected_query_clusters

VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
QUERY_FIELDS = ("query_id", "base_query_id", "query_type", "source", "noise_type", "split")
SOURCES = {"sintetis", "arsiparis"}
SPLITS = {"tuning", "test"}


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _positive_int(value):
    return type(value) is int and value > 0


def verify_split(queries, archive_metadata):
    groups = {}
    for query in queries:
        archive = archive_metadata.get(query.get("origin_archive_id"), {})
        numbers = {
            normalize_code(value)
            for value in (query.get("spm_number"), archive.get("spm_number"))
            if value
        }
        parties = {
            normalize_text(value)
            for value in (query.get("party_name"), archive.get("party_normalized"))
            if value
        }
        duplicate = (query.get("duplicate_group_id") or "").casefold()
        for kind, values in (("SPM", numbers), ("pihak", parties), ("duplikat", {duplicate})):
            for value in filter(None, values):
                previous = groups.setdefault((kind, value), query["split"])
                if previous != query["split"]:
                    raise ValueError(f"Split bertabrakan pada kelompok {kind}.")

    for cluster in find_connected_query_clusters(queries):
        if len({query["split"] for query in cluster}) > 1:
            raise ValueError("Kueri dasar, arsip asal, atau SPM yang sama melintasi split.")


def summarize_queries(queries):
    splits = Counter(query["split"] for query in queries)
    base_by_split = {
        split: len({query["base_query_id"].casefold() for query in queries if query["split"] == split})
        for split in SPLITS
    }
    return {
        "n_queries": len(queries),
        "n_tuning": splits["tuning"],
        "n_test": splits["test"],
        "n_base_queries": sum(base_by_split.values()),
        "n_tuning_base_queries": base_by_split["tuning"],
        "n_test_base_queries": base_by_split["test"],
    }


def validate_testset(payload, archive_metadata):
    if not isinstance(payload, dict) or not isinstance(payload.get("version"), str):
        raise ValueError("JSON set uji wajib memiliki versi.")
    if not VERSION_PATTERN.fullmatch(payload["version"]):
        raise ValueError("Versi harus memakai huruf, angka, titik, garis bawah, atau tanda hubung.")
    queries = payload.get("queries")
    if not isinstance(queries, list) or not 1 <= len(queries) <= 2000:
        raise ValueError("Set uji harus memuat 1 sampai 2.000 kueri.")
    seen = set()
    bases = {}
    for query in queries:
        if not isinstance(query, dict) or not all(_text(query.get(key)) for key in QUERY_FIELDS):
            raise ValueError("Identitas, teks, jenis, asal, gangguan, dan split kueri wajib diisi.")
        text = query.get("query_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Teks kueri wajib diisi.")
        key = query["query_id"].casefold()
        if key in seen:
            raise ValueError("ID kueri berulang.")
        seen.add(key)
        if query["source"] not in SOURCES or query["split"] not in SPLITS:
            raise ValueError("Asal kueri atau split tidak dikenal.")
        origin = query.get("origin_archive_id")
        if (origin is not None or query["source"] == "sintetis") and not _positive_int(origin):
            raise ValueError("Kueri sintetis membutuhkan ID arsip asal yang valid.")
        if any(
            query.get(field) is not None and not _text(query[field])
            for field in ("spm_number", "party_name", "duplicate_group_id")
        ):
            raise ValueError("Metadata kelompok kueri tidak valid.")
        judgments = query.get("judgments")
        if not isinstance(judgments, list):
            raise ValueError("Penilaian kueri harus berupa daftar.")
        labels = {}
        for item in judgments:
            if not isinstance(item, dict) or not _positive_int(item.get("archive_id")):
                raise ValueError("ID arsip pada penilaian tidak valid.")
            archive_id = item["archive_id"]
            if archive_id in labels or any(
                type(value) is not int or value not in (0, 1)
                for value in (item.get("is_relevant"), item.get("ragu", 0))
            ):
                raise ValueError("Label penilaian tidak valid atau arsip dinilai dua kali.")
            labels[archive_id] = (item["is_relevant"], item.get("ragu", 0))
        base = query["base_query_id"].casefold()
        reference = (query["source"], query["query_type"], origin, labels)
        if bases.setdefault(base, reference) != reference:
            raise ValueError("Varian satu kueri dasar harus berbagi asal, jenis, dan penilaian.")
    verify_split(queries, archive_metadata)
    counts = summarize_queries(queries)
    if any(key in payload and (type(payload[key]) is not int or payload[key] != value)
           for key, value in counts.items()):
        raise ValueError("Jumlah kueri pada metadata tidak cocok dengan isi set uji.")
    unsigned = {key: value for key, value in payload.items() if key != "content_sha256"}
    try:
        canonical = json.dumps(unsigned, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        digest = compute_content_sha256(canonical)
    except (ValueError, RecursionError) as error:
        raise ValueError("Set uji berisi nilai JSON yang tidak didukung.") from error
    if "content_sha256" in payload and payload["content_sha256"] != digest:
        raise ValueError("SHA-256 set uji tidak cocok dengan isi JSON.")
    return {**unsigned, "content_sha256": digest}
