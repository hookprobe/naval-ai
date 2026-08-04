"""Stage D gate: JONSWAP integrates right, RAO physics limits hold, response
spectra sane; inertia cross-checked in MuJoCo; CFD post-processor exact on
synthetic data."""

import numpy as np
import pytest

from navalai.cfd.post import gci, mean_resistance, parse_forces
from navalai.dynamics import (inertia, lifting, mooring,
                              pendulum_period_analytic)
from navalai.energy import EnergySpec, weight_budget
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.waves import (BLACK_SEA_COASTAL, DANUBE_WAKE, SeaState,
                           heave_response, jonswap)
from tests.test_phase0 import mid_params


# ---------------- waves ----------------

def test_jonswap_zeroth_moment_matches_hs():
    w = np.linspace(0.05, 6.0, 4000)
    for sea in (BLACK_SEA_COASTAL, DANUBE_WAKE):
        s = jonswap(w, sea)
        m0 = np.trapezoid(s, w)
        assert m0 == pytest.approx(sea.hs**2 / 16.0, rel=0.02)


def test_jonswap_peak_at_tp():
    w = np.linspace(0.05, 6.0, 4000)
    s = jonswap(w, BLACK_SEA_COASTAL)
    assert w[np.argmax(s)] == pytest.approx(BLACK_SEA_COASTAL.wp, rel=0.05)


def test_black_sea_steeper_than_swell():
    """Fetch-limited gamma=3.3 concentrates energy near the peak vs gamma=1."""
    w = np.linspace(0.05, 6.0, 4000)
    js = jonswap(w, BLACK_SEA_COASTAL)
    pm = jonswap(w, SeaState("pm-like", 2.0, 5.5, 1.0))
    assert js.max() > 1.15 * pm.max()


# ---------------- RAO + response (Capytaine) ----------------

@pytest.fixture(scope="module")
def rao_curve():
    pytest.importorskip("capytaine")
    from navalai.seakeeping import heave_rao
    ev = evaluate(mid_params(), MissionSpec())
    hull = Hull(mid_params())
    omegas = np.linspace(0.4, 3.2, 8)
    rao = heave_rao(hull, omegas, ev.hydro.disp_kg, ev.hydro.awp, nx=24, nz=6)
    return omegas, rao


def test_rao_long_wave_limit(rao_curve):
    omegas, rao = rao_curve
    assert rao[0] == pytest.approx(1.0, abs=0.15)   # boat follows long waves


def test_rao_short_wave_attenuation(rao_curve):
    omegas, rao = rao_curve
    assert rao[-1] < 0.5 * rao[0]                    # chop is filtered


def test_heave_response_black_sea_vs_danube(rao_curve):
    omegas, rao = rao_curve
    rb = heave_response(omegas, rao, BLACK_SEA_COASTAL)
    rd = heave_response(omegas, rao, DANUBE_WAKE)
    assert rb.hs_heave > rd.hs_heave                 # worse seas, more motion
    assert rb.hs_heave < 1.5 * BLACK_SEA_COASTAL.hs  # no free energy


# ---------------- dynamics ----------------

@pytest.fixture(scope="module")
def wb():
    h = Hull(mid_params())
    return h, weight_budget(10.0, 1.55, h.wetted_surface(0) * 1.6,
                            h.deck_area(), EnergySpec())


def test_inertia_sane(wb):
    h, budget = wb
    rep = inertia(h, budget)
    assert rep.iyy > rep.ixx                 # pitch inertia > roll for a slender hull
    assert 0.30 < rep.kxx < 0.55             # roll gyradius fractions, naval practice
    assert 0.20 < rep.kyy < 0.40


def test_inertia_mujoco_crosscheck(wb):
    mujoco = pytest.importorskip("mujoco")
    from navalai.dynamics import pendulum_period_mujoco
    h, budget = wb
    rep = inertia(h, budget)
    d = 2.0
    t_analytic = pendulum_period_analytic(rep.mass, rep.iyy, d)
    t_mj = pendulum_period_mujoco(rep.mass, rep.iyy, d)
    assert t_mj == pytest.approx(t_analytic, rel=0.02), (
        f"mujoco {t_mj:.3f}s vs analytic {t_analytic:.3f}s")


