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
from navalai.admissibility import (CALIBRATION_GENOME_N_PARAMS, Basis, Metric,
                                   Verdict, calibration_is_current, screen,
                                   surface_grid)
from navalai.cfd.case import _HULL_REFINE, _refine_boxes, layer_spec
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
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
    triangulation.

    STRENGTHENED 2026-08-12, when the chine became a grid row: the fence used
    to re-derive the grid from `_section_at` + `_halfbreadth_at`, which is a
    THIRD transcription of the sampling rule and drifts with the other two.
    It now asserts that every point of `surface_grid` is literally a vertex of
    what `closed_mesh` returned — the only statement that cannot be satisfied
    by two copies agreeing with each other and disagreeing with the mesh.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    for x in X:
        h = Hull(x)
        nx, nz = 61, 12
        S = surface_grid(h, nx, nz)
        verts, tris = h.closed_mesh(nx=nx, nz=nz)
        emitted = {tuple(np.round(v, 9)) for v in verts[tris.ravel()]}
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
        for i in (0, 1, nx // 3, nx // 2, nx - 2, nx - 1):
            assert S[i, :, 0] == pytest.approx(xs[i])
            for j in range(nz + 1):
                assert tuple(np.round(S[i, j], 9)) in emitted, (i, j)


def test_the_chine_is_a_row_of_the_grid_not_a_corner_it_chords_across():
    """Stage A, and the reason `chine_row` exists at all.

    MEASURED 2026-08-12 at the nx=600/nz=120 triangulation
    `make_resistance_case` writes: the exact chine point of the blended
    section sat 11.95 / 4.50 / 11.45 mm off the chord the uniform-z grid put
    in its place, on hulls 4 / 8 / 14 of `sample_valid(25, MissionSpec(),
    seed=0)` — at EVERY x, not only at the stem. Bar: 1e-9 m, i.e. the chine
    is ON the surface, not near it (docs/LESSONS.md defect class 3 — the
    assertion has to be the one the old grid FAILS, and the old grid fails
    this by 12 mm).

    PINNED TO roundness = 0 ON 2026-08-13. `chine_row` still exists after the
    geometry rebuild, but for a FILLETED bilge it returns the fillet's
    mid-point, not a corner — so "the chine is a row of the grid" is a claim
    about a hull that HAS a chine. Measured on the reference hull with the
    fillet live, the row sits 0.430 m from `_section_at`'s breakpoint, which is
    the fillet's own curvature and not a regression. At roundness = 0 the
    kernel is bit-identical to the pre-rebuild one (fenced at 1e-12 in
    tests/test_geometry_kernel.py) and the 1e-9 bar below is exactly as hard as
    it was. Relaxing the bar to cover a fillet would have retired the
    measurement this test exists for.
    """
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    ir = grammar.NAMES.index("roundness")
    for hid in (4, 8, 14):
        x = np.asarray(X[hid], float).copy()
        x[ir] = 0.0                       # a chine claim needs a chine
        h = Hull(x)
        nz = 120
        jc = h.chine_row(nz)
        assert 1 <= jc <= nz - 1
        S = surface_grid(h, 97, nz)
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), 97)
        for i in range(0, 97, 7):
            pts = h._section_at(float(xs[i]))
            assert S[i, jc, 1] == pytest.approx(pts[1, 0], abs=1e-9)
            assert S[i, jc, 2] == pytest.approx(pts[1, 1], abs=1e-9)
        # and the row is still a partition: keel at 0, sheer at nz
        assert S[50, 0, 2] == pytest.approx(h._section_at(float(xs[50]))[0, 1])
        assert S[50, nz, 2] == pytest.approx(h._section_at(float(xs[50]))[2, 1])


