"""Gate SWEEP — the seam properties, run as a gate.

WHY A SWEEP AND NOT MORE UNIT TESTS. On 2026-09-01 an end-to-end integration
audit found nineteen defects against a suite that was 2094 passed, 14 skipped,
0 failed. Not one was a row in `docs/GAP-REGISTER.md` and not one was a bug
inside a module: every one was an AGREEMENT BETWEEN TWO SUBSYSTEMS that
nothing checked — the descriptor layer measuring a hull the ladder does not
float, a propulsion lever credited to a hull that does not have it, a
catamaran served the monohull pool, a repair judged by bands it did not climb,
an ordinary brief crashing the optimizer.

A test pins a known answer. `scripts/gap_sweep.py` takes a PROPERTY that must
hold across a seam and sweeps it over a generated population, so it finds the
case nobody thought to write down. The suite is the ratchet; the sweep is the
search. This file is what makes the search run on every push.

THE ALLOW-LIST IS THE LEDGER IDIOM, deliberately. A known, measured, declared
finding is recorded here with its number and its reason; a NEW finding fails.
That is the same rule `data/gate-ledger.json` applies to red gates, and for
the same reason: "is anything broken that we did not already record?" is a
signal, and "is anything broken?" is a constant.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gap_sweep                                             # noqa: E402


#: Findings this tree has MEASURED, DECLARED and decided to carry, each with
#: the reason it is not being fixed today. A finding outside this list fails
#: the gate. Nothing above P3 may ever appear here: a P0/P1/P2 seam defect is
#: a fix, not a record.
DECLARED: dict = {
    # EMPTY since 2026-09-02, and the two entries that stood here are worth a
    # tombstone because both were CLOSED rather than carried:
    #
    #   ("meshclose", "split") — the split stern's surface did not close (57
    #   open edges at 80x16, 141 at 200x40). Root cause located by printing
    #   the unpaired edges: they were the two row-0 curves (the TOPS of the
    #   slot's inner walls — row 0 is the keel only on a hull without a
    #   split) plus the one transom-cap edge bridging the slot mouth. Closed
    #   by ONE ribbon quad strip between the port and starboard row-0 curves
    #   (the slot ceiling / wet deck) in `closed_mesh`; on every hull without
    #   a split both of its triangles have two identical vertices and are
    #   dropped, so the reference hull and 4 sampled hulls are BIT-IDENTICAL
    #   (same triangle counts, 5232/32284, as the docstring records).
    #
    #   ("stations", "split") — BM off 0.532% at 41 stations against the
    #   0.1% bar. Closed by shipping split hulls at 161 stations
    #   (`geometry._SPLIT_LADDER_STATIONS`; 161 = 4x40+1, the tree's aligned
    #   count) after clustered-41 grids were measured and REFUTED: each grid
    #   law fixed one corner of the (split_w, split_len) box and broke
    #   another. Uniform 161 measures <= 0.063% on every corner tried.
}

@pytest.fixture(scope="module")
def findings():
    return gap_sweep.run()


def test_no_new_seam_defect(findings):
    """Any finding not in DECLARED is a new seam defect."""
    new = [f for f in findings
           if (f.probe, f.detail.get("case", "")) not in DECLARED]
    assert not new, (
        "gap_sweep found seam defect(s) this tree has not declared:\n  "
        + "\n  ".join(f"[{f.severity}] {f.probe}/{f.subsystem}: {f.claim}"
                      f"\n        {f.evidence}" for f in new)
        + "\n\nFix it, or — if it is measured and deliberately carried — add "
          "it to tests/test_gap_sweep.py::DECLARED WITH ITS NUMBER AND ITS "
          "REASON. Do not widen a probe.")


def test_nothing_serious_is_merely_declared(findings):
    """A P0, P1 or P2 seam defect is a fix, never a record.

    The allow-list exists so a NEW finding is distinguishable from a known
    one — not so a serious one can be filed away. `data/gate-ledger.json`
    draws the same line for red gates.
    """
    for f in findings:
        if (f.probe, f.detail.get("case", "")) in DECLARED:
            assert f.severity == "P3", (
                f"{f.probe}/{f.claim} is declared at {f.severity}. Only P3 "
                f"may be carried; anything worse is fixed or the declaration "
                f"is wrong.")


def test_every_declaration_still_describes_a_real_finding(findings):
    """A stale allow-list entry is how a fixed defect becomes furniture.

    Same rule the ledger applies to a gate that recovered: "a GREEN gate still
    listed here -> FAIL (stale; delete the entry)".
    """
    live = {(f.probe, f.detail.get("case", "")) for f in findings}
    stale = sorted(set(DECLARED) - live)
    assert not stale, (
        f"{stale} no longer reproduce. If they were fixed, delete the "
        f"entry in the same commit; a declaration nobody rechecks is "
        f"wallpaper.")


def test_the_probes_all_ran(findings):
    """A probe that could not run is a FINDING, not a silent skip.

    `gap_sweep.run` converts an exception into a finding for exactly this
    reason (docs/LESSONS.md defect class 1: an unmeasurable metric scored as
    a passing one). This asserts the conversion is wired, so the sweep cannot
    report CLEAN because it crashed.
    """
    assert len(gap_sweep._PROBES) >= 13, (
        f"only {len(gap_sweep._PROBES)} probes are registered; the sweep's "
        f"value is its coverage of seams")
    broken = [f for f in findings if f.subsystem == "gap_sweep"]
    assert not broken, (
        "a probe raised instead of measuring:\n  "
        + "\n  ".join(f"{f.probe}: {f.evidence}" for f in broken))


def test_the_sweep_is_cheap_enough_to_run_on_every_push():
    """It is a gate, so it has to cost like one."""
    import time
    t0 = time.perf_counter()
    gap_sweep.run(selected={"declared", "cache", "twice"})
    assert time.perf_counter() - t0 < 30.0
