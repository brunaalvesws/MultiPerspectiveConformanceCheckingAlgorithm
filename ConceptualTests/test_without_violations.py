# -*- coding: utf-8 -*-
"""
Tests that the algorithm reports no violations when given inputs that are
fully compliant with the process and access models.

Uses the synthetic "no errors" logs in `ModelosLogsTeste/`.
"""

from __future__ import annotations

EXPECTED_CATEGORIES = [
    "Prohibited activity",
    "Unexpected activity",
    "Illegal activity",
    "Ignored mandatory activity",
    "Prohibited data access",
    "Unexpected data access",
    "Illegal data access",
    "Ignored mandatory data access",
]


def test_report_structure(report_without_violations):
    report = report_without_violations
    assert "overview" in report
    assert "violations" in report
    assert "activityDistribution" in report
    for category in EXPECTED_CATEGORIES:
        assert category in report["violations"], f"Missing category {category!r} in report"


def test_zero_violation_count(report_without_violations):
    overview = report_without_violations["overview"]
    assert overview["violationCount"] == 0, (
        f"Expected 0 violations, got {overview['violationCount']}. "
        f"Details: {report_without_violations['violations']}"
    )


def test_success_rate_is_one_hundred(report_without_violations):
    assert report_without_violations["overview"]["successRate"] == 100


def test_no_prohibited_activity(report_without_violations):
    assert report_without_violations["violations"]["Prohibited activity"] == []


def test_no_unexpected_activity(report_without_violations):
    assert report_without_violations["violations"]["Unexpected activity"] == []


def test_no_illegal_activity(report_without_violations):
    assert report_without_violations["violations"]["Illegal activity"] == []


def test_no_ignored_mandatory_activity(report_without_violations):
    assert report_without_violations["violations"]["Ignored mandatory activity"] == []


def test_no_prohibited_data_access(report_without_violations):
    assert report_without_violations["violations"]["Prohibited data access"] == []


def test_no_unexpected_data_access(report_without_violations):
    assert report_without_violations["violations"]["Unexpected data access"] == []


def test_no_illegal_data_access(report_without_violations):
    assert report_without_violations["violations"]["Illegal data access"] == []


def test_no_ignored_mandatory_data_access(report_without_violations):
    assert report_without_violations["violations"]["Ignored mandatory data access"] == []
