"""Gate 6M — the manufacturing back end, against the bars it actually claims.

Every test here names the finding it exists to stop coming back (gap register
section G, BuildPlan3 R7):

  G2  there was no nesting, only stacking — the two hull panels fit on NO sheet
  G3  no BOM — three aggregate scalars, no line items, no panel->sheet map
  G4  the refold was never tested — Gate 6's clause was prose
  G5  `dev_error_rel` could not fail — it is O(h^2) for ANY smooth surface
  G6  the exported solid was not the validated hull — 12 stations vs 41
  A5  the export boundary enforced nothing (`refuse_unvalidated` had no test)
  C12 `WASTE_FACTOR = 1.30` asserted a nesting waste the layout could measure
"""

import math

import numpy as np
import pytest

from navalai import engineer, unroll
from navalai.engineer import assess
from navalai.geometry import Hull
from navalai.unroll import (SCARPH_RATIO, SHEET_L_M, SHEET_M2, SHEET_W_M,
                            develop, export_dxf, hull_panels, min_area_rect,
                            nest, parse_dxf_polylines, refold,
                            refold_deviation_mm, refold_surface_deviation_mm,
                            rulings_that_cross, split_panel)
from tests.test_phase0 import mid_params

# The bar Gate 6 owes: a panel that refolds this far off the hull is a panel
# whose seam you cannot fair. 5 mm is a fillable gap on a 10 m panel and is
# already generous; it is NOT tuned to what the hull happens to achieve.
# MEASURED, two-sided, reference hull at 41 stations, as multiples of this bar:
#
#     family        bottom-stbd        topside-stbd
#     constant-x    28.0x -> 30.7x     44.9x -> 94.5x
#     developable    9.6x -> 24.8x     13.2x ->  8.8x
#
# (BEFORE is 2026-08-11 on the old geometry kernel, AFTER is 2026-08-13 on the
# rebuilt one.) THE BAR DID NOT MOVE WHEN THE GEOMETRY CHANGED UNDER IT, in
# either direction — the rebuilt topside got 1.5x better and the rebuilt bottom
# got 2.6x WORSE, and both are readable only because the divisor is fixed.
# See test_gate6_refold_clause_is_red_on_the_hull.
#
# The number itself now lives in `limits.REFOLD_BAR_MM` (single source: the
# kit-line admission `buildability.kit_buildability` consumes the same bar),
# imported here so this file cannot drift from the one the product enforces.
from navalai.limits import REFOLD_BAR_MM


def _chord_error_mm(hull, edge, params):
    """Max distance from an edge CURVE to the polyline through it at `params`.

    The panel's boundary is that polyline, so this is how far the exported part
    is from the hull before any developability question is asked."""
    P = hull.edge_curves(params)[edge]
    Q = hull.edge_curves(np.linspace(0.0, float(hull.x[-1]), 20001))[edge]
    seg = P[1:] - P[:-1]
    ll = np.einsum("ij,ij->i", seg, seg)
    w = Q[:, None, :] - P[None, :-1]
    s = np.clip(np.einsum("kij,ij->ki", w, seg) / np.maximum(ll, 1e-300), 0, 1)
    return float(np.sqrt(((w - s[..., None] * seg[None]) ** 2).sum(-1))
                 .min(axis=1).max()) * 1000.0


# ---------------- fixtures: surfaces whose developability we KNOW ----------

def _true_cylinder(n=41):
    """Rulings all parallel: developable, and the textbook easy case."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))], axis=1)
    return A, A + np.array([5.0, 0.0, 0.0])


def _cone(n=41):
    """Rulings all concurrent: developable, and the case a twist metric must
    also pass, or it is only detecting non-parallel rulings."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))], axis=1)
    return A, np.repeat(np.array([[5.0, 0.0, 1.0]]), n, axis=0)


def _hypar(n=41):
    """z = 1.5 x y. Doubly ruled, Gaussian curvature strictly negative, and
    NOT developable by any definition — the negative control."""
    x = np.linspace(0, 2, n)
    A = np.stack([x, np.zeros(n), np.zeros(n)], axis=1)
    B = np.stack([x, np.ones(n), 1.5 * x], axis=1)
    return A, B


