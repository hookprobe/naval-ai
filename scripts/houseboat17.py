"""HOUSEBOAT 17 -- the owner's OWN topology, built from four continuous lines.

    python scripts/houseboat17.py --out data/exports/houseboat17

THE INSTRUCTION, verbatim from the owner, because it IS the design:

    "imagine you are doing a deep v hull boat that is 50% of the length. as
    the stern keel curve raises up and closes the keel line. now from the
    chine line of the deep v hull, start by adding two side demihulls so the
    line from the chine transforms into the keel line for the demihull."

What that means, and why it beats houseboat16's construction: in 16 the
tunnel is a NOTCH cut into a monohull's bottom -- an extra boundary that has
to be faired into everything around it (the groove at 32%, the arch fillet
and the cap bugs all came from that seam). Here there is no seam, because no
line ever terminates:

    centre keel line   deep-V keel forward  --rises, crosses the chine
                       height, and becomes-->  the CROWN of the tunnel
    chine lines        deep-V chine forward --descends and becomes-->
                       the KEEL of each demihull
    sheer line         runs transom to stem as always
    deck               closes the top

The transverse section is just the polyline threaded through those lines at
one station: a V forward (centre below chines), momentarily FLAT where the
centre and chine heights cross (s ~= 0.5), and a W aft (centre above
chines). The tunnel is what the W encloses below the crown. Surfaces are
STRAIGHT panels stretched between the lines -- "we unite points, we make
lines, then we stretch the surface from the lines" -- so the hull is fair
exactly when the four lines are fair, and each line is one C2 B-spline
through named control points (`_fair`, shared with hookprobe_hull; the
method is the skinning construction of Zhu et al., jmse-11-01816).

Kept from the hookprobe work, because the owner approved them there: the
20 deg aft-raked axe stem, the knife-edge stem bar, LOA normalised to
exactly 16.000 m, mesh repair + re-diagnosis in the pipeline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.hookprobe_hull import (G, RHO, _fair, _smoothstep,  # noqa: E402
                                    _ear_clip, _resample_arc,
                                    hydrostatics)


class Hull17:
    """Deep-V forward morphing into twin demihulls, from four fair lines."""

    loa = 16.0
    x_bmax = 0.50          # read by hookprobe_hull.hydrostatics for its Cb

    def __init__(self,
                 t_stem=1.30,        # centre keel at the stem (axe depth)
                 crown_aft=0.44,     # tunnel crown at the transom
                 t_demi=0.88,        # demihull (ex-chine) keel, deepest
                 stern_rise=0.14,    # demihull keel eases up into the transom
                 bmax=4.0,
                 stem_rake_deg=20.0, rake_start=0.72,
                 chine_r=0.10,       # fillet radius where panels meet
                 # THE OCEAN KNOBS. houseboat17's proportions are a river /
                 # coastal liveaboard's; `ocean17` is the SAME four lines with
                 # these three raised -- the topology is the design and the
                 # proportions are the wave climate. Defaults reproduce
                 # houseboat17 exactly.
                 depth=1.55,
                 sheer_aft=0.70,     # deck edge over the stern body
                 sheer_bow=1.48,     # deck edge at the stem
                 # WHERE THE KEEL LINE CLOSES. The owner's observation: the W
                 # stern buys its stability and prop protection with interior
                 # VOLUME -- the tunnel is space the boat displaces but cannot
                 # use. This is the one lever that trades it back: moving the
                 # closing AFT keeps the full-width V (where accommodation
                 # lives) over more of the length and shortens the tunnel to
                 # just the propeller run. 0.5 reproduces houseboat17.
                 x_close=0.50):
        L = self.loa
        self.depth = depth
        self.bmax = bmax
        self.stem_rake_deg = stem_rake_deg
        self.rake_start = rake_start
        self.chine_r = chine_r
        self.t_stem = t_stem

        # THE FOUR LINES. s = 0 transom, s = 1 stem. Each is ONE spline.
        #
        # Centre keel: deep at the stem, deep-V through the forward half,
        # then "raises up and closes" -- crosses the chine height near
        # s = 0.5 and levels out as the tunnel crown.
        xc = float(x_close)
        self.z_c = _fair([0.0, 0.5 * xc, xc, xc + 0.5 * (1 - xc), 1.0],
                         [crown_aft, 0.30, -0.40, -0.95, -t_stem])
        # Chine -> demihull keel: near the waterline at the stem (a deep-V
        # chine), descending aft THROUGH the crossing to become the demihull
        # keel, deepest just forward of the transom and easing up into it
        # (the stern rise the owner asked for on 16, here it is native).
        self.z_ch = _fair([0.0, 0.36 * xc, xc, xc + 0.6 * (1 - xc), 1.0],
                          [-t_demi + stern_rise, -t_demi, -0.40, -0.10, 0.12])
        self.y_ch = _fair([0.0, 0.40, 0.70, 0.90, 1.0],
                          [1.32, 1.58, 1.35, 0.72, 0.010])
        # Sheer: full beam amidships, slab-sided, knife entry (16 mm half).
        self.y_sh = _fair([0.0, 0.35, 0.70, 0.92, 1.0],
                          [1.93, 2.00, 1.75, 0.98, 0.016])
        self.z_sh = _fair([0.0, 0.50, 0.80, 1.0],
                          [sheer_aft, sheer_aft,
                           sheer_aft + 0.45 * (sheer_bow - sheer_aft),
                           sheer_bow])

    # -- the deepest point at a station, for flotation and reporting --------
    def keel_z(self, s):
        s = np.asarray(s, float)
        return np.minimum(self.z_c(s), self.z_ch(s))

    def rake_dx(self, s, z):
        """The 20 deg aft-raked axe stem, as in hookprobe_hull."""
        s = np.asarray(s, float); z = np.asarray(z, float)
        w = _smoothstep((s - self.rake_start) / max(1.0 - self.rake_start,
                                                    1e-9))
        return -z * math.tan(math.radians(self.stem_rake_deg)) * w

    # -- one half-section: centreline -> chine -> sheer -> deck -> centreline
    def section(self, s, n=48):
        s = float(s)
        zc = float(self.z_c(s)); zch = float(self.z_ch(s))
        ych = float(self.y_ch(s)); ysh = float(self.y_sh(s))
        zsh = float(self.z_sh(s))
        A = np.array([0.0, zc])          # centre: keel fwd / crown aft
        B = np.array([ych, zch])         # chine fwd / demihull keel aft
        C = np.array([ysh, zsh])         # sheer
        # straight panels with a small fillet at B, so the chine is a line
        # with a radius, not a knuckle. The fillet shrinks as B pinches
        # toward A or C (the stem), so it can never fold the path.
        r = min(self.chine_r,
                0.45 * np.linalg.norm(B - A), 0.45 * np.linalg.norm(C - B))
        d1 = (B - A) / max(np.linalg.norm(B - A), 1e-12)
        d2 = (C - B) / max(np.linalg.norm(C - B), 1e-12)
        P0, P2 = B - d1 * r, B + d2 * r
        k1 = max(6, n // 3); k2 = max(6, n // 3); kf = max(6, n // 4)
        u = np.linspace(0.0, 1.0, k1, endpoint=False)[:, None]
        seg1 = A + u * (P0 - A)
        w = np.linspace(0.0, 1.0, kf, endpoint=False)[:, None]
        arc = (1 - w) ** 2 * P0 + 2 * (1 - w) * w * B + w ** 2 * P2
        v = np.linspace(0.0, 1.0, k2, endpoint=False)[:, None]
        seg2 = P2 + v * (C - P2)
        kd = max(4, n // 6)
        t = np.linspace(0.0, 1.0, kd)[:, None]
        deck = C + t * (np.array([0.0, zsh]) - C)
        return np.vstack([seg1, arc, seg2, deck])

    def full_section(self, s, n=48):
        p = self.section(s, n=n)
        mir = p[::-1][1:-1].copy()
        mir[:, 0] *= -1.0
        return np.vstack([p, mir])


def float_to(h: Hull17, mass_kg: float) -> float:
    lo = float(h.keel_z(np.linspace(0, 1, 50)).min()) + 1e-3
    hi = float(h.z_sh(0.3)) - 1e-3
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        r = hydrostatics(h, mid, ns=61)
        if (r["disp_kg"] if r else 0.0) > mass_kg:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def write_stl(h: Hull17, path: Path, ns: int = 241, nsec: int = 56):
    s = np.linspace(0.0, 1.0, ns)
    secs = [h.full_section(si, n=nsec) for si in s]
    # constant path structure at every station, so no resampling is needed:
    # index j is the same landmark everywhere and the loft cannot twist.
    m = len(secs[0])
    assert all(len(p) == m for p in secs)
    R = secs
    XP = [s[i] * h.loa + h.rake_dx(np.full(m, s[i]), R[i][:, 1])
          for i in range(ns)]
    tris = []

    def quad(a, b, c, d):
        tris.append((a, b, c)); tris.append((a, c, d))

    for i in range(ns - 1):
        P, Q = R[i], R[i + 1]
        xp, xq = XP[i], XP[i + 1]
        for j in range(m):
            j2 = (j + 1) % m
            quad((xp[j], P[j, 0], P[j, 1]), (xp[j2], P[j2, 0], P[j2, 1]),
                 (xq[j2], Q[j2, 0], Q[j2, 1]), (xq[j], Q[j, 0], Q[j, 1]))
    for (P, xv, flip) in ((R[0], XP[0], True), (R[-1], XP[-1], False)):
        for (i0, i1, i2) in _ear_clip(P):
            a = (xv[i0], P[i0, 0], P[i0, 1])
            b = (xv[i1], P[i1, 0], P[i1, 1])
            c = (xv[i2], P[i2, 0], P[i2, 1])
            tris.append((a, b, c) if flip else (a, c, b))
    # normalise LOA to the brief (the rake pushes the forefoot forward)
    _V = np.array([v for t in tris for v in t], float)
    _lo, _hi = _V[:, 0].min(), _V[:, 0].max()
    _k = h.loa / (_hi - _lo)
    tris = [tuple(((v[0] - _lo) * _k, v[1], v[2]) for v in t) for t in tris]
    with open(path, "w") as f:
        f.write("solid houseboat17\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid houseboat17\n")
    return len(tris)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/exports/houseboat17")
    ap.add_argument("--mass", type=float, default=14000.0)
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    h = Hull17()
    wl = float_to(h, args.mass)
    r = hydrostatics(h, wl, ns=161)
    kg = 0.55 * h.depth - 0.60
    gm = r["kb_m"] + r["bm_m"] - kg
    s = np.linspace(0, 1, 401)
    zc, zch = h.z_c(s), h.z_ch(s)
    cross = s[np.argmin(np.abs(zc - zch))]
    print(f"HOUSEBOAT 17 -- the owner's line topology")
    print(f"  deep-V forward of s={cross:.2f} ({(1-cross)*100:.0f}% of length is V)"
          f", W/demihull aft of it; the keel line CLOSES at the crown")
    print(f"  centre keel: stem {zc[-1]:+.3f} -> crossing {float(h.z_c(np.array([cross]))[0]):+.3f}"
          f" -> crown at transom {zc[0]:+.3f}")
    print(f"  chine line : stem {zch[-1]:+.3f} -> demihull keel {zch.min():+.3f}"
          f" -> transom {zch[0]:+.3f}  (stern rise {zch[0]-zch.min():+.3f})")
    print(f"  floats {r['disp_kg']:.0f} kg at z={wl:+.3f}: draft"
          f" {wl - zc[-1]:.3f} m at the stem, {wl - zch.min():.3f} m at the"
          f" demihull keels")
    print(f"  BWL {r['bwl_m']:.2f} | Awp {r['awp_m2']:.1f} m2 | wetted"
          f" {r['wetted_m2']:.1f} m2 | GM {gm:.2f} m")
    stl = out / "houseboat17.stl"
    n = write_stl(h, stl)
    from navalai import mesh_repair as _mr
    V, T, rep = _mr.repair(str(stl))
    with open(stl, "w") as f:
        f.write("solid houseboat17\n")
        for t in T:
            a, b, c = V[t[0]], V[t[1]], V[t[2]]
            nn = np.cross(b - a, c - a); ln = np.linalg.norm(nn)
            nn = nn / ln if ln > 0 else nn
            f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} {nn[2]:.6e}\n"
                    "  outer loop\n")
            for v in (a, b, c):
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write("endsolid houseboat17\n")
    chk = _mr.diagnose(str(stl))
    bad = {k: v for k, v in chk.found.items() if v}
    print(f"  STL {stl}  {n} lofted -> {rep.n_tris_after} after repair")
    for a in rep.applied:
        print(f"    repair: {a}")
    print(f"    WATERTIGHT AND MANIFOLD: {not bad}"
          + ("" if not bad else f"  STILL FOUND {bad}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