def test_every_grid_point_still_lies_on_the_analytic_section_polyline():
    """Redistributing rows must MOVE VERTICES ALONG the section, never off it.

    The panels are unchanged straight segments; only the sampling parameter
    changed. If this ever fails, the row split has become a shape change —
    which would be a different boat, not a better mesh.

    PINNED TO roundness = 0 ON 2026-08-13, and the pin is the point rather than
    a convenience. "Lies on the section POLYLINE" is a HARD-CHINE property: the
    geometry kernel rebuild made the bilge a fillet, and a point on a curve is
    not on the chord that used to approximate it — measured 0.058 m off at the
    reference hull, which is the fillet, not a defect. The claim this test was
    written to defend (redistributing rows moves vertices ALONG the section,
    never off it) is exactly true at roundness = 0, where the kernel is
    bit-identical to the old one to 1e-12. The curved case has its own
    assertion in tests/test_geometry_kernel.py, against the analytic CURVE.
    Weakening this bound to swallow a fillet would have made it measure nothing.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    ir = grammar.NAMES.index("roundness")
    for x in X:
        x = np.array(x, dtype=float).copy()
        x[ir] = 0.0                      # a polyline claim needs a polyline
        h = Hull(x)
        nx, nz = 61, 12
        S = surface_grid(h, nx, nz)
        xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
        for i in range(nx):
            pts = h._section_at(float(xs[i]))
            for j in range(nz + 1):
                y, z = float(S[i, j, 1]), float(S[i, j, 2])
                d = min(_seg_dist(y, z, 0.0, pts[0, 1], pts[1, 0], pts[1, 1]),
                        _seg_dist(y, z, pts[1, 0], pts[1, 1],
                                  pts[2, 0], pts[2, 1]))
                assert d < 1e-12, (i, j, d)


def _seg_dist(py, pz, ay, az, by, bz) -> float:
    e = np.array([by - ay, bz - az])
    q = np.array([py - ay, pz - az])
    den = float(e @ e)
    t = 0.0 if den <= 1e-30 else float(np.clip((q @ e) / den, 0.0, 1.0))
    return float(np.linalg.norm(q - t * e))


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

# The nine tests below read a LABELLED mesh campaign — hull indices and the
# screen's catch rate against measured checkMesh outcomes. The geometry kernel
# rebuild changed the genome 15 -> 16 parameters, so those stored vectors no
# longer describe hulls this `Hull` can build and "hull 12" is a different boat.
# The LABELS are what was lost. Re-tuning the bars against hulls whose mesh
# outcome nobody has measured would be calibrating against nothing.
#
# They are SKIPPED, not deleted and not re-tuned, on a PROBE
# (`admissibility.calibration_is_current`) rather than a flag — so they un-skip
# by themselves the moment a campaign is run on the current genome. Gate 2A's
# ledger row carries the debt with an owner and a review-by date.
_needs_calibration = pytest.mark.skipif(
    not calibration_is_current(),
    reason=(f"the screen's bars were calibrated on a "
            f"{CALIBRATION_GENOME_N_PARAMS}-parameter genome and this tree has "
            f"{grammar.N_PARAMS}; the campaign labels cannot be transferred — "
            f"re-run scripts/mesh_robustness.py on the current genome"))


@pytest.mark.parametrize("hid", DRAFT_BAR_HULLS)
@_needs_calibration
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
@_needs_calibration
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


@_needs_calibration
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

@_needs_calibration
def test_the_screen_refuses_no_hull_that_actually_meshed(reports):
    """Zero false alarms on the 6 hulls that meshed — the direction that
    matters, because a screen that refuses good hulls silently shrinks the
    design space and Gate 2U would then pass by exclusion."""
    for hid in MESHED:
        assert reports[hid].verdict is not Verdict.DANGEROUS, (
            f"hull {hid} MESHED but the screen refused it: "
            f"{reports[hid].refused_by}")


@_needs_calibration
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


@_needs_calibration
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


def test_the_screen_guards_the_case_writer_C18(tmp_path):
    """Forensics C-18: the meshability screen and the case writer were two
    disconnected halves — a DANGEROUS hull sailed into a case write. The
    writer now refuses a DANGEROUS/UNMEASURED verdict with the screen's
    own metric receipt, writes it as a DECLARED experiment only under
    allow_dangerous_mesh=True, and records the verdict in case.info."""
    import numpy as np
    import pytest

    from navalai import formcheck
    from navalai.admissibility import Verdict, screen
    from navalai.cfd.case import write_resistance_case
    from navalai.evaluate import sample_valid
    from navalai.geometry import Hull
    from navalai.mission import MissionSpec

    # find a DANGEROUS hull the way the screen's own calibration did
    X, _ = sample_valid(30, MissionSpec(), seed=0)
    bad = next((x for x in X
                if screen(Hull(x), speed=2.57).verdict
                in (Verdict.DANGEROUS, Verdict.UNMEASURED)), None)
    if bad is None:
        pytest.skip("no DANGEROUS hull in 30 draws at this seed — "
                    "recalibrate the fixture, do not delete the guard test")
    with pytest.raises(ValueError, match="admissibility screen"):
        write_resistance_case(Hull(bad), 2.57, tmp_path / "refused",
                              end_time=1.0, symmetric=True, n_layers=2)
    # the declared-experiment override writes, and says so in the receipt
    write_resistance_case(Hull(bad), 2.57, tmp_path / "declared",
                          end_time=1.0, symmetric=True, n_layers=2,
                          allow_dangerous_mesh=True)
    info = (tmp_path / "declared" / "case.info").read_text()
    assert "admissibility_verdict=" in info