def _old_cylinder_fixture(n=41):
    """The surface tests/test_stageF.py called 'a cylindrical surface'."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.linspace(0, 5, n), np.zeros(n), np.zeros(n)], axis=1)
    B = A + np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))],
                     axis=1)
    return A, B


# ---------------- G5: a developability metric that CAN fail ---------------

@pytest.mark.parametrize("fixture", [_true_cylinder, _cone])
def test_true_developables_have_zero_ruling_twist(fixture):
    """POSITIVE CONTROL. A cylinder and a cone are developable, so
    det(A', r, r') must vanish — to machine precision, not 'small'."""
    p = develop(*fixture(), "dev")
    assert p.twist_max < 1e-12, f"twist {p.twist_max:.3e}"
    assert p.dev_error_rel < 1e-9


def test_hypar_negative_control_fails_developability():
    """NEGATIVE CONTROL, gap G5. A metric with no negative control is not a
    metric. z = 1.5xy is doubly ruled and emphatically non-developable; the
    twist criterion reads 1.000 max / 0.555 median on it.

    And the same fixture PASSES the old metric's bars, which is the whole
    finding: `dev_error_rel` is a per-quad chord residual, i.e. O(h^2)
    discretisation error for ANY smooth surface."""
    p = develop(*_hypar(41), "hypar")
    assert p.twist_max > 0.9 and p.twist_median > 0.5
    # the two bars this repository actually used, both cleared by 7.7x and 77x
    assert p.dev_error_rel < 5e-3      # tests/test_stageF cylinder bar
    assert p.dev_error_rel < 5e-2      # tests/test_stageF hull bar
    assert p.dev_error_rel == pytest.approx(6.46e-4, rel=0.05)


def test_refining_the_polyline_hides_the_hypar_but_not_its_twist():
    """The gap register proposed a refinement-convergence test as the fix for
    G5. MEASURED, it does not work: the hypar's chord residual converges at
    O(h^2.01) — the same rate as the genuinely developable-in-the-mean hull
    bottom panel — so 'the residual plateaus' does not separate them. The
    ruling twist is what does: it is INVARIANT under refinement."""
    coarse = develop(*_hypar(41), "hypar")
    fine = develop(*_hypar(161), "hypar")
    order = np.log(coarse.dev_error_rel / fine.dev_error_rel) / np.log(4.0)
    assert 1.8 < order < 2.2, f"order {order:.2f}"
    assert fine.dev_error_rel < 1e-4          # refined away to nothing
    assert fine.twist_median == pytest.approx(coarse.twist_median, rel=1e-6)


def test_the_old_cylinder_fixture_was_a_conoid():
    """RECORDED. `test_cylinder_develops_exactly` called its fixture 'a
    cylindrical surface' and asserted dev_error_rel < 5e-3 on it. Its rulings
    are chords from a straight axis to a quarter circle — a CONOID, whose
    ruling direction rotates, so it is not developable either: twist median
    0.383. The positive control and the negative control were the same kind of
    object, and the metric could tell neither of them from a cylinder."""
    p = develop(*_old_cylinder_fixture(41), "conoid")
    assert p.twist_median == pytest.approx(0.383, abs=0.02)
    assert p.dev_error_rel < 5e-3             # it passed the old bar


def test_hull_panel_twist_is_recorded_not_blessed():
    """MEASURED on the reference hull, and NOT softened (honesty rule 6).

    THE CLAIM THIS TEST CARRIED UNTIL 2026-08-13 IS REFUTED, AND THE REFUTATION
    IS THE FINDING, NOT A BUMPED CONSTANT. It read: "the TOPSIDE panel is not
    developable anywhere — median 0.617, indistinguishable from the hypar
    negative control above". The rebuilt geometry kernel measures the
    constant-x topside's median ruling twist at 1.5e-14 — machine zero, 13
    orders of magnitude away from the number this test was written around.

    THE MECHANISM THAT WENT AWAY. The old kernel closed the deck with
    `y_sheer = ys * w**0.15`, i.e. the sheer half-breadth carried a plan-form
    envelope the chine did not, so the ruling direction r = sheer - chine
    rotated at EVERY station and det(A', r, r') never vanished.
    `geometry._stations` now runs the topside as ONE straight line from the
    chine at the enveloped flare, `ys = yc + (zs - zc) * f`, so
    r = (0, (zs - zc) * f, zs - zc) is proportional to (0, f, 1) and depends on
    NOTHING but f. Aft of the max-area station (x_mb * L = 5.50 m here) the
    envelope is 1, f is the constant `flare`, r' vanishes identically and the
    determinant with it. Half the panel became exactly developable; no metric
    was relaxed to get there.

    WHAT DID NOT GO AWAY IS THE PEAK. Forward of x_mb the envelope tapers f to
    close the deck at the stem, f changes station to station, and the
    constant-x topside still reads a max twist of 0.952 — the hypar's order of
    magnitude, concentrated in the forefoot. A machine-zero median with a
    0.95 peak is a panel that is developable over its run and emphatically not
    over its bow, which is a different and more useful statement than the one
    this test used to make.

        quantity                          BEFORE          AFTER
        constant-x  bottom  median        3.8e-15         3.5e-16
        constant-x  bottom  max           0.288           0.5415
        constant-x  topside median        0.617           1.5e-14
        constant-x  topside max           (> 0.9)         0.9520
        developable bottom  max           0.029           0.0341
        developable topside median        0.0074          0.0095
        developable topside max           0.432           0.3569

    The constant-x BOTTOM max nearly doubled, 0.288 -> 0.5415, and that is the
    same rebuild seen from the other side: the chine plan-form is no longer a
    free curve with its own exponent, it is SOLVED station by station from the
    sectional area curve, so the forefoot warp the bottom panel has to absorb
    is whatever the area curve and the 8 deg -> 30 deg deadrise ramp jointly
    demand rather than whatever a shaping exponent happened to give.

    AND THE FITTED RULINGS NOW MAKE THE TOPSIDE MEDIAN WORSE, NOT 83x BETTER.
    They give up 1.5e-14 -> 0.0095 in the median to buy 0.952 -> 0.357 on the
    peak. That is the right trade for a refold — the peak is where the panel
    misses the hull — but it is the exact opposite of the "83x better median"
    this test recorded, so it is asserted in the direction it actually runs.
    There is still no bar here that the fitted topside would pass and the hypar
    would fail; see test_gate6_refold_clause_is_red_on_the_hull for the cost."""
    hull = Hull(mid_params())
    bottom, topside = hull_panels(hull, rulings="constant-x")
    hypar = develop(*_hypar(41), "h").twist_median
    assert bottom.twist_median < 1e-9
    assert 0.45 < bottom.twist_max < 0.65

    # THE TWO ASSERTIONS THAT INVERTED, STATED AS INVERSIONS RATHER THAN
    # QUIETLY REWRITTEN. They were `0.4 < topside.twist_median < 0.8` and
    # `topside.twist_median > hypar * 0.9`; the constant-x topside is now
    # nine orders of magnitude BELOW the hypar it was said to be
    # indistinguishable from, and the aft run is exactly developable.
    assert topside.twist_median < 1e-9
    assert topside.twist_median < hypar * 1e-9
    assert topside.twist_max > 0.9      # ...and the forefoot peak survives

    fb, ft = hull_panels(hull, rulings="developable")
    assert fb.rulings == ft.rulings == "developable"
    assert fb.twist_max == pytest.approx(0.034, abs=0.010)
    assert ft.twist_max == pytest.approx(0.357, abs=0.050)
    assert ft.twist_median == pytest.approx(0.0095, abs=0.0040)
    assert ft.twist_max > 0.3          # the PEAK is not fixed, and is not hidden
    # The fitted topside sits 58x under the hypar's median, MEASURED. The
    # assertion is placed at 20x rather than the 50x this line used to carry,
    # because 0.0095 against hypar/50 = 0.0111 is a 14% margin on the root of a
    # Levenberg-Marquardt solve whose branch selection this file already records
    # as not bit-portable across platforms — and a bound that tight would be
    # measuring libm, not developability. The VALUE is pinned above.
    assert ft.twist_median < hypar / 20.0
    # ...and the fit PAYS in the median for that peak, which is the claim this
    # test used to make backwards.
    assert ft.twist_median > topside.twist_median * 1e6


# ---------------- G4: the refold ------------------------------------------

@pytest.mark.parametrize("fixture", [_true_cylinder, _cone])
def test_refold_of_a_true_developable_is_exact(fixture):
    """Gap G4: no code mapped 2-D back to 3-D, so Gate 6's clause 'exported
    panels re-fold to the hull within tolerance' was untested prose.

    The mechanism has to be shown correct before its verdict on the hull means
    anything: rolling a developable's flat pattern back up must land ON the
    surface. It lands within 0.0002 mm."""
    A, B = fixture()
    p = develop(A, B, "dev")
    dev = refold_deviation_mm(p)
    assert refold(p).shape == (len(A), 3)
    assert dev.max() < 1e-3, f"{dev.max():.6f} mm"


def test_gate6_refold_clause_is_red_on_the_hull():
    """STILL RED after the slanted-ruling fix. RECORDED, NOT SOFTENED.

    The clearing condition on Gate 6D's ledger entry was "solve for SLANTED
    rulings instead of constant-x ones". That is done — `developable_pairing`
    — and it does not clear the bar.

    THE WATERMARK MOVED, AND IT MOVED THE WRONG WAY: 66.2 -> 124.1 mm. It did
    that without the unroller changing at all. The geometry-kernel rebuild
    landed on 2026-08-13 (the sectional area curve and the design waterline
    became first-class design curves and the chine half-breadth is SOLVED from
    them), and the WORST PANEL CHANGED WITH IT — it is now the BOTTOM, not the
    topside. MEASURED on the reference hull at 41 stations, two-sided
    panel-vs-hull (`refold_surface_deviation_mm`), edge-only beside it:

        panel          constant-x                developable
                       BEFORE      AFTER         BEFORE      AFTER
        bottom-stbd    140.2       153.6         48.1        124.1
                      (edge 141.0)(edge 154.7)  (edge 29.2) (edge  29.9)
        topside-stbd   224.5       472.7         66.2         44.0
                      (edge 225.7)(edge 479.4)  (edge 66.2) (edge  43.7)

    Two mechanisms, both in the kernel and not in the unroller. The TOPSIDE
    improved 66.2 -> 44.0 because `w**0.15` is gone from the sheer and the
    topside is one straight run at the enveloped flare (see
    test_hull_panel_twist_is_recorded_not_blessed). The BOTTOM worsened
    48.1 -> 124.1 because its chine edge is no longer a free plan-form curve
    but the root of the section quadratic against the area curve, and the
    forefoot the fit now has to develop is harder.

    LOOK AT THE BOTTOM ROW OF THAT TABLE ONE MORE TIME: the developable bottom
    panel reads 29.9 mm on the EDGE and 124.1 mm on the SURFACE. That 4.2x gap
    is the defect
    `test_the_edge_only_refold_can_be_bought_and_the_two_sided_one_cannot`
    exists to name, present — bounded, but present — in the SHIPPED fit. It is
    the reason the watermark is the two-sided number and would have been
    invisible under the edge-only one, which barely moved (29.2 -> 29.9).

    So: 124.1 mm against a 5 mm bar is 25x out, where it was 13x out. It is RED
    by record and it stays RED by record, and the ledger's 66.2 is now stale —
    `data/gate-ledger.json` is not this file's to edit and the re-measurement
    is owed there.

    THE BAR IS UNTOUCHED. REFOLD_BAR_MM is still 5.0 and both panels and every
    station are still measured; what moved is the hull, not the accounting."""
    hull = Hull(mid_params())
    bottom, topside = hull_panels(hull)
    db = refold_deviation_mm(bottom)
    dt = refold_deviation_mm(topside)
    sb = refold_surface_deviation_mm(hull, bottom)
    st = refold_surface_deviation_mm(hull, topside)

    assert db.max() > REFOLD_BAR_MM and dt.max() > REFOLD_BAR_MM
    assert sb > REFOLD_BAR_MM and st > REFOLD_BAR_MM
    assert 26.0 < db.max() < 34.0, f"bottom edge {db.max():.1f} mm"
    assert 40.0 < dt.max() < 48.0, f"topside edge {dt.max():.1f} mm"
    assert 118.0 < sb < 130.0, f"bottom surface {sb:.1f} mm"
    assert 40.0 < st < 48.0, f"topside surface {st:.1f} mm"
    # the ledger watermark is the worse of the two panels, two-sided
    assert max(sb, st) == pytest.approx(124.1, abs=4.0)
    # ...and it is the BOTTOM panel that carries it now. Asserted, because the
    # ledger prose names the topside and a silent swap of which panel is worst
    # is how a watermark goes stale without any number visibly changing.
    assert sb > st


def test_the_constant_x_control_is_worse_on_both_panels_and_both_metrics():
    """THE GUARD, MADE TO FIRE (defect class 3). The fix is a change of ruling
    family, so the only way to show it is a fix is to run the VERBATIM old
    ruling selection through the same measurement and watch it lose.

    `rulings="constant-x"` is that old selection — station i paired with
    station i — and it is kept executable for exactly this reason. It must be
    worse on BOTH panels under BOTH metrics, or the improvement is an artefact
    of how the number is taken.

    THE CLAIM SURVIVES THE 2026-08-13 GEOMETRY REBUILD. THE MARGIN DOES NOT,
    ON ONE CELL OF FOUR, AND THAT CELL IS THE INTERESTING ONE. This test
    asserted `n < o / 2.0` on all four (panel, metric) pairs. MEASURED:

        panel         metric     constant-x   developable   margin
        bottom-stbd   edge         154.7         29.9        5.17x
        bottom-stbd   surface      153.6        124.1        1.24x   <-- was 2.9x
        topside-stbd  edge         479.4         43.7       10.97x
        topside-stbd  surface      472.7         44.0       10.75x

    The bottom panel's TWO-SIDED margin collapsed from 2.9x (140.2 / 48.1) to
    1.24x, while its EDGE margin went the other way, 1.0x to 5.17x. The fit is
    buying the edge and leaving the surface: 29.9 mm on the far edge with the
    panel 124.1 mm off the hull. That is the same trade
    `test_the_edge_only_refold_can_be_bought_and_the_two_sided_one_cannot`
    forces to its extreme, appearing under the shipped `_MAX_RULING_STEP`.

    So the `/2.0` is asserted where it holds and the fourth margin is asserted
    AS MEASURED, with a floor of 1.0 on all four. A blanket `/2.0` would now be
    a failing test, and a blanket `< 1.0` would be a test that could not notice
    the collapse — neither is the honest statement.

    THE CONSTANT-X BOTTOM FIGURE IS A BAND, NOT A VALUE. At 41 stations it is
    bistable under a one-ULP nudge, 150.4 .. 154.7 mm edge and 149.4 .. 153.6
    surface — see
    `test_the_constant_x_refold_at_161_stations_is_decided_by_roundoff`, whose
    onset moved DOWN from n >= 81 to n >= 41 in the same rebuild. Every margin
    above is quoted at the attractor this machine lands on and asserted at a
    bound that holds at BOTH attractors."""
    hull = Hull(mid_params())
    old = {p.name: p for p in hull_panels(hull, rulings="constant-x")}
    new = {p.name: p for p in hull_panels(hull, rulings="developable")}
    margin = {}
    for name in ("bottom-stbd", "topside-stbd"):
        o, n = old[name], new[name]
        assert o.rulings == "constant-x" and n.rulings == "developable"
        margin[name, "edge"] = (refold_deviation_mm(o).max()
                                / refold_deviation_mm(n).max())
        margin[name, "surface"] = (refold_surface_deviation_mm(hull, o)
                                   / refold_surface_deviation_mm(hull, n))

    # THE CLAIM: worse on both panels under both metrics. This is what has to
    # hold for the fitted family to be a fix at all, and it is unchanged.
    for k, m in margin.items():
        assert m > 1.0, f"constant-x is not worse on {k[0]} {k[1]}: {m:.3f}x"

    # THE MARGINS, as measured. Three of the four keep the 2x this test was
    # written with; the fourth is pinned at what it is so a further collapse
    # toward 1.0 — the fit ceasing to be an improvement at all — fails here.
    assert margin["bottom-stbd", "edge"] > 4.0
    assert margin["topside-stbd", "edge"] > 8.0
    assert margin["topside-stbd", "surface"] > 8.0
    assert 1.1 < margin["bottom-stbd", "surface"] < 1.4, (
        f"bottom two-sided margin {margin['bottom-stbd', 'surface']:.3f}x")

    # ...and the old family really is the recorded watermark, so a future
    # reader can tell an improvement from a re-measurement. BEFORE 2026-08-13,
    # on the old geometry kernel: 141.0 and 225.7 mm. The bottom is asserted as
    # the whole one-ULP band because that is the honest extent of the number.
    assert 148.0 < refold_deviation_mm(old["bottom-stbd"]).max() < 157.0
    assert refold_deviation_mm(old["topside-stbd"]).max() == pytest.approx(
        481.3, abs=6.0)


def test_the_edge_only_refold_can_be_bought_and_the_two_sided_one_cannot():
    """WHY GATE 6D'S WATERMARK IS NOT `refold_deviation_mm` ANY MORE.

    `refold_deviation_mm` watches the panel's far EDGE. A pairing free to take
    an arbitrarily long ruling step reaches machine-zero quad warp — the strip
    really is developable — by dumping metres of chine into ONE quad. The edge
    lands on the chine at both ends of that quad, so the edge metric reads
    almost nothing; the chord in between misses the chine by two orders of
    magnitude more, and every point of that chord lies between keel and chine
    (i.e. ON the hull surface), so a one-sided panel->hull test scores it
    perfect too.

    THE TRADE GOT WORSE ON THE REBUILT KERNEL, WHICH IS WHY THIS TEST HAD TO
    CHANGE SHAPE. MEASURED on the reference hull's bottom panel at 41 stations
    with `_MAX_RULING_STEP` removed:

        quantity                     BEFORE          AFTER
        longest ruling step          1.843 m         1.766 m
          ...as multiples of h        7.4x            7.06x
        edge-only refold             0.20 mm         0.070 mm
        two-sided panel-vs-hull      97.5 mm       263.3 mm

    3760x between the two metrics on the same panel, against 490x before.

    AND THE ACCEPTANCE GUARD NOW REFUSES IT, WHICH THIS TEST USED TO RECORD THE
    OPPOSITE OF. The old prose said "the acceptance guard in `hull_panels`
    still ACCEPTS the uncapped fit — 97.5 mm is better than the 140.2 mm
    constant-x panel it replaces". That is REFUTED: 263.3 mm is worse than the
    153.6 mm constant-x panel, so `hull_panels` falls back and returns a
    `rulings="constant-x"` panel. Good news, and it is exactly why the
    demonstration can no longer be taken through `hull_panels` — the fallback
    hides the very object under test. The uncapped pairing is therefore built
    here the way `hull_panels` builds it, `developable_pairing` + `develop`,
    with the guard out of the way, and the guard's refusal is asserted
    SEPARATELY as the second line of defence it now is.

    Nothing about that makes `_MAX_RULING_STEP` or the two-sided metric
    redundant. The guard only compares against the constant-x control; a fit
    that beat that control while still 200 mm off the hull would pass it. The
    bound and the metric are what stop the trade, and the guard is what catches
    the residue."""
    from dataclasses import replace

    from navalai.unroll import developable_pairing

    hull = Hull(mid_params())
    x = np.asarray(hull.x, dtype=float)
    h = float(x[-1] - x[0]) / (len(x) - 1)

    saved = unroll._MAX_RULING_STEP
    try:
        unroll._MAX_RULING_STEP = 1e9
        v = developable_pairing(hull, 0, 1)
        loose = replace(develop(hull.edge_curves(x)[0],
                                hull.edge_curves(v)[1], "bottom-stbd"),
                        rulings="developable", par_a=x.copy(),
                        par_b=np.asarray(v).copy())
        refused = hull_panels(hull)[0]
    finally:
        unroll._MAX_RULING_STEP = saved

    step = float(np.diff(loose.par_b).max())
    assert step > 6.0 * h, f"max ruling step {step:.3f} m"
    assert np.all(np.diff(loose.par_b) > 0.0)      # it is a monotone pairing
    assert refold_deviation_mm(loose).max() < 1.0        # the edge is perfect
    assert refold_surface_deviation_mm(hull, loose) > 200.0  # the panel is not
    assert (refold_surface_deviation_mm(hull, loose)
            > 1000.0 * refold_deviation_mm(loose).max())

    # THE GUARD, FIRED. With the bound removed the two-sided acceptance test in
    # `hull_panels` throws the fit away and ships the constant-x control. This
    # assertion is the inversion of the sentence this test used to carry, and
    # it is written out rather than deleted.
    assert refused.rulings == "constant-x"

    # ...and the shipped bound refuses the trade before the guard has to. The
    # bound is a PENALTY, not a constraint, so it can in principle be exceeded;
    # MEASURED, at the weight used it is overshot by 2.8e-8 m (it was 4e-9
    # before the rebuild), and 1 micron is the bar this asserts.
    tight = hull_panels(hull)[0]
    assert tight.rulings == "developable"
    assert float(np.diff(tight.par_b).max()) <= 4.0 * h + 1e-6
    # 124.1 mm, MEASURED — it was 48.1 mm before the rebuild, and the number is
    # the Gate 6D watermark, not a tolerance. What this asserts is the
    # RELATION: bounding the step is worth better than 2x on the metric that
    # decides, which is the claim, and it holds at whatever the hull measures.
    assert (refold_surface_deviation_mm(hull, tight)
            < refold_surface_deviation_mm(hull, loose) / 2.0)
    assert 118.0 < refold_surface_deviation_mm(hull, tight) < 130.0


def test_fitted_rulings_span_the_whole_edge_and_do_not_cross():
    """A slanted-ruling fit is only a panel if its rulings sweep the strip once
    and both edges are still the WHOLE edge. Pinning the endpoints is what
    stops the fit from clearing the bar by developing a convenient part of the
    hull, which is the other way the metric could have been bought."""
    hull = Hull(mid_params())
    for p in hull_panels(hull):
        assert p.par_b[0] == pytest.approx(hull.x[0])
        assert p.par_b[-1] == pytest.approx(hull.x[-1])
        assert np.all(np.diff(p.par_b) > 0.0)
        assert rulings_that_cross(p) == 0, p.name
        assert not np.allclose(p.par_b, p.par_a)   # they really are slanted


def test_no_exact_developable_spans_the_bottom_panels_two_edges():
    """MECHANISM (a) behind the residual 46 mm, kept executable.

    Marching the planar-quad condition forward from the transom — keel at the
    hull's own stations, chine parameter chosen so each quad is planar — the
    march TERMINATES at keel x = 7.25 m of 10.00 m: the plane through the
    current ruling and the next keel point no longer meets the chine ahead of
    the current chine parameter. The developable generated off this keel runs
    out of chine before it runs out of keel, so there is no exact developable
    with both ends pinned, and no ruling selection can produce one."""
    hull = Hull(mid_params())
    grid = np.linspace(0.0, float(hull.x[-1]), 40001)
    chine = hull.edge_curves(grid)[1]
    v, reached = 0.0, 0
    for i in range(len(hull.x) - 1):
        a0, a1 = hull.edge_curves(hull.x[i:i + 2])[0]
        b0 = hull.edge_curves(np.array([v]))[1][0]
        f = (chine - a0) @ np.cross(a1 - a0, b0 - a0)
        j0 = int(np.searchsorted(grid, v + 1e-9))
        k = np.where(np.diff(np.sign(f[j0:])) != 0)[0]
        if not len(k):
            break
        j = j0 + int(k[0])
        t = abs(f[j]) / (abs(f[j]) + abs(f[j + 1]))
        v = grid[j] + t * (grid[j + 1] - grid[j])
        reached = i + 1
    assert reached < len(hull.x) - 1, "the march completed; re-derive (a)"
    assert float(hull.x[reached]) == pytest.approx(7.25, abs=0.5)


def test_the_sheer_polyline_is_already_off_the_sheer_curve():
    """MECHANISM (b), AND IT HAS BEEN REMOVED. THIS TEST NOW RECORDS ITS OWN
    REFUTATION, WHICH IS WHY IT IS STILL HERE.

    WHAT THIS TEST USED TO FIND, verbatim: "`y_sheer = ys * w**0.15` sends
    dy/dx to infinity at the stem, so the sheer is not resolvable by uniform
    stations: the 41-station polyline misses the curve by 65.6 mm before
    developability is asked about, and it converges at roughly O(h^0.5) — 81.0
    / 65.6 / 47.3 / 29.9 mm at 21 / 41 / 81 / 161. The topside panel's 82.2 mm
    therefore is NOT mostly a ruling problem, and no unroller change will move
    it."

    EVERY CLAUSE OF THAT IS NOW FALSE, and none of it was fixed in the
    unroller. The 2026-08-13 geometry-kernel rebuild deleted the `w**0.15`
    envelope: `geometry._stations` runs the topside as one straight line from
    the chine at the enveloped flare, `ys = yc + (zs - zc) * f`, so the sheer
    inherits the chine's plan-form and the flare's taper and has no unbounded
    derivative anywhere.

        41-station chord error, sheer          65.6 mm  ->   8.75 mm   (7.5x)
        convergence order over 21 -> 161      O(h^0.5)  ->  O(h^1.72)

        n_stations        21      41      81     161
        BEFORE  sheer   81.0    65.6    47.3    29.9   mm
        AFTER   sheer   28.72    8.75    2.18    0.797 mm

    THE FLOOR THE TOPSIDE PANEL SAT ON IS GONE, and the topside panel came off
    it: 66.2 -> 44.0 mm two-sided (see
    test_gate6_refold_clause_is_red_on_the_hull). The residual IS mostly a
    ruling problem now — 44.0 mm of panel error over an 8.75 mm chord error —
    which is the opposite of the sentence this test was written to support.

    AND THE TWO EDGES SWAPPED PLACES. The old finding leaned on the chine being
    the well-behaved edge, "whose plan-form carries no such exponent, reads
    3.4 mm at the same 41 stations". The chine is now the WORSE of the two at
    10.64 mm, because it is no longer a shaping curve at all: it is the root of
    the section quadratic, solved station by station against the sectional area
    curve, so it carries whatever curvature the area curve demands. The keel,
    which the old kernel never had trouble with either, reads 0.573 mm.

    So the assertion inverts — `< 5.0` on the chine becomes `> the sheer` — and
    it is written out rather than dropped, because "the chine is the easy edge"
    is exactly the kind of remembered fact that would otherwise survive into
    the next person's reasoning."""
    got = []
    for n in (21, 41, 81, 161):
        hull = Hull(mid_params(), n_stations=n)
        got.append(_chord_error_mm(hull, 2, hull.x))
    assert got[1] == pytest.approx(8.75, abs=0.60)
    assert Hull(mid_params()).x.size == 41

    # THE ASSERTION THAT INVERTED. It was `order < 0.75` — "a 4x refinement
    # buys less than 2.5x, i.e. nowhere near O(h^2)". An 8x refinement now buys
    # 36x. It is still not O(h^2), and the shortfall is the flare envelope's
    # own kink at the max-area station, not an unbounded derivative.
    order = np.log(got[0] / got[3]) / np.log(8.0)
    assert order > 1.5, f"sheer chord error converges at O(h^{order:.2f})"
    assert order < 2.1, f"sheer chord error converges at O(h^{order:.2f})"

    # THE OTHER INVERSION: the chine is now the worse edge, not the better one.
    hull = Hull(mid_params())
    chine = _chord_error_mm(hull, 1, hull.x)
    keel = _chord_error_mm(hull, 0, hull.x)
    assert chine == pytest.approx(10.6, abs=1.0)
    assert chine > got[1], "the chine used to be the well-behaved edge"
    assert keel < 1.0


