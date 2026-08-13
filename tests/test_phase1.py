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


def test_an_unbracketable_or_unconverged_flotation_is_refused_not_midpointed():
    """Gap E14: `solve_to_displacement` returned the bisection MIDPOINT after
    80 iterations, in the same 2-tuple as a converged answer.

    MEASURED on this hull, and it reproduces the register's figure exactly:
    asking for 1.0 kg returned a state displacing 4.134 kg, an error of
    +313.4%, with nothing in the return value to say so. The cause was never
    the iteration count — `z_lo = z_keel.min() * 0.98` is "nearly dry" and the
    hull still displaces 4.134 kg there, so a target below that is outside the
    bracket and bisection cannot reach it however long it runs. Defect class 1:
    a failure to converge scored as an answer.

    BOTH new refusals are fed the verbatim input they exist to reject, and both
    are checked against the good case, because a guard proved only on the good
    case proves nothing about rejection.
    """
    h = Hull(mid_params())

    # 1. THE LOW BRACKET. 1.0 kg is the register's own input.
    with pytest.raises(ValueError, match="floats too high"):
        solve_to_displacement(h, 1.0)
    # ...and the message must carry the number that made it impossible, or the
    # refusal is not diagnosable.
    try:
        solve_to_displacement(h, 1.0)
    except ValueError as exc:
        assert "4.134" in str(exc)
    # It is NOT the swamping refusal wearing a new string.
    with pytest.raises(ValueError, match="swamp"):
        solve_to_displacement(h, 1e6)

    # The boundary is where it is measured to be: 4.0 kg is unreachable and
    # 5.0 kg floats, so the guard is not simply rejecting small numbers.
    with pytest.raises(ValueError, match="floats too high"):
        solve_to_displacement(h, 4.0)
    s5, _wl5 = solve_to_displacement(h, 5.0)
    assert s5.disp_kg == pytest.approx(5.0, rel=1e-3)

    # 2. NON-CONVERGENCE. `tol=0.0` can never be satisfied, so the loop runs
    #    out — the branch that used to return the midpoint.
    with pytest.raises(ValueError, match="did not converge"):
        solve_to_displacement(h, 6000.0, tol=0.0)

    # 3. THE ORDINARY PATH IS UNTOUCHED, at the four targets measured above.
    for target in (10.0, 100.0, 2000.0, 6000.0):
        st, _wl = solve_to_displacement(h, target)
        assert st.disp_kg == pytest.approx(target, rel=1e-3)


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
    # The vocabulary GREW on 2026-08-12 and it grew in the honest direction:
    # `energy.wh_per_nm_sigma` names its own basis, and evaluate() now serves
    # that string instead of re-typing "assumed" beside a sigma it did not
    # compute. "placeholder" is deliberately NOT in the accepted set here —
    # it is a legal EnergyReport state, but a badge wearing it means no input
    # sigma reached the propagation and that is a defect at THIS call site.
    from navalai.energy import (SIGMA_PLACEHOLDER, SIGMA_PROPAGATED,
                                SIGMA_PROPAGATED_LOWER_BOUND)
    for _q, (tier, sigma, basis) in ev.badges.items():
        assert tier == "L1" and sigma > 0
        assert basis in ("measured", "assumed", SIGMA_PROPAGATED,
                         SIGMA_PROPAGATED_LOWER_BOUND)
        assert basis != SIGMA_PLACEHOLDER
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


# ---------------------------------------------------------------------------
# MULTI-HULL WAVE INTERFERENCE — plate P4 (Gate 1)
# ---------------------------------------------------------------------------
#
# `michell_rw(..., separation=s)` puts two identical demihulls at y = +-s/2 and
# returns the wave resistance of the pair. It is a PURE ADDITION: no genome
# change, no `total_resistance` wiring, and `separation=None` must reproduce
# the monohull bit for bit. The section below is the three acceptance bars,
# plus the derivation check and the refusals.
#
# Every measurement here is on the Wigley demihull (L = 10 m, 121 x 25
# offsets, rho = 1000) — stated because docs/LESSONS.md defect class 6 is a
# number measured at a configuration the product never runs.

import math

_CAT_L = 10.0                       # Wigley demihull length [m]
_CAT_SEPS_OVER_L = np.arange(0.15, 1.5001, 0.005)   # the sweep, s / Lwl


@pytest.fixture(scope="module")
def cat_demihull():
    from benchmarks.wigley import wigley_offsets
    xs, zs, Y, B, T = wigley_offsets(_CAT_L, 121, 25)
    return xs, zs, Y, B, T


