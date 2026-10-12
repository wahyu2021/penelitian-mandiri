"""Fungsi pembangkit gangguan realistis pada teks kueri pencarian arsip.

Mendukung 6 jenis gangguan realistis yang umum terjadi pada pencarian pengguna:
1. typo: transposisi atau penghapusan karakter tunggal.
2. singkatan: singkatan kata administratif umum (jalan -> jl, dsb.).
3. spasi_tanda_baca: variasi spasi di sekitar tanda baca atau garis miring.
4. urutan_kata: pembalikan atau pengacakan posisi kata.
5. kata_hilang: pengurangan kata fungsional/penjelas.
6. ejaan_varian: variasi ejaan bahasa Indonesia (februari -> pebruari, dsb.).
"""
import random
from typing import Callable, Dict, List, Optional

ABBREVIATION_MAP = {
    "kecamatan": "kec",
    "kelurahan": "kel",
    "jalan": "jl",
    "lorong": "lrg",
    "gedung": "gd",
    "nomor": "no",
    "tanggal": "tgl",
}

SPELLING_VARIANTS = {
    "februari": "pebruari",
    "november": "nopember",
    "provinsi": "propinsi",
    "kantor": "kantur",
    "ijin": "izin",
    "jadwal": "jadual",
}


def apply_typo(text: str, rng: Optional[random.Random] = None) -> str:
    """Terapkan satu kesalahan ketik (transposisi atau delesi karakter)."""
    r = rng or random.Random()
    words = text.split()
    if not words:
        return text

    candidates = [i for i, w in enumerate(words) if len(w) >= 4]
    if not candidates:
        return text

    idx = r.choice(candidates)
    word = list(words[idx])

    if len(word) >= 4 and r.random() < 0.6:
        # Transposisi dua karakter bersebelahan
        pos = r.randint(1, len(word) - 2)
        word[pos], word[pos + 1] = word[pos + 1], word[pos]
    else:
        # Hapus satu karakter
        pos = r.randint(1, len(word) - 1)
        word.pop(pos)

    words[idx] = "".join(word)
    return " ".join(words)


def apply_abbreviation(text: str, rng: Optional[random.Random] = None) -> str:
    """Ubah kata menjadi singkatan jika ada padanan di kamus."""
    words = text.split()
    changed = False
    for i, w in enumerate(words):
        w_low = w.lower().strip(".,")
        if w_low in ABBREVIATION_MAP:
            words[i] = ABBREVIATION_MAP[w_low]
            changed = True
            break
    if not changed and words:
        # Jika tidak ada di kamus, buat singkatan buatan (misal Dinas -> Dis)
        for i, w in enumerate(words):
            if len(w) >= 6:
                words[i] = w[:3] + "."
                break
    return " ".join(words)


def apply_punctuation_spacing(text: str, rng: Optional[random.Random] = None) -> str:
    """Ubah spasi di sekitar tanda baca atau garis miring."""
    r = rng or random.Random()
    if "/" in text:
        # Tambah atau hapus spasi di sekitar slash
        if " / " in text:
            return text.replace(" / ", "/")
        return text.replace("/", " / ")
    if "-" in text:
        return text.replace("-", " - ")
    # Tambah tanda titik atau koma di akhir
    return text + (", " if r.random() < 0.5 else " .")


def apply_word_order(text: str, rng: Optional[random.Random] = None) -> str:
    """Tukar posisi dua kata dalam kueri."""
    r = rng or random.Random()
    words = text.split()
    if len(words) < 2:
        return text
    idx1, idx2 = r.sample(range(len(words)), 2)
    words[idx1], words[idx2] = words[idx2], words[idx1]
    return " ".join(words)


def apply_missing_word(text: str, rng: Optional[random.Random] = None) -> str:
    """Hilangkan satu kata non-kunci dari kueri."""
    r = rng or random.Random()
    words = text.split()
    if len(words) <= 2:
        return text
    idx = r.randint(0, len(words) - 1)
    words.pop(idx)
    return " ".join(words)


def apply_spelling_variant(text: str, rng: Optional[random.Random] = None) -> str:
    """Terapkan variasi ejaan resmi atau ejaan lama."""
    words = text.split()
    for i, w in enumerate(words):
        w_low = w.lower().strip(".,")
        if w_low in SPELLING_VARIANTS:
            words[i] = SPELLING_VARIANTS[w_low]
            return " ".join(words)
    # Variasi vokal umum jika kata khusus tidak ada
    for i, w in enumerate(words):
        if "u" in w.lower():
            words[i] = w.lower().replace("u", "o", 1)
            return " ".join(words)
    return text


NOISE_FUNCTIONS: Dict[str, Callable[[str, Optional[random.Random]], str]] = {
    "typo": apply_typo,
    "singkatan": apply_abbreviation,
    "spasi_tanda_baca": apply_punctuation_spacing,
    "urutan_kata": apply_word_order,
    "kata_hilang": apply_missing_word,
    "ejaan_varian": apply_spelling_variant,
}


def add_noise(
    text: str,
    noise_type: str,
    seed: Optional[int] = None,
) -> str:
    """Tambahkan jenis gangguan tertentu pada teks.

    Args:
        text: Teks kueri mentah.
        noise_type: Salah satu dari 6 jenis gangguan, atau 'tanpa_gangguan'.
        seed: Random seed untuk determinisme.

    Returns:
        Teks kueri setelah diberi gangguan.
    """
    if noise_type == "tanpa_gangguan":
        return text
    func = NOISE_FUNCTIONS.get(noise_type)
    if not func:
        raise ValueError(
            f"Jenis gangguan tidak dikenal: {noise_type}. "
            f"Pilihan: {list(NOISE_FUNCTIONS.keys()) + ['tanpa_gangguan']}"
        )
    rng = random.Random(seed) if seed is not None else random.Random()
    return func(text, rng)
