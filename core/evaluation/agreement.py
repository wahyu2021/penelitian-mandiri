"""Persentase kesepakatan antar penilai relevansi (peneliti vs arsiparis) dan Cohen's kappa."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Hashable, Iterable, Mapping, Optional, Sequence, Tuple, Union


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


def _normalize_binary(value: Union[bool, int, str]) -> int:
    """Validasi dan konversi nilai relevansi biner ke 0 atau 1."""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int) and value in (0, 1):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned in ("0", "1"):
            return int(cleaned)
    raise ValueError("Nilai relevansi biner harus 0 atau 1.")


def _imbalance_limitation(counts: Iterable[int], total_ratings: int) -> Optional[str]:
    """Kembalikan catatan keterbatasan jika distribusi kelas sangat tidak seimbang (>= 80%)."""
    if total_ratings <= 0:
        return None
    max_count = max(counts, default=0)
    dominant_share = max_count / total_ratings
    if dominant_share >= 0.80:
        pct = dominant_share * 100.0
        return (
            f"Distribusi kelas tidak seimbang (kelas dominan {pct:.1f}% dari seluruh penilaian); "
            "pada prevalensi tinggi, Cohen's kappa dapat bernilai rendah meski kesepakatan mentah tinggi."
        )
    return None


def binary_agreement_summary(
    pairs: Sequence[Tuple[Union[bool, int, str], Union[bool, int, str]]],
    *,
    n_expected: Optional[int] = None,
    query_types: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Hitung ringkasan kesepakatan biner (matriks 2x2, kelas relevan, dan Cohen's kappa).

    Jika sampel belum lengkap (`n_expected == 0`, `n_paired == 0`, atau `n_paired < n_expected`),
    status dikembalikan sebagai `pending` tanpa menerbitkan angka metrik akhir.
    """
    if n_expected is not None and n_expected < 0:
        raise ValueError("n_expected tidak boleh negatif.")
    if query_types is not None and len(query_types) != len(pairs):
        raise ValueError("Panjang query_types harus sama dengan jumlah pasangan.")

    normalized_pairs = [(_normalize_binary(first), _normalize_binary(second)) for first, second in pairs]
    n_paired = len(normalized_pairs)
    n_total = n_expected if n_expected is not None else n_paired

    if n_total == 0 or n_paired == 0 or n_paired < n_total:
        if n_total == 0:
            reason = "Belum ada pasangan sampel yang tersedia untuk dihitung."
        elif n_paired == 0:
            reason = f"Belum ada pasangan yang dinilai kedua pihak (0 dari {n_total} sampel)."
        else:
            reason = (
                f"Sampel belum lengkap: baru {n_paired} dari {n_total} pasangan dinilai kedua pihak; "
                "metrik kesepakatan ditunda."
            )
        return {
            "status": "pending",
            "n_total": n_total,
            "n_paired": n_paired,
            "n_agreed": None,
            "percentage_agreement": None,
            "relevant_class_agreement": None,
            "cohen_kappa": None,
            "confusion_matrix": None,
            "agreement_by_query_type": {},
            "limitations": [reason],
        }

    both_relevant = sum(1 for a, b in normalized_pairs if a == 1 and b == 1)
    rater1_only = sum(1 for a, b in normalized_pairs if a == 1 and b == 0)
    rater2_only = sum(1 for a, b in normalized_pairs if a == 0 and b == 1)
    both_irrelevant = n_paired - both_relevant - rater1_only - rater2_only
    n_agreed = both_relevant + both_irrelevant
    pct_agreement = n_agreed / n_paired

    positive_denom = 2 * both_relevant + rater1_only + rater2_only
    relevant_class_agreement = (2 * both_relevant / positive_denom) if positive_denom > 0 else None

    expected_agreement = (
        (both_relevant + rater1_only) * (both_relevant + rater2_only)
        + (both_irrelevant + rater2_only) * (both_irrelevant + rater1_only)
    ) / (n_paired * n_paired)
    cohen_kappa = (
        (pct_agreement - expected_agreement) / (1.0 - expected_agreement)
        if expected_agreement < 1.0
        else None
    )

    limitations = ["Dihitung dari penilaian biner 0/1 pada pasangan yang dinilai kedua pihak."]
    if cohen_kappa is None:
        status = "complete_kappa_undefined"
        limitations.append(
            "Cohen's kappa tidak terdefinisi karena kedua penilai hanya memakai satu kelas "
            "(kesepakatan peluang expected_agreement = 1,0)."
        )
    else:
        status = "complete"
        ones_total = 2 * both_relevant + rater1_only + rater2_only
        zeros_total = 2 * both_irrelevant + rater1_only + rater2_only
        imbalance_note = _imbalance_limitation((ones_total, zeros_total), 2 * n_paired)
        if imbalance_note:
            limitations.append(imbalance_note)

    if relevant_class_agreement is None:
        limitations.append(
            "Kesepakatan kelas relevan tidak terdefinisi karena tidak ada butir yang dinilai relevan oleh salah satu pihak."
        )

    agreement_by_type: Dict[str, Dict[str, Any]] = {}
    if query_types is not None:
        grouped: Dict[str, list[Tuple[int, int]]] = defaultdict(list)
        for q_type, pair in zip(query_types, normalized_pairs):
            grouped[q_type].append(pair)
        for q_type, items in grouped.items():
            agreed_type = sum(1 for a, b in items if a == b)
            agreement_by_type[q_type] = {
                "n_samples": len(items),
                "n_agreed": agreed_type,
                "agreement": agreed_type / len(items),
            }

    return {
        "status": status,
        "n_total": n_total,
        "n_paired": n_paired,
        "n_agreed": n_agreed,
        "percentage_agreement": pct_agreement,
        "relevant_class_agreement": relevant_class_agreement,
        "cohen_kappa": cohen_kappa,
        "confusion_matrix": {
            "both_relevant": both_relevant,
            "rater1_only_relevant": rater1_only,
            "rater2_only_relevant": rater2_only,
            "both_irrelevant": both_irrelevant,
        },
        "agreement_by_query_type": agreement_by_type,
        "limitations": limitations,
    }


