"""Gate 6R — the parity review is RECORDED, not asserted.

This gate cannot be closed by code: it asks whether our numeric thresholds
match the licensed standard text, which needs a qualified human holding the
purchased documents. What code CAN do is refuse to call it closed unless the
verdict is attributable, and make sure a green 6R does not quietly bless
things no standard governs.

WHY THIS SUITE IS "6R-mech" AND GATE 6R ITSELF IS RED IN THE LEDGER.

Gap D8 (audit 2026-08-05): `review.py` states in its own docstring that "a
confirmation that cannot say WHO checked WHICH edition is not a review, it is
a rumour", and then `is_complete()` checked `reviewer` and `confirmed` and NOT
`editions` — whose two values both read "edition not recorded — set this".
The parity gate was green on a record that admits it cannot name the document
it checked.

`is_complete()` now requires every edition to be set and dated. That flips the
PARITY claim red, and it is recorded as red in `data/gate-ledger.json` with an
owner and a review-by date rather than softened (honesty rule 6). What is
still genuinely verifiable — that the record's MECHANICS work, that `basis`
routes from the record rather than from the source, that nothing unreviewed
leaks a 'standard' basis, and that our own practice values are not blessed by
a green gate — is what this suite tests, and it is green.

So: a test here asserting `is_complete()` would be asserting the defect. It
asserts the refusal instead, and asserts that a properly filled record WOULD
pass, so the clearing condition is executable and not just prose.
"""

from navalai.rules import DISCLAIMER, RuleFinding, report
from navalai.rules.review import (NOT_FROM_STANDARD, REVIEW, basis_for,
                                  edition_defects, is_complete)


def test_every_implemented_rule_has_a_review_verdict():
    implemented = {"R-CAT", "R-DFH", "R-GM", "R-OLH", "R-PBM", "R-TBM"}
    # A verdict is EITHER confirmed OR an explicit reason for not being. A rule
    # in neither set is an oversight; a rule in `unconfirmed` is a decision,
    # and three moved there on 2026-08-12 when the 2015 text was first read.
    verdicts = set(REVIEW["confirmed"]) | set(REVIEW["unconfirmed"])
    missing = implemented - verdicts
    assert not missing, f"no review verdict recorded for {sorted(missing)}"
    assert not (set(REVIEW["confirmed"]) & set(REVIEW["unconfirmed"])), (
        "a rule cannot be both confirmed and unconfirmed")
    for rule, why in REVIEW["unconfirmed"].items():
        assert len(why) > 80, f"{rule}: 'not confirmed' without a reason"


def test_the_record_names_a_reviewer_and_a_date():
    # A confirmation with no reviewer cannot be audited, so it does not count.
    # This is what stops the gate going green because someone edited a set.
    assert REVIEW["reviewer"] and REVIEW["date"]


def test_the_record_NOW_names_the_editions_it_checked():
    """INVERTED 2026-08-20, which is the outcome its predecessor asked for.

    This test used to assert `edition_defects()` was NON-empty and carried the
    instruction in its own failure message: "editions now look recorded — flip
    Gate 6R green in navalai/gates.py, delete its data/gate-ledger.json entry,
    and invert this test." All three were done in the same commit.

    MEASURED, both required standards now name the DATED edition the reviewer
    held, which is exactly the bar the ledger entry stated:

        ISO 12217-1 -> "ISO 12217-1:2015 (Third edition, 2015-10-15)"
        ISO 12215-5 -> "ISO 12215-5:2008(E), First edition, 2008-04
                        (withdrawn; replaced by ISO 12215-5:2019 —
                         do not mix editions)"

    The ledger watermark had gone stale at "0 editions recorded, of 2
    required" while the work was already done. A stale RED is as dishonest as
    a soft GREEN: it spends the reader's attention on a defect that no longer
    exists and teaches them to discount the gate ladder.

    WHAT THIS DOES NOT CLAIM. Gate 6R is threshold PARITY against the dated
    text, not verdict parity, and 12215-5:2008(E) is WITHDRAWN — the record
    says so itself. Naming an edition is not the same as holding a current
    one, and gap D9 ("reference designs + hand calculations exist, so Gate
    6R's threshold parity could become Gate 6's VERDICT parity") stays OPEN.
    """
    from navalai.rules.review import REVIEW as _R

    assert edition_defects() == [], edition_defects()
    assert is_complete()

    # and the editions must be DATED, not bare standard numbers — a set
    # someone edited to "ISO 12215-5" would satisfy a membership test and
    # is exactly what the original guard existed to refuse
    for name, text in _R["editions"].items():
        assert any(ch.isdigit() for ch in text.split(":")[-1][:6]), (
            f"{name} names no dated edition: {text!r}")
        assert text.startswith(name), (
            f"{name}'s entry does not name the standard it belongs to: {text!r}")

    # the withdrawn-edition warning must survive: mixing editions is the
    # failure mode this record exists to prevent
    assert "withdrawn" in _R["editions"]["ISO 12215-5"].lower()

    # a reviewer and a date remain required — an unauditable confirmation
    # must never be able to turn this green
    assert _R["reviewer"] and _R["date"]


def test_an_UNDATED_edition_is_still_refused():
    """The guard the inversion must not lose.

    The original test's whole purpose was that a bare standard NUMBER does
    not count as a recorded edition. Inverting the assertion would quietly
    drop that if it were not re-pinned here against verbatim input.
    """
    bare = dict(REVIEW, editions={"ISO 12217-1": "ISO 12217-1",
                                  "ISO 12215-5": "ISO 12215-5"})
    assert edition_defects(bare), (
        "a bare standard number was accepted as a dated edition")
    assert not is_complete(bare)

    missing = dict(REVIEW, editions={"ISO 12217-1": "ISO 12217-1:2015"})
    assert edition_defects(missing), "a MISSING standard was not reported"


def test_a_properly_filled_record_does_complete():
    """The clearing condition is executable, not prose."""
    filled = dict(REVIEW, editions={"ISO 12217-1": "ISO 12217-1:2022",
                                    "ISO 12215-5": "ISO 12215-5:2019"})
    assert edition_defects(filled) == []
    assert is_complete(filled)


def test_an_undated_edition_is_not_an_edition():
    # "ISO 12217-1" identifies a standard; only ":2022" identifies the text
    # somebody actually held and a later auditor can go and re-check.
    for bad in ("ISO 12217-1", "", "edition not recorded — set this", "TBD"):
        rec = dict(REVIEW, editions={"ISO 12217-1": bad})
        assert not is_complete(rec), bad


def test_basis_comes_from_the_record_not_the_source():
    assert basis_for("R-OLH") == "standard"       # confirmed vs the 2015 text
    assert basis_for("R-GM") == "approx", (
        "R-GM has no basis in ISO 12217-1:2015 at all — zero hits for an "
        "absolute metacentric requirement across 86 pages")
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
