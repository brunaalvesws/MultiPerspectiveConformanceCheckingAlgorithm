# -*- coding: utf-8 -*-
"""
Exercises every DECLARE rule template supported by the algorithm by combining
the synthetic 'no errors' logs with `ProcessModelAllRules.decl`, which
includes all supported rule templates.

The compliant log intentionally does not satisfy the broader set of rules in
the all-rules model, so we expect at least one violation per supported
template. This validates that the algorithm correctly detects and classifies
violations of every rule type.

Templates checked (as they appear normalized by Declare4Py with spaces):

Prohibited-activity templates (rules that, when violated, mean an activity
happened that shouldn't have / a forbidden pattern occurred):
  - Precedence
  - Alternate Precedence
  - Chain Precedence
  - Not Response
  - Not Responded Existence
  - Not Precedence
  - Not Chain Response
  - Not Chain Precedence
  - Exclusive Choice
  - Exactly3
  - Absence2

Ignored-mandatory-activity templates (rules that, when violated, mean an
activity that should have happened did not):
  - Init
  - End
  - Existence1
  - Responded Existence
  - Response
  - Alternate Response
  - Chain Response
  - Choice
"""

from __future__ import annotations


PROHIBITED_TEMPLATES = [
    "Precedence",
    "Alternate Precedence",
    "Chain Precedence",
    "Not Response",
    "Not Responded Existence",
    "Not Precedence",
    "Not Chain Response",
    "Not Chain Precedence",
    "Exclusive Choice",
    "Exactly3",
    "Absence2",
]

MANDATORY_TEMPLATES = [
    "Init",
    "End",
    "Existence1",
    "Responded Existence",
    "Response",
    "Alternate Response",
    "Chain Response",
    "Choice",
]


def _rule_template(rule: str) -> str:
    """Extract the template portion (everything before the first '[')."""
    return rule.split("[", 1)[0].strip()


def _has_template(violations, template: str) -> bool:
    """Returns True if any violation entry uses exactly the given template.

    Matches against `template` as a full prefix, so 'Precedence' does not
    match 'Alternate Precedence' / 'Chain Precedence' / 'Not Precedence'."""
    for v in violations:
        if not isinstance(v, dict):
            continue
        rule = v.get("rule", "")
        if _rule_template(rule) == template:
            return True
    return False


def test_some_violations_are_detected(report_all_rules):
    """Sanity check: the all-rules model must produce violations on the
    otherwise-compliant log."""
    assert report_all_rules["overview"]["violationCount"] > 0


def test_all_prohibited_templates_detected(report_all_rules):
    """Each prohibited-activity rule template present in ProcessModelAllRules.decl
    must produce at least one violation classified under 'Prohibited activity'."""
    prohibited = report_all_rules["violations"]["Prohibited activity"]
    found = {t for t in PROHIBITED_TEMPLATES if _has_template(prohibited, t)}
    missing = set(PROHIBITED_TEMPLATES) - found
    assert not missing, (
        f"Prohibited templates not detected: {sorted(missing)}. "
        f"Templates observed: "
        f"{sorted({_rule_template(v['rule']) for v in prohibited if isinstance(v, dict)})}"
    )


def test_all_mandatory_templates_detected(report_all_rules):
    """Each mandatory-activity rule template present in ProcessModelAllRules.decl
    must produce at least one violation classified under 'Ignored mandatory activity'."""
    ignored = report_all_rules["violations"]["Ignored mandatory activity"]
    found = {t for t in MANDATORY_TEMPLATES if _has_template(ignored, t)}
    missing = set(MANDATORY_TEMPLATES) - found
    assert not missing, (
        f"Mandatory templates not detected: {sorted(missing)}. "
        f"Templates observed: "
        f"{sorted({_rule_template(v['rule']) for v in ignored if isinstance(v, dict)})}"
    )


def test_no_unknown_rule_classification(report_all_rules):
    """Every violated rule must end up in exactly one of the two activity
    categories. If a rule template falls through the FormatMapping logic,
    the algorithm raises an exception — this test makes that explicit."""
    prohibited = report_all_rules["violations"]["Prohibited activity"]
    mandatory = report_all_rules["violations"]["Ignored mandatory activity"]
    prohibited_templates = {_rule_template(v["rule"]) for v in prohibited if isinstance(v, dict)}
    mandatory_templates = {_rule_template(v["rule"]) for v in mandatory if isinstance(v, dict)}
    overlap = prohibited_templates & mandatory_templates
    assert not overlap, (
        f"The same rule template was classified in both categories: {overlap}"
    )
