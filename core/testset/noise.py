"""Fungsi pembangkit gangguan realistis pada teks kueri pencarian arsip.

Mendukung 6 jenis gangguan realistis yang umum terjadi pada pencarian pengguna:
1. typo: salah ketik satu karakter pada kata, kode, atau singkatan.
2. singkatan: singkatan kata administratif umum (dinas -> dis, nomor -> no, dsb.).
3. spasi_tanda_baca: variasi spasi di sekitar tanda baca atau garis miring.
4. urutan_kata: pembalikan atau pengacakan posisi kata atau komponen nomor.
5. kata_hilang: pengurangan kata fungsional atau satu komponen nomor SPM.
6. ejaan_varian: variasi ejaan bahasa Indonesia atau ejaan resmi/lama (L.S, 02, dsb.).
"""
import random
import re
from typing import Callable, Dict, List, Optional
from rapidfuzz.distance import Levenshtein

ABBREVIATION_MAP = {
    "kecamatan": "kec",
    "kelurahan": "kel",
    "jalan": "jl",
    "lorong": "lrg",
    "gedung": "gd",
    "nomor": "no",
    "tanggal": "tgl",
    "pembangunan": "pemb",
    "pemeliharaan": "pemel",
    "rehabilitasi": "rehab",
    "pengadaan": "peng",
    "pekerjaan": "pek",
    "perencanaan": "perenc",
    "rekanan": "rek",
    "perseroan": "pt",
    "komanditer": "cv",
    "ruangan": "rua",
    "ruang": "rg",
}

SPELLING_VARIANTS = {
    "februari": "pebruari",
    "november": "nopember",
    "provinsi": "propinsi",
    "kantor": "kantur",
    "ijin": "izin",
    "jadwal": "jadual",
    "mesin": "mesen",
    "pompa": "pompe",
    "biaya": "beaya",
    "sarana": "sarane",
    "gedung": "gedong",
    "piala": "pialaa",
    "adipura": "adipoora",
    "kuto": "kuto",
    "besak": "bessak",
}

SPM_ABBREV_MAP = {
    "dinas": "dis",
    "setwan": "stw",
    "sekwan": "sw",
    "perta": "prt",
    "pertanian": "perta",
    "diskominfo": "kominfo",
    "kantor": "kt",
}

SPM_CODE_VARIANTS = {
    "LS": "L.S",
    "BT": "B.T",
    "GU": "G.U",
    "UP": "U.P",
    "TU": "T.U",
    "PK": "P.K",
    "BS": "B.S",
    "SETWAN": "SEKWAN",
    "SEKWAN": "SETWAN",
    "PERTA": "PERTANIAN",
}

KEYBOARD_NEIGHBORS = {
    "A": "Q", "B": "V", "C": "X", "D": "S", "E": "W", "F": "D",
    "G": "F", "H": "G", "I": "U", "J": "H", "K": "J", "L": "K",
    "M": "N", "N": "B", "O": "P", "P": "O", "Q": "W", "R": "E",
    "S": "A", "T": "R", "U": "Y", "V": "C", "W": "Q", "X": "Z",
    "Y": "T", "Z": "X",
}


def is_spm_number(text: str) -> bool:
    """Deteksi apakah teks berpola nomor SPM (berformat slash kode/unit)."""
    clean = text.strip()
    return "/" in clean and len(clean.split()) <= 3


def apply_spm_typo(text: str, r: random.Random) -> str:
    """Salah ketik satu karakter pada kode, singkatan, atau nomor SPM."""
    parts = text.split("/")
    # Prioritaskan salah ketik pada huruf kode/singkatan (LS, BT, Dinas, dll)
    alpha_candidates = [i for i, p in enumerate(parts) if any(c.isalpha() for c in p)]
    if alpha_candidates:
        idx = r.choice(alpha_candidates)
        part = list(parts[idx])
        letter_pos = [i for i, c in enumerate(part) if c.isalpha()]
        pos = r.choice(letter_pos)
        ch = part[pos]
        rep = KEYBOARD_NEIGHBORS.get(ch.upper(), "X")
        part[pos] = rep if ch.isupper() else rep.lower()
        parts[idx] = "".join(part)
        return "/".join(parts)

    # Bila tidak ada huruf, ubah salah satu digit angka
    digit_candidates = [i for i, p in enumerate(parts) if any(c.isdigit() for c in p)]
    if digit_candidates:
        idx = r.choice(digit_candidates)
        part = list(parts[idx])
        digit_pos = [i for i, c in enumerate(part) if c.isdigit()]
        pos = r.choice(digit_pos)
        part[pos] = str((int(part[pos]) + 1) % 10)
        parts[idx] = "".join(part)
        return "/".join(parts)

    return text + "1"


