# -*- coding: utf-8 -*-
"""
Validates that every ExperimentLogsAndModels file combination used by
runExperiment.py produces violations ONLY of the designated type and NO
violations of any other type.

Scenario-to-expected-violation mapping
--------------------------------------
  SemViolacao    → no violations in any category
  Processo10/30  → only flow violations:    "Prohibited activity" / "Ignored mandatory activity"
  Acesso10/30    → only access violations:  "Prohibited data access" / "Ignored mandatory data access"
  Recurso10/30   → only resource violations:"Illegal activity" / "Illegal data access"
  Inesperada10/30→ only unexpected:         "Unexpected activity" / "Unexpected data access"

Case sizes covered
------------------
  OneCase (1), TenCases (10), HundredCases (100),
  ThousandCases (1 000) [slow], TenThousandCases (10 000) [slow]

  Slow tests (≥1 000 cases) are skipped by default.
  Run them with:  pytest --run-slow ConceptualTests/test_experiment_scenario_isolation.py

OneCase naming quirks
---------------------
  - SyntheticProcessLogOneCaseResourceViolation{pct}.xes  (singular "Violation")
  - No SyntheticDataAccessLogOneCaseResourceViolations{pct}.xes file exists;
    the clean access log is used instead.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import FrozenSet, Tuple

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TEST_DIR      = Path(__file__).resolve().parent
REPO_ROOT     = TEST_DIR.parent
ALGORITHM_DIR = REPO_ROOT / "Algorithm"
LOGS_DIR      = REPO_ROOT / "ExperimentLogsAndModels"
REPORT_DIR     = TEST_DIR / "report_outputs"
RESULTS_FILE   = TEST_DIR / "test_experiment_scenario_isolation_results.jsonl"

sys.path.insert(0, str(ALGORITHM_DIR))

_ACCESS_MODEL = LOGS_DIR / "DataAccessRestrictionModel.csv"


@pytest.fixture(scope="session", autouse=True)
def _reset_test_output_dirs() -> None:
    """Prepare the test output folders used by this scenario test."""
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        RESULTS_FILE.unlink()
    except FileNotFoundError:
        pass


def _append_scenario_result(n_cases: int, label: str, report: dict, report_path: Path) -> None:
    """Append one scenario's report into the ConceptualTests JSON results file."""
    record = {
        "n_cases": n_cases,
        "label": label,
        "report_path": str(report_path),
        "overview": report.get("overview", {}),
        "violations": report.get("violations", {}),
    }
    with RESULTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Violation-category groupings
# ---------------------------------------------------------------------------

_PROCESS_CATS   = frozenset({"Prohibited activity",     "Ignored mandatory activity"})
_ACCESS_CATS    = frozenset({"Prohibited data access",  "Ignored mandatory data access"})
_RESOURCE_CATS  = frozenset({"Illegal activity",        "Illegal data access"})
_UNEXPECTED_CATS = frozenset({"Unexpected activity",    "Unexpected data access"})
_ALL_CATS       = _PROCESS_CATS | _ACCESS_CATS | _RESOURCE_CATS | _UNEXPECTED_CATS


def _groups(label: str) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """Return *(expected, forbidden)* violation-category sets for *label*.

    *expected*  – categories that MUST contain at least one violation entry
                  (empty for SemViolacao).
    *forbidden* – categories that MUST be empty for the scenario to be
                  properly isolated.
    """
    if label == "SemViolacao":
        return frozenset(), _ALL_CATS
    if label.startswith("Processo"):
        return _PROCESS_CATS, _ACCESS_CATS | _RESOURCE_CATS | _UNEXPECTED_CATS
    if label.startswith("Acesso"):
        return _ACCESS_CATS, _PROCESS_CATS | _RESOURCE_CATS | _UNEXPECTED_CATS
    if label.startswith("Recurso"):
        return _RESOURCE_CATS, _PROCESS_CATS | _ACCESS_CATS | _UNEXPECTED_CATS
    if label.startswith("Inesperada"):
        return _UNEXPECTED_CATS, _PROCESS_CATS | _ACCESS_CATS | _RESOURCE_CATS
    raise ValueError(f"Unknown scenario label: {label!r}")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _proc(case_suffix: str, variant: str) -> Path:
    stem = f"{case_suffix}{variant}" if variant else case_suffix
    return LOGS_DIR / f"SyntheticProcessLog{stem}.xes"


