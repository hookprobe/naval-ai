"""Gate 1: Wigley Michell anchor, hydrostatics physics, full L1 eval < 50 ms."""

import pathlib

import time

import numpy as np
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.wigley import cw_curve, wigley_offsets, wetted_surface
from navalai import grammar
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.hydrostatics import solve, solve_to_displacement, gm
from navalai.mission import MissionSpec, parse_mission
from tests.test_phase0 import mid_params


# ---------------- Wigley anchor ----------------

FNS = np.array([0.20, 0.24, 0.266, 0.30, 0.32, 0.35, 0.40, 0.45, 0.482, 0.50])


@pytest.fixture(scope="module")
def wigley_cw():
    cws, S = cw_curve(FNS, nx=121, nz=25)
    return cws, S


def test_wigley_magnitude_band(wigley_cw):
    """Michell Cw for Wigley at the last hump (Fn~0.5) is order 1e-3.
    Published Michell computations put it roughly in [1e-3, 4e-3]."""
    cws, _ = wigley_cw
    cw_50 = cws[-1]
    assert 8e-4 < cw_50 < 5e-3, f"Cw(0.5) = {cw_50:.3e} outside honest band"


def test_wigley_hump_hollow_oscillation(wigley_cw):
    """The classic hump/hollow interference pattern must exist below Fn 0.45."""
    cws, _ = wigley_cw
    seg = cws[:8]  # Fn 0.20 .. 0.45
    d = np.diff(seg)
    sign_changes = int(np.sum(np.abs(np.diff(np.sign(d))) > 0))
    assert sign_changes >= 2, f"no interference oscillation: {seg}"


def test_wigley_positive_and_monotone_tail(wigley_cw):
    cws, _ = wigley_cw
    assert (cws > 0).all()
    # rising toward the last hump: Cw(0.482) > Cw(0.40)
    assert cws[8] > cws[6]


def test_wigley_grid_convergence():
    fns = np.array([0.30, 0.40])
    c1, _ = cw_curve(fns, nx=81, nz=17)
    c2, _ = cw_curve(fns, nx=161, nz=33)
    rel = np.abs(c2 - c1) / c2
    assert (rel < 0.02).all(), f"grid sensitivity {rel} >= 2%"


def test_wigley_wetted_surface_reasonable():
    # analytic flat-plate lower bound: S > 2 * L * T (two sides of centreplane)
    S = wetted_surface(10.0)
    assert 2 * 10.0 * (1.0 / 1.6) < S < 2.2 * 10.0 * (1.0 / 1.6) * 1.6


# ---------------- hydrostatics physics ----------------

def test_hydrostatics_archimedes_consistency():
    h = Hull(mid_params())
    hs = solve(h)
    assert hs.volume > 1.0
    assert 0.3 < hs.cb < 0.75          # sane block coefficient for a chine hull
    assert 0.45 < hs.cp < 0.85
    assert 0 < hs.kb < -float(h.z_keel.min())   # KB between keel and WL
    assert hs.bm > 0.5                 # a 3.2 m beam boat has real BM


def test_draft_solve_converges_and_is_monotone():
    h = Hull(mid_params())
    hs0 = solve(h)
    m_light = hs0.disp_kg * 0.6
    m_heavy = hs0.disp_kg * 1.3
    s1, wl1 = solve_to_displacement(h, m_light)
    s2, wl2 = solve_to_displacement(h, m_heavy)
    assert s1.disp_kg == pytest.approx(m_light, rel=2e-3)
    assert s2.disp_kg == pytest.approx(m_heavy, rel=2e-3)
    assert wl1 < wl2                   # heavier -> floats deeper


def test_gm_decreases_with_higher_kg():
    h = Hull(mid_params())
    hs = solve(h)
    assert gm(hs, 0.5) > gm(hs, 1.0)


def test_swamping_is_refused():
    h = Hull(mid_params())
    with pytest.raises(ValueError, match="swamp"):
        solve_to_displacement(h, 1e6)


# ---------------- full ladder ----------------

