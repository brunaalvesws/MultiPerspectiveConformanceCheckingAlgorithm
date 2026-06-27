import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import analyzeResults


def test_route_is_non_parametric_when_no_valid_clean_group_exists(monkeypatch):
    monkeypatch.setattr(
        analyzeResults,
        "load_all",
        lambda n_cases: {
            "SemViolacao": [1, 2, 3, 4, 5],
            "Processo10": [1, 2, 3, 4, 5],
        },
    )

    def fake_descriptive(values):
        return {
            "n": len(values),
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "q1": 0.0,
            "q3": 0.0,
            "iqr": 0.0,
            "min": 0.0,
            "max": 0.0,
            "outliers": 0,
            "clean": [],
        }

    monkeypatch.setattr(analyzeResults, "descriptive", fake_descriptive)

    result = analyzeResults.analyse_case_size(1)

    assert result["route"] == "non-parametric"