def _acc(case_suffix: str, variant: str) -> Path:
    stem = f"{case_suffix}{variant}" if variant else case_suffix
    return LOGS_DIR / f"SyntheticDataAccessLog{stem}.xes"


def _org(case_suffix: str) -> Path:
    return LOGS_DIR / f"OrganizationalModel{case_suffix}.csv"


def _decl(case_suffix: str, stem: str) -> Path:
    """Resolve declare model path, inserting case_suffix for activity-specific models.
    
    Examples:
    - _decl("OneCase", "ProcessModelActivityViolations10")
      → "ProcessModelOneCaseActivityViolations10.decl"
    - _decl("HundredCases", "ProcessModelActivityViolations30")
      → "ProcessModelHundredCasesActivityViolations30.decl"
    - _decl("OneCase", "ProcessModelUnexpectedViolations")
      → "ProcessModelUnexpectedViolations.decl" (unchanged)
    - _decl("OneCase", "ProcessModel")
      → "ProcessModel.decl" (unchanged)
    """
    # Insert case_suffix for activity violation models
    if "ActivityViolations" in stem and case_suffix:
        # stem is like "ProcessModelActivityViolations{10|30}"
        # should become "ProcessModel{CaseSuffix}ActivityViolations{10|30}"
        base = "ProcessModel"
        rest = stem[len(base):]  # "ActivityViolations10" or "ActivityViolations30"
        stem = f"{base}{case_suffix}{rest}"
    
    return LOGS_DIR / f"{stem}.decl"


# ---------------------------------------------------------------------------
# Scenario definitions
# Each tuple: (n_cases, case_suffix, label, proc_variant, acc_variant, declare_stem)
# ---------------------------------------------------------------------------

# (n_cases, case_suffix, label, proc_variant, acc_variant, declare_stem)
_ScenarioTuple = Tuple[int, str, str, str, str, str]

_REGULAR_SCENARIOS = [
    # label              proc_variant            acc_variant              declare_stem
    ("SemViolacao",    "",                     "",                      "ProcessModel"),
    ("Processo10",     "",                     "",                      "ProcessModelActivityViolations10"),
    ("Processo30",     "",                     "",                      "ProcessModelActivityViolations30"),
    ("Acesso10",       "",                     "AccessViolations10",    "ProcessModel"),
    ("Acesso30",       "",                     "AccessViolations30",    "ProcessModel"),
    ("Recurso10",      "ResourceViolations10", "ResourceViolations10",  "ProcessModel"),
    ("Recurso30",      "ResourceViolations30", "ResourceViolations30",  "ProcessModel"),
    ("Inesperada10",   "UnexpectedViolations10", "",                    "ProcessModelUnexpectedViolations"),
    ("Inesperada30",   "UnexpectedViolations30", "",                    "ProcessModelUnexpectedViolations"),
]



_CASE_SUFFIX_MAP = {
    1:     "OneCase",
    10:    "TenCases",
    100:   "HundredCases",
    1000:  "ThousandCases",
    #10000: "TenThousandCases",
}

_SLOW_THRESHOLD = 1000  # n_cases >= this → @pytest.mark.slow


def _build_params() -> tuple[list, list]:
    params: list = []
    ids:    list = []

    for n_cases, case_suffix in [
        (1,     "OneCase"),
        (10,    "TenCases"),
        (100,   "HundredCases"),
        (1000,  "ThousandCases"),
        #(10000, "TenThousandCases"),
    ]:
        for label, pv, av, ds in _REGULAR_SCENARIOS:
            t = (n_cases, case_suffix, label, pv, av, ds)
            if n_cases >= _SLOW_THRESHOLD:
                params.append(pytest.param(t, marks=pytest.mark.slow))
            else:
                params.append(t)
            ids.append(f"{n_cases}-{case_suffix}-{label}")

    return params, ids


