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
    bm: float             # m
    awp: float            # m^2 waterplane
    lcf: float            # m from transom
    b_wl_max: float
    cb: float             # block coefficient
    cp: float             # prismatic
    wetted: float         # m^2
    freeboard_min: float  # m


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
    bmax = 2.0 * float(b.max())
    lwl_eff = float(x[a > 1e-6].max() - x[a > 1e-6].min()) if (a > 1e-6).any() else 1e-9
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
        awp=awp, lcf=lcf, b_wl_max=bmax, cb=cb, cp=cp,
        wetted=hull.wetted_surface(wl), freeboard_min=fb,
    )


def gm(state: HydroState, kg: float) -> float:
    """Transverse metacentric height. kg measured above keel plane."""
    return state.kb + state.bm - kg


def solve_to_displacement(hull: Hull, target_kg_mass: float,
                          rho: float = RHO_WATER,
                          tol: float = 1e-3) -> tuple[HydroState, float]:
    """Find the waterline at which displacement matches target mass (bisection).

    Returns (state, wl). wl < 0 means floating higher than design WL.
    Raises if the hull cannot carry the mass with positive freeboard.
    """
    z_lo = float(hull.z_keel.min()) * 0.98          # nearly dry
    z_hi = float(hull.z_sheer.min()) - 0.02          # just below deck edge
    m_hi = solve(hull, rho, z_hi).disp_kg
    if m_hi < target_kg_mass:
        raise ValueError(
            f"hull swamps: max buoyant mass {m_hi:.0f} kg < target {target_kg_mass:.0f} kg")
    lo, hi = z_lo, z_hi
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
    return solve(hull, rho, 0.5 * (lo + hi)), 0.5 * (lo + hi)