def test_mooring_and_lifting(wb):
    h, budget = wb
    mo = mooring(h)
    assert mo.wind_force_n > 0 and mo.line_tension_n > mo.wind_force_n * 0.9
    li = lifting(budget.total_kg, 30.0)
    # 30 deg slings carry more than W/2 each — the classic rigging trap
    assert li.tension_per_sling_n > 0.5 * li.weight_n
    assert li.required_wll_kg > budget.total_kg


# ---------------- CFD post ----------------

def test_forces_parser_and_mean(tmp_path):
    f = tmp_path / "force.dat"
    rows = ["# Time (px py pz) (vx vy vz)"]
    rng = np.random.default_rng(1)
    for i in range(200):
        t = i * 0.1
        drag = -300.0 + (50.0 if t < 10 else 0.0) + rng.normal(0, 2)
        rows.append(f"{t:.2f} ({drag * 0.8:.3f} 0 0) ({drag * 0.2:.3f} 0 0)")
    f.write_text("\n".join(rows))
    t, fx = parse_forces(f)
    assert len(t) == 200
    mean, std = mean_resistance(f, tail_frac=0.3)
    assert mean == pytest.approx(-300.0, abs=2.0)    # settled tail only
    assert std < 5.0


def test_gci_recovers_known_convergence():
    """Synthetic 2nd-order convergence: f(h) = f0 + c h^2, r = sqrt(2)."""
    f0, c = 100.0, 8.0
    h = np.array([2.0, 2.0 / np.sqrt(2), 1.0])
    f3, f2, f1 = f0 + c * h**2
    rep = gci(f3, f2, f1, refinement=np.sqrt(2))
    assert rep.p_observed == pytest.approx(2.0, abs=0.05)
    assert rep.f_extrapolated == pytest.approx(f0, rel=1e-3)
    assert rep.gci_fine_pct < 15.0
    assert "GCI" in rep.method                       # method named, per V&V finding


def test_gci_oscillatory_falls_back_conservative():
    rep = gci(100.0, 104.0, 101.0)
    assert np.isnan(rep.p_observed)
    assert rep.gci_fine_pct > 0 and "oscillatory" in rep.method


def test_restarted_run_merges_its_force_segments(tmp_path):
    """The Mac has no working cooling and lost a triplet to 'Thermal Emergency
    Sleep' mid-run. Resuming writes a SECOND postProcessing/forces/<t>/ dir, so
    reading only `0/` would analyse the pre-crash fragment and report it as the
    whole run -- a silently wrong settled average, which is the exact failure
    mode the honesty rules exist to prevent.
    """
    from navalai.cfd.post import forces_path

    root = tmp_path / "case" / "postProcessing" / "forces"
    (root / "0").mkdir(parents=True)
    (root / "12").mkdir()
    # pre-crash: t=0..12 drifting; post-resume: t=12..25 settled at -300
    (root / "0" / "force.dat").write_text("\n".join(
        f"{t/10:.2f} ({-1000 + t*5:.3f} 0 0) (0 0 0)" for t in range(0, 121)))
    (root / "12" / "force.dat").write_text("\n".join(
        f"{t/10:.2f} (-300.0 0 0) (0 0 0)" for t in range(120, 251)))

    merged = forces_path(tmp_path / "case")
    t, fx = parse_forces(merged)
    assert t[0] == pytest.approx(0.0) and t[-1] == pytest.approx(25.0)
    assert len(t) == 251, "segments must join without gaps or duplicates"
    # the resumed segment wins on the overlapping sample at t=12.0
    assert fx[t == 12.0][0] == pytest.approx(-300.0)
    # and the settled tail is the post-resume value, not the pre-crash drift
    mean, _ = mean_resistance(merged, tail_frac=0.3)
    assert mean == pytest.approx(-300.0, abs=1e-6)


