"""
runExperiment.py
================
Implements the performance evaluation protocol from the LaTeX section
"Metodologia de Avaliação de Desempenho e Escalabilidade".

Protocol
--------
1. Pilot Study
   - 5 warm-up runs (discarded) on the worst-case scenario:
     10 000 cases × Access violations × 30 % density.
   - 15 measured runs to estimate the sample standard deviation s.
   - Calculates the minimum sample size n:
       n = ceil( (Z_{α/2} · s / E)² )   with Z=1.96, E = 2 % of pilot mean.
   - Saves summary to ExperimentTestData/pilot_study.txt.

2. Full Experiment
   - 5 warm-up runs (discarded) per scenario (only on first execution).
   - n measured runs per scenario, resuming from wherever interrupted.
   - Results appended to ExperimentTestData/report{cases}{label}.txt.
   - Format per line:  <duration_s> <num_violations> <log_size>

Scenario matrix
---------------
Case sizes  : 10, 100, 1 000, 10 000
Labels      : SemViolacao | Processo10 | Processo30
              Acesso10    | Acesso30
              Recurso10   | Recurso30
              Inesperada10| Inesperada30

Usage
-----
    python runExperiment.py               # pilot (if missing) then full experiment
    python runExperiment.py --pilot       # pilot study only
    python runExperiment.py --cases 100   # only run 100-case scenarios
    python runExperiment.py --label Acesso30   # only run Acesso30 label
"""

import argparse
import math
import os
import statistics
import sys
import tempfile

# ── paths ────────────────────────────────────────────────────────────────────
ROOT_DIR      = os.path.dirname(os.path.abspath(__file__))
ALGORITHM_DIR = os.path.join(ROOT_DIR, 'Algorithm')
LOGS_DIR      = os.path.join(ROOT_DIR, 'ExperimentLogsAndModels')
OUTPUT_DIR    = os.path.join(ROOT_DIR, 'ExperimentOfficialData')

sys.path.insert(0, ALGORITHM_DIR)
from MultiConformanceAlgorithm import MultiperspectiveConformanceAlgorithm  # noqa: E402

# ── constants ─────────────────────────────────────────────────────────────────
WARMUP_RUNS = 5
PILOT_RUNS  = 15
Z_ALPHA_2   = 1.96
E_RELATIVE  = 0.02        # 2 % of the pilot mean

CASE_SIZES = [10, 100, 1000, 10000]

CASE_SUFFIX = {
    10:    'TenCases',
    100:   'HundredCases',
    1000:  'ThousandCases',
    10000: 'TenThousandCases',
}

ACCESS_MODEL = os.path.join(LOGS_DIR, 'DataAccessRestrictionModel.csv')

# Each entry: (report_label, process_variant, access_variant, declare_stem)
# Variants are suffixes appended to the case suffix when building file paths.
# An empty string means "use the clean (no-violation) file".
SCENARIOS = [
    # label            proc variant          access variant         declare stem
    ('SemViolacao',    '',                   '',                    'ProcessModel'),
    ('Processo10',     '',                   '',                    'ProcessModelActivityViolations10'),
    ('Processo30',     '',                   '',                    'ProcessModelActivityViolations30'),
    ('Acesso10',       '',                   'AccessViolations10',  'ProcessModel'),
    ('Acesso30',       '',                   'AccessViolations30',  'ProcessModel'),
    ('Recurso10',      'ResourceViolations10', 'ResourceViolations10', 'ProcessModel'),
    ('Recurso30',      'ResourceViolations30', 'ResourceViolations30', 'ProcessModel'),
    ('Inesperada10',   'UnexpectedViolations10', '',                'ProcessModelUnexpectedViolations'),
    ('Inesperada30',   'UnexpectedViolations30', '',                'ProcessModelUnexpectedViolations'),
]

# Worst-case scenario for the pilot study (Access violations, 30 %, 10 000 cases)
PILOT_SCENARIO = ('Acesso30', '', 'AccessViolations30', 'ProcessModel')
PILOT_CASES    = 10000


