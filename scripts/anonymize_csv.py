"""Skrip untuk menganonimkan berkas CSV penilaian di output/ agar aman dari paparan data nyata.

Data dinas nyata (nama rekanan, nomor SPM/SP2D, nominal, dan uraian proyek)
digantikan dengan data contoh/sintetis dengan mempertahankan pola struktur formatnya.
Berkas asli secara otomatis dicadangkan di output/.real_data_backup/.
"""
import csv
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.testset.noise import add_noise
from scripts.export_relevance_verification_sample import export_verification_sample

OUTPUT_DIR = ROOT_DIR / "output"
BACKUP_DIR = OUTPUT_DIR / ".real_data_backup"

GENERIC_PROJECTS = [
    "pekerjaan pembangunan gedung kantor dinas contoh",
    "pekerjaan rehabilitasi fasilitas umum contoh",
    "pengadaan barang inventaris dan sarana kantor contoh",
    "pekerjaan pemeliharaan fasilitas dinas contoh",
    "pekerjaan penataan lingkungan dan sarana prasarana contoh",
    "pengadaan peralatan operasional dinas contoh",
    "pekerjaan pembangunan sarana fisik contoh",
    "pekerjaan renovasi ruang kerja contoh",
    "penyusunan dokumen perencanaan teknis contoh",
    "pekerjaan pemeliharaan gedung dinas contoh",
]

MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


