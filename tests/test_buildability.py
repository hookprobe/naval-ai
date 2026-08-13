"""Gate tests for `navalai/buildability.py`.

WHAT THESE ASSERT, AND WHAT THEY DELIBERATELY DO NOT.

They assert the MECHANISM — the things that can silently break and leave a
plausible-looking complexity number behind:

  * that a metric which cannot be measured is REFUSED, never defaulted to zero
    (zero is the most buildable answer there is, so this is defect class 1 in
    its most dangerous shape).
  * that the metrics are GRID-CONVERGED, and by a measured residual rather than
    a declared one.
  * that the two shape metrics are DIFFERENT QUANTITIES and both discriminate a
    deliberately warped hull from the reference.
  * THE HEADLINE FENCE: that the area-AVERAGED Gaussian curvature is inverted
    on the inflated hull, i.e. that the literature's own preferred form would
    score the worse boat better. This is the reason the module refuses it as an
    objective and the reason the fence is here rather than in a comment.
  * that nothing here re-implements a quantity another module owns.

They do NOT pin the complexity of any particular hull as a requirement. Those
are MEASUREMENTS, they live in the module's docstrings with the command that
produced them, and a test that froze them would convert a finding into a bar.
"""

from __future__ import annotations

import numpy as np
import pytest

from navalai import buildability as Bd
from navalai import experiments as X
from navalai import geometry, grammar, unroll
from navalai.energy import EnergySpec, shell_area_m2, weight_budget


@pytest.fixture(scope="module")
def ref_hull():
    return geometry.Hull(X.reference_demihull(), n_stations=41)


@pytest.fixture(scope="module")
def warped_hull():
    """Deadrise warped 2 -> 45 deg over 0.6 L with 25 deg of flare.

    THE CONTROL FOR EVERY CURVATURE ASSERTION. Without a hull that is known to
    be harder to build, a curvature metric that returned a constant would pass
    every test in this file.
    """
    return geometry.Hull(
        X.with_genes(beta_mid=2.0, beta_bow=45.0, beta_len=0.6, flare=25.0),
        n_stations=41)


# ---------------------------------------------------------------------------
# Refusals — an unmeasurable metric is FATAL, never a default
# ---------------------------------------------------------------------------


def test_a_filleted_bilge_is_refused_not_approximated():
    """`roundness > 0` has no two-strip moulded surface, so there is nothing
    to measure and a number would be a number about a different hull.

    `unroll.hull_panels` refuses the same hull for the same reason, and that
    refusal was itself a fix: the ValueError used to be swallowed and the hull
    came out as "no feasible nesting layout", which is a lie of category. This
    module must not reintroduce the swallow on the other side.
    """
    round_bilge = geometry.Hull(X.with_genes(roundness=0.6), n_stations=41)
    with pytest.raises(Bd.BuildabilityError, match="roundness"):
        Bd.shell_complexity(round_bilge)
    # and the refusal is the SAME one unroll makes, on the same hull
    with pytest.raises(ValueError, match="roundness"):
        unroll.hull_panels(round_bilge)


def test_a_degenerate_grid_is_refused_by_whichever_guard_it_reaches_first(
        ref_hull):
    """Angle deficit needs an interior vertex; the twist needs three unmasked
    stations. BOTH are refusals and neither returns zero.

    The two cases below fire DIFFERENT guards, and the test says which rather
    than matching a common substring: a 2-RULING grid has no interior vertex,
    while a 2-STATION grid is stopped one line earlier by the ruling-width
    mask, which leaves only 1 station. Asserting a single message for both
    would have passed even if one guard were deleted.
    """
    with pytest.raises(Bd.BuildabilityError, match="interior vertex"):
        Bd.shell_complexity(ref_hull, n_stations=41, n_rulings=2)
    with pytest.raises(Bd.BuildabilityError, match="ruling-width mask"):
        Bd.shell_complexity(ref_hull, n_stations=2, n_rulings=17)


# ---------------------------------------------------------------------------
# Convergence — a measured residual, not a declared percentage
# ---------------------------------------------------------------------------