def test_refold_does_not_converge_with_station_count():
    """A refold error that shrank under refinement would be a discretisation
    artefact of the development, not a statement about the panel.

    It does not, on EITHER ruling family. What changed on 2026-08-12 is the
    STATION COUNTS this is asked at, because one of them was asking about a
    number that does not exist — see
    `test_the_constant_x_refold_at_161_stations_is_decided_by_roundoff` below,
    which is the finding, not the fix.

      constant-x   21 -> 41 stations (2x):  142.5 -> 154.7 mm, i.e. WORSE
      developable  41 ->  81 stations (2x):   43.7 ->  63.6 mm, also worse,
        because refinement pushes the sheer/chine chord error down while
        leaving the pairing a harder problem in 79 unknowns instead of 39.

    Either way the miss is geometry.

    THE DEVELOPABLE FAMILY GETS ITS RATIO BACK, at a different pair. On
    2026-08-12 it was demoted to a bare magnitude because 41 -> 161 was not
    reproducible across platforms (this Mac 1.553, ubuntu-latest 0.839 — the
    error shrank there and grew here). MEASURED on the rebuilt kernel, 8
    one-ULP perturbations of the 3-D datum edges, worst panel:

        family        n=21             n=41              n=81
        developable   142.4 (1.001x)   43.6..43.9        63.55 (1.000x)
                                         (1.006x)

    41 and 81 are both computable, so the ratio 43.7 -> 63.6 IS a function of
    its input and is asserted as one. 161 stays withdrawn: at 161 the bottom
    panel's fit loses the acceptance guard and falls back to constant-x, which
    at that count spans 22.3 .. 157.2 mm under one ULP (7.0x). That is the
    SAME withdrawal as 2026-08-12, one level further down, and it is driven by
    the measurement below rather than by the number being inconvenient.

    THE CONSTANT-X PAIR IS NOW ASKED ACROSS AN ILL-POSED ENDPOINT AND SAYS SO.
    Its n=41 value is bistable at 150.4 / 154.7 mm (spread 1.029x), where it
    was 1.004x before the rebuild. The RATIO nevertheless survives: 150.4/142.6
    = 1.055 at one attractor and 154.7/142.4 = 1.087 at the other, so the whole
    band lies inside [1.0, 1.2] and the CONCLUSION — refinement makes it worse
    — holds at both roots even though the value does not. That is stated rather
    than hidden; if the attractors ever separate enough to straddle 1.0, this
    pair must be withdrawn too, not re-banded.

    NEITHER BAND MOVED where it applies: [1.0, 1.2] is the constant-x bar
    recorded on 2026-08-11. [1.2, 2.0] on the developable pair is NEW — there
    was no ratio bar on that family to move, and it is set around a measured
    1.45 rather than inherited.
    """
    def edges(rulings, n):
        """max refold_deviation_mm per panel, and over both panels."""
        d = {p.name: float(refold_deviation_mm(p).max())
             for p in hull_panels(Hull(mid_params(), n_stations=n), rulings)}
        return d, max(d.values())

    cx21, cx21_worst = edges("constant-x", 21)
    cx41, cx41_worst = edges("constant-x", 41)
    dv41, dv41_worst = edges("developable", 41)
    dv81, dv81_worst = edges("developable", 81)

    # PER PANEL, BOTH FAMILIES, BOTH DIRECTIONS ON THE RECORD. The two panels
    # do NOT move together, and that is the point: under the same 2x refinement
    # the developable topside IMPROVES 2.1x while the developable bottom
    # WORSENS 2.1x. A test watching either one alone would report convergence
    # or divergence according to which panel it happened to pick — and the
    # version of this test that stood until 2026-08-13 picked `[0]`, the
    # bottom, for both families.
    #
    #   family        panel           coarse       fine        ratio
    #   constant-x    bottom-stbd     142.5 (21)   154.7 (41)   1.086
    #   constant-x    topside-stbd     76.4 (21)   479.4 (41)   6.272
    #   developable   bottom-stbd      29.9 (41)    63.6 (81)   2.124
    #   developable   topside-stbd     43.7 (41)    20.5 (81)   0.470
    #
    # THE RECORDED 2026-08-11 BAR, UNMOVED, on the panel it was recorded for.
    r = cx41["bottom-stbd"] / cx21["bottom-stbd"]
    assert 1.0 <= r <= 1.2, f"constant-x bottom: fine/coarse = {r:.3f}"

    # THE WATERMARK QUANTITY is the WORST panel — that is what Gate 6D records
    # and what `test_gate6_refold_clause_is_red_on_the_hull` asserts — so the
    # non-convergence claim is made on it as well. Both bands are NEW: neither
    # was measured on the worst panel before, so nothing here is a widened bar.
    r = cx41_worst / cx21_worst
    assert 3.0 <= r <= 3.8, f"constant-x worst: fine/coarse = {r:.3f}"
    r = dv81_worst / dv41_worst
    assert 1.2 <= r <= 2.0, f"developable worst: fine/coarse = {r:.3f}"

    # THE OPPOSITE DIRECTIONS ARE ASSERTED, NOT MERELY TABULATED. This is the
    # fact that makes the worst-panel framing necessary rather than a taste,
    # and a table in a comment cannot fail when it stops being true.
    assert dv81["bottom-stbd"] > dv41["bottom-stbd"], "developable bottom"
    assert dv81["topside-stbd"] < dv41["topside-stbd"], "developable topside"
    assert cx41["topside-stbd"] > cx21["topside-stbd"], "constant-x topside"

    # AND THE MAGNITUDE, AT EVERY COMPUTABLE COUNT, BECAUSE A RATIO ALONE
    # CANNOT SAY WHETHER THE PANELS ARE BUILDABLE.
    #
    # 161 IS NOT ONE OF THOSE COUNTS AND THE REASON CHANGED. Until 2026-08-12
    # the developable ratio was asked at 41 -> 161 and was not a function of its
    # input across platforms: this Mac measured 1.553 where ubuntu-latest
    # measured 0.839 on the same commit, via `developable_pairing`'s
    # Levenberg-Marquardt solve landing on a DIFFERENT ROOT. On the rebuilt
    # kernel there is a second, simpler reason on top of it: at 161 stations the
    # bottom panel's fit LOSES the acceptance guard in `hull_panels` and falls
    # back to constant-x, and the constant-x bottom at 161 spans 22.3 .. 157.2
    # mm under a one-ULP nudge (7.0x — see the test below). So the worst panel
    # at 161 is a roundoff-decided number wearing a `rulings="constant-x"`
    # label, and it is withdrawn rather than banded.
    #
    # A one-ULP sweep does NOT catch the LM root problem, and the reason is
    # worth stating so the next person does not repeat the mistake: perturbing
    # `src_a` AFTER `hull_panels()` has run measures `refold` given a FIXED
    # pairing. The pairing is what moves. Within one machine it is
    # deterministic — three runs give identical par_b to nine decimals — so
    # only a cross-platform comparison exposes it.
    #
    # THE TRIPWIRE MOVED FROM 10x THE BAR TO 5x, AND THE OLD FIGURE WAS THE
    # BUG, NOT THE BASELINE. 10 * REFOLD_BAR_MM is 50 mm, and the worst
    # developable panel at 41 stations now measures 43.7 mm — so the old
    # tripwire sits ABOVE the current measurement and would fire on a hull that
    # is still 8.7x outside the bar. It is a TRIPWIRE, not a bar: REFOLD_BAR_MM
    # is 5.0 and is asserted directly in
    # test_gate6_refold_clause_is_red_on_the_hull. At 5x it still fires after a
    # 1.75x improvement on the tightest count measured here, which is long
    # before anything could be mistaken for passing.
    #
    #     n_stations      21       41       81
    #     worst [mm]     142.4     43.7     63.6      (1.001x / 1.006x / 1.000x
    #                                                  under 16 one-ULP nudges)
    for n in (21, 41, 81):
        worst = max(refold_deviation_mm(p).max()
                    for p in hull_panels(Hull(mid_params(), n_stations=n),
                                         "developable"))
        assert worst > 5.0 * REFOLD_BAR_MM, (
            f"developable at {n} stations refolds to {worst:.1f} mm — if this "
            f"ever approaches the {REFOLD_BAR_MM} mm bar, Gate 6D's watermark "
            f"is stale and the ledger must be re-measured, not this test")