# ── path helpers ──────────────────────────────────────────────────────────────

def proc_path(case_suffix: str, variant: str = '') -> str:
    stem = f"{case_suffix}{variant}" if variant else case_suffix
    return os.path.join(LOGS_DIR, f"SyntheticProcessLog{stem}.xes")

def acc_path(case_suffix: str, variant: str = '') -> str:
    stem = f"{case_suffix}{variant}" if variant else case_suffix
    return os.path.join(LOGS_DIR, f"SyntheticDataAccessLog{stem}.xes")

def org_path(case_suffix: str) -> str:
    return os.path.join(LOGS_DIR, f"OrganizationalModel{case_suffix}.csv")

def decl_path(stem: str) -> str:
    return os.path.join(LOGS_DIR, f"{stem}.decl")

def report_path(n_cases: int, label: str) -> str:
    return os.path.join(OUTPUT_DIR, f"report{n_cases}{label}.txt")


# ── I/O helpers ───────────────────────────────────────────────────────────────

def count_measured_lines(path: str) -> int:
    """Count non-empty lines already written in a report file."""
    if not os.path.exists(path):
        return 0
    with open(path, 'r', encoding='utf-8') as fh:
        return sum(1 for line in fh if line.strip())


# ── execution ─────────────────────────────────────────────────────────────────

def _execute_runs(n_cases: int, label: str, proc_v: str, acc_v: str,
                  declare: str, n_runs: int, write_dir: str) -> list[float]:
    """
    Run the algorithm *n_runs* times writing report files to *write_dir*.
    Returns the list of execution times (seconds).
    """
    cs            = CASE_SUFFIX[n_cases]
    event_path_   = proc_path(cs, proc_v)
    access_path_  = acc_path(cs, acc_v)
    resource_path = org_path(cs)
    declare_path_ = decl_path(declare)

    prev_dir = os.getcwd()
    os.chdir(write_dir)
    times = []
    try:
        for i in range(n_runs):
            report = MultiperspectiveConformanceAlgorithm(
                eventPATH=event_path_,
                accessPATH=access_path_,
                resourcePATH=resource_path,
                declarePATH=declare_path_,
                accessmodelPATH=ACCESS_MODEL,
                consider_vacuity=True,
                cases=n_cases,
                report_label=label,
            )
            t = report['overview']['averageDuration']
            times.append(t)
            print(f"    run {i+1:>3}/{n_runs}:  {t:.4f} s  "
                  f"(violations={report['overview']['violationCount']})")
    finally:
        os.chdir(prev_dir)
    return times


def run_scenario(n_cases: int, label: str, proc_v: str, acc_v: str,
                 declare: str, n_runs: int, warmup: bool = False) -> list[float]:
    """
    Run one scenario.  If *warmup* is True the results are written to a
    temporary directory and discarded; otherwise they go to OUTPUT_DIR.
    """
    phase = 'warm-up (discarded)' if warmup else 'measured'
    print(f"  [{phase}]  cases={n_cases}  label={label}  n={n_runs}")

    if warmup:
        with tempfile.TemporaryDirectory() as tmp:
            return _execute_runs(n_cases, label, proc_v, acc_v, declare,
                                 n_runs, tmp)
    else:
        return _execute_runs(n_cases, label, proc_v, acc_v, declare,
                             n_runs, OUTPUT_DIR)


# ── pilot study ───────────────────────────────────────────────────────────────

