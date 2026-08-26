"""Gate tests for the experiment suite (`navalai/experiments.py`).

WHAT THESE TESTS ASSERT, AND WHAT THEY DELIBERATELY DO NOT.

They assert the MECHANISM — the thing that can silently break and leave a
plausible-looking sweep behind:

  * that a sweep HOLDS ITS CONTROLLED QUANTITIES FIXED. This is the whole
    validity of experiments 1 and 3, it is invisible in the output, and a
    change to `geometry._stations` or `sac_exponents` could break it without
    breaking anything else in the repository.
  * that a sweep ACTUALLY VARIES the thing it claims to vary.
  * that an out-of-envelope point is REFUSED and EXCLUDED, not extrapolated.
  * that the Michell interference phase matches an INDEPENDENT amplitude
    superposition, and that the check has the resolution to catch the wrong
    convention.
  * that s -> infinity recovers the sum of the independent hulls.
  * that the interference is non-monotonic in s/L, and that the located optimum
    survives DOUBLING the theta resolution.
  * that a bow ranking does not change between the production and the converged
    Michell grid — otherwise a "better bow" is quadrature error.
  * that every number in every record carries a tier and a sigma.
  * that the whole suite is deterministic.

They do NOT assert that sharper is better, that any particular Cp wins, or that
any particular s/L is optimal. Those are the MEASUREMENTS, they are recorded in
the module's docstrings with the command that produced them, and a test that
pinned them would convert a result into a requirement — which is how a suite
built to find out whether "sharper = better" holds ends up enforcing it.

The measured VALUES are pinned in exactly one place and for one reason: the
docstrings, so that a future change that moves them is visible in a diff.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from navalai import experiments as X
from navalai import formlib, geometry, grammar, limits, resistance
from navalai.evaluate import tier_rank


# ---------------------------------------------------------------------------
# The record contract
# ---------------------------------------------------------------------------


ALL_RECORDS = ("1-bow-sharpness", "2-prismatic", "3-lcb", "4-separation",
               "5-objective-gaming")


@pytest.fixture(scope="module")
def suite():
    return X.run_all()


def test_the_suite_runs_and_returns_every_experiment(suite):
    assert set(suite) == set(ALL_RECORDS)
    for rec in suite.values():
        assert rec.points, f"{rec.name} produced no points"
        assert rec.question
        assert rec.protocol


def test_every_quantity_carries_a_tier_and_a_sigma(suite):
    """Honesty rule 1. No bare numbers anywhere in a record.

    Walks every quantity of every point of every experiment. The `Quantity`
    constructor already refuses a bad tier or a defaulted sigma; this proves
    that nothing bypassed the constructor and that the tier vocabulary is one
    `evaluate.tier_rank` can actually rank.
    """
    seen = 0
    for rec in suite.values():
        for label, key, q in X.all_quantities(rec):
            assert isinstance(q, X.Quantity), f"{rec.name}/{label}/{key}"
            assert q.tier in (X.TIER_GEOMETRY, X.TIER_PHYSICS,
                              X.TIER_PHYSICS_INVALID)
            assert math.isfinite(q.sigma) and q.sigma >= 0.0
            if q.sigma == 0.0:
                assert q.basis in X.Quantity.ZERO_SIGMA_BASES, (
                    f"{rec.name}/{label}/{key} has a zero sigma with basis "
                    f"{q.basis!r} — an unmeasured band scored as certainty")
            seen += 1
    assert seen > 1000, f"only {seen} quantities walked; the walk is not doing its job"


def test_the_invalid_tier_ranks_below_l0():
    """`L1-INVALID` must never be promotable by a `>=` comparison.

    The mechanism the whole out-of-envelope story rests on: `evaluate.tier_rank`
    ranks an unrecognised badge at -1, and `L1-INVALID` is deliberately such a
    badge. If someone "tidied" the spelling to `L1` this test is what fails.
    """
    assert tier_rank(X.TIER_PHYSICS_INVALID) == -1
    assert tier_rank(X.TIER_GEOMETRY) == 0
    assert tier_rank(X.TIER_PHYSICS) == 1
    assert tier_rank(X.TIER_PHYSICS_INVALID) < tier_rank(X.TIER_GEOMETRY)


def test_a_zero_sigma_from_a_model_basis_is_refused():
    """The `${VAR:-0}` fence, at the constructor."""
    X.Quantity(1.0, X.TIER_PHYSICS, 0.0, "N", X.BASIS_EXACT)     # allowed
    X.Quantity(1.0, X.TIER_PHYSICS, 0.0, "N", X.BASIS_GRID)      # allowed
    with pytest.raises(X.ExperimentError, match="zero band"):
        X.Quantity(1.0, X.TIER_PHYSICS, 0.0, "N", X.BASIS_MODEL)
    with pytest.raises(X.ExperimentError, match="not one of"):
        X.Quantity(1.0, "CFD", 1.0, "N", X.BASIS_MODEL)
    with pytest.raises(X.ExperimentError, match="finite"):
        X.Quantity(1.0, X.TIER_PHYSICS, -1.0, "N", X.BASIS_MODEL)


def test_no_resistance_sigma_constant_is_copied_out_of_resistance_py(suite):
    """A NUMBER LIVES IN EXACTLY ONE PLACE — checked on the sigmas.

    `resistance.total_resistance` builds its band from two constants that are
    INLINE in that function and are not importable:

        sigma_rf = rf * sqrt((sigma_k / (1 + k))**2 + 0.10**2)
        sigma    = 0.25 * rw + sigma_rf

    The first version of `resistance_quantities` retyped `0.25 * rw` and
    `0.10 * cf` — this repository's recurring defect, and one that would drift
    silently the next time `resistance.py` revised either band (it has revised
    the friction one once already). The components now carry a MEASURED
    grid-refinement band labelled `BASIS_GRID_LOWER_BOUND`, and only `rt_n`,
    `form_k` and `wh_per_nm` carry a model band — each read from the object
    that owns it (`ResistanceResult.uncertainty`, `FormFactor.sigma_k`,
    `EnergyReport.sigma_wh_per_nm`).

    This test proves the component sigmas are NOT a fixed fraction of their
    value, which is what a copied constant would look like.
    """
    for p in suite["1-bow-sharpness"].points:
        for k in ("rw_n", "rf_n", "cw", "cf"):
            q = p.q[f"prod/fn0.30/{k}"]
            assert q.basis == X.BASIS_GRID_LOWER_BOUND, (
                f"{k} carries basis {q.basis!r}; a component band this module "
                f"cannot read from resistance.py must be labelled a lower "
                f"bound, never declared")
            if q.value != 0.0:
                frac = q.sigma / abs(q.value)
                assert frac not in (pytest.approx(0.25), pytest.approx(0.10)), (
                    f"{k}'s sigma is exactly {frac:.2f} of its value — that is "
                    f"resistance.py's inline constant, copied")
        assert p.q["prod/fn0.30/rt_n"].basis == X.BASIS_MODEL
        assert p.q["prod/fn0.30/form_k"].basis == X.BASIS_MODEL
        assert p.q["prod/fn0.30/wh_per_nm"].basis == X.BASIS_PROPAGATED


def test_resistance_quantities_refuses_to_run_without_a_second_grid():
    """No second grid, no measured band — and a declared band is refused."""
    params = X.reference_demihull()
    hull, st, wl = X._float_hull(params, X.HYDRO_STATIONS, None)
    with pytest.raises(X.ExperimentError, match="other_grid"):
        X.resistance_quantities(hull, st, wl, 0.30,
                                dict(resistance.PRODUCTION_GRID))


def test_the_rt_model_band_is_resistance_pys_own_number(suite):
    """`rt_n`'s sigma must BE `ResistanceResult.uncertainty`, not a copy.

    Recomputed here by calling `resistance.total_resistance` directly with the
    experiment's own recorded inputs, so a divergence between the record and
    the model is caught rather than assumed away.
    """
    p = suite["1-bow-sharpness"].points[0]
    hull, st, wl = X._float_hull(X.with_genes(forefoot=dict(p.genes)["forefoot"]),
                                 X.HYDRO_STATIONS, None)
    g = dict(resistance.PRODUCTION_GRID)
    r = resistance.total_resistance(
        hull, p.value("prod/fn0.30/speed_mps"), st.wetted, st.cb, X.RHO, wl,
        nz=g["nz"], n_stations=g["n_stations"], beam_wl=st.b_wl_max,
        draft=st.draft)
    assert p.q["prod/fn0.30/rt_n"].sigma == pytest.approx(r.uncertainty,
                                                          rel=1e-12)
    assert p.value("prod/fn0.30/rt_n") == pytest.approx(r.total, rel=1e-12)


def test_the_suite_is_deterministic(suite):
    """No RNG, no wall-clock. Two runs must agree bit for bit.

    `run_all` is memoised, so this compares against a FRESH computation by
    clearing the caches — otherwise it would compare an object with itself and
    pass no matter what.
    """
    before = {name: [dict((k, v.value) for k, v in p.q.items())
                     for p in rec.points]
              for name, rec in suite.items()}
    for fn in (X.experiment_1_bow_sharpness, X.experiment_2_prismatic,
               X.experiment_3_lcb, X.experiment_4_separation,
               X.michell_interference_convention_check, X.lever_comparison):
        fn.cache_clear()
    again = X.run_all()
    for name in before:
        for i, p in enumerate(again[name].points):
            for k, v in p.q.items():
                assert v.value == before[name][i][k] or (
                    math.isnan(v.value) and math.isnan(before[name][i][k])), (
                    f"{name} point {i} key {k} is not reproducible")


def test_the_protocol_is_read_from_resistance_not_hard_coded(suite):
    """The integration grid is whatever `resistance.py` currently declares.

    MOTIVATING INCIDENT: this repository MEASURED a 6.9% difference between the
    old 41x14 Michell grid and its convergence grid, with the STATION axis
    responsible for most of it, and the production grid has moved twice since.
    A suite that copied the numbers would keep reporting the protocol it was
    written against rather than the one it ran on.
    """
    for name in ("1-bow-sharpness", "2-prismatic", "3-lcb"):
        p = suite[name].protocol
        assert p["production_grid"] == dict(resistance.PRODUCTION_GRID)
        assert p["converged_grid"] == dict(resistance.CONVERGED_GRID)
    assert (suite["4-separation"].protocol["offsets_grid"]
            == dict(resistance.PRODUCTION_GRID))


# ---------------------------------------------------------------------------
# EXPERIMENT 1 — the controlled quantities, and the quadrature guard
# ---------------------------------------------------------------------------


def test_bow_sweep_holds_the_volume_distribution_exactly_fixed(suite):
    """THE MECHANISM ASSERTION FOR EXPERIMENT 1, and the reason it can exist.

    `geometry._stations` SOLVES the chine half-breadth at every station so the
    delivered immersed area IS the sectional area curve A(x), whatever the
    deadrise and keel depth are. So changing the forefoot changes the WATERLINE
    SHAPE and leaves the LONGITUDINAL VOLUME DISTRIBUTION untouched — which is
    precisely the experiment's claim, and it is invisible in the output.

    MEASURED at the time of writing: volume 4.168216888 m^3, Cp 0.599998 and
    LCB -1.00007 %LWL at ALL SIX bows, i.e. identical to every printed digit.
    The bar here is 1e-9 relative, which is four orders tighter than anything
    the sweep is trying to resolve (the smallest R_t effect measured is 1e-3
    relative).

    IF THIS TEST FAILS the bow sweep is no longer a controlled experiment: it
    would be comparing bows at different displacements and reporting the
    difference as a bow effect. The likely cause would be `x_mb` moving forward
    of the deadrise-warp start (1 - beta_len = 0.65 L) or of the forefoot rise
    start (0.70 L), which would let the bow genes reach the maximum sectional
    area — so this test also fences those two gene choices.
    """
    pts = suite["1-bow-sharpness"].points
    assert len(pts) >= 5, "the brief asks for at least 5 bows"
    for key in ("volume_design_m3", "cp_design", "lcb_design_pct",
                "volume_m3", "disp_kg", "draft_m"):
        vals = np.array([p.value(key) for p in pts])
        ref = vals[0]
        rel = np.max(np.abs(vals - ref)) / max(abs(ref), 1e-12)
        assert rel < 1e-9, (
            f"{key} is NOT held fixed across the bow sweep: "
            f"{vals} (relative spread {rel:.3e}). The sweep is not controlled.")
    # ... and the genes that are supposed to be identical, are.
    for gene in ("LWL", "BWL", "T", "D", "Cp", "lcb", "x_mb", "r_transom",
                 "beta_mid", "beta_bow", "beta_len", "roundness", "rocker",
                 "flare", "sheer_rise"):
        vals = {dict(p.genes)[gene] for p in pts}
        assert len(vals) == 1, f"{gene} varied across the bow sweep: {vals}"
    # ... and the ONE gene that is supposed to vary, does.
    assert len({dict(p.genes)["forefoot"] for p in pts}) == len(pts)


def test_bow_sweep_actually_varies_the_entry_angle(suite):
    """A controlled sweep that varies nothing is a null result by construction.

    MEASURED span: alpha_e_1pct 9.02 -> 34.34 deg, monotone in the forefoot.
    The bar is a 2x span, which is far below the measured 3.8x and would still
    catch a sweep that had collapsed.
    """
    pts = suite["1-bow-sharpness"].points
    ae = [p.value("alpha_e_1pct") for p in pts]
    assert ae == sorted(ae), f"alpha_e is not monotone in the forefoot: {ae}"
    assert max(ae) / min(ae) > 2.0, f"the bow sweep barely moved alpha_e: {ae}"


def test_alpha_e_is_reported_against_formlibs_chord_floor(suite):
    """alpha_e is NOT independent of L/B, so a bare alpha_e means little.

    `formlib.alpha_e_chord_floor_deg` owns the arithmetic and this suite must
    IMPORT it, never re-derive it — a second copy of that floor would be the
    number-declared-twice defect on the one quantity whose whole purpose is to
    make alpha_e interpretable.

    The test recomputes the floor from the record's own L/B and L_E/L via
    formlib and requires agreement, and requires every measured alpha_e to lie
    ABOVE its floor (a chord half-angle cannot beat the chord).
    """
    for p in suite["1-bow-sharpness"].points:
        floor = p.value("alpha_e_chord_floor")
        expect = formlib.alpha_e_chord_floor_deg(p.value("l_over_b_wl"),
                                                 p.value("le_over_l"))
        assert floor == pytest.approx(expect, rel=1e-12)
        assert p.value("alpha_e_1pct") > floor, (
            f"{p.label}: alpha_e {p.value('alpha_e_1pct'):.3f} is below its "
            f"own chord floor {floor:.3f} — the metric is broken")
        assert p.value("alpha_e_over_floor") == pytest.approx(
            p.value("alpha_e_1pct") / floor, rel=1e-12)


def test_the_two_alpha_e_methods_are_reported_for_every_hull(suite):
    """A hull must not be able to game alpha_e with a point plus a spike.

    Both frac = 0.01 and frac = 0.02 are computed BY THE SAME METHOD for every
    hull and the spread is recorded. MEASURED: the spread runs -0.03 deg on the
    finest bow to +3.21 deg on the bluntest, so the metric's method-dependence
    is itself a shape signal and is visible.
    """
    for rec in ("1-bow-sharpness", "2-prismatic", "3-lcb"):
        for p in suite[rec].points:
            a1, a2 = p.value("alpha_e_1pct"), p.value("alpha_e_2pct")
            assert p.value("alpha_e_method_spread") == pytest.approx(a1 - a2,
                                                                     abs=1e-12)


def test_waterline_curvature_is_grid_converged_not_a_sampling_artefact(suite):
    """The discontinuity detector must be measuring the hull, not the sampler.

    `kappa_refinement_ratio` = max kappa at 2n / max kappa at n. A curvature-
    continuous waterline gives ~1.0; a knuckle makes kappa diverge like 1/h and
    the ratio grows without bound. MEASURED across the whole bow sweep:
    1.000000-1.000125.

    This is the same failure mode `geometry.Hull.fairness` records having hit
    once already — a step in the sampling read as a crease in the surface — so
    the fence is here from the start.
    """
    for p in suite["1-bow-sharpness"].points:
        r = p.value("kappa_refinement_ratio")
        assert 0.99 < r < 1.05, (
            f"{p.label}: curvature refinement ratio {r:.4f}. Either the design "
            f"waterline has a curvature singularity in the forward quarter, or "
            f"the metric is reading its own sampling.")
        for band in ("0_10", "10_25"):
            assert p.value(f"kappa_max_{band}") >= p.value(f"kappa_p95_{band}")


def test_a_bow_ranking_that_changes_with_the_grid_is_quadrature_not_physics(
        suite):
    """THE GUARD AGAINST DISCOVERING A BETTER BOW THAT IS AN INTEGRATION ERROR.

    Every bow is evaluated on BOTH `resistance.PRODUCTION_GRID` and
    `resistance.CONVERGED_GRID`, and the ordering of the six by total
    resistance must be identical. This repository MEASURED a 6.9% difference
    between an old production grid and its convergence grid, most of it on the
    station axis — an effect an order of magnitude larger than the bow effect
    being measured here. If the ranking ever differs, the finding in
    `experiment_1_bow_sharpness`'s docstring is not about hulls.

    The test asserts the GUARD, not a direction: it does not care WHICH bow
    wins, only that both grids agree about it.
    """
    rec = suite["1-bow-sharpness"]
    for fn, ok in rec.findings["ranking_identical_on_both_grids"].items():
        assert ok, (
            f"{fn}: the six bows rank differently on the production grid "
            f"{dict(resistance.PRODUCTION_GRID)} and the converged grid "
            f"{dict(resistance.CONVERGED_GRID)}. A 'better bow' that depends "
            f"on the quadrature is not a better bow.")
    for fn in X.VALID_FROUDES:
        f = rec.findings[f"fn{fn:.2f}"]
        assert f["optimum_same_on_both_grids"], (
            f"fn{fn:.2f}: the optimum moves between grids "
            f"({f['best_alpha_e_deg']:.3f} vs "
            f"{f['best_alpha_e_deg_converged_grid']:.3f} deg)")


def test_the_bow_finding_records_whether_its_optimum_is_resolved(suite):
    """An unresolved optimum must be LABELLED, not reported as an optimum.

    MEASURED: at Fn 0.35, 0.40 and 0.45 the winner beats the runner-up by less
    than the production-to-converged grid shift, so
    `optimum_resolved_above_grid_shift` is False there and the docstring says
    so. This test does not require any particular verdict — it requires the
    verdict to be PRESENT and to be arithmetically consistent with the two
    numbers it is derived from, so nobody can quietly drop it.
    """
    for fn in X.VALID_FROUDES:
        f = suite["1-bow-sharpness"].findings[f"fn{fn:.2f}"]
        assert f["optimum_resolved_above_grid_shift"] == (
            f["optimum_margin_n"] > f["grid_shift_n"])
        assert f["grid_shift_n"] > 0.0


# ---------------------------------------------------------------------------
# The validity envelope
# ---------------------------------------------------------------------------


# The records that SWEEP a declared Froude list, and therefore carry a visible
# per-Fn refusal. Experiment 5 is deliberately not among them: it holds the
# speed fixed in m/s and varies LENGTH, so the Froude number is an OUTPUT and
# there is no `fnX.XX` finding to exclude. Its envelope discipline is asserted
# by `test_no_gaming_point_sits_above_the_michell_envelope`, which checks the
# per-point bar and the refusal COUNT — the right shape of check for a sweep
# where an argmin cannot show a reader that it declined a candidate.
#
# Listing it here instead of parametrising over ALL_RECORDS is deliberate: a
# blanket parametrisation would have to be weakened to accommodate experiment
# 5, and weakening a refusal test to fit a new record is how an envelope check
# stops checking anything.
FROUDE_SWEPT_RECORDS = ("1-bow-sharpness", "2-prismatic", "3-lcb",
                        "4-separation")


@pytest.mark.parametrize("name", FROUDE_SWEPT_RECORDS)
def test_points_above_fn_michell_max_are_refused_and_excluded(suite, name):
    """NEVER EVALUATE OUTSIDE A MODEL'S ENVELOPE, and never interpolate over it.

    `FROUDE_SWEEP` deliberately contains Fn 0.50 against
    `resistance.FN_MICHELL_MAX` = 0.45. Every Froude-swept experiment must
    (a) badge that point `L1-INVALID`, (b) mark the finding `excluded`, and
    (c) NOT let it into any optimum, shape or span. The point is carried rather
    than dropped so that the refusal is visible.
    """
    rec = suite[name]
    invalid_fns = [fn for fn in X.FROUDE_SWEEP
                   if fn > resistance.FN_MICHELL_MAX]
    assert invalid_fns, "the sweep no longer contains an out-of-envelope point"
    for fn in invalid_fns:
        key = f"fn{fn:.2f}"
        assert key in rec.findings, f"{name} lost the {key} refusal entirely"
        assert rec.findings[key]["excluded"] is True
        assert "reason" in rec.findings[key]
        for k in ("best_alpha_e_deg", "best_cp_by_rt", "best_lcb_by_rt",
                  "best_s_over_l"):
            assert k not in rec.findings[key], (
                f"{name}/{key}: an optimum was reported for an "
                f"out-of-envelope Froude number")


def test_out_of_envelope_resistance_quantities_carry_the_invalid_badge(suite):
    """The badge is on the QUANTITY, not only on the finding."""
    fn = max(X.FROUDE_SWEEP)
    assert fn > resistance.FN_MICHELL_MAX
    p = suite["1-bow-sharpness"].points[0]
    for k in ("rt_n", "rw_n", "rf_n", "wh_per_nm"):
        q = p.q[f"prod/fn{fn:.2f}/{k}"]
        assert q.tier == X.TIER_PHYSICS_INVALID, f"{k} was badged {q.tier}"
        assert not q.valid
    # and the in-envelope ones are not badged invalid
    for k in ("rt_n", "rw_n", "wh_per_nm"):
        assert p.q[f"prod/fn0.30/{k}"].tier == X.TIER_PHYSICS


def test_the_separation_sweep_excludes_the_invalid_froude_from_its_points(suite):
    """Experiment 4 must not emit sweep points it cannot stand behind."""
    for p in suite["4-separation"].points:
        assert p.valid
        assert p.q["fn"].value <= resistance.FN_MICHELL_MAX


# ---------------------------------------------------------------------------
# EXPERIMENT 2 — fixed displacement
# ---------------------------------------------------------------------------


def test_cp_sweep_holds_displacement_fixed(suite):
    """THE MECHANISM ASSERTION FOR EXPERIMENT 2.

    Volume = Cp * A_max * LWL and A_max does not depend on Cp, so at fixed L, B
    and T a Cp sweep necessarily changes the displacement. Every hull is
    therefore FLOATED to a common target with
    `hydrostatics.solve_to_displacement` at a 1e-6 relative tolerance, and the
    DRAFT is the dependent variable. If this test fails, the sweep is comparing
    boats of different weights.
    """
    pts = suite["2-prismatic"].points
    target = pts[0].value("target_disp_kg")
    for p in pts:
        assert p.value("disp_kg") == pytest.approx(target, rel=2e-6), (
            f"{p.label}: floated to {p.value('disp_kg'):.3f} kg against a "
            f"target of {target:.3f} kg")
    # the dependent variable really did move — otherwise nothing was controlled
    drafts = [p.value("draft_m") for p in pts]
    assert max(drafts) - min(drafts) > 0.05, (
        f"the draft barely moved across the Cp sweep: {drafts}")
    # and the gene really was delivered
    for p in pts:
        assert p.value("cp_gene") == pytest.approx(dict(p.genes)["Cp"],
                                                   abs=1e-12)


def test_cp_sweep_spans_the_declared_gene_bounds(suite):
    """The sweep must cover the DELIVERABLE span, not a literal.

    2026-08-26: `CP_GENE_BOUNDS` is now the range of existing recreational
    craft (0.50-0.95), wider than any single hull's proportions can
    deliver, and the corrected sac solve refuses the undeliverable part
    honestly. The sweep therefore spans `cp_band ∩ CP_GENE_BOUNDS` for its
    own hull — recomputed here from the sweep's recorded genes, never
    restated as numbers.
    """
    from navalai.experiments import cp_sweep_for, reference_demihull

    expect = cp_sweep_for(reference_demihull())
    cps = [p.value("cp_gene") for p in suite["2-prismatic"].points]
    assert min(cps) == pytest.approx(expect[0], abs=1e-12)
    assert max(cps) == pytest.approx(expect[-1], abs=1e-12)
    assert len(cps) >= 5


def test_the_cp_finding_compares_against_limits_and_does_not_restate_it(suite):
    """The practice curve is IMPORTED for comparison, never copied.

    `limits.prismatic_target` is the one home of the Cp(Fn) relation. The
    finding records its value beside the measured optimum and their difference;
    this test recomputes it from `limits` and requires agreement, so a copy
    could not drift in unnoticed.
    """
    for fn in X.VALID_FROUDES:
        f = suite["2-prismatic"].findings[f"fn{fn:.2f}"]
        assert f["practice_curve_cp"] == pytest.approx(
            limits.prismatic_target(fn), abs=1e-12)
        assert f["measured_minus_practice"] == pytest.approx(
            f["best_cp_by_rt"] - limits.prismatic_target(fn), abs=1e-12)


# ---------------------------------------------------------------------------
# EXPERIMENT 3 — LCB at fixed displacement and Cp
# ---------------------------------------------------------------------------


def test_lcb_sweep_holds_displacement_and_cp_fixed_by_construction(suite):
    """THE MECHANISM ASSERTION FOR EXPERIMENT 3.

    `geometry.sac_exponents` solves the two SAC shape exponents subject to
    int a dx = Cp * L, so the ZEROTH moment is a constraint of the solve and
    moving `lcb` redistributes area without changing how much there is. The
    hull therefore floats at its design waterline at every point and the
    displacement is fixed WITHOUT a bisection.

    MEASURED: volume constant to 1.3e-6 relative and Cp to 1e-6 over the whole
    +-3 %LWL band. The bar is 1e-4, two orders looser than measured and three
    orders tighter than the 12-37% R_t effect being resolved.
    """
    pts = suite["3-lcb"].points
    for key in ("volume_design_m3", "cp_design", "disp_kg", "draft_m"):
        vals = np.array([p.value(key) for p in pts])
        rel = np.max(np.abs(vals - vals[0])) / max(abs(vals[0]), 1e-12)
        assert rel < 1e-4, f"{key} moved across the LCB sweep: {vals}"


def test_lcb_sweep_delivers_the_lcb_it_was_asked_for(suite):
    """The design TARGET must be delivered, not approximated.

    Plate P1's whole point is that Cp and LCB are inputs the area curve is
    solved to deliver. MEASURED: the delivered LCB tracks the gene to 2e-4
    %LWL. The bar is 0.01 %LWL — still 50x tighter than
    `limits.PRISMATIC_TOLERANCE`'s spirit and far tighter than the 0.75 %LWL
    sweep step, so a solver that started returning "the nearest reachable LCB"
    would fail here.
    """
    for p in suite["3-lcb"].points:
        assert p.value("lcb_design_pct") == pytest.approx(
            p.value("lcb_gene"), abs=0.01), (
            f"{p.label}: asked for {p.value('lcb_gene'):+.3f} %LWL, delivered "
            f"{p.value('lcb_design_pct'):+.3f}")


def test_lcb_sweep_spans_the_band_limits_declares(suite):
    lcbs = [p.value("lcb_gene") for p in suite["3-lcb"].points]
    assert min(lcbs) == pytest.approx(-limits.LCB_BAND_PCT_LWL, abs=1e-12)
    assert max(lcbs) == pytest.approx(+limits.LCB_BAND_PCT_LWL, abs=1e-12)


def test_a_band_edge_optimum_is_labelled_as_an_edge_not_as_an_optimum(suite):
    """MEASURED: at three of six speeds the best LCB is the -3.0 %LWL EDGE.

    Reporting a binding constraint as an optimum is the failure this flag
    exists to prevent — it would tell a reader that wave resistance has been
    minimised when in fact `limits.LCB_BAND_PCT_LWL` stopped the search. The
    test asserts the flag is consistent with the argmin's position, not that
    any particular speed hits the edge.
    """
    for fn in X.VALID_FROUDES:
        f = suite["3-lcb"].findings[f"fn{fn:.2f}"]
        assert f["optimum_is_band_edge"] == (not f["best_lcb_by_rt_is_interior"])
        if f["optimum_is_band_edge"]:
            assert f["best_lcb_by_rt"] in (pytest.approx(-limits.LCB_BAND_PCT_LWL),
                                           pytest.approx(+limits.LCB_BAND_PCT_LWL))


def test_trim_is_reported_as_a_sensitivity_and_not_as_an_invented_angle(suite):
    """No arrangement, no LCG, therefore no trim angle — only a stiffness.

    `weights.trim_angle_deg` needs an (LCG - LCB) lever and this experiment
    defines no weights, so an angle here would be an invented number. What IS
    measurable is the hull's longitudinal stiffness and the degrees-per-metre
    it implies; the test checks the two are consistent with each other.
    """
    for p in suite["3-lcb"].points:
        stiff = p.value("bml_plus_kb_m")
        assert stiff > 0.0
        assert p.value("trim_deg_per_m_of_lcg_error") == pytest.approx(
            math.degrees(math.atan(1.0 / stiff)), rel=1e-12)
        assert "trim_deg" not in p.q, "an unfounded trim angle appeared"


# ---------------------------------------------------------------------------
# EXPERIMENT 4 — the phase convention, and the two required validations
# ---------------------------------------------------------------------------


def test_the_michell_phase_convention_matches_amplitude_superposition():
    """CORRECTNESS FINDING: `resistance.py`'s interference phase is right.

    The transverse wavenumber is NOT taken on faith from any remembered
    catamaran formula. It is reconstructed from the two kernels
    `resistance._free_wave_vals` visibly uses — the depth decay
    exp(k0 sec^2(th) z), whose exponent is the wavenumber MAGNITUDE, and the
    longitudinal phase exp(i k0 sec(th) x) — as

        ky = sqrt(|k|^2 - kx^2) = k0 sec(th) tan(th) = k0 sec^2(th) sin(th)

    and the two-hull amplitude superposition is then written out in COMPLEX
    exponentials, one per hull at y = -s/2 and +s/2, and integrated. It agrees
    with `michell_rw(..., separation=s)` to 0.0 relative difference.

    NOTE THE `sec` IS SQUARED. A `k0 sec(th) sin(th)` transverse wavenumber —
    the plausible remembered form, one power of sec short — is also computed
    here and differs from what the code contains by 3.99 on a factor whose
    entire range is [0, 4]. So this test has the resolution to catch the error
    it is looking for; it is not a tautology that would pass on any convention.
    """
    c = X.michell_interference_convention_check()
    assert c["match"] is True
    assert c["rw_relative_diff_vs_independent_superposition"] < 1e-12, (
        "the module's catamaran wave resistance does not match an independent "
        "amplitude superposition — the phase convention disagrees with the "
        "derivation and THAT IS THE FINDING")
    assert c["factor_max_abs_diff"] < 1e-8
    # the control: the wrong convention is discriminable
    assert c["factor_max_abs_diff_against_sec1_convention"] > 1.0, (
        "the check cannot tell sec^2 from sec, so it proves nothing")


def test_the_interference_factor_averages_to_two_over_theta():
    """Two infinitely separated demihulls make TWICE one demihull's waves.

    `4 cos^2` averages to 2, NOT to 1 — `resistance.py` records this as an
    explicit correction to the brief it was built from, and
    `CATAMARAN_INTERFERENCE_AT_INFINITY` is the constant. Imported, never
    restated. MEASURED theta-average over s/L 1, 2, 5, 10: 1.99549.
    """
    c = X.michell_interference_convention_check()
    assert resistance.CATAMARAN_INTERFERENCE_AT_INFINITY == 2.0
    assert c["theta_average_of_factor"] == pytest.approx(
        resistance.CATAMARAN_INTERFERENCE_AT_INFINITY, rel=5e-3)


def test_separation_to_infinity_recovers_the_independent_sum(suite):
    """OWNER TEST (a): the correctness test for the phase convention.

    As s -> infinity the two demihulls stop seeing each other's waves, so the
    pair's wave resistance must approach TWICE the isolated demihull's. If the
    transverse phase were wrong this ratio would not approach 1 at all.

    MEASURED, worst over Fn 0.20/0.30/0.45 x s/Lwl 2/5/10: 0.99626, i.e. 0.37%
    low. The bar is `resistance.CATAMARAN_ASYMPTOTIC_RESIDUAL` (0.49%), which
    that module MEASURED and EXPLAINED (the theta grid omits [0, theta_0] and
    weights the omission by 4 for the pair against 2 for the doubled monohull).
    The bar is imported, not restated, and it is NOT a round number chosen to
    swallow the residual.
    """
    rows = suite["4-separation"].findings["asymptotic_recovers_independent_sum"]
    bar = resistance.CATAMARAN_ASYMPTOTIC_RESIDUAL
    assert bar == suite["4-separation"].findings["asymptotic_bar"]
    worst = 0.0
    for fn_key, entries in rows.items():
        assert entries, f"{fn_key} has no asymptotic points"
        for e in entries:
            for col in ("ratio_vs_production_monohull", "ratio_same_theta_grid"):
                dev = abs(e[col] - 1.0)
                worst = max(worst, dev)
                assert dev <= bar, (
                    f"{fn_key} s/L {e['s_over_l']}: {col} = {e[col]:.6f}, "
                    f"{dev:.4%} from the independent sum against a {bar:.2%} "
                    f"bar. s -> infinity does not recover two independent "
                    f"hulls, so the phase convention is wrong.")
            # the ratio must APPROACH 1 from below, not overshoot
            assert e["ratio_vs_production_monohull"] < 1.0 + bar
    assert worst > 0.0, "the asymptotic check measured nothing"


def test_the_interference_is_non_monotonic_in_separation(suite):
    """OWNER TEST (b): the physics must have structure, and it must survive
    doubling the quadrature.

    THE ASSERTION IS THE MECHANISM, NOT A DIRECTION. It requires that at least
    one valid Froude number shows an interior turning point in the interference
    ratio over s/L 0.20-0.50 — i.e. that "wider is always better" is REFUTED
    somewhere — and, separately, that wherever an optimum is located it does
    not move by more than one s/L grid step when the theta resolution is
    DOUBLED. It does NOT require any particular s/L, nor that every speed be
    non-monotonic (MEASURED: Fn 0.40 and 0.45 are monotone over this band and
    the record says so).

    The grid-independence half is the load-bearing one. `resistance.py`
    MEASURED that an under-resolved theta sweep puts up to 1.2% of quadrature
    error into this curve, error that CHANGES SIGN with separation — which is
    exactly the shape of a spurious optimum. A non-monotonicity that vanished
    at 2x n_theta would be that error, not physics.
    """
    rec = suite["4-separation"]
    fnkeys = [f"fn{fn:.2f}" for fn in X.VALID_FROUDES]
    nonmono = [k for k in fnkeys if rec.findings[k]["turning_points"] > 0]
    assert nonmono, (
        "the interference ratio is monotone in s/L at EVERY valid Froude "
        "number. Either the swept band no longer contains a node of the "
        "interference oscillation, or the factor is not being applied.")
    for k in fnkeys:
        f = rec.findings[k]
        assert f["optimum_grid_independent"], (
            f"{k}: the located optimum s/L moves when n_theta is doubled "
            f"({f['n_theta']} -> {f['n_theta_check']}). That is quadrature "
            f"error, not an optimum.")
        assert f["n_theta"] >= resistance.n_theta_for_separation(
            rec.protocol["lwl_m"],
            max(X.SEPARATION_S_OVER_L) * rec.protocol["lwl_m"])
    # an interior optimum must exist somewhere, or "non-monotonic" is only
    # about the ends of the band
    assert any(rec.findings[k]["best_is_interior"] for k in fnkeys), (
        "no valid Froude number has an INTERIOR optimum in s/L")


def test_a_band_edge_separation_optimum_is_labelled_as_an_edge(suite):
    """MEASURED: at Fn 0.40 and 0.45 the best s/L in 0.20-0.50 is 0.500, the
    band EDGE, and the whole band is constructive. Reporting that as "the
    optimum spacing is 0.50" would be reporting where the sweep stopped."""
    for fn in X.VALID_FROUDES:
        f = suite["4-separation"].findings[f"fn{fn:.2f}"]
        edge = (f["best_s_over_l"] in (pytest.approx(X.SEPARATION_S_OVER_L[0]),
                                       pytest.approx(X.SEPARATION_S_OVER_L[-1])))
        assert f["best_is_interior"] == (not edge)