def _refold_under_1ulp(n_stations, rulings, seed):
    """`refold_deviation_mm` of the bottom panel with the 3-D datum edges
    nudged by one unit in the last place — the size of a difference between
    two correctly-rounded `libm` implementations."""
    panel = hull_panels(Hull(mid_params(), n_stations=n_stations), rulings)[0]
    rng = np.random.default_rng(seed)
    for edge in (panel.src_a, panel.src_b):
        edge *= 1.0 + 1e-16 * rng.standard_normal(edge.shape)
    return refold_deviation_mm(panel).max()


def test_the_constant_x_refold_at_161_stations_is_decided_by_roundoff():
    """THE DEFECT macOS WAS HIDING, and it is worth more than the CI fix that
    found it.

    MOTIVATING INCIDENT, CI run 31611386179 on ubuntu-latest. The test above
    passed here (Apple Accelerate) and failed there:

        AssertionError: constant-x: fine/coarse = 0.17
        assert 1.0 <= 0.17403726874190614

    0.174 is not a rounding difference, it is a DIFFERENT ANSWER: 24.534 mm
    where this machine reads 143.799 mm at the same 161 stations, on the same
    committed code, from the same inputs.

    THE MECHANISM is a square-root branch point in a marching reconstruction,
    not a BLAS or LAPACK convention — there is no SVD, eigendecomposition,
    least squares or rotation fit anywhere in the constant-x refold path, and
    pinning the thread counts changes nothing. `unroll._trilaterate` computes
    the out-of-plane offset as `sqrt(max(r1^2 - x^2 - y^2, 0))`, and that
    radicand is ZERO exactly when the quad is planar. The aft bottom panel is
    planar to machine precision — `unroll` already records that it "refolds to
    0.008 mm" and that "the sign flips 63 times" — so the sphere intersection
    is tangential over most of the panel, `d(sqrt(a))/da = 1/(2 sqrt(a))`
    amplifies by a measured geometric mean of ~650 per step, and `refold`
    feeds each reconstructed point into the next. Over 160 steps the result is
    BISTABLE: two widely separated attractors and nothing in between.

    MEASURED HERE, 16 one-ULP perturbations of the 3-D datum edges, max
    `refold_deviation_mm` of `bottom-stbd` in mm. BEFORE is 2026-08-12 on the
    old geometry kernel; AFTER is 2026-08-13 on the rebuilt one:

        n      BEFORE band          spread    AFTER band            spread
        21     139.706 .. 139.765   1.000x    142.428 .. 142.551    1.001x
        41     140.452 .. 141.010   1.004x    150.411 .. 154.743    1.029x
        81      67.641 .. 142.699   2.110x     50.072 .. 156.267    3.121x
       161      24.534 .. 143.799   5.861x     22.329 .. 157.247    7.042x
       321      11.571 .. 144.492  12.487x     10.755 .. 157.812   14.673x

    THE ONSET MOVED DOWN ONE REFINEMENT LEVEL, AND THIS TEST NOW ASSERTS THAT
    RATHER THAN THE OPPOSITE. It used to pin 41 as COMPUTABLE — "so the refusal
    cannot creep down onto counts that are fine" — and 41 is no longer fine:
    two attractors 2.9% apart where there was one. The last computable count is
    21. That is an inversion of a previously asserted fact and it is written
    out as one; a bistability that has spread to a coarser grid is a finding,
    not a tolerance to widen.

    THE MECHANISM IS UNCHANGED and the rebuild did not touch it: `_trilaterate`
    still takes `sqrt(max(r1^2 - x^2 - y^2, 0))`, the radicand is still zero
    exactly when the quad is planar, and the constant-x bottom panel is still
    planar over its run — its median ruling twist measures 3.5e-16 on the
    rebuilt kernel (`test_hull_panel_twist_is_recorded_not_blessed`). What
    moved is WHERE the amplification first outruns float64, and that is a
    MEASURED onset, not a derived one: no attempt is made here to say why the
    rebuilt chine crosses it at 41 rather than 81.

    The 2026-08-12 CI value, 24.534 / 140.997 = 0.17400, was the low attractor
    at 161 over the then-stable 41 — i.e. the Linux answer was reproduced here
    exactly, by a one-ULP nudge. Higher precision does not help: the same
    computation in `decimal` at 20 through 2000 digits returns one of the same
    two values and flips between them non-monotonically. This is ill-posed, not
    precision-limited.

    So this test asserts the honest statement — that the 161-station number is
    NOT A MEASUREMENT — by feeding the computation the verbatim perturbation
    it cannot survive (docs/LESSONS.md defect class 3), and it pins 21 as the
    count that still is one.

    IF THIS TEST EVER FAILS BECAUSE THE SPREAD COLLAPSED, that is good news
    and it must be re-measured, not deleted: it would mean the branch point
    was removed (a noise-floor snap in `_trilaterate` was measured NOT to do
    this) and the n>=81 figures could be quoted again.

    THE THREE OWED WITHDRAWALS ARE DONE (C-36, 2026-08-18): `navalai/
    unroll.py` records "143.8 mm stood here until 2026-08-12 and IS NOT A
    COMPUTABLE NUMBER"; `tests/test_gaps.py`'s alignment text quotes the
    bistable RANGE instead of a figure; and the Gate 6D ledger prose now
    withdraws its 143.1 / 203.4 by name.

    ~~GATE 6D'S WATERMARK ITSELF DOES NOT MOVE: 66.2 mm is the DEVELOPABLE
    family at 41 stations, which is stable (spread 1.000x), and it is
    unaffected.~~ SUPERSEDED 2026-08-13. The watermark DID move, for a reason
    that has nothing to do with this test: the geometry-kernel rebuild took the
    worst developable panel from 66.2 mm to **124.1 mm** and moved it from the
    topside to the bottom. It is still measured at 41 stations and it is still
    the stable quantity — the DEVELOPABLE bottom panel spans 29.922 .. 29.944
    mm edge-only under one ULP (1.001x) even though the CONSTANT-X bottom panel
    at the same count does not. Those are two different pairings and only one
    of them is ill-posed here. See
    test_gate6_refold_clause_is_red_on_the_hull; the ledger re-measurement is
    owed there and not in this file.
    """
    seeds = range(16)
    at21 = [_refold_under_1ulp(21, "constant-x", s) for s in seeds]
    at41 = [_refold_under_1ulp(41, "constant-x", s) for s in seeds]
    at161 = [_refold_under_1ulp(161, "constant-x", s) for s in seeds]

    assert max(at21) / min(at21) < 1.02, (
        f"21 stations must still be computable: {min(at21):.3f} .. "
        f"{max(at21):.3f} mm — if this widened, there is no count left at "
        f"which the constant-x bottom panel has a value, and every ratio "
        f"quoted on that family must be withdrawn")
    assert 141.5 < np.median(at21) < 143.5, (
        "and it must still be the measured 142.5 mm, so a collapse of the "
        "spread cannot be mistaken for stability at a different value")

    # THE ASSERTION THAT INVERTED ON 2026-08-13. It read
    # `max(at41)/min(at41) < 1.02` with the comment "41 stations must still be
    # computable". It is not: 150.411 .. 154.743 mm, spread 1.029x, two
    # attractors 2.9% apart. The bound is stated in the direction it now runs
    # so that a RETURN to computability at 41 also fails here and gets
    # re-measured — the spread collapsing is good news either way, and the
    # thing this test must never do is silently accept both answers.
    assert max(at41) / min(at41) > 1.02, (
        f"41 stations read {min(at41):.3f} .. {max(at41):.3f} mm under a "
        f"one-ULP nudge (spread {max(at41)/min(at41):.4f}x). If this is now "
        f"under 1.02x the branch point has moved back up and the n = 41 "
        f"figures can be quoted again — RE-MEASURE the table above, and the "
        f"ratio bands in test_refold_does_not_converge_with_station_count "
        f"which are asserted across this endpoint")
    assert min(at41) < 152.0 < max(at41), (
        "the two attractors must still straddle 152 mm, so a band that has "
        "widened for some other reason is not mistaken for this one")

    assert max(at161) / min(at161) > 2.0, (
        f"161 stations read {min(at161):.3f} .. {max(at161):.3f} mm under a "
        f"one-ULP nudge (spread {max(at161)/min(at161):.2f}x). If this is "
        f"now under 2x, RE-MEASURE the whole table above and re-open the "
        f"n>=81 figures — do not delete this test")
    assert min(at161) < 100.0, (
        "the low attractor is what CI landed on (24.5 mm); a band that is "
        "wide but never reaches it is a different phenomenon")


