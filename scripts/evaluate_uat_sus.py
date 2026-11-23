"""Skrip CLI persiapan template dan perhitungan UAT + SUS tanpa data pribadi [PM-22]."""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.evaluation.sus import summarize_sus_responses, summarize_uat_results

UAT_HEADER = [
    "participant_code",
    "role",
    "task_id",
    "task_name",
    "status",
    "duration_seconds",
    "notes",
]

SUS_HEADER = [
    "participant_code",
    "role",
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
    "q6",
    "q7",
    "q8",
    "q9",
    "q10",
    "notes",
]


def write_empty_templates(output_dir: Path) -> Dict[str, Path]:
    """Buat template CSV kosong (hanya header) di luar folder ter-commit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    uat_path = output_dir / "uat_results_template.csv"
    sus_path = output_dir / "sus_responses_template.csv"

    with uat_path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(UAT_HEADER)
    with sus_path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(SUS_HEADER)
    return {"uat_template": uat_path, "sus_template": sus_path}


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_field_study(uat_csv_path: Path, sus_csv_path: Path) -> Dict[str, Any]:
    """Hitung ringkasan UAT, skor SUS, dan cek kecocokan daftar peserta."""
    uat_rows = _read_csv_rows(uat_csv_path)
    sus_rows = _read_csv_rows(sus_csv_path)

    uat_summary = summarize_uat_results(uat_rows)
    sus_summary = summarize_sus_responses(sus_rows)

    uat_participants = {r.get("participant_code", "").strip() for r in uat_rows if r.get("participant_code")}
    sus_participants = {r.get("participant_code", "").strip() for r in sus_rows if r.get("participant_code")}
    warnings: List[str] = []
    if uat_participants or sus_participants:
        missing_in_sus = sorted(uat_participants - sus_participants)
        missing_in_uat = sorted(sus_participants - uat_participants)
        if missing_in_sus:
            warnings.append(f"Peserta ada di UAT tetapi belum mengisi SUS: {missing_in_sus}")
        if missing_in_uat:
            warnings.append(f"Peserta mengisi SUS tetapi belum tercatat di UAT: {missing_in_uat}")

    overall_status = (
        "complete"
        if uat_summary["status"] == "complete" and sus_summary["status"] == "complete"
        else "pending"
    )
    return {
        "status": overall_status,
        "participant_mismatch_warnings": warnings,
        "uat": uat_summary,
        "sus": sus_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Template dan kalkulator uji lapangan UAT/SUS [PM-22].")
    parser.add_argument("--init-templates", action="store_true", help="Buat template CSV kosong.")
    parser.add_argument("--output-dir", default="output/uat_sus", help="Direktori keluaran template.")
    parser.add_argument("--uat-csv", default="output/uat_sus/uat_results.csv", help="Path CSV hasil UAT.")
    parser.add_argument("--sus-csv", default="output/uat_sus/sus_responses.csv", help="Path CSV jawaban SUS.")
    parser.add_argument("--output-json", default="output/uat_sus/uat_sus_summary.json", help="Path ringkasan JSON.")
    args = parser.parse_args()

    if args.init_templates:
        paths = write_empty_templates(Path(args.output_dir))
        print(f"Template UAT : {paths['uat_template']}")
        print(f"Template SUS : {paths['sus_template']}")
        return

    report = evaluate_field_study(Path(args.uat_csv), Path(args.sus_csv))
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Status: {report['status']} | Disimpan ke: {out_path}")


if __name__ == "__main__":
    main()
