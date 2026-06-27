"""
analyzeResults.py
=================
Full statistical analysis pipeline for the multi-perspective conformance
checking performance evaluation, following the methodology described in
the LaTeX section "Procedimentos de Análise Estatística".

Pipeline (per case size)
------------------------
1. Load data from report files; parse duration values.
2. Descriptive statistics (mean, median, std, IQR, Q1, Q3) + Tukey outlier flag.
3. Shapiro-Wilk normality test (α = 0.05) on each group → route decision.
4. Omnibus test:
     • Parametric   → One-Way ANOVA
     • Non-parametric → Kruskal-Wallis
5. Post-hoc (only if omnibus p < 0.05):
     • Parametric   → Tukey HSD
     • Non-parametric → Dunn with Bonferroni correction
6. Effect size:
     • Global   → η²  (ANOVA)  or  ε²  (Kruskal-Wallis)
     • Pairwise → Cohen's d  (parametric)  or  Cliff's Δ + A₁₂ (non-parametric)
7. LaTeX table generation for all results.

Usage
-----
    python analyzeResults.py                  # analyse all case sizes
    python analyzeResults.py --cases 100      # single case size
    python analyzeResults.py --no-latex       # skip LaTeX output
    python analyzeResults.py --out results.tex  # custom LaTeX file
"""

import argparse
import math
import os
import sys
import warnings
from contextlib import contextmanager
from itertools import combinations
from typing import Optional
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

import numpy as np
from scipy import stats

# Optional heavy dependencies – degrade gracefully if absent
try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    warnings.warn("statsmodels not installed – Tukey HSD unavailable.", stacklevel=1)

try:
    import scikit_posthocs as sp
    HAS_POSTHOCS = True
except ImportError:
    HAS_POSTHOCS = False
    warnings.warn("scikit-posthocs not installed – Dunn test unavailable.", stacklevel=1)

# ── configuration ─────────────────────────────────────────────────────────────
ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(ROOT_DIR, 'ExperimentOfficialData')

ALPHA = 0.05

CASE_SIZES = [1, 10, 100, 1000] #10000

SCENARIO_LABELS = [
    'SemViolacao',
    'Processo10', 'Processo30',
    'Acesso10',   'Acesso30',
    'Recurso10',  'Recurso30',
    'Inesperada10', 'Inesperada30',
]

# Human-readable names for LaTeX tables
LABEL_DISPLAY = {
    'SemViolacao':   r'Sem Viola\c{c}\~ao (0\,\%)',
    'Processo10':    r'Fluxo 10\,\%',
    'Processo30':    r'Fluxo 30\,\%',
    'Acesso10':      r'Acesso 10\,\%',
    'Acesso30':      r'Acesso 30\,\%',
    'Recurso10':     r'Recurso 10\,\%',
    'Recurso30':     r'Recurso 30\,\%',
    'Inesperada10':  r'Inesperada 10\,\%',
    'Inesperada30':  r'Inesperada 30\,\%',
}

# Effect size thresholds (Cohen 1988 / standard)
COHENS_D_THRESHOLDS  = [(0.2, 'negligível'), (0.5, 'pequeno'), (0.8, 'médio'), (float('inf'), 'grande')]
CLIFFS_D_THRESHOLDS  = [(0.147, 'negligível'), (0.33, 'pequeno'), (0.474, 'médio'), (float('inf'), 'grande')]
ETA2_THRESHOLDS      = [(0.01, 'negligível'), (0.06, 'pequeno'), (0.14, 'médio'), (float('inf'), 'grande')]


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _parse_duration(token: str) -> float:
    """Accept both dot and comma as decimal separator."""
    return float(token.strip().replace(',', '.'))


def load_report(n_cases: int, label: str) -> list[float]:
    """
    Load execution times (seconds) from
    ExperimentTestData/report{n_cases}{label}.txt.
    Returns an empty list if the file does not exist or has no valid data.
    """
    path = os.path.join(DATA_DIR, f"report{n_cases}{label}.txt")
    if not os.path.exists(path):
        return []
    times = []
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            parts = line.strip().split()
            if not parts:
                continue
            try:
                times.append(_parse_duration(parts[0]))
            except ValueError:
                continue
    return times


def load_all(n_cases: int) -> dict[str, list[float]]:
    """Load data for every scenario at a given case size."""
    return {lbl: load_report(n_cases, lbl) for lbl in SCENARIO_LABELS}


