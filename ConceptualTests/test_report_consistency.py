# -*- coding: utf-8 -*-
"""
Internal consistency tests for the conformance report.

These tests do not depend on the specific input files — they only verify
that the algorithm's report is internally coherent for every fixture
(`report_with_violations`, `report_without_violations`, `report_all_rules`).

What is checked:
  - The top-level shape of the report (`overview`, `violations`,
    `activityDistribution`).
  - `overview.violationCount` equals the total number of violation entries
    across all categories.
  - `overview.successRate` is in [0, 100] and follows the formula
    `(log_size - violations) * 100 / log_size`, derived back from the
    reported values.
  - `overview.averageDuration` is a non-negative number.
  - `activityDistribution` contains non-negative integer counts only.
  - Every violation entry is a dict carrying the schema documented in
    `FormatMapping.non_conformance_patterns_mapping` for its category.
"""

from __future__ import annotations

import math

import pytest


CATEGORY_REQUIRED_KEYS = {
    "Prohibited activity":         {"case_id", "rule", "instance"},
    "Unexpected activity":         {"name", "case_id", "instance", "resource"},
    "Illegal activity":            {"name", "case_id", "resource", "instance"},
    "Ignored mandatory activity":  {"case_id", "rule", "instance"},
    "Prohibited data access":      {"case_id", "tool", "activity", "operation", "instance"},
    "Unexpected data access":      {"tool", "operation", "case_id", "instance", "resource", "activity"},
    # Illegal data access has two sources with different schemas;
    # 'resource' is always present, 'designated_resource' only on the
    # access-violations source.
    "Illegal data access":         {"case_id", "tool", "activity", "operation", "instance", "resource"},
    "Ignored mandatory data access": {"case_id", "tool", "activity", "operation", "instance"},
}


ALL_REPORTS = ["report_with_violations", "report_without_violations", "report_all_rules"]


@pytest.fixture(params=ALL_REPORTS)
def any_report(request):
    """Parametrized fixture that yields every report in the test session,
    so consistency checks run on each of them."""
    return request.getfixturevalue(request.param)


# --- Top-level shape --------------------------------------------------------

def test_top_level_keys(any_report):
    assert set(any_report.keys()) >= {"overview", "violations", "activityDistribution"}


def test_overview_keys(any_report):
    overview = any_report["overview"]
    assert set(overview.keys()) == {"successRate", "averageDuration", "violationCount"}


def test_violation_categories(any_report):
    assert set(any_report["violations"].keys()) == set(CATEGORY_REQUIRED_KEYS.keys())


# --- Overview numerics ------------------------------------------------------

def test_violation_count_equals_sum_of_categories(any_report):
    total = sum(len(items) for items in any_report["violations"].values())
    assert any_report["overview"]["violationCount"] == total


def test_average_duration_is_non_negative(any_report):
    duration = any_report["overview"]["averageDuration"]
    assert isinstance(duration, (int, float))
    assert duration >= 0


def test_success_rate_in_valid_range(any_report):
    rate = any_report["overview"]["successRate"]
    assert isinstance(rate, (int, float))
    assert 0 <= rate <= 100


def test_success_rate_matches_formula(any_report):
    """`successRate = (log_size - violations) * 100 / log_size`.

    Without log_size in the report, we invert the formula to recover an
    integer log_size and require it to be a positive whole number that is
    consistent with the reported success rate."""
    rate = any_report["overview"]["successRate"]
    violations = any_report["overview"]["violationCount"]
    if violations == 0:
        assert rate == 100
        return
    # rate < 100 implies (100 - rate) > 0
    assert rate < 100
    log_size = violations * 100.0 / (100 - rate)
    assert math.isclose(log_size, round(log_size), abs_tol=1e-6), (
        f"Recovered log_size {log_size} is not a whole number"
    )
    assert round(log_size) > violations


# --- Activity distribution --------------------------------------------------

def test_activity_distribution_counts_are_non_negative_integers(any_report):
    distribution = any_report["activityDistribution"]
    assert isinstance(distribution, dict)
    assert distribution, "activityDistribution should not be empty"
    for activity, count in distribution.items():
        assert isinstance(activity, str)
        assert isinstance(count, int)
        assert count >= 0


# --- Per-category schema ----------------------------------------------------

@pytest.mark.parametrize("category,required_keys", list(CATEGORY_REQUIRED_KEYS.items()))
def test_violation_entries_have_required_keys(any_report, category, required_keys):
    """Every dict in every category must carry at least the documented keys."""
    for entry in any_report["violations"][category]:
        assert isinstance(entry, dict), (
            f"Entry in {category!r} is not a dict: {entry!r}"
        )
        missing = required_keys - set(entry.keys())
        assert not missing, (
            f"Entry in {category!r} is missing keys {missing}: {entry!r}"
        )


def test_illegal_data_access_designated_resource_consistency(any_report):
    """`Illegal data access` may contain two shapes:
      - entries originating from IllegalTeamAccess (no `designated_resource`)
      - entries originating from access_violations['Resource'] (with
        `designated_resource`)
    When `designated_resource` is present, it must differ from `resource`
    (otherwise it would not be a violation)."""
    for entry in any_report["violations"]["Illegal data access"]:
        if "designated_resource" in entry:
            assert entry["designated_resource"] != entry["resource"], (
                f"designated_resource equals resource in illegal data access entry: {entry!r}"
            )
