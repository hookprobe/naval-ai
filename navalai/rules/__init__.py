"""Tier R: rules-as-code (BuildPlan Phase 6 — the moat; nothing open exists).

DISCLAIMER: ASSESSMENT AID — NOT CERTIFICATION. Checks implement simplified
interpretations of ISO 12217 (small-craft stability) and ISO 12215-5
(scantlings); numeric thresholds marked basis='approx' await parity review
against the licensed standard text by a qualified reviewer (Gate 6 bar).
"""

from __future__ import annotations

from dataclasses import dataclass

DISCLAIMER = "ASSESSMENT AID — NOT CERTIFICATION"


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    clause: str          # provenance of the bar
    basis: str           # 'standard' | 'approx' (pending parity review)
    passed: bool
    measured: float
    required: float
    unit: str
    note: str = ""


def report(findings: list[RuleFinding]) -> dict:
    return {
        "disclaimer": DISCLAIMER,
        "pass": all(f.passed for f in findings),
        "passed": sum(f.passed for f in findings),
        "total": len(findings),
        "findings": [f.__dict__ for f in findings],
        "unreviewed_bases": sorted({f.rule_id for f in findings if f.basis == "approx"}),
    }
