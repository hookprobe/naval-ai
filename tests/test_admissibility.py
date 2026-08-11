"""Gate tests for the CFD-admissibility screen.

THE MOTIVATING INCIDENT. The Gate 2U seed-0 campaign
(`scripts/mesh_robustness.py --n 25 --seed 0 --solve 2 --np 10`, scale 1.0,
speed 2.57, LTS) meshed **6 of its first 18 hulls** against a >=95% bar, and
all 18 pass `grammar.check()`. The hull indices below are those campaign
hulls, regenerated from the same `sample_valid(seed=0)` call the campaign
uses, so every bar in `navalai/admissibility.py` is tested against the
VERBATIM geometry it was written to refuse (docs/LESSONS.md defect class 3: a
test showing a guard accepts a good case proves nothing about rejection).

The campaign's own JSON is deliberately NOT read here. It is an untracked,
still-growing artefact of a running campaign; a gate test that reads it would
change verdict as rows land. The outcomes are transcribed into this file as
the measurement they are.
"""

import ast
import re
from pathlib import Path

import numpy as np
import pytest

from navalai import grammar
from navalai.admissibility import (Basis, Metric, Verdict, screen,
                                   surface_grid)
from navalai.cfd.case import _HULL_REFINE, _refine_boxes, layer_spec
from navalai.evaluate import sample_valid
from navalai.geometry import Hull, _halfbreadth_at
from navalai.mission import MissionSpec

SPEED = 2.57
SCALE = 1.0

# MEASURED, campaign `data/gate2u-campaign-baseline.json`, rows 0-17.
MESHED = (2, 7, 9, 13, 15, 17)
FAILED = (0, 1, 3, 4, 5, 6, 8, 10, 11, 12, 14, 16)
# ...and WHY, for the four/three the screen is supposed to catch:
#   0  checkmesh-zero-volume       draft 10.14 cells   1  wrong-oriented  12.31
#   6  checkmesh-zero-volume       draft 11.82         12  zero-volume     13.20
#   5  mesh-build-failed           sheer collapse 3.04 cells
#   11 checkmesh-wrong-oriented    sheer collapse 2.13
#   12 checkmesh-zero-volume       sheer collapse 4.36
DRAFT_BAR_HULLS = (0, 1, 6, 12)
COLLAPSE_BAR_HULLS = (5, 11, 12)


@pytest.fixture(scope="module")
def campaign_hulls():
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    return X


@pytest.fixture(scope="module")
def reports(campaign_hulls):
    return [screen(x, SPEED, SCALE) for x in campaign_hulls]


# ---------------------------------------------------------------------------
# The screen must not become a SECOND copy of the geometry or of the pipeline.
# ---------------------------------------------------------------------------

