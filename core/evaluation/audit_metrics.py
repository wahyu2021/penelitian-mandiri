"""Kalkulasi akurasi audit ekstraksi, interval Wilson, dan persentase kesepakatan."""
import math
from typing import Dict, List, Optional, Tuple, Union

Z_95 = 1.959963984540054  # z-score untuk interval kepercayaan 95%


def wilson_score_interval(
    successes: int,
    total: int,
    z: float = Z_95,
) -> Tuple[float, float, float]:
    """Hitung interval kepercayaan Wilson score untuk proporsi binomial.

    Args:
        successes: Jumlah kejadian sukses / benar (k).
        total: Total observasi (n).
        z: Nilai z-score (default 1.96 untuk 95% confidence).

    Returns:
        Tuple (estimasi_titik, batas_bawah, batas_atas).

    Raises:
        ValueError: Nilai negatif atau successes > total.
    """
    if successes < 0 or total < 0:
        raise ValueError("Jumlah sukses dan total tidak boleh negatif.")
    if successes > total:
        raise ValueError("Jumlah sukses tidak boleh melebihi total observasi.")
    if total == 0:
        return 0.0, 0.0, 0.0

    p = successes / total
    z2 = z * z
    denom = 1.0 + (z2 / total)
    center = (p + (z2 / (2.0 * total))) / denom
    margin = (z / denom) * math.sqrt(
        (p * (1.0 - p) / total) + (z2 / (4.0 * total * total))
    )

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    if successes == total:
        upper = 1.0
    if successes == 0:
        lower = 0.0
    return p, lower, upper


def calculate_field_audit_metrics(
    verdicts: List[str],
    missed_flags: Optional[List[bool]] = None,
) -> Dict[str, Union[int, float, Tuple[float, float, float]]]:
    """Hitung metrik akurasi satu field dari daftar penilaian audit.

    Nilai verdict yang sah:
    - 'benar': Ekstraksi ada dan tepat.
    - 'salah': Ekstraksi ada tetapi keliru.
    - 'tidak_ada_di_teks': Ekstraksi kosong dan teks memang tidak memuat field ini.

    Args:
        verdicts: Daftar status penilaian per baris audit.
        missed_flags: Daftar boolean apakah ada nilai di teks yang terlewat diekstrak.

    Returns:
        Kamus berisi jumlah benar, salah, tidak ada, missed, serta akurasi dan interval Wilson.
    """
    n_total = len(verdicts)
    if n_total == 0:
        raise ValueError("Daftar penilaian audit tidak boleh kosong.")

    if missed_flags is None:
        missed_flags = [False] * n_total

    n_benar = 0
    n_salah = 0
    n_tidak_ada = 0
    n_missed = 0

    for v, missed in zip(verdicts, missed_flags):
        v_clean = (v or "").strip().lower()
        if missed:
            n_missed += 1

        if v_clean == "benar":
            n_benar += 1
        elif v_clean == "salah":
            n_salah += 1
        elif v_clean in {"tidak_ada_di_teks", "tidak_ada", "none"}:
            n_tidak_ada += 1
        else:
            raise ValueError(f"Verdict audit tidak dikenal: {v!r}")

    # 1. Akurasi ekstraksi positif (precision): Benar / (Benar + Salah)
    n_ekstrak = n_benar + n_salah
    if n_ekstrak > 0:
        p_pos, low_pos, up_pos = wilson_score_interval(n_benar, n_ekstrak)
    else:
        p_pos, low_pos, up_pos = 0.0, 0.0, 0.0

    # 2. Akurasi keputusan menyeluruh: (Benar + Tidak Ada Valid) / (Total + Missed)
    # Jika ada missed (false negative), baris tersebut dianggap salah keputusan
    n_sukses_total = n_benar + (n_tidak_ada if n_missed == 0 else max(0, n_tidak_ada - n_missed))
    p_all, low_all, up_all = wilson_score_interval(n_sukses_total, n_total)

    return {
        "total_evaluated": n_total,
        "n_benar": n_benar,
        "n_salah": n_salah,
        "n_tidak_ada_di_teks": n_tidak_ada,
        "n_missed": n_missed,
        "n_extracted": n_ekstrak,
        "accuracy_extracted": p_pos,
        "wilson_ci_extracted": (low_pos, up_pos),
        "accuracy_overall": p_all,
        "wilson_ci_overall": (low_all, up_all),
    }


def calculate_percentage_agreement(
    ratings_a: List[str],
    ratings_b: List[str],
) -> float:
    """Hitung persentase kesepakatan (percentage agreement) antar dua penilaian.

    Args:
        ratings_a: Daftar rating dari penilai A / sesi 1.
        ratings_b: Daftar rating dari penilai B / sesi 2.

    Returns:
        Nilai pecahan 0.0 s.d. 1.0 (proporsi kesepakatan identik).
    """
    if len(ratings_a) != len(ratings_b):
        raise ValueError("Panjang daftar penilaian harus sama.")
    if not ratings_a:
        raise ValueError("Daftar penilaian tidak boleh kosong.")

    matches = sum(
        1 for a, b in zip(ratings_a, ratings_b)
        if (a or "").strip().lower() == (b or "").strip().lower()
    )
    return matches / len(ratings_a)