_ALL_PARAMS, _PARAM_IDS = _build_params()


# ---------------------------------------------------------------------------
# Session-scoped fixture: runs the algorithm once per scenario
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", params=_ALL_PARAMS, ids=_PARAM_IDS)
def experiment_scenario(request):
    """Run the algorithm for one (n_cases, scenario) combination and return
    a dict ``{'n_cases': int, 'label': str, 'report': dict}``.

    The fixture skips automatically when any required input file is absent.
    """
    n_cases, case_suffix, label, proc_v, acc_v, declare = request.param

    proc  = _proc(case_suffix, proc_v)
    acc   = _acc(case_suffix, acc_v)
    org   = _org(case_suffix)
    decl  = _decl(case_suffix, declare)  # Pass case_suffix for activity models

    missing = [str(p) for p in [proc, acc, org, decl, _ACCESS_MODEL] if not p.exists()]
    if missing:
        pytest.skip(f"Input file(s) not found: {', '.join(missing)}")

    from MultiConformanceAlgorithm import MultiperspectiveConformanceAlgorithm  # noqa: PLC0415

    run_dir = REPORT_DIR / f"exp_{n_cases}_{label}"
    run_dir.mkdir(parents=True, exist_ok=True)

    prev_cwd = os.getcwd()
    os.chdir(str(run_dir))
    try:
        report = MultiperspectiveConformanceAlgorithm(
            eventPATH=str(proc),
            accessPATH=str(acc),
            resourcePATH=str(org),
            declarePATH=str(decl),
            accessmodelPATH=str(_ACCESS_MODEL),
            consider_vacuity=True,
            cases=n_cases,
            report_label=label,
        )
    finally:
        os.chdir(prev_cwd)

    report_filename = f"report{n_cases}{label}.txt"
    report_path = run_dir / report_filename
    _append_scenario_result(n_cases, label, report, report_path)

    return {"n_cases": n_cases, "label": label, "report": report}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_cross_type_violations(experiment_scenario):
    """Categories that do NOT belong to the scenario's violation type must be
    completely empty (no violation entries)."""
    label      = experiment_scenario["label"]
    violations = experiment_scenario["report"]["violations"]
    _, forbidden = _groups(label)

    non_empty_forbidden = {
        cat: violations[cat]
        for cat in forbidden
        if violations.get(cat)
    }
    assert not non_empty_forbidden, (
        f"Scenario {label!r}: found violations in categories that should be "
        f"empty for this scenario type: {list(non_empty_forbidden.keys())}\n"
        f"Details: {non_empty_forbidden}"
    )


def test_expected_violations_are_detected(experiment_scenario):
    """For scenarios that inject a specific violation type, at least one
    category belonging to that type must contain violation entries.

    For SemViolacao, asserts that every violation category is empty and the
    overall violation count is zero.
    """
    label      = experiment_scenario["label"]
    report     = experiment_scenario["report"]
    violations = report["violations"]
    expected, _ = _groups(label)

    if not expected:
        # SemViolacao: the report must have zero violations across all categories
        non_empty = {cat: v for cat, v in violations.items() if v}
        assert not non_empty, (
            f"Scenario {label!r}: expected a completely clean report but found "
            f"violations in: {list(non_empty.keys())}\nDetails: {non_empty}"
        )
        assert report["overview"]["violationCount"] == 0, (
            f"Scenario {label!r}: violationCount should be 0 but is "
            f"{report['overview']['violationCount']}"
        )
        return

    assert any(violations.get(cat) for cat in expected), (
        f"Scenario {label!r}: expected at least one violation in categories "
        f"{sorted(expected)!r}, but all were empty.\n"
        f"Full violations dict: {violations}"
    )