def test_the_separation_sweep_pins_one_theta_grid_across_the_whole_band(suite):
    """A sweep whose members sat on different theta grids would compare
    quadrature errors as if they were interference.

    `resistance.michell_rw_separation_sweep` resolves n_theta ONCE from the
    largest separation; this test proves the experiment used that path with an
    explicit pinned value rather than letting each point resolve its own.
    """
    rec = suite["4-separation"]
    nts = {rec.findings[f"fn{fn:.2f}"]["n_theta"] for fn in X.VALID_FROUDES}
    assert len(nts) == 1, f"the band sweep used several theta grids: {nts}"
    assert rec.protocol["n_theta_band"] == nts.pop()


def test_the_separation_refuses_a_spacing_the_hulls_would_intersect(suite):
    """A demihull spacing below the demihull beam is not a boat.

    `resistance._separation_or_raise` refuses it; the experiment's swept band
    must stay clear of it, and the protocol records the beam so a reader can
    check. MEASURED: demihull beam 1.500 m, smallest swept separation
    0.20 x 12.0 = 2.40 m.
    """
    rec = suite["4-separation"]
    beam = rec.protocol["demihull_beam_m"]
    lwl = rec.protocol["lwl_m"]
    assert min(X.SEPARATION_S_OVER_L) * lwl > beam
    # The hull is built OUTSIDE the raises block on purpose: inside it, a
    # ValueError from any earlier line would satisfy the assertion and the test
    # would pass without ever reaching the call it is about.
    hull = geometry.Hull(X.reference_demihull(),
                         n_stations=resistance.PRODUCTION_GRID["n_stations"])
    xs, zs, Y = hull.offsets_grid(nz=resistance.PRODUCTION_GRID["nz"])
    assert 2.0 * float(Y.max()) == pytest.approx(beam, rel=1e-12)
    with pytest.raises(ValueError, match="INTERSECT"):
        resistance.michell_rw(xs, zs, Y, 3.0, separation=0.5 * beam)