def test_michell_monohull_is_bit_identical_without_a_separation(cat_demihull):
    """BAR 1. `separation=None` is TODAY'S `michell_rw`, bit for bit.

    Not "close" — identical. Two halves, because either alone is weak:

    (a) the default call and the explicit `separation=None` call must produce
        the same 64 bits. This is what stops the monohull path from acquiring
        a stray `* 1.0` or a reordered sum when the catamaran factor is
        maintained.
    (b) the monohull path must still land on the CLOSED FORM. Bit-identity to
        oneself proves nothing if both sides moved together, and
        `benchmarks.wigley.rw_analytic` evaluates Michell's x and z integrals
        symbolically, touching none of our grids — see
        `test_wigley_matches_the_reference_curve_point_by_point`, which is the
        full anchor; this is the corner of it that guards the refactor.

    A frozen hex literal is deliberately NOT used as the bit-identity
    reference. Commit c7b7c4b measured `developable_pairing` landing on a
    different root on this Mac and on ubuntu-latest, and `np.exp`/`np.cos`
    are libm calls: a cross-platform bit-exact pin would assert a quantity
    that is not well defined. MEASURED instead, on this machine, against a
    `git archive HEAD` copy of the pre-change module over 3 hulls x 5 Froude
    numbers x 2 densities: 30 of 30 cases bit-identical, 0 mismatches.
    """
    import struct

    from benchmarks.wigley import (ANALYTIC_RW_N, ANALYTIC_TOL_PRODUCTION,
                                   rw_analytic, wigley_offsets)
    from navalai.geometry import G
    from navalai.resistance import michell_rw

    for L, nx, nz in ((10.0, 121, 25), (7.0, 161, 28), (12.5, 81, 17)):
        xs, zs, Y, _B, _T = wigley_offsets(L, nx, nz)
        for fn in (0.15, 0.20, 0.30, 0.40, 0.50):
            u = fn * math.sqrt(G * L)
            for rho in (1000.0, 1025.0):
                a = michell_rw(xs, zs, Y, u, rho)
                b = michell_rw(xs, zs, Y, u, rho, separation=None)
                assert struct.pack("<d", a) == struct.pack("<d", b), (
                    f"L {L} Fn {fn} rho {rho}: the monohull path is no longer "
                    f"reachable unchanged — {a!r} vs {b!r}")

    # (b) and it is still Michell's integral, not merely still itself.
    xs, zs, Y, _B, _T = wigley_offsets(10.0, 121, 25)
    for fn, _ in sorted(ANALYTIC_RW_N.items()):
        u = fn * math.sqrt(G * 10.0)
        assert michell_rw(xs, zs, Y, u) == pytest.approx(
            rw_analytic(fn), rel=ANALYTIC_TOL_PRODUCTION), (
            f"Fn {fn}: the monohull path drifted off the closed form")


