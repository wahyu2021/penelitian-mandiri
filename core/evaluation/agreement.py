"""Persentase kesepakatan antar penilai relevansi (peneliti vs arsiparis)."""
from dataclasses import dataclass
from typing import Hashable, Mapping, Tuple


@dataclass(frozen=True)
class AgreementResult:
    """Hasil perbandingan dua set penilaian.

    Attributes:
        n_compared: Jumlah butir yang dinilai kedua pihak.
        n_agreed: Jumlah butir dengan penilaian sama.
        agreement_rate: n_agreed / n_compared (0..1).
        disagreements: Kunci butir yang berbeda, untuk ditinjau.
    """

    n_compared: int
    n_agreed: int
    agreement_rate: float
    disagreements: Tuple[Hashable, ...]


def percentage_agreement(
    first: Mapping[Hashable, bool], second: Mapping[Hashable, bool]
) -> AgreementResult:
    """Bandingkan penilaian pada butir yang dinilai oleh kedua pihak.

    Args:
        first: Penilaian pihak pertama (kunci butir -> relevan atau tidak).
        second: Penilaian pihak kedua.

    Raises:
        ValueError: tidak ada butir yang dinilai bersama.
    """
    common = sorted(set(first) & set(second), key=repr)
    if not common:
        raise ValueError("Tidak ada butir yang dinilai oleh kedua pihak")
    disagreements = tuple(key for key in common if bool(first[key]) != bool(second[key]))
    agreed = len(common) - len(disagreements)
    return AgreementResult(len(common), agreed, agreed / len(common), disagreements)