def test_the_separation_wiring_finding_tracks_the_code_it_describes(suite):
    """THE FINDING MUST TRACK THE CODE, IN BOTH DIRECTIONS.

    This test was written to fail when the production path GAINED a separation
    argument, so that nobody could leave a stale "catamarans are scored as one
    demihull" claim behind. IT FIRED, on 2026-08-14: `evaluate.py` now derives
    `separation_m` from `mission.VesselConfig` and passes it to
    `resistance.total_resistance`, and experiment 4's finding has been
    re-measured from False to True.

    It is now written symmetrically — the finding must equal what the code
    actually does — so it will fire again if the wiring is ever removed and the
    record is left claiming the term is live. The record is read from the
    CODE OBJECT, not from a docstring, because a docstring is what went stale.
    """
    rec = suite["4-separation"]
    wired = "separation" in resistance.total_resistance.__code__.co_varnames
    assert rec.findings["production_path_wires_separation"] is wired, (
        f"total_resistance {'has' if wired else 'has no'} a `separation` path, "
        f"but experiment 4 records "
        f"production_path_wires_separation="
        f"{rec.findings['production_path_wires_separation']}. Re-measure the "
        f"finding; do not edit the test to match the stale value.")
    if wired:
        import inspect
        from navalai import evaluate as _ev
        assert "separation=" in inspect.getsource(_ev), (
            "total_resistance accepts `separation` but evaluate.py never "
            "passes it — the ladder is not actually scoring interference and "
            "the finding must say so")
        assert "RE-MEASURED" in rec.findings["production_path_note"]


