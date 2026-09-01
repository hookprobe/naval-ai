"""The CLI face of the product — which had NO TESTS AT ALL until 2026-09-02.

`docs/PRODUCTION_CORE.md` lists `navalai/design_report.py` as core, "the CLI
face". Nothing in `tests/` imported it, and that is exactly why the defect
below survived: a flag can be declared, documented in `--help`, and never read,
and no amount of green elsewhere will notice.
"""
from __future__ import annotations

import io
import contextlib

import pytest

from navalai import design_report


def _run(argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = design_report.main(argv)
    return code, buf.getvalue()


_BRIEF = "8 m plywood cabin launch, 6 knots, 1.8 tonne, category C"


def test_the_reference_flag_is_actually_read():
    """MEASURED 2026-09-02 by the end-to-end flow check.

    `--reference` ("certify the reference hull against --mission") was
    declared, documented and NEVER READ — `args.reference` appears nowhere in
    the body. `--mission` used the reference hull unconditionally, so the flag
    selected nothing and its absence selected nothing either.

    The user-visible consequence was worse than a dead flag. The brief
    "8 m plywood cabin launch, 6 knots, 1.8 tonne" printed a full report
    headed by that brief and reported a 2643 kg hull with `VERDICT: REFUSE`
    and violations (B/T 12.60 outside its band, beam_carried 0.122) that
    belong to the REFERENCE HULL, not to anything the user asked for. One
    parenthetical line said so; forty lines of numbers did not. A reader takes
    REFUSE to mean "your boat is bad" when it means "the reference hull does
    not meet your brief" — the worst kind of true statement.
    """
    code, out = _run(["--mission", _BRIEF, "--reference", "--no-gz"])
    assert code == 0
    # the attribution is LOUD, not parenthetical: the verdict is named as
    # belonging to the reference hull
    assert "THE REFERENCE HULL" in out
    assert "INCLUDING THE VERDICT" in out
    # ...and it says how to get the other behaviour
    assert "--reference" in out
    assert "designing for this brief" not in out


def test_a_mission_alone_DESIGNS_rather_than_grading_the_reference_hull():
    """The product's design route is a SEARCH, and the CLI face now runs it.

    MEASURED on the same brief, before and after: the reported hull went from
    the reference hull's 2643 kg / fairness 278.8 / wetted 19.0 m^2 with
    `VERDICT: REFUSE`, to a designed 2239.6 kg / fairness 28.0 / wetted
    13.1 m^2 with `VERDICT: MARGINAL`. Same brief, same ladder, same bars —
    what changed is that the report is now about a hull drawn FOR the brief.
    """
    code, out = _run(["--mission", _BRIEF, "--no-gz"])
    assert code == 0
    assert "designing for this brief" in out
    assert "DESIGNED for this brief" in out
    assert "THE REFERENCE HULL" not in out
    # WHICH design and WHY that one must be stated: a Pareto front has no
    # single best point, and a CLI that silently picks one is choosing for
    # the user without saying so.
    assert "Pareto front" in out and "lowest-energy" in out


def test_an_impossible_brief_is_REFUSED_with_the_rows_that_refused_it():
    """A refusal is a RESULT, and it carries its reasons — the same contract
    `evaluate.MissionInfeasible` holds for the design feed. A CLI that
    returned a plausible boat here would be the worst false green in the
    product."""
    code, out = _run(["--mission", "30 m submarine, 40 knots, 500 tonne, "
                                   "category A", "--no-gz"])
    assert code == 2, "an impossible brief must exit non-zero"
    assert "REFUSE" in out
    # the tally, not just the verdict
    assert "freeboard" in out and "candidates" in out
    # and a way forward that does not involve pretending
    assert "--reference" in out