def test_refold_refuses_a_panel_it_cannot_locate():
    """A FlatPanel built by hand carries no 3-D datum; refolding it would have
    to invent the jig line. It refuses instead of guessing."""
    from navalai.unroll import FlatPanel
    p = FlatPanel("hand-made", np.zeros((3, 2)), np.ones((3, 2)), 0.0)
    with pytest.raises(ValueError, match="3-D edges"):
        refold(p)


# ---------------- G2: real nesting ----------------------------------------

def test_the_hull_panels_fit_no_sheet_at_all():
    """The incident, asserted so it cannot be forgotten: the developed panels
    measure 10.02 x 1.54 m and 10.57 x 1.55 m against a 1.22 x 2.44 m sheet.
    `export_dxf` used to draw them whole, offset in y.

    (BEFORE the 2026-08-13 geometry rebuild: 10.05 x 1.62 m and 10.54 x 1.44 m.
    The assertion is on the LENGTH, which is 4x the sheet either way, so the
    finding does not depend on these four figures — they are recorded because a
    developed panel size is the one number a boatbuilder checks first.)"""
    for p in hull_panels(Hull(mid_params())):
        w, h, _ = min_area_rect(p.outline)
        assert max(w, h) > SHEET_L_M * 3, f"{p.name}: {w:.2f} x {h:.2f} m"


def test_split_panel_produces_pieces_that_fit_a_sheet():
    """Every piece, including its scarph flanges, fits the stock sheet."""
    t = 0.015
    allow = SCARPH_RATIO * t / 2.0
    for panel in hull_panels(Hull(mid_params())):
        parts = split_panel(panel, t)
        assert len(parts) > 1
        for q in parts:
            w, h, _ = min_area_rect(q.outline)
            assert min(w, h) + 2 * allow <= SHEET_W_M + 1e-9
            assert max(w, h) + 2 * allow <= SHEET_L_M + 1e-9


def test_scarph_allowance_is_eight_to_one_and_counted_once():
    """A plywood scarph is 8:1 on thickness, and the two tapers OVERLAP: one
    joint costs 8t of extra material in total, so each of the two pieces
    meeting there carries 4t — not 8t each, which would double the overlap."""
    t = 0.018
    parts = split_panel(hull_panels(Hull(mid_params()))[0], t)
    interior = [q for q in parts if "0 scarph" not in q.note]
    assert interior, "a split panel with no scarph joints is not a split panel"
    for q in interior:
        w, h, _ = min_area_rect(q.outline)
        n_edges = int(q.note.split(" scarph")[0].split()[-1])
        assert q.scarph_m2 <= n_edges * (SCARPH_RATIO * t / 2.0) * max(w, h) + 1e-9
        assert q.scarph_m2 > 0.0


def test_every_placed_part_is_inside_its_sheet_and_overlaps_nothing():
    """What 'nesting' has to mean before the word is used: parts on sheets,
    inside the boundary, not on top of each other. The old layout had no sheet
    boundary to be inside of."""
    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    assert layout.sheets >= 2
    for pl in layout.placements:
        assert -1e-9 <= pl.x and pl.x + pl.w <= layout.sheet_w + 1e-9
        assert -1e-9 <= pl.y and pl.y + pl.h <= layout.sheet_l + 1e-9
        assert pl.polygon[:, 0].min() >= -1e-9
        assert pl.polygon[:, 1].min() >= -1e-9
        assert pl.polygon[:, 0].max() <= layout.sheet_w + 1e-9
        assert pl.polygon[:, 1].max() <= layout.sheet_l + 1e-9
    for i in range(layout.sheets):
        rs = [(p.x, p.y, p.w, p.h) for p in layout.on_sheet(i)]
        assert rs, f"sheet {i} is empty — the packer opened a sheet for nothing"
        for a in range(len(rs)):
            for b in range(a + 1, len(rs)):
                ax, ay, aw, ah = rs[a]
                bx, by, bw, bh = rs[b]
                overlap = (min(ax + aw, bx + bw) - max(ax, bx) > 1e-9
                           and min(ay + ah, by + bh) - max(ay, by) > 1e-9)
                assert not overlap, f"sheet {i}: parts {a} and {b} overlap"


def test_rotation_is_a_rotation_and_not_a_reflection():
    """'Nesting' with no rotation is stacking with extra steps, so the packer
    must demonstrably turn parts through 90 degrees — and turning them must not
    MIRROR them. `polygon[:, ::-1]` swaps x and y, which is a reflection: it
    yields the mirror image of the strake, a piece that will not fit the boat.
    A reflection flips the signed area; a rotation preserves it."""
    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    assert any(pl.rotated for pl in layout.placements)

    def signed_area(poly):
        x, y = poly[:, 0], poly[:, 1]
        return float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2

    for pl in layout.placements:
        if not pl.rotated:
            continue
        src = next(p for p in parts if pl.part.startswith(p.name))
        assert np.sign(signed_area(pl.polygon)) == np.sign(signed_area(src.outline))
        assert abs(signed_area(pl.polygon)) == pytest.approx(
            abs(signed_area(src.outline)), rel=1e-9)


def test_sheets_are_not_mixed_across_thicknesses():
    """You cannot cut a 21 mm bottom piece out of a 15 mm topside sheet. The
    sheet count is a sum over thickness groups, which is one reason a single
    area/SHEET_M2 division could never have been right."""
    panels = hull_panels(Hull(mid_params()))
    parts = split_panel(panels[0], 0.021) + split_panel(panels[1], 0.015)
    layout = nest(parts)
    for i, t in enumerate(layout.sheet_thickness_mm):
        for pl in layout.on_sheet(i):
            src = next(p for p in parts if pl.part.startswith(p.name))
            assert src.thickness_m * 1e3 == pytest.approx(t)


# ---------------- G2/C12: ply_sheets comes off the layout ------------------

def test_waste_factor_is_gone():
    """C12. `WASTE_FACTOR = 1.30` asserted a nesting waste that the layout
    could measure. There is nothing left to declare."""
    assert not hasattr(engineer, "WASTE_FACTOR")


def test_ply_sheets_is_counted_off_the_layout():
    """MEASURED, reference hull: 59 sheets at 80.9% utilisation, against the
    31 that `ceil(area * 1.30 / SHEET_M2)` returns on the same hull.

    The old number was not mostly wrong because 1.30 was a bad guess — the
    layout's own ratio of sheet area to part area comes out at 1.366. It was
    wrong because `area` was shell + deck ONLY (68.8 m^2) while the same report
    counted 7 bulkheads and a transom that consumed no material at all. The
    boat needs 128.6 m^2 of ply; 31 sheets is 92.3 m^2 of it.

    RE-MEASURED 2026-08-13 (geometry rebuild). BEFORE: 68 sheets, 76.8%, ratio
    1.36, shell+deck 79.5 m^2, ply 148.6 m^2, old estimate 35 sheets = 104.2
    m^2. The hull got smaller — `mid_params` went `forefoot` 0.85 -> 0.60 and
    `r_transom` 0.75 -> 0.30 — so every area fell together; the ARGUMENT is the
    gap between 31 and 59, and that widened from 1.94x to 1.90x, i.e. it is the
    same finding."""
    r = assess(Hull(mid_params()))
    assert 45 <= r.ply_sheets <= 75, r.ply_sheets
    # strictly more than the old `ceil(area * 1.30 / SHEET_M2)` estimate,
    # RECOMPUTED on this hull rather than quoted as the historical 35 — the
    # whole point is that the formula under-counts whatever hull it is given.
    assert r.ply_sheets > math.ceil(r.panel_area_m2 * 1.30 / SHEET_M2)
    assert 0.70 < r.nest_utilisation < 1.0
    assert r.sheet_area_m2 == pytest.approx(r.ply_sheets * SHEET_M2, abs=0.01)
    ply = [b for b in r.bom if b.material == "marine ply"]
    assert sum(b.area_m2 for b in ply) < r.sheet_area_m2   # cannot use more
    assert sum(b.area_m2 for b in ply) > r.panel_area_m2   # nor less than shell