def test_the_metrics_are_grid_converged_by_a_measured_residual(ref_hull):
    """MEASURED on the reference demihull, SHELL_GRID against REFINEMENT_CHECK:

        non_developable_area_m2   0.0446 on 9.380   ->  0.48%
        gauss_abs_integral        2.05e-4 on 0.00581 -> 3.5%
        gauss_abs_mean_per_m2     1.2e-5 on 3.42e-4  -> 3.5%

    The bars below are 2% and 8%, i.e. loose enough not to be a restatement of
    the measurement and tight enough that a metric which stopped converging
    would fail. THE CURVATURE BAR IS DELIBERATELY LOOSER THAN THE TWIST BAR
    because the measurement says it converges more slowly in `n_rulings`, and
    softening the tighter one to a common value would hide that.
    """
    c = Bd.shell_complexity(ref_hull)
    res = Bd.refinement_residual(ref_hull)
    assert res["non_developable_area_m2"] / c.non_developable_area_m2 < 0.02
    assert res["gauss_abs_integral"] / c.gauss_abs_integral < 0.08
    assert res["gauss_abs_mean_per_m2"] / c.gauss_abs_mean_per_m2 < 0.08


def test_non_developability_does_not_depend_on_the_ruling_sampling(ref_hull):
    """`ruling_twist` is evaluated on the two EDGE CURVES, so the interior grid
    density cannot move it — and that invariance is the property that makes it
    usable as a metric at all (see `unroll.ruling_twist`'s docstring: "a metric
    you can drive to zero by adding stations is not a metric").

    If this fails, someone has started sampling the twist off the interior
    grid and the number has become a function of the sampler.
    """
    a = Bd.shell_complexity(ref_hull, n_rulings=9)
    b = Bd.shell_complexity(ref_hull, n_rulings=33)
    assert a.non_developable_area_m2 == pytest.approx(
        b.non_developable_area_m2, rel=1e-12)
    assert a.twist_max == pytest.approx(b.twist_max, rel=1e-12)
    # ... while the curvature integral, which IS measured on the grid, moves
    assert a.gauss_abs_integral != pytest.approx(b.gauss_abs_integral, rel=1e-6)


# ---------------------------------------------------------------------------
# The two shape metrics are different quantities, and both discriminate
# ---------------------------------------------------------------------------


def test_both_shape_metrics_separate_a_warped_hull_from_the_reference(
        ref_hull, warped_hull):
    """MEASURED: at shell areas that agree to 0.4% (33.825 vs 33.957 m^2), the
    warped hull carries 10.6x the curvature integral (0.06182 vs 0.00581) and
    1.23x the non-developable area (11.53 vs 9.38 m^2).

    The bars are 3x and 1.1x. A metric that could not tell those two hulls
    apart would not be measuring shape difficulty at all, and this is the test
    that would catch a curvature routine that had silently started returning a
    constant.
    """
    r = Bd.shell_complexity(ref_hull)
    w = Bd.shell_complexity(warped_hull)
    assert w.shell_area_m2 == pytest.approx(r.shell_area_m2, rel=0.02), (
        "the control hull is no longer area-matched, so a difference in the "
        "curvature metrics could just be a difference in size")
    assert w.gauss_abs_integral > 3.0 * r.gauss_abs_integral
    assert w.non_developable_area_m2 > 1.1 * r.non_developable_area_m2


def test_the_two_metrics_are_not_the_same_number(ref_hull, warped_hull):
    """Non-developability is RULING-FAMILY DEPENDENT; Gaussian curvature is
    INTRINSIC. If the two ever became proportional, one of them is redundant
    and the module's claim that they answer different questions is false.

    MEASURED ratio Int|K|dA / nondev_m2: 6.19e-4 on the reference and 5.36e-3
    on the warped hull — an 8.7x spread, so they are not a rescaling of each
    other.
    """
    r = Bd.shell_complexity(ref_hull)
    w = Bd.shell_complexity(warped_hull)
    ratio_r = r.gauss_abs_integral / r.non_developable_area_m2
    ratio_w = w.gauss_abs_integral / w.non_developable_area_m2
    assert max(ratio_r, ratio_w) / min(ratio_r, ratio_w) > 2.0, (
        f"Int|K|dA and Int|sin psi|dA are within 2x of proportional "
        f"({ratio_r:.3e} vs {ratio_w:.3e}). One of them is not adding "
        f"information and the module says they answer different questions.")


# ---------------------------------------------------------------------------
# THE HEADLINE FENCE
# ---------------------------------------------------------------------------


