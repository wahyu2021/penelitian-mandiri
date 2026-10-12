"""Modul blind pooling untuk menggabungkan hasil temu kembali multi-metode."""
import random
from typing import Dict, List, Optional, Set

from core.search.index import SearchIndex
from core.search.like_baseline import LikeBaselineSearch
from core.search.matchers.base import BaseMatcher
from core.search.ranker import FieldRanker

DEFAULT_POOL_DEPTH = 10


def build_query_pool(
    query_text: str,
    index: SearchIndex,
    matchers: Dict[str, BaseMatcher],
    like_search: LikeBaselineSearch,
    origin_archive_id: Optional[int] = None,
    pool_depth: int = DEFAULT_POOL_DEPTH,
    seed: Optional[int] = None,
) -> List[int]:
    """Bangun kumpulan dokumen kandidat (blind pool) untuk satu kueri.

    Menggabungkan Top-N hasil dari baseline LIKE dan 4 pencocok fuzzy,
    menambahkan arsip asal (jika ada), dan mengacak urutan dokumen.

    Args:
        query_text: Teks kueri pencarian.
        index: SearchIndex korpus dokumen.
        matchers: Kamus nama metode -> instance BaseMatcher.
        like_search: Instance LikeBaselineSearch.
        origin_archive_id: ID arsip asal kueri sintetis (wajib masuk pool).
        pool_depth: Batas peringkat teratas yang diambil per metode (default 10).
        seed: Random seed untuk pengacakan urutan pool.

    Returns:
        Daftar ID arsip unik yang telah diacak tanpa nama metode atau skor.
    """
    candidate_ids: Set[int] = set()

    # 1. Hasil pencarian LIKE (maksimal pool_depth dokumen urut ID)
    like_hits = like_search.search(query_text, top_n=pool_depth)
    for hit in like_hits:
        candidate_ids.add(hit.id)

    # 2. Hasil pencarian masing-masing metode fuzzy berbobot sama rata
    for _, matcher in matchers.items():
        ranker = FieldRanker(index, matcher)
        hits = ranker.search(query_text, top_n=pool_depth)
        for hit in hits:
            candidate_ids.add(hit.id)

    # 3. Arsip asal kueri sintetis wajib disertakan dalam pool
    if origin_archive_id is not None:
        candidate_ids.add(origin_archive_id)

    pool_list = list(candidate_ids)
    rng = random.Random(seed) if seed is not None else random.Random()
    rng.shuffle(pool_list)

    return pool_list
