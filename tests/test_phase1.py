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
