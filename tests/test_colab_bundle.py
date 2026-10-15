"""Uji integritas, keamanan privasi, dan validitas hasil pada output/colab_bundle."""
import csv
import hashlib
import json
from pathlib import Path
import pytest

BUNDLE_DIR = Path("output/colab_bundle")
FORBIDDEN_COLUMNS = {
    "query_text",
    "summary_raw",
    "summary_clean",
    "party_name",
    "spm_number",
    "sp2d_number",
    "amount_rp",
    "haystack",
    "nominal",
}

EXPECTED_HEADER = [
    "query_id",
    "method",
    "config",
    "split",
    "source",
    "query_type",
    "noise_type",
    "n_relevant",
    "p5",
    "r10",
    "rr10",
    "hit5",
    "hit10",
    "zero_result",
    "latency_ms",
    "unjudged_in_top10",
]


def test_bundle_files_exist_and_manifest_valid():
    """Uji bahwa semua berkas bundle tersedia dan cocok dengan manifest SHA-256."""
    manifest_path = BUNDLE_DIR / "manifest.sha256"
    assert manifest_path.is_file(), "Berkas manifest.sha256 harus ada."

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) >= 5, "Manifest harus memuat minimal 5 berkas bundle."

    for line in lines:
        parts = line.split(maxsplit=1)
        assert len(parts) == 2, f"Format baris manifest tidak valid: {line}"
        expected_hash, filename = parts
        file_path = BUNDLE_DIR / filename
        assert file_path.is_file(), f"Berkas bundle tidak ditemukan: {filename}"

        # Hitung hash aktual
        h = hashlib.sha256()
        with open(file_path, "rb") as bf:
            while chunk := bf.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest()
        assert actual_hash == expected_hash, f"Hash SHA-256 tidak cocok untuk {filename}!"


def test_no_forbidden_columns():
    """Uji bahwa TIDAK ADA kolom teks arsip (privasi dinas terjaga ketat)."""
    for csv_name in ["per_query_results.csv", "tuning_results.csv"]:
        csv_path = BUNDLE_DIR / csv_name
        assert csv_path.is_file()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = set(next(reader))
            intersection = FORBIDDEN_COLUMNS.intersection(header)
            assert not intersection, f"Ditemukan kolom terlarang di {csv_name}: {intersection}"

    # Pastikan header per_query_results.csv persis sesuai spesifikasi
    with open(BUNDLE_DIR / "per_query_results.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == EXPECTED_HEADER, f"Header kolom tidak persis: {header}"


def test_methods_not_identical():
    """Uji bahwa tidak ada dua metode berbeda yang menghasilkan hasil per kueri identik sepenuhnya."""
    csv_path = BUNDLE_DIR / "per_query_results.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Kelompokkan vektor metrik per metode
    from collections import defaultdict
    method_vectors = defaultdict(list)
    for r in rows:
        key = f"{r['method']}_{r['config']}"
        # Ambil vektor metrik utama
        vector = (
            r["query_id"],
            float(r["p5"]),
            float(r["r10"]),
            float(r["rr10"]),
            int(r["hit5"]),
            int(r["zero_result"]),
        )
        method_vectors[key].append(vector)

    keys = list(method_vectors.keys())
    assert len(keys) >= 5, "Harus ada minimal 5 konfigurasi metode yang dievaluasi."

    # Periksa kesamaan antar tiap pasang metode berbeda
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            m1 = keys[i]
            m2 = keys[j]
            v1 = method_vectors[m1]
            v2 = method_vectors[m2]
            assert v1 != v2, f"Metode {m1} dan {m2} menghasilkan hasil per kueri identik sepenuhnya!"


def test_metrics_not_all_zero():
    """Uji bahwa tidak semua metrik bernilai nol (pipeline evaluasi bekerja nyata)."""
    csv_path = BUNDLE_DIR / "per_query_results.csv"
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total_p5 = sum(float(r["p5"]) for r in rows)
    total_rr10 = sum(float(r["rr10"]) for r in rows)
    total_hits = sum(int(r["hit5"]) for r in rows)

    assert total_p5 > 0.0, "Total Precision@5 seluruh kueri tidak boleh nol!"
    assert total_rr10 > 0.0, "Total RR@10 seluruh kueri tidak boleh nol!"
    assert total_hits > 0, "Harus ada setidaknya satu hit relevan yang ditemukan!"


def test_run_meta_contract():
    """Uji kontrak run_meta.json memenuhi syarat formal evaluasi akhir."""
    meta_path = BUNDLE_DIR / "run_meta.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta.get("mode") == "final", "Mode evaluasi harus 'final'."
    assert meta.get("seed") == 42, "Seed acak harus 42."
    assert meta.get("commit_sha"), "Commit SHA harus tercatat."
    assert meta.get("data_hash"), "Hash data arsip harus tercatat."
    assert meta.get("testset_hash"), "Hash set uji harus tercatat."
    assert "package_versions" in meta, "Versi paket ilmiah harus tercatat."
