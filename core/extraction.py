"""Ekstraksi metadata terstruktur dari kolom `ringkasan`.

Modul ini hanya mengekstrak. Ketepatan hasil belum terbukti sebelum audit
manual selesai; yang bisa dilaporkan lebih dulu hanyalah cakupan.
"""
import re
from datetime import date
from typing import Dict, Optional, Union

from core.normalization import normalize_code

MONTHS = {
    "januari": 1, "jan": 1,
    "februari": 2, "pebruari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "agt": 8, "ags": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nopember": 11, "nov": 11,
    "desember": 12, "des": 12,
}

_STOP_WITH_SP2D = r"(?=\s*(?:-\s*)?(?:tanggal|tgl|no\.?\s*sp2d|jumlah)\b|\s*$)"
_STOP = r"(?=\s*(?:-\s*)?(?:tanggal|tgl|jumlah)\b|\s*$)"
_SPM_LABEL = re.compile(r"no\.?\s*spm", re.I)
_SPM = re.compile(r"no\.?\s*spm\s*[:.\-]?\s*(?P<v>.{2,45}?)" + _STOP_WITH_SP2D, re.I)
_SP2D = re.compile(r"no\.?\s*sp2d\s*[:.\-]?\s*(?P<v>.{2,30}?)" + _STOP, re.I)
_DATE_TEXT = re.compile(
    r"(?:tanggal|tgl)\.?\s*[:\-]?\s*(\d{1,2})\s*[-/ ]?\s*([A-Za-z]{3,9})\s*[-/ ]?\s*(\d{4})", re.I)
_DATE_NUMERIC = re.compile(
    r"(?:tanggal|tgl)\.?\s*[:\-]?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})", re.I)
_AMOUNT = re.compile(r"jumlah\s*[:\-]?\s*rp\.?\s*:?\s*(\d[\d.,]*)", re.I)
_PARTY = re.compile(
    r"\b((?:CV|PT)\.?\s*[A-Za-z0-9&.\- ]{2,40}?)"
    r"(?=\s+(?:No\.?\s*SPM|Tanggal|Tgl|Jumlah|di\s|dengan|berdasarkan|sesuai)|\s*[,(]|\s*$)")

Metadata = Dict[str, Union[str, int, bool, None]]


def _build_date(year: int, month: int, day: int) -> Optional[str]:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_rupiah(text: str) -> Optional[int]:
    """Ubah teks nominal (`228.399.000,-`, `1.000.000,00`) menjadi bilangan bulat rupiah.

    Titik/koma dianggap pemisah ribuan; dua digit di ujung dianggap sen dan dibuang
    hanya bila didahului kelompok ribuan.
    """
    cleaned = re.sub(r"[.,]-+$", "", text.strip()).rstrip(".,")
    if re.search(r"\d[.,]\d{3}[.,]\d{2}$", cleaned) or re.search(r"\d{4,}[.,]\d{2}$", cleaned):
        cleaned = cleaned[:-3]
    digits = re.sub(r"\D", "", cleaned)
    return int(digits) if digits else None


def extract_metadata(summary: str) -> Metadata:
    """Ekstrak SPM, SP2D, tanggal, nominal, dan pihak dari ringkasan.

    Args:
        summary: Isi kolom ringkasan.

    Returns:
        Kamus `spm_number`, `spm_sequence`, `spm_type_code`, `spm_suffix`,
        `sp2d_number`, `document_date` (ISO), `amount_rp`, `party_name`,
        `has_spm_label`. Nilai yang tidak terbaca bernilai None.
    """
    text = re.sub(r"\s+", " ", summary or "")
    result: Metadata = {
        "spm_number": None, "spm_sequence": None, "spm_type_code": None,
        "spm_suffix": None, "sp2d_number": None, "document_date": None,
        "amount_rp": None, "party_name": None,
        "has_spm_label": bool(_SPM_LABEL.search(text)),
    }

    search_from = 0
    spm_match = _SPM.search(text)
    if spm_match:
        number = normalize_code(spm_match.group("v"))
        parts = number.split("/")
        result["spm_number"] = number or None
        if parts[0].isdigit():
            result["spm_sequence"] = parts[0].lstrip("0") or "0"
        if len(parts) > 1:
            result["spm_type_code"] = parts[1] or None
        if len(parts) > 2:
            result["spm_suffix"] = "/".join(parts[2:]) or None
        search_from = spm_match.end()

    sp2d_match = _SP2D.search(text)
    if sp2d_match:
        result["sp2d_number"] = normalize_code(sp2d_match.group("v")) or None

    # Tanggal dicari setelah nomor SPM dulu agar tidak tertukar dengan tanggal lain.
    for scope in (text[search_from:], text):
        found = _DATE_TEXT.search(scope)
        if found and found.group(2).lower() in MONTHS:
            parsed = _build_date(int(found.group(3)), MONTHS[found.group(2).lower()],
                                 int(found.group(1)))
            if parsed:
                result["document_date"] = parsed
                break
        found = _DATE_NUMERIC.search(scope)
        if found:
            parsed = _build_date(int(found.group(3)), int(found.group(2)),
                                 int(found.group(1)))
            if parsed:
                result["document_date"] = parsed
                break

    amount_match = _AMOUNT.search(text)
    if amount_match:
        result["amount_rp"] = parse_rupiah(amount_match.group(1))

    party_match = _PARTY.search(text)
    if party_match:
        result["party_name"] = re.sub(r"\s+", " ", party_match.group(1)).strip(" .,-") or None

    return result