def test_the_interference_term_is_recorded_as_unvalidated(suite):
    """Self-consistency is not validation, and the record must not blur them.

    `resistance.py` cites Insel & Molland (1992) and Molland et al. (1996) and
    records that NEITHER is transcribed into this repository. So the
    interference term has no experimental anchor at all, and the convention
    check proves only that the implementation matches the derivation.
    """
    c = X.michell_interference_convention_check()
    assert c["validated_against_experiment"] is False
    assert "towing tank" in c["validation_note"]


# ---------------------------------------------------------------------------
# EXPERIMENT 5 — is the objective gameable?
# ---------------------------------------------------------------------------


def test_the_gaming_sweep_holds_displacement_and_absolute_speed_fixed(suite):
    """THE MECHANISM ASSERTION FOR EXPERIMENT 5.

    The whole finding rests on the claim that LENGTH is free while DISPLACEMENT
    and ABSOLUTE SPEED are pinned. If the speed were pinned as a Froude number
    instead, a longer hull would be a faster hull and the gaming direction
    would vanish — that is precisely the control under which the earlier
    959-point fixed-LWL sweep found NOTHING, and the difference between the two
    is the whole experiment.

    So: every point must float to one displacement, run at one speed in m/s,
    and the Froude number must be an OUTPUT that actually varies.
    """
    rec = suite["5-objective-gaming"]
    pts = rec.points
    assert len(pts) > 100, f"only {len(pts)} points; this is not a sweep"
    target = rec.protocol["displacement_target_kg"]
    speed = rec.protocol["speed_mps"]
    for p in pts:
        assert p.value("disp_kg") == pytest.approx(target, rel=2e-6), (
            f"{p.label}: floated to {p.value('disp_kg'):.3f} kg against "
            f"{target:.3f} kg — the sweep is comparing boats of different "
            f"weights and the whole finding is void")
        assert p.value("prod/speed_mps") == pytest.approx(speed, rel=1e-12)
    # Fn is a DEPENDENT variable and must really move, or length is not free
    fns = [p.value("prod/fn") for p in pts]
    assert max(fns) / min(fns) > 1.3, (
        f"Froude number spans only {min(fns):.3f}-{max(fns):.3f}; length is "
        f"not actually free and the gaming axis is not being explored")
    lwls = {p.value("lwl_m") for p in pts}
    assert len(lwls) >= 4, f"only {len(lwls)} lengths swept: {sorted(lwls)}"


