"""Uji unit untuk SearchEvaluator dan run_comparative_evaluation."""
import pytest

from core.evaluation.evaluator import SearchEvaluator, run_comparative_evaluation
from core.search.index import SearchIndex
from core.search.matchers import create_matcher
from core.search.ranker import SearchHit
from scripts.evaluate import build_markdown_report, get_git_info
from tests.conftest import make_record


def test_search_evaluator_breakdowns():
    records = [
        make_record(1, summary="Renovasi pasar"),
        make_record(2, summary="Pembangunan jembatan"),
    ]
    index = SearchIndex.from_records(records)
    evaluator = SearchEvaluator(index)

    queries = [
        {
            "query_id": "Q1",
            "query_text": "pasar",
            "source": "nyata",
            "query_type": "topik",
            "noise_type": "tanpa_gangguan",
            "judgments": [
                {"archive_id": 1, "is_relevant": 1},
                {"archive_id": 2, "is_relevant": 0},
            ],
        },
        {
            "query_id": "Q2",
            "query_text": "jembatan",
            "source": "sintetis",
            "query_type": "topik",
            "noise_type": "typo",
            "judgments": [
                {"archive_id": 2, "is_relevant": 1},
            ],
        },
    ]

    def mock_search(q, top_n=10):
        if "pasar" in q:
            return [SearchHit(1, 0.9)]
        return [SearchHit(2, 0.8)]

    res = evaluator.evaluate_searcher("mock_search", mock_search, queries, top_n=5)
    assert res["searcher_name"] == "mock_search"
    assert res["overall"]["n_queries"] == 2
    assert res["overall"]["mrr_at_10"] == 1.0
    assert "nyata" in res["by_source"]
    assert "sintetis" in res["by_source"]
    assert "typo" in res["by_noise"]
    assert "mean_latency_ms" in res["overall"]


def test_run_comparative_evaluation():
    records = [
        make_record(1, summary="Pembayaran gaji pegawai"),
        make_record(2, summary="Pengadaan barang perlengkapan"),
    ]
    index = SearchIndex.from_records(records)
    matchers = {"levenshtein": create_matcher("levenshtein")}
    tuned_weights = {"levenshtein": {"summary": 0.8, "spm": 0.1, "party": 0.1}}

    queries = [
        {
            "query_id": "Q1",
            "query_text": "gaji pegawai",
            "source": "sintetis",
            "query_type": "topik",
            "noise_type": "tanpa_gangguan",
            "judgments": [{"archive_id": 1, "is_relevant": 1}],
        }
    ]

    res = run_comparative_evaluation(
        index=index,
        queries=queries,
        matchers=matchers,
        tuned_weights_by_matcher=tuned_weights,
    )

    assert "like_baseline" in res
    assert "levenshtein_equal" in res
    assert "levenshtein_tuned" in res
    assert res["levenshtein_tuned"]["overall"]["mrr_at_10"] > 0.0


def test_build_markdown_report_structure():
    mock_eval = {
        "like_baseline": {
            "overall": {
                "precision_at_5": 0.2, "recall_at_10": 0.5, "mrr_at_10": 0.4,
                "hit_rate_at_5": 0.6, "hit_rate_at_10": 0.7, "zero_result_queries": 1,
                "unjudged_in_top10": 0, "mean_latency_ms": 1.2, "p95_latency_ms": 2.0,
            },
            "by_source": {},
            "by_noise": {},
        }
    }
    manifest = {
        "timestamp": "2026-10-12T00:00:00Z",
        "git_commit_sha": "abc1234",
        "git_branch": "feat/testset-and-evaluation",
        "is_clean": True,
        "dump_sha256": "def5678",
        "testset_sha256": "789ghij",
        "testset_version": "v1.0.0",
        "seed": 42,
        "python_version": "3.14.0",
        "platform": "Windows-11",
        "n_test_queries": 28,
    }

    report = build_markdown_report(mock_eval, manifest)
    assert "# Laporan Evaluasi Ilmiah Temu Kembali Arsip" in report
    assert "Reproducibility Manifest" in report
    assert "LIKE Baseline" in report
    assert "Clean (Bersih)" in report


def test_get_git_info():
    sha, branch, is_clean = get_git_info()
    assert isinstance(sha, str)
    assert isinstance(branch, str)
    assert isinstance(is_clean, bool)