def test_l1_evaluation_complete_and_fast():
    m = MissionSpec()
    ev = evaluate(mid_params(), m)
    assert ev.tier == "L1"
    assert ev.hydro is not None and ev.resistance is not None
    assert ev.energy.wh_per_nm > 0
    assert ev.gm_m is not None
    assert set(ev.badges) >= {"displacement", "GM", "resistance", "wh_per_nm"}
    # honesty rule 1, tightened: every number carries a band AND says whether
    # that band was PROPAGATED or merely declared. The audit found every sigma
    # in the system was a hard-coded fraction of its own value while the one
    # real uncertainty the mass model computes (agg.sigma_kg) was discarded —
    # a band that is always 0.30 x value is a decoration, and calling it
    # 'one-sigma' in the provenance DB was the dishonest part.
    for _q, (tier, sigma, basis) in ev.badges.items():
        assert tier == "L1" and sigma > 0
        assert basis in ("measured", "assumed")
    assert ev.badges["displacement"][2] == "measured", (
        "displacement sigma must come from the weight model, not a fraction")
    # Gate 1 timing: warm evaluation under 50 ms
    evaluate(mid_params(), m)
    t0 = time.perf_counter()
    evaluate(mid_params(), m)
    assert (time.perf_counter() - t0) * 1e3 < 50.0


def test_l0_reject_is_cheap_and_early():
    x = mid_params()
    x[0] = 50.0   # LWL out of bounds
    ev = evaluate(x, MissionSpec())
    assert not ev.ok and ev.tier == "L0"
    assert ev.eval_ms < 5.0


def test_mission_parser_floor():
    m = parse_mission("6 tonne solar-electric liveaboard, 10 m, Danube and "
                      "Black Sea coastal, cruise 5 knots, 2 crew, 40 kWh battery")
    assert m.displacement_target_kg == pytest.approx(6000)
    assert m.lwl_hint_m == pytest.approx(10)
    assert m.cruise_speed_kn == pytest.approx(5)
    assert m.design_category == "C"     # Black Sea coastal governs over river
    assert m.crew == 2
    assert m.energy.battery_kwh == pytest.approx(40)


def test_mission_parser_defaults_are_flagged():
    m = parse_mission("a nice boat please")
    assert "displacement" in m.notes and "speed" in m.notes


# --------------------------------------------------------------------------
# Weight / CG model — the spine BuildPlan2 tiers E and F feed into.
# --------------------------------------------------------------------------

def test_draft_is_measured_from_the_keel_not_inverted():
    """`t_mean = t_design - wl` was inverted; it is exact only at wl = 0, which
    is why every test passed. MEASURED on the mid hull: at wl = -0.40 the
    volume collapses to 1.088 m^3 (barely immersed) while draft was reported
    as 0.95 m — LARGER than the 0.55 m at wl = 0. Immersion is wl + t_design.

    It propagated: cb = vol/(lwl*bmax*t_mean) came out ~0.11 instead of ~0.34,
    and evaluate() feeds that cb to form_factor(), so the frictional form
    factor was wrong at any off-design waterline.
    """
    from navalai.geometry import Hull
    from navalai.hydrostatics import solve
    from tests.test_phase0 import mid_params

    h = Hull(mid_params())
    t_design = -float(h.z_keel.min())

    prev_vol = prev_draft = None
    for wl in (0.3, 0.1, 0.0, -0.1, -0.3):
        s = solve(h, wl=wl)
        assert s.draft == pytest.approx(wl + t_design, abs=1e-9), wl
        if prev_vol is not None:
            # falling waterline => less volume AND less draft, together
            assert s.volume < prev_vol, wl
            assert s.draft < prev_draft, wl
        prev_vol, prev_draft = s.volume, s.draft
    assert solve(h, wl=0.0).draft == pytest.approx(t_design)


