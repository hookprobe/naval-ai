"""Wigley hull benchmark — the analytic anchor for the Michell tier (Gate 1).

Wigley parabolic hull: y(x,z) = (B/2)(1 - (2x/L)^2)(1 - (z/T)^2),
standard proportions L/B = 10, B/T = 1.6. The Michell-integral Cw curve for
this hull is the classic validation case (Tuck's computations; ITTC/tow-tank
data from Shearer et al.). Gate 1 asserts:
  - magnitude band at the last hump (Fn ~ 0.5)
  - presence of the hump/hollow oscillation in Fn 0.2-0.45
  - grid convergence < 2% on refinement
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.geometry import G
from navalai.resistance import michell_rw


def wigley_offsets(L: float = 10.0, nx: int = 121, nz: int = 25):
    B = L / 10.0
    T = B / 1.6
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
    B = L / 10.0
    T = B / 1.6
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


if __name__ == "__main__":
    fns = np.linspace(0.15, 0.55, 33)
    cws, S = cw_curve(fns)
    print(f"# Wigley L=10 m, S={S:.2f} m^2  (Michell integral, theta form)")
    for fn, cw in zip(fns, cws):
        print(f"Fn={fn:.3f}  Cw={cw:.4e}")


# ---------------------------------------------------------------------------
# REFERENCE CURVE — the thing Gate 1 always claimed to check and never did.
#
# BuildPlan Gate 1's bar is "Wigley wave resistance matches the analytic/tank
# curve within published Michell error bars". The test asserted a MAGNITUDE
# BAND (8e-4 < Cw(0.5) < 5e-3) plus the presence of >=2 sign changes. No
# reference curve existed anywhere in the repo and no per-point comparison was
# made, so the anchor was not anchored: any function of roughly the right size
# with a couple of wiggles would have passed.
#
# These values are OUR OWN Michell integral evaluated on a CONVERGED grid
# (nx=321, nz=65) — not an external dataset. That makes this a GRID-CONVERGENCE
# and REGRESSION anchor, not an independent validation, and it must not be
# described as the latter. Its job is to catch a change in the integral, the
# offsets or the quadrature. The independent check on the integral itself is
# the exact separable solution, which agrees to -0.86..-2.11%.
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
