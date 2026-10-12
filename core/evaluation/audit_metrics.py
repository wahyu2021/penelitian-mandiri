"""Kalkulasi akurasi audit ekstraksi, interval Wilson 95%, dan persentase kesepakatan."""
import math
from typing import Dict, List, Tuple, Union

Z_95 = 1.959963984540054  # z-score untuk interval kepercayaan 95%
VALID_VERDICTS = frozenset({"benar", "salah", "tidak_ada_di_teks", "terlewat"})


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
) -> Dict[str, Union[int, float, Tuple[float, float, float]]]:
    """Hitung metrik ketepatan dan keterambilan satu field dari daftar penilaian audit.

    Nilai verdict yang sah:
    - 'benar': Ekstraksi ada dan tepat sesuai teks.
    - 'salah': Ekstraksi ada tetapi keliru/terpotong/berlebih/ekstraksi palsu.
    - 'terlewat': Teks memuat data tetapi ekstraksi kosong (false negative).
    - 'tidak_ada_di_teks': Teks tidak memuat data dan ekstraksi kosong (true negative).

    Args:
        verdicts: Daftar status penilaian per baris audit (tidak boleh ada sel kosong).

    Returns:
        Kamus berisi jumlah per verdict, ketepatan (precision), keterambilan (recall),
        beserta 95% interval kepercayaan Wilson score masing-masing.

    Raises:
        ValueError: Terdapat sel kosong atau nilai di luar 4 pilihan sah.
    """
    n_total = len(verdicts)
    if n_total == 0:
        raise ValueError("Daftar penilaian audit tidak boleh kosong.")

    n_benar = 0
    n_salah = 0
    n_tidak_ada = 0
    n_terlewat = 0

    for idx, v in enumerate(verdicts, start=1):
        if v is None:
            raise ValueError(f"Baris ke-{idx} kosong (belum dinilai). Seluruh baris wajib dinilai.")
        v_clean = v.strip().lower()
        if not v_clean:
            raise ValueError(f"Baris ke-{idx} kosong (belum dinilai). Seluruh baris wajib dinilai.")

        if v_clean == "benar":
            n_benar += 1
        elif v_clean == "salah":
            n_salah += 1
        elif v_clean == "tidak_ada_di_teks":
            n_tidak_ada += 1
        elif v_clean == "terlewat":
            n_terlewat += 1
        else:
            raise ValueError(
                f"Baris ke-{idx} memiliki nilai tidak sah: {v!r}. "
                f"Pilihan nilai sah: {sorted(VALID_VERDICTS)}"
            )

    # 1. Ketepatan (Precision): Benar / (Benar + Salah)
    n_ekstrak = n_benar + n_salah
    if n_ekstrak > 0:
        p_ket, low_ket, up_ket = wilson_score_interval(n_benar, n_ekstrak)
    else:
        p_ket, low_ket, up_ket = 0.0, 0.0, 0.0

    # 2. Keterambilan (Recall): Benar / (Benar + Terlewat)
    n_ada_di_teks = n_benar + n_terlewat
    if n_ada_di_teks > 0:
        p_ret, low_ret, up_ret = wilson_score_interval(n_benar, n_ada_di_teks)
    else:
        p_ret, low_ret, up_ret = 0.0, 0.0, 0.0

    return {
        "total_evaluated": n_total,
        "n_benar": n_benar,
        "n_salah": n_salah,
        "n_tidak_ada_di_teks": n_tidak_ada,
        "n_terlewat": n_terlewat,
        "n_extracted": n_ekstrak,
        "n_in_text": n_ada_di_teks,
        "ketepatan": p_ket,
        "wilson_ci_ketepatan": (low_ket, up_ket),
        "keterambilan": p_ret,
        "wilson_ci_keterambilan": (low_ret, up_ret),
    }


def calculate_percentage_agreement(
    ratings_a: List[str],
    ratings_b: List[str],
) -> float:
    """Hitung persentase kesepakatan (percentage agreement) antar dua penilai.

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