def backup_original_files() -> None:
    """Cadangkan berkas asli sebelum diubah jika cadangan belum ada."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target_files = [
        "audit_extraction_sample.csv",
        "audit_agreement_sample.csv",
        "audit_strata_summary.json",
        "relevance_pool.csv",
        "relevance_pool_pilot_5.csv",
        "relevance_verification_sample.csv",
        ".candidate_queries.json",
    ]
    for fname in target_files:
        src = OUTPUT_DIR / fname
        dst = BACKUP_DIR / fname
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)
            print(f"Dicadangkan: {fname} -> {dst}")


def detect_spm_type(text: str) -> str:
    """Deteksi jenis SPM dari teks."""
    upper = text.upper()
    for code in ["LS", "BT", "BS", "GU", "UP", "TU", "PK"]:
        if re.search(rf"\b{code}\b", upper) or f"/{code}/" in upper or f"/{code}" in upper:
            return code
    return "LS"


def detect_termin(text: str) -> str:
    """Deteksi frase termin jika ada di teks asli."""
    m = re.search(r"(termin[a-z]*\s+(?:ke\s+)?(?:[I|V|X|0-9]+(?:\s*[,/dan\s]+\s*[I|V|X|0-9]+)*))", text, re.I)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"(\b(?:100\s*%\s*|uang\s+muka)\b)", text, re.I)
    if m2:
        return m2.group(1).strip()
    return ""


def generate_archive_dummy(archive_id: int, original_summary: str) -> Dict[str, str]:
    """Hasilkan data tiruan yang konsisten per archive_id."""
    has_spm = bool(re.search(r"no\.?\s*spm", original_summary, re.I))
    has_sp2d = bool(re.search(r"no\.?\s*sp2d", original_summary, re.I))
    has_party = bool(re.search(r"\b(?:CV|PT)\b", original_summary, re.I))
    has_date = bool(re.search(r"(?:tgl|tanggal)", original_summary, re.I))
    has_amount = bool(re.search(r"jumlah\s*[:\-]?\s*rp", original_summary, re.I))

    spm_type = detect_spm_type(original_summary)
    year = 2000 + (archive_id % 10)
    month_idx = (archive_id % 12)
    day = (archive_id % 28) + 1
    month_name = MONTH_NAMES_ID[month_idx]
    iso_date = f"{year}-{month_idx + 1:02d}-{day:02d}"

    seq_num = f"{((archive_id * 7) % 900) + 100:03d}"
    spm_code = f"{seq_num}/{spm_type}/Dinas/{year}" if has_spm else ""

    sp2d_num = f"{((archive_id * 13) % 9000) + 1000}/{year}" if has_sp2d else ""

    party_num = (archive_id % 25) + 1
    if has_party:
        party_name = f"PT Rekanan Contoh {party_num}" if archive_id % 2 == 0 else f"CV Contoh Mandiri {party_num}"
    else:
        party_name = ""

    amount_val = ((archive_id * 19) % 80 + 5) * 2_500_000
    amount_str = f"Rp {amount_val:,.0f}".replace(",", ".")

    termin_phrase = detect_termin(original_summary)
    proj_idx = (archive_id % len(GENERIC_PROJECTS))
    proj_name = GENERIC_PROJECTS[proj_idx]

    parts = []
    if termin_phrase:
        parts.append(f"Pembayaran {termin_phrase} atas {proj_name}")
    else:
        parts.append(f"Pembayaran atas {proj_name}")

    if party_name:
        parts.append(party_name)
    if spm_code:
        parts.append(f"No. SPM: {spm_code}")
    if sp2d_num:
        parts.append(f"No. SP2D: {sp2d_num}")
    if has_date:
        parts.append(f"Tanggal: {day} {month_name} {year}")
    if has_amount:
        parts.append(f"Jumlah: {amount_str}")

    dummy_summary = " ".join(parts)

    return {
        "summary_raw": dummy_summary,
        "spm_number": spm_code,
        "sp2d_number": sp2d_num,
        "party_name": party_name,
        "date_iso": iso_date if has_date else "",
        "amount_num": str(amount_val) if has_amount else "",
        "amount_str": amount_str if has_amount else "",
    }


def anonymize_all_csvs() -> None:
    """Terapkan anonimisasi langsung pada seluruh berkas CSV di output/."""
    backup_original_files()

    # 1. Kumpulkan seluruh archive_id dan buat peta dummy konsisten
    archive_dummies: Dict[int, Dict[str, str]] = {}

    # Muat dari berkas cadangan agar selalu deterministik dari sumber asli
    target_csvs = [
        "relevance_pool.csv",
        "relevance_pool_pilot_5.csv",
        "relevance_verification_sample.csv",
        "audit_extraction_sample.csv",
        "audit_agreement_sample.csv",
    ]

    for fname in target_csvs:
        src = BACKUP_DIR / fname
        if not src.is_file():
            src = OUTPUT_DIR / fname
        with open(src, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aid = int(row["archive_id"])
                if aid not in archive_dummies:
                    archive_dummies[aid] = generate_archive_dummy(aid, row.get("summary_raw", ""))

    print(f"Total archive dummy dipetakan: {len(archive_dummies)}")

    # 2. Anonimkan candidate queries dengan menerapkan gangguan realistis
    cq_path = BACKUP_DIR / ".candidate_queries.json"
    if not cq_path.is_file():
        cq_path = OUTPUT_DIR / ".candidate_queries.json"

    query_text_map: Dict[str, str] = {}
    if cq_path.is_file():
        with open(cq_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)

        for idx, cq in enumerate(candidates, start=1):
            qid = cq["query_id"]
            qtype = cq["query_type"]
            noise = cq["noise_type"]
            aid = cq.get("origin_archive_id")
            dummy_data = archive_dummies.get(aid, {})

            if qtype == "nomor_spm" and dummy_data.get("spm_number"):
                base_q = dummy_data["spm_number"]
            elif qtype == "pihak" and dummy_data.get("party_name"):
                base_q = dummy_data["party_name"]
            elif qtype == "topik":
                base_q = cq.get("base_text") or cq["query_text"]
                if "kuto besak" in base_q.lower():
                    base_q = "gedung fasilitas umum"
            elif qtype == "campuran":
                base_q = cq.get("base_text") or cq["query_text"]
                if "kuto besak" in base_q.lower():
                    base_q = "gedung fasilitas umum"
            else:
                base_q = cq.get("base_text") or cq["query_text"]

            # Terapkan gangguan secara deterministik
            seed = 42 + idx
            noisy_q = add_noise(base_q, noise, seed=seed)

            cq["base_text"] = base_q
            cq["query_text"] = noisy_q
            query_text_map[qid] = noisy_q

        with open(OUTPUT_DIR / ".candidate_queries.json", "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2, ensure_ascii=False)
        print("Diperbarui: .candidate_queries.json dengan gangguan realistis")

    # 3. Anonimkan relevance_pool.csv
    src_pool = BACKUP_DIR / "relevance_pool.csv"
    if not src_pool.is_file():
        src_pool = OUTPUT_DIR / "relevance_pool.csv"

    with open(src_pool, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        pool_rows = list(reader)

    for row in pool_rows:
        aid = int(row["archive_id"])
        dummy = archive_dummies[aid]
        row["summary_raw"] = dummy["summary_raw"]
        row["spm_number"] = dummy["spm_number"]
        row["party_name"] = dummy["party_name"]
        if row["query_id"] in query_text_map:
            row["query_text"] = query_text_map[row["query_id"]]
        # Wajib kosongkan kolom penilaian
        row["is_relevant"] = ""
        row["ragu"] = ""
        if "auditor_notes" in row:
            row["auditor_notes"] = ""
        if "archivist_notes" in row:
            row["archivist_notes"] = ""

    out_pool = OUTPUT_DIR / "relevance_pool.csv"
    with open(out_pool, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pool_rows)
    print(f"Diperbarui langsung (data dummy): relevance_pool.csv ({len(pool_rows)} baris)")

    # Perbarui relevance_pool_pilot_5.csv (hanya kueri Q001 s.d Q005)
    pilot_rows = [r for r in pool_rows if r["query_id"] in ["Q001", "Q002", "Q003", "Q004", "Q005"]]
    with open(OUTPUT_DIR / "relevance_pool_pilot_5.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pilot_rows)
    print(f"Diperbarui langsung (data dummy): relevance_pool_pilot_5.csv ({len(pilot_rows)} baris)")

    # Perbarui relevance_verification_sample.csv (sampel berstrata acak 120 baris)
    export_verification_sample(
        pool_csv_path=out_pool,
        output_csv_path=OUTPUT_DIR / "relevance_verification_sample.csv",
        sample_size=120,
        seed=42,
    )
    print("Diperbarui langsung (data dummy): relevance_verification_sample.csv (120 baris)")

    # 4. Anonimkan audit_extraction_sample.csv & audit_agreement_sample.csv
    new_reference_records = {}
    new_agreement_reference_records = {}

    for fname in ["audit_extraction_sample.csv", "audit_agreement_sample.csv"]:
        src = BACKUP_DIR / fname
        if not src.is_file():
            src = OUTPUT_DIR / fname
        with open(src, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        for row in rows:
            aid = int(row["archive_id"])
            dummy = archive_dummies[aid]
            row["summary_raw"] = dummy["summary_raw"]
            row["extracted_spm"] = dummy["spm_number"]
            row["extracted_sp2d"] = dummy["sp2d_number"]
            row["extracted_date"] = dummy["date_iso"]
            row["extracted_amount"] = dummy["amount_num"]
            row["extracted_party"] = dummy["party_name"]

            # Kolom penilaian wajib kosong
            for fld in ["spm", "sp2d", "date", "amount", "party"]:
                row[f"verdict_{fld}"] = ""
            if "auditor_notes" in row:
                row["auditor_notes"] = ""

            record_entry = {
                "sample_id": int(row["sample_id"]),
                "archive_id": aid,
                "summary_raw": dummy["summary_raw"],
                "extracted_spm": dummy["spm_number"],
                "extracted_sp2d": dummy["sp2d_number"],
                "extracted_date": dummy["date_iso"],
                "extracted_amount": dummy["amount_num"],
                "extracted_party": dummy["party_name"],
            }
            if fname == "audit_extraction_sample.csv":
                new_reference_records[str(aid)] = record_entry
            else:
                new_agreement_reference_records[str(aid)] = record_entry

        with open(OUTPUT_DIR / fname, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Diperbarui langsung (data dummy): {fname} ({len(rows)} baris)")

    # 5. Perbarui audit_strata_summary.json agar reference_records cocok dengan data dummy
    manifest_src = BACKUP_DIR / "audit_strata_summary.json"
    if not manifest_src.is_file():
        manifest_src = OUTPUT_DIR / "audit_strata_summary.json"

    if manifest_src.is_file():
        with open(manifest_src, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest["reference_records"] = new_reference_records
        manifest["agreement_reference_records"] = new_agreement_reference_records
        manifest["is_anonymized"] = True
        with open(OUTPUT_DIR / "audit_strata_summary.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print("Diperbarui: audit_strata_summary.json dengan referensi rekaman dummy")


if __name__ == "__main__":
    anonymize_all_csvs()
