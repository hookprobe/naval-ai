"""Gate BARGE: a houseboat is a rectangle, and the kernel can finally draw one.

MOTIVATING INCIDENT (2026-08-23, docs/research/HOUSEBOAT-16M.md). A
non-expert asked for a 16 m x 4 m houseboat, got a hull he described as "a
spearhead", and was right: 4 m of beam over 22% of the length, 61% of a
rectangle's deck area. Not a tuning failure — no slider could fix it.

THREE INDEPENDENT BOUNDS EACH FORBADE A BARGE, and all three had to move:
`r_stem` had to exist at all (the SAC's forward branch ended at a hardcoded
zero), `r_transom` was capped at 0.50 (best measured transom beam 1.96 m of
4.00), and Cp was capped at 0.710 while a barge's SAC reaches 0.831 at the
lowest. The first landed 2026-08-24; the other two ceilings moved on
2026-08-26 (commit b1d2145, the DRAW-box recalibration event), which is the
day this test came out of docs/morphology/pending/ where it had been HELD
since 6e91d33 waiting for exactly that event.

MEASURED on the 16 x 4 m liveaboard, before and after, re-verified on the
corrected sac solve the day this landed (values reproduce to the decimal):

                   % length at >=90% beam    deck area      stern    bow
    before                 39%               43.6 m2 (68%)  1.96 m  0.00 m
    after                  88%               59.4 m2 (93%)  4.22 m  1.50 m

The cost is real and is paid in drag, not hidden: 7 kn went from 9.0 kW to
12.3 kW, still inside the 15 kW installed.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import grammar, limits
from navalai.geometry import GeometryError, Hull
from navalai.reference import REFERENCE_HULL


def test_the_barge_bounds_are_open_far_enough_to_draw_a_box():
    """The three ceilings, pinned so none of them silently returns."""
    hi = dict((p[0], p[3]) for p in grammar.PARAMS)
    assert hi["r_transom"] >= 0.9, "a full transom is unreachable again"
    assert hi["r_stem"] >= 0.8, "a pram bow is unreachable again"
    assert limits.CP_GENE_BOUNDS[1] >= 0.9, (
        "the Cp ceiling is back below what a box's SAC reaches (0.831 at the "
        "lowest), so the kernel will refuse a barge by naming a Cp nobody "
        "chose")


def test_the_draw_box_still_holds_the_historical_ceilings():
    """The seeded streams' box did NOT widen — that is the whole design of
    the recalibration event: legal envelope wide, recorded history frozen."""
    for gene, (lo, hi) in grammar._LEGACY_DRAW_ROWS.items():
        i = grammar.NAMES.index(gene)
        assert grammar.DRAW_LOW[i] == lo and grammar.DRAW_HIGH[i] == hi, gene


def test_a_sixteen_by_four_houseboat_carries_its_beam():
    """THE BAR, and it is the user-visible one: a houseboat is a rectangle.

    Bars are set BELOW the measured values (88% and 59.4 m2) so ordinary
    kernel drift does not fail the suite, but far above the pre-fix state
    (39% and 43.6 m2) so a regression to a spearhead does.
    """
    g = dict(REFERENCE_HULL, LWL=15.2, BWL=4.0, T=0.391, D=1.55,
             r_stem=0.40, r_transom=0.92, Cp=0.92, lcb=-1.5, x_mb=0.50,
             beta_mid=8.0, beta_bow=10.0, beta_len=0.45, roundness=0.0,
             rocker=0.05, forefoot=0.10, flare=6.0, sheer_rise=0.12)
    x = grammar.vector(g)
    rep = grammar.check(x)
    assert rep.ok, [str(v) for v in rep.violations]

    hull = Hull(x)
    beam = 2.0 * hull.y_sheer
    carried = float((beam >= 0.90 * 4.0).mean())
    deck = hull.deck_area()
    assert carried >= 0.75, (
        f"only {100 * carried:.0f}% of the waterline carries full beam "
        f"(pre-fix was 39%, post-fix 88%) — the spearhead is back")
    assert deck >= 55.0, (
        f"deck area {deck:.1f} m2 against 64.0 m2 for a 16x4 rectangle "
        f"(pre-fix 43.6, post-fix 59.4)")
    assert beam[0] >= 3.5, f"transom beam {beam[0]:.2f} m — the stern is pinched"
    assert beam[-1] >= 1.0, f"bow beam {beam[-1]:.2f} m — the point is back"


def test_the_pointed_bow_is_still_reachable():
    """Opening the box must not close the old corner of it."""
    g = dict(REFERENCE_HULL, r_stem=0.0)
    hull = Hull(grammar.vector(g))
    assert 2.0 * hull.y_sheer[-1] == pytest.approx(0.0, abs=1e-9)


def test_a_stem_fullness_the_cp_gene_cannot_feed_is_refused_by_name():
    """The kernel must still REFUSE an unreachable target, not approximate
    it — the corrected solve names the fullness genes in the refusal."""
    g = dict(REFERENCE_HULL, r_transom=0.92, r_stem=0.70, Cp=0.60)
    with pytest.raises(GeometryError, match="Cp"):
        Hull(grammar.vector(g))


def test_an_unknown_gene_is_refused_rather_than_discarded():
    """MEASURED 2026-08-23: `vector` silently dropped unknown keys. When the
    E5 recalibration removed `l_pmb`, every caller still passing it went on
    running and quietly got a different hull — a false measurement (three
    `l_pmb` settings reported as 'giving identical beam' when none was ever
    applied)."""
    with pytest.raises(KeyError, match="l_pmb"):
        grammar.vector(dict(REFERENCE_HULL, l_pmb=0.7))
