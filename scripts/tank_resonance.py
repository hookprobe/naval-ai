"""Is the low-frequency force oscillation a TANK MODE, and if so which one?

MEASURED on `runs/val_coarse5` (symmetric KCS, 230725 cells, 19.81 s = 1.33
flow-throughs): the viscous force sits steady at 1.22-1.36x ITTC-57 — a
textbook form factor, so the wall model is right — while the PRESSURE force
swings between 0.27x and 5.92x its expected 20.8 N and passes THROUGH ZERO
into thrust, which no real hull drag does. Per-second means went -7.07, -1.51,
-29.23, -50.30, -59.35, -39.87, -5.78, **+14.42**, -10.53, -47.83, -62.05,
-71.83, -40.69 N. The ship-wave period at Fn 0.26 is 2*pi*U/g = 1.41 s and the
oscillation is nowhere near it, so the question is which DOMAIN-scale timescale
it is — and there is more than one candidate:

  still-water seiche   the textbook standing mode of a closed basin,
                       T = 2L/sqrt(g h) = 7.75 s for this tank. Depends on L
                       and h only, so it does NOT move with ship speed.
  Doppler-shifted      the same tank WAVELENGTHS (lambda = 2L/n), but the tank
  tank mode            is not still: a wave that holds station in it runs
                       upstream through water moving at U, so what goes past
                       the hull has period lambda / (c(lambda) - U).

MEASURED, and this is the finding. Same tank, two speeds, and the free surface
read directly out of the saved alpha.water fields:

    run              U m/s   lambda m   T measured   lambda/(c-U)   2L/sqrt(gh)
    val_coarse5      2.196     11.44       5.53 s        5.64 s        7.75 s
    seiche_u_half    1.098     11.50       3.67 s        3.66 s        7.75 s

The WAVELENGTH did not move when the speed halved (11.44 -> 11.50 m, and the
two runs are on different meshes), so it is the DOMAIN that selects it — it
sits on tank mode n=6, lambda = 2L/6 = 10.92 m. The PERIOD did move, by exactly
the Doppler shift, to 0.3% and 1.9%. A still-water seiche explains neither: it
predicts 7.75 s at both speeds.

So it IS a tank resonance, and it is NOT the seiche that was hypothesised. That
matters for the fix, because 2L/sqrt(gh) says "resize the tank" and this says
"the reflecting ends are the problem".

A note on the blocking condition, because it is the reason the design point is
the worst case: T(lambda) = lambda/(c-U) has a MINIMUM at c = 2U, i.e. where
the GROUP velocity equals U and the wave's energy holds station. At Fn 0.26 the
blocking wavelength is 12.35 m and the tank mode is 10.92 m — they nearly
coincide, so the mode the tank selects is also the one whose energy cannot
drain. At half speed they are 3.09 m apart and the oscillation is
correspondingly less coherent (the pressure history there will not yield a
single period at all: 41.7% of the detrended variance, refused).

    python scripts/tank_resonance.py runs/val_coarse5
    python scripts/tank_resonance.py runs/val_coarse5 --surface

REFUSALS ARE THE POINT. A period needs cycles, and most runs in this repository
are far too short to have any: `runs/beach` (10.40 s) and `runs/wigley`
(9.99 s) both put their largest spectral peak at EXACTLY the record length,
which is the signature of a record that cannot resolve its own dominant
timescale, not a measurement of one. This tool searches only periods it can see
at least `MIN_CYCLES` of and says NO RESULT otherwise. It also refuses an LTS
case outright: pseudo-time has no periods in it.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.cfd import post

# A period claimed from fewer cycles than this is a trend, not an oscillation.
# Calibrated by the two runs that fail it: beach at 10.40 s and wigley at
# 9.99 s each return their own record length as "the period" when the bound is
# lifted, because a linear-detrended record always correlates best with the
# longest sinusoid it can hold.
MIN_CYCLES = 2.0

# Fraction of the DETRENDED variance one sinusoid must explain before it is
# called an oscillation. The fit always returns something; this is what stops
# that something being reported, and it is CALIBRATED, not chosen:
#
#     run              record    best fit   explained    leading candidate
#     val_coarse5      19.79 s    5.95 s      88.1%      inside the record
#     seiche_u_half    23.94 s    4.19 s      93.9%      inside the record
#     beach            10.40 s    4.05 s      33.1%      OUTSIDE (5.63 s needs
#                                                        2 cycles = 11.3 s)
#
# beach is the calibration point and it is not academic: at 33.1% the tool
# returned "seiche n=3, 4.05 s" for a case whose leading candidate its record
# could not even hold, on the SAME tank and the SAME speed where 19.79 s of
# record gives 5.95 s. A short record does not find a different mechanism; it
# finds whatever it is allowed to find.
MIN_EXPLAINED_VARIANCE = 0.50

# How close a measured period must sit to a prediction to be called that
# mechanism. 15% is loose on purpose: the competing predictions for
# val_coarse5 are 5.63 s and 7.75 s, 38% apart, so a bar this wide still
# separates them, and a tighter one would reject a real match on a 6-snapshot
# surface fit.
MATCH_TOL = 0.15


class ResonanceError(ValueError):
    """This case cannot yield a period, and says why.

    Its own type, following `post.ForceHistoryError` and `WaterplaneError`, so
    a caller can distinguish "unusable data" from a missing file without a
    broad `except ValueError` swallowing both.
    """


# --------------------------------------------------------------------------
# what the case actually is: geometry from the mesh, g from constant/g
# --------------------------------------------------------------------------

_NUM = re.compile(r"[-+]?\d[\d.eE+-]*")


def gravity(case: str | Path) -> float:
    """|g| from the case's OWN constant/g. Never a literal.

    case.py's `_G = 9.81` is a second declaration of the same number and the
    recurring defect in this codebase is a number declared twice. The solver
    read constant/g; so does this.
    """
    p = Path(case) / "constant" / "g"
    if not p.exists():
        raise ResonanceError(f"no constant/g under {case}: cannot know the "
                             f"gravity the solver used, and it is not this "
                             f"script's to assume")
    txt = p.read_text()
    m = re.search(r"value\s*\(([^)]*)\)", txt)
    if not m:
        raise ResonanceError(f"constant/g in {case} has no `value (...)` entry")
    v = [float(x) for x in _NUM.findall(m.group(1))]
    return float(np.linalg.norm(v))


def domain(case: str | Path) -> dict:
    """Tank length and still-water depth MEASURED from system/blockMeshDict.

    Not from case.info: `tank_depth_m` has been recorded since the beginning
    but `domain_length_m` only since 2026-08-06, and every run older than that
    would otherwise get the 4.5 Lwl assumption silently applied. The vertex
    list is the mesh the solver ran on.
    """
    p = Path(case) / "system" / "blockMeshDict"
    if not p.exists():
        raise ResonanceError(f"no system/blockMeshDict under {case}")
    txt = p.read_text()
    m = re.search(r"vertices\s*\((.*?)\n\)", txt, re.S)
    if not m:
        raise ResonanceError(f"cannot parse vertices from {p}")
    pts = np.array([[float(x) for x in _NUM.findall(v)]
                    for v in re.findall(r"\(([^)]*)\)", m.group(1))])
    if pts.size == 0 or pts.shape[1] != 3:
        raise ResonanceError(f"cannot parse vertices from {p}")
    x0, x1 = float(pts[:, 0].min()), float(pts[:, 0].max())
    # The waterline sits at z = 0 STRUCTURALLY (blockMesh splits there), so the
    # still-water depth is the distance from the bottom to zero, not the full
    # z extent — which also contains the air block.
    return {"length_m": x1 - x0, "x0": x0, "x1": x1,
            "depth_m": -float(pts[:, 2].min()),
            "half_width_m": float(pts[:, 1].max() - pts[:, 1].min())}


def is_lts(case: str | Path) -> bool:
    """True for a local-time-stepping (pseudo-time) case.

    `runs/lts` samples 'time' 10, 20 ... 2000 with a dead-flat 10 s interval:
    those are ITERATIONS, not seconds, and an FFT over them measures nothing.
    The marker is fvSchemes' `ddtSchemes { default localEuler ... }`.
    """
    p = Path(case) / "system" / "fvSchemes"
    return p.exists() and "localEuler" in p.read_text()


def speed(case: str | Path) -> float:
    info = post.read_case_info(case)
    if "speed_ms" not in info:
        raise ResonanceError(f"no speed_ms in {case}/case.info")
    return float(info["speed_ms"])


# --------------------------------------------------------------------------
# the candidate mechanisms, as closed-form predictions
# --------------------------------------------------------------------------

def wave_speed(wavelength: float, depth: float, g: float) -> float:
    """Full-dispersion phase speed — IMPORTED from the one home (the model
    this script's measurement promoted into `navalai.fidelity`)."""
    from navalai.fidelity import wave_speed as _ws
    return _ws(wavelength, depth, g)


def apparent_period(wavelength: float, depth: float, u: float,
                    g: float) -> float:
    """Tank-frame period of an UPSTREAM-running wave of this length.

    THE POINT OF THIS FUNCTION. A tank mode in still water has period
    lambda/c. This tank is not still — the stream runs at U — so a wave that
    holds station in the tank must run upstream through the water at c, and
    what an observer (or a force probe on the hull) sees go past is

        T = lambda / (c(lambda) - U)

    MEASURED, and it is the whole difference between the two verdicts this
    tool can print. On the SAME domain at two speeds:

        U = 2.196 m/s   lambda 11.44 m   T = 5.65 s predicted, 5.53 measured
        U = 1.098 m/s   lambda 11.50 m   T = 3.60 s predicted, 3.67 measured

    The still-water form gives 2.77 s for both and matches neither, and
    2L/sqrt(gh) gives 7.75 s for both and matches neither. Ignoring the
    Doppler shift is not a refinement, it is a different answer.

    Returns inf for a wave the stream can outrun (c <= U): its energy is
    swept downstream and out, so it cannot stand in the tank at all.
    """
    c = wave_speed(wavelength, depth, g)
    return float("inf") if c <= u else wavelength / (c - u)


def predictions(length: float, depth: float, u: float, g: float,
                n_modes: int = 8) -> dict:
    """Every domain-scale timescale this case can support, named.

    Two families, and they are NOT the same:

      still-water seiche n   the textbook 2L/n mode with no current. This was
                             the hypothesis under test and the data refutes
                             it: it predicts a period independent of U, and
                             the measured period halved-ish when U halved.
      tank mode n (Doppler)  the SAME wavelengths, but with the stream
                             accounted for. This is what matches.
    """
    out = {}
    for n in (1, 2, 3):
        lam = 2.0 * length / n
        out[f"still-water seiche n={n}"] = {
            "period_s": lam / wave_speed(lam, depth, g),
            "wavelength_m": lam,
        }
    out["still-water seiche n=1 (2L/sqrt(gh))"] = {
        "period_s": 2.0 * length / np.sqrt(g * depth),
        "wavelength_m": 2.0 * length,
    }
    for n in range(1, n_modes + 1):
        lam = 2.0 * length / n
        out[f"tank mode n={n} (Doppler)"] = {
            "period_s": apparent_period(lam, depth, u, g),
            "wavelength_m": lam,
        }
    # The Doppler curve T(lambda) = lambda/(c-U) has a MINIMUM, and it is not
    # an incidental one: dT/dlambda = 0 at c = 2U, i.e. exactly where the
    # GROUP velocity c/2 equals U and the wave's energy holds station in the
    # tank. T_min = 8 pi U / g — four ship-wave periods — and the curve is
    # flat around it, so every tank mode within a factor of ~1.5 in wavelength
    # lands on nearly the same apparent period. That flatness is why the
    # oscillation is so sharply defined despite no single mode being selected.
    out["blocking minimum (cg = U)"] = {
        "period_s": 8.0 * np.pi * u / g,
        "wavelength_m": 8.0 * np.pi * u * u / g,
    }
    out["ship transverse wave"] = {
        "period_s": 2.0 * np.pi * u / g,
        "wavelength_m": 2.0 * np.pi * u * u / g,
    }
    out["flow-through L/U"] = {
        "period_s": length / u,
        "wavelength_m": float("nan"),
    }
    return out


# --------------------------------------------------------------------------
# measuring a period, with the guard that refuses one
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PeriodFit:
    period_s: float
    explained_variance: float
    n_cycles: float
    span_s: float
    amplitude: float
    method: str


def dominant_period(t: np.ndarray, y: np.ndarray, *,
                    min_cycles: float = MIN_CYCLES,
                    n_scan: int = 3000) -> PeriodFit:
    """Least-squares single-sinusoid scan over the RESOLVABLE periods only.

    Not an FFT peak. Two reasons, both measured on this data:

      - FFT bins are spaced in FREQUENCY, so at 19.79 s of record the only
        available periods near the answer are 9.90, 6.60 and 4.95 s. The true
        value falls between two bins and the peak splits across them (6.60
        amplitude 9748, 4.95 amplitude 7204), which reads as two mechanisms
        where there is one.
      - Nothing in an FFT stops it returning the record length. Both
        `runs/beach` and `runs/wigley` do exactly that.

    The upper end of the scan is span/min_cycles, so a period the record cannot
    show is not merely rejected afterwards — it is never a candidate. A best
    fit that piles up against that bound is reported as UNRESOLVED rather than
    as a number.

    A linear trend is fitted SIMULTANEOUSLY with the sinusoid rather than
    removed first: detrending first subtracts part of a slow oscillation and
    then blames the remainder on a shorter one.
    """
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    if len(t) < 20:
        raise ResonanceError(
            f"force history has {len(t)} samples; a period needs a history, "
            f"not a handful of rows (runs/val_coarse holds 4, from a solve "
            f"that diverged at t=0.0072)")
    span = float(t[-1] - t[0])
    dt = float(np.median(np.diff(t)))
    t_lo = max(6.0 * dt, 0.05 * span)          # Nyquist-ish floor
    t_hi = span / min_cycles
    if t_hi <= t_lo:
        raise ResonanceError(
            f"record spans {span:.2f} s at dt {dt:.4g} s: there is no period "
            f"both longer than the sampling and shorter than "
            f"span/{min_cycles:g}")

    grid = np.linspace(t_lo, t_hi, n_scan)
    tn = t - t[0]
    base = np.column_stack([np.ones_like(tn), tn])
    # THE BASELINE IS THE TREND, NOT THE MEAN. Measuring the fit against the
    # mean credits the LINE to the oscillation: a pure ramp with a whisker of
    # noise then scores ~100% "explained variance" and every guard downstream
    # waves it through. What is being asked is what the sinusoid adds ON TOP OF
    # the trend that is there in every impulsively started run.
    bcoef, *_ = np.linalg.lstsq(base, y, rcond=None)
    ss_base = float(((y - base @ bcoef) ** 2).sum())
    best = (-np.inf, np.nan, 0.0)
    for T in grid:
        w = 2.0 * np.pi / T
        M = np.column_stack([base, np.cos(w * tn), np.sin(w * tn)])
        coef, *_ = np.linalg.lstsq(M, y, rcond=None)
        ev = 1.0 - float(((y - M @ coef) ** 2).sum()) / max(ss_base, 1e-30)
        if ev > best[0]:
            best = (ev, T, float(np.hypot(coef[2], coef[3])))
    ev, T, amp = best
    if T >= grid[-1] * 0.99:
        raise ResonanceError(
            f"the best fit sits at the top of the resolvable range "
            f"({T:.2f} s from a {span:.2f} s record): whatever dominates this "
            f"history is SLOWER than {min_cycles:g} cycles of it, so this run "
            f"cannot name it. Extend the run; do not report this number.")
    if ev < MIN_EXPLAINED_VARIANCE:
        raise ResonanceError(
            f"the best single sinusoid explains {100*ev:.1f}% of what the "
            f"linear trend leaves behind (bar "
            f"{100*MIN_EXPLAINED_VARIANCE:.0f}%): there is no coherent "
            f"oscillation here to name")
    return PeriodFit(T, ev, span / T, span, amp,
                     f"least-squares sinusoid + linear trend, scanned "
                     f"{t_lo:.2f}-{t_hi:.2f} s")


def pressure_history(case: str | Path):
    """(t, pressure_x) for a case, restart segments merged.

    The PRESSURE component specifically: the viscous part is the one that is
    already correct (1.22-1.36x ITTC-57 throughout runs/val_coarse5), so
    putting the total in here would dilute the signal with the stable half.
    """
    t, fp, _fv = post.parse_forces_components(post.forces_path(case))
    return t, fp


# --------------------------------------------------------------------------
# the free surface: standing or propagating?
# --------------------------------------------------------------------------

def _read_of_scalar(p: Path, n: int | None = None) -> np.ndarray:
    txt = p.read_text()
    i = txt.index("internalField")
    head = txt[i:txt.index(";", i)]
    if "nonuniform" not in head:
        return np.full(n, float(_NUM.findall(head.split("uniform")[1])[0]))
    j = txt.index("(", i)
    return np.fromstring(txt[j + 1:txt.index(")", j)], sep="\n")


def surface_profiles(case: str | Path, nbins: int = 80):
    """Water-column height per x-bin at every saved time, from alpha.water.

    Needs the cell volumes and centres, which OpenFOAM does not write by
    default. Generate them ONCE (they are static for a fixed hull):

        mpirun -np <np> postProcess -parallel -func writeCellVolumes
        mpirun -np <np> postProcess -parallel -func writeCellCentres -time <t0>

    Integrating alpha*V per bin rather than contouring alpha = 0.5 is
    deliberate: `scripts/render_case.py` records that ParaView CANNOT contour
    this mesh, because the z-only refineMesh rounds leave hanging-node
    POLYHEDRA. A volume integral does not care what shape the cells are.
    """
    case = Path(case)
    procs = sorted(case.glob("processor*"))
    if not procs:
        raise ResonanceError(f"{case} is not decomposed; --surface reads the "
                             f"processor*/ fields directly")
    times = []
    for d in procs[0].iterdir():
        try:
            tv = float(d.name)
        except ValueError:
            continue
        if d.is_dir() and (d / "alpha.water").exists() and (d / "V").exists():
            times.append(tv)
    times = sorted(times)
    if len(times) < 4:
        raise ResonanceError(
            f"{len(times)} saved field time(s) with both alpha.water and V. "
            f"A mode shape needs at least 4 to separate a standing wave from a "
            f"propagating one, and writeCellVolumes must have been run over "
            f"them.")
    centres = None
    for d in procs[0].iterdir():
        if d.is_dir() and (d / "Cx").exists():
            centres = d.name
            break
    if centres is None:
        raise ResonanceError(
            f"no Cx field under {case}/processor0/*/. Run "
            f"`mpirun -np <np> postProcess -parallel -func writeCellCentres "
            f"-time <one-saved-time>` first.")

    dom = domain(case)
    edges = np.linspace(dom["x0"], dom["x1"], nbins + 1)
    mid = 0.5 * (edges[1:] + edges[:-1])
    bin_area = (edges[1] - edges[0]) * dom["half_width_m"]
    prof = []
    for tv in times:
        tn = f"{tv:g}"
        col = np.zeros(nbins)
        for pd in procs:
            v = _read_of_scalar(pd / tn / "V")
            a = _read_of_scalar(pd / tn / "alpha.water", len(v))
            cx = _read_of_scalar(pd / centres / "Cx", len(v))
            idx = np.clip(np.digitize(cx, edges) - 1, 0, nbins - 1)
            col += np.bincount(idx, weights=a * v, minlength=nbins)
        prof.append(col / bin_area)
    return np.array(times), mid, np.array(prof)


@dataclass(frozen=True)
class ModeShape:
    period_s: float
    explained_variance: float
    wavelength_m: float
    phase_speed_tank: float        # + is upstream, toward the inlet
    phase_speed_intrinsic: float   # relative to the stream
    dispersion_speed: float        # what a free wave of that length must do
    standing_score: float          # 1 = perfectly standing, 0 = propagating
    doppler_period: float          # lambda/(c-U) for the MEASURED lambda


def mode_shape(times, x, prof, u: float, depth: float, g: float,
               *, min_cycles: float = MIN_CYCLES) -> ModeShape:
    """Fit eta'(x,t) = A(x) cos(wt) + B(x) sin(wt) and ask what it is.

    The MEAN over the snapshots is removed first, which cancels both the hull's
    own displaced volume and the steady Kelvin pattern — neither is unsteady,
    and both are much larger than what we are after (the hull alone shifts the
    column by tens of centimetres against a 10 mm signal).

    `standing_score` is |sum(mode^2)| / sum(|mode|^2): 1 when every bin shares
    one phase up to a sign (a standing wave), ~0 when the phase ramps with x (a
    travelling one). READ IT AS A TEST OF THE STILL-WATER SEICHE, NOT OF A TANK
    MODE IN GENERAL. A mode in a current is a superposition of an upstream and
    a downstream component that have the SAME tank-frame frequency but
    DIFFERENT wavelengths, so it cannot be a clean standing wave even when the
    tank is what selects it; and near blocking the upstream component is the
    one that survives, which leaves a pattern that mostly travels. Measured
    0.34 and 0.17 on the two runs here.

    `doppler_period` is the check that carries the verdict, because it has NO
    free parameter: take the wavelength this fit measured, ask the dispersion
    relation how fast such a wave runs, subtract the stream, and the period
    follows. Measured 5.65 vs 5.53 s and 3.60 vs 3.67 s.
    """
    times = np.asarray(times, float)
    span = float(times[-1] - times[0])
    D = prof - prof.mean(axis=0)
    ss_tot = float((D ** 2).sum())
    # NYQUIST, and nothing tighter. An earlier floor of max(3*dt, 0.1*span) put
    # the scan over runs/val_coarse5's 6 snapshots at 6.00-7.00 s and the fit
    # returned 6.00 — the bound itself — where the free range gives 5.54 s. A
    # limit chosen for comfort rather than from the sampling theorem does not
    # refuse a bad answer, it manufactures one.
    dt = float(np.median(np.diff(times)))
    lo, hi = 2.2 * dt, span / min_cycles
    if hi <= lo:
        raise ResonanceError(
            f"{len(times)} snapshots over {span:.2f} s at {dt:.2f} s spacing "
            f"cannot resolve a period that is both above Nyquist and shorter "
            f"than span/{min_cycles:g}")
    best = (-np.inf, np.nan, None)
    for T in np.linspace(lo, hi, 2000):
        w = 2.0 * np.pi / T
        M = np.column_stack([np.cos(w * times), np.sin(w * times)])
        coef, *_ = np.linalg.lstsq(M, D, rcond=None)
        ev = 1.0 - float(((D - M @ coef) ** 2).sum()) / max(ss_tot, 1e-30)
        if ev > best[0]:
            best = (ev, T, coef)
    ev, T, coef = best
    if T >= hi * 0.99:
        raise ResonanceError(
            f"the free-surface fit sits at the top of the resolvable range "
            f"({T:.2f} s from {span:.2f} s of snapshots)")
    if T <= lo * 1.01:
        raise ResonanceError(
            f"the free-surface fit sits at the Nyquist floor ({T:.2f} s "
            f"against {dt:.2f} s snapshot spacing): the real period may be "
            f"shorter and ALIASED onto this one. Save fields more often.")
    mode = coef[0] + 1j * coef[1]
    amp = np.abs(mode)
    sel = amp > 0.3 * amp.max()
    standing = abs(complex((mode[sel] ** 2).sum())) / float((amp[sel] ** 2).sum())

    ks = np.linspace(-3.0, 3.0, 12001)
    powr = [abs(complex((mode[sel] * np.exp(-1j * k * x[sel])).sum())) for k in ks]
    k = float(ks[int(np.argmax(powr))])
    lam = 2.0 * np.pi / abs(k) if k else float("inf")
    c_tank = lam / T * np.sign(k)
    return ModeShape(T, ev, lam, float(c_tank), float(abs(c_tank) + u),
                     wave_speed(lam, depth, g), float(standing),
                     apparent_period(lam, depth, u, g))


# --------------------------------------------------------------------------
# the verdict
# --------------------------------------------------------------------------

def family(name: str) -> str:
    if name.startswith("still-water seiche"):
        return "STILL-WATER SEICHE"
    if name.startswith("tank mode") or name.startswith("blocking minimum"):
        return "DOPPLER-SHIFTED TANK MODE"
    return "other"


def classify(measured: float, preds: dict, span: float,
             *, tol: float = MATCH_TOL) -> tuple[str, list]:
    """Name the mechanism whose prediction the measurement matches.

    Only predictions the record could actually have SHOWN are eligible: a
    candidate slower than span/MIN_CYCLES is reported as out of reach rather
    than quietly ruled out, because "we did not see it" and "it is not there"
    are different findings and this project has confused them before.

    The verdict is a FAMILY, not a mode number. The Doppler curve is flat near
    its minimum, so at U = 2.196 m/s in this tank the apparent periods of
    modes n = 4..8 span only 5.63-5.93 s: the measurement cannot pick between
    them and must not pretend to. What it CAN separate is the family — the
    still-water form and the Doppler form differ by 40% and by their entire
    dependence on U.
    """
    hits = []
    for name, p in preds.items():
        if name.startswith(("ship transverse", "flow-through")):
            continue
        T = p["period_s"]
        resolvable = np.isfinite(T) and span / T >= MIN_CYCLES
        err = abs(measured - T) / T if np.isfinite(T) else float("inf")
        hits.append((name, T, err, resolvable))
    matched = [h for h in hits if h[2] <= tol and h[3]]
    if not matched:
        return "UNEXPLAINED", hits
    matched.sort(key=lambda h: h[2])
    fam = family(matched[0][0])
    same = [h for h in matched if family(h[0]) == fam]
    return (f"{fam} — closest {matched[0][0]} at {matched[0][1]:.2f} s; "
            f"{len(same)} candidate(s) in this family match, and the "
            f"measurement cannot separate them"), hits


def report(case: str | Path, do_surface: bool = False) -> int:
    case = Path(case)
    print(f"=== tank resonance: {case}")
    if is_lts(case):
        print("  REFUSED: this is an LTS (local-time-stepping) case. Its "
              "'time' axis is pseudo-time —")
        print("  runs/lts samples it at a dead-flat 10 s interval out to 2000 "
              "— and pseudo-time")
        print("  has no periods in it. NO RESULT.")
        return 2

    g = gravity(case)
    dom = domain(case)
    u = speed(case)
    L, h = dom["length_m"], dom["depth_m"]
    print(f"  tank  L = {L:.3f} m, still-water depth h = {h:.3f} m, "
          f"half-width {dom['half_width_m']:.3f} m")
    print(f"  flow  U = {u:.4f} m/s, g = {g:.4f} m/s^2 (from constant/g)")

    try:
        t, fp = pressure_history(case)
    except (FileNotFoundError, post.ForceHistoryError) as exc:
        print(f"  REFUSED: {exc}")
        return 2
    span = float(t[-1] - t[0])
    ft = span / (L / u)
    print(f"  force history: {len(t)} samples over {span:.2f} s "
          f"({ft:.2f} flow-throughs)")
    if ft < post.FLOW_THROUGH_FLOOR:
        # Not fatal here — a PERIOD is a timescale, not a mean, and a tank mode
        # is excited by the impulsive start rather than by a settled wake. But
        # it must be said out loud, because a domain the free stream has not
        # crossed still holds its initial condition and the amplitude below is
        # a startup amplitude.
        print(f"    NOTE: under {post.FLOW_THROUGH_FLOOR:g} flow-through. A "
              f"period may still be measurable, but no AMPLITUDE or mean from")
        print("    this record describes a settled flow, and none may be "
              "quoted as resistance.")

    preds = predictions(L, h, u, g)
    print()
    print("  candidate mechanisms (a period needs "
          f"{MIN_CYCLES:g} cycles of record to be seen at all):")
    for name, p in preds.items():
        T = p["period_s"]
        if not np.isfinite(T):
            print(f"     {name:34s} SWEPT OUT (c <= U: the stream outruns "
                  f"this wavelength, so it cannot stand in the tank)")
            continue
        cyc = span / T
        flag = "  " if cyc >= MIN_CYCLES else " *"
        lam = ("     -  " if not np.isfinite(p["wavelength_m"])
               else f"{p['wavelength_m']:7.2f}")
        print(f"   {flag} {name:34s} T = {T:6.2f} s  "
              f"lambda = {lam} m  ({cyc:.2f} cycles of this record)")
    print("     * = this record is too short to have shown it")

    print()
    fit = None
    try:
        fit = dominant_period(t, fp)
    except ResonanceError as exc:
        print(f"  MEASURED PERIOD (pressure_x): NO RESULT — {exc}")
    else:
        print(f"  MEASURED (pressure_x): T = {fit.period_s:.2f} s, "
              f"amplitude {fit.amplitude:.1f} N, "
              f"{fit.n_cycles:.2f} cycles, "
              f"{100*fit.explained_variance:.1f}% of the detrended variance")
        print(f"    method: {fit.method}")

        _v, hits = classify(fit.period_s, preds, span)
        print()
        for name, T, err, ok in sorted(hits, key=lambda q: q[2])[:8]:
            mark = ("MATCH " if (err <= MATCH_TOL and ok)
                    else ("      " if ok else "unseen"))
            tstr = "  swept" if not np.isfinite(T) else f"{T:6.2f}"
            estr = "      -" if not np.isfinite(err) else f"{100*err:+7.1f}%"
            print(f"    {mark} {name:34s} predicted {tstr} s  "
                  f"({estr} from measured)")

    # THE FREE SURFACE IS NOT DOWNSTREAM OF THE FORCE FIT. It used to be —
    # `return 2` on a refused force period skipped it entirely — and that is
    # backwards: the mode shape is INDEPENDENT evidence, and it is exactly the
    # case whose force history is too messy to name that most needs it.
    ms = None
    if do_surface:
        print()
        try:
            times, x, prof = surface_profiles(case)
            ms = mode_shape(times, x, prof, u, h, g)
        except ResonanceError as exc:
            print(f"  free surface: NO RESULT — {exc}")
        else:
            print(f"  free surface ({len(times)} snapshots, "
                  f"{times[0]:g}..{times[-1]:g} s):")
            print(f"    T = {ms.period_s:.2f} s "
                  f"({100*ms.explained_variance:.1f}% of variance)")
            print(f"    wavelength {ms.wavelength_m:.2f} m, "
                  f"tank-frame phase speed {ms.phase_speed_tank:+.3f} m/s "
                  f"(+ = upstream)")
            print(f"    intrinsic phase speed {ms.phase_speed_intrinsic:.3f} "
                  f"m/s vs {ms.dispersion_speed:.3f} m/s required of a free "
                  f"wave that long "
                  f"({100*(ms.phase_speed_intrinsic/ms.dispersion_speed-1):+.1f}%)")
            print(f"    c / U = {ms.phase_speed_intrinsic/u:.3f}  "
                  f"(2.000 would be exactly cg = U, the blocking condition)")
            print(f"    standing score {ms.standing_score:.2f} "
                  f"(1 = still-water standing wave; 0 = travelling)")
            print(f"    DOPPLER CHECK: lambda/(c-U) for the measured "
                  f"{ms.wavelength_m:.2f} m gives {ms.doppler_period:.2f} s "
                  f"against the fitted {ms.period_s:.2f} s "
                  f"({100*(ms.period_s/ms.doppler_period-1):+.1f}%)")

    print()
    if fit is None and ms is None:
        print("  VERDICT: NO RESULT — nothing here can be named")
        return 2
    # The free surface OUTRANKS the force history when both speak. The force
    # is a single scalar integrated over the hull, so several mechanisms land
    # on top of each other in it; the mode shape is resolved in x, so it can
    # measure the WAVELENGTH — and the wavelength is what tells a tank mode
    # from anything the ship is doing.
    verdict, _hits = classify(ms.period_s if ms is not None else fit.period_s,
                              preds, span)
    if ms is not None and ms.standing_score < 0.5 and "STILL-WATER" in verdict:
        verdict = (f"NOT A STILL-WATER SEICHE (period near {verdict}, but the "
                   f"mode TRAVELS)")
    print(f"  VERDICT: {verdict}")
    if verdict.startswith("DOPPLER"):
        print("    A wave whose WAVELENGTH the tank selects, running upstream "
              "against the stream")
        print("    and reflecting off the ends. It is a DOMAIN defect: the "
              "energy cannot leave a")
        print("    box with reflecting boundaries. The period is NOT "
              "2L/sqrt(gh) — it carries the")
        print("    Doppler shift, so it moves with speed — and the fix is "
              "ABSORPTION (a relaxation")
        print("    zone or a coarsened beach), not deepening the tank to move "
              "a still-water mode.")
    return 0 if verdict != "UNEXPLAINED" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", nargs="+")
    ap.add_argument("--surface", action="store_true",
                    help="also fit the free-surface mode shape from the saved "
                         "alpha.water fields (needs V and Cx; see "
                         "surface_profiles)")
    args = ap.parse_args()
    rc = 0
    for c in args.case:
        try:
            rc = max(rc, report(c, args.surface))
        except ResonanceError as exc:
            print(f"=== tank resonance: {c}")
            print(f"  REFUSED: {exc}")
            rc = max(rc, 2)
        print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