def test_the_interference_factor_is_two_shifted_source_sheets(cat_demihull):
    """The DERIVATION, checked by an implementation that never writes cos^2.

    `catamaran_interference` ships the closed factor `4 cos^2(k_y s / 2)`,
    which is an algebraic identity away from what thin-ship theory actually
    says: the Kochin amplitude of a source sheet translated to y = y0 picks up
    e^{i k_y y0}, and a catamaran is TWO sheets at y = +-s/2. This test builds
    the amplitude that way — complex sum, then modulus squared — so a wrong
    transverse wavenumber or a factor of two in the half-separation cannot
    hide behind the identity.

    k_y = k0 sec^2(theta) sin(theta) is read off this module's own kernel: the
    longitudinal component is the `k0 sec(theta) x` phase and the magnitude is
    the `k0 sec^2(theta) z` depth decay, so the transverse component is
    k sin(theta) with k = k0 sec^2(theta).

    (Also recorded here because it is what makes the change safe to write: the
    lambda form of Michell, Int_1^inf (...) lam^2/sqrt(lam^2-1) dlam, is THIS
    integral under lam = sec(theta) — dlam = lam sqrt(lam^2-1) dtheta, so
    sec^3(theta) dtheta = lam^2/sqrt(lam^2-1) dlam, term for term.)
    """
    from navalai.geometry import G
    from navalai.resistance import (_theta_grid, catamaran_interference,
                                    michell_rw, n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull

    # The lambda/theta equivalence, VERIFIED rather than asserted: integrate
    # the same amplitude shape both ways. With A(lam) = lam^-3 the theta form
    # Int_0^{pi/2} A^2 sec^3 dtheta is Int cos^3 = 2/3 exactly, and the lambda
    # form is Int_1^inf A^2 lam^2/sqrt(lam^2-1) dlam over the same physics.
    th = np.linspace(0.0, 0.5 * math.pi, 200_001)[:-1]
    theta_form = float(np.trapezoid(np.cos(th) ** 3, th))
    # log-spaced in (lam - 1): the lambda integrand carries an integrable
    # (lam-1)^-1/2 singularity at lam = 1 that a uniform grid cannot resolve.
    lam = 1.0 + np.geomspace(1e-14, 1e4, 500_001)
    lam_form = float(np.trapezoid(lam**-6 * lam**2 / np.sqrt(lam**2 - 1.0), lam))
    assert theta_form == pytest.approx(2.0 / 3.0, rel=1e-9)
    assert lam_form == pytest.approx(theta_form, rel=1e-5), (
        f"the lambda form {lam_form:.8f} and the theta form {theta_form:.8f} "
        f"are not the same integral under lam = sec(theta); this module ships "
        f"the theta form and every result quoted from the lambda-form "
        f"literature rests on them being identical")

    for fn, sep in ((0.25, 2.5), (0.30, 4.45), (0.40, 9.0)):
        u = fn * math.sqrt(G * _CAT_L)
        k0 = G / u**2
        n_theta = n_theta_for_separation(_CAT_L, sep)
        thetas, sec = _theta_grid(n_theta)
        dydx = np.gradient(Y, xs, axis=0)
        # the reference: two source sheets summed as complex amplitudes
        ref = np.empty(n_theta)
        for i, (t, sc) in enumerate(zip(thetas, sec)):
            depth = np.exp(np.minimum(k0 * sc**2 * zs, 0.0))[None, :]
            fx = np.trapezoid(dydx * depth, zs, axis=1)
            amp = (np.trapezoid(fx * np.cos(k0 * sc * xs), xs)
                   + 1j * np.trapezoid(fx * np.sin(k0 * sc * xs), xs))
            ky = k0 * sc**2 * math.sin(t)
            both = amp * (np.exp(1j * ky * (+sep / 2.0))
                          + np.exp(1j * ky * (-sep / 2.0)))
            ref[i] = abs(both) ** 2 * sc**3
        expect = float(4.0 * 1000.0 * G**2 / (math.pi * u**2)
                       * np.trapezoid(ref, thetas))
        got = michell_rw(xs, zs, Y, u, 1000.0, separation=sep)
        assert got == pytest.approx(expect, rel=1e-12), (
            f"Fn {fn}, s {sep} m: the shipped factor {got:.8e} does not agree "
            f"with two explicitly shifted source sheets {expect:.8e}")
    # and the factor's own range and mean are the physics: [0, 4], mean 2
    thetas, _sec = _theta_grid(4000)
    f = catamaran_interference(1.1111, thetas, 40.0)
    assert f.min() < 1e-3 and f.max() > 3.999, (
        f"the interference factor never reaches its bounds: "
        f"[{f.min():.4f}, {f.max():.4f}] should span [0, 4]")


def test_catamaran_tends_to_twice_a_demihull_at_large_separation(cat_demihull):
    """BAR 2. R_w(cat) -> 2 R_w(demi) as s -> inf, with the residual EXPLAINED.

    The interference factor 4 cos^2(k_y s / 2) averages to 2 (NOT to 1 — that
    is the one correction this plate made to its own brief), so two demihulls
    far enough apart to stop seeing each other's waves cost twice one demihull.

    MEASURED over Fn 0.20-0.45 x s/Lwl 5, 10, 20 on a rule-compliant theta
    grid: the ratio is 0.995189 to 0.999620, i.e. the residual is -0.0380% to
    **-0.4811%** and is always NEGATIVE.

    THE RESIDUAL IS NOT QUADRATURE NOISE AND IS NOT HIDDEN BY THE TOLERANCE.
    `michell_rw`'s theta sweep starts at theta_0 = 0.5 pi * 0.998 * (1e-4)^0.7
    = 2.4848e-3 rad for EVERY n_theta, so the trapezoid omits [0, theta_0] in
    both cases — but at any practical separation phi(theta_0) = k0 s theta_0 is
    still well under pi, so the catamaran omits that sliver weighted by ~4
    while twice-the-demihull omits it weighted by 2. The predicted deficit is
    (4 - 2) vals(0) theta_0 / (2 Int vals dtheta):

        Fn     predicted    measured
        0.20    -0.4805%     -0.4811%  (s/Lwl = 5)
        0.30    -0.2540%     -0.2440%  (s/Lwl = 20)
        0.40    -0.3300%     -0.3229%  (s/Lwl = 20)

    So the bar is set AT the worst measured value (`CATAMARAN_ASYMPTOTIC_
    RESIDUAL` = 0.49%) rather than at a round number that would swallow it,
    and the residual is asserted to be one-signed — a tolerance that admits
    +0.49% would stop distinguishing this mechanism from a real error.
    """
    from navalai.geometry import G
    from navalai.resistance import (CATAMARAN_ASYMPTOTIC_RESIDUAL,
                                    CATAMARAN_INTERFERENCE_AT_INFINITY,
                                    michell_rw, n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull
    sep = 5.0 * _CAT_L                     # 50 m on a 10 m waterline
    n_theta = n_theta_for_separation(_CAT_L, sep)
    assert n_theta == 4400
    worst = 0.0
    for fn in (0.20, 0.30, 0.40):
        u = fn * math.sqrt(G * _CAT_L)
        demi = michell_rw(xs, zs, Y, u, 1000.0, n_theta=n_theta)
        cat = michell_rw(xs, zs, Y, u, 1000.0, n_theta=n_theta, separation=sep)
        ratio = cat / (CATAMARAN_INTERFERENCE_AT_INFINITY * demi)
        worst = max(worst, abs(ratio - 1.0))
        assert ratio == pytest.approx(1.0, abs=CATAMARAN_ASYMPTOTIC_RESIDUAL), (
            f"Fn {fn}, s/Lwl 5: R_w(cat)/(2 R_w(demi)) = {ratio:.6f}, "
            f"{100 * (ratio - 1):+.4f}% — outside the measured "
            f"{100 * CATAMARAN_ASYMPTOTIC_RESIDUAL:.2f}% residual")
        assert ratio < 1.0, (
            f"Fn {fn}: the asymptotic residual came out POSITIVE ({ratio:.6f}). "
            f"The omitted [0, theta_0] sliver can only make the catamaran LOW; "
            f"a high answer is a different mechanism and wants diagnosing, not "
            f"absorbing into this tolerance")
    # and the bar is not slack: the worst case must be within a factor of two
    # of it, or the tolerance has stopped measuring anything.
    assert worst > 0.5 * CATAMARAN_ASYMPTOTIC_RESIDUAL, (
        f"worst residual {100 * worst:.4f}% is far inside the "
        f"{100 * CATAMARAN_ASYMPTOTIC_RESIDUAL:.2f}% bar — re-measure the bar "
        f"downward rather than leaving a tolerance that cannot fail")


def test_catamaran_interference_is_real_and_signed(cat_demihull):
    """BAR 3. There are separations that HELP and separations that HURT.

    The number an optimiser will chase. MEASURED at Fn 0.30 on the Wigley
    demihull, sweeping s/Lwl from 0.150 to 1.500 in steps of 0.005 (271
    points, n_theta 1321), as R_w(cat) / (2 R_w(demi)):

        DESTRUCTIVE (best):   0.922342  at s/Lwl 0.4450  (s = 4.4500 m)
        CONSTRUCTIVE (worst): 1.472953  at s/Lwl 0.1500  (s = 1.5000 m)
        spread                0.550611  = 55.1% of twice a demihull
        84.9% of the swept separations are below 1.0

    The constructive maximum sits at the FLOOR of the sweep, and the floor is
    stated rather than treated as an interior optimum: at Fn 0.30 the closer
    the demihulls the worse it gets, down to the geometric limit where they
    touch. The destructive minimum at 0.4450 is interior and is a real
    stationary point.

    Bars are set with margin against `CATAMARAN_THETA_QUADRATURE_ERROR`
    (0.061%, measured) — the effect is three orders of magnitude larger than
    the numerics that could fake it, which is the point of asserting the SIZE
    and not merely the sign.
    """
    from navalai.geometry import G
    from navalai.resistance import (CATAMARAN_THETA_QUADRATURE_ERROR,
                                    michell_rw, michell_rw_separation_sweep,
                                    n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull
    seps = _CAT_SEPS_OVER_L * _CAT_L
    n_theta = n_theta_for_separation(_CAT_L, seps.max())
    u = 0.30 * math.sqrt(G * _CAT_L)
    demi = michell_rw(xs, zs, Y, u, 1000.0, n_theta=n_theta)
    ratio = michell_rw_separation_sweep(xs, zs, Y, u, seps, 1000.0,
                                        n_theta=n_theta) / (2.0 * demi)
    lo, hi = int(np.argmin(ratio)), int(np.argmax(ratio))

    assert ratio[lo] < 1.0 - 50 * CATAMARAN_THETA_QUADRATURE_ERROR, (
        f"no destructive interference anywhere in the sweep: best ratio "
        f"{ratio[lo]:.6f} at s/Lwl {seps[lo] / _CAT_L:.4f}")
    assert ratio[hi] > 1.0 + 50 * CATAMARAN_THETA_QUADRATURE_ERROR, (
        f"no constructive interference anywhere in the sweep: worst ratio "
        f"{ratio[hi]:.6f} at s/Lwl {seps[hi] / _CAT_L:.4f}")
    # the measured extrema, pinned as physics rather than as a sign test
    assert ratio[lo] == pytest.approx(0.922342, abs=2e-3), ratio[lo]
    assert ratio[hi] == pytest.approx(1.472953, abs=5e-3), ratio[hi]
    assert seps[lo] / _CAT_L == pytest.approx(0.4450, abs=0.02), seps[lo]
    assert seps[hi] / _CAT_L == pytest.approx(0.1500, abs=1e-9), (
        "the constructive maximum left the floor of the sweep — the range this "
        "test measures over has changed and the numbers above describe a "
        "different experiment")
    assert ratio[hi] - ratio[lo] == pytest.approx(0.550611, abs=5e-3)


def test_the_optimal_separation_moves_inward_with_froude_number(cat_demihull):
    """The naval-architecture result, and it is cheap here so it is recorded.

    Within one interference lobe the least-resistance separation moves INWARD,
    monotonically, as Froude number rises. MEASURED on the Wigley demihull
    over the same sweep as bar 3, restricted to s/Lwl <= 1.0 (a designer's
    range; the unrestricted minimum hops to the far field above Fn 0.365):

        Fn       best s/Lwl   R_w(cat) / 2 R_w(demi)
        0.2875     0.5800            0.981220
        0.3000     0.4450            0.922342
        0.3125     0.3600            0.797847
        0.3250     0.3050            0.619008
        0.3375     0.2700            0.488426   <- deepest, -51.2%
        0.3500     0.2400            0.576188
        0.3625     0.2200            0.855341

    A 2.64x contraction in optimal spacing across a 26% rise in speed: the
    optimum is NOT a fixed fraction of the waterline, so a hull-form parameter
    chosen at one design speed is wrong at another, and this is the reason
    separation has to be a searched dimension rather than a rule of thumb.

    ABOVE THE LOBE THERE IS NO FAVOURABLE SEPARATION AT ALL. At Fn 0.3750 the
    best interior value is 1.030151 at s/Lwl 0.9950 — every practical spacing
    is constructive and the only way down is out of interference range. That
    is asserted too, because an optimiser that always finds a favourable
    separation would be reporting the sweep's boundary as physics.
    """
    from navalai.geometry import G
    from navalai.resistance import (michell_rw, michell_rw_separation_sweep,
                                    n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull
    seps = _CAT_SEPS_OVER_L * _CAT_L
    n_theta = n_theta_for_separation(_CAT_L, seps.max())
    inner = seps / _CAT_L <= 1.0

    def best(fn):
        u = fn * math.sqrt(G * _CAT_L)
        demi = michell_rw(xs, zs, Y, u, 1000.0, n_theta=n_theta)
        r = (michell_rw_separation_sweep(xs, zs, Y, u, seps, 1000.0,
                                         n_theta=n_theta) / (2.0 * demi))[inner]
        i = int(np.argmin(r))
        return float(seps[inner][i] / _CAT_L), float(r[i])

    prev = None
    for fn in (0.2875, 0.3000, 0.3125, 0.3250, 0.3375, 0.3500, 0.3625):
        s_over_l, ratio = best(fn)
        assert ratio < 1.0, (
            f"Fn {fn}: no favourable separation inside s/Lwl <= 1 "
            f"(best {ratio:.6f}) — the lobe this test tracks has moved")
        if prev is not None:
            assert s_over_l < prev, (
                f"Fn {fn}: optimal s/Lwl {s_over_l:.4f} is not inside the "
                f"{prev:.4f} measured at the previous Froude number")
        prev = s_over_l
    assert prev == pytest.approx(0.2200, abs=0.02), prev
    # the deepest point of the lobe, as a magnitude
    assert best(0.3375)[1] == pytest.approx(0.488426, abs=5e-3)

    # and the lobe ENDS: above it nothing inside s/Lwl <= 1 helps.
    s_over_l, ratio = best(0.3750)
    assert ratio > 1.0, (
        f"Fn 0.3750 now has a favourable interior separation at s/Lwl "
        f"{s_over_l:.4f} (ratio {ratio:.6f}); MEASURED 1.030151 at 0.9950")


def test_a_separation_the_grid_or_the_geometry_cannot_carry_is_refused(
        cat_demihull):
    """Every guard, fed the VERBATIM input it exists to reject.

    docs/LESSONS.md defect class 1 is an unmeasurable value scored as a
    passing one, and class 3 is a guard never made to fire. The interference
    factor has three ways to produce a confident wrong number:

    1. AN UNRESOLVED THETA SWEEP. The interference phase is
       phi(theta) = k0 s sec^2(theta) sin(theta), so dphi/dtheta grows as
       sec^3 while `michell_rw`'s node density does not. MEASURED on this
       demihull against an n_theta = 60000 reference, worst |error| over 25
       separations per band:

           s/Lwl        n_theta 220    440      880
           0.1 - 1.0        0.62%     0.23%   0.089%
           1.0 - 2.0        1.21%     0.39%   0.148%

       1.2% that CHANGES SIGN with separation is exactly the shape of a
       spurious optimum, and bar 3's real effect is 55%, so this would not be
       caught by looking at the answer. The rule n_theta >= 880 max(1, s/Lwl)
       holds every band to 0.061% and is ENFORCED, not documented.
    2. INTERSECTING DEMIHULLS. Thin-ship theory is linear in the hull surface
       and integrates two overlapping centreplanes without complaint.
    3. A NON-POSITIVE OR NaN SEPARATION quietly read as a monohull, which
       would report a two-hull vessel as a one-hull one.
    """
    from navalai.geometry import G
    from navalai.resistance import (N_THETA_MONOHULL, michell_rw,
                                    michell_rw_separation_sweep,
                                    n_theta_for_separation)

    xs, zs, Y, B, _T = cat_demihull
    u = 0.30 * math.sqrt(G * _CAT_L)

    # 1. the shipped monohull sweep is NOT enough for a catamaran
    assert n_theta_for_separation(_CAT_L, 0.5 * _CAT_L) > N_THETA_MONOHULL
    with pytest.raises(ValueError, match="cannot resolve the interference"):
        michell_rw(xs, zs, Y, u, 1000.0, n_theta=N_THETA_MONOHULL,
                   separation=0.445 * _CAT_L)
    # one node below the rule fails, the rule itself passes
    need = n_theta_for_separation(_CAT_L, 2.0 * _CAT_L)
    assert need == 1760
    with pytest.raises(ValueError, match="cannot resolve the interference"):
        michell_rw(xs, zs, Y, u, 1000.0, n_theta=need - 1,
                   separation=2.0 * _CAT_L)
    assert michell_rw(xs, zs, Y, u, 1000.0, n_theta=need,
                      separation=2.0 * _CAT_L) > 0.0
    # a sweep pins ONE grid, sized by its LARGEST member, so no point of it is
    # compared against another point's quadrature error
    with pytest.raises(ValueError, match="cannot resolve the interference"):
        michell_rw_separation_sweep(xs, zs, Y, u, np.array([2.0, 20.0]),
                                    1000.0, n_theta=880)

    # 2. demihulls that intersect. The beam that matters is the one ON THE
    #    GRID, 2*max(Y) — `wigley_offsets` stops just below z = 0, so the
    #    gridded beam is 2.6e-6 short of the analytic B and using B here would
    #    be asserting against a hull the integral never sees.
    beam = 2.0 * float(Y.max())
    assert beam < B and beam == pytest.approx(B, rel=1e-5)
    for bad in (beam, 0.999 * beam, 0.5 * beam):
        with pytest.raises(ValueError, match="INTERSECT"):
            michell_rw(xs, zs, Y, u, 1000.0, separation=bad)
    assert michell_rw(xs, zs, Y, u, 1000.0, separation=1.001 * beam) > 0.0

    # 3. a separation that is not a length
    # (`None` is NOT in this list: None is the monohull, and bar 1 pins it.)
    for bad in (0.0, -3.0, float("nan"), float("inf"), "3", [4.0]):
        with pytest.raises(ValueError, match="positive finite length"):
            michell_rw(xs, zs, Y, u, 1000.0, separation=bad)
    # ... and the refusal happens BEFORE any integration, so a NaN never
    # reaches the theta-grid sizing that would raise a less informative error
    with pytest.raises(ValueError, match="positive finite length"):
        michell_rw(xs, zs, Y, 0.0, 1000.0, separation=float("nan"))


def test_the_free_wave_spectrum_is_the_integrand_of_the_resistance(
        cat_demihull):
    """`free_wave_spectrum` must BE `michell_rw`'s integrand, not a copy of it.

    A number declared twice is this codebase's recurring defect, and a second
    path to the wave resistance is the most expensive shape it takes. So the
    bar is not "close": integrating the spectrum over theta must reproduce
    `michell_rw` to within the trapezoid's own reassociation, monohull and
    catamaran alike.

    The spectrum is exposed because it is the honest half of the wet-deck
    question: any calculation of the wave elevation between two demihulls has
    to start here, and this is the piece the module can supply exactly.
    """
    from navalai.geometry import G
    from navalai.resistance import (free_wave_spectrum, michell_rw,
                                    n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull
    for fn in (0.20, 0.30, 0.45):
        u = fn * math.sqrt(G * _CAT_L)
        th, spec = free_wave_spectrum(xs, zs, Y, u, 1000.0)
        assert float(np.trapezoid(spec, th)) == pytest.approx(
            michell_rw(xs, zs, Y, u, 1000.0), rel=1e-12)
        sep = 0.445 * _CAT_L
        n_theta = n_theta_for_separation(_CAT_L, sep)
        th, spec = free_wave_spectrum(xs, zs, Y, u, 1000.0, n_theta=n_theta,
                                      separation=sep)
        assert float(np.trapezoid(spec, th)) == pytest.approx(
            michell_rw(xs, zs, Y, u, 1000.0, n_theta=n_theta, separation=sep),
            rel=1e-12)
    # the spectrum is an energy density: non-negative everywhere, and the
    # catamaran factor can only redistribute it between 0 and 4x
    th, mono = free_wave_spectrum(xs, zs, Y, 2.97, 1000.0, n_theta=1760)
    th, cat = free_wave_spectrum(xs, zs, Y, 2.97, 1000.0, n_theta=1760,
                                 separation=2.0 * _CAT_L)
    assert (mono >= 0.0).all() and (cat >= 0.0).all()
    ratio = cat[mono > 1e-12] / mono[mono > 1e-12]
    assert ratio.min() >= -1e-9 and ratio.max() <= 4.0 + 1e-9, (
        f"the interference factor left [0, 4]: [{ratio.min():.6f}, "
        f"{ratio.max():.6f}]")
    # and a speed below the cut-off returns a grid with a ZERO spectrum, not a
    # short array a caller would have to special-case
    th0, spec0 = free_wave_spectrum(xs, zs, Y, 0.01, 1000.0)
    assert len(th0) == len(spec0) and not spec0.any()


def test_wet_deck_clearance_is_a_constraint_row_with_a_number_in_it():
    """The wet-deck clearance term, and the thing this module REFUSES.

    An optimiser handed demihull separation as a free variable and no clearance
    term will pick a spacing for wave interference and say nothing about the
    bridge deck that spacing implies — and wet-deck slamming, not bow slamming,
    is what typically destroys catamarans.

    IT WAS PROPOSED THAT THE BOW WAVE AMPLITUDE COME OUT OF THE KOCHIN
    MACHINERY. It cannot, and the refusal is the finding:

      - `michell_rw`'s integrand is the FAR-FIELD free-wave spectrum. Michell
        keeps only the radiating disturbance and discards the local
        non-radiating near field, which is the part that makes the stem wave.
      - the far-field elevation is not one amplitude: the Kelvin pattern decays
        as R^-1/2, so "the amplitude" depends on where you stand.
      - |I(theta)| has dimensions of AREA. Supplying a constant to make it a
        height would be inventing the answer.

    WHAT IS SHIPPED INSTEAD IS EXACT WHERE IT APPLIES: at a stagnation point
    the whole dynamic head converts to elevation, so zeta_bow = U^2/(2g) =
    Fn^2 Lwl / 2, an upper bound for any hull with a finite entrance angle and
    a length in metres at a stated speed. On a 10 m waterline that is 0.450 m
    at Fn 0.30, 0.613 m at Fn 0.35 and 0.800 m at Fn 0.40 — the number a
    genome-wirer needs, rather than an intention.

    The row is `bow_wave_rise(speed) - clearance_m`, metres, POSITIVE WHEN
    VIOLATED, which is the sign and the units `evaluate`'s `"freeboard"` row
    already uses, so it appends to `CONSTRAINT_NAMES` without a convention
    change.
    """
    from navalai.geometry import G
    from navalai.resistance import bow_wave_rise, wet_deck_clearance_g

    # the closed form, and its Froude-scaled twin — two ways to the same metre
    for fn in (0.30, 0.35, 0.40):
        u = fn * math.sqrt(G * _CAT_L)
        assert bow_wave_rise(u) == pytest.approx(fn**2 * _CAT_L / 2.0, rel=1e-12)
    assert bow_wave_rise(0.30 * math.sqrt(G * _CAT_L)) == pytest.approx(0.450,
                                                                       abs=5e-4)
    assert bow_wave_rise(0.35 * math.sqrt(G * _CAT_L)) == pytest.approx(0.6125,
                                                                       abs=5e-4)
    assert bow_wave_rise(0.40 * math.sqrt(G * _CAT_L)) == pytest.approx(0.800,
                                                                       abs=5e-4)
    # it IS the stagnation head: 0.5 rho U^2 expressed as a head of water
    rho, u = 1025.0, 4.0
    assert bow_wave_rise(u) == pytest.approx(0.5 * rho * u**2 / (rho * G),
                                             rel=1e-12)
    assert bow_wave_rise(0.0) == 0.0
    assert bow_wave_rise(6.0) > bow_wave_rise(3.0)

    # the constraint row: sign, units, and the boundary
    u = 0.35 * math.sqrt(G * _CAT_L)
    rise = bow_wave_rise(u)
    assert wet_deck_clearance_g(rise + 0.10, u) == pytest.approx(-0.10, abs=1e-9)
    assert wet_deck_clearance_g(rise - 0.10, u) == pytest.approx(+0.10, abs=1e-9)
    assert wet_deck_clearance_g(rise, u) == pytest.approx(0.0, abs=1e-12)
    assert wet_deck_clearance_g(0.30, u) > 0.0, (
        "a 0.30 m wet deck at Fn 0.35 on a 10 m boat must be a VIOLATION: the "
        "ship's own bow wave stands 0.613 m above the still waterline")

    # an unmeasured clearance is refused, never scored as satisfied
    for bad in (float("nan"), float("inf"), "0.5", None):
        with pytest.raises(ValueError, match="finite height"):
            wet_deck_clearance_g(bad, u)
    for bad in (float("nan"), -1.0, "3"):
        with pytest.raises(ValueError, match="non-negative finite"):
            bow_wave_rise(bad)


def test_destructive_interference_also_shrinks_the_wet_deck_wave_field(
        cat_demihull):
    """The coupling between the two, MEASURED rather than assumed.

    The worry that motivated the clearance term was that an optimiser chasing
    destructive wave interference would drive the wet deck into trouble. On the
    CALM-WATER term the two are ALIGNED: the interference ratio is a ratio of
    radiated wave ENERGY, so a spacing that cuts R_w cuts the wave field
    between the hulls by the same factor.

    MEASURED at Fn 0.30 on the Wigley demihull: the destructive optimum at
    s/Lwl 0.4450 radiates 0.9223 of two independent demihulls; the
    constructive worst case at s/Lwl 0.1500 radiates 1.4730. The wet deck sees
    the largest wave field at exactly the spacings the resistance objective
    already rejects, so the two constraints do not pull against each other.

    THIS IS NOT A SLAMMING RESULT. It says the ship's own steady wave field
    scales with its own radiated energy. Wet-deck slamming in a seaway is
    driven by relative motion against the INCIDENT wave, which is
    `navalai/seakeeping.py`'s question; nothing here bounds it.
    """
    from navalai.geometry import G
    from navalai.resistance import (free_wave_spectrum,
                                    n_theta_for_separation)

    xs, zs, Y, _B, _T = cat_demihull
    u = 0.30 * math.sqrt(G * _CAT_L)
    n_theta = n_theta_for_separation(_CAT_L, 1.5 * _CAT_L)
    _th, mono = free_wave_spectrum(xs, zs, Y, u, 1000.0, n_theta=n_theta)
    energy = {}
    for tag, s_over_l in (("destructive", 0.4450), ("constructive", 0.1500)):
        _th, spec = free_wave_spectrum(xs, zs, Y, u, 1000.0, n_theta=n_theta,
                                       separation=s_over_l * _CAT_L)
        energy[tag] = float(np.trapezoid(spec, _th)
                            / (2.0 * np.trapezoid(mono, _th)))
    assert energy["destructive"] == pytest.approx(0.9223, abs=2e-3)
    assert energy["constructive"] == pytest.approx(1.4730, abs=5e-3)
    assert energy["destructive"] < 1.0 < energy["constructive"], (
        f"the two spacings no longer straddle the no-interference case: "
        f"{energy}")
