"""Pembanding LIKE yang meniru pencarian daftar arsip e-Arsip.

e-Arsip memakai pencarian bawaan DataTables: kueri dipecah per spasi, setiap
kata harus muncul sebagai potongan teks (tanpa membedakan huruf besar-kecil)
pada gabungan kolom tampil; urutan hasil `id_arsip` naik.

Penyederhanaan yang disengaja: fitur frasa berkutip DataTables tidak ditiru.
Kueri kosong tidak mengembalikan apa pun (DataTables akan menampilkan semua baris).
"""
from typing import List, Optional

from core.search.index import SearchIndex
from core.search.ranker import SearchHit

MATCH_SCORE = 1.0


class LikeBaselineSearch:
    """Pencarian substring AND, diurutkan menurut id; tidak punya peringkat kemiripan."""

    name = "like"

    def __init__(self, index: SearchIndex) -> None:
        self._index = index

    def search(
        self,
        query: str,
        top_n: Optional[int] = 10,
        opd_id: Optional[int] = None,
        year: Optional[int] = None,
        status: Optional[int] = None,
    ) -> List[SearchHit]:
        """Cari arsip yang memuat semua kata kueri.

        Args:
            query: Kueri mentah.
            top_n: Batas hasil; None untuk semua.
            opd_id, year, status: Filter opsional.

        Returns:
            Daftar SearchHit berurut id naik. Skor tetap `MATCH_SCORE`
            karena LIKE hanya menyatakan cocok atau tidak.
        """
        terms = query.lower().split()
        if not terms:
            return []
        hits = [
            SearchHit(document.id, MATCH_SCORE)
            for document in self._index.filtered(opd_id, year, status)
            if all(term in document.haystack for term in terms)
        ]
        hits.sort(key=lambda hit: hit.id)
        return hits if top_n is None else hits[:top_n]