def test_weight_items_reproduce_the_scalar_budget_exactly():
    """Positioning the masses must not move them. If the item list and the old
    five-bucket budget ever disagree on total or KG, one of them is wrong and
    'one weight model, one truth' is already broken.
    """
    from navalai.energy import (EnergySpec, shell_area_m2, weight_budget,
                                weight_items)
    from navalai.geometry import Hull
    from navalai.weights import aggregate
    from tests.test_phase0 import mid_params

    h = Hull(mid_params())
    lwl, depth, t_design = float(h.x[-1]), 1.55, -float(h.z_keel.min())
    # gap C9: `h.wetted_surface(0.0) * 1.6` here too, the L1 ladder's old
    # literal copied into the fixture that checks the L1 ladder.
    surf, deck, spec = shell_area_m2(h), h.deck_area(), EnergySpec()

    wb = weight_budget(lwl, depth, surf, deck, spec)
    agg = aggregate(weight_items(lwl, depth, surf, deck, spec, t_design))

    assert agg.total_kg == pytest.approx(wb.total_kg, rel=1e-12)
    assert agg.vcg_above_keel(t_design) == pytest.approx(wb.kg_above_keel,
                                                         rel=1e-12)
    # and the model now knows things it could not express before
    assert 0.0 < agg.lcg_m < lwl
    assert agg.tcg_m == pytest.approx(0.0)
    assert agg.sigma_kg > 0.0


def test_moving_mass_moves_the_centre_of_gravity_analytically():
    """The whole point: a berth moved aft must move the CG, by the amount
    statics says. Previously mass had no position, so an arrangement could not
    trim or list the boat at all.
    """
    from navalai.weights import MassItem, aggregate

    base = [MassItem("hull", 4000.0, x_m=5.0, z_m=-0.2),
            MassItem("berth", 500.0, x_m=5.0, z_m=0.4)]
    moved = [base[0], MassItem("berth", 500.0, x_m=7.0, z_m=0.4)]

    a, b = aggregate(base), aggregate(moved)
    # dLCG = m*d / total
    assert b.lcg_m - a.lcg_m == pytest.approx(500.0 * 2.0 / 4500.0, rel=1e-12)
    assert b.vcg_m == pytest.approx(a.vcg_m)          # z unchanged

    # asymmetry produces a real TCG, which used to be inexpressible
    listed = aggregate([base[0], MassItem("galley", 500.0, x_m=5.0, z_m=0.4,
                                          y_m=1.2)])
    assert listed.tcg_m == pytest.approx(500.0 * 1.2 / 4500.0, rel=1e-12)


def test_slack_tank_raises_g_by_the_free_surface_moment():
    """A slack tank raises G virtually by rho*i_t/displacement. For a wide flat
    tank this is the difference between clearing a category GM floor and not,
    so it is modelled rather than assumed small.
    """
    from navalai.weights import MassItem, aggregate

    i_t = 0.9 * 0.6 ** 3 / 12.0                      # box tank l*b^3/12
    items = [MassItem("hull", 4000.0, x_m=5.0, z_m=-0.2),
             MassItem("water", 200.0, x_m=4.0, z_m=-0.3,
                      fluid_rho=1000.0, fsm_i_t_m4=i_t, slack=True)]
    agg = aggregate(items)
    assert agg.free_surface_moment == pytest.approx(1000.0 * i_t)
    assert agg.free_surface_correction() == pytest.approx(
        1000.0 * i_t / 4200.0, rel=1e-12)

    # a PRESSED tank has no free surface and must not be charged for one
    pressed = aggregate([items[0],
                         MassItem("water", 200.0, x_m=4.0, z_m=-0.3,
                                  fluid_rho=1000.0)])
    assert pressed.free_surface_correction() == 0.0


def test_aggregate_refuses_to_invent_a_displacement():
    """Honesty rule 1 applied to mass: an empty list is not zero mass, it is an
    unanswered question. A silently-zero aggregate would float the boat on
    nothing.
    """
    from navalai.weights import MassItem, aggregate

    with pytest.raises(ValueError):
        aggregate([])
    with pytest.raises(ValueError):
        MassItem("bad-tier", 10.0, x_m=1.0, z_m=0.0, tier="L9")
    with pytest.raises(ValueError):
        MassItem("negative", -1.0, x_m=1.0, z_m=0.0)
    with pytest.raises(ValueError):
        MassItem("slack-no-fsm", 10.0, x_m=1.0, z_m=0.0, slack=True)