def test_area_averaged_curvature_is_inverted_on_the_inflated_hull():
    """THE MEASUREMENT THAT DECIDES WHICH FORM MAY BE AN OBJECTIVE.

    MOTIVATING INCIDENT (2026-08-13): `docs/research/HULL-GAN-PAPERS.md` names
    area-averaged Gaussian curvature as the most adoptable manufacturing-cost
    idea in the four papers read, and this project was one step from adopting
    it. Experiment 5 then measured that ShipGen's own failure — wave drag
    x0.086 with surface area x2.138, which its authors call "not desirable" —
    is caused by NORMALISING BY A LENGTH THE OPTIMISER CONTROLS (LOA^2 instead
    of wetted area). An area-AVERAGED curvature has that same property.

    MEASURED here, on experiment 5's two optima at fixed speed and fixed
    displacement:

        hull                  shell A    Int|K|dA    Int|K|dA / A   nondev m^2
        R_t optimum (12 m)     40.73      0.00594      2.90e-4         8.79
        R_w-only opt (20 m)   114.28      0.00575      1.00e-4        29.46

    The 20 m hull is 2.81x the shell area, 2.83x the structural mass, 3.35x the
    plywood, 3.68x the build hours and 28.7% worse in Wh/NM — and the
    area-averaged curvature scores it **2.9x BETTER**.

    AND SO, MILDLY, DOES THE INTEGRAL (0.00575 against 0.00594). An earlier
    version of this test asserted the integral was NOT inverted and it passed,
    because it was measured on a differently-proportioned pair of hulls. It is
    not a robust property: Gauss-Bonnet makes Int|K|dA a near-invariant of
    SHAPE rather than of size, so on two hulls of similar shape and very
    different size it can fall either way. The module therefore refuses BOTH
    curvature forms as cost terms and recommends `non_developable_area_m2`,
    which has units of m^2 and is the only one of the three that tracks the
    boat's actual size — and this test fences that ordering rather than a claim
    about the integral's sign.
    """
    # EXPERIMENT 5's TWO OPTIMA, built from its own gene grid and its own
    # derived-depth rule so that this fence and that experiment cannot drift
    # apart. `GAMING_DEPTH_OVER_LWL` is imported, not retyped.
    def gaming_hull(lwl, lob, t, cp, lcb, ff):
        return geometry.Hull(
            X.with_genes(LWL=lwl, BWL=lwl / lob, T=t,
                         D=max(0.6, X.GAMING_DEPTH_OVER_LWL * lwl),
                         Cp=cp, lcb=lcb, forefoot=ff), n_stations=41)

    small = gaming_hull(12.0, 8.5, 0.30, 0.6175, -3.0, 0.0)   # the R_t optimum
    big = gaming_hull(20.0, 6.5, 0.50, 0.525, -3.0, 0.5)      # the R_w optimum
    s = Bd.shell_complexity(small)
    b = Bd.shell_complexity(big)

    assert b.shell_area_m2 > 2.5 * s.shell_area_m2, (
        "the inflated hull is no longer inflated; this fence has lost its case")
    # THE INVERSION, and it is the thing being fenced.
    assert b.gauss_abs_mean_per_m2 < s.gauss_abs_mean_per_m2, (
        f"the area-averaged Gaussian curvature no longer prefers the inflated "
        f"hull ({b.gauss_abs_mean_per_m2:.3e} vs {s.gauss_abs_mean_per_m2:.3e})"
        f". Re-measure before relaxing the module's refusal to use it as an "
        f"objective — the refusal rests on this number.")
    # THE INTEGRAL IS NOT A COST EITHER. It is asserted to be nearly
    # SIZE-INVARIANT — within 25% across a 2.8x change in shell area — which is
    # exactly why it must not be used to price manufacturing. The bar is a
    # band, not a direction, because the sign is not robust and this test does
    # not pretend it is.
    ratio = b.gauss_abs_integral / s.gauss_abs_integral
    assert 0.75 < ratio < 1.25, (
        f"Int|K|dA moved by {ratio:.2f}x across a "
        f"{b.shell_area_m2 / s.shell_area_m2:.2f}x change in shell area. The "
        f"module refuses it as a COST metric precisely because it is nearly "
        f"size-invariant; if that has changed, re-measure the refusal.")
    # ... and the ONE form the module recommends tracks the boat's size.
    assert b.non_developable_area_m2 > 2.5 * s.non_developable_area_m2
    assert b.build_area_m2 > 2.5 * s.build_area_m2


# ---------------------------------------------------------------------------
# A number lives in exactly one place
# ---------------------------------------------------------------------------