def _box_stl(path, zlo=-1.0, zhi=1.0):
    """Unit-square-section box spanning z in [zlo, zhi], as an ascii STL."""
    x0 = y0 = 0.0
    x1 = y1 = 1.0
    c = [(x0, y0, zlo), (x1, y0, zlo), (x1, y1, zlo), (x0, y1, zlo),
         (x0, y0, zhi), (x1, y0, zhi), (x1, y1, zhi), (x0, y1, zhi)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)]
    lines = ["solid box"]
    for a, b, cc, d in quads:
        for tri in ((a, b, cc), (a, cc, d)):
            lines.append(" facet normal 0 0 0")
            lines.append("  outer loop")
            for i in tri:
                lines.append("   vertex %.6e %.6e %.6e" % c[i])
            lines.append("  endloop")
            lines.append(" endfacet")
    lines.append("endsolid box")
    path.write_text("\n".join(lines))
    return path


def test_cap_planar_holes_closes_external_geometry(tmp_path):
    """Gate 2M: the Tokyo-2015 KCS IGES is a trimmed-surface HALF body, open at
    the deck — 450 open edges as delivered. CFD needs a closed manifold or the
    mesher floods the interior (the own-hull STL taught this at 198 open
    edges). Here: a box missing its lid must come back closed, with the
    enclosed volume exactly right and windings outward.
    """
    from navalai.cfd.case import stl_watertight_report
    from navalai.cfd.post import cap_planar_holes

    from navalai.cfd.post import _read_stl_tris, _write_stl

    # unit box spanning z in [-1, 1], lid deliberately removed
    src = _box_stl(tmp_path / "open.stl")
    tris = []
    for t in _read_stl_tris(src):
        if all(abs(p[2] - 1.0) < 1e-9 for p in t):
            continue                    # this is the lid
        tris.append(t)
    _write_stl(tris, tmp_path / "open.stl")
    assert not stl_watertight_report(tmp_path / "open.stl")["watertight"]

    rep = cap_planar_holes(tmp_path / "open.stl", tmp_path / "closed.stl")
    assert rep["loops_capped"] == 1, rep

    closed = stl_watertight_report(tmp_path / "closed.stl")
    assert closed["watertight"], closed
    assert closed["open_or_nonmanifold_edges"] == 0
    # 1x1 base, 2 tall -> volume 2, and POSITIVE means outward windings
    assert closed["signed_volume"] == pytest.approx(2.0, rel=1e-6)


def test_wetted_area_clips_at_the_waterline(tmp_path):
    """Gate 2M needs C_t, so it needs the submerged area the CFD actually saw.

    Exact answer for a 1x1 box spanning z in [-1, 1] clipped at z=0: the
    bottom face (1) plus four side faces of height 1 (4) = 5 m^2; the deck and
    the topsides above the waterline must NOT be counted.
    """
    from navalai.cfd.post import resistance_coefficient, stl_wetted_area
    stl = _box_stl(tmp_path / "box.stl")
    assert stl_wetted_area(stl, 0.0) == pytest.approx(5.0, rel=1e-6)
    assert stl_wetted_area(stl, -1.0) == pytest.approx(1.0, rel=1e-6)  # keel only
    # whole box: 2 end caps (1 each) + 4 sides of 1 x 2 = 10
    assert stl_wetted_area(stl, 1.0) == pytest.approx(10.0, rel=1e-6)

    # C_t = R_t / (0.5 rho S U^2)
    ct = resistance_coefficient(1000.0, 5.0, 2.0, rho=1000.0)
    assert ct == pytest.approx(1000.0 / (0.5 * 1000.0 * 5.0 * 4.0), rel=1e-9)
    with pytest.raises(ValueError):
        resistance_coefficient(100.0, 0.0, 2.0)
