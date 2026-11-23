"""Adapter baca saja dari arsip SQLite ke mesin pencarian inti."""

import sqlite3
from functools import lru_cache
from pathlib import Path

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers import FUZZY_METHOD_NAMES, create_matcher
from core.search.ranker import FieldRanker, equal_weights

METHODS = ("like", *FUZZY_METHOD_NAMES)
DEFAULT_METHOD = "levenshtein"


def get_default_search_method(db_path: Path) -> str:
    """Baca metode pencarian bawaan dari app_setting jika tersedia dan valid."""
    connection = sqlite3.connect(str(db_path))
    try:
        row = connection.execute(
            "SELECT value FROM app_setting WHERE key = 'default_search_method'"
        ).fetchone()
    finally:
        connection.close()
    if row is not None and row[0] in METHODS:
        return str(row[0])
    return DEFAULT_METHOD


@lru_cache(maxsize=4)
def _indexed_corpus(db_path: str, modified_ns: int):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        records = [dict(row) for row in conn.execute("""
            SELECT a.id, a.opd_id, a.year, a.status, a.summary_clean,
                   a.summary_raw, a.file_number, a.index_label,
                   a.location_block, a.location_rack, a.location_row,
                   a.box_number, a.has_document, o.name AS opd_name,
                   c.name AS classification_label, m.spm_number, m.party_name
            FROM archive a
            LEFT JOIN opd o ON o.id = a.opd_id
            LEFT JOIN classification c ON c.id = a.classification_id
            LEFT JOIN archive_metadata m ON m.archive_id = a.id
            ORDER BY a.id
        """)]
    finally:
        conn.close()
    return SearchIndex.from_records(records), {row["id"]: row for row in records}


def search_archives(db_path: Path, query: str, method: str = DEFAULT_METHOD,
                    opd_id=None, year=None, status=None, limit: int | None = 20):
    """Kembalikan hasil pencarian dan metadata tampilan tanpa mengubah basis data."""
    if method not in METHODS:
        raise ValueError(f"Metode pencarian tidak dikenal: {method}")
    if not query.strip():
        return []
    path = Path(db_path).resolve()
    index, record_by_id = _indexed_corpus(str(path), path.stat().st_mtime_ns)
    searcher = (LikeBaselineSearch(index) if method == "like" else
                FieldRanker(index, create_matcher(method), equal_weights(), query_aware=True))
    hits = searcher.search(query, top_n=limit, opd_id=opd_id, year=year, status=status)
    return [{**record_by_id[hit.id], "score": hit.score} for hit in hits]


def compare_methods(db_path: Path, query: str, opd_id=None, year=None, status=None,
                    limit: int = 10):
    return {method: search_archives(db_path, query, method, opd_id, year, status, limit)
            for method in METHODS}


def list_opd_options(db_path: Path):
    """Daftar OPD dari salinan SQLite untuk formulir filter pencarian."""
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(
            "SELECT id, name FROM opd ORDER BY name, id"
        )]
    finally:
        connection.close()