# ---------------------------------------------------------------------------
# "One weight model, one truth" — audit 2026-08-05. The positioned model in
# weights.py existed only in ITS OWN TESTS: evaluate() read a separate scalar
# budget, and dynamics.inertia() inlined a THIRD copy of the placement that had
# drifted (payload 0.55*Lwl against 0.48*Lwl in energy.LCG_FRACTION — 0.7 m
# apart on a 10 m boat). So an arrangement could move mass with no effect on
# stability, and inertia was taken about a CG stability did not agree with.
def test_placement_is_declared_in_exactly_one_place():
    import navalai.dynamics as D
    import navalai.energy as E
    src = pathlib.Path(D.__file__).read_text()
    body = src[src.index("def inertia("):src.index("def mooring(")]
    # positions must come from the items, never from a local fraction table
    assert "i.x_m" in body and "i.z_m" in body
    for frac in ("0.55 * L", "0.45 * L", "0.70 * D", "1.00 * D"):
        assert frac not in body, f"dynamics.inertia re-declares placement: {frac}"
    assert set(D._OWN_GYRADIUS) == set(E.LCG_FRACTION) == set(E.VCG_FRACTION)


def test_moving_mass_aft_trims_the_boat():
    """The point of a positioned model: mass that moves must have a consequence.

    Before this was wired up, evaluate() took KG from a scalar budget and had no
    LCG at all, so a 500 kg battery could sit anywhere with identical output.
    """
    import numpy as np

    from navalai.evaluate import evaluate
    from navalai.mission import parse_mission
    import navalai.energy as E

    m = parse_mission("a 10 metre solar boat for 6 people, 3 tonnes, category C")
    base = evaluate(np.array(mid_params()), m)
    assert base.masses is not None and base.gm_l_m is not None

    orig = dict(E.LCG_FRACTION)
    try:
        E.LCG_FRACTION["battery"] = orig["battery"] - 0.25   # 2.5 m aft
        moved = evaluate(np.array(mid_params()), m)
    finally:
        E.LCG_FRACTION.clear()
        E.LCG_FRACTION.update(orig)

    assert moved.masses.lcg_m < base.masses.lcg_m, "LCG did not move"
    assert moved.trim_deg < base.trim_deg, "moving mass aft did not trim it aft"
    assert abs(moved.trim_deg - base.trim_deg) > 0.05, "trim response is inert"


def test_slack_tank_lowers_gm_through_the_free_surface_moment():
    from navalai.weights import MassItem, aggregate

    dry = [MassItem("hull", 2000.0, 5.0, 0.2)]
    slack = dry + [MassItem("tank", 200.0, 4.0, -0.3, fluid_rho=1000.0,
                            fsm_i_t_m4=0.35, slack=True)]
    a_dry, a_slack = aggregate(dry), aggregate(slack)
    assert a_dry.free_surface_correction() == 0.0
    # FSC = sum(rho*i_t)/displacement, a VIRTUAL RISE of G, so it must be > 0
    assert a_slack.free_surface_correction() == pytest.approx(
        1000.0 * 0.35 / 2200.0, rel=1e-12)


def test_lateral_areas_use_the_same_convention():
    """Wind and current must both act on ONE side of the profile.

    Measured before the fix: 20.84 m^2 windage against a 10.42 m^2 side profile
    (the factor 2 was applied above the waterline only), so line tension came
    out about 2x while the underwater area was correct.
    """
    import numpy as np

    from navalai.dynamics import mooring
    h = Hull(mid_params())
    side_profile = float(np.trapezoid(np.maximum(h.z_sheer, 0.0), h.x))
    mo = mooring(h, wind_ms=25.0, current_ms=0.0)
    implied = mo.wind_force_n / (0.5 * 1.225 * 1.0 * 25.0 ** 2)
    assert implied == pytest.approx(side_profile, rel=1e-9)