def test_surface_grid_is_the_grid_closed_mesh_triangulates():
    """`surface_grid` is a fast replica of `Hull.closed_mesh`'s vertex grid.

    A replica is defect class 2 (a number — here a whole surface — declared
    twice) unless it is fenced, and it exists only because `closed_mesh` is a
    Python double loop costing ~1.4 s per hull at the case's 600x120
    triangulation. This asserts it against the two PRIVATE helpers
    `closed_mesh` itself calls, so a change to either side is caught.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    for x in X:
        h = Hull(x)
        nx, nz = 61, 12
        S = surface_grid(h, nx, nz)
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
        for i in (0, 1, nx // 3, nx // 2, nx - 2, nx - 1):
            pts = h._section_at(float(xs[i]))
            zt = np.linspace(pts[0, 1], pts[2, 1], nz + 1)
            for j, z in enumerate(zt):
                assert S[i, j, 0] == pytest.approx(xs[i])
                assert S[i, j, 2] == pytest.approx(z)
                assert S[i, j, 1] == pytest.approx(
                    _halfbreadth_at(pts, float(z)), abs=1e-12)


def test_no_pipeline_constant_is_restated_in_this_module():
    """The bars are IMPORTED from `navalai.cfd.case`, never transcribed.

    The draft bar is 14.187 cells at scale 1 — but that number appears nowhere
    in `admissibility.py`, because it is `_refine_boxes(...)[-1]['bz1']` over
    the level-5 hull cell and it must move when `_FS_BOX`, `_HULL_REFINE` or
    `_NX_BASE` move. A transcribed copy is the defect this repository pays for
    most often (docs/LESSONS.md class 2).
    """
    src = Path("navalai/admissibility.py").read_text()
    # Comments and docstrings QUOTE these numbers on purpose — that is the
    # measurement record. Only executable code is checked (docs/LESSONS.md
    # defect class 8: a predicate that reads comments finds the word it is
    # looking for sitting in the comment ON the defect).
    code = re.sub(r"#.*", "", re.sub(r'"""(?:.|\n)*?"""', "", src))
    for literal in (r"14\.18", r"\b0\.035\b", r"\b0\.025\b", r"\b_FS_BOX\b"):
        assert not re.search(literal, code), \
            f"pipeline constant {literal!r} restated in code"
    # ...and the ones it MUST import instead. Read from the AST, not from the
    # text: an import list wraps across lines and a line-anchored regex then
    # silently stops seeing half of it.
    imported = {a.name for n in ast.walk(ast.parse(src))
                if isinstance(n, ast.ImportFrom) for a in n.names}
    assert {"_refine_boxes", "_HULL_REFINE", "_NX_BASE", "layer_spec",
            "_LAYER_EXPANSION", "_DOMAIN_LENGTH_L"} <= imported


def test_the_draft_bar_is_the_refinement_band_and_not_a_fitted_number(
        campaign_hulls, reports):
    lwl = float(Hull(campaign_hulls[0]).x[-1])
    spec = layer_spec(lwl, SPEED, SCALE)
    cell = spec["hull_cell_m"] / 2.0 ** (_HULL_REFINE[1] - _HULL_REFINE[0])
    expected = _refine_boxes(lwl, True)[-1]["bz1"] / cell
    assert reports[0].get("draft_over_hull_cell").danger_below == \
        pytest.approx(expected)


# ---------------------------------------------------------------------------
# Every bar, fed the input it must REFUSE.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hid", DRAFT_BAR_HULLS)
def test_draft_bar_refuses_the_hulls_whose_keel_sits_in_the_refine_band(
        reports, hid):
    """Campaign hulls 0, 1, 6, 12 — draft 10.14/12.31/11.82/13.20 hull cells.

    All four failed checkMesh (two zero-volume, one wrongly-oriented, one
    zero-volume). All four have their keel inside the tightest post-snappy
    z-refinement box, whose bottom is 14.187 cells down at scale 1.
    """
    m = reports[hid].get("draft_over_hull_cell")
    assert m.verdict is Verdict.DANGEROUS
    assert m.basis is Basis.DERIVED
    assert "draft_over_hull_cell" in reports[hid].refused_by


@pytest.mark.parametrize("hid", COLLAPSE_BAR_HULLS)
def test_collapse_bar_refuses_the_hulls_whose_sheer_was_silently_clipped(
        reports, hid):
    """Campaign hulls 5, 11, 12 — 3.04, 2.13 and 4.36 cells of collapsed deck.

    `station_geometry` computes `ys` from the flare and then writes
    `np.maximum(ys, 0.0)`: where the flare drives the sheer inboard of the
    centreline the code delivers a DIFFERENT hull and says nothing. All three
    failed to mesh. (The mechanism is NOT an open STL — see the module comment;
    all three are watertight.)
    """
    m = reports[hid].get("sheer_collapse_cells")
    assert m.verdict is Verdict.DANGEROUS
    assert m.value > 0.0
    assert "sheer_collapse_cells" in reports[hid].refused_by


def test_sub_cell_bars_refuse_a_verbatim_sub_cell_hull(reports):
    """Campaign hull 20: bottom panel 0.998 cells, transom half-beam 0.998 cells.

    The sub-cell bars were unexercised by hulls 0-17, which is exactly the
    condition under which a bar rots. Hull 20 trips both. It is a PREDICTION —
    hull 20's mesh outcome had not been recorded when this test was written
    (see docs/BUILD-PLAN.md, the pre-registered block).
    """
    r = reports[20]
    assert r.get("min_bottom_panel_width_cells").verdict is Verdict.DANGEROUS
    assert r.get("transom_half_beam_cells").verdict is Verdict.DANGEROUS
    assert r.verdict is Verdict.DANGEROUS


def test_an_unmeasurable_metric_is_refused_and_beats_every_other_verdict():
    """docs/LESSONS.md defect class 1: `${_MQ_SKEW:-0}` scored 'could not
    measure' as a perfect 0 against a bar of 20. A NaN here must never be able
    to admit a hull, and it must SAY which metric could not be read."""
    m = Metric.of("x", float("nan"), "cells", Basis.DERIVED, "why",
                  danger_below=1.0)
    assert m.verdict is Verdict.UNMEASURED
    assert "NOT MEASURABLE" in m.note
    assert Verdict.UNMEASURED.value > Verdict.DANGEROUS.value
    assert Metric.of("y", None, "-", Basis.DERIVED, "z").verdict is \
        Verdict.UNMEASURED


def test_a_diagnostic_metric_never_votes(reports):
    """The stem cusp and the x_mb tangent break are REAL and do not predict.

    MEASURED AUC against mesh failure over campaign hulls 0-17 (hull 5
    excluded, its record is self-contradictory): bow_bluntness_cells 0.500,
    xmb_tangent_break_deg 0.500 — chance, both of them. They are reported and
    forbidden to vote, so no later session can promote 'we compute it' into
    'it predicts it'.
    """
    diag = [m for m in reports[7].metrics if m.basis is Basis.DIAGNOSTIC]
    assert {m.name for m in diag} >= {"bow_bluntness_cells",
                                      "xmb_tangent_break_deg"}
    for m in diag:
        assert not m.votes
        assert m.verdict is Verdict.SAFE
    # hull 7 MESHED and has bow_bluntness 13.55 cells and a 23.1 deg tangent
    # break — larger than several hulls that failed. It must come out unrefused.
    assert reports[7].refused_by == ()


# ---------------------------------------------------------------------------
# The screen as a whole, against every historical case.
# ---------------------------------------------------------------------------

def test_the_screen_refuses_no_hull_that_actually_meshed(reports):
    """Zero false alarms on the 6 hulls that meshed — the direction that
    matters, because a screen that refuses good hulls silently shrinks the
    design space and Gate 2U would then pass by exclusion."""
    for hid in MESHED:
        assert reports[hid].verdict is not Verdict.DANGEROUS, (
            f"hull {hid} MESHED but the screen refused it: "
            f"{reports[hid].refused_by}")


def test_the_screen_catches_half_the_failures_and_no_more(reports):
    """PINS THE MEASUREMENT, INCLUDING ITS LIMIT. TP 6, FP 0, FN 6, TN 6 —
    precision 1.000, recall 0.500 over campaign hulls 0-17.

    The recall is pinned as well as the precision on purpose: half of the
    observed Gate 2U failures have NO cheap geometric explanation in this
    module, and a future edit that quietly claims more must fail this test
    rather than be believed.
    """
    tp = sum(reports[h].verdict is Verdict.DANGEROUS for h in FAILED)
    fp = sum(reports[h].verdict is Verdict.DANGEROUS for h in MESHED)
    assert (tp, fp) == (6, 0)
    assert tp / len(FAILED) == pytest.approx(0.5)


def test_a_refused_hull_is_rescuable_and_the_module_says_so(reports):
    """THE FINDING THAT BOUNDS THIS WHOLE MODULE, pinned so it cannot be
    quietly dropped when someone wants a stronger claim.

    MEASURED 2026-08-11, `data/gate2u-campaign-backoff-mesh.json` — same seed-0
    hulls, mesh-only, `--layer-backoff 3`: hulls 0, 1, 5, 6 and 11, which this
    screen refuses, ALL MESH once the prism-layer count steps down, at 8/7/8/8/7
    layers with 0 zero-volume and 0 wrongly-oriented faces and skew
    4.52/3.25/4.54/4.65/5.13. Hull 4, which the ladder cannot save (38 wrongly
    oriented at 3 layers, 4 attempts), this screen calls SAFE. Over hulls 0-11
    the rate goes 3/12 at rung 0 to 11/12 with the ladder.

    So DANGEROUS means "expect a refusal at the DERIVED layer count", and the
    module must not sell it as "unmeshable". A docstring is not usually
    load-bearing, but this one is the difference between a screen and a claim
    the data does not support (docs/LESSONS.md defect class 4), so it is
    asserted.
    """
    for hid in (0, 1, 5, 6, 11):
        assert reports[hid].verdict is Verdict.DANGEROUS
    assert reports[4].verdict is not Verdict.DANGEROUS
    import navalai.admissibility as adm
    assert "back-off campaign" in adm.__doc__
    assert "not *\"this hull cannot be meshed\"*" in adm.__doc__ or \
        "cannot be meshed" in adm.__doc__
    assert "rung 0" in adm.screen.__doc__


def test_the_manifold_the_grammar_emits_is_a_third_inadmissible():
    """MEASURED over 200 grammar-valid hulls (seed 1234, speed 2.57, scale 1):
    68 DANGEROUS / 79 MARGINAL / 53 SAFE. 19.5% put the keel inside the
    free-surface refinement band and 17.0% have a silently clipped sheer.

    This is the number the Gate 2U funnel in docs/BUILD-PLAN.md is built on,
    so it is pinned. Bounds, not equality: `sample_valid` depends on
    `evaluate()`, which is not this module's to freeze.
    """
    X, _ = sample_valid(200, MissionSpec(), seed=1234)
    reps = [screen(x, SPEED, SCALE) for x in X]
    dangerous = sum(r.verdict is Verdict.DANGEROUS for r in reps)
    assert 55 <= dangerous <= 85, dangerous
    for name, lo, hi in (("draft_over_hull_cell", 25, 55),
                         ("sheer_collapse_cells", 20, 50)):
        n = sum(name in r.refused_by for r in reps)
        assert lo <= n <= hi, f"{name}: {n}"


def test_screening_is_cheaper_than_meshing_by_four_orders_of_magnitude():
    """The whole point: ~8 ms against ~80 s of snappy per hull. A screen that
    is not cheap is a second mesher."""
    import time
    X, _ = sample_valid(20, MissionSpec(), seed=3)
    t0 = time.perf_counter()
    for x in X:
        screen(x, SPEED, SCALE)
    per = (time.perf_counter() - t0) / len(X)
    assert per < 0.10, f"{per * 1000:.1f} ms/hull"


def test_a_grammar_valid_hull_is_not_the_same_thing_as_a_meshable_one():
    """The claim the module exists to make, stated as an assertion: hulls that
    `grammar.check()` blesses are refused here. If this ever stops being true
    the module is redundant and should be deleted, not kept as decoration."""
    X, _ = sample_valid(60, MissionSpec(), seed=11)
    assert all(grammar.check(x).ok for x in X)
    assert any(screen(x, SPEED, SCALE).verdict is Verdict.DANGEROUS for x in X)