def test_every_imported_quantity_is_the_owning_modules_own_number(ref_hull):
    """No second copy of an area, a mass or a twist.

    Each of these is recomputed here by calling the module that OWNS it and
    required to agree exactly. A drifting second copy is this repository's
    recurring defect and it has already produced a 5.2% error in shell area
    (`energy.shell_area_m2`, gap C9) and a 0.7 m error in payload LCG.
    """
    c = Bd.shell_complexity(ref_hull)
    assert c.shell_area_m2 == pytest.approx(shell_area_m2(ref_hull), rel=1e-12)
    assert c.deck_area_m2 == pytest.approx(ref_hull.deck_area(), rel=1e-12)
    assert c.wetted_area_m2 == pytest.approx(ref_hull.wetted_surface(0.0),
                                             rel=1e-12)
    assert c.panel_twist_deg_per_m == pytest.approx(
        ref_hull.panel_twist_rate(), rel=1e-12)
    wb = weight_budget(float(ref_hull.x[-1]),
                       float(grammar.named(ref_hull.params)["D"]),
                       shell_area_m2(ref_hull), ref_hull.deck_area(),
                       EnergySpec())
    assert c.structure_kg == pytest.approx(wb.structure_kg, rel=1e-12)
    # build_area is optimize.py's objective 2, spelled the same way
    assert c.build_area_m2 == pytest.approx(
        ref_hull.wetted_surface(float(ref_hull.z_sheer.max()))
        + ref_hull.deck_area(), rel=1e-12)


def test_the_twist_is_unrolls_own_criterion(ref_hull):
    """`ruling_twist` is IMPORTED. This recomputes it on the same edge curves
    and requires the module's maximum to be one of those values, so a local
    re-derivation of the developability criterion could not slip in."""
    x = np.linspace(float(ref_hull.x[0]), float(ref_hull.x[-1]),
                    Bd.SHELL_GRID["n_stations"])
    keel, chine, sheer = ref_hull.edge_curves(x)
    every = np.concatenate([unroll.ruling_twist(keel, chine),
                            unroll.ruling_twist(chine, sheer)])
    c = Bd.shell_complexity(ref_hull)
    assert np.any(np.isclose(every, c.twist_max, rtol=1e-12))
    assert c.twist_max <= float(every.max()) + 1e-12


def test_the_end_mask_is_what_keeps_the_twist_metric_discriminating(ref_hull):
    """MEASURED: without the mask, twist_max is 1.00000 on every hull the
    grammar emits — the degenerate stem ruling saturates it and the metric
    stops separating hulls. `Hull.fairness` and `Hull.panel_twist_rate` both
    mask at the same 10% and both record why.
    """
    x = np.linspace(float(ref_hull.x[0]), float(ref_hull.x[-1]),
                    Bd.SHELL_GRID["n_stations"])
    keel, chine, sheer = ref_hull.edge_curves(x)
    unmasked = max(float(unroll.ruling_twist(keel, chine).max()),
                   float(unroll.ruling_twist(chine, sheer).max()))
    assert unmasked > 0.999, (
        "the unmasked twist no longer saturates, so the mask's justification "
        "has changed and should be re-measured rather than assumed")
    assert Bd.SHELL_GRID and Bd.END_MASK_FRAC == 0.10


# ---------------------------------------------------------------------------
# Nesting — measurements of a planned layout, labelled as such
# ---------------------------------------------------------------------------


def test_nesting_metrics_come_off_the_layout_and_the_waste_is_derived(ref_hull):
    """`ply_sheets` is COUNTED off `unroll.nest`, which is what retired the
    declared 1.30 waste factor. The waste fraction here must be derived from
    the two areas that report already carries, never declared.

    MEASURED on the reference demihull: 41 panels, 31 sheets, utilisation
    0.823, waste 0.498, 1123 build hours.
    """
    n = Bd.nesting_complexity(ref_hull)
    assert n.ply_sheets > 0 and n.panel_count > 0
    assert n.material_waste_frac == pytest.approx(
        1.0 - n.panel_area_m2 / n.sheet_area_m2, rel=1e-12)
    assert 0.0 < n.material_waste_frac < 1.0
    assert "NOT rule-derived" in n.thickness_basis, (
        "no mLDC was passed, so the thickness is the nominal stock sheet and "
        "the record must say so rather than implying a rule derivation")
