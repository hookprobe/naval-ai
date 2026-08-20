"""PHYSICS SANITY — a solver that exits 0 has not thereby produced physics.

THE DEFECT THESE TESTS CLOSE, walked end to end by the 2026-08-20 audit:
nothing in the tree checked the SIGN or the MAGNITUDE of an extracted force.
Every C_T was produced through `abs()` — which also made
`pipeline.check_cfd`'s `ct <= 0` refusal unreachable — so a sign-flipped
-500 N (a thrust) passed `settled_drag`, was rectified by `abs()`, landed
inside the Tokyo band and minted an L3 "measured" badge.
"""
import numpy as np
import pytest

from navalai.cfd.post import (PHYSICS_RATIO_IMPOSSIBLE, PHYSICS_RATIO_SUSPECT,
                              ForceHistoryError, parse_forces, physics_sanity)
from tests.test_settled_drag import _write_case


# ---------------------------------------------------------------------------
# the pure bars
# ---------------------------------------------------------------------------


def test_a_positive_total_is_a_thrust_not_a_resistance():
    """The walked exploit, refused at its first step.

    MEASURED convention (the Mac's 2026-08-20 export, all 19 histories):
    drag_n is NEGATIVE, -238 to -20206 N. A settled positive total is a
    flipped normal, a swapped column or a thrust — and abs() hides all three.
    """
    bad = physics_sanity(+500.0)
    assert not bad["ok"]
    assert "tow convention" in " ".join(bad["reasons"])
    assert physics_sanity(-500.0)["ok"]


def test_non_finite_and_zero_forces_are_refused_not_scored():
    for value in (float("nan"), float("inf"), -float("inf")):
        r = physics_sanity(value)
        assert not r["ok"] and "not a number" in " ".join(r["reasons"])
    z = physics_sanity(0.0)
    assert not z["ok"] and "zero" in " ".join(z["reasons"])


def test_an_impossible_magnitude_is_refused_and_a_suspect_one_is_flagged():
    """The two-level bar, keyed to this repository's OWN measured defects.

    IMPOSSIBLE (refuse) is a factor of 10: not a modelling difference but a
    unit, area or reference-velocity error. SUSPECT (flag) must sit BELOW the
    two force defects this project has actually shipped — the double-counted
    pressure column (KCS C_t 9.33e-3 against forceCoeffs' 4.26e-3, 2.19x) and
    forceCoeffs wrong by exactly 2.0x on every symmetric run — or it is
    decoration. THIS TEST CAUGHT EXACTLY THAT: the constant's first draft was
    2.5 and passed the 2.19x defect unremarked.
    """
    prior = -1000.0
    impossible = physics_sanity(-1000.0 * (PHYSICS_RATIO_IMPOSSIBLE + 1.0),
                                prior_n=prior)
    assert not impossible["ok"] and "unit, area" in " ".join(
        impossible["reasons"])

    historical = physics_sanity(-2190.0, prior_n=prior)      # the 2.19x defect
    assert historical["ok"], "a 2.19x disagreement is not impossible physics"
    assert historical["flags"], "...but it must never pass unremarked"
    assert historical["ratio"] == pytest.approx(2.19, abs=1e-9)

    symmetric_2x = physics_sanity(-2000.0, prior_n=prior)
    assert symmetric_2x["ok"] and symmetric_2x["flags"], (
        "the 2.0x symmetric reference-area defect must flag too")

    ordinary = physics_sanity(-1400.0, prior_n=prior)
    assert ordinary["ok"] and not ordinary["flags"]
    assert 1.0 / PHYSICS_RATIO_SUSPECT < ordinary["ratio"] < PHYSICS_RATIO_SUSPECT


def test_a_missing_prior_does_not_become_a_passing_magnitude_check():
    r = physics_sanity(-500.0, prior_n=None)
    assert r["ok"] and r["ratio"] is None and not r["flags"]
    assert not physics_sanity(+500.0, prior_n=None)["ok"], (
        "the sign clause must still run without a prior")


# ---------------------------------------------------------------------------
# the reader
# ---------------------------------------------------------------------------


