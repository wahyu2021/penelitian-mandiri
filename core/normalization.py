"""Normalisasi teks dan tokenisasi, dipakai sama persis untuk dokumen dan kueri."""
import re
import unicodedata
from typing import List

# Kamus singkatan terbatas; setiap entri harus bisa dipertanggungjawabkan di laporan.
ABBREVIATIONS = {
    "kec": "kecamatan",
    "kel": "kelurahan",
    "jl": "jalan",
    "jln": "jalan",
    "lrg": "lorong",
    "pebruari": "februari",
    "nopember": "november",
}

_SLASH_BETWEEN_ALNUM = re.compile(r"(?<=[a-z0-9])\s*/\s*(?=[a-z0-9])")
_TOKEN = re.compile(r"[a-z0-9]+(?:/[a-z0-9]+)*")


def normalize_code(value: str) -> str:
    """Rapikan nomor surat: hapus spasi di sekitar `/`, huruf besar, tanpa tanda tepi."""
    cleaned = re.sub(r"\s*/\s*", "/", (value or "").strip(" .-:"))
    return re.sub(r"\s+", " ", cleaned).upper()


def normalize_text(text: str, expand_abbreviations: bool = True) -> str:
    """Normalisasi teks untuk pengindeksan dan pencarian.

    Langkah: NFKC, huruf kecil, kode bergaris miring dijaga utuh
    (`446 / bt/5/p` -> `446/bt/5/p`), tanda baca lain jadi pemisah,
    lalu ekspansi singkatan bila diminta.

    Args:
        text: Teks mentah.
        expand_abbreviations: Terapkan kamus ABBREVIATIONS.

    Returns:
        Token dipisah satu spasi.
    """
    lowered = unicodedata.normalize("NFKC", text or "").lower()
    joined = _SLASH_BETWEEN_ALNUM.sub("/", lowered)
    tokens = _TOKEN.findall(joined)
    if expand_abbreviations:
        tokens = [ABBREVIATIONS.get(token, token) for token in tokens]
    return " ".join(tokens)


def tokenize(text: str, expand_abbreviations: bool = True) -> List[str]:
    """Pecah teks ternormalisasi menjadi daftar token."""
    return normalize_text(text, expand_abbreviations).split()
