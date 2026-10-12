"""Evaluasi hasil audit manual ekstraksi metadata dari berkas CSV penilaian."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.audit_metrics import (
    VALID_VERDICTS,
    calculate_field_audit_metrics,
    calculate_percentage_agreement,
)

FIELDS = ["spm", "sp2d", "date", "amount", "party"]
FIELD_LABELS = {
    "spm": "Nomor SPM",
    "sp2d": "Nomor SP2D",
    "date": "Tanggal Dokumen",
    "amount": "Nilai Rupiah",
    "party": "Nama Pihak (CV/PT)",
}
EXPECTED_EXTRACTOR_VERSION = "v1.0.0"


def read_audit_file(csv_path: Path) -> List[Dict[str, str]]:
    """Baca berkas CSV audit dengan encoding utf-8-sig."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Berkas audit tidak ditemukan: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def validate_audit_integrity(
    audit_rows: List[Dict[str, str]],
    manifest_path: Optional[Path] = None,
) -> None:
    """Validasi integritas kolom ekstraksi dan versi ekstraktor."""
    if manifest_path and manifest_path.is_file():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        v = manifest.get("extractor_version")
        if v != EXPECTED_EXTRACTOR_VERSION:
            raise ValueError(
                f"Versi ekstraktor tidak cocok: ditemukan {v!r}, "
                f"diharapkan {EXPECTED_EXTRACTOR_VERSION!r}."
            )

        expected_hash = manifest.get("extracted_data_sha256")
        if expected_hash:
            canonical = json.dumps(
                [
                    {
                        "archive_id": int(r["archive_id"]),
                        "summary_raw": r.get("summary_raw", ""),
                        "spm": r.get("extracted_spm", ""),
                        "sp2d": r.get("extracted_sp2d", ""),
                        "date": r.get("extracted_date", ""),
                        "amount": r.get("extracted_amount", ""),
                        "party": r.get("extracted_party", ""),
                    }
                    for r in audit_rows
                ],
                sort_keys=True,
            )
            calc_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if calc_hash != expected_hash:
                raise ValueError(
                    "Integritas data ekstraksi terlanggar: kolom extracted_* atau "
                    "summary_raw telah diubah dibanding sampel awal yang diekspor."
                )


def validate_and_collect_verdicts(
    rows: List[Dict[str, str]],
    file_label: str = "audit",
) -> Dict[str, List[str]]:
    """Validasi bahwa tidak ada sel kosong dan nilai sah, lalu kumpulkan verdicts."""
    field_verdicts: Dict[str, List[str]] = {fld: [] for fld in FIELDS}

    for idx, r in enumerate(rows, start=1):
        arch_id = r.get("archive_id", f"row_{idx}")
        for fld in FIELDS:
            col_name = f"verdict_{fld}"
            val = r.get(col_name)
            if val is None or not val.strip():
                raise ValueError(
                    f"[{file_label}] Baris ke-{idx} (archive_id={arch_id}) memiliki sel kosong "
                    f"pada kolom {col_name}. Seluruh sel wajib dinilai."
                )
            clean_val = val.strip().lower()
            if clean_val not in VALID_VERDICTS:
                raise ValueError(
                    f"[{file_label}] Baris ke-{idx} (archive_id={arch_id}) bernilai tidak sah: "
                    f"{val!r}. Pilihan sah: {sorted(VALID_VERDICTS)}"
                )
            field_verdicts[fld].append(clean_val)

    return field_verdicts