def test_thicker_ply_costs_more_sheets():
    """The layout must respond to the scantling rule, or it is not a layout.
    mLDC 6000 kg drives the bottom to a stock sheet the 15 mm topsides
    cannot share.

    RE-MEASURED 2026-08-20, 21 mm -> 18 mm, and the reason is a rule change
    rather than a drift: this pin and its old docstring ("ISO 12215-5 wants
    18.24 mm") were both computed under the PRE-6R approximation. Gate 6R
    implemented ISO 12215-5:2008(E) from the operator's delivered text —
    kDC by category, Eq 3's kL with its continuity resolution, Eq 4's kAR
    with the AD cap, Table E.2's sigma_uf, and a per-sheet self-consistent
    ply count — and the requirement at this mLDC fell to 14.49 mm bare,
    landing on 18 mm once the ply count and the sheet are solved together.
    The CLAIM is unchanged and is what this test is for: the bottom does
    not share a sheet with the topsides, and the layout pays for it.
    """
    plain = assess(Hull(mid_params()))
    ruled = assess(Hull(mid_params()), mldc_kg=6000.0)
    assert ruled.bottom_thickness_mm == 18.0
    assert ruled.bottom_thickness_mm != plain.bottom_thickness_mm, (
        "the rule must move the sheet, or the layout is not responding")
    assert plain.bottom_thickness_mm == 15.0
    assert ruled.ply_sheets > plain.ply_sheets


# ---------------- G3: the BOM ---------------------------------------------

def test_bom_has_line_items_and_reconciles_with_the_layout():
    """G3: the report was three aggregate scalars. Every line now names its
    part, material, thickness, area, source panel and the SHEET it nests on,
    and those sheet numbers must be exactly the sheets the packer opened."""
    r = assess(Hull(mid_params()))
    assert len(r.bom) > 50
    ply = [b for b in r.bom if b.material == "marine ply"]
    assert {b.sheet for b in ply} == set(range(1, r.ply_sheets + 1))
    for b in ply:
        assert b.part and b.source_panel and b.note
        assert b.qty == 1 and b.area_m2 > 0.0 and b.thickness_mm > 0.0
        assert set(b.as_dict()) == {"part", "qty", "material", "thickness_mm",
                                    "area_m2", "source_panel", "sheet", "note"}
    # part names are unique, or a cut list cannot be followed
    assert len({b.part for b in r.bom}) == len(r.bom)
    # both sides of the boat are in it: the shell panels are developed to
    # starboard and built twice
    assert any(b.part.endswith("_2") for b in ply)


def test_bom_covers_every_structural_item_the_report_counts():
    """The old estimate counted 7 bulkheads and 18 frames in `panel_count` and
    then priced none of them. Every counted item must appear as line items."""
    r = assess(Hull(mid_params()))
    srcs = {b.source_panel for b in r.bom}
    assert {"bottom-stbd", "topside-stbd", "deck", "transom"} <= srcs
    assert sum(1 for s in srcs if s.startswith("bulkhead-")) == r.bulkheads
    frames = [b for b in r.bom if b.source_panel == "frames"]
    assert len(frames) == r.frames
    # frames are NOT sheet goods: counting a 2.5 x 1.0 m blank per ring frame
    # would inflate the sheet count with a fiction of the opposite sign.
    for b in frames:
        assert b.sheet is None and b.material == "laminated timber"


def test_bom_says_whether_the_bottom_thickness_is_rule_derived():
    """`limits.PLY_THICKNESS_M` is the NOMINAL sheet and failed ISO 12215-5 for
    every SKU in PLM.md. A BOM that prints 15 mm without saying which of the
    two it is invites the same contradiction back in."""
    plain = assess(Hull(mid_params()))
    ruled = assess(Hull(mid_params()), mldc_kg=6000.0)
    for r, expect in ((plain, "NOT rule-derived"), (ruled, "ISO 12215-5")):
        line = next(b for b in r.bom if b.source_panel == "bottom-stbd")
        assert expect in line.note


# ---------------- the nested DXF ------------------------------------------

def test_nested_dxf_draws_sheets_and_keeps_every_part_inside_one(tmp_path):
    """Gate R7's bar: 'a nested DXF whose declared units re-import at the right
    scale and whose panels fit real sheets'. Both halves, on the file."""
    panels = hull_panels(Hull(mid_params()))
    parts = []
    for p in panels:
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    path = export_dxf(layout, tmp_path / "nest.dxf")
    back = parse_dxf_polylines(path)

    sheets = {k: v for k, v in back.items() if k.startswith("SHEET-")}
    assert len(sheets) == layout.sheets
    for k, v in sheets.items():
        assert np.ptp(v[:, 0]) == pytest.approx(SHEET_W_M * 1000.0, abs=1.0)
        assert np.ptp(v[:, 1]) == pytest.approx(SHEET_L_M * 1000.0, abs=1.0)

    # the declared unit must be present, or "millimetres" is a habit rather
    # than a statement the importer can read
    head = path.read_text()
    assert "$INSUNITS" in head and "\n4\n" in head.split("$INSUNITS")[1][:20]

    for pl in layout.placements:
        pts = back[pl.part]
        ox = pl.sheet * (layout.sheet_w + 0.1) * 1000.0
        assert pts[:, 0].min() >= ox - 1.0
        assert pts[:, 0].max() <= ox + SHEET_W_M * 1000.0 + 1.0
        assert pts[:, 1].min() >= -1.0
        assert pts[:, 1].max() <= SHEET_L_M * 1000.0 + 1.0
        # ...and at the scale the header declares, not the metre values that
        # used to be written under no header at all
        assert np.ptp(pts[:, 0]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 0]), abs=1.0)


def test_export_dxf_nests_a_bare_panel_list_rather_than_stacking_it(tmp_path):
    """No caller can go back to stacking by accident: handing `export_dxf` the
    raw panels nests them here."""
    path = export_dxf(hull_panels(Hull(mid_params())), tmp_path / "auto.dxf")
    back = parse_dxf_polylines(path)
    assert any(k.startswith("SHEET-") for k in back)
    assert "bottom-stbd" not in back          # the whole panel is never drawn
    for k, v in back.items():
        if not k.startswith("SHEET-"):
            assert np.ptp(v[:, 0]) <= SHEET_W_M * 1000.0 + 1.0
            assert np.ptp(v[:, 1]) <= SHEET_L_M * 1000.0 + 1.0


# ---------------- A5: the export boundary ---------------------------------

def test_export_refuses_a_design_that_failed_the_ladder(tmp_path):
    """A5 had a fix and no test. An L0-failing hull exported to an 8,487-byte
    DXF and a 174,406-byte STEP without a murmur; `refuse_unvalidated` closed
    that and nothing pinned it shut."""
    from types import SimpleNamespace
    ev = SimpleNamespace(ok=False, tier="L0", violations=["deadrise.order"])
    with pytest.raises(ValueError, match="did not pass the ladder"):
        export_dxf(hull_panels(Hull(mid_params())), tmp_path / "no.dxf", ev=ev)
    assert not (tmp_path / "no.dxf").exists()
    # ev=None is the declared escape hatch for a deliberately unvalidated
    # artefact, and it must keep working
    export_dxf(hull_panels(Hull(mid_params())), tmp_path / "yes.dxf", ev=None)


# ---------------- G6: the exported solid IS the validated hull -------------

def test_step_export_lofts_denser_than_the_validated_discretisation(tmp_path):
    """G6, AND THE CLAIM IN THIS TEST'S OLD NAME IS NOW REFUTED.

    It was `test_step_export_defaults_to_the_validated_discretisation`, and it
    asserted `rec["n_stations_exported"] == hull.n_stations == 41` — the
    exporter must loft exactly the discretisation the ladder validated. That
    was the right fix for the original defect (a hard-coded 12 stations against
    a validated 41, MEASURED at **-0.539%**) and it is the WRONG resting place,
    because matching the ladder's station count does not make the loft the
    ladder's boat.

    MEASURED 2026-08-13. `Hull._section_at_rows` LERPS THE CONTROL POINTS
    between stations, so a loft through 41 stations describes the
    piecewise-linear-in-controls surface, while `hydrostatics.solve` trapezoids
    the EXACT areas at those same stations. Area is CONVEX in the control
    points, so `A(lerp p) <= lerp(A p)`: the loft can only ever enclose LESS,
    and it does, on every hull tested. Receipt `displacement_error_pct` on the
    reference hull:

        loft stations      12         41        161 (shipped)
        displacement    -0.4587%   -0.0129%     +0.0123%
        vs kernel       -0.5066%   +0.0075%     +0.0335%

    The sign flips at 161 because the loft has converged onto the true hull and
    what remains is the LADDER's own 41-station trapezoid — a separate and
    smaller question. `export._LOFT_STATIONS` is 161, station-ALIGNED
    (161 = 4 x 40 + 1) so the loft grid contains the validated stations exactly,
    and the export REBUILDS the hull at that count rather than resampling the
    41-station one, which is measured not to help.

    The receipt still records BOTH counts, which is the part that was always
    right: a discretisation nobody wrote down is the defect, not the
    discretisation itself.
    """
    import json
    pytest.importorskip("cadquery")
    from navalai.export import _LOFT_STATIONS, export_step, moulded_volume_m3

    hull = Hull(mid_params())
    p = export_step(hull, tmp_path / "hull.step")
    rec = json.loads((tmp_path / "hull.step.receipt.json").read_text())
    assert rec["n_stations_exported"] == _LOFT_STATIONS == 161
    assert rec["n_stations_validated"] == hull.n_stations == 41
    # station-ALIGNED, so the loft grid contains the validated stations
    assert (_LOFT_STATIONS - 1) % (hull.n_stations - 1) == 0
    assert rec["kernel_moulded_volume_m3"] == pytest.approx(
        moulded_volume_m3(hull), abs=1e-5)
    assert rec["volume_error_pct"] == pytest.approx(0.0335, abs=0.01)
    # and the loft is now on the OTHER side of the ladder, which is the whole
    # point: it no longer under-encloses the boat that passed the gates
    assert rec["displacement_error_pct"] == pytest.approx(0.0123, abs=0.01)
    assert p.stat().st_size > 10_000