def run_pilot() -> int:
    label, proc_v, acc_v, declare = PILOT_SCENARIO
    print(f"\n{'='*60}")
    print(f"PILOT STUDY  –  {PILOT_CASES} cases / {label}")
    print(f"{'='*60}")

    print(f"\n--- Warm-up ({WARMUP_RUNS} runs, discarded) ---")
    run_scenario(PILOT_CASES, label, proc_v, acc_v, declare,
                 WARMUP_RUNS, warmup=True)

    print(f"\n--- Measured ({PILOT_RUNS} runs) ---")
    times = run_scenario(PILOT_CASES, label, proc_v, acc_v, declare,
                         PILOT_RUNS, warmup=False)

    mean_t = statistics.mean(times)
    s      = statistics.stdev(times)
    E      = E_RELATIVE * mean_t
    n      = max(1, math.ceil((Z_ALPHA_2 * s / E) ** 2))

    print(f"\nPilot summary:")
    print(f"  mean = {mean_t:.4f} s")
    print(f"  s    = {s:.4f} s")
    print(f"  E    = {E:.4f} s  (= {E_RELATIVE*100:.0f}% of mean)")
    print(f"  n    = ceil((1.96 × {s:.4f} / {E:.4f})²) = {n}")

    pilot_file = os.path.join(OUTPUT_DIR, 'pilot_study.txt')
    with open(pilot_file, 'w', encoding='utf-8') as fh:
        fh.write(f"mean={mean_t}\n")
        fh.write(f"s={s}\n")
        fh.write(f"E={E}\n")
        fh.write(f"n={n}\n")
        fh.write("# raw times (s):\n")
        for t in times:
            fh.write(f"{t}\n")
    print(f"\nPilot data saved to {pilot_file}")
    return n


def load_n_from_pilot() -> int:
    pilot_file = os.path.join(OUTPUT_DIR, 'pilot_study.txt')
    if not os.path.exists(pilot_file):
        raise FileNotFoundError(
            "pilot_study.txt not found. Run `python runExperiment.py --pilot` first.")
    with open(pilot_file, 'r', encoding='utf-8') as fh:
        for line in fh:
            if line.startswith('n='):
                return int(line.split('=')[1])
    raise ValueError("Could not parse n from pilot_study.txt.")


# ── full experiment ────────────────────────────────────────────────────────────

def run_full_experiment(n: int,
                        filter_cases: int | None = None,
                        filter_label: str | None = None) -> None:
    print(f"\n{'='*60}")
    print(f"FULL EXPERIMENT  –  n = {n} measured runs per scenario")
    print(f"{'='*60}")

    sizes    = [filter_cases] if filter_cases else CASE_SIZES
    for n_cases in sizes:
        for label, proc_v, acc_v, declare in SCENARIOS:
            if filter_label and label != filter_label:
                continue

            rfile    = report_path(n_cases, label)
            existing = count_measured_lines(rfile)
            needed   = n - existing

            if needed <= 0:
                print(f"\n  SKIP  {n_cases:>6} cases / {label:<14}"
                      f"  (already {existing}/{n} runs)")
                continue

            print(f"\n{'─'*60}")
            print(f"  {n_cases:>6} cases / {label}   "
                  f"(existing={existing}, running={needed})")

            if existing == 0:
                print(f"\n  --- Warm-up ({WARMUP_RUNS} runs, discarded) ---")
                run_scenario(n_cases, label, proc_v, acc_v, declare,
                             WARMUP_RUNS, warmup=True)

            print(f"\n  --- Measured ({needed} run(s)) ---")
            run_scenario(n_cases, label, proc_v, acc_v, declare,
                         needed, warmup=False)

    print(f"\n{'='*60}")
    print("Experiment complete.")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run the multi-perspective conformance performance experiment.')
    parser.add_argument('--pilot',  action='store_true',
                        help='Run (or re-run) the pilot study only.')
    parser.add_argument('--cases',  type=int, choices=CASE_SIZES, default=None,
                        help='Restrict to a single case-size level.')
    parser.add_argument('--label',  type=str, default=None,
                        help='Restrict to a single scenario label (e.g. Acesso30).')
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.pilot:
        run_pilot()
    else:
        try:
            n = load_n_from_pilot()
            print(f"Loaded n={n} from pilot_study.txt")
        except FileNotFoundError:
            print("No pilot study found – running pilot first ...\n")
            n = run_pilot()

        run_full_experiment(n, filter_cases=args.cases, filter_label=args.label)
