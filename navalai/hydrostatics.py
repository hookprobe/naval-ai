"""L1 hydrostatics: displacement, centres, GM, and the draft solve.

Classic naval-architecture integrals over the station arrays (Simpson via
trapezoid on a fine grid). Everything here is deterministic and O(ms).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import G, RHO_WATER, Hull


@dataclass(frozen=True)
class HydroState:
    draft: float          # m, waterline used (>=0 means WL at z = T_design - draft shift)
    volume: float         # m^3
    disp_kg: float
    lcb: float            # m from transom
    kb: float             # m above keel (baseline = keel at midship, z=-T)
    bm: float             # m, transverse
    bm_l: float           # m, longitudinal (about the transverse axis at F)
    awp: float            # m^2 waterplane
    lcf: float            # m from transom
    b_wl_max: float
    # The waterline length the hull ACTUALLY floats at, not the LWL parameter.
    # It was computed inside solve() as a local, used for cb/cp, and thrown
    # away — so the only length available to a caller wanting LCB as a
    # percentage was the design parameter, which is a different number at any
    # floated waterline. Gap B8 needs the floated one: LCB is meaningful only
    # relative to the midpoint of the waterline it was integrated over.
    lwl_eff: float
    # x of the aft end of the immersed waterline. The transom does not sit at
    # x = 0 once rocker lifts it clear, so the midships station is
    # x_wl_aft + lwl_eff/2 and NOT lwl_eff/2 — an error of half the rocker
    # overhang, straight onto the quantity B8 constrains.
    x_wl_aft: float
    cb: float             # block coefficient
    cp: float             # prismatic
    wetted: float         # m^2
    freeboard_min: float  # m

    @property
    def lcb_pct_lwl(self) -> float:
        """LCB relative to midships, as a percentage of the floated waterline
        length. NEGATIVE = aft of midships, the naval-architecture convention.

        Derived here rather than at the call site so the reference station is
        defined once — see `limits.LCB_BAND_PCT_LWL` for the band it is judged
        against and gap B8 for why it is judged at all.
        """
        mid = self.x_wl_aft + 0.5 * self.lwl_eff
        return 100.0 * (self.lcb - mid) / max(self.lwl_eff, 1e-9)


def _waterline_ends(x, a, wet) -> tuple[float, float]:
    """(x_wl_aft, lwl_eff), with the ends INTERPOLATED, not snapped to a station.

    THE BUG THIS REPLACES. `lwl_eff` was the span of WET STATIONS:

        x_wl_aft = float(x[wet].min())
        lwl_eff  = float(x[wet].max() - x[wet].min())

    The waterline does not end at a station; it ends between the last wet one
    and the first dry one. Snapping to the last wet station therefore truncates
    by up to one spacing, and -- this is what makes it a defect rather than
    noise -- it can only ever be too SHORT. The error never averages out over a
    population, so every hull in the batch is biased the same way.

    MEASURED 2026-08-12 on the seed-0 batch, hull 0 at x_mb = 0.5123 (chosen to
    fall BETWEEN stations at the shipped n_stations = 41), against a converged
    reference at n_stations = 2561:

        n_stations     lwl_eff        cb         cp
                41   14.639769  0.370325   0.708813
                81   14.827458  0.365835   0.700272
               161   14.921303  0.363595   0.695983
               641   14.991687  0.361914   0.692767
              1281   15.003417  0.361634   0.692230

    True LWL is 15.0151 m and the station spacing is 0.375379 m, so the shipped
    grid was short by 0.363648 m = 0.969 of ONE station -- an off-by-one-cell
    truncation, converging at observed order p = 1.00. It propagates straight
    into the two coefficients that divide by it: `cb` and `cp` were both
    inflated 2.4% (Richardson-extrapolated cp 0.691693 against 0.708813).

    Volume was never the problem -- it converges to 0.087% over the same range,
    and `awp` to 0.12%. Nor was it the max-beam station: `Am` is CONSTANT at
    0.603408 across 41..1281, which refutes the first explanation offered for
    this (that the coarse grid was missing the true midship section). The error
    is entirely in the LENGTH.

    Found while sweeping x_mb for station-period aliasing. That aliasing is real
    -- a sawtooth of period 1/40 in x_mb that collapses ~60x per station
    doubling -- but it is small (264 ppm on wetted area at n=41) and reaches
    `wh_per_nm` at only ~0.01% above the noise floor. The bias found alongside
    it is 200x larger and has nothing to do with x_mb.
    """
    if not wet.any():
        return 0.0, 1e-9
    idx = np.flatnonzero(wet)
    i0, i1 = int(idx[0]), int(idx[-1])
    # Forward end: a falls from a[i1] to a[i1+1] <= 1e-6. Linear in the section
    # area, so the estimate is exact for a wedge and second-order otherwise.
    x_fwd = float(x[i1])
    if i1 + 1 < len(x):
        da = float(a[i1] - a[i1 + 1])
        if da > 0.0:
            x_fwd += float(x[i1 + 1] - x[i1]) * float(a[i1]) / da
    # Aft end: usually the transom, which is wet AT x[0] -- there is no dry
    # station behind it and the waterline genuinely ends there. Only a hull that
    # runs dry aft of its first station gets an interpolated aft end.
    x_aft = float(x[i0])
    if i0 - 1 >= 0:
        da = float(a[i0] - a[i0 - 1])
        if da > 0.0:
            x_aft -= float(x[i0] - x[i0 - 1]) * float(a[i0]) / da
    return x_aft, max(x_fwd - x_aft, 1e-9)


def solve(hull: Hull, rho: float = RHO_WATER, wl: float = 0.0) -> HydroState:
    """Hydrostatics at a given waterline height wl (0 = design WL)."""
    a, b, zc = hull.hydro_arrays(wl)
    x = hull.x
    vol = 2.0 * float(np.trapezoid(a, x))
    if vol <= 1e-9:
        raise ValueError("hull has no displacement at this waterline")
    lcb = 2.0 * float(np.trapezoid(a * x, x)) / vol
    # KB: volume-weighted z-centroid, referenced to keel plane z=-T
    zb = 2.0 * float(np.trapezoid(a * zc, x)) / vol
    t_design = -float(hull.z_keel.min())
    kb = zb + t_design
    awp = 2.0 * float(np.trapezoid(b, x))
    lcf = 2.0 * float(np.trapezoid(b * x, x)) / max(awp, 1e-12)
    ixx = (2.0 / 3.0) * float(np.trapezoid(b**3, x))
    bm = ixx / vol
    # Longitudinal waterplane inertia about the TRANSVERSE axis through the
    # centre of flotation (parallel-axis, so it must use lcf and not midships).
    # Without this there is no GM_L, and without GM_L `weights.trim_angle_deg`
    # has no denominator — which is why the trim check could not exist and an
    # arrangement could move 500 kg aft with no consequence anywhere.
    i_l = 2.0 * float(np.trapezoid(b * (x - lcf) ** 2, x))
    bm_l = i_l / vol
    bmax = 2.0 * float(b.max())
    wet = a > 1e-6
    x_wl_aft, lwl_eff = _waterline_ends(x, a, wet)
    # Immersion is measured from the KEEL (z = -t_design) up to the waterline
    # plane (z = wl), so it is wl + t_design. The sign was inverted, which is
    # exact only at wl = 0 — which is why every test passed. MEASURED on the
    # mid hull: at wl = -0.40 the volume collapses to 1.088 m^3 (barely
    # immersed) while draft was reported as 0.95 m, LARGER than the 0.55 m at
    # wl = 0. It propagates: cb = vol/(lwl*bmax*t_mean) was then ~0.11 instead
    # of ~0.34, and evaluate() feeds that cb to form_factor(), so the friction
    # form factor k came out ~0.03 instead of ~0.29 — a large error in
    # frictional resistance at any off-design waterline.
    t_mean = t_design + wl
    cb = vol / max(lwl_eff * bmax * t_mean, 1e-12)
    amax = float(a.max()) * 2.0
    cp = vol / max(amax * lwl_eff, 1e-12)
    fb = float((hull.z_sheer - wl).min())
    return HydroState(
        draft=t_mean, volume=vol, disp_kg=rho * vol, lcb=lcb, kb=kb, bm=bm,
        bm_l=bm_l,
        awp=awp, lcf=lcf, b_wl_max=bmax, lwl_eff=lwl_eff, x_wl_aft=x_wl_aft,
        cb=cb, cp=cp,
        wetted=hull.wetted_surface(wl), freeboard_min=fb,
    )


def gm(state: HydroState, kg: float) -> float:
    """Transverse metacentric height. kg measured above keel plane."""
    return state.kb + state.bm - kg


def gm_long(state: HydroState, kg: float) -> float:
    """Longitudinal metacentric height [m]. kg measured above keel plane.

    Typically ~Lwl in magnitude, i.e. two orders above transverse GM, which is
    exactly why trim is stiff and small LCG errors show up as tenths of a
    degree rather than a capsize.
    """
    return state.kb + state.bm_l - kg


def solve_to_displacement(hull: Hull, target_kg_mass: float,
                          rho: float = RHO_WATER,
                          tol: float = 1e-3) -> tuple[HydroState, float]:
    """Find the waterline at which displacement matches target mass (bisection).

    Returns (state, wl). wl < 0 means floating higher than design WL.
    Raises if the hull cannot carry the mass with positive freeboard, AND if it
    cannot float that lightly, AND if the bisection does not close on `tol`.

    BOTH ENDS OF THE BRACKET ARE VERIFIED NOW (gap E14). Only `z_hi` was, and
    the post-loop line returned `solve(hull, rho, 0.5*(lo+hi))` — the midpoint
    after 80 iterations — with the SAME shape as the converged return, so no
    caller could tell them apart. The mechanism was never the iteration count:
    `z_lo = z_keel.min() * 0.98` is commented "nearly dry" and is not dry.

    MEASURED 2026-08-12 on `tests/test_phase0.mid_params`, exactly reproducing
    the register's figure:

        target kg   returned disp kg      error
              1.0             4.134    +313.4%
             10.0            10.003      +0.0%
            100.0            99.960      -0.0%
           2000.0          1999.393      -0.0%

    The hull still displaces 4.134 kg at `z_lo`, so any target below that
    cannot be bracketed, `hi` walks down to `z_lo`, and the loop hands back a
    waterline whose displacement is four times what was asked for — an
    unconverged answer returned as an answer, which is defect class 1. It is
    now a refusal, symmetric with the "hull swamps" one above it, and it is a
    ValueError because `evaluate()` already catches exactly that and turns it
    into a `floatation: ...` violation string (navalai/evaluate.py:454-460).
    A `converged=` flag on `HydroState` was considered and rejected: a flag
    nobody is forced to read is the same defect with a field added.
    """
    z_lo = float(hull.z_keel.min()) * 0.98          # nearly dry, NOT dry
    z_hi = float(hull.z_sheer.min()) - 0.02          # just below deck edge
    m_hi = solve(hull, rho, z_hi).disp_kg
    if m_hi < target_kg_mass:
        raise ValueError(
            f"hull swamps: max buoyant mass {m_hi:.0f} kg < target {target_kg_mass:.0f} kg")
    # The LOW end. `solve` raises when the waterline is below the keel, and
    # that is the GOOD case: it means the bracket really does reach zero
    # displacement and any positive target is reachable.
    try:
        m_lo = solve(hull, rho, z_lo).disp_kg
    except ValueError:
        m_lo = 0.0
    if m_lo > target_kg_mass:
        raise ValueError(
            f"hull floats too high: min buoyant mass {m_lo:.3f} kg at the "
            f"lowest bracketable waterline {z_lo:.4f} m > target "
            f"{target_kg_mass:.3f} kg. The bracket does not contain the "
            f"answer, so bisection cannot find it and the midpoint it would "
            f"return is not a flotation.")
    lo, hi = z_lo, z_hi
    m = float("nan")
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        try:
            m = solve(hull, rho, mid).disp_kg
        except ValueError:
            lo = mid
            continue
        if abs(m - target_kg_mass) < tol * target_kg_mass:
            return solve(hull, rho, mid), mid
        if m < target_kg_mass:
            lo = mid
        else:
            hi = mid
    raise ValueError(
        f"solve_to_displacement did not converge: {m:.3f} kg against target "
        f"{target_kg_mass:.3f} kg after 80 bisections on [{z_lo:.4f}, "
        f"{z_hi:.4f}] m, still {abs(m - target_kg_mass) / max(target_kg_mass, 1e-9):.1%} "
        f"out against a {tol:.1%} tolerance. The midpoint is not the answer "
        f"and must not be returned as one.")
