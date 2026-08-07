"""Write the analytic Wigley hull as a watertight STL for CFD.

WHY THIS EXISTS. Across six KCS runs the viscous drag came out right
(1.15-1.22x ITTC-57) while the pressure drag was 3-6x the expected wave+form
value and GREW with time, independent of mesh, tank depth, run-out length,
layers, solver settings and time-stepping scheme. Every hypothesis tested so
far (convergence, boundary layer, wave reflection, LTS) has been eliminated by
measurement.

The Wigley hull separates the two remaining explanations, because it has a
CLOSED-FORM answer and none of KCS's features:

    Y(x,z) = (B/2) (1 - (2x/L)^2) (1 - (z/T)^2)

no transom, no bulb, no bulbous stem, no appendages — just a parabolic thin
ship. `benchmarks/wigley.py` computes its Michell wave resistance, and that
integral has been verified to -0.86..-2.11% against an exact separable
solution, so we know the target.

  - CFD ~4x Michell here  => the wave-resistance MACHINERY is broken, and the
                             KCS geometry was never the issue.
  - CFD ~ Michell here    => the machinery is sound and the defect is
                             KCS-specific; prime suspect is the transom, which
                             at Fn 0.26 should ventilate (run dry) and which
                             produces exactly this signature — a growing
                             low-pressure base region — if VOF keeps it wetted.

Michell over-predicts at the humps by tens of percent (its standing caveat), so
agreement to ~30% is a pass here and 4x is not.

The CFD hull is wall-sided above z=0 so it has freeboard; the analytic form is
used only below the waterline, which is all Michell integrates.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.wigley import wetted_surface


def wigley_stl(path: Path, L: float = 10.0, nx: int = 161, nz: int = 41,
               freeboard_frac: float = 0.6) -> dict:
    """Closed, outward-wound Wigley STL. Returns its measured properties."""
    B, T = L / 10.0, L / 16.0
    fb = freeboard_frac * T
    xs = np.linspace(0.0, L, nx)          # bow at +x, matching the KCS convention
    zs_hull = np.linspace(-T, 0.0, nz)

    def half_beam(x, z):
        xi = 2.0 * (x - L / 2) / L
        return (B / 2) * (1 - xi ** 2) * (1 - (z / T) ** 2)

    # Station curves below the waterline, then a wall-sided extension above it.
    zs = np.concatenate([zs_hull, np.linspace(0.0, fb, 9)[1:]])
    Y = np.empty((nx, len(zs)))
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            Y[i, j] = half_beam(x, min(z, 0.0))

    tris: list = []

    def quad(a, b, c, d):
        for t in ((a, b, c), (a, c, d)):
            p = np.array(t)
            if np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) > 1e-14:
                tris.append(t)

    S = [[(xs[i], Y[i, j], zs[j]) for j in range(len(zs))] for i in range(nx)]
    P = [[(xs[i], -Y[i, j], zs[j]) for j in range(len(zs))] for i in range(nx)]

    for i in range(nx - 1):
        for j in range(len(zs) - 1):
            # starboard outward +y; port mirrored so BOTH wind outward
            quad(S[i][j], S[i][j + 1], S[i + 1][j + 1], S[i + 1][j])
            quad(P[i + 1][j], P[i + 1][j + 1], P[i][j + 1], P[i][j])
        # deck lid, outward +z. Wound S -> P -> P -> S: with S at +y this gives
        # n_z > 0. The hull generator in geometry.py had this exact quad the
        # other way round and wrote its whole deck inside-out.
        quad(S[i][-1], P[i][-1], P[i + 1][-1], S[i + 1][-1])
    # keel line is a degenerate edge (Y=0 at z=-T) and the ends taper to points,
    # so no end caps are needed: the surface closes on itself there.

    out = ["solid wigley"]
    for t in tris:
        p = np.array(t)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        n = n / (np.linalg.norm(n) or 1.0)
        out.append(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        out.append("  outer loop")
        for v in p:
            out.append(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        out += ["  endloop", " endfacet"]
    out.append("endsolid wigley")
    path.write_text("\n".join(out) + "\n")
    return {"n_tris": len(tris), "L": L, "B": B, "T": T,
            "wetted_analytic": wetted_surface(L)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/benchmark_geom/wigley.stl")
    ap.add_argument("--lwl", type=float, default=10.0)
    args = ap.parse_args()
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    info = wigley_stl(p, args.lwl)

    from navalai.cfd.case import stl_watertight_report
    rep = stl_watertight_report(p)
    print(f"{p}: {info['n_tris']} tris  L={info['L']} B={info['B']:.3f} "
          f"T={info['T']:.4f}")
    print(f"  watertight={rep['watertight']}  winding_conflicts="
          f"{rep['winding_conflicts']}  outward={rep['outward']}  "
          f"signed_volume={rep['signed_volume']:.4f} m^3")
    print(f"  wetted (analytic, both sides, to z=0) = "
          f"{info['wetted_analytic']:.4f} m^2")


if __name__ == "__main__":
    main()
