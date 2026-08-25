"""HULL 21 — TRACED from the owner's drawing, not re-imagined.

    python scripts/hull21_traced.py

THE METHOD CHANGE (owner, 2026-08-25): "you can trace lines and create the
exact same shape... if you trace the PLAN you have the exact shape of the
boat... take houseboat17 and extend the keel line for about 80% of the boat
[leaving] 20% space for the motor and the fins... ignore the motor part,
just create space for where the motor is."  Plus: "the boat should have a
flat surface on the top because this is how it will be 3d printed."

So every longitudinal line here comes from PIXELS of
`downloads/hull-examples/hookprobe-concept.jpg` (trace2.npz, component-
extracted and slope-limited), not from guessed control points:

  plan half-beam  b(s)   traced outline, scaled to B = 4 m
  deck            z_d(s) the drawing's own line -- measured STRAIGHT
                         (slope -0.181 px/px): ONE PLANE, which is exactly
                         the printable flat top; no camber athwartships
  keel            z_k(s) traced hull bottom over s in [0.15, 1] (the ~80%);
                         over the aft bay it rises to the drawn stern
                         overhang -- the MOTOR + FIN SPACE, left open

Scales: length 12 m over the traced 649 px (plan) / 590 px (side); beam set
by max full beam = 4.0 m; side heights by the side view's own px/m with the
drawn waterline as z = 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.hookprobe_hull import (_ear_clip, _fair, _resample_arc,  # noqa: E402
                                    _smoothstep)

L = 12.0
T = np.load("data/exports/hookprobe-concept/trace2.npz")
T0 = np.load("data/exports/hookprobe-concept/trace.npz")

# ---- plan: s (0 stern .. 1 bow) -> half-beam, EXACT ----------------------
_px0, _px1 = float(T["pxs"].min()), float(T["pxs"].max())
_s_plan = (T["pxs"] - _px0) / (_px1 - _px0)
_half_px = (T["pb"] - T["pt"]) / 2.0
_B_SCALE = 2.0 / _half_px.max()                     # max full beam = 4 m


def half_beam(s):
    return np.interp(np.asarray(s, float), _s_plan, _half_px) * _B_SCALE


# ---- side: the drawing's own vertical scale ------------------------------
_SX0, _SX1, _WL = 473.0, 1063.0, 318.0
_PXM = (_SX1 - _SX0) / L                            # px per metre


def _z(px):
    return (_WL - np.asarray(px, float)) / _PXM


# deck: the straight plane the drawing draws (and the print needs)
_dm = (T0["stop"] is not None)
_dx = T0["sxs"] if "sxs" in T0 else None
_deck_x = T0["sxs"]; _deck_y = T0["stop"]
_msk = (_deck_x >= 480) & (_deck_x <= 1060)
_A = np.polyfit((_deck_x[_msk] - _SX0) / (_SX1 - _SX0), _z(_deck_y[_msk]), 1)


def deck_z(s):
    return np.polyval(_A, np.asarray(s, float))


# keel: traced over the 80%, arch over the motor bay
_ks = (T["sxs"] - _SX0) / (_SX1 - _SX0)
_kz = _z(T["sb"])
BAY_S = 0.16                                        # the ~20% motor space


def keel_z(s):
    s = np.asarray(s, float)
    z = np.interp(np.clip(s, _ks.min(), 1.0), _ks, _kz)
    bay = s < BAY_S
    if np.any(bay):
        z0 = np.interp(BAY_S, _ks, _kz)             # keel depth at bay start
        z_tip = 0.30                                # drawn stern overhang
        u = (BAY_S - s[bay]) / BAY_S
        z[bay] = z0 + (z_tip - z0) * _smoothstep(u)
    return z


def chine(s):
    s = np.asarray(s, float)
    y = 0.88 * half_beam(s)
    zk = keel_z(np.maximum(s, BAY_S))               # walls hang from the hull
    z = zk + 0.42 * (0.0 - zk)                      # between keel and WL
    return y, np.minimum(z, deck_z(s) - 0.15)


def section(s, n=56):
    """Half section, CL only at the two ends (the manifold rule)."""
    s = float(s)
    b = float(half_beam(s)); zd = float(deck_z(s))
    _yc, _zc = chine(np.array([s]))
    yc, zc = float(_yc[0]), float(_zc[0])
    zk = float(keel_z(np.array([s]))[0])
    pts = [(0.0, zd)]

    def line(p, q, k):
        for i in range(1, k + 1):
            t = i / k
            pts.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))

    line((0.0, zd), (b, zd), max(3, n // 8))        # FLAT deck
    line((b, zd), (yc, zc), max(4, n // 5))         # topside
    if s >= BAY_S:
        line((yc, zc), (0.0, zk), max(6, n // 3))   # V bottom to the keel
    else:
        # THE MOTOR BAY: walls come down from the chine, the roof is the
        # risen keel line -- open space below for motor and fins. The roof
        # is CLAMPED below the chine (self-intersection guard: as the roof
        # sweeps up toward the stern overhang it would otherwise cross the
        # wall path -- measured 110 self-intersections before this clamp),
        # and the walls fade as the roof approaches the chine so the section
        # morphs, never folds.
        roof_raw = float(keel_z(np.array([s]))[0])
        roof = min(roof_raw, zc - 0.08)
        depth_frac = np.clip((zc - roof) / max(zc - zk, 1e-6), 0.0, 1.0)
        wall_y = max(0.30, 0.55 * yc) * (0.4 + 0.6 * depth_frac)
        line((yc, zc), (wall_y, zc - 0.02), max(2, n // 10))
        line((wall_y, zc - 0.02), (wall_y * 0.9, roof), max(4, n // 6))
        line((wall_y * 0.9, roof), (0.0, roof), max(3, n // 8))
    return np.array(pts)


def full_section(s, n=56):
    p = section(s, n=n)
    mir = p[::-1][1:-1].copy(); mir[:, 0] *= -1.0
    return np.vstack([p, mir])


def main() -> int:
    out = Path("data/exports/hull21"); out.mkdir(parents=True, exist_ok=True)
    ss = np.linspace(0.0, 0.999, 241)
    secs = [full_section(si) for si in ss]
    m = max(len(p) for p in secs)
    R = [_resample_arc(p, m) for p in secs]
    tris = []
    for i in range(len(ss) - 1):
        x0, x1 = ss[i] * L, ss[i + 1] * L
        P, Q = R[i], R[i + 1]
        for j in range(m):
            j2 = (j + 1) % m
            a, b = (x0, P[j, 0], P[j, 1]), (x0, P[j2, 0], P[j2, 1])
            c, d = (x1, Q[j2, 0], Q[j2, 1]), (x1, Q[j, 0], Q[j, 1])
            tris.append((a, b, c)); tris.append((a, c, d))
    for (P, xx, flip) in ((R[0], 0.0, True), (R[-1], ss[-1] * L, False)):
        for (i0, i1, i2) in _ear_clip(P):
            tris.append(((xx, P[i0, 0], P[i0, 1]), (xx, P[i1, 0], P[i1, 1]),
                         (xx, P[i2, 0], P[i2, 1])) if flip else
                        ((xx, P[i0, 0], P[i0, 1]), (xx, P[i2, 0], P[i2, 1]),
                         (xx, P[i1, 0], P[i1, 1])))
    stl = out / "hull21.stl"
    with open(stl, "w") as f:
        f.write("solid hull21\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid hull21\n")
    from navalai import mesh_repair as _mr
    for _ in range(2):
        V, Tt, rep = _mr.repair(str(stl))
        with open(stl, "w") as f:
            f.write("solid hull21\n")
            for t in Tt:
                a, b, c = V[t[0]], V[t[1]], V[t[2]]
                nn = np.cross(b - a, c - a); ln = np.linalg.norm(nn)
                nn = nn / ln if ln > 0 else nn
                f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n"
                        "  outer loop\n")
                for v in (a, b, c):
                    f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                f.write("  endloop\n endfacet\n")
            f.write("endsolid hull21\n")
        chk = _mr.diagnose(str(stl))
        bad = {k: v for k, v in chk.found.items() if v and k in
               ("boundary_edges", "nonmanifold_edges", "winding_conflicts",
                "self_intersections")}
        if not bad:
            break
    print(f"HULL21 traced: L {L} m, B {2*half_beam(np.array([0.4])).max():.2f}+ m")
    print(f"  keel: bay roof +0.30 -> {keel_z(np.array([BAY_S]))[0]:+.2f} at "
          f"s={BAY_S} -> deepest {keel_z(np.linspace(0.2,1,50)).min():+.2f}")
    print(f"  deck plane: {deck_z(np.array([0.0]))[0]:+.2f} (stern) -> "
          f"{deck_z(np.array([1.0]))[0]:+.2f} m (bow) — ONE FLAT PLANE")
    print(f"  STL {stl}: {rep.n_tris_after} tris, MANIFOLD: {not bad} {bad or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