def test_wigley_matches_the_reference_curve_point_by_point():
    """Gate 1's bar is "Wigley wave resistance matches the analytic/tank curve
    within published Michell error bars". THE ANCHOR WAS MEASURING ITSELF.

    Two findings, one on top of the other.

    FIRST (closed 2026-08-06): the test asserted a MAGNITUDE BAND (8e-4 <
    Cw(0.5) < 5e-3) plus >=2 sign changes, with no reference curve in the repo
    and no per-point comparison, so any function of roughly the right size with
    a couple of wiggles would have passed.

    SECOND, and the reason this test changed again — GAP E2. The reference
    added to close the first finding, `REFERENCE_CW`, was OUR OWN Michell
    integral on a converged grid, frozen. The docstring said so honestly, but a
    gate that compares our output against a frozen copy of our output measures
    SELF-CONSISTENCY: any coherent error in the offsets, the kernel or the
    quadrature that was re-frozen would have passed forever, and every claim
    resting on Gate 1 inherits that. The prose here even cited "the exact
    separable solution, which agrees to -0.86..-2.11%" — a number computed once
    by a past session and never committed as code, so it could not be re-run.

    IT IS CODE NOW. `benchmarks.wigley.rw_analytic` evaluates the x and z
    integrals of Michell's amplitude function SYMBOLICALLY (the Wigley offset is
    a product of a function of x and a function of z, so the double integral
    factors and both factors have antiderivatives), leaving a single theta
    quadrature that converges to 1e-10 and agrees with scipy's adaptive
    integrator to 1e-6. It touches no grid, no offsets array and no trapezoid
    of ours. `ANALYTIC_RW_N` freezes it as a force in newtons, so not even the
    wetted surface is ours.

    HONEST SCOPE, still: this is exact for MICHELL'S INTEGRAL, and it now
    validates our implementation against mathematics rather than against
    itself. It does NOT validate thin-ship theory against a towing tank —
    Michell overpredicts the humps by tens of percent and no tank data for this
    hull is transcribed anywhere in this repository. That anchor is still owed.

    MEASURED 2026-08-07: the shipped production grid (121x25) sits -2.113%
    (Fn 0.20) to -0.861% (Fn 0.50) from the closed form — consistently LOW,
    which is the expected sign, since `wigley_offsets` truncates the z-grid at
    -T/nz^2 rather than 0 and under-resolves the shoulders. Bar 3%.
    """
    import numpy as np

    from benchmarks.wigley import (ANALYTIC_RW_N, ANALYTIC_TOL_PRODUCTION,
                                   REFERENCE_S, cw_analytic, cw_curve,
                                   rw_analytic, wetted_surface)

    assert wetted_surface(10.0) == pytest.approx(REFERENCE_S, rel=1e-6)

    # 1. the anchor is reproducible: the function still lands on the literals.
    for fn, rw in ANALYTIC_RW_N.items():
        assert rw_analytic(fn) == pytest.approx(rw, rel=1e-6), (
            f"Fn {fn}: closed form moved to {rw_analytic(fn):.6e} against the "
            f"frozen {rw:.6e} — re-derive it deliberately or something broke")

    # 2. our numerics against it, per point. S cancels: both sides use the
    #    module's wetted surface, so the physics being compared is the force.
    fns = np.array(sorted(ANALYTIC_RW_N))
    cws, _S = cw_curve(fns, 10.0)          # production grid, as shipped
    exact = cw_analytic(fns)
    worst = 0.0
    for fn, cw, ex in zip(fns, cws, exact):
        worst = max(worst, abs(cw / ex - 1.0))
        assert cw == pytest.approx(ex, rel=ANALYTIC_TOL_PRODUCTION), (
            f"Fn {fn}: {cw:.4e} vs closed form {ex:.4e} "
            f"({100 * (cw / ex - 1):+.3f}%)")
    assert worst < ANALYTIC_TOL_PRODUCTION, worst
    # and the error is one-signed, which is the diagnostic a band cannot give
    assert (cws < exact).all(), "the truncation bias changed sign"

    # 3. The SHAPE is the physics, asserted ON THE CLOSED FORM: the hump at
    #    Fn 0.30 exceeds the hollow at 0.35 by >1.5x and the curve rises again.
    #    Asserting it on our own curve alone is what "measuring itself" means.
    i30, i35 = list(fns).index(0.30), list(fns).index(0.35)
    assert exact[i30] > exact[i35] * 1.5
    assert exact[-1] > exact[i35]
    assert cws[i30] > cws[i35] * 1.5
    assert cws[-1] > cws[i35]


