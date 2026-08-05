"""Gate 1: Wigley Michell anchor, hydrostatics physics, full L1 eval < 50 ms."""

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
    for _q, (tier, sigma) in ev.badges.items():
        assert tier == "L1" and sigma > 0    # honesty: every number has a band
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
    from navalai.energy import EnergySpec, weight_budget, weight_items
    from navalai.geometry import Hull
    from navalai.weights import aggregate
    from tests.test_phase0 import mid_params

    h = Hull(mid_params())
    lwl, depth, t_design = float(h.x[-1]), 1.55, -float(h.z_keel.min())
    surf, deck, spec = h.wetted_surface(0.0) * 1.6, h.deck_area(), EnergySpec()

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
