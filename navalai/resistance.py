"""L1 resistance: Michell thin-ship wave resistance + ITTC-57 friction.

Michell integral in the theta form (Tuck 1987 lineage):

    R_w = (4 rho g^2) / (pi U^2) * Int_0^{pi/2} |I(theta)|^2 sec^3(theta) dtheta
    I(theta) = Int_S (dy/dx)(x,z) * exp(k0 sec^2(theta) z)
                                  * exp(i k0 sec(theta) x) dz dx,   k0 = g/U^2

Validity: slender hulls, low-to-moderate Froude; known to overpredict at the
humps by tens of percent (the literature's standing caveat) — which is why
every number leaving this module carries tier='L1' and an uncertainty band.
Friction: ITTC-1957 line with a Watanabe-style form factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .geometry import G, Hull

NU_WATER = 1.14e-6  # kinematic viscosity, ~15 C fresh water [m^2/s]


# MICHELL'S VALIDITY ENVELOPE, ENFORCED.
# The thin-ship integral assumes a slender hull at low-to-moderate Froude
# number with no dynamic lift. MEASURED: a "3 t, 6 m, 25 kn tender" mission was
# evaluated at **Fn 1.09 / Fn_vol 3.42** -- deep planing -- and returned
# Rw 498 N against Rf 3832 N, i.e. "friction-dominated at 25 knots", with a
# PASS on every requirement. There is no planing lift, no dynamic trim, no
# spray and no appendage drag in this model; at that speed the answer is not
# approximate, it is about a different physical regime.
#
# 0.45 is the conventional upper limit for displacement/thin-ship methods
# (transom immersion and dynamic effects take over above it). Above the bar the
# result is still returned -- refusing outright would hide the number from a
# designer who wants to see it -- but `valid` is False and the tier reads
# L1-INVALID, so nothing downstream can badge it as a validated L1 quantity.
# The honest fix beyond this is a Savitsky planing model; that is gap B7's
# second half and is not yet built.
FN_MICHELL_MAX = 0.45


@dataclass(frozen=True)
class ResistanceResult:
    speed: float      # m/s
    fn: float
    rw: float         # wave resistance [N]
    rf: float         # frictional (with form factor) [N]
    total: float      # N
    cw: float         # wave resistance coeff on 0.5 rho S U^2
    cf: float
    uncertainty: float  # one-sigma on total [N] — honest L1 band (~25%)
    valid: bool = True          # False above FN_MICHELL_MAX
    regime: str = "displacement"


def michell_rw(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray, speed: float,
               rho: float = 1000.0, n_theta: int = 220) -> float:
    """Wave resistance from a half-breadth grid Y[x, z] below the waterline."""
    if speed <= 0.05:
        return 0.0
    k0 = G / speed**2
    dydx = np.gradient(Y, xs, axis=0)
    # theta grid dense near pi/2 (integrand peaky), via substitution theta = pi/2 * s^0.7
    s = np.linspace(1e-4, 1.0, n_theta) ** 0.7
    thetas = 0.5 * math.pi * s * 0.998
    sec = 1.0 / np.cos(thetas)
    vals = np.empty(n_theta)
    for i, (th, sc) in enumerate(zip(thetas, sec)):
        # zs must be <= 0 (below the actual free surface); clamp defensively
        depth = np.exp(np.minimum(k0 * sc**2 * zs, 0.0))[None, :]
        phase = k0 * sc * xs                               # (nx,)
        gz = (dydx * depth)                                # (nx, nz)
        fx = np.trapezoid(gz, zs, axis=1)                  # integrate z
        re = np.trapezoid(fx * np.cos(phase), xs)
        im = np.trapezoid(fx * np.sin(phase), xs)
        vals[i] = (re**2 + im**2) * sc**3
    integral = np.trapezoid(vals, thetas)
    return float(4.0 * rho * G**2 / (math.pi * speed**2) * integral)


def ittc57_cf(speed: float, lwl: float, nu: float = NU_WATER) -> float:
    re = max(speed * lwl / nu, 1e4)
    return 0.075 / (math.log10(re) - 2.0) ** 2


def form_factor(cb: float, lwl: float, beam: float, t: float) -> float:
    """Watanabe estimate; clamped to a sane band for small craft."""
    k = -0.095 + 25.6 * cb / ((lwl / beam) ** 2 * math.sqrt(beam / t))
    return float(np.clip(k, 0.0, 0.45))


def total_resistance(hull: Hull, speed: float, wetted: float, cb: float,
                     rho: float = 1000.0, wl: float = 0.0,
                     nz: int = 14) -> ResistanceResult:
    xs, zs, Y = hull.offsets_grid(nz=nz, wl=wl)
    # Michell frame: free surface at z=0 — shift the grid by the floated WL
    rw = michell_rw(xs, zs - wl, Y, speed, rho)
    lwl = float(hull.x[-1])
    cf = ittc57_cf(speed, lwl)
    k = form_factor(cb, lwl, 2.0 * float(hull.y_chine.max()), -float(hull.z_keel.min()))
    q = 0.5 * rho * wetted * speed**2
    rf = (1.0 + k) * cf * q
    total = rw + rf
    fn = speed / math.sqrt(G * lwl)
    cw = rw / max(q, 1e-9)
    # honest L1 band: Michell hump overprediction + form-factor scatter
    sigma = 0.25 * rw + 0.10 * rf
    valid = fn <= FN_MICHELL_MAX
    if not valid:
        # The band is meaningless outside the model's regime; say so with a
        # sigma the size of the answer rather than a comfortable 25%.
        sigma = max(sigma, total)
    return ResistanceResult(speed, fn, rw, rf, total, cw, cf, sigma,
                            valid=valid,
                            regime="displacement" if valid else "planing")
