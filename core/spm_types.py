"""Kamus jenis SPM.

Seluruh entri berstatus `dugaan` sampai dikonfirmasi tertulis oleh dinas.
Arti kode LS/UP/GU/TU memakai istilah umum keuangan daerah; arti BT/BS/PK
belum diketahui dan sengaja tidak ditebak.
"""
from typing import Dict, Optional

CONFIDENCE_GUESS = "dugaan"
CONFIDENCE_CONFIRMED = "terkonfirmasi"

SPM_TYPE_CATALOG: Dict[str, str] = {
    "LS": "Langsung (LS)",
    "UP": "Uang Persediaan (UP)",
    "GU": "Ganti Uang Persediaan (GU)",
    "TU": "Tambahan Uang Persediaan (TU)",
    "BT": "BT (arti belum diketahui)",
    "BS": "BS (arti belum diketahui)",
    "PK": "PK (arti belum diketahui)",
}


def describe_spm_type(code: Optional[str]) -> Dict[str, Optional[str]]:
    """Cari makna kode jenis SPM.

    Args:
        code: Kode (mis. `LS`); None atau kosong bila tidak terbaca.

    Returns:
        Kamus `code`, `label`, `confidence`. Kode di luar kamus diberi label
        `Tidak ada di kamus`. Status selalu `dugaan` pada tahap ini.
    """
    clean = (code or "").strip().upper()
    if not clean:
        return {"code": None, "label": None, "confidence": CONFIDENCE_GUESS}
    label = SPM_TYPE_CATALOG.get(clean, "Tidak ada di kamus")
    return {"code": clean, "label": label, "confidence": CONFIDENCE_GUESS}