# ── descriptive statistics ────────────────────────────────────────────────────

def descriptive(values: list[float]) -> dict:
    if not values:
        return {}
    arr = np.array(values, dtype=float)
    q1, q3   = np.percentile(arr, [25, 75])
    iqr      = q3 - q1
    fence_lo = q1 - 1.5 * iqr
    fence_hi = q3 + 1.5 * iqr
    outliers = arr[(arr < fence_lo) | (arr > fence_hi)]
    return {
        'n':        len(arr),
        'mean':     float(np.mean(arr)),
        'median':   float(np.median(arr)),
        'std':      float(np.std(arr, ddof=1)),
        'q1':       float(q1),
        'q3':       float(q3),
        'iqr':      float(iqr),
        'min':      float(np.min(arr)),
        'max':      float(np.max(arr)),
        'outliers': len(outliers),
        'clean':    arr[(arr >= fence_lo) & (arr <= fence_hi)].tolist(),
    }


# ── normality ─────────────────────────────────────────────────────────────────

def shapiro_wilk(values: list[float]) -> tuple[float, float]:
    """Return (statistic, p-value). Requires n ≥ 3."""
    if len(values) < 3:
        return (float('nan'), float('nan'))
    stat, p = stats.shapiro(values)
    return float(stat), float(p)


# ── omnibus tests ─────────────────────────────────────────────────────────────

def anova(*groups) -> tuple[float, float]:
    f_stat, p = stats.f_oneway(*groups)
    return float(f_stat), float(p)


def kruskal_wallis(*groups) -> tuple[float, float]:
    h_stat, p = stats.kruskal(*groups)
    return float(h_stat), float(p)


# ── effect sizes ──────────────────────────────────────────────────────────────

def eta_squared(groups: list[list[float]]) -> float:
    """η² from groups (one-way ANOVA)."""
    grand = np.concatenate([np.array(g) for g in groups])
    grand_mean = np.mean(grand)
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)
    ss_total   = np.sum((grand - grand_mean) ** 2)
    return float(ss_between / ss_total) if ss_total else 0.0


def epsilon_squared(h_stat: float, n_total: int, k: int) -> float:
    """ε² from Kruskal-Wallis H statistic."""
    denom = n_total - k
    return float((h_stat - k + 1) / denom) if denom else 0.0


def cohens_d(a: list[float], b: list[float]) -> float:
    """Pooled-variance Cohen's d."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float('nan')
    s_pool = math.sqrt(
        ((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1))
        / (n1 + n2 - 2)
    )
    return float((np.mean(a) - np.mean(b)) / s_pool) if s_pool else 0.0


def cliffs_delta(a: list[float], b: list[float]) -> float:
    """Cliff's Delta: P(X > Y) − P(Y > X)."""
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return float('nan')
    count = sum(
        (1 if xi > yj else -1 if xi < yj else 0)
        for xi in a for yj in b
    )
    return count / (n1 * n2)


def vargha_delaney_a12(a: list[float], b: list[float]) -> float:
    """Vargha-Delaney A₁₂ (= P(X > Y) + 0.5·P(X = Y))."""
    n1, n2 = len(a), len(b)
    if not n1 or not n2:
        return float('nan')
    count = sum(
        (1 if xi > yj else 0.5 if xi == yj else 0)
        for xi in a for yj in b
    )
    return count / (n1 * n2)


def _threshold_label(value: float, thresholds: list[tuple]) -> str:
    for limit, label in thresholds:
        if abs(value) <= limit:
            return label
    return thresholds[-1][1]


# ── post-hoc ──────────────────────────────────────────────────────────────────

def tukey_hsd_result(data: dict[str, list[float]]) -> Optional[object]:
    """Run Tukey HSD via statsmodels. Returns the result object or None."""
    if not HAS_STATSMODELS:
        return None
    import pandas as pd
    rows = [(t, lbl)
            for lbl, times in data.items()
            for t in times]
    df_vals = [r[0] for r in rows]
    df_grps = [r[1] for r in rows]
    return pairwise_tukeyhsd(df_vals, df_grps, alpha=ALPHA)


