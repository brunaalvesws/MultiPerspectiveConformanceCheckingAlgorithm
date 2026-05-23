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
from itertools import combinations
from typing import Optional

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
DATA_DIR    = os.path.join(ROOT_DIR, 'ExperimentTestData')

ALPHA = 0.05

CASE_SIZES = [10, 100, 1000, 10000]

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

    # Use clean samples (outliers removed) for inference
    clean = {lbl: d['clean'] for lbl, d in desc.items() if d.get('clean')}

    # 2 ─ Shapiro-Wilk
    print("\n2. Shapiro-Wilk normality test (α = 0.05)")
    normal = {}
    for lbl, vals in clean.items():
        w, p = shapiro_wilk(vals)
        is_normal = p >= ALPHA
        normal[lbl] = {'W': w, 'p': p, 'normal': is_normal}
        flag = 'normal' if is_normal else 'NOT normal'
        print(f"   {lbl:<16}  W={w:.4f}  p={p:.4f}  → {flag}")
    results['normality'] = normal

    all_normal = all(v['normal'] for v in normal.values())
    route = 'parametric' if all_normal else 'non-parametric'
    results['route'] = route
    print(f"\n   Route: {route.upper()}")

    groups = [clean[lbl] for lbl in clean]
    labels = list(clean.keys())

    # 3 ─ Omnibus test
    print(f"\n3. Omnibus test")
    if route == 'parametric':
        f_stat, p_omni = anova(*groups)
        results['omnibus'] = {'test': 'ANOVA', 'stat': f_stat, 'p': p_omni}
        print(f"   One-Way ANOVA:  F = {f_stat:.4f},  p = {p_omni:.6f}  {_sig(p_omni)}")
    else:
        h_stat, p_omni = kruskal_wallis(*groups)
        results['omnibus'] = {'test': 'Kruskal-Wallis', 'stat': h_stat, 'p': p_omni}
        print(f"   Kruskal-Wallis:  H = {h_stat:.4f},  p = {p_omni:.6f}  {_sig(p_omni)}")

    # 4 ─ Post-hoc
    if p_omni < ALPHA:
        print(f"\n4. Post-hoc ({route})")
        ph_data = {lbl: clean[lbl] for lbl in labels}
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
            d = cohens_d(clean[lbl_a], clean[lbl_b])
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
            cd   = cliffs_delta(clean[lbl_a], clean[lbl_b])
            a12  = vargha_delaney_a12(clean[lbl_a], clean[lbl_b])
            interp = _threshold_label(cd, CLIFFS_D_THRESHOLDS)
            pairwise[(lbl_a, lbl_b)] = {'cliff': cd, 'a12': a12,
                                        'interp': interp}
            print(f"     {lbl_a} vs {lbl_b}:  Δ = {cd:.4f}  A₁₂ = {a12:.4f}  ({interp})")
        results['effect_pairwise'] = pairwise

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
    args = parser.parse_args()

    sizes = [args.cases] if args.cases else CASE_SIZES
    all_results = []
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


if __name__ == '__main__':
    main()