def apply_spm_punctuation_spacing(text: str, r: random.Random) -> str:
    """Variasi spasi atau tanda baca pada nomor SPM."""
    parts = text.split("/")
    style = r.choice(["slash_space", "dash", "space_mixed"])
    if style == "slash_space":
        return " / ".join(parts)
    if style == "dash":
        return "-".join(parts)
    if len(parts) >= 2:
        idx = r.randint(0, len(parts) - 2)
        sep = " " if r.random() < 0.5 else "-"
        return "/".join(parts[:idx] + [parts[idx] + sep + parts[idx + 1]] + parts[idx + 2:])
    return text.replace("/", " / ")


def apply_spm_missing_component(text: str, r: random.Random) -> str:
    """Hilangkan satu komponen nomor SPM."""
    parts = text.split("/")
    if len(parts) <= 1:
        return text[:-1] if text else text
    idx = r.randint(0, len(parts) - 1)
    parts.pop(idx)
    return "/".join(parts)


def apply_spm_abbreviation(text: str, r: random.Random) -> str:
    """Singkatan komponen dinas, singkatan kode, atau pemotongan komponen SPM."""
    parts = text.split("/")
    changed = False
    for i, p in enumerate(parts):
        p_low = p.lower()
        if p_low in SPM_ABBREV_MAP:
            parts[i] = SPM_ABBREV_MAP[p_low]
            changed = True
            break
        if p.upper() == "SPM":
            parts.pop(i)
            changed = True
            break
        if p.isdigit() and p.startswith("0") and len(p) > 1:
            parts[i] = str(int(p))
            changed = True
            break

    if not changed:
        for i, p in enumerate(parts):
            if len(p) >= 4 and p.isalpha():
                parts[i] = p[:3]
                changed = True
                break

    if not changed and parts:
        if len(parts[-1]) > 2:
            parts[-1] = parts[-1][:2]
        else:
            parts.insert(0, "No.")

    return "/".join(parts)


def apply_spm_spelling_variant(text: str, r: random.Random) -> str:
    """Varian ejaan atau penulisan kode/tahun pada nomor SPM."""
    parts = text.split("/")
    for i, p in enumerate(parts):
        if p.upper() in SPM_CODE_VARIANTS:
            parts[i] = SPM_CODE_VARIANTS[p.upper()]
            return "/".join(parts)
        if len(p) == 4 and p.isdigit() and p.startswith(("19", "20")):
            # Varian tahun 2 digit
            parts[i] = p[2:]
            return "/".join(parts)

    for i, p in enumerate(parts):
        if len(p) >= 2 and p.isalpha():
            parts[i] = ".".join(list(p))
            return "/".join(parts)

    return text.replace("/", ".")


def apply_spm_word_order(text: str, r: random.Random) -> str:
    """Pembalikan atau pengacakan posisi komponen nomor SPM."""
    parts = text.split("/")
    if len(parts) < 2:
        return text
    idx1, idx2 = r.sample(range(len(parts)), 2)
    parts[idx1], parts[idx2] = parts[idx2], parts[idx1]
    return "/".join(parts)


