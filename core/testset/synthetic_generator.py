"""Pembangkit kueri sintetis dari korpus arsip dengan variasi gangguan."""
import re
from typing import Dict, List, Optional

from core.testset.noise import add_noise

SKIP_TOPIC_WORDS = {
    "atas", "pekerjaan", "pekerjan", "pembayaran", "pembayaraan", "angsuran",
    "dan", "ke", "di", "pada", "untuk", "biaya", "tahap",
    "term", "termin", "terminj", "terminan", "oleh", "dalam", "deret",
}


def extract_topic_phrase(summary: str) -> Optional[str]:
    """Ekstrak frase inti pekerjaan dari teks ringkasan bebas."""
    text = summary or ""
    text = re.sub(
        r"(?i)\b(?:no\.?\s*spm|nospm|no\.?\s*sp2d|tgl\.?|tanggal|jumlah)\b.*",
        " ",
        text,
    )
    text = re.sub(r"(?i)\b(?:cv|pt|ud)\b\.?\s*[A-Za-z0-9&.,\- ]*", " ", text)
    text = re.sub(
        r"(?i)^\s*(?:spm\s+pembangunan\s+\d{4}\s*[-,:]?\s*)?(?:ls\s*[-,:]?\s*)?",
        "",
        text,
    )
    text = re.sub(
        r"(?i)^\s*(?:pembayaran\s+)?(?:uang\s+muka\s+(?:kerja\s+)?|termin\w*\s+(?:ke\s+)?(?:(?:s/d|dan|[ivx0-9,/\-.\s])+)?|\(\s*\d+\s*%\s*\)\s*|tahap\s+[ivx0-9]+\s*)?(?:\(\s*\d+\s*%\s*\)\s*)?(?:atas\s+pekerjaan\s+|pekerjaan\s+|atas\s+biaya\s+|biaya\s+umum\s+|biaya\s+|untuk\s+)?",
        "",
        text,
    )
    text = re.sub(
        r"(?i)^\s*(?:pembayaran\s+)?uang\s+untuk\s+di\s*pertanggung\s*jawabkan\s*(?:\(\s*uudp\s*\))?\s*[,.\-]?\s*(?:biaya\s+umum\s+|biaya\s+)?",
        "",
        text,
    )
    tokens: List[str] = []
    for raw in text.split():
        w = raw.strip(" .,-()/\"\\")
        if len(w) < 2 or "%" in w:
            continue
        if w.lower() in {"jl", "jln"}:
            continue
        if len(w) < 3 or w.lower() in SKIP_TOPIC_WORDS:
            continue
        tokens.append(w)
    if len(tokens) >= 2:
        take_n = 4 if "tiang" in [t.lower() for t in tokens[:3]] else 3
        return " ".join(tokens[:take_n])
    return None


def generate_synthetic_query(
    archive_record: Dict[str, object],
    query_type: str,
    noise_type: str = "tanpa_gangguan",
    seed: Optional[int] = None,
) -> Optional[Dict[str, object]]:
    """Bangun satu kueri sintetis dari satu record arsip.

    Args:
        archive_record: Record arsip memuat summary_clean, spm_number, party_name, year, id.
        query_type: Jenis kueri ('topik', 'nomor_spm', 'pihak', 'campuran').
        noise_type: Jenis gangguan dari NOISE_FUNCTIONS atau 'tanpa_gangguan'.
        seed: Random seed.

    Returns:
        Kamus kueri terstruktur, atau None bila arsip tidak memuat field yang dibutuhkan.
    """
    summary = str(archive_record.get("summary_clean") or "")
    spm = archive_record.get("spm_number")
    party = archive_record.get("party_name")
    year = archive_record.get("year")
    arch_id = archive_record.get("id")

    base_text: Optional[str] = None

    if query_type == "topik":
        base_text = extract_topic_phrase(summary)
    elif query_type == "nomor_spm":
        if spm:
            base_text = str(spm)
    elif query_type == "pihak":
        if party:
            base_text = str(party)
    elif query_type == "campuran":
        topic = extract_topic_phrase(summary)
        eff_year = year
        if eff_year and int(eff_year) > 2020:
            m_yr = re.search(r"\b(19\d{2}|20[01]\d)\b", f"{spm or ''} {summary}")
            if m_yr:
                eff_year = int(m_yr.group(1))
        if topic and eff_year:
            base_text = f"{topic} {eff_year}"
        elif party and eff_year:
            base_text = f"{party} {eff_year}"
        elif topic and spm:
            base_text = f"{topic} {spm}"

    if not base_text:
        return None

    noisy_text = add_noise(base_text, noise_type, seed=seed)

    return {
        "query_text": noisy_text,
        "base_text": base_text,
        "query_type": query_type,
        "noise_type": noise_type,
        "source": "sintetis",
        "origin_archive_id": arch_id,
    }
