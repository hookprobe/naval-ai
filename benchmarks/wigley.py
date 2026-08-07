"""Wigley hull benchmark — the analytic anchor for the Michell tier (Gate 1).

Wigley parabolic hull: y(x,z) = (B/2)(1 - (2x/L)^2)(1 - (z/T)^2),
standard proportions L/B = 10, B/T = 1.6. Gate 1 asserts:
  - magnitude band at the last hump (Fn ~ 0.5)
  - presence of the hump/hollow oscillation in Fn 0.2-0.45
  - grid convergence < 2% on refinement
  - per-point agreement with `rw_analytic`, the CLOSED-FORM Michell solution

WHY THIS HULL HAS A CLOSED FORM, AND WHY THAT MATTERS (gap E2).
Michell's amplitude integral is a double integral of dy/dx over the centreplane.
The Wigley offset is a PRODUCT of a function of x and a function of z, so
dy/dx is too, and the double integral FACTORS into two elementary integrals
that both have antiderivatives. `rw_analytic` evaluates them symbolically and
leaves only the one-dimensional theta quadrature, which converges to 1e-10.
Nothing in it touches `wigley_offsets`, `michell_rw`, the x-z grid or the
trapezoid rule, so comparing `cw_curve` against it measures OUR numerics
against exact mathematics rather than against a frozen copy of themselves.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.geometry import G
from navalai.resistance import michell_rw

# THE PROPORTIONS LIVE HERE, ONCE. `wigley_offsets`, `wetted_surface`,
# `displacement_exact` and `rw_analytic` all derive B and T from this, because
# three of them used to carry their own `B = L / 10.0; T = B / 1.6` and a hull
# whose beam disagreed with its own displacement is exactly the defect class
# `limits.py` exists to prevent, one floor down in the stack.
L_OVER_B = 10.0
B_OVER_T = 1.6


def proportions(L: float = 10.0) -> tuple[float, float]:
    """(B, T) for the standard Wigley model at length L."""
    B = L / L_OVER_B
    return B, B / B_OVER_T


def displacement_exact(L: float = 10.0) -> float:
    """Displaced volume [m^3] of the Wigley hull to z = 0 — EXACTLY 4LBT/9.

    Both sides. Int_-L/2^L/2 (1-(2x/L)^2) dx = 2L/3 and Int_-T^0 (1-(z/T)^2) dz
    = 2T/3, so 2 * (B/2) * (2L/3) * (2T/3) = 4LBT/9. This is the one number in
    the whole benchmark that carries no discretisation at all.

    NOTE (flagged, not silently duplicated): `tests/test_cfd_reference_parity.py`
    restates `4 * L * B * T / 9` inline against `data/benchmark_geom/
    CHECKSUMS.json`. That is a second declaration of this number and should
    import this function when that file is next edited; it is outside this
    change's file ownership.
    """
    B, T = proportions(L)
    return 4.0 * L * B * T / 9.0


def wigley_offsets(L: float = 10.0, nx: int = 121, nz: int = 25):
    B, T = proportions(L)
    xs = np.linspace(-L / 2, L / 2, nx)
    # cluster z quadratically toward the free surface: the Michell kernel
    # exp(k0 sec^2(theta) z) concentrates in a thin surface sliver at large theta
    s = np.linspace(1.0, 0.0, nz, endpoint=False)
    zs = -T * s**2
    zs = np.sort(zs)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    Y = (B / 2) * (1 - (2 * X / L) ** 2) * (1 - (Z / T) ** 2)
    return xs, zs, np.maximum(Y, 0.0), B, T


def wetted_surface(L: float = 10.0, n: int = 400) -> float:
    """Numeric wetted surface of the Wigley hull (both sides)."""
    B, T = proportions(L)
    xs = np.linspace(-L / 2, L / 2, n)
    zs = np.linspace(-T, 0.0, n)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    Y = (B / 2) * (1 - (2 * X / L) ** 2) * (1 - (Z / T) ** 2)
    dydx = np.gradient(Y, xs, axis=0)
    dydz = np.gradient(Y, zs, axis=1)
    dA = np.sqrt(1.0 + dydx**2 + dydz**2)
    return 2.0 * float(np.trapezoid(np.trapezoid(dA, zs, axis=1), xs))


def cw_curve(fns: np.ndarray, L: float = 10.0, nx: int = 121, nz: int = 25,
             rho: float = 1000.0):
    xs, zs, Y, _B, _T = wigley_offsets(L, nx, nz)
    S = wetted_surface(L)
    cws = np.empty_like(fns)
    for i, fn in enumerate(fns):
        u = fn * np.sqrt(G * L)
        rw = michell_rw(xs, zs, Y, u, rho)
        cws[i] = rw / (0.5 * rho * S * u**2)
    return cws, S


# ---------------------------------------------------------------------------
# THE CLOSED-FORM MICHELL SOLUTION — the independent anchor (gap E2)
# ---------------------------------------------------------------------------
#
# Michell, in the theta form this project ships (see navalai/resistance.py):
#
#     R_w = 4 rho g^2 / (pi U^2) * Int_0^{pi/2} |I(theta)|^2 sec^3(theta) dtheta
#     I   = Int_{-T}^{0} Int_{-L/2}^{L/2} (dy/dx) e^{k sec^2 z} e^{i k sec x} dx dz
#
# with k = g/U^2. For the Wigley hull y = (B/2) f(x) h(z) with
# f(x) = 1 - (2x/L)^2 and h(z) = 1 - (z/T)^2, so dy/dx = (B/2) f'(x) h(z) and
# I(theta) = (B/2) * Fx(theta) * Fz(theta):
#
#   Fx = Int_{-L/2}^{L/2} (-8x/L^2) e^{i a x} dx,          a = k sec
#      = -4i [ sin(P)/P^2 - cos(P)/P ],                    P = aL/2
#        (odd integrand: the cosine half vanishes, and Int x sin(ax) dx is
#         elementary — this is where the x-quadrature disappears)
#     => |Fx|^2 = 16 [ sin(P)/P^2 - cos(P)/P ]^2
#
#   Fz = Int_{-T}^{0} (1 - (z/T)^2) e^{b z} dz,            b = k sec^2
#      = T [ (1 - e^-B)/B - (2 - e^-B (B^2 + 2B + 2))/B^3 ],   B = bT
#        (real and positive; from Int_0^1 e^-Bu du and Int_0^1 u^2 e^-Bu du)
#
# so |I|^2 = (B/2)^2 * 16 [sin P/P^2 - cos P/P]^2 * Fz^2 and only the theta
# integral is left. Its integrand decays as sec^-3 (Fz^2 ~ sec^-4, |Fx|^2 ~
# sec^-2, times sec^3), so it converges; substituting t = tan(theta) puts it
# on [0, inf) with dtheta = dt/(1+t^2).
#
# HONEST SCOPE. This is exact for MICHELL'S INTEGRAL. It validates the
# offsets, the x-z grid, the trapezoid rule and the theta substitution in
# `michell_rw` against mathematics — which is what gap E2 asked for, since the
# previous reference was our own output. It does NOT validate thin-ship theory
# against a towing tank: Michell is known to overpredict the humps by tens of
# percent, and no tank data for this hull is transcribed anywhere in this
# repository. That second anchor is still owed and is NOT claimed here.


def rw_analytic(fn: float, L: float = 10.0, rho: float = 1000.0,
                t_max: float = 60.0, n: int = 200_001,
                n_tail: int = 40_001) -> float:
    """Wigley Michell wave resistance [N] in closed form, up to one quadrature.

    The x and z integrals are evaluated symbolically (see the derivation
    above); the remaining theta integral is done by composite trapezoid on
    t = tan(theta), fine enough on [0, `t_max`] to resolve the interference
    oscillation (its period in t is 2 pi / (k L / 2) = 4 pi Fn^2 L / L, worst
    case ~0.5 at Fn 0.2, sampled ~1600 times per period) and log-spaced on the
    sec^-3 tail. MEASURED: doubling both counts moves the answer by 1e-10
    relative, and scipy.integrate.quad on the same integrand agrees to 1e-6.
    """
    if fn <= 0.0:
        return 0.0
    B, T = proportions(L)
    u = fn * math.sqrt(G * L)
    k = G / u**2

    def integrand(t: np.ndarray) -> np.ndarray:
        sec = np.sqrt(1.0 + t * t)
        p = k * sec * L / 2.0
        beta = k * sec * sec * T
        fx2 = 16.0 * (np.sin(p) / p**2 - np.cos(p) / p) ** 2
        e = np.exp(-beta)
        fz = T * ((1.0 - e) / beta
                  - (2.0 - e * (beta * beta + 2.0 * beta + 2.0)) / beta**3)
        return (B / 2.0) ** 2 * fx2 * fz * fz * sec**3 / (1.0 + t * t)

    t_core = np.linspace(0.0, t_max, n)
    t_tail = np.geomspace(t_max, 1.0e6, n_tail)
    total = (float(np.trapezoid(integrand(t_core), t_core))
             + float(np.trapezoid(integrand(t_tail), t_tail)))
    return 4.0 * rho * G**2 / (math.pi * u**2) * total


def cw_analytic(fns, L: float = 10.0, rho: float = 1000.0) -> np.ndarray:
    """Closed-form Cw on the SAME non-dimensionalisation as `cw_curve`.

    The wetted surface in the denominator is this module's numeric `S` on both
    sides of any comparison, so it cancels: the physics content of the anchor
    is `rw_analytic`, a force, which involves no geometry of ours at all.
    """
    S = wetted_surface(L)
    fns = np.asarray(fns, dtype=float)
    out = np.empty_like(fns)
    for i, fn in enumerate(fns):
        u = fn * math.sqrt(G * L)
        out[i] = rw_analytic(float(fn), L, rho) / (0.5 * rho * S * u**2)
    return out


# THE INDEPENDENT ANCHOR, FROZEN. L = 10 m, rho = 1000 kg/m^3.
#
# Frozen as literals rather than computed at import, deliberately: a reference
# that recomputes itself from a function moves whenever that function moves,
# which is the disease `REFERENCE_CW` had. `tests/test_phase1.py` recomputes
# `rw_analytic` and pins it against these to 1e-6, so the function is checked
# against the literal and the literal is checked against nothing — as it must
# be for an anchor.
ANALYTIC_RW_N = {
    0.20: 2.590152e+01,
    0.25: 4.851266e+01,
    0.30: 1.406244e+02,     # hump
    0.35: 1.115295e+02,     # hollow
    0.40: 3.191342e+02,
    0.45: 6.137404e+02,
    0.50: 8.239110e+02,
}

# MEASURED 2026-08-07, production grid (nx=121, nz=25) against the closed form,
# over Fn 0.20..0.50:  -2.113% (worst, at Fn 0.20) .. -0.861% (at Fn 0.50).
# The bar is 3%: real margin, and far tighter than any tolerance a magnitude
# band could express. The sign is consistent — the discrete x-z quadrature
# truncates a thin surface sliver (`wigley_offsets` stops at z = -T/nz^2, not
# z = 0) and under-resolves the bow/stern shoulders, so it UNDER-predicts.
ANALYTIC_TOL_PRODUCTION = 0.03
# Same comparison for the converged grid (nx=321, nz=65): -0.773% .. -0.240%.
ANALYTIC_TOL_CONVERGED = 0.01


# ---------------------------------------------------------------------------
# REGRESSION PIN — NOT the anchor. Read the paragraph before quoting it.
#
# These values are OUR OWN Michell integral on a CONVERGED grid (nx=321,
# nz=65). Gap E2's finding was that this dict was the only "reference" in the
# repository and Gate 1's per-point test compared our output against it, so
# the gate measured SELF-CONSISTENCY: any coherent change to the integral, the
# offsets or the quadrature that was re-frozen here would have passed forever.
#
# It is kept because it still has a job — `navalai.flywheel.benchmark_integrity`
# uses it to detect that the physics moved under a retrain, which is a drift
# question, not a correctness question — but it is no longer what Gate 1's
# correctness test compares against. `ANALYTIC_RW_N` is, and
# `test_the_regression_pin_still_agrees_with_the_closed_form` ties this dict to
# the closed form so it cannot drift back into being self-referential.
#
# Wigley: L=10 m, B=L/10, T=B/1.6, S=14.87905 m^2 (both sides, to z=0).
REFERENCE_CW = {
    0.20: 8.807045e-04,
    0.25: 1.061372e-03,
    0.30: 2.133448e-03,     # hump
    0.35: 1.244703e-03,     # hollow
    0.40: 2.721631e-03,
    0.45: 4.139621e-03,
    0.50: 4.505337e-03,
}
REFERENCE_GRID = dict(nx=321, nz=65)
REFERENCE_S = 14.87905


if __name__ == "__main__":
    fns = np.linspace(0.15, 0.55, 33)
    cws, S = cw_curve(fns)
    exact = cw_analytic(fns)
    print(f"# Wigley L=10 m, S={S:.4f} m^2, displacement {displacement_exact():.6f} m^3")
    print(f"# {'Fn':>6} {'Cw (121x25)':>14} {'Cw (closed form)':>18} {'err':>9}")
    for fn, cw, ex in zip(fns, cws, exact):
        print(f"  {fn:6.3f} {cw:14.6e} {ex:18.6e} {100 * (cw / ex - 1):8.3f}%")