def test_no_gaming_point_sits_above_the_michell_envelope(suite):
    """Fn is an OUTPUT here, so the envelope check has to happen per point.

    Experiments 1-4 sweep a declared Froude list and carry the out-of-envelope
    member as a visible refusal. This one cannot: an argmin over 898 candidates
    has no way to show a reader that it declined one, so the point is dropped
    and COUNTED. The count must be present, and nothing that survived may be
    above the bar.
    """
    rec = suite["5-objective-gaming"]
    assert "design_space_refused_above_fn_michell_max" in rec.findings
    assert "design_space_refused_l0" in rec.findings
    assert rec.findings["design_space_evaluated"] == len(rec.points)
    for p in rec.points:
        assert p.value("prod/fn") <= resistance.FN_MICHELL_MAX, (
            f"{p.label} is at Fn {p.value('prod/fn'):.3f}, above "
            f"{resistance.FN_MICHELL_MAX}")
        assert p.q["prod/rt_n"].tier == X.TIER_PHYSICS


def test_minimising_wave_resistance_alone_is_measurably_gameable(suite):
    """THE HEADLINE, AND IT IS ASSERTED AS A MECHANISM, NOT AS A NUMBER.

    MEASURED: the R_w-only optimum buys -84.2% of wave resistance and pays
    +70.7% wetted surface, +55.3% friction, +28.7% total resistance and Wh/NM,
    +183.5% build area and structural mass, and 3.35x non-developable area.

    The test does NOT pin those percentages — they are the measurement and they
    live in the docstring. It asserts the SIGNS and a loose magnitude, so it
    would still fail if the trade-off ever inverted or collapsed, and it would
    not fail merely because the grammar or the grid moved a number.
    """
    f = suite["5-objective-gaming"].findings
    cost = f["rw_only_cost_vs_rt_optimum_frac"]
    assert f["objective_is_gameable_by_rw_alone"] is True
    assert cost["rw_n"] < -0.5, (
        f"the R_w-only optimum only improves R_w by {-100 * cost['rw_n']:.1f}%"
        f"; there is no 'win' left for it to be bought with")
    for k in ("wetted_m2", "rf_n", "rt_n", "wh_per_nm", "build_area_m2",
              "structure_kg", "non_developable_m2"):
        assert cost[k] > 0.05, (
            f"minimising R_w alone no longer costs {k} ({100 * cost[k]:+.1f}%)"
            f". If this is real the gaming direction has closed and the "
            f"finding must be re-measured, not deleted.")


