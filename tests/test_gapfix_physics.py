"""Gate 1P — the L1 physics core says what it actually computed.

This suite is the fence around the gap-register rows whose defect was NOT a
wrong formula but a QUIET one: a number the model did not produce (a clamp), a
grid nothing was converged on, a state assembled from two different waterlines,
a spectrum evaluated in the wrong frame, a sigma that was a fraction of its own
value. Every test below names the register row and the MEASURED number that was
wrong, and every guard is tested twice — once where it must FIRE on realistic
input, once where the metric behind it is absent or garbled and it must still
refuse rather than fall back to a comfortable default.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai import grammar, resistance
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.hydrostatics import solve_to_displacement
from navalai.mission import MissionSpec
from navalai.resistance import (CONVERGED_GRID, GRID_CONVERGED_TO,
                                PRODUCTION_GRID, form_factor, nu_water,
                                total_resistance)
from tests.test_phase0 import mid_params


@pytest.fixture(scope="module")
def ref():
    """The reference hull, floated to the default mission displacement."""
    m = MissionSpec()
    ev = evaluate(mid_params(), m)
    assert ev.hydro is not None
    return Hull(mid_params()), m, ev


# --------------------------------------------------------------- gap E7 ---
# "The form factor rides its clamp on 30.8% of the design space (raw k 0.470
# -> returned 0.4500) and is fed DESIGN beam and draft while cb comes from the
# FLOATED state (0.55 m passed against a floated 0.3737 m)."

def test_the_form_factor_clamp_is_reported_and_widens_the_band():
    """MEASURED 2026-08-07 over 400 L0-feasible grammar hulls floated to the
    6 t mission displacement, with the state made consistent: **30.1%** return
    a raw k outside [0, 0.45] and are handed 0.4500, max raw k **2.31**. The
    old code returned that 0.4500 as a bare float with the same flat 10%
    friction band as a hull sitting mid-range, so a quarter of the design space
    reported a number the estimator never produced and said nothing about it.
    """
    # A beamy, full hull: L/B 3.3, B/T 5.0, cb 0.6 -> raw k well over the bar.
    ff = form_factor(cb=0.60, lwl=10.0, beam=3.0, t=0.60)
    assert ff.k_raw > resistance.FORM_FACTOR_BAND[1], ff
    assert ff.clamped and ff.k == resistance.FORM_FACTOR_BAND[1]
    # The distance to the raw value is a MEASURED lower bound on the error,
    # and it must beat the declared band rather than be averaged with it.
    assert ff.sigma_k == pytest.approx(ff.k_raw - ff.k)
    assert ff.sigma_k > resistance.FORM_FACTOR_SIGMA_DECLARED
    assert not ff.in_support
    assert any("clamp" in v for v in ff.envelope_violations)

    # And an in-support hull is NOT flagged, or the flag would mean nothing.
    ok = form_factor(cb=0.55, lwl=10.0, beam=1.5, t=0.60)
    assert not ok.clamped and ok.sigma_k == resistance.FORM_FACTOR_SIGMA_DECLARED


def test_the_form_factor_refuses_a_state_it_cannot_evaluate():
    """The other half of the guard: a metric that is ABSENT or GARBLED must be
    fatal, never a passing default. With t = 0 the estimator's sqrt(B/T) term
    goes to infinity and k collapses to -0.095, which the old `np.clip` turned
    into a serene **0.0** — the most optimistic form factor available, handed
    back for a hull with no draft at all. `${VAR:-0}` scoring an unreadable
    metric as perfect has already cost this project a run.
    """
    for bad in (dict(cb=0.5, lwl=10.0, beam=3.0, t=0.0),
                dict(cb=0.5, lwl=10.0, beam=0.0, t=0.5),
                dict(cb=float("nan"), lwl=10.0, beam=3.0, t=0.5),
                dict(cb=0.5, lwl=float("inf"), beam=3.0, t=0.5),
                dict(cb=0.5, lwl=-10.0, beam=3.0, t=0.5)):
        with pytest.raises(ValueError, match="form factor"):
            form_factor(**bad)


def test_the_form_factor_is_fed_one_waterline(ref):
    """cb from the floated state and B, T from the design parameters is not a
    boat. MEASURED on the reference hull: design B 3.200 m / T 0.550 m against
    a floated 3.252 m / 0.3737 m — a **47%** error on the draft, entering as
    sqrt(B/T), which took k from a genuine 0.382 up onto the 0.45 clamp.
    """
    hull, _m, ev = ref
    hs = ev.hydro
    lwl = float(hull.x[-1])
    consistent = form_factor(hs.cb, lwl, hs.b_wl_max, hs.draft)
    assert ev.resistance.form.k == pytest.approx(consistent.k, rel=1e-12)

    # The defect, reproduced: the mixed state gives a DIFFERENT answer, so this
    # test would have failed before the fix rather than passing by luck.
    mixed = form_factor(hs.cb, lwl, 2.0 * float(hull.y_chine.max()),
                        -float(hull.z_keel.min()))
    assert abs(mixed.k - consistent.k) > 0.05, (
        f"design state {mixed.k:.4f} vs floated {consistent.k:.4f} — if these "
        f"ever agree, this test has stopped measuring anything")


# --------------------------------------------------------------- gap E8 ---
# "Michell is not grid-converged at production defaults: 425.8 N shipped vs
# 456.0 N converged. The Wigley convergence test uses its own finer grid and
# never exercises the shipped one."

def test_michell_ships_the_grid_it_was_converged_on(ref):
    """RE-MEASURED 2026-08-07 on the reference hull at its 5 kn cruise:

        (n_stations x nz)   41x14 = 425.8 N   <- what shipped
                           161x28 = 455.3 N   <- production now
                           321x65 = 457.2 N   <- converged

    i.e. the shipped default was **-6.9%** on wave resistance, and the STATION
    axis carried -6.2% of it while the z-axis carried -1.3%. That matters:
    a convergence study refining z alone — which is the one this module's
    docstring pointed at — would have called the integral converged.
    """
    hull, m, ev = ref
    hs = ev.hydro
    kw = dict(rho=1000.0, wl=ev.wl, beam_wl=hs.b_wl_max, draft=hs.draft)
    u = m.cruise_speed_ms()

    prod = total_resistance(hull, u, hs.wetted, hs.cb, **kw)
    assert prod.grid["n_stations"] == PRODUCTION_GRID["n_stations"]
    assert prod.grid["nz"] == PRODUCTION_GRID["nz"]

    conv = total_resistance(hull, u, hs.wetted, hs.cb,
                            n_stations=CONVERGED_GRID["n_stations"],
                            nz=CONVERGED_GRID["nz"], **kw)
    rel = abs(prod.rw - conv.rw) / conv.rw
    assert rel < GRID_CONVERGED_TO, (
        f"production grid is {100 * rel:.2f}% from converged, bar "
        f"{100 * GRID_CONVERGED_TO:.2f}%")

    # The bar has to be able to fail, so assert the OLD default misses it.
    old = total_resistance(hull, u, hs.wetted, hs.cb, n_stations=41, nz=14,
                           **kw)
    assert abs(old.rw - conv.rw) / conv.rw > GRID_CONVERGED_TO


def test_a_hull_carrying_the_wrong_station_count_is_regridded(ref):
    """The production grid is a property of the INTEGRAL, not of whatever
    station count the caller's Hull happened to be built with — the geometry
    default is 41 and hydrostatics is happy there. Two hulls that differ only
    in `n_stations` must give the same wave resistance.
    """
    _hull, m, ev = ref
    hs = ev.hydro
    kw = dict(rho=1000.0, wl=ev.wl, beam_wl=hs.b_wl_max, draft=hs.draft)
    a = total_resistance(Hull(mid_params(), n_stations=41),
                         m.cruise_speed_ms(), hs.wetted, hs.cb, **kw)
    b = total_resistance(Hull(mid_params(), n_stations=61),
                         m.cruise_speed_ms(), hs.wetted, hs.cb, **kw)
    assert a.rw == pytest.approx(b.rw, rel=1e-12)


# -------------------------------------------------------- gap E17 (part) ---
# "NU_WATER is a fresh-water constant never re-derived from rho."

def test_viscosity_follows_the_water_it_is_asked_about():
    """`total_resistance(..., rho=1025.0)` is a supported call and
    `geometry.py` advertises it ("pass 1025 for salt"), but nu stayed at the
    fresh-water 1.14e-6, so Re came out **4.2%** high and C_F 0.51% low for
    every salt-water run. The salt anchor is IMPORTED from holtrop rather than
    retyped: one physical constant, one home.
    """
    from navalai.holtrop import NU_SEA_15C

    assert nu_water(1000.0) == resistance.NU_FRESH_15C
    assert nu_water(1025.0) == NU_SEA_15C
    assert nu_water(1000.0) < nu_water(1012.5) < nu_water(1025.0)
    # Clamped rather than extrapolated: a two-point fit run out to brine or to
    # hot fresh water would invent a number the ITTC table does not carry.
    assert nu_water(800.0) == nu_water(1000.0)
    assert nu_water(1300.0) == nu_water(1025.0)

    cf_fresh = resistance.ittc57_cf(2.5, 10.0, rho=1000.0)
    cf_salt = resistance.ittc57_cf(2.5, 10.0, rho=1025.0)
    assert cf_salt > cf_fresh          # more viscous -> lower Re -> higher Cf
    assert abs(cf_salt / cf_fresh - 1.0) > 1e-3


# ------------------------------------------------------- gaps F2 and F3 ---
# "Every solver is a bare cpt.BEMSolver(); 2.3.1 defaults to method='indirect'
# — the code runs the exact trap the plan names." / "The Green-function grid is
# correct only because the library defaults to it."

def test_the_direct_bie_is_chosen_and_it_is_the_better_one():
    """MEASURED 2026-08-07 against Hulme's (1982) analytic hemisphere limit,
    mu33/(2/3 pi rho a^3) -> 0.8310, at the resolution Gate 2 actually runs
    (n_theta 20, n_phi 40, omega 0.15):

        method='indirect'   0.85630   +3.05%   <- what shipped
        method='direct'     0.83479   +0.46%

    Same mesh, same frequency: the BIE the plan asks for is **6.6x** closer to
    the analytic answer on this project's own Gate 2 anchor, and Gate 2's 6%
    tolerance is why nothing noticed. This test asserts the ORDERING, not the
    numbers, so a capytaine release that improves both still passes — but a
    silent return to the indirect default fails it.
    """
    from navalai import seakeeping

    assert seakeeping.BIE_METHOD == "direct"
    direct = seakeeping.hemisphere_added_mass_lowfreq(
        n_theta=20, n_phi=40, omega=0.15, method="direct")
    indirect = seakeeping.hemisphere_added_mass_lowfreq(
        n_theta=20, n_phi=40, omega=0.15, method="indirect")
    assert abs(direct - 0.8310) < abs(indirect - 0.8310), (
        f"direct {direct:.5f} vs indirect {indirect:.5f} against 0.8310")
    # And the shipped default is the good one, not merely available.
    shipped = seakeeping.hemisphere_added_mass_lowfreq(
        n_theta=20, n_phi=40, omega=0.15)
    assert shipped == pytest.approx(direct, rel=1e-12)


def test_the_green_function_grid_is_pinned_not_inherited():
    """A library default is not a decision. The 676x372 tabulation the plan
    names is what capytaine 2.3.1 happens to choose; a downgrade in a later
    release would re-open the trap with nothing to notice it. The solver is
    built with the grid stated, and this test reads it back off the object.
    """
    from navalai import seakeeping

    assert seakeeping.TABULATION == {"tabulation_nr": 676,
                                     "tabulation_nz": 372}
    s = seakeeping.solver()
    got = s.green_function.exportable_settings
    assert got["tabulation_nr"] == 676 and got["tabulation_nz"] == 372, (
        f"solver built on a {got['tabulation_nr']}x{got['tabulation_nz']} "
        f"tabulation")
    # The grid is really BUILT at that size, not merely requested — the same
    # distinction that had run-case.sh printing "3 of 3 layers" off a spec
    # table on a mesh with none.
    assert len(s.green_function.tabulated_r_range) == 676
    assert len(s.green_function.tabulated_z_range) == 372
    assert s.method == "direct"


# --------------------------------------------------------------- gap F4 ---
# "SeakeepingResult — the only L2 type carrying uncertainty_rel — is defined
# and never constructed anywhere."

def test_the_l2_result_is_constructed_and_carries_a_measured_sigma(ref):
    """The type existed, `convergence_sweep()` was called only from tests, and
    `evaluate.revalidate` assembled its own dict from its own copy of the mesh
    levels — so no L2 number ever left the module with a convergence-derived
    band. MEASURED on the reference hull: uncertainty_rel 0.0036 over the
    (20,5) -> (28,7) pair, i.e. a real 0.36% and not a declared fraction.
    """
    from navalai import seakeeping
    from navalai.evaluate import revalidate

    _hull, m, ev = ref
    out = revalidate(ev, m, "L2")
    assert out.tier == "L2"
    sk = out.seakeeping
    # The escalation path serialises the DATACLASS, so these keys exist
    # because the type has them, not because a dict literal was typed twice.
    assert sk["method"] == seakeeping.BIE_METHOD
    assert sk["tabulation"] == seakeeping.TABULATION
    assert sk["meshes"] == [list(x) for x in seakeeping.L2_MESHES]
    assert 0.0 < sk["uncertainty_rel"] < 0.5
    assert out.badges["heave_added_mass"][0] == "L2"
    assert out.badges["heave_added_mass"][1] > 0.0


def test_a_single_mesh_l2_result_is_refused_not_defaulted(ref):
    """The other half: with one mesh there is no convergence evidence, and
    `uncertainty_rel = None` on a badged L2 quantity is a sigma of nothing at
    all. It refuses instead.
    """
    from navalai import seakeeping

    hull, _m, ev = ref
    with pytest.raises(ValueError, match="two mesh levels"):
        seakeeping.heave_seakeeping(hull, np.array([1.0]), ev.hydro.disp_kg,
                                    ev.hydro.awp, meshes=((20, 5),))


# --------------------------------------------------------------- gap F5 ---
# "waves.heave_response convolves a zero-speed RAO with JONSWAP in ABSOLUTE
# frequency — no encounter-frequency transform."

def test_the_response_spectrum_is_read_at_the_encounter_frequency():
    """MEASURED on the reference hull's heave RAO in the Black Sea coastal
    state (Hs 2.0 m, Tp 5.5 s) at its 5 kn cruise: the spectral peak sits at
    w = 1.1424 rad/s and is met at w_e = 1.4847 rad/s in head seas — **+30%**,
    which on a small-craft heave RAO is the difference between the resonant
    flank and the far side of it. Significant heave response over the same
    RAO and the same sea: 1.792 m at zero speed, **1.458 m** head, **2.033 m**
    following. The old code returned 1.792 m for all three.
    """
    from navalai.waves import (BLACK_SEA_COASTAL, ResponseReport,
                               encounter_omega, heave_response)

    w = np.linspace(0.3, 3.0, 40)
    # A peaked RAO, so a 30% frequency shift has somewhere to move to.
    rao = 1.0 / np.sqrt((1.0 - (w / 1.15) ** 2) ** 2 + (0.25 * w / 1.15) ** 2)
    u = 2.5722                                     # 5 kn

    zero = heave_response(w, rao, BLACK_SEA_COASTAL)
    head = heave_response(w, rao, BLACK_SEA_COASTAL, speed=u,
                          heading_deg=180.0)
    foll = heave_response(w, rao, BLACK_SEA_COASTAL, speed=u, heading_deg=0.0)

    # Head seas raise the encountered frequency, following seas lower it.
    assert head.omega_e_peak > BLACK_SEA_COASTAL.wp > foll.omega_e_peak
    assert head.omega_e_peak / BLACK_SEA_COASTAL.wp == pytest.approx(1.30,
                                                                     abs=0.02)
    # The transform must MOVE the answer, or it is decoration.
    assert abs(head.hs_heave - zero.hs_heave) / zero.hs_heave > 0.05
    assert head.hs_heave != pytest.approx(foll.hs_heave, rel=1e-3)
    # Following seas fold w -> w_e; the report says so rather than hiding it.
    assert foll.following_sea_fold and not head.following_sea_fold
    assert isinstance(head, ResponseReport)
    assert encounter_omega(np.array([1.0]), 0.0, 180.0)[0] == 1.0


def test_zero_speed_is_exactly_the_old_answer():
    """The guard has to be inert where it does not apply: at U = 0 the
    encounter frequency IS the wave frequency, and this must reproduce the
    pre-fix number bit for bit rather than approximately. A transform that
    quietly perturbs the zero-speed case would have broken Gate D.
    """
    from navalai.waves import BLACK_SEA_COASTAL, heave_response, jonswap

    w = np.linspace(0.3, 3.0, 60)
    rao = 1.0 / (1.0 + (w / 1.2) ** 4)
    r = heave_response(w, rao, BLACK_SEA_COASTAL)
    m0r = float(np.trapezoid(rao**2 * jonswap(w, BLACK_SEA_COASTAL), w))
    assert r.hs_heave == 4.0 * math.sqrt(m0r)
    assert r.speed == 0.0 and not r.following_sea_fold


def test_the_friction_band_propagates_the_form_factor(ref):
    """Gap H1's shape inside the resistance band: sigma on R_F was a flat
    `0.10 * rf` regardless of whether k came from the regression or off the
    clamp. It now carries sigma_k/(1+k) in quadrature with the friction-line
    scatter, so a hull whose form factor is a guess reports a wide band.
    """
    hull, m, ev = ref
    hs = ev.hydro
    r = ev.resistance
    expect = r.rf * math.sqrt((r.form.sigma_k / (1.0 + r.form.k)) ** 2 + 0.01)
    assert r.uncertainty == pytest.approx(0.25 * r.rw + expect, rel=1e-12)
    # And it is BIGGER for a clamped hull than for an in-support one, which is
    # the entire point of measuring it.
    assert (form_factor(0.60, 10.0, 3.0, 0.60).sigma_k
            > form_factor(0.55, 10.0, 1.5, 0.60).sigma_k)
