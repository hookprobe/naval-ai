"""Gate 6R — the parity review is RECORDED, not asserted.

This gate cannot be closed by code: it asks whether our numeric thresholds
match the licensed standard text, which needs a qualified human holding the
purchased documents. What code CAN do is refuse to call it closed unless the
verdict is attributable, and make sure a green 6R does not quietly bless
things no standard governs.
"""

from navalai.rules import DISCLAIMER, RuleFinding, report
from navalai.rules.review import (NOT_FROM_STANDARD, REVIEW, basis_for,
                                  is_complete)


def test_every_implemented_rule_has_a_review_verdict():
    implemented = {"R-CAT", "R-DFH", "R-GM", "R-OLH", "R-PBM", "R-TBM"}
    missing = implemented - set(REVIEW["confirmed"])
    assert not missing, f"no review verdict recorded for {sorted(missing)}"


def test_the_record_is_attributable():
    # A confirmation with no reviewer cannot be audited, so it does not count.
    # This is what stops the gate going green because someone edited a set.
    assert is_complete()
    assert REVIEW["reviewer"] and REVIEW["date"]


def test_basis_comes_from_the_record_not_the_source():
    assert basis_for("R-GM") == "standard"
    assert basis_for("R-NOT-A-RULE") == "approx", (
        "an unreviewed rule must never report basis='standard'")


def test_no_unreviewed_bases_leak_into_a_report():
    findings = [RuleFinding(r, "clause", basis_for(r), True, 1.0, 0.0, "m")
                for r in sorted(REVIEW["confirmed"])]
    assert report(findings)["unreviewed_bases"] == []


def test_a_green_gate_still_is_not_certification():
    # Honesty rule 5. Parity on thresholds does not make an assessment aid a
    # certification: CE marking needs a Notified Body, and we implement a few
    # clauses, not a standard.
    assert "NOT CERTIFICATION" in DISCLAIMER
    assert "does not" in REVIEW["scope"].lower() or "only" in REVIEW["scope"].lower()


def test_our_own_practice_values_are_not_blessed_by_this_gate():
    # These are OURS. No ISO clause governs them, so a reviewed rules tier must
    # not be read as having confirmed them.
    from navalai import limits
    for name in NOT_FROM_STANDARD:
        assert hasattr(limits, name)
        assert name not in REVIEW["confirmed"]


def test_recorded_interpretations_survive_the_green_gate():
    # The packet raised that categories A and B both carry hs = 4.0 m. A
    # blanket "confirmed" does not resolve it — the senses differ (A is a lower
    # bound, B an upper), and the table stores one scalar. Keep it visible.
    assert "R-CAT" in REVIEW["interpretations"]
    assert "lower bound" in REVIEW["interpretations"]["R-CAT"]