def test_a_nan_row_refuses_instead_of_silently_shortening_the_history(tmp_path):
    """`_NUM` matches only [-+0-9.eE], so a row carrying `nan` yielded fewer
    than 7 numbers and the old `continue` DROPPED it: a poisoned history
    shortened into a clean-looking one, and settled_drag's non-finite guard —
    which can only see what it is handed — never fired."""
    t = np.arange(1.0, 21.0)
    case = _write_case(tmp_path / "poisoned", t, -np.ones(20) * 100.0,
                       -np.ones(20) * 10.0)
    f = case / "postProcessing" / "forces" / "0" / "force.dat"
    rows = f.read_text().splitlines()
    rows[10] = "10.000000 (nan 0 0) (nan 0 0) (nan 0 0)"
    f.write_text("\n".join(rows) + "\n")

    with pytest.raises(ForceHistoryError, match="non-finite token"):
        parse_forces(f)


def test_a_truncated_final_write_is_tolerated_but_a_corrupt_interior_is_not(
        tmp_path):
    """The one benign case is a solver killed mid-write — and ONLY on the
    final line. A short row anywhere else means the file is corrupt, not
    truncated, and the two must not share a verdict."""
    t = np.arange(1.0, 21.0)
    case = _write_case(tmp_path / "trunc", t, -np.ones(20) * 100.0,
                       -np.ones(20) * 10.0)
    f = case / "postProcessing" / "forces" / "0" / "force.dat"
    rows = f.read_text().splitlines()

    f.write_text("\n".join(rows) + "\n20.5 (-110.0 0")     # killed mid-write
    tt, fx = parse_forces(f)
    assert len(tt) == 20 and np.all(np.isfinite(fx))

    rows[10] = "10.0 (-110.0 0"
    f.write_text("\n".join(rows) + "\n")
    with pytest.raises(ForceHistoryError, match="not the final line"):
        parse_forces(f)


# ---------------------------------------------------------------------------
# the campaign classifier and the pipeline gate
# ---------------------------------------------------------------------------


def _classify(**row):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "_mr", Path(__file__).resolve().parents[1] / "scripts"
        / "mesh_robustness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    base = {"screen_no_rescue": (), "runner_exit": 0, "cells": 100000,
            "zero_volume_cells": 0, "wrong_oriented": 0, "max_skewness": 3.0,
            "solve_requested": True, "solve_attempted": True, "solves": True,
            "solve_steps": 2000}
    base.update(row)
    return mod.classify(base)


def test_ran_to_budget_without_a_readable_force_history_is_not_ok():
    """The Mac corrected Gate 2U 88.2% -> 17.6% on 2026-08-20 for exactly this
    conflation: `solves` is time-only (reached endTime without dying). A run
    that produced no readable forces has no resistance to grade."""
    assert _classify() == "ok"                       # field absent: unmeasured
    assert _classify(forces_readable=True) == "ok"
    assert _classify(forces_readable=False) == "force-extraction-failed"
    assert _classify(forces_readable=None) == "force-history-missing"


def test_a_new_field_does_not_retroactively_relabel_older_rows():
    """UNMEASURED IS NOT FAILED, and the distinction is the KEY, not the
    value: every campaign row banked before 2026-08-20 carries no
    `forces_readable`, and grading those as extraction failures would
    fabricate a measurement nobody took."""
    assert "forces_readable" not in {}
    assert _classify() == "ok"


def test_a_resource_refusal_is_not_a_mesh_failure():
    """run-case.sh exits 3 when the concurrency guard refuses to start —
    nothing about the mesh was measured. Calling that `mesh-build-failed`
    is the 'wall of false failures' in another form."""
    assert _classify(runner_exit=3, cells=-1, max_skewness=-1.0,
                     solve_attempted=False, solves=False,
                     solve_steps=0) == "resource-limit-refused"


def test_check_cfd_can_finally_see_a_sign_flip():
    """`check_cfd`'s `ct <= 0` clause was UNREACHABLE: every C_T in the tree
    is produced through abs(), so no caller could hand it a negative one. The
    signed force is where the flip is still visible."""
    from navalai.pipeline import check_cfd

    ok = check_cfd(0.01, ct=0.004, flow_throughs=2.0, drag_n=-500.0)
    assert ok.ok, ok.reasons
    flipped = check_cfd(0.01, ct=0.004, flow_throughs=2.0, drag_n=+500.0)
    assert not flipped.ok
    assert "tow convention" in " ".join(flipped.reasons)
