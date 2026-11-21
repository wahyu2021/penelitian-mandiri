import csv
import json

import pytest

from scripts.evaluate_relevance_agreement import evaluate_relevance_agreement
from scripts.export_colab_bundle import build_agreement_summary


def write_ratings(path, values):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["query_id", "archive_id", "query_type", "is_relevant"])
        writer.writeheader()
        for idx, value in enumerate(values, 1):
            writer.writerow({"query_id": f"Q{idx:03d}", "archive_id": idx,
                             "query_type": "topik", "is_relevant": value})


def test_confusion_matrix_kappa_and_positive_agreement(tmp_path):
    main = tmp_path / "main.csv"
    second = tmp_path / "second.csv"
    write_ratings(main, ["1", "1", "1", "0", "0"])
    write_ratings(second, ["1", "1", "0", "0", "0"])

    result = evaluate_relevance_agreement(main, second)

    assert result["confusion_matrix"] == {
        "both_relevant": 2, "researcher_only_relevant": 1,
        "archivist_only_relevant": 0, "both_irrelevant": 2,
    }
    assert result["percentage_agreement"] == pytest.approx(0.8)
    assert result["relevant_class_agreement"] == pytest.approx(0.8)
    assert result["cohen_kappa"] == pytest.approx(8 / 13)


def test_bundle_recomputes_instead_of_using_stale_report(tmp_path):
    main = tmp_path / "main.csv"
    second = tmp_path / "second.csv"
    stale = tmp_path / "stale.json"
    write_ratings(main, ["1", "0"])
    write_ratings(second, ["1", "0"])
    stale.write_text(json.dumps({"percentage_agreement": 0.0}), encoding="utf-8")

    result = build_agreement_summary(main, second, stale)

    assert result["status"] == "complete"
    assert result["percentage_agreement"] == 1.0
    assert result["cohen_kappa"] == 1.0


def test_incomplete_ratings_do_not_produce_metrics(tmp_path):
    second = tmp_path / "second.csv"
    write_ratings(second, ["1", ""])

    result = build_agreement_summary(tmp_path / "missing.csv", second)

    assert result["status"] == "pending_second_rater"
    assert result["n_completed"] == 1
    assert result["cohen_kappa"] is None


def test_invalid_rating_rejected(tmp_path):
    main = tmp_path / "main.csv"
    second = tmp_path / "second.csv"
    write_ratings(main, ["1"])
    write_ratings(second, ["mungkin"])

    with pytest.raises(ValueError, match="0 atau 1"):
        evaluate_relevance_agreement(main, second)


def test_kappa_undefined_when_both_raters_use_one_class(tmp_path):
    main = tmp_path / "main.csv"
    second = tmp_path / "second.csv"
    write_ratings(main, ["1", "1"])
    write_ratings(second, ["1", "1"])

    result = evaluate_relevance_agreement(main, second)

    assert result["status"] == "complete_kappa_undefined"
    assert result["percentage_agreement"] == 1.0
    assert result["cohen_kappa"] is None