def test_rt_and_wh_per_nm_pick_the_same_hull(suite):
    """`wh_per_nm` = R_t * 1852 / (3600 eta) is monotone in R_t at fixed speed,
    so the two MUST agree. If they ever disagree, either `energy.py` has grown
    a term that is not proportional to resistance, or the speed stopped being
    held fixed — and both would invalidate the reading of experiment 5's whole
    normalisation table."""
    f = suite["5-objective-gaming"].findings
    assert f["rt_and_wh_per_nm_pick_the_same_hull"] is True
    assert f["rw_only_optimum_is_the_rt_optimum"] is False


def test_every_ratio_objective_inflates_and_no_absolute_one_does(suite):
    """THE FINDING THAT OUTRANKS THE REST, fenced as a partition.

    MOTIVATING INCIDENT (2026-08-13/14): ShipGen reports wave drag x0.086 with
    surface area x2.138 and volume x47.9, and diagnoses it as a NORMALISATION
    choice — they scaled the wave-drag coefficient by LOA^2 instead of by
    wetted area. This project was one step from adopting two things on the
    strength of that diagnosis: normalising by wetted area, and an
    area-averaged Gaussian-curvature manufacturing term.

    MEASURED here over ten candidate objectives: the partition is not between
    good and bad denominators, it is between RATIOS and ABSOLUTE QUANTITIES.
    C_T normalised by wetted area inflates the boat by 2.835x and costs +28.7%
    R_t; area-averaged Gaussian curvature is the WORST column in the table at
    3.207x and +52.7%. Every absolute quantity is clean.

    This test asserts the partition, not the individual numbers, so it fences
    the RULE ("never put a coefficient in the objective vector") rather than a
    measurement that is free to move.
    """
    f = suite["5-objective-gaming"].findings
    audit = f["normalisation_audit"]
    ratios = {k: v for k, v in audit.items() if v["is_a_ratio"]}
    absolutes = {k: v for k, v in audit.items() if not v["is_a_ratio"]}
    assert ratios and absolutes, "the audit no longer contains both kinds"

    for k, v in ratios.items():
        assert v["build_area_ratio_vs_rt_optimum"] > 1.5, (
            f"ratio objective {k} no longer inflates the boat "
            f"({v['build_area_ratio_vs_rt_optimum']:.3f}x). Re-measure before "
            f"relaxing the 'no coefficient in the objective' rule — the rule "
            f"rests on this partition.")
    for k in ("rt_n", "wh_per_nm", "build_area_m2", "wetted_m2"):
        assert absolutes[k]["build_area_ratio_vs_rt_optimum"] <= 1.5, (
            f"absolute objective {k} now inflates the boat "
            f"({absolutes[k]['build_area_ratio_vs_rt_optimum']:.3f}x)")
    assert f["every_coefficient_objective_inflates"] is True
    assert f["absolute_objectives_do_not_inflate"] is True

    # ... and the specific one this project was about to adopt.
    assert audit["gauss_abs_mean_per_m2"]["is_a_ratio"] is True
    assert audit["gauss_abs_mean_per_m2"]["rt_penalty_frac"] > 0.1, (
        "area-averaged Gaussian curvature no longer picks a materially worse "
        "boat; navalai/buildability.py's refusal to use it as an objective "
        "rests on this number and must be re-measured, not assumed")


