"""Gate: the tank-resonance diagnostic must REFUSE a period it cannot see.

The incident that motivated this file, MEASURED 2026-08-06: the pressure force
on `runs/val_coarse5` oscillates between 0.27x and 5.92x its expected 20.8 N
and swings through zero into thrust, and the first attempt to name the period
reached for an FFT. On `runs/beach` (10.40 s of record) and `runs/wigley`
(9.99 s) that FFT returned its largest peak at EXACTLY 10.40 s and EXACTLY
10.00 s — the record length in both cases, which is what a linear-detrended
history always correlates with best. Two "measurements" of nothing.

So every guard here is a real failure mode, and each test names it. The
diagnostic itself is exercised on synthetic histories, following
`navalai.cfd.post`'s convention that the post-processing is testable without
OpenFOAM; the real cases live under the gitignored `runs/` and are picked up
opportunistically at the bottom.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import tank_resonance as TR

REPO = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# the period fit, and the two ways it is allowed to say NO
# --------------------------------------------------------------------------

def _sine(period, span, n=400, amp=1.0, trend=0.0, noise=0.0, seed=0):
    t = np.linspace(0.0, span, n)
    rng = np.random.default_rng(seed)
    y = amp * np.sin(2 * np.pi * t / period) + trend * t
    return t, y + noise * rng.standard_normal(n)


def test_a_resolvable_period_is_recovered():
    """Six clean cycles: the fit must land on the period, not near it."""
    t, y = _sine(3.0, 18.0)
    fit = TR.dominant_period(t, y)
    assert fit.period_s == pytest.approx(3.0, rel=0.03)
    assert fit.n_cycles == pytest.approx(6.0, rel=0.05)
    assert fit.explained_variance > 0.95


def test_a_period_survives_a_startup_trend():
    """The trend is fitted WITH the sinusoid, not subtracted before it.

    Every run here starts impulsively, so the slow ramp is always present.
    Detrending first removes part of a slow oscillation and then blames the
    remainder on a shorter one.
    """
    t, y = _sine(4.0, 24.0, amp=1.0, trend=0.5, noise=0.05)
    fit = TR.dominant_period(t, y)
    assert fit.period_s == pytest.approx(4.0, rel=0.05)


def test_one_cycle_of_record_refuses_to_name_a_period():
    """THE runs/beach AND runs/wigley INCIDENT.

    beach holds 10.40 s and wigley 9.99 s, and an FFT of each puts its largest
    peak at the record length itself. A period needs cycles; one is not enough
    and the tool must say NO RESULT rather than report the span back.
    """
    t, y = _sine(9.0, 9.5)                 # ~1.06 cycles
    with pytest.raises(TR.ResonanceError, match="resolvable range|cycles"):
        TR.dominant_period(t, y)


def test_a_pure_ramp_is_not_an_oscillation():
    """A monotone history has no period, and the fit must not invent one."""
    t = np.linspace(0.0, 40.0, 500)
    y = 3.0 * t + 0.001 * np.random.default_rng(1).standard_normal(500)
    with pytest.raises(TR.ResonanceError):
        TR.dominant_period(t, y)


def test_four_samples_is_not_a_history():
    """runs/val_coarse holds FOUR force rows — a solve that diverged at
    t = 0.0072 s. post.MIN_WINDOW_SAMPLES refuses it a mean; this refuses it
    a period, for the same reason."""
    t = np.array([0.0071, 0.00715, 0.00718, 0.0072])
    y = np.array([1.0, -2.0, 5.0, -9.0])
    with pytest.raises(TR.ResonanceError, match="samples"):
        TR.dominant_period(t, y)


def test_the_scan_never_offers_a_period_it_cannot_show():
    """The guard is structural, not a post-hoc rejection.

    MIN_CYCLES caps the SEARCH at span/MIN_CYCLES, so an unresolvable period
    is never a candidate in the first place. A check applied after the fact
    can be forgotten; a bound on the search cannot.
    """
    t, y = _sine(2.0, 20.0)
    fit = TR.dominant_period(t, y)
    assert fit.period_s <= 20.0 / TR.MIN_CYCLES + 1e-9
    assert fit.n_cycles >= TR.MIN_CYCLES


# --------------------------------------------------------------------------
# what the case IS — measured, never assumed
# --------------------------------------------------------------------------

def _case(tmp_path, *, depth=7.2786, x0=-18.1965, x1=14.5572, y1=10.9179,
          g=9.81, speed=2.196, lts=False):
    c = tmp_path / "case"
    (c / "system").mkdir(parents=True)
    (c / "constant").mkdir(parents=True)
    (c / "constant" / "g").write_text(
        "FoamFile { object g; }\nvalue           (0 0 -%r);\n" % g)
    verts = []
    # bottom, waterline and an AIR block above it: the still-water depth is the
    # distance to z = 0, and the air block must not be counted into it.
    for z in (-depth, 0.0, 0.25 * 7.2786):
        for (x, y) in ((x0, 0.0), (x1, 0.0), (x1, y1), (x0, y1)):
            verts.append(f"  ({x} {y} {z})")
    (c / "system" / "blockMeshDict").write_text(
        "vertices (\n" + "\n".join(verts) + "\n)\n;\n")
    (c / "system" / "fvSchemes").write_text(
        "ddtSchemes { default %s; }\n" % ("localEuler rDeltaT" if lts
                                          else "Euler"))
    (c / "case.info").write_text(f"speed_ms={speed}\nsymmetric=True\n")
    return c


def test_gravity_is_read_from_the_case_not_declared_here(tmp_path):
    """A NUMBER LIVES IN EXACTLY ONE PLACE. case.py's `_G = 9.81` is the
    generator's copy; the solver read constant/g, and so does this."""
    c = _case(tmp_path, g=9.5)
    assert TR.gravity(c) == pytest.approx(9.5)