def apply_typo(text: str, rng: Optional[random.Random] = None) -> str:
    """Terapkan satu kesalahan ketik (transposisi atau delesi karakter)."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_typo(text, r)

    words = text.split()
    if not words:
        return text

    candidates = [i for i, w in enumerate(words) if len(w) >= 2]
    if not candidates:
        return text + "x"

    idx = r.choice(candidates)
    word = list(words[idx])

    if len(word) >= 3 and r.random() < 0.6:
        # Transposisi dua karakter bersebelahan
        pos = r.randint(0, len(word) - 2)
        word[pos], word[pos + 1] = word[pos + 1], word[pos]
    elif len(word) >= 2:
        # Hapus satu karakter
        pos = r.randint(0, len(word) - 1)
        word.pop(pos)
    else:
        word.append("x")

    words[idx] = "".join(word)
    return " ".join(words)


def apply_abbreviation(text: str, rng: Optional[random.Random] = None) -> str:
    """Ubah kata menjadi singkatan jika ada padanan di kamus."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_abbreviation(text, r)

    words = text.split()
    changed = False
    for i, w in enumerate(words):
        w_low = w.lower().strip(".,")
        if w_low in ABBREVIATION_MAP:
            words[i] = ABBREVIATION_MAP[w_low]
            changed = True
            break

    if not changed and words:
        for i, w in enumerate(words):
            if len(w) >= 5 and w.isalpha():
                words[i] = w[:3] + "."
                changed = True
                break

    if not changed and words:
        for i, w in enumerate(words):
            if len(w) >= 3:
                words[i] = w[:2] + "."
                changed = True
                break

    return " ".join(words)


def apply_punctuation_spacing(text: str, rng: Optional[random.Random] = None) -> str:
    """Ubah spasi di sekitar tanda baca atau garis miring."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_punctuation_spacing(text, r)

    if "/" in text:
        return text.replace("/", " / ") if " / " not in text else text.replace(" / ", "/")
    if "-" in text:
        return text.replace("-", " - ") if " - " not in text else text.replace(" - ", "-")

    if r.random() < 0.5:
        return text + ", "

    words = text.split()
    if len(words) >= 2:
        return words[0] + "  " + " ".join(words[1:])
    return text + " ."


def apply_word_order(text: str, rng: Optional[random.Random] = None) -> str:
    """Tukar posisi dua kata dalam kueri."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_word_order(text, r)

    words = text.split()
    if len(words) < 2:
        return text
    idx1, idx2 = r.sample(range(len(words)), 2)
    words[idx1], words[idx2] = words[idx2], words[idx1]
    return " ".join(words)


def apply_missing_word(text: str, rng: Optional[random.Random] = None) -> str:
    """Hilangkan satu kata dari kueri."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_missing_component(text, r)

    words = text.split()
    if len(words) <= 1:
        return text
    idx = r.randint(0, len(words) - 1)
    words.pop(idx)
    return " ".join(words)


def apply_spelling_variant(text: str, rng: Optional[random.Random] = None) -> str:
    """Terapkan variasi ejaan resmi atau ejaan lama."""
    r = rng or random.Random()
    if is_spm_number(text):
        return apply_spm_spelling_variant(text, r)

    words = text.split()
    for i, w in enumerate(words):
        w_low = w.lower().strip(".,")
        if w_low in SPELLING_VARIANTS:
            words[i] = SPELLING_VARIANTS[w_low]
            return " ".join(words)

    for i, w in enumerate(words):
        w_low = w.lower()
        if "u" in w_low:
            words[i] = w_low.replace("u", "o", 1)
            return " ".join(words)
        if "o" in w_low:
            words[i] = w_low.replace("o", "u", 1)
            return " ".join(words)
        if "e" in w_low:
            words[i] = w_low.replace("e", "i", 1)
            return " ".join(words)
        if "i" in w_low:
            words[i] = w_low.replace("i", "e", 1)
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
        Teks kueri setelah diberi gangguan. Untuk jenis bergangguan, dijamin
        jarak Levenshtein terhadap teks asli selalu > 0.
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
    res = func(text, rng)

    # Jaminan keselamatan: jika gangguan belum mengubah teks, lakukan modifikasi deterministik
    if res == text or int(Levenshtein.distance(text, res)) == 0:
        if is_spm_number(text):
            res = apply_spm_typo(text, rng)
            if res == text or int(Levenshtein.distance(text, res)) == 0:
                res = text + "/01"
        else:
            if len(text) > 3:
                res = text[:-1]
            else:
                res = text + " ."

    return res