def categorical_agreement_summary(
    pairs: Sequence[Tuple[str, str]],
    *,
    labels: Sequence[str],
    n_expected: Optional[int] = None,
) -> Dict[str, Any]:
    """Hitung ringkasan kesepakatan multi-kelas (percentage agreement dan Cohen's kappa)."""
    if n_expected is not None and n_expected < 0:
        raise ValueError("n_expected tidak boleh negatif.")
    normalized_labels = tuple(label.strip().lower() for label in labels if label.strip())
    if not normalized_labels:
        raise ValueError("Daftar label kategori tidak boleh kosong.")
    allowed = set(normalized_labels)

    normalized_pairs = []
    for first, second in pairs:
        v1 = (first or "").strip().lower()
        v2 = (second or "").strip().lower()
        if v1 not in allowed or v2 not in allowed:
            raise ValueError(f"Nilai kategori tidak sah: {first!r}, {second!r}.")
        normalized_pairs.append((v1, v2))

    n_paired = len(normalized_pairs)
    n_total = n_expected if n_expected is not None else n_paired

    if n_total == 0 or n_paired == 0 or n_paired < n_total:
        if n_total == 0:
            reason = "Belum ada butir yang dapat dibandingkan."
        elif n_paired == 0:
            reason = f"Belum ada butir yang dinilai kedua penilai (0 dari {n_total})."
        else:
            reason = (
                f"Penilaian belum lengkap: baru {n_paired} dari {n_total} butir dinilai kedua penilai; "
                "status kesepakatan tetap tertunda."
            )
        return {
            "status": "pending",
            "n_total": n_total,
            "n_paired": n_paired,
            "n_agreed": None,
            "percentage_agreement": None,
            "cohen_kappa": None,
            "limitations": [reason],
        }

    n_agreed = sum(1 for a, b in normalized_pairs if a == b)
    pct_agreement = n_agreed / n_paired

    count1 = Counter(a for a, _ in normalized_pairs)
    count2 = Counter(b for _, b in normalized_pairs)
    expected_agreement = sum(count1[label] * count2[label] for label in normalized_labels) / (
        n_paired * n_paired
    )
    cohen_kappa = (
        (pct_agreement - expected_agreement) / (1.0 - expected_agreement)
        if expected_agreement < 1.0
        else None
    )

    limitations = ["Dihitung dari kecocokan kategori identik kedua penilai pada butir yang sama."]
    if cohen_kappa is None:
        status = "complete_kappa_undefined"
        limitations.append(
            "Cohen's kappa tidak terdefinisi karena kedua penilai hanya memakai satu kategori "
            "(expected_agreement = 1,0)."
        )
    else:
        status = "complete"
        combined = count1 + count2
        imbalance_note = _imbalance_limitation(combined.values(), 2 * n_paired)
        if imbalance_note:
            limitations.append(imbalance_note)

    return {
        "status": status,
        "n_total": n_total,
        "n_paired": n_paired,
        "n_agreed": n_agreed,
        "percentage_agreement": pct_agreement,
        "cohen_kappa": cohen_kappa,
        "limitations": limitations,
    }