def dunn_bonferroni(data: dict[str, list[float]]) -> Optional[object]:
    """Run Dunn test with Bonferroni correction via scikit-posthocs."""
    if not HAS_POSTHOCS:
        return None
    import pandas as pd
    rows = [(t, lbl) for lbl, ts in data.items() for t in ts]
    df = pd.DataFrame(rows, columns=['value', 'group'])
    return sp.posthoc_dunn(df, val_col='value', group_col='group',
                           p_adjust='bonferroni')


# ── LaTeX helpers ─────────────────────────────────────────────────────────────

def _fmt(v, decimals=2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return r'\textemdash'
    return f"{v:.{decimals}f}"


def _sig(p: float) -> str:
    """Return significance stars."""
    if p < 0.001: return r'***'
    if p < 0.01:  return r'**'
    if p < 0.05:  return r'*'
    return 'ns'


@contextmanager
def redirect_stdout_to_file(path: str):
    """Temporarily redirect stdout to a text file."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    old_stdout = sys.stdout
    with open(path, 'w', encoding='utf-8') as fh:
        sys.stdout = fh
        try:
            yield
        finally:
            sys.stdout = old_stdout


# ── main analysis ─────────────────────────────────────────────────────────────

def analyse_case_size(n_cases: int) -> dict:
    """Run the full pipeline for one case size. Returns a results dict."""
    print(f"\n{'='*60}")
    print(f"Case size: {n_cases}")
    print(f"{'='*60}")

    raw = load_all(n_cases)
    available = {k: v for k, v in raw.items() if len(v) >= 3}

    if len(available) < 2:
        print("  Not enough data – skipping.")
        return {}

    results = {'n_cases': n_cases, 'descriptive': {}, 'normality': {},
               'route': None, 'omnibus': {}, 'posthoc': None,
               'effect_global': {}, 'effect_pairwise': {}}

    # 1 ─ Descriptive + outlier detection
    print("\n1. Descriptive statistics")
    desc = {}
    for lbl, vals in available.items():
        d = descriptive(vals)
        desc[lbl] = d
        print(f"   {lbl:<16}  n={d['n']}  mean={d['mean']:.3f}s  "
              f"median={d['median']:.3f}s  std={d['std']:.4f}s  "
              f"IQR={d['iqr']:.4f}  outliers={d['outliers']}")
    results['descriptive'] = desc

    # 2 ─ Shapiro-Wilk
    print("\n2. Shapiro-Wilk normality test (α = 0.05)")
    normal = {}
    for lbl, vals in available.items():
        w, p = shapiro_wilk(vals)
        is_normal = bool(np.isfinite(p) and p >= ALPHA)
        flag = 'normal' if is_normal else 'NOT normal'
        normal[lbl] = {'W': w, 'p': p, 'normal': is_normal}
        print(f"   {lbl:<16}  W={w:.4f}  p={p:.4f}  → {flag}")
    results['normality'] = normal

    if not normal:
        route = 'non-parametric'
    else:
        all_normal = all(v['normal'] for v in normal.values())
        route = 'parametric' if all_normal else 'non-parametric'
    results['route'] = route
    print(f"\n   Route: {route.upper()}")

    valid_labels = list(available.keys())
    groups = [available[lbl] for lbl in valid_labels]
    labels = valid_labels

    if len(groups) < 2:
        print("\n3. Omnibus test skipped (need at least two valid groups)")
        results['omnibus'] = {}
        results['posthoc'] = None
        results['effect_global'] = {}
        results['effect_pairwise'] = {}
        return results

    # 3 ─ Omnibus test
    print(f"\n3. Omnibus test")
    if route == 'parametric':
        f_stat, p_omni = anova(*groups)
        results['omnibus'] = {'test': 'ANOVA', 'stat': f_stat, 'p': p_omni}
        print(f"   One-Way ANOVA:  F = {f_stat:.4f},  p = {p_omni:.3e}  {_sig(p_omni)}")
    else:
        h_stat, p_omni = kruskal_wallis(*groups)
        results['omnibus'] = {'test': 'Kruskal-Wallis', 'stat': h_stat, 'p': p_omni}
        print(f"   Kruskal-Wallis:  H = {h_stat:.4f},  p = {p_omni:.3e}  {_sig(p_omni)}")

    # 4 ─ Post-hoc
    if p_omni < ALPHA:
        print(f"\n4. Post-hoc ({route})")
        ph_data = {lbl: available[lbl] for lbl in labels}
        if route == 'parametric':
            ph = tukey_hsd_result(ph_data)
            results['posthoc'] = {'method': 'Tukey HSD', 'result': ph}
            if ph:
                print(ph)
        else:
            ph = dunn_bonferroni(ph_data)
            results['posthoc'] = {'method': 'Dunn-Bonferroni', 'result': ph}
            if ph is not None:
                print(ph.to_string())
                plot_dunn_heatmap(
                    ph,
                    n_cases,
                    save_path=f"dunn_heatmap{n_cases}.png"
                )
    else:
        print(f"\n4. Post-hoc skipped (omnibus p ≥ {ALPHA})")

    # 5 ─ Effect size
    print(f"\n5. Effect size ({route})")
    if route == 'parametric':
        eta2 = eta_squared(groups)
        interpretation = _threshold_label(eta2, ETA2_THRESHOLDS)
        results['effect_global'] = {'metric': 'η²', 'value': eta2,
                                    'interpretation': interpretation}
        print(f"   η² = {eta2:.4f}  ({interpretation})")

        print("   Pairwise Cohen's d:")
        pairwise = {}
        for lbl_a, lbl_b in combinations(labels, 2):
            d = cohens_d(available[lbl_a], available[lbl_b])
            interp = _threshold_label(d, COHENS_D_THRESHOLDS)
            pairwise[(lbl_a, lbl_b)] = {'d': d, 'interp': interp}
            print(f"     {lbl_a} vs {lbl_b}:  d = {d:.4f}  ({interp})")
        results['effect_pairwise'] = pairwise

    else:
        n_total = sum(len(g) for g in groups)
        k       = len(groups)
        eps2    = epsilon_squared(h_stat, n_total, k)
        interpretation = _threshold_label(eps2, ETA2_THRESHOLDS)
        results['effect_global'] = {'metric': 'ε²', 'value': eps2,
                                    'interpretation': interpretation}
        print(f"   ε² = {eps2:.4f}  ({interpretation})")

        print("   Pairwise Cliff's Δ / A₁₂:")
        pairwise = {}
        for lbl_a, lbl_b in combinations(labels, 2):
            cd   = cliffs_delta(available[lbl_a], available[lbl_b])
            a12  = vargha_delaney_a12(available[lbl_a], available[lbl_b])
            interp = _threshold_label(cd, CLIFFS_D_THRESHOLDS)
            pairwise[(lbl_a, lbl_b)] = {'cliff': cd, 'a12': a12,
                                        'interp': interp}
            print(f"     {lbl_a} vs {lbl_b}:  Δ = {cd:.4f}  A₁₂ = {a12:.4f}  ({interp})")
        results['effect_pairwise'] = pairwise
        plot_cliffs_delta_heatmap(pairwise, n_cases, save_path=f"cliffs_delta_heatmap{n_cases}.png")

    return results


# ── LaTeX output ──────────────────────────────────────────────────────────────

def make_descriptive_table(all_results: list[dict]) -> str:
    """
    Generate a LaTeX longtable with mean ± std, median, IQR, n, outliers
    for every (case size, scenario) combination.
    """
    lines = []
    lines.append(r'\begin{longtable}{llrrrrrr}')
    lines.append(r'\caption{Estatísticas descritivas do tempo de execução (segundos). '
                 r'Outliers detectados pelo critério de Tukey ($1{,}5 \times \text{IQR}$).}'
                 r'\\')
    lines.append(r'\toprule')
    lines.append(r'Cases & Cenário & $n$ & Média & Mediana & DP & IQR & Outliers \\')
    lines.append(r'\midrule')
    lines.append(r'\endfirsthead')
    lines.append(r'\midrule')
    lines.append(r'Cases & Cenário & $n$ & Média & Mediana & DP & IQR & Outliers \\')
    lines.append(r'\midrule')
    lines.append(r'\endhead')
    lines.append(r'\midrule')
    lines.append(r'\multicolumn{8}{r}{\textit{continua na próxima página}} \\')
    lines.append(r'\endfoot')
    lines.append(r'\bottomrule')
    lines.append(r'\endlastfoot')

    for res in all_results:
        n_cases = res['n_cases']
        first   = True
        for lbl in SCENARIO_LABELS:
            d = res['descriptive'].get(lbl)
            if not d:
                continue
            case_col = str(n_cases) if first else ''
            first    = False
            disp     = LABEL_DISPLAY.get(lbl, lbl)
            lines.append(
                f"{case_col} & {disp} & {d['n']} & "
                f"${_fmt(d['mean'])}$ & ${_fmt(d['median'])}$ & "
                f"${_fmt(d['std'], 4)}$ & ${_fmt(d['iqr'], 4)}$ & "
                f"{d['outliers']} \\\\"
            )
        lines.append(r'\midrule')

    lines.append(r'\end{longtable}')
    return '\n'.join(lines)


def make_omnibus_table(all_results: list[dict]) -> str:
    lines = []
    lines.append(r'\begin{table}[ht]')
    lines.append(r'\centering')
    lines.append(r'\caption{Resultados dos testes omnibus de comparação de grupos.}')
    lines.append(r'\begin{tabular}{lllrrr}')
    lines.append(r'\toprule')
    lines.append(r'Cases & Rota & Teste & Estatística & $p$-valor & Decisão \\')
    lines.append(r'\midrule')

    for res in all_results:
        if not res.get('omnibus'):
            continue
        n_cases = res['n_cases']
        route   = res.get('route', '—')
        test    = res['omnibus']['test']
        stat    = res['omnibus']['stat']
        p       = res['omnibus']['p']
        stat_sym = 'F' if test == 'ANOVA' else 'H'
        decision = r'Rejeita $H_0$' if p < ALPHA else r'Não rejeita $H_0$'
        lines.append(
            f"{n_cases} & {route} & {test} & "
            f"${stat_sym}={_fmt(stat)}$ & ${_fmt(p, 4)}$ & {decision} \\\\"
        )

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    return '\n'.join(lines)


def make_effect_size_table(all_results: list[dict]) -> str:
    lines = []
    lines.append(r'\begin{table}[ht]')
    lines.append(r'\centering')
    lines.append(r'\caption{Magnitude do efeito global (tamanho do efeito).}')
    lines.append(r'\begin{tabular}{lllrl}')
    lines.append(r'\toprule')
    lines.append(r'Cases & Rota & Métrica & Valor & Interpretação \\')
    lines.append(r'\midrule')

    for res in all_results:
        eg = res.get('effect_global')
        if not eg:
            continue
        n_cases = res['n_cases']
        route   = res.get('route', '—')
        lines.append(
            f"{n_cases} & {route} & ${eg['metric']}$ & "
            f"${_fmt(eg['value'], 4)}$ & {eg['interpretation']} \\\\"
        )

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    return '\n'.join(lines)


def make_normality_table(all_results: list[dict]) -> str:
    lines = []
    lines.append(r'\begin{longtable}{llrrl}')
    lines.append(r'\caption{Teste de normalidade Shapiro-Wilk ($\alpha = 0{,}05$).} \\')
    lines.append(r'\toprule')
    lines.append(r'Cases & Cenário & $W$ & $p$-valor & Resultado \\')
    lines.append(r'\midrule')
    lines.append(r'\endfirsthead')
    lines.append(r'\midrule')
    lines.append(r'Cases & Cenário & $W$ & $p$-valor & Resultado \\')
    lines.append(r'\midrule')
    lines.append(r'\endhead')
    lines.append(r'\bottomrule')
    lines.append(r'\endlastfoot')

    for res in all_results:
        n_cases = res['n_cases']
        first   = True
        for lbl in SCENARIO_LABELS:
            nm = res.get('normality', {}).get(lbl)
            if not nm:
                continue
            case_col = str(n_cases) if first else ''
            first    = False
            disp     = LABEL_DISPLAY.get(lbl, lbl)
            outcome  = 'Normal' if nm['normal'] else r'\textbf{Não normal}'
            lines.append(
                f"{case_col} & {disp} & ${_fmt(nm['W'], 4)}$ & "
                f"${_fmt(nm['p'], 4)}$ & {outcome} \\\\"
            )
        lines.append(r'\midrule')

    lines.append(r'\end{longtable}')
    return '\n'.join(lines)


def build_latex_document(all_results: list[dict]) -> str:
    header = r"""\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{geometry}
\geometry{margin=2.5cm}

\begin{document}

\section*{Resultados da Avaliação de Desempenho e Escalabilidade}

"""
    footer = r"""
\end{document}
"""
    tables = [
        make_descriptive_table(all_results),
        r'\bigskip',
        make_normality_table(all_results),
        r'\bigskip',
        make_omnibus_table(all_results),
        r'\bigskip',
        make_effect_size_table(all_results),
    ]
    return header + '\n\n'.join(tables) + footer


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Statistical analysis of performance experiment results.')
    parser.add_argument('--cases', type=int, choices=CASE_SIZES, default=None,
                        help='Analyse only this case size.')
    parser.add_argument('--no-latex', action='store_true',
                        help='Skip LaTeX table generation.')
    parser.add_argument('--out', type=str, default=None,
                        help='Output LaTeX file path (default: stdout).')
    parser.add_argument('--log-file', type=str, default='analysis_output.txt',
                        help='File where the analysis prints will be written.')
    args = parser.parse_args()

    sizes = [args.cases] if args.cases else CASE_SIZES
    log_path = os.path.abspath(args.log_file)
    all_results = []

    with redirect_stdout_to_file(log_path):
        for n in sizes:
            res = analyse_case_size(n)
            if res:
                all_results.append(res)

        if not args.no_latex and all_results:
            print(f"\n{'='*60}")
            print("Generating LaTeX tables …")
            latex = build_latex_document(all_results)
            if args.out:
                with open(args.out, 'w', encoding='utf-8') as fh:
                    fh.write(latex)
                print(f"LaTeX saved to {args.out}")
            else:
                print("\n" + latex)
    boxplot()
    plot_execution_scalability_5curves()
    plot_density_slope()
    print(f"Analysis output saved to {log_path}")

# ── plot ────────────────────────────────────────────────────────────────────────

def boxplot():

    CASE_SIZES = [1, 10, 100, 1000]

    labels = [
        'SemViolacao',
        'Processo10',
        'Processo30',
        'Acesso10',
        'Acesso30',
        'Recurso10',
        'Recurso30',
        'Inesperada10',
        'Inesperada30'
    ]

    display = [
        'Sem\nViol.',
        'Fluxo\n10%',
        'Fluxo\n30%',
        'Acesso\n10%',
        'Acesso\n30%',
        'Recurso\n10%',
        'Recurso\n30%',
        'Inesp.\n10%',
        'Inesp.\n30%'
    ]

    colors = [
        "#CFCFCF",      # Sem violação

        "#6FA8DC",      # Fluxo
        "#6FA8DC",

        "#93C47D",      # Acesso
        "#93C47D",

        "#F6B26B",      # Recurso
        "#F6B26B",

        "#E06666",      # Inesperada
        "#E06666"
    ]

    fig, axs = plt.subplots(2, 2, figsize=(18, 10))

    axs = axs.flatten()

    for ax, n_cases in zip(axs, CASE_SIZES):

        raw = load_all(n_cases)

        values = []
        names = []
        box_colors = []

        for lbl, disp, cor in zip(labels, display, colors):
            if len(raw[lbl]) > 0:
                values.append(raw[lbl])
                names.append(disp)
                box_colors.append(cor)

        bp = ax.boxplot(
            values,
            patch_artist=True,
            showmeans=True,
            widths=0.6,
            medianprops=dict(color='black', linewidth=2),
            meanprops=dict(
                marker='D',
                markerfacecolor='red',
                markeredgecolor='red',
                markersize=5
            ),
            flierprops=dict(
                marker='o',
                markersize=4,
                alpha=0.6
            )
        )

        for patch, color in zip(bp['boxes'], box_colors):
            patch.set_facecolor(color)

        ax.set_title(f"{n_cases} cases", fontsize=13, weight="bold")
        ax.set_ylabel("Tempo (s)")
        ax.set_xticklabels(names)
        ax.grid(axis='y', alpha=0.3)

    fig.suptitle(
        "Distribuição dos tempos de execução por cenário experimental",
        fontsize=16,
        weight="bold"
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    plt.savefig(
        "boxplots_tempo_execucao.png",
        dpi=300,
        bbox_inches="tight"
    )

    # plt.show()



def plot_dunn_heatmap(
        dunn_df,
        n,
        alpha=0.05,
        save_path=None
):
    """
    Gera um heatmap dos p-valores ajustados do teste de Dunn-Bonferroni.

    Parameters
    ----------
    dunn_df : pandas.DataFrame
        Resultado retornado por scikit_posthocs.posthoc_dunn()
    """

    labels = list(dunn_df.columns)
    p = dunn_df.to_numpy(dtype=float)

    # Máscara para esconder a diagonal
    mask = np.eye(len(labels), dtype=bool)

    # Evita problemas no LogNorm
    plot_data = p.copy()
    plot_data[plot_data < 1e-300] = 1e-300

    plot_data = np.ma.masked_where(mask, plot_data)

    fig, ax = plt.subplots(figsize=(9,8))

    cmap = plt.cm.RdYlGn
    cmap.set_bad(color="white")

    im = ax.imshow(
        plot_data,
        cmap=cmap.reversed(),
        norm=LogNorm(vmin=1e-50, vmax=1)
    )

    # ticks
    ax.set_xticks(np.arange(len(labels)))
    ax.set_yticks(np.arange(len(labels)))

    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)

    # linhas da grade
    ax.set_xticks(np.arange(-.5, len(labels), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(labels), 1), minor=True)

    ax.grid(which="minor", color="gray", linewidth=0.5)

    ax.tick_params(which="minor", bottom=False, left=False)

    # escreve os p-valores
    for i in range(len(labels)):
        for j in range(len(labels)):

            if i == j:
                continue

            value = p[i, j]

            if value < 0.001:
                text = "<0.001"
            elif value > 0.999:
                text = "1.000"
            else:
                text = f"{value:.3f}"

            color = "white" if value < 0.01 else "black"

            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=8,
                color=color
            )

    cbar = fig.colorbar(im)

    cbar.set_label("p-valor ajustado (escala logarítmica)")
    title=f"Teste post-hoc de Dunn-Bonferroni - {n} Cases"
    ax.set_title(title, fontsize=14)

    plt.tight_layout()

    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    # plt.show()
    

def plot_cliffs_delta_heatmap(
        pairwise_results,
        n_cases,
        save_path=None
):
    """
    pairwise_results:
        dicionário produzido pelo código:
        {
            ('A','B'): {'cliff': ..., ...},
            ...
        }
    """
    
    labels = [
        'SemViolacao',
        'Processo10',
        'Processo30',
        'Acesso10',
        'Acesso30',
        'Recurso10',
        'Recurso30',
        'Inesperada10',
        'Inesperada30'
    ]

    n = len(labels)

    matrix = np.zeros((n, n))

    index = {g: i for i, g in enumerate(labels)}

    # diagonal
    np.fill_diagonal(matrix, 0)

    # preenche matriz
    for (a, b), res in pairwise_results.items():

        d = res["cliff"]

        i = index[a]
        j = index[b]

        matrix[i, j] = d
        matrix[j, i] = -d

    fig, ax = plt.subplots(figsize=(9,8))

    im = ax.imshow(
        matrix,
        cmap="RdBu_r",
        vmin=-1,
        vmax=1
    )

    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))

    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)

    # grade
    ax.set_xticks(np.arange(-.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-.5, n, 1), minor=True)

    ax.grid(which="minor", color="gray", linewidth=0.5)

    ax.tick_params(which="minor", bottom=False, left=False)

    # escreve os valores
    for i in range(n):
        for j in range(n):

            if i == j:
                txt = "—"
            else:
                txt = f"{matrix[i,j]:.2f}"

            cor = "white" if abs(matrix[i,j]) > 0.55 else "black"

            ax.text(
                j,
                i,
                txt,
                ha="center",
                va="center",
                fontsize=8,
                color=cor
            )

    cbar = plt.colorbar(im)

    cbar.set_label("Cliff's Delta (Δ)")

    cbar.set_ticks([-1,-0.5,0,0.5,1])
    
    title=f"Cliff's Delta (Tamanho do efeito) - {n_cases} Cases"

    ax.set_title(title, fontsize=14)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    # plt.show()

def plot_execution_scalability_5curves():

    CASE_SIZES = [1, 10, 100, 1000]

    groups = {
        "Sem violação": ["SemViolacao"],
        "Fluxo": ["Processo10", "Processo30"],
        "Acesso": ["Acesso10", "Acesso30"],
        "Recurso": ["Recurso10", "Recurso30"],
        "Inesperada": ["Inesperada10", "Inesperada30"]
    }

    colors = {
        "Sem violação": "black",
        "Fluxo": "#1f77b4",
        "Acesso": "#2ca02c",
        "Recurso": "#ff7f0e",
        "Inesperada": "#d62728"
    }

    markers = {
        "Sem violação": "o",
        "Fluxo": "s",
        "Acesso": "^",
        "Recurso": "D",
        "Inesperada": "X"
    }

    plt.figure(figsize=(10,6))

    for group_name, scenarios in groups.items():

        means = []
        ci95 = []

        for cases in CASE_SIZES:

            values = []

            for scenario in scenarios:
                values.extend(load_all(cases)[scenario])

            values = np.array(values)

            mean = np.mean(values)

            std = np.std(values, ddof=1)

            sem = std / np.sqrt(len(values))

            ci = 1.96 * sem

            means.append(mean)
            ci95.append(ci)

        plt.errorbar(
            CASE_SIZES,
            means,
            yerr=ci95,
            color=colors[group_name],
            marker=markers[group_name],
            linewidth=2.5,
            markersize=8,
            capsize=4,
            label=group_name
        )

    plt.xscale("log")

    # Eu também colocaria o eixo Y em log
    plt.yscale("log")

    plt.xticks(CASE_SIZES, CASE_SIZES)

    plt.xlabel("Número de cases", fontsize=12)
    plt.ylabel("Tempo médio de execução (s)", fontsize=12)

    plt.title(
        "Escalabilidade do algoritmo por tipo de violação",
        fontsize=15,
        weight="bold"
    )

    plt.grid(True, which="both", linestyle="--", alpha=0.35)

    plt.legend(
        title="Tipo de cenário",
        fontsize=11,
        title_fontsize=11
    )

    plt.tight_layout()

    plt.savefig(
        "escalabilidade_5_curvas.png",
        dpi=300,
        bbox_inches="tight"
    )

    # plt.show()
    

def plot_density_slope():

    CASE_SIZES = [1, 10, 100, 1000]

    scenarios = {
        "Fluxo": ("Processo10", "Processo30"),
        "Acesso": ("Acesso10", "Acesso30"),
        "Recurso": ("Recurso10", "Recurso30"),
        "Inesperada": ("Inesperada10", "Inesperada30")
    }

    colors = {
        "Fluxo": "#1f77b4",
        "Acesso": "#2ca02c",
        "Recurso": "#ff7f0e",
        "Inesperada": "#d62728"
    }

    markers = {
        "Fluxo": "s",
        "Acesso": "^",
        "Recurso": "D",
        "Inesperada": "o"
    }

    fig, axs = plt.subplots(2, 2, figsize=(11,8))

    axs = axs.flatten()

    for ax, cases in zip(axs, CASE_SIZES):

        data = load_all(cases)

        for nome, (g10, g30) in scenarios.items():

            m10 = np.mean(data[g10])
            m30 = np.mean(data[g30])

            ci10 = 1.96*np.std(data[g10],ddof=1)/np.sqrt(len(data[g10]))
            ci30 = 1.96*np.std(data[g30],ddof=1)/np.sqrt(len(data[g30]))

            ax.plot(
                [0,1],
                [m10,m30],
                color=colors[nome],
                linewidth=2.5,
                marker=markers[nome],
                markersize=8,
                label=nome
            )

            ax.errorbar(
                [0,1],
                [m10,m30],
                yerr=[ci10,ci30],
                fmt="none",
                color=colors[nome],
                capsize=4,
                linewidth=1.5
            )

        ax.set_xticks([0,1])
        ax.set_xticklabels(["10%","30%"])

        ax.set_title(f"{cases} cases",weight="bold")

        ax.grid(axis="y",linestyle="--",alpha=0.3)

    fig.suptitle(
        "Impacto da densidade de inconformidades",
        fontsize=16,
        weight="bold"
    )

    fig.text(
        0.04,
        0.5,
        "Tempo médio de execução (s)",
        va="center",
        rotation="vertical",
        fontsize=12
    )

    handles, labels = axs[0].get_legend_handles_labels()

    fig.text(
        0.5,
        0.07,
        "Densidade de inconformidades",
        ha="center",
        fontsize=12
    )

    leg = fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=4,
        frameon=False
    )

    plt.tight_layout(rect=[0.05, 0.12, 1, 0.93])

    plt.savefig(
        "slope_density.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

if __name__ == '__main__':
    main()