def test_the_old_twelve_station_loft_really_did_lose_half_a_percent(tmp_path):
    """The measurement behind G6, kept executable so the default can never
    drift back without someone seeing the number it costs.

    RE-MEASURED 2026-08-13 against the rebuilt geometry kernel:

        quantity                       BEFORE        AFTER
        solid_volume_m3 at 12          37.248        29.363
        volume_error_pct at 12         -0.497%       -0.5066%

    The volume moved because the REFERENCE HULL moved, not because the loft
    did: `mid_params` went `forefoot` 0.85 -> 0.60 and `r_transom` 0.75 -> 0.30
    (that symbol also changed meaning, from a transom half-BEAM ratio to a
    transom sectional-AREA ratio), which is a materially finer bow and a much
    smaller transom. The FINDING is unchanged and is the percentage, not the
    cubic metres: a 12-station default still loses about half a percent of the
    displacement the ladder signed off.

    THE SECOND FIGURE MOVED AGAIN LATER THE SAME DAY, 29.353 -> 29.363 and
    -0.539% -> -0.5066%, and the reason is worth a line because it makes this
    test sharper rather than blunter. `export_step(..., n_stations=12)` used to
    SAMPLE the 41-station hull at twelve places; it now REBUILDS the hull at
    twelve stations from the closed form. The first is a lerp of a lerp and the
    second is an honestly coarse boat, so a 12-station loft is now exactly what
    the name says it is. It still loses half a percent.

    NOT AFFECTED BY THE `Hull.section()` POSITIONAL-READ DEFECT fixed in
    `navalai/export.py` on the same day. That defect bites hulls with
    `roundness > 0`, where `section()` returns 257 points and `pts[0]/[1]/[2]`
    read three adjacent samples of the bilge fillet instead of the three
    moulded corners. The reference hull has `roundness == 0.0` and its
    `section()` is (3, 2) — verified point-for-point against `edge_curves` —
    so these two figures are identical before and after that fix, and they are
    quoted from a run made after it landed."""
    import json
    pytest.importorskip("cadquery")
    from navalai.export import export_step

    export_step(Hull(mid_params()), tmp_path / "coarse.step", n_stations=12)
    rec = json.loads((tmp_path / "coarse.step.receipt.json").read_text())
    assert rec["n_stations_exported"] == 12
    assert rec["solid_volume_m3"] == pytest.approx(29.363, abs=0.01)
    assert rec["volume_error_pct"] == pytest.approx(-0.5066, abs=0.01)


# ---------------------------------------------------------------------------
# The kit-line admission: build ROUTE, measured with the gate's own meter
# ---------------------------------------------------------------------------


def _corner_params():
    """The reference proportions moved into the LOW-TWIST CORNER.

    MEASURED 2026-08-19 (the Gate 6D dial-isolation campaign): with
    flare = 0, forefoot = 0 and no deadrise warp (beta_bow = beta_mid) the
    reference 7 m proportions refold at 4.6/4.7 mm — the first hull in this
    repository to pass the 5 mm bar on BOTH panels. The corner tolerates
    warp up to ~+8 deg OR forefoot 0.2 individually, and flare 3 deg alone
    breaks the topside (26.8 mm): flare is the topside's hard constraint,
    deadrise warp the bottom's. Sharpie/dory-class shapes live here; the
    kit product class is this corner.
    """
    v = np.asarray(mid_params(), float).copy()
    v[9] = v[8]      # beta_bow = beta_mid: no deadrise warp
    v[13] = 0.0      # no forefoot rise
    v[14] = 0.0      # no flare
    return v


def test_kit_admission_corner_hull_is_sheet_buildable():
    """The corner hull routes to sheet-kit, under the bar on both panels."""
    from navalai.buildability import kit_buildability

    kit = kit_buildability(Hull(_corner_params()))
    assert kit["route"] == "sheet-kit" and kit["kit_buildable"]
    assert kit["bar_mm"] == REFOLD_BAR_MM
    for name, mm in kit["refold_mm"].items():
        assert mm <= REFOLD_BAR_MM, f"{name} {mm:.2f} mm"
        # ...and not by accident of a degenerate panel: the deviation is a
        # real measured number in the corner's known band, not machine zero.
        assert 2.0 < mm, f"{name} {mm:.2f} mm suspiciously perfect"


def test_kit_admission_reference_hull_routes_to_mould():
    """The reference hull (warp 22 deg, flare 10 deg) is a MOULD boat.

    Same numbers as `test_gate6_refold_clause_is_red_on_the_hull` — the
    admission and the gate read one meter. The route is a routing fact,
    not a defect: the hull remains certifiable, it is just not a kit.
    """
    from navalai.buildability import kit_buildability

    kit = kit_buildability(Hull(mid_params()))
    assert kit["route"] == "mould" and not kit["kit_buildable"]
    assert 118.0 < kit["refold_mm"]["bottom-stbd"] < 130.0
    assert 40.0 < kit["refold_mm"]["topside-stbd"] < 48.0


def test_kit_admission_round_bilge_routes_to_mould_without_a_meter():
    """roundness > 0 is not a two-panel shell: mould, by construction."""
    from navalai.buildability import kit_buildability

    v = np.asarray(mid_params(), float).copy()
    v[11] = 0.3
    kit = kit_buildability(Hull(v))
    assert kit["route"] == "mould" and not kit["kit_buildable"]
    assert "refold_mm" not in kit and "mould" in kit["why"]


# The KIT REFERENCE HULL: the first design in this repository that is BOTH
# certifiable (MARGINAL — every floor met, some within the marginal band) AND
# sheet-kit buildable (both panels under REFOLD_BAR_MM). Found 2026-08-19 by
# searching the low-twist corner under the full certification: a 12.2 m
# dory-class monohull — constant 9.0 deg deadrise (no warp), zero flare,
# zero forefoot rise, Cp 0.639. The searches that FAILED on the way are the
# instructive part: the 7 m reference proportions in the corner REFUSE on the
# 18 mm-ply cold-bend radius (0.94 m < 1.44 m — kit-refoldable but not
# cold-bendable), and several 11.5-12.6 m corner variants refold 11-26 mm
# (the corner has structure; flat dials alone do not guarantee the bar).
KIT_REFERENCE_PARAMS = [
    12.24464859, 3.105685017, 0.55, 1.55, 0.6392941018, -1.0,
    0.4760097448, 0.3, 9.039289126, 9.039289126, 0.35, 0.0,
    0.15, 0.0, 0.0, 0.18]


def test_the_kit_reference_hull_is_certifiable_and_kit_buildable():
    """The Kit-Line's existence proof, pinned: certification + kit route.

    If a geometry-kernel change moves this hull off either verdict, the
    Kit-Line's premise moved — that is exactly the regression this pin is
    for (Gate 6D's proposed re-framing keys on it; see the ledger row).
    """
    from navalai.buildability import kit_buildability
    from navalai.certify import certify
    from navalai.mission import MissionSpec

    v = np.asarray(KIT_REFERENCE_PARAMS, float)
    cert = certify(v, MissionSpec(), with_gz=False)
    assert cert.verdict in ("ACCEPT", "MARGINAL"), cert.reasons
    kit = kit_buildability(Hull(v))
    assert kit["kit_buildable"], kit
    for name, mm in kit["refold_mm"].items():
        assert 2.0 < mm <= REFOLD_BAR_MM, f"{name} {mm:.2f} mm"


def test_a_cut_file_is_refused_when_the_panels_would_not_close_on_the_hull():
    """GATE 6D AT THE BOUNDARY THAT MATTERS. MEASURED 2026-08-21.

    `export_dxf` gated on `refuse_unvalidated(ev, 'DXF')`, which asks whether
    the LADDER passed. The ladder does not measure refold accuracy -- there is
    no such row in `evaluate.CONSTRAINT_NAMES` -- so it cannot answer the only
    question a shop cares about: will these panels close on the hull?

    On a hull the GOVERNED search delivered and the ladder passed (ev.ok True),
    the worst refold deviation was 221.5 mm against a 5 mm bar, and export_dxf
    wrote a 67 kB DXF without complaint. Someone could have cut it; the topside
    would have missed the chine by the better part of a quarter metre.

    Gate 6D is RED and ledgered at 124.1 mm. A red gate whose ARTEFACT ships
    anyway is a gate softened by omission, so the check is made where the file
    is produced.
    """
    import numpy as np
    import pytest as _pytest

    from navalai.geometry import Hull
    from navalai.limits import PLY_THICKNESS_M, REFOLD_BAR_MM
    from navalai.unroll import (export_dxf, hull_panels, nest,
                                refold_surface_deviation_mm, split_panel)

    hull = Hull(mid_params())
    panels = hull_panels(hull)
    worst = max(float(np.max(refold_surface_deviation_mm(hull, p)))
                for p in panels)
    assert worst > REFOLD_BAR_MM, (
        "this fixture is chosen BECAUSE it misses the bar; if the unroller "
        "improves enough that it passes, re-point the test at a hull that "
        "still fails rather than deleting it")

    parts = []
    for p in panels:
        parts += split_panel(p, PLY_THICKNESS_M)
    layout = nest(parts)

    # The message names the FAMILY now, not a single deviation: this fixture's
    # family is (124.07, 74.06, 22.29) mm — REFINING, i.e. falling but still
    # over the bar at the finest count, which is a refusal for a different and
    # honest reason than NON_DEVELOPABLE.
    with _pytest.raises(ValueError, match="refold family"):
        export_dxf(layout, "/dev/null", hull=hull)

    # The override exists for geometry research and SAYS SO IN THE FILE.
    import tempfile
    import pathlib
    with tempfile.TemporaryDirectory() as d:
        out = export_dxf(layout, pathlib.Path(d) / "over.dxf", hull=hull,
                         allow_unverified=True)
        head = out.read_text()[:400]
        assert "OVERRIDDEN" in head and "NOT a production cut file" in head

        # And a file written with NO hull must not read as verified: an
        # unmeasured quantity is refused, never assumed good.
        out2 = export_dxf(layout, pathlib.Path(d) / "unk.dxf")
        assert "REFOLD NOT VERIFIED" in out2.read_text()[:400]


def test_the_unroller_is_EXACT_on_a_developable_surface():
    """THE MATHEMATICAL CONTROL FOR GATE 6D, and it moves the blame.

    Gate 6D is RED at 124.1 mm against a 5 mm bar, and the cause on record --
    `navalai/gates.py`, `docs/audit/PRODUCTION-READINESS.md` -- was "a
    geometric property of taking the rulings at constant station x", i.e. the
    UNROLLER. That reading survived because the shortfall does not refine away,
    which looked like a structural property of the algorithm.

    MEASURED 2026-08-21 against surfaces whose developability is known in
    CLOSED FORM, so there is no hull, no grammar and no scatter band to hide
    in -- the same discipline as Wigley's 4LBT/9 for the integrator:

        surface                developable?   max |refold(B) - B|
        cylinder                    yes            0.0000 mm
        flat plane                  yes            0.0002 mm
        cone (tapered)              yes            0.0013 mm
        twisted cylinder            NO           436.6376 mm
        hyperbolic paraboloid       NO            46.7388 mm

    The unroller is EXACT on developables to the last bit, and it correctly
    reports a large error on surfaces that are not. It is not the defect.

    What Gate 6D measures is the HULL: `shell_complexity` reads the topside's
    constant-x twist at 0.958 against the hypar negative control's 1.000, and
    over governed hulls corr(non_developable_frac, refold) = +0.783 with
    `flare` the dominant driver at +0.694 (flare 0 deg -> ndev 0.0064,
    flare 25 deg -> ndev 0.2953). The shortfall does not refine away because
    REFINEMENT CANNOT FLATTEN DOUBLE CURVATURE.

    This test exists so the blame cannot drift back: if someone "fixes" the
    unroller and this starts failing, they broke the one part that was right.
    """
    import numpy as np

    from navalai.unroll import develop, refold

    def err_mm(A, B, name):
        pan = develop(A, B, name)
        return float(np.max(np.linalg.norm(refold(pan) - B, axis=1))) * 1e3

    n = 60
    th = np.linspace(0.0, 0.9, n)
    t = np.linspace(0.0, 1.0, n)

    # --- positive controls: zero Gaussian curvature by construction --------
    cyl_a = np.stack([np.zeros(n), np.cos(th), np.sin(th)], axis=1)
    cyl_b = np.stack([np.full(n, 3.0), np.cos(th), np.sin(th)], axis=1)
    assert err_mm(cyl_a, cyl_b, "cyl") < 1e-3

    pl_a = np.stack([np.zeros(n), t * 2.0, np.zeros(n)], axis=1)
    pl_b = np.stack([np.ones(n), t * 2.0, np.zeros(n)], axis=1)
    assert err_mm(pl_a, pl_b, "plane") < 1e-2

    cone_a = np.stack([np.zeros(n), 0.2 * np.cos(th), 0.2 * np.sin(th)], axis=1)
    cone_b = np.stack([np.full(n, 4.0), 2.0 * np.cos(th), 2.0 * np.sin(th)],
                      axis=1)
    assert err_mm(cone_a, cone_b, "cone") < 1e-1

    # --- negative controls: the meter must not read zero on everything -----
    tw_b = np.stack([np.full(n, 3.0), np.cos(th + 0.6 * t),
                     np.sin(th + 0.6 * t)], axis=1)
    assert err_mm(cyl_a, tw_b, "twisted") > 100.0

    hyp_b = np.stack([np.ones(n), t * 2.0, t * t * 1.5], axis=1)
    assert err_mm(pl_a, hyp_b, "hypar") > 10.0


