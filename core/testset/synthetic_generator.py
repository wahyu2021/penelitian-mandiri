"""Pembangkit kueri sintetis dari korpus arsip dengan variasi gangguan."""
import random
import re
from typing import Dict, List, Optional

from core.testset.noise import NOISE_FUNCTIONS, add_noise


def extract_topic_phrase(summary: str) -> Optional[str]:
    """Ekstrak frase inti pekerjaan dari teks ringkasan bebas."""
    cleaned = re.sub(r"(?i)no\.?\s*spm.*", "", summary)
    pattern_prefix = r"(?i)pembayaran\s+(?:termin\s+[^a-z]+|atas\s+pekerjaan\s+|untuk\s+)?"
    cleaned = re.sub(pattern_prefix, "", cleaned)
    cleaned = re.sub(r"\b(?:CV|PT)\.?\s+[A-Za-z0-9&.\- ]+", "", cleaned)
    tokens = [w.strip(" .,-") for w in cleaned.split() if len(w.strip(" .,-")) >= 3]
    if len(tokens) >= 2:
        return " ".join(tokens[:4])
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
        if topic and year:
            base_text = f"{topic} {year}"
        elif party and year:
            base_text = f"{party} {year}"
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