def test_a_case_with_no_gravity_file_is_refused(tmp_path):
    c = _case(tmp_path)
    (c / "constant" / "g").unlink()
    with pytest.raises(TR.ResonanceError, match="constant/g"):
        TR.gravity(c)


def test_depth_is_to_the_waterline_not_the_top_of_the_air_block(tmp_path):
    """blockMesh puts the waterline on z = 0 STRUCTURALLY. Taking the full z
    extent would add the 0.25 L air block to the tank depth and shorten every
    predicted seiche period by ~12%."""
    c = _case(tmp_path, depth=7.2786)
    dom = TR.domain(c)
    assert dom["depth_m"] == pytest.approx(7.2786)
    assert dom["length_m"] == pytest.approx(32.7537, abs=1e-3)


def test_an_lts_case_is_refused_outright(tmp_path, capsys):
    """runs/lts samples 'time' at a dead-flat 10 s interval out to 2000. Those
    are ITERATIONS. A spectrum over pseudo-time measures nothing, and the
    numbers it produces look exactly like real ones."""
    c = _case(tmp_path, lts=True)
    assert TR.is_lts(c) is True
    assert TR.report(c) == 2
    assert "LTS" in capsys.readouterr().out


# --------------------------------------------------------------------------
# the mechanisms, and telling them apart
# --------------------------------------------------------------------------

def test_the_doppler_shift_is_the_whole_difference_between_the_verdicts():
    """THE MEASUREMENT THAT DECIDED IT.

    The same tank at two speeds. A still-water seiche predicts one number for
    both; the Doppler form predicts two, and it is the two that were measured.
    Both figures below come from the free-surface fit, not from the forces.
    """
    L, h = 32.7537, 7.2786
    # runs/val_coarse5: U 2.196, measured lambda 11.44 m, measured T 5.53 s
    assert TR.apparent_period(11.44, h, 2.196, 9.81) == pytest.approx(5.53, rel=0.03)
    # runs/seiche_u_half: U 1.098, measured lambda 11.50 m, measured T 3.67 s
    assert TR.apparent_period(11.50, h, 1.098, 9.81) == pytest.approx(3.67, rel=0.03)
    # the still-water form gives ONE number for both, and it is neither
    still = 2.0 * L / np.sqrt(9.81 * h)
    assert still == pytest.approx(7.752, rel=1e-3)
    assert abs(still - 5.53) / 5.53 > 0.35
    assert abs(still - 3.67) / 3.67 > 1.0


def test_a_wave_the_stream_outruns_cannot_stand_in_the_tank():
    """c <= U means the energy is swept out of the domain, so that wavelength
    has no tank-frame period at all. Returning a finite number there would
    invent a mode out of a wave that has left."""
    assert TR.apparent_period(0.5, 7.2786, 2.196, 9.81) == float("inf")
    assert np.isfinite(TR.apparent_period(11.5, 7.2786, 2.196, 9.81))


def test_the_blocking_minimum_is_exactly_four_ship_wave_periods():
    """dT/dlambda = 0 at c = 2U, i.e. where cg = U — so the floor of the
    Doppler curve is T = 8 pi U/g, four times 2 pi U/g. Worth pinning because
    the curve is FLAT there, which is why modes n=4..8 all land within 5% of
    one another at Fn 0.26 and the measurement cannot separate them."""
    p = TR.predictions(32.7537, 7.2786, 2.196, 9.81)
    block = p["blocking minimum (cg = U)"]
    ship = p["ship transverse wave"]
    assert block["period_s"] == pytest.approx(4.0 * ship["period_s"])
    assert block["wavelength_m"] == pytest.approx(4.0 * ship["wavelength_m"])
    assert block["period_s"] == pytest.approx(5.626, rel=1e-3)
    # and it really is the minimum of the Doppler curve
    lams = np.linspace(4.0, 40.0, 400)
    assert min(TR.apparent_period(l, 7.2786, 2.196, 9.81) for l in lams) \
        >= block["period_s"] - 1e-3


