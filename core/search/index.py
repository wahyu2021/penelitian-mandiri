"""Dokumen pencarian dan indeks di memori."""
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Mapping, Optional, Tuple

from core.normalization import tokenize

DOCUMENT_DOWNLOAD_LABEL = "download"
DOCUMENT_MISSING_LABEL = "belum ada file"


@dataclass(frozen=True)
class SearchDocument:
    """Satu arsip siap cari.

    Attributes:
        id: `id_arsip`.
        opd_id, year, status: untuk penyaringan (None bila tidak valid).
        summary_tokens, spm_tokens, party_tokens: token ternormalisasi per field.
        haystack: teks gabungan kolom tampilan e-Arsip (huruf kecil) untuk LIKE.
    """

    id: int
    opd_id: Optional[int]
    year: Optional[int]
    status: Optional[int]
    summary_tokens: Tuple[str, ...]
    spm_tokens: Tuple[str, ...]
    party_tokens: Tuple[str, ...]
    haystack: str


def spm_search_tokens(spm_number: Optional[str]) -> Tuple[str, ...]:
    """Token field SPM: kode utuh ditambah tiap bagiannya.

    Bagian dipisah agar kueri sebagian (mis. `158`) tetap bisa cocok.
    """
    if not spm_number:
        return ()
    tokens: List[str] = []
    for token in tokenize(spm_number, expand_abbreviations=False):
        for candidate in [token, *token.split("/")]:
            if candidate and candidate not in tokens:
                tokens.append(candidate)
    return tuple(tokens)


def build_haystack(record: Mapping[str, object]) -> str:
    """Gabungkan kolom yang tampil pada daftar arsip e-Arsip menjadi satu teks.

    Kolom: OPD, nomor berkas, klasifikasi, index, kurun waktu, ringkasan,
    lokasi (blok/rak/baris/no box), dan teks kolom dokumen. Nomor urut baris
    tabel tidak disertakan.
    """
    location = "/".join(str(record.get(key) or "") for key in (
        "location_block", "location_rack", "location_row", "box_number"))
    document_label = DOCUMENT_DOWNLOAD_LABEL if record.get("has_document") else DOCUMENT_MISSING_LABEL
    year = record.get("year")
    parts = [
        record.get("opd_name"), record.get("file_number"), record.get("classification_label"),
        record.get("index_label"), "" if year is None else str(year),
        record.get("summary_clean"), location, document_label,
    ]
    return " ".join(str(part or "") for part in parts).lower()


def build_document(record: Mapping[str, object]) -> SearchDocument:
    """Bangun SearchDocument dari record bersih + metadata hasil ekstraksi.

    Kunci wajib: id, opd_id, year, status, summary_clean, spm_number, party_name.
    Kunci opsional untuk haystack: opd_name, classification_label, file_number,
    index_label, location_*, box_number, has_document.
    """
    return SearchDocument(
        id=int(record["id"]),
        opd_id=record.get("opd_id"),
        year=record.get("year"),
        status=record.get("status"),
        summary_tokens=tuple(tokenize(str(record.get("summary_clean") or ""))),
        spm_tokens=spm_search_tokens(record.get("spm_number")),
        party_tokens=tuple(tokenize(str(record.get("party_name") or ""))),
        haystack=build_haystack(record),
    )


def matches_filters(
    document: SearchDocument,
    opd_id: Optional[int] = None,
    year: Optional[int] = None,
    status: Optional[int] = None,
) -> bool:
    """True bila dokumen lolos seluruh filter yang diisi."""
    return (
        (opd_id is None or document.opd_id == opd_id)
        and (year is None or document.year == year)
        and (status is None or document.status == status)
    )


class SearchIndex:
    """Kumpulan SearchDocument di memori."""

    def __init__(self, documents: Iterable[SearchDocument]) -> None:
        self.documents: List[SearchDocument] = list(documents)

    @classmethod
    def from_records(cls, records: Iterable[Mapping[str, object]]) -> "SearchIndex":
        """Bangun indeks dari record (lihat `build_document`)."""
        return cls(build_document(record) for record in records)

    def __len__(self) -> int:
        return len(self.documents)

    def filtered(
        self,
        opd_id: Optional[int] = None,
        year: Optional[int] = None,
        status: Optional[int] = None,
    ) -> Iterator[SearchDocument]:
        """Iterasi dokumen yang lolos filter."""
        return (d for d in self.documents if matches_filters(d, opd_id, year, status))