def test_the_gaming_conclusion_survives_the_converged_grid(suite):
    """A CONCLUSION THAT DEPENDS ON THE QUADRATURE IS NOT A CONCLUSION.

    Every point runs on `resistance.PRODUCTION_GRID` (241 x 44) and
    `resistance.CONVERGED_GRID` (481 x 88). This repository MEASURED a 6.9%
    difference between an older production grid and its convergence grid, most
    of it on the station axis — larger than several effects this suite reports.

    THE BAR IS DELIBERATELY NOT "the full ordering is identical". MEASURED, it
    is NOT: over 898 points there are adjacent pairs closer together than the
    quadrature separates, and asserting the stronger property would be the
    more impressive-sounding lie. What the conclusion needs is that the ARGMIN
    is grid-independent and that the SEPARATION BETWEEN the two optima is large
    against the grid shift — MEASURED 89.04 N against 1.36 N, a factor of 65.
    """
    g = suite["5-objective-gaming"].findings["grid_check"]
    for key in ("rw_n", "rt_n"):
        assert g[key]["argmin_identical"], (
            f"the {key} optimum MOVES between the production and converged "
            f"Michell grids. The gaming finding would then be quadrature "
            f"error, not hydrodynamics, and that is itself the finding.")
        assert g[key]["top10_set_agreement"] >= 0.8
    assert g["conclusion_resolved_above_grid_shift"] is True
    assert g["separation_over_grid_shift"] > 10.0, (
        f"the two optima are separated by only "
        f"{g['separation_over_grid_shift']:.1f}x the grid shift; below ~10x "
        f"this experiment cannot tell a boat from a quadrature")
    assert g["largest_production_to_converged_shift_n"] > 0.0, (
        "the grid shift measured as zero, so the two grids returned identical "
        "answers everywhere — which means only one of them actually ran")