def test_the_two_families_depend_on_disjoint_inputs():
    """A still-water seiche cannot move with speed and a Doppler tank mode
    must. That asymmetry is what made a speed sweep in a FIXED tank the
    decisive experiment — and it was the only one available, since the
    generator derives tank depth from Lwl and speed and exposes no depth
    knob."""
    a = TR.predictions(32.7537, 7.2786, 2.196, 9.81)
    b = TR.predictions(32.7537, 7.2786, 1.098, 9.81)
    assert (a["still-water seiche n=1"]["period_s"]
            == pytest.approx(b["still-water seiche n=1"]["period_s"]))
    assert (b["tank mode n=6 (Doppler)"]["period_s"]
            < a["tank mode n=6 (Doppler)"]["period_s"])
    # the WAVELENGTHS are the tank's either way, and do not move with speed
    assert (a["tank mode n=6 (Doppler)"]["wavelength_m"]
            == pytest.approx(b["tank mode n=6 (Doppler)"]["wavelength_m"]))


def test_shallow_water_is_not_good_enough_for_this_tank():
    """2L/sqrt(gh) and the tanh(kh) form differ by 7.6% on the KCS tank, and
    the candidates being separated are 40% apart — close enough that using the
    wrong one moves a verdict."""
    p = TR.predictions(32.7537, 7.2786, 2.196, 9.81)
    exact = p["still-water seiche n=1"]["period_s"]
    shallow = p["still-water seiche n=1 (2L/sqrt(gh))"]["period_s"]
    assert shallow == pytest.approx(7.752, rel=1e-3)
    assert exact == pytest.approx(8.343, rel=1e-3)
    assert exact > shallow


def test_an_out_of_reach_candidate_is_unseen_not_ruled_out():
    """"We did not see it" and "it is not there" are different findings, and
    this project has confused them before."""
    # runs/val_coarse5: U = 2.196, 19.79 s of record.
    full = TR.predictions(32.7537, 7.2786, 2.196, 9.81)
    _v, hits = TR.classify(5.95, full, span=19.79)
    by_name = {h[0]: h for h in hits}
    assert by_name["still-water seiche n=1"][3] is True    # 2.37 cycles
    assert by_name["tank mode n=1 (Doppler)"][3] is False  # 11.58 s: 1.71
    assert by_name["tank mode n=6 (Doppler)"][3] is True

    # runs/seiche_u_half at its FIRST stopping point, 8.90 s. Same tank, half
    # the speed: the still-water candidate is still out of reach (it never
    # moves) while the Doppler modes shorten and come into it. That is exactly
    # why the run was extended to 24 s before anything was concluded — at 8.90
    # the fit returned 4.21 s from a scan capped at 4.45.
    half = TR.predictions(32.7537, 7.2786, 1.098, 9.81)
    _v2, hits2 = TR.classify(4.21, half, span=8.90)
    by_name2 = {h[0]: h for h in hits2}
    assert by_name2["still-water seiche n=1"][3] is False  # 1.07 cycles
    assert by_name2["tank mode n=6 (Doppler)"][3] is True  # 3.60 s: 2.47


def test_the_verdict_names_the_family_not_a_mode_number():
    """The Doppler curve is flat near its minimum: modes n=4..8 predict
    5.63-5.94 s at Fn 0.26 and no 19.79 s record separates them. Claiming a
    single n would be a precision the measurement does not have."""
    preds = TR.predictions(32.7537, 7.2786, 2.196, 9.81)
    verdict, _ = TR.classify(5.95, preds, span=19.79)
    assert verdict.startswith("DOPPLER-SHIFTED TANK MODE")
    assert "cannot separate them" in verdict


# --------------------------------------------------------------------------
# standing vs propagating — the discriminator the periods alone cannot give
# --------------------------------------------------------------------------

def _synthetic_surface(kind, period, wavelength, times, x):
    k = 2 * np.pi / wavelength
    w = 2 * np.pi / period
    T, X = np.meshgrid(times, x, indexing="ij")
    if kind == "standing":
        return np.cos(k * X) * np.cos(w * T)
    return np.cos(k * X - w * T)