def _kit_corner_params(**over):
    """The developable corner of the grammar: no flare, no forefoot, no
    deadrise warp, hard chine. `over` perturbs one gene at a time."""
    d = {n: (lo + hi) / 2 for (n, u, lo, hi, _d) in unroll.grammar.PARAMS}
    d.update(LWL=10.5, BWL=3.2, T=0.55, D=1.35, roundness=0.0, flare=0.0,
             forefoot=0.0, rocker=0.0, beta_bow=2.0, beta_mid=2.0,
             sheer_rise=0.0)
    d.update(over)
    return d


def test_a_refold_shortfall_is_told_apart_from_its_station_count():
    """MEASURED 2026-08-21. The COMPANION to
    `test_refold_does_not_converge_with_station_count` above, which measures
    `mid_params` — a hull whose non-developable area fraction is 0.201 (flare
    10 deg, forefoot 0.600, deadrise warping 8 -> 30 deg). Refinement does not
    help there, and that test is right about that hull.

    What had never been measured is whether refinement helps ANYWHERE, and it
    does. `refold_surface_deviation_mm` builds the panel as straight chords
    between the hull's stations and compares it against the hull sampled at
    4001, so at `_LADDER_STATIONS` = 41 part of every reported deviation is a
    40-segment polyline's sagitta. On a hull that is actually developable that
    part is the WHOLE of it:

        hull                  ndev_frac    n=41    n=81   n=161   n=321
        flare 0                0.000000    17.1     5.8     4.1     1.5
        deadrise warp 2->40    0.063811    40.6    20.5    10.3     5.3
        flare 25               0.275547   379.8   448.3   484.6   503.6

    Row one is machine-zero Gaussian curvature (7.8e-14) reading 17.1 mm at the
    count Gate 6D quotes. So the 41-station value is not a manufacturing
    verdict on its own — 41 was chosen for hydrostatics cost, and this is
    CLAUDE.md's rule 4, a defect measured at a configuration the product never
    runs.

    The DIRECTION is the discriminator, and it is the same discipline
    `cfd.post.gci` applies to a mesh family: falling under refinement is
    measurement, rising is geometry, and only the second is a reason to change
    the hull. This test pins both signs so neither can drift.

    It also settles the question `hull_panels`' history left open — whether the
    grammar admits a sub-bar hull at all. It does.
    """
    dev = unroll.refold_convergence(_kit_corner_params(), counts=(41, 81, 161))
    assert dev.verdict == "PASSES", (dev.verdict, dev.worst_mm)
    assert dev.finest_mm <= REFOLD_BAR_MM, dev.worst_mm
    # strictly falling, and by a lot: 17.1 -> 4.1 is the polyline going away
    assert all(b < a for a, b in zip(dev.worst_mm, dev.worst_mm[1:])), dev.worst_mm
    assert dev.worst_mm[0] > 3.0 * dev.worst_mm[-1], dev.worst_mm

    nondev = unroll.refold_convergence(_kit_corner_params(flare=25.0),
                                       counts=(41, 81, 161))
    assert nondev.verdict == "NON_DEVELOPABLE", (nondev.verdict, nondev.worst_mm)
    # RISING. A finer sample of a doubly-curved surface finds more of the error
    # it could not represent, never less.
    assert all(b > a for a, b in zip(nondev.worst_mm, nondev.worst_mm[1:])), \
        nondev.worst_mm

    # A hull the unroller refuses is REFUSED, not given a fabricated number.
    filleted = unroll.refold_convergence(_kit_corner_params(roundness=0.5),
                                         counts=(41, 81))
    assert filleted.verdict == "REFUSED" and filleted.worst_mm == ()


def test_refold_convergence_refuses_to_name_an_order_it_cannot_support():
    """The successive ratios on the developable family are 2.97 and 1.41 —
    they disagree by more than 2x, so no single power law describes them and
    `order` stays None. Printing one anyway is the defect `post_gci` was fixed
    for: quoting a convergence order off a family whose refinement ratio was
    never measured.
    """
    dev = unroll.refold_convergence(_kit_corner_params(), counts=(41, 81, 161))
    assert dev.order is None, dev.ratios
    assert len(dev.ratios) == 2 and max(dev.ratios) / min(dev.ratios) > 2.0

    with pytest.raises(ValueError):
        unroll.refold_convergence(_kit_corner_params(), counts=(81, 41))


def test_the_cut_file_draws_every_part_the_BOM_tells_the_builder_to_cut():
    """MEASURED 2026-08-21, on a hull the kit lane actually delivered.

    `engineer.assess` computed the nesting layout, read `ply_sheets`,
    `nest_utilisation` and every `BomLine.sheet` off it -- and then RETURNED
    ONLY THE BOM. So anything wanting the CUT FILE had to re-derive the nest,
    and re-deriving it is easy to get subtly wrong: rebuilding from
    `_shell_parts` alone, omitting the `fixed` parts (deck, transom and the
    eight bulkheads), gave a DXF with **84 part outlines against a BOM of 186
    sheet-good parts**.

    102 parts the builder is told to cut were not drawn in the file they cut
    from. Nothing detected it, because nothing compared them: two nests, one
    BOM, one cut file, no fence. That is A NUMBER DECLARED TWICE in its most
    expensive form -- the boat is short a bottom strake, six deck tiles and
    every bulkhead, and you find out at the saw.

    `EngineerReport` now carries `layout` and `parts`, so the BOM and the cut
    file are the same nest by construction. This test is the fence.
    """
    import numpy as np

    from navalai.engineer import assess
    from navalai.geometry import Hull
    from navalai.unroll import export_dxf, parse_dxf_polylines

    # The developable corner of the grammar — `assess` refuses a radiused
    # bilge outright, so the fixture must be hard-chine for the test to reach
    # the nest at all.
    d = _kit_corner_params()
    hull = Hull(np.array([d[n] for n in unroll.grammar.NAMES], float))
    rep = assess(hull, wl=0.0)
    assert rep.layout is not None, "assess must carry the nest it computed"
    assert rep.parts, "assess must carry the parts it nested"

    # `ply_sheets` and the BOM's sheet assignments are read off THAT layout.
    assert rep.ply_sheets == rep.layout.sheets

    import tempfile
    import pathlib
    with tempfile.TemporaryDirectory() as d:
        out = export_dxf(rep.layout, pathlib.Path(d) / "cut.dxf",
                         hull=hull, allow_unverified=True)
        drawn = {k for k in parse_dxf_polylines(out)
                 if not k.startswith("SHEET-")}

    want = {b.part for b in rep.bom if b.sheet is not None}
    assert want, "this hull must have sheet-good parts for the test to mean anything"
    missing = want - drawn
    assert not missing, (
        f"{len(missing)} of {len(want)} BOM part(s) are NOT drawn in the cut "
        f"file, e.g. {sorted(missing)[:6]}. A builder cannot cut what the file "
        f"does not contain.")


def test_a_refold_verdict_is_a_FAMILY_and_the_cut_file_gate_uses_it():
    """MEASURED 2026-08-21, and it caught a hull this session had ALREADY
    SHIPPED as verified.

    `export_dxf`'s first buildability guard read `refold_surface_deviation_mm`
    at the ladder's 41 stations and compared it to the 5 mm bar. But the panel
    is built as straight chords between stations, so at n=41 part of every
    reading is a 40-segment polyline's sagitta: a surface whose Gaussian
    curvature is 7.8e-14 -- machine zero, exactly developable -- reads 17.1 mm
    there and 1.5 mm at n=321.

    The consequence was not a conservative gate. It was a FALSE PASS. A
    refinement search scored on that same 41-station number returned

        n=41  4.92 mm      n=81  5.22 mm      n=161  8.71 mm

    -- under the bar at the count it was optimised against, and RISING. It
    optimised the artefact instead of the curvature, and the cut file was
    stamped REFOLD VERIFIED.

    Falling under refinement is measurement; rising is geometry. Only the
    second is a hull you cannot build, and only a family can tell them apart --
    the same discipline `cfd.post.gci` applies to a mesh family.
    """
    import numpy as np
    import pytest as _pytest

    from navalai import unroll
    from navalai.geometry import Hull
    from navalai.limits import PLY_THICKNESS_M, REFOLD_BAR_MM
    from navalai.unroll import (export_dxf, hull_panels, nest,
                                refold_convergence, split_panel)

    # A DEVELOPABLE hull whose 41-station reading is far OVER the bar: the
    # positive control for "falling is measurement".
    corner = _kit_corner_params()
    fam = refold_convergence(corner, counts=(41, 81, 161))
    assert fam.verdict == "PASSES", (fam.verdict, fam.worst_mm)
    assert fam.worst_mm[0] > REFOLD_BAR_MM, (
        "this control is only meaningful if the COARSE count misses the bar "
        "while the family passes")
    assert fam.finest_mm <= REFOLD_BAR_MM

    # and the gate must let it through on the strength of the trend, not
    # refuse it on the strength of its 41-station value.
    hull = Hull(np.array([corner[n] for n in unroll.grammar.NAMES], float))
    parts = []
    for pan in hull_panels(hull):
        parts += split_panel(pan, PLY_THICKNESS_M)
    layout = nest(parts)

    import pathlib
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = export_dxf(layout, pathlib.Path(d) / "ok.dxf", hull=hull)
        head = out.read_text()[:300]
        assert "REFOLD VERIFIED" in head, head[:160]
        # the stamp must carry the FAMILY, not a lone number
        assert "PASSES" in head or "family" in head, head[:160]

    # A hull whose family RISES must be refused however good n=41 looks.
    bad = _kit_corner_params(flare=25.0)
    fam_bad = refold_convergence(bad, counts=(41, 81, 161))
    assert fam_bad.verdict == "NON_DEVELOPABLE", fam_bad.worst_mm
    hull_bad = Hull(np.array([bad[n] for n in unroll.grammar.NAMES], float))
    parts_b = []
    for pan in hull_panels(hull_bad):
        parts_b += split_panel(pan, PLY_THICKNESS_M)
    with _pytest.raises(ValueError, match="NON_DEVELOPABLE"):
        export_dxf(nest(parts_b), "/dev/null", hull=hull_bad)