def evaluate_audit_data(
    audit_rows: List[Dict[str, str]],
    agreement_rows: Optional[List[Dict[str, str]]] = None,
    manifest_path: Optional[Path] = None,
) -> Dict[str, object]:
    """Evaluasi audit ekstraksi dengan validasi ketat dan uji kesepakatan."""
    if not audit_rows:
        raise ValueError("Berkas audit CSV kosong.")

    validate_audit_integrity(audit_rows, manifest_path)

    # Validasi dan kumpulkan penilaian
    audit_verdicts = validate_and_collect_verdicts(audit_rows, file_label="audit_utama")

    field_results = {}
    for fld in FIELDS:
        res = calculate_field_audit_metrics(audit_verdicts[fld])
        field_results[fld] = res

    # Uji kesepakatan penilai kedua jika ada
    agreement_results = {}
    if agreement_rows:
        agree_verdicts = validate_and_collect_verdicts(
            agreement_rows, file_label="audit_kesepakatan"
        )
        map_b = {r["archive_id"]: r for r in agreement_rows}

        for fld in FIELDS:
            ratings_a = []
            ratings_b = []
            for r_a in audit_rows:
                aid = r_a["archive_id"]
                if aid in map_b:
                    v_a = r_a[f"verdict_{fld}"].strip().lower()
                    v_b = map_b[aid][f"verdict_{fld}"].strip().lower()
                    ratings_a.append(v_a)
                    ratings_b.append(v_b)

            if ratings_a:
                agr = calculate_percentage_agreement(ratings_a, ratings_b)
                agreement_results[fld] = agr

    return {
        "extractor_version": EXPECTED_EXTRACTOR_VERSION,
        "n_evaluated": len(audit_rows),
        "fields": field_results,
        "agreement": agreement_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hitung akurasi audit ekstraksi dan persentase kesepakatan."
    )
    parser.add_argument(
        "--audit-csv",
        default="output/audit_extraction_sample.csv",
        help="Path berkas CSV audit utama yang telah dinilai.",
    )
    parser.add_argument(
        "--agreement-csv",
        default="output/audit_agreement_sample.csv",
        help="Path berkas CSV penilaian ganda untuk uji kesepakatan.",
    )
    parser.add_argument(
        "--manifest",
        default="output/audit_strata_summary.json",
        help="Path berkas manifest sampel audit untuk validasi integritas.",
    )
    parser.add_argument(
        "--export-json",
        default="output/extraction_audit_report.json",
        help="Path ekspor ringkasan hasil audit format JSON.",
    )
    args = parser.parse_args()

    audit_path = Path(args.audit_csv)
    agree_path = Path(args.agreement_csv)
    manifest_path = Path(args.manifest)

    try:
        audit_rows = read_audit_file(audit_path)
    except Exception as exc:
        print(f"[GALAT] Gagal membaca berkas audit: {exc}", file=sys.stderr)
        sys.exit(1)

    agree_rows = None
    if agree_path.is_file():
        agree_rows = read_audit_file(agree_path)

    try:
        report = evaluate_audit_data(
            audit_rows=audit_rows,
            agreement_rows=agree_rows,
            manifest_path=manifest_path if manifest_path.is_file() else None,
        )
    except Exception as exc:
        print(f"[GALAT VALIDASI] {exc}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 90)
    print("HASIL EVALUASI AUDIT EKSTRAKSI METADATA (100 SAMPEL BERSTRATA)")
    print("=" * 90)
    fmt = "{:<16} | {:<5} | {:<5} | {:<5} | {:<7} | {:<18} | {:<18}"
    print(
        fmt.format(
            "Field", "Benar", "Salah", "Lewat", "Tdk Ada",
            "Ketepatan (P) ± CI", "Keterambilan (R) ± CI"
        )
    )
    print("-" * 90)

    for fld in FIELDS:
        res = report["fields"][fld]
        p_pct = res["ketepatan"] * 100.0
        p_l, p_u = res["wilson_ci_ketepatan"][0] * 100, res["wilson_ci_ketepatan"][1] * 100
        p_str = f"{p_pct:>5.1f}% [{p_l:.1f}%, {p_u:.1f}%]"

        r_pct = res["keterambilan"] * 100.0
        r_l, r_u = res["wilson_ci_keterambilan"][0] * 100, res["wilson_ci_keterambilan"][1] * 100
        r_str = f"{r_pct:>5.1f}% [{r_l:.1f}%, {r_u:.1f}%]"

        print(
            fmt.format(
                FIELD_LABELS[fld],
                res["n_benar"],
                res["n_salah"],
                res["n_terlewat"],
                res["n_tidak_ada_di_teks"],
                p_str,
                r_str,
            )
        )

    if report["agreement"]:
        print("-" * 90)
        print("PERSENTASE KESEPAKATAN ANTAR-PENILAI (PERCENTAGE AGREEMENT - 20 SAMPEL GANDA):")
        for fld in FIELDS:
            agr_pct = report["agreement"][fld] * 100.0
            print(f"  - {FIELD_LABELS[fld]:<20}: {agr_pct:>6.2f} %")
        macro_agr = sum(report["agreement"].values()) / len(report["agreement"]) * 100.0
        print(f"  * Rata-rata Makro    : {macro_agr:>6.2f} %")

    print("=" * 90)

    # Simpan hasil JSON
    export_path = Path(args.export_json)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[+] Laporan audit berhasil disimpan ke: {export_path}\n")


if __name__ == "__main__":
    main()