def test_the_wigley_displacement_is_the_exact_4LBT_over_9():
    """The one Wigley quantity that carries no discretisation at all.

    Int (1-(2x/L)^2) dx = 2L/3 and Int (1-(z/T)^2) dz = 2T/3, so the displaced
    volume to z=0 is 2 * (B/2) * (2L/3) * (2T/3) = 4LBT/9 exactly. Integrating
    the offsets grid the Michell tier actually uses must land on it, or the
    hull being resisted is not the hull being displaced.

    MEASURED: the shipped 121x25 grid integrates to within 0.42% of exact, and
    the converged 321x65 grid to 0.024% — the residual is the z-grid stopping
    at -T/nz^2 instead of 0, i.e. the same truncation that makes Cw read low.
    """
    import numpy as np

    from benchmarks.wigley import displacement_exact, proportions, wigley_offsets

    L = 10.0
    B, T = proportions(L)
    assert displacement_exact(L) == pytest.approx(4 * L * B * T / 9, rel=1e-15)

    for (nx, nz), tol in (((121, 25), 5e-3), ((321, 65), 5e-4)):
        xs, zs, Y, _B, _T = wigley_offsets(L, nx, nz)
        vol = 2.0 * float(np.trapezoid(np.trapezoid(Y, zs, axis=1), xs))
        assert vol == pytest.approx(displacement_exact(L), rel=tol), (
            f"{nx}x{nz}: {vol:.6f} m^3 vs exact {displacement_exact(L):.6f}")


def test_the_regression_pin_still_agrees_with_the_closed_form():
    """`REFERENCE_CW` survives gap E2 with a demoted job, and this is the fence.

    It is our own converged-grid output, kept because `flywheel.
    benchmark_integrity` needs a frozen curve to detect that the physics moved
    under a retrain — a drift question. It is no longer what Gate 1's
    correctness test compares against. Without this test it could be re-frozen
    around a broken integral and go on satisfying every drift check forever,
    which is exactly the self-reference E2 is about, displaced by one hop.

    MEASURED 2026-08-07: the converged grid sits -0.773% (Fn 0.20) to -0.240%
    (Fn 0.25) from the closed form. Bar 1%.
    """
    import numpy as np

    from benchmarks.wigley import (ANALYTIC_RW_N, ANALYTIC_TOL_CONVERGED,
                                   REFERENCE_CW, REFERENCE_S, cw_analytic)

    assert set(REFERENCE_CW) == set(ANALYTIC_RW_N), (
        "the pin and the anchor stopped covering the same Froude numbers, so "
        "one of them is no longer checked against the other")
    fns = np.array(sorted(REFERENCE_CW))
    exact = cw_analytic(fns)
    for fn, ex in zip(fns, exact):
        ref = REFERENCE_CW[float(fn)]
        assert ref == pytest.approx(ex, rel=ANALYTIC_TOL_CONVERGED), (
            f"Fn {fn}: pinned {ref:.4e} vs closed form {ex:.4e} "
            f"({100 * (ref / ex - 1):+.3f}%) — the regression pin has drifted "
            f"away from the mathematics it is supposed to approximate")
    # the pin must also still describe the grid it claims to
    assert REFERENCE_S == pytest.approx(14.87905, rel=1e-6)