def test_a_standing_wave_and_a_travelling_wave_are_told_apart():
    """A SEICHE IS A STANDING WAVE BY DEFINITION. Whatever the period says,
    a mode whose phase ramps with x is not one — which is the finding that
    settled runs/val_coarse5 (standing score 0.34)."""
    x = np.linspace(-18.2, 14.6, 80)
    times = np.arange(4.0, 19.0, 1.0)
    std = TR.mode_shape(times, x,
                        _synthetic_surface("standing", 5.5, 11.5, times, x),
                        u=2.196, depth=7.2786, g=9.81)
    trv = TR.mode_shape(times, x,
                        _synthetic_surface("travelling", 5.5, 11.5, times, x),
                        u=2.196, depth=7.2786, g=9.81)
    assert std.standing_score > 0.9
    assert trv.standing_score < 0.2
    assert std.period_s == pytest.approx(5.5, rel=0.05)
    assert trv.wavelength_m == pytest.approx(11.5, rel=0.05)


def test_the_surface_scan_floor_is_nyquist_not_a_comfort_bound():
    """MEASURED BUG. The floor was max(3*dt, 0.1*span), which on
    runs/val_coarse5's six snapshots (2 s apart, 14 s span) put the scan at
    6.00-7.00 s — and the fit returned 6.00, the bound itself, where the
    Nyquist-floored scan gives 5.53 s. A limit chosen for comfort does not
    reject a bad answer, it manufactures one."""
    x = np.linspace(-18.2, 14.6, 80)
    times = np.array([4.0, 6.0, 8.0, 14.0, 16.0, 18.0])
    prof = _synthetic_surface("travelling", 5.53, 11.4, times, x)
    ms = TR.mode_shape(times, x, prof, u=2.196, depth=7.2786, g=9.81)
    assert ms.period_s == pytest.approx(5.53, rel=0.05)
    assert ms.period_s < 3.0 * 2.0          # would have been forbidden before


def test_too_few_snapshots_refuse_a_mode_shape():
    x = np.linspace(-18.2, 14.6, 40)
    times = np.array([4.0, 6.0])
    with pytest.raises(TR.ResonanceError):
        TR.mode_shape(times, x,
                      _synthetic_surface("standing", 5.5, 11.5, times, x),
                      u=2.196, depth=7.2786, g=9.81)


def test_a_mode_at_the_nyquist_floor_is_refused_as_possibly_aliased():
    """4.4 s is 2.2x a 2 s snapshot interval: a shorter true period folds onto
    it and there is no way to tell from this sampling."""
    x = np.linspace(-18.2, 14.6, 60)
    times = np.arange(4.0, 20.0, 2.0)
    prof = _synthetic_surface("travelling", 4.4, 11.4, times, x)
    with pytest.raises(TR.ResonanceError, match="Nyquist|ALIAS"):
        TR.mode_shape(times, x, prof, u=2.196, depth=7.2786, g=9.81)


# --------------------------------------------------------------------------
# the real cases, when this machine has them (runs/ is gitignored)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name,span_s", [("beach", 10.40), ("wigley", 9.99)])
def test_the_short_runs_still_refuse_on_the_real_files(name, span_s):
    """The two runs whose FFT returned their own record length. If they are
    present, they must produce NO RESULT — exit 2, never a number."""
    case = REPO / "runs" / name
    if not (case / "postProcessing" / "forces").exists():
        pytest.skip(f"runs/{name} not on this machine (runs/ is gitignored)")
    t, fp = TR.pressure_history(case)
    assert (t[-1] - t[0]) == pytest.approx(span_s, abs=0.3)
    with pytest.raises(TR.ResonanceError):
        TR.dominant_period(t, fp)


@pytest.mark.parametrize("name,u,lam,period", [
    ("val_coarse5", 2.196, 11.44, 5.53),
    ("seiche_u_half", 1.098, 11.50, 3.67),
])
def test_the_two_speeds_agree_on_the_wavelength_and_not_on_the_period(
        name, u, lam, period):
    """THE DECIDING MEASUREMENT, pinned. Same tank, U halved.

    The wavelength is unchanged (11.44 -> 11.50 m) across two speeds AND two
    meshes, so the DOMAIN selects it; the period follows the Doppler shift.
    A still-water seiche would hold the period at 7.75 s and say nothing about
    either observation.
    """
    case = REPO / "runs" / name
    if not (case / "processor0").exists():
        pytest.skip(f"runs/{name} not on this machine (runs/ is gitignored)")
    g = TR.gravity(case)
    dom = TR.domain(case)
    assert TR.speed(case) == pytest.approx(u)
    times, x, prof = TR.surface_profiles(case)
    ms = TR.mode_shape(times, x, prof, u, dom["depth_m"], g)
    assert ms.wavelength_m == pytest.approx(lam, rel=0.05)
    assert ms.period_s == pytest.approx(period, rel=0.05)
    # the free-wave dispersion relation holds on the MEASURED wavelength: this
    # is a real gravity wave, not a numerical mode
    assert ms.phase_speed_intrinsic == pytest.approx(ms.dispersion_speed, rel=0.03)
    # and the Doppler form reproduces the period with no free parameter
    assert ms.doppler_period == pytest.approx(ms.period_s, rel=0.05)
