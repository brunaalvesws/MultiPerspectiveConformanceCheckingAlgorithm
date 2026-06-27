# -*- coding: utf-8 -*-
"""
Tests that the algorithm detects the seeded violations in
`Algorithm/DevelopmentFiles/`. The expected violations are documented in
`Algorithm/DevelopmentFiles/violationTestMapping.txt`. All violations refer
to the only case in the log (case index 0, "Demanda 0001").

These tests check that each expected violation is present in the report.
They do not require exact-count equality, so additional incidental
violations would not cause false failures, but each known violation must
be detected.
"""

from __future__ import annotations


# --- Small helpers ----------------------------------------------------------

def _instance_matches(value, expected: int) -> bool:
    """`concept:instance` is sometimes stored as an int and sometimes joined
    into a string in the report — accept both."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_instance_matches(v, expected) for v in value)
    try:
        return int(value) == expected
    except (TypeError, ValueError):
        return str(expected) in str(value).split(", ")


def _has(items, **expected):
    """Returns True if some dict in `items` matches all expected key/value
    pairs. For the `instance` key, both ints and "i1, i2" strings match."""
    for item in items:
        if not isinstance(item, dict):
            continue
        ok = True
        for key, want in expected.items():
            got = item.get(key)
            if key == "instance":
                if not _instance_matches(got, want):
                    ok = False
                    break
            else:
                if got != want:
                    ok = False
                    break
        if ok:
            return True
    return False


def _count(items, **expected):
    n = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        ok = True
        for key, want in expected.items():
            got = item.get(key)
            if key == "instance":
                if not _instance_matches(got, want):
                    ok = False
                    break
            else:
                if got != want:
                    ok = False
                    break
        if ok:
            n += 1
    return n


# --- Report shape -----------------------------------------------------------

EXPECTED_CATEGORIES = {
    "Prohibited activity",
    "Unexpected activity",
    "Illegal activity",
    "Ignored mandatory activity",
    "Prohibited data access",
    "Unexpected data access",
    "Illegal data access",
    "Ignored mandatory data access",
}


def test_report_structure(report_with_violations):
    report = report_with_violations
    assert "overview" in report
    assert "violations" in report
    assert "activityDistribution" in report
    assert set(report["violations"].keys()) == EXPECTED_CATEGORIES
    assert report["overview"]["violationCount"] > 0


# --- Activity-perspective violations ----------------------------------------

def test_prohibited_activity_elaborar_caso_de_teste(report_with_violations):
    """Elaborar caso de teste (instance 16) occurs without preceding
    Documentacao de requisitos funcionais — violates Precedence rule."""
    prohibited = report_with_violations["violations"]["Prohibited activity"]
    matches = [
        v for v in prohibited
        if "Precedence" in v.get("rule", "")
        and "Elaborar caso de teste" in v.get("rule", "")
        and _instance_matches(v.get("instance"), 16)
    ]
    assert matches, f"Expected Precedence violation on instance 16. Got: {prohibited}"


def test_unexpected_activity_teste_erro(report_with_violations):
    """TESTE ERRO (instance 2) is not declared in the process model."""
    unexpected = report_with_violations["violations"]["Unexpected activity"]
    assert _has(unexpected, name="TESTE ERRO", instance=2), (
        f"Expected unexpected activity 'TESTE ERRO' at instance 2. Got: {unexpected}"
    )


def test_illegal_activity_publicar_solucao_by_re3(report_with_violations):
    """Publicar solucao (instance 12) was done by re3, which is not in the
    organizational model team (only re7 and re10)."""
    illegal = report_with_violations["violations"]["Illegal activity"]
    assert _has(illegal, name="Publicar solucao", resource="re3", instance=12), (
        f"Expected illegal activity 'Publicar solucao' by 're3' at instance 12. Got: {illegal}"
    )


def test_ignored_mandatory_activity_review_da_entrega(report_with_violations):
    """Review da entrega was never executed, so both Existence[Review da entrega]
    and Response[Planejamento de entrega, Review da entrega] should be violated."""
    ignored = report_with_violations["violations"]["Ignored mandatory activity"]
    existence = [v for v in ignored if "Existence" in v.get("rule", "") and "Review da entrega" in v.get("rule", "")]
    response = [
        v for v in ignored
        if "Response" in v.get("rule", "")
        and "Planejamento de entrega" in v.get("rule", "")
        and "Review da entrega" in v.get("rule", "")
    ]
    assert existence, f"Expected Existence violation for Review da entrega. Got: {ignored}"
    assert response, f"Expected Response[Planejamento de entrega, Review da entrega] violation. Got: {ignored}"


# --- Data-access-perspective violations -------------------------------------

def test_prohibited_data_access_pf_read_on_atualizacao(report_with_violations):
    """A 'PF' read during 'Atualizacao de requisitos funcionais' (instance 1)
    is not allowed by the data access model."""
    prohibited = report_with_violations["violations"]["Prohibited data access"]
    matches = [
        v for v in prohibited
        if v.get("tool") == "PF"
        and v.get("operation") == "r"
        and v.get("activity") == "Atualizacao de requisitos funcionais"
        and _instance_matches(v.get("instance"), 1)
    ]
    assert matches, (
        f"Expected prohibited data access PF/read on Atualizacao de requisitos funcionais "
        f"instance 1. Got: {prohibited}"
    )


def test_unexpected_data_accesses_from_teste_erro(report_with_violations):
    """All data accesses linked to the unexpected activity TESTE ERRO
    (instance 2) should be reported as unexpected. The mapping describes 7."""
    unexpected = report_with_violations["violations"]["Unexpected data access"]
    teste_erro_accesses = [v for v in unexpected if v.get("activity") == "TESTE ERRO" and _instance_matches(v.get("instance"), 2)]
    assert len(teste_erro_accesses) == 7, (
        f"Expected 7 unexpected data accesses under TESTE ERRO (instance 2), "
        f"found {len(teste_erro_accesses)}: {teste_erro_accesses}"
    )


def test_illegal_data_access_executar_teste_re7(report_with_violations):
    """5 accesses of Executar teste (instance 20) were performed by re7,
    while the activity itself was performed by re10."""
    illegal = report_with_violations["violations"]["Illegal data access"]
    matches = [
        v for v in illegal
        if v.get("activity") == "Executar teste"
        and _instance_matches(v.get("instance"), 20)
        and v.get("resource") == "re7"
    ]
    assert len(matches) >= 5, (
        f"Expected at least 5 illegal accesses by re7 on Executar teste instance 20, "
        f"found {len(matches)}: {matches}"
    )


def test_illegal_data_access_pf_on_atualizacao(report_with_violations):
    """PF read on Atualizacao de requisitos funcionais (instance 1) by re10
    while the activity was done by re7."""
    illegal = report_with_violations["violations"]["Illegal data access"]
    matches = [
        v for v in illegal
        if v.get("activity") == "Atualizacao de requisitos funcionais"
        and v.get("tool") == "PF"
        and v.get("operation") == "r"
        and v.get("resource") == "re10"
        and _instance_matches(v.get("instance"), 1)
    ]
    assert matches, (
        f"Expected illegal PF/read access by re10 on Atualizacao de requisitos "
        f"funcionais instance 1. Got: {illegal}"
    )


def test_illegal_data_access_publicar_solucao_wrong_resources(report_with_violations):
    """Accesses on Publicar solucao (instance 12) by re6/re7 — activity was
    done by re3 (which is itself an illegal activity)."""
    illegal = report_with_violations["violations"]["Illegal data access"]
    matches = [
        v for v in illegal
        if v.get("activity") == "Publicar solucao"
        and _instance_matches(v.get("instance"), 12)
        and v.get("resource") in {"re6", "re7"}
    ]
    assert matches, (
        f"Expected illegal data accesses by re6/re7 on Publicar solucao "
        f"instance 12. Got: {illegal}"
    )


def test_illegal_data_access_gestao_by_re6_outside_team(report_with_violations):
    """Gestao r on Publicar solucao by re6 — re6 is not in the organizational model."""
    illegal = report_with_violations["violations"]["Illegal data access"]
    matches = [
        v for v in illegal
        if v.get("tool") == "Gestao"
        and v.get("activity") == "Publicar solucao"
        and v.get("resource") == "re6"
    ]
    assert matches, (
        f"Expected illegal Gestao access by re6 on Publicar solucao "
        f"(re6 not in team). Got: {illegal}"
    )


def test_ignored_mandatory_data_access_atualizacao(report_with_violations):
    """Gestao update and Requisito update in Atualizacao de requisitos funcionais
    (instance 1) were not performed but were mandatory."""
    ignored = report_with_violations["violations"]["Ignored mandatory data access"]
    gestao = [
        v for v in ignored
        if v.get("tool") == "Gestao"
        and v.get("operation") == "u"
        and v.get("activity") == "Atualizacao de requisitos funcionais"
        and _instance_matches(v.get("instance"), 1)
    ]
    requisito = [
        v for v in ignored
        if v.get("tool") == "Requisito"
        and v.get("operation") == "u"
        and v.get("activity") == "Atualizacao de requisitos funcionais"
        and _instance_matches(v.get("instance"), 1)
    ]
    assert gestao, f"Expected ignored mandatory Gestao/update on instance 1. Got: {ignored}"
    assert requisito, f"Expected ignored mandatory Requisito/update on instance 1. Got: {ignored}"