def test_the_gaming_record_carries_the_buildability_proxies_as_proxies(suite):
    """Manufacturing complexity is a MODELLING CLAIM here, not a measurement,
    and the record must not let it pass as one.

    The metrics come from `navalai/buildability.py`, which imports rather than
    re-implements every quantity it composes. This test proves the experiment
    reads that module rather than carrying its own copy — a second copy of a
    curvature or an area is this repository's recurring defect.
    """
    from navalai import buildability

    rec = suite["5-objective-gaming"]
    assert rec.protocol["shell_grid"] == dict(buildability.SHELL_GRID)
    p = rec.points[0]
    genes = dict(p.genes)
    hull = geometry.Hull(grammar.vector(genes), n_stations=X.HYDRO_STATIONS)
    c = buildability.shell_complexity(hull, p.value("prod/fn") * 0.0)
    assert p.value("build_area_m2") == pytest.approx(c.build_area_m2, rel=1e-9)
    assert p.value("structure_kg") == pytest.approx(c.structure_kg, rel=1e-9)
    assert p.value("non_developable_m2") == pytest.approx(
        c.non_developable_area_m2, rel=1e-9)
    # and the sigma is a MEASURED refinement residual, not a declared fraction
    q = p.q["non_developable_m2"]
    assert q.basis == X.BASIS_GRID and q.sigma > 0.0


def test_structural_mass_and_build_area_are_the_same_number(suite):
    """A NUMBER LIVES IN EXACTLY ONE PLACE — and this one already lives twice.

    MOTIVATING FINDING (2026-08-14): the brief for this work asked for
    "structural mass" to be ADDED to the objective alongside wetted area. It is
    already there. `energy.weight_budget` computes
    structure = (shell + deck) * t * PLY_DENSITY * 1.35 and `optimize.py`'s
    objective 2 is (shell + deck), so at a fixed panel thickness the two are
    EXACTLY proportional and a separate structural-mass objective would be a
    second copy of an existing column.

    This test measures the proportionality across the whole sweep, so that if
    the thickness ever becomes hull-dependent (ISO 12215-5 derived per hull,
    which `engineer.assess` already supports) the constant breaks and the
    recommendation genuinely changes.
    """
    pts = suite["5-objective-gaming"].points
    ratios = np.array([p.value("structure_kg") / p.value("build_area_m2")
                       for p in pts])
    spread = (ratios.max() - ratios.min()) / ratios.mean()
    assert spread < 1e-9, (
        f"structure_kg / build_area_m2 spans {spread:.3e} across the sweep. "
        f"It used to be a constant, which is why a separate structural-mass "
        f"objective was refused as a number declared twice. If the panel "
        f"thickness is now hull-dependent, that recommendation must be "
        f"re-derived.")


# ---------------------------------------------------------------------------
# The cross-experiment result
# ---------------------------------------------------------------------------


def test_the_lever_comparison_is_computed_on_one_protocol(suite):
    """The three levers must be comparable, or ranking them means nothing.

    All three sweeps run on one parent hull, one displacement and one
    integration grid; this test asserts that the parent genes agree everywhere
    except on the gene each sweep varies, so the spans in `lever_comparison`
    are differences of the same thing.
    """
    varied = {"1-bow-sharpness": "forefoot", "2-prismatic": "Cp",
              "3-lcb": "lcb"}
    ref = dict(X.REFERENCE_DEMIHULL)
    for name, gene in varied.items():
        for p in suite[name].points:
            g = dict(p.genes)
            for k, v in ref.items():
                if k == gene:
                    continue
                assert g[k] == pytest.approx(v, abs=1e-12), (
                    f"{name}/{p.label}: gene {k} is {g[k]} not the reference "
                    f"{v}; the lever spans are not comparable")
    lv = X.lever_comparison()
    for fn in X.VALID_FROUDES:
        row = lv[f"fn{fn:.2f}"]
        assert set(row) >= {"bow_waterline_shape", "cp", "lcb",
                            "strongest_lever", "weakest_lever"}
        assert all(row[k] > 0.0 for k in ("bow_waterline_shape", "cp", "lcb"))
        assert row[row["strongest_lever"]] >= row[row["weakest_lever"]]


def test_the_reference_demihull_is_feasible_and_slender():
    """The parent hull must pass L0 and must be the slender thing Michell wants.

    `resistance.py` records that this repository's usual reference hull is
    L/B 3.13, outside the slenderness thin-ship theory assumes. A bow
    experiment run on a hull the theory does not describe would be measuring
    the wrong integral, so the parent here sits at the top of
    `grammar.L_OVER_B_BAND`.
    """
    params = X.reference_demihull()
    rep = grammar.check(params)
    assert rep.ok, rep.violations
    p = grammar.named(params)
    l_over_b = p["LWL"] / p["BWL"]
    assert l_over_b == pytest.approx(grammar.L_OVER_B_BAND[1], abs=0.51), (
        f"the parent demihull is L/B {l_over_b:.2f}, not near the slender end "
        f"of {grammar.L_OVER_B_BAND}")


def test_with_genes_refuses_an_unknown_gene():
    """A typo'd override that silently does nothing produces a sweep of
    identical hulls that looks like a null result."""
    with pytest.raises(X.ExperimentError, match="not one of"):
        X.with_genes(forefeet=0.5)
    assert len(X.with_genes(forefoot=0.5)) == grammar.N_PARAMS


def test_curve_shape_classifies_what_it_claims():
    """The classifier is used to state findings, so it is fenced itself."""
    assert curve("monotonic-increasing", [1, 2, 3], [1.0, 2.0, 3.0])
    assert curve("monotonic-decreasing", [1, 2, 3], [3.0, 2.0, 1.0])
    assert curve("interior-minimum", [1, 2, 3], [3.0, 1.0, 2.0])
    assert curve("interior-maximum", [1, 2, 3], [1.0, 3.0, 2.0])
    assert curve("non-monotonic", [1, 2, 3, 4, 5], [3.0, 1.0, 2.0, 0.5, 2.0])
    sh = X.curve_shape([1, 2, 3], [3.0, 1.0, 2.0])
    assert sh["argmin_is_interior"] and sh["argmin_x"] == 2
    with pytest.raises(X.ExperimentError):
        X.curve_shape([1, 2], [1.0, 2.0])


def curve(expect, xs, ys):
    got = X.curve_shape(xs, ys)["shape"]
    assert got == expect, f"expected {expect}, got {got}"
    return True


def test_the_report_renders(suite):
    """The report is the deliverable; it must not throw on any record shape."""
    txt = X.report()
    assert "NavalAI experiment suite" in txt
    for name in ALL_RECORDS:
        assert name in txt
    assert "EXCLUDED" in txt, "the refusal is not visible in the report"
    assert str(resistance.FN_MICHELL_MAX) in txt
