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


def test_the_batch_section_sampler_is_the_loop():
    """`Hull._sections_at_rows_batch` == a loop over `Hull._section_at_rows`.

    The batch is a SECOND COPY of the section sampler (defect class 2), kept
    only because the per-station call overhead of `sample_section` put the
    screen at ~140 ms/hull against its 100 ms bar (~600 stations per hull on
    the round-bilge path). The screen's danger/margin bars were MEASURED
    through this grid, so the batch must be VALUE-PRESERVING: every sampled
    point equal to the single-x path at 1e-12, on BOTH branches — roundness 0
    (the vectorised polyline) and roundness > 0 (the Bezier + arc-length
    resample) — INCLUDING at the real 600x120 screen resolution, because the
    bars' calibration lives at that grid, not at a toy one.
    `_section_at_rows` stays the definition; this fence is what lets
    `surface_grid` call the copy.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=7)
    ir = grammar.NAMES.index("roundness")
    exercised_round = False
    for x in X:
        for force_hard_chine in (False, True):
            xv = np.asarray(x, float).copy()
            if force_hard_chine:
                xv[ir] = 0.0
            h = Hull(xv)
            exercised_round |= h.roundness > 0.0
            nz = 24
            jc = h.chine_row(nz)
            xs = np.linspace(float(h.x[0]), float(h.x[-1]), 37)
            batch = h._sections_at_rows_batch(xs, jc, nz - jc)
            assert batch.shape == (37, nz + 1, 2)
            for k, xq in enumerate(xs):
                ref = h._section_at_rows(float(xq), jc, nz - jc)
                err = float(np.max(np.abs(batch[k] - ref)))
                assert err < 1e-12, (float(xq), h.roundness, err)
    assert exercised_round, (
        "seed-7 draw no longer contains a round-bilge hull — the Bezier "
        "branch went untested; pick a seed that exercises it")
    # ...and once at the resolution the screen actually samples (600x120,
    # from `stl_resolution` at scale 1), on one round-bilge hull: the
    # calibrated bars were measured through THIS grid, so the equality
    # claim has to hold where they live, not only on a small grid.
    h = Hull(np.asarray(X[0], float))
    assert h.roundness > 0.0
    nx, nz = 600, 120
    jc = h.chine_row(nz)
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), nx)
    batch = h._sections_at_rows_batch(xs, jc, nz - jc)
    for k in range(nx):
        ref = h._section_at_rows(float(xs[k]), jc, nz - jc)
        err = float(np.max(np.abs(batch[k] - ref)))
        assert err < 1e-12, (k, err)


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


def test_the_draft_bar_is_demoted_to_a_receipt_by_the_confusion_table(
        campaign_hulls, reports):
    """RE-POINTED 2026-08-19: the first 16-gene confusion table
    (data/gate2u-16gene-mesh.json) measured this bar 0-for-4 as a rung-0
    predictor — hulls 4/5/6/8 below it all meshed CLEAN with the ladder
    unused — while catching neither actual refusal. The value is still
    RECORDED (the receipt survives); it votes on nothing, and this fence
    keeps it demoted until a measurement says otherwise."""
    m = reports[0].get("draft_over_hull_cell")
    assert m is not None, "the receipt must survive the demotion"
    assert m.danger_below is None, (
        "draft_over_hull_cell is voting again — the 16-gene confusion "
        "table measured it 0-for-4; re-basing it needs NEW evidence")
    assert "DEMOTED" in m.note


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
    """Campaign hulls 5, 11, 12 — the OLD kernel delivered a zero-width deck.

    UPDATED 2026-08-18 for the re-derivation: `sheer_collapse_cells` was
    retired (it was a second copy of the PRE-P1 sheer law; the rebuilt kernel
    refuses a negative sheer at L0, so the clip it measured no longer exists).
    Its successor measures the DELIVERED deck half-width in cells, and the
    old kernel delivered these three hulls a LITERAL zero-width ridge — 0.0
    cells against a bar of 1.0 — so if a 15-gene campaign is ever replayed,
    the successor must refuse the same three hulls the retired bar was
    validated on. (Permanently skipped in practice: the genome is 16 now.)
    """
    m = reports[hid].get("min_interior_sheer_halfwidth_cells")
    assert m.verdict is Verdict.DANGEROUS
    assert m.value < 1.0
    assert "min_interior_sheer_halfwidth_cells" in reports[hid].refused_by


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
# The 2026-08-18 re-derivation (docs/MESHABILITY_MATH.md): retirement fences,
# the rescue axis, and the solvability receipt.
# ---------------------------------------------------------------------------

def test_the_stale_sheer_formula_is_retired_and_its_successor_exists(reports):
    """`sheer_collapse_cells` recomputed the PRE-P1 sheer law (unenveloped
    flare) while the rebuilt kernel refuses a negative sheer at L0 — a second
    copy, voting. MEASURED: it refused 5 of 25 seed-0 hulls whose delivered
    interior sheer is 0.06..0.37 m. This fence keeps it dead and pins the
    successor's contract (delivered surface, sub-cell bar, no ladder rescue).
    """
    names = {m.name for m in reports[0].metrics}
    assert "sheer_collapse_cells" not in names, (
        "the retired stale-copy metric is back; see admissibility module "
        "docstring item 1 before resurrecting it")
    m = reports[0].get("min_interior_sheer_halfwidth_cells")
    assert m.basis is Basis.DERIVED
    # 1.0 -> 0.1 (2026-08-19): hull 18 at 0.35 cells meshed clean at rung
    # 0 on the metal; the labelled-fatal anchors are literal 0.0 ridges.
    assert m.danger_below == 0.1
    assert m.ladder_rescuable is False


def test_the_rescue_axis_matches_each_metrics_mechanism(reports):
    """Cell-scale metrics have no rung (the cell ignores the layer count);
    layer-scale metrics are the ladder's own domain (measured: the backoff
    campaign meshed every draft-bar refusal at a lower count, and the stack
    height falls with n). The writer refuses only the first set."""
    r = reports[0]
    for nm in ("min_bottom_panel_width_cells", "min_topside_panel_height_cells",
               "transom_half_beam_cells", "transom_immersion_cells",
               "min_interior_sheer_halfwidth_cells"):
        assert r.get(nm).ladder_rescuable is False, nm
    for nm in ("draft_over_hull_cell", "stack_over_min_radius"):
        assert r.get(nm).ladder_rescuable is True, nm


def test_refused_no_rescue_is_the_unrescuable_subset_and_unmeasured_is_fatal():
    """The writer's refusal set: DANGEROUS-without-a-rung plus UNMEASURED —
    an unmeasurable quantity must never admit a hull (defect class 1), and a
    rescuable DANGEROUS must never appear here (it has a measured
    deterministic path, the run-case.sh ladder)."""
    from navalai.admissibility import Report
    mets = (
        Metric.of("cell_scale", 0.5, "cells", Basis.DERIVED, "sub-cell",
                  danger_below=1.0, ladder_rescuable=False),
        Metric.of("layer_scale", 0.5, "cells", Basis.DERIVED, "rung-0",
                  danger_below=1.0, ladder_rescuable=True),
        Metric.of("unread", float("nan"), "-", Basis.DERIVED, "unmeasured",
                  danger_below=1.0, ladder_rescuable=True),
        Metric.of("diag", 0.0, "-", Basis.DIAGNOSTIC, "reported only"),
    )
    rep = Report(Verdict.UNMEASURED, mets, 0.04, 10.0, 7)
    assert set(rep.refused_no_rescue) == {"cell_scale", "unread"}
    assert set(rep.refused_by) == {"cell_scale", "layer_scale", "unread"}


def test_the_solvability_receipt_carries_the_measured_anchors(reports):
    """tau = V/(A_max*U) separates solved (7.8e-6..2.1e-5 s) from diverged
    (4.356e-18 s) by 12 orders while checkMesh is blind (docs/audit/STATUS.md,
    2026-08-18). The screen's pre-mesh receipt is the INTENDED minimum cell
    time scale; a healthy scale-1 case intends ~1e-4 s, orders above the
    run-case.sh 1e-12 s abort bar, and the receipt must say so and not vote.
    """
    m = reports[0].get("intended_min_cell_flow_time_scale_s")
    assert m.basis is Basis.DIAGNOSTIC and not m.votes
    assert 1e-5 < m.value < 1e-2, (
        f"intended tau {m.value:.3g}s is outside the healthy design decade — "
        f"either the layer/fs derivation moved or the receipt broke")
    assert "1e-12" in m.note and "7.8e-6" in m.note


def test_the_bilge_fillet_radius_is_reported_and_does_not_vote_yet(reports):
    """The 16th gene's own failure mode: NO round-bilge hull has a measured
    mesh outcome (case a is a hard chine; every labelled campaign is
    15-gene), so the fillet-radius metric reports its pre-registered window
    (stl_row < r < cell) and is forbidden to vote until a campaign labels
    it. Promoting it without labels would be the V6-first-draft defect."""
    m = reports[0].get("bilge_min_radius_cells")
    assert m.basis is Basis.DIAGNOSTIC and not m.votes
    # a hard chine reports inf: no fillet, no radius, nothing to resolve
    X, _ = sample_valid(1, MissionSpec(), seed=0)
    xr = np.asarray(X[0], float).copy()
    xr[grammar.NAMES.index("roundness")] = 0.0
    hard = screen(xr, SPEED, SCALE).get("bilge_min_radius_cells")
    assert not (hard.value < float("inf"))


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


def test_the_manifold_the_grammar_emits_is_screened_and_mostly_admissible():
    """RE-PINNED 2026-08-18 with the re-derivation (was "a third
    inadmissible": 68 DANGEROUS / 79 MARGINAL / 53 SAFE on the 15-gene-era
    metrics, 17.0% of it the retired stale sheer formula firing on decks the
    rebuilt kernel delivers healthy).

    RE-MEASURED 2026-08-19 after the confusion-table re-base (the
    2026-08-18 row read 39 DANGEROUS / 86 MARGINAL / 75 SAFE with
    writer-admissible 189/200 — dominated by the draft bar the table then
    measured 0-for-4): now **0 DANGEROUS / 11 MARGINAL / 189 SAFE**,
    refused_by empty, writer-admissible **200/200** at scale 1. The
    DANGEROUS class has not vanished from the screen — it lives below the
    0.1-cell edge and at model scales (see the Gate 2D sliver test) —
    it has vanished from the FULL-SCALE grammar manifold, which is what
    the metal measured: 23/25 mesh at rung 0 and the 2 that do not are
    not screen-predictable.

    Bounds, not equality: `sample_valid` depends on `evaluate()`, which is
    not this module's to freeze.
    """
    X, _ = sample_valid(200, MissionSpec(), seed=1234)
    reps = [screen(x, SPEED, SCALE) for x in X]
    dangerous = sum(r.verdict is Verdict.DANGEROUS for r in reps)
    assert dangerous <= 10, (
        f"{dangerous} DANGEROUS at full scale — the re-based bars moved, "
        f"or the grammar started emitting sub-0.1-cell features")
    # the writer's denominator: most of what the grammar emits must keep a
    # deterministic CFD path, or the screen has become a second grammar
    admissible = sum(1 for r in reps if not r.refused_no_rescue)
    assert admissible >= 190, f"writer admits only {admissible}/200"


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
    """The claim the module exists to make, stated as an assertion: a hull
    `grammar.check()` blesses can still be refused here — the screen is a
    statement about a (hull, speed, SCALE) case, not about the genome.
    RE-BASED 2026-08-19: at full scale the re-based bars admit the whole
    seed-11 draw (measured — that is the confusion table's verdict, not a
    regression), so the demonstration lives where the physics puts it: at
    model scale the cell coarsens relative to the features and the SAME
    grammar-valid hulls go sub-0.1-cell, refused with no rescue."""
    X, _ = sample_valid(19, MissionSpec(), seed=0)
    assert all(grammar.check(x).ok for x in X)
    # hull 18's bottom panel measures 0.26 cells at scale 1 (metal-clean,
    # warn band) and 0.065 at scale 0.25 — below every measured-clean
    # anchor, refused with no rescue. Same genome, same grammar blessing.
    rep = screen(X[18], SPEED, 0.25)
    assert rep.verdict is Verdict.DANGEROUS
    assert rep.refused_no_rescue


def test_the_screen_guards_the_case_writer_C18(tmp_path):
    """Forensics C-18, RE-SCOPED 2026-08-18 (docs/MESHABILITY_MATH.md): the
    writer refuses the hulls the layer ladder CANNOT rescue — sub-cell
    features and anything UNMEASURED (`Report.refused_no_rescue`) — and
    WRITES a rescuable-DANGEROUS hull with a warning, because run-case.sh's
    canonical backoff ladder is its measured deterministic recovery
    (metal-proven on case a: derived n=6 FATAL -> n=5 CLEAN, unattended).
    Refusing rescuable hulls at the writer was blocking hulls with a
    measured path; the phantom half of those refusals came from the retired
    stale sheer formula. Declared experiments still bypass with
    allow_dangerous_mesh=True, and every case records the verdict."""
    import warnings as _warnings

    import numpy as np
    import pytest

    from navalai.admissibility import Verdict, screen
    from navalai.cfd.case import write_resistance_case
    from navalai.evaluate import sample_valid
    from navalai.geometry import Hull
    from navalai.mission import MissionSpec

    X, _ = sample_valid(30, MissionSpec(), seed=0)
    no_rescue = next((x for x in X
                      if screen(Hull(x), speed=2.57).refused_no_rescue), None)
    rescuable = next((x for x in X
                      if screen(Hull(x), speed=2.57).verdict
                      is Verdict.DANGEROUS
                      and not screen(Hull(x), speed=2.57).refused_no_rescue),
                     None)
    if no_rescue is None or rescuable is None:
        pytest.skip("seed-0/30 no longer holds both guard fixtures — "
                    "recalibrate the fixture, do not delete the guard test")
    # 1. un-rescuable (sub-cell feature): REFUSED with the metric receipt
    with pytest.raises(ValueError, match="admissibility screen"):
        write_resistance_case(Hull(no_rescue), 2.57, tmp_path / "refused",
                              end_time=1.0, symmetric=True, n_layers=2)
    # 2. rescuable DANGEROUS: WRITES, warns, and records the prediction
    with _warnings.catch_warnings(record=True) as w:
        _warnings.simplefilter("always")
        write_resistance_case(Hull(rescuable), 2.57, tmp_path / "rescuable",
                              end_time=1.0, symmetric=True, n_layers=2)
    assert any("admissibility screen" in str(x.message) for x in w), (
        "the rung-0 prediction must be warned, not silent")
    info = (tmp_path / "rescuable" / "case.info").read_text()
    assert "admissibility_verdict=DANGEROUS" in info
    assert "admissibility_no_rescue=none" in info
    # 3. the declared-experiment override still writes the un-rescuable one
    write_resistance_case(Hull(no_rescue), 2.57, tmp_path / "declared",
                          end_time=1.0, symmetric=True, n_layers=2,
                          allow_dangerous_mesh=True)
    info = (tmp_path / "declared" / "case.info").read_text()
    assert "admissibility_verdict=" in info
    assert "admissibility_no_rescue=" in info
    assert "admissibility_no_rescue=none" not in info
