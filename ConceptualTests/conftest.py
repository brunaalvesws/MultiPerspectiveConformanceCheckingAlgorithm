# -*- coding: utf-8 -*-
"""
Pytest configuration for the conformance checking algorithm tests.

- Adds the `Algorithm/` folder to `sys.path` so the algorithm modules can be
  imported by the tests.
- Provides path constants for the input files used by the tests.
- Provides session-scoped fixtures that execute the algorithm once per
  input combination and expose the resulting report to the tests.
- Chdirs into a temporary directory so the algorithm's side-effect report
  files (`report{cases}Acesso.txt`) do not pollute the workspace.
"""

import os
import sys
from pathlib import Path

import pytest

# Workspace and algorithm paths
TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent
ALGORITHM_DIR = REPO_ROOT / "Algorithm"
DEV_FILES_DIR = ALGORITHM_DIR / "DevelopmentFiles"
MODELOS_LOGS_TESTE_DIR = REPO_ROOT / "ModelosLogsTeste"

# Make the algorithm package importable
sys.path.insert(0, str(ALGORITHM_DIR))


@pytest.fixture(scope="session")
def tmp_run_dir(tmp_path_factory):
    """A temp directory used as CWD while running the algorithm, so the
    `report*.txt` side-effect files do not pollute the workspace."""
    return tmp_path_factory.mktemp("conformance_runs")


def _run_algorithm(process_log, access_log, org_model, declare_model,
                   access_model, cases, run_dir):
    """Run the algorithm with absolute paths from a temp working directory."""
    from MultiConformanceAlgorithm import MultiperspectiveConformanceAlgorithm

    cwd = os.getcwd()
    os.chdir(str(run_dir))
    try:
        return MultiperspectiveConformanceAlgorithm(
            eventPATH=str(process_log),
            accessPATH=str(access_log),
            resourcePATH=str(org_model),
            declarePATH=str(declare_model),
            accessmodelPATH=str(access_model),
            consider_vacuity=True,
            cases=cases,
        )
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="session")
def report_with_violations(tmp_run_dir):
    """Runs the algorithm against the DevelopmentFiles inputs which contain
    a known set of seeded violations (see DevelopmentFiles/violationTestMapping.txt)."""
    return _run_algorithm(
        process_log=DEV_FILES_DIR / "LogSinteticoProcessoOFICIALv4.xes",
        access_log=DEV_FILES_DIR / "LogSinteticoAcessoOFICIALv4.xes",
        org_model=DEV_FILES_DIR / "ModeloRecursosOFICIALv4.csv",
        declare_model=DEV_FILES_DIR / "Modelo_Log_Sintetico_OFICIAL.decl",
        access_model=DEV_FILES_DIR / "ModeloAcessoOFICIAL.csv",
        cases=1,
        run_dir=tmp_run_dir,
    )


@pytest.fixture(scope="session")
def report_without_violations(tmp_run_dir):
    """Runs the algorithm against the synthetic 'no errors' inputs in
    ModelosLogsTeste. No violations of any category are expected."""
    return _run_algorithm(
        process_log=MODELOS_LOGS_TESTE_DIR / "SyntheticProcessLogTenCasesNoErrors.xes",
        access_log=MODELOS_LOGS_TESTE_DIR / "SyntheticDataAccessLogTenCasesNoErrors.xes",
        org_model=MODELOS_LOGS_TESTE_DIR / "OrganizationalModelTenCases.csv",
        declare_model=MODELOS_LOGS_TESTE_DIR / "ProcessModel.decl",
        access_model=MODELOS_LOGS_TESTE_DIR / "DataAccessRestrictionModel.csv",
        cases=10,
        run_dir=tmp_run_dir,
    )


@pytest.fixture(scope="session")
def report_all_rules(tmp_run_dir):
    """Runs the algorithm against the synthetic 'no errors' logs but using
    `ProcessModelAllRules.decl`, which covers every DECLARE rule template
    supported by Declare4Py.

    The compliant log intentionally does not satisfy the broader set of
    rules added in the all-rules model, so this run is expected to surface
    violations from every rule template the algorithm supports."""
    return _run_algorithm(
        process_log=MODELOS_LOGS_TESTE_DIR / "SyntheticProcessLogTenCasesNoErrors.xes",
        access_log=MODELOS_LOGS_TESTE_DIR / "SyntheticDataAccessLogTenCasesNoErrors.xes",
        org_model=MODELOS_LOGS_TESTE_DIR / "OrganizationalModelTenCases.csv",
        declare_model=MODELOS_LOGS_TESTE_DIR / "ProcessModelAllRules.decl",
        access_model=MODELOS_LOGS_TESTE_DIR / "DataAccessRestrictionModel.csv",
        cases=10,
        run_dir=tmp_run_dir,
    )
