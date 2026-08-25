"""HOOKPROBE CONCEPT — the integrated-motor hull, built DIRECTLY.

    python scripts/hookprobe_concept.py --out data/exports/hookprobe-concept

FROM `downloads/hull-examples/hookprobe-concept.jpg` (updated 2026-08-25
18:45, "REFINED DIMENSIONS L=12m, B_stern=4m"), with the owner's own
explanation as the spec:

    "an axe type bow that transitions into the stern which has a motor in
    the middle and the motor comes with the keel line from the bow. the
    stern forms from the lateral chines."

The four views, as built here:

  PLAN   reverse teardrop: 4 m ROUNDED STERN tapering continuously to a
         needle axe bow ("SMOOTH HYDRODYNAMIC TAPER").
  SIDE   deep plumb axe bow; the KEEL LINE runs from the stem down and aft
         and BECOMES the integrated motor pod — one curve, hull to hub.
  BACK   the lateral chines sweep down and wrap into a complete RING — a
         DUCT — around the propeller, pod at its centre, outrigger legs
         either side ("CONFIRMED 4m STERN WIDTH").
  FRONT  central V-keel blade + outriggers ("V-KEEL & OUTRIGGERS").

WHY THIS IS BUILT WITHOUT THE GENOME, said precisely: the stern sections
are KEYHOLES — outer hull + duct ring + pod, the pod joined to the hull
through the keel-blade strut — and the section stops being expressible as a
single-valued keel-chine-sheer walk. Same class of gap as houseboat17's
tunnel (a notch) but stronger: an interior ring. `geometry._halfbreadth_at`
documents the single-valued assumption this violates. The owner's
instruction is the method: design the shape directly first, THEN teach the
grammar what it needs (a pod solid + a duct boundary are the two new words).

Every transverse section here is ONE closed loop (the keyhole is simply
connected because the strut joins pod to hull), so the loft is manifold by
construction — the houseboat17 lesson, kept.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.hookprobe_hull import (G, RHO, _ear_clip, _fair,      # noqa: E402
                                    _resample_arc, _smoothstep,
                                    hydrostatics)

L = 12.0            # TOTAL LENGTH: 12m  (drawing)
B_STERN = 4.0       # CONFIRMED 4m STERN WIDTH  (drawing)


class Concept:
    """s = 0 at the transom face, s = 1 at the stem, as everywhere here."""

    loa = L
    depth = 1.6
    x_bmax = 0.20       # widest near the stern (reverse teardrop)

    def __init__(self):
        # -- the LINES ----------------------------------------------------
        # sheer half-beam: 2.0 m at the rounded stern easing to the needle
        self.y_sh = _fair([0.0, 0.10, 0.30, 0.60, 0.85, 1.0],
                          [1.80, 2.00, 1.95, 1.45, 0.70, 0.012])
        # deck: LOW stern rising smoothly to the TALL axe bow (side view)
        self.z_sh = _fair([0.0, 0.35, 0.70, 1.0],
                          [0.70, 0.85, 1.15, 1.60])
        # THE KEEL LINE THAT BECOMES THE MOTOR: from the stem at -1.05 (axe,
        # deepest forward part of the HULL) sweeping aft; over the pod span
        # it IS the pod axis. Pod centreline depth -0.62.
        self.z_keel = _fair([0.0, 0.12, 0.35, 0.65, 0.88, 1.0],
                            [-0.62, -0.62, -0.60, -0.55, -0.80, -1.05])
        # chine: near the WL forward, descending aft as the chines wrap DOWN
        # to form the duct (back view)
        self.y_ch = _fair([0.0, 0.15, 0.40, 0.70, 1.0],
                          [1.35, 1.65, 1.55, 1.00, 0.008])
        self.z_ch = _fair([0.0, 0.20, 0.50, 0.80, 1.0],
                          [-0.30, -0.28, -0.18, -0.05, 0.30])

        # -- the POD (the keel line's ending) -----------------------------
        self.pod_s0, self.pod_s1 = 0.03, 0.38      # x 0.36..4.56 m
        self.pod_r_max = 0.34
        # -- the DUCT: chines close into a ring around the prop -----------
        self.duct_s0, self.duct_s1 = 0.03, 0.16    # ring complete here
        self.duct_r = 0.55                          # nozzle inner radius
        self.strut_half = 0.09                      # keel-blade strut width

    def pod_r(self, s):
        """Pod radius along its span: a smooth body of revolution."""
        u = (np.asarray(s, float) - self.pod_s0) / (self.pod_s1 - self.pod_s0)
        u = np.clip(u, 0.0, 1.0)
        # blunt-ish nose aft (prop hub), long tail forward into the keel
        prof = np.sin(np.pi * np.clip(u, 0, 1)) ** 0.8
        taper = _smoothstep((1.0 - u) * 4.0) * _smoothstep(u * 6.0)
        return self.pod_r_max * np.maximum(prof, 0.0) * np.maximum(taper, 0)

    def ring_frac(self, s):
        """0 = open arch, 1 = complete duct ring (near the prop)."""
        u = (self.duct_s1 - np.asarray(s, float)) / (self.duct_s1 - self.duct_s0)
        return _smoothstep(np.clip(u, 0.0, 1.0))

    # -- one HALF section: a single open path, CL touched ONLY at the ends
    # (the houseboat17 lesson: an interior centreline segment mirrors into a
    # duplicated face and the shell stops being manifold). The duct is a
    # 330-degree ring with a narrow BOTTOM SLOT: the slot is what lets the
    # section stay one loop, and hydrodynamically it is a drain gap a real
    # nozzle build would want anyway. The pod is a SEPARATE closed shell.
    def section(self, s, n=64):
        s = float(s)
        ysh = float(self.y_sh(s)); zsh = float(self.z_sh(s))
        ych = float(self.y_ch(s)); zch = float(self.z_ch(s))
        zk = float(self.z_keel(s))
        rf = float(self.ring_frac(np.array([s]))[0])

        pts = [(0.0, zsh)]

        def line(p, q, k):
            for i in range(1, k + 1):
                t = i / k
                pts.append((p[0] + t * (q[0] - p[0]),
                            p[1] + t * (q[1] - p[1])))

        line((0.0, zsh), (ysh, zsh - 0.02), max(3, n // 10))
        line((ysh, zsh - 0.02), (ych, zch), max(4, n // 6))
        if rf < 1e-3:
            # forward body: chine -> deep V keel blade, end ON the CL
            line((ych, zch), (0.0, zk), max(6, n // 4))
            return np.array(pts)
        # AFT BODY: the chines wrap down into the duct.
        Ro = self.duct_r + 0.10 * (1 - rf)   # outer wall radius
        Ri = self.duct_r                      # nozzle bore
        cz = zk                                # duct centre ON the keel line
        wall = 0.09
        slot = 0.10 + 0.9 * (1 - rf)          # half-width of the bottom slot
        th_slot = math.asin(min(0.95, slot / Ro))
        th_top = 0.55 - 0.35 * rf             # where the wall leaves the hull
        # outer wall: from the chine to the ring, then around to the slot
        line((ych, zch), ((Ro + wall) * math.sin(th_top),
                          cz + (Ro + wall) * math.cos(th_top)), max(4, n // 6))
        k = max(10, n // 3)
        for i in range(1, k + 1):
            th = th_top + (math.pi - th_slot - th_top) * i / k
            pts.append(((Ro + wall) * math.sin(th),
                        cz + (Ro + wall) * math.cos(th)))
        # the slot tip: step inboard to the bore
        tipth = math.pi - th_slot
        pts.append((Ro * math.sin(tipth) - 0.0, cz + (Ro + 0.0) * math.cos(tipth)))
        # up the INSIDE of the bore to the arch roof
        for i in range(1, k + 1):
            th = tipth - (tipth - th_top * 0.6) * i / k
            pts.append((Ri * math.sin(th), cz + Ri * math.cos(th)))
        # roof of the arch back to the CL — the LAST point, on the CL
        line((Ri * math.sin(th_top * 0.6), cz + Ri * math.cos(th_top * 0.6)),
             (0.0, cz + Ri), max(3, n // 10))
        return np.array(pts)

    def full_section(self, s, n=64):
        p = self.section(s, n=n)
        mir = p[::-1][1:-1].copy(); mir[:, 0] *= -1.0
        return np.vstack([p, mir])

    # -- the POD: its own closed shell, the keel line made solid ----------
    def pod_section(self, s, n=40):
        """Full closed loop: circle + a strut tab reaching up to the arch."""
        rp = float(self.pod_r(np.array([s]))[0])
        if rp < 5e-3:
            return None
        zk = float(self.z_keel(s))
        w = min(self.strut_half, 0.8 * rp)
        top = zk + self.duct_r + 0.12          # tab tip: inside the arch roof
        th0 = math.asin(w / max(rp, w + 1e-6))
        pts = [(w, top)]
        k = max(10, n // 2)
        for i in range(k + 1):                  # starboard down and around
            th = th0 + (2 * math.pi - 2 * th0) * i / k
            pts.append((rp * math.sin(th), zk + rp * math.cos(th)))
        pts.append((-w, top))
        return np.array(pts)


def _loft(sarr, secs, loa, name, path):
    """Loft closed loops -> ASCII STL shell with ear-clipped caps."""
    m = max(len(q) for q in secs)
    R = [_resample_arc(q, m) for q in secs]
    tris = []
    for i in range(len(sarr) - 1):
        x0, x1 = sarr[i] * loa, sarr[i + 1] * loa
        P, Q = R[i], R[i + 1]
        for j in range(m):
            j2 = (j + 1) % m
            a, b = (x0, P[j, 0], P[j, 1]), (x0, P[j2, 0], P[j2, 1])
            c, d = (x1, Q[j2, 0], Q[j2, 1]), (x1, Q[j, 0], Q[j, 1])
            tris.append((a, b, c)); tris.append((a, c, d))
    for (P, xx, flip) in ((R[0], sarr[0] * loa, True),
                          (R[-1], sarr[-1] * loa, False)):
        for (i0, i1, i2) in _ear_clip(P):
            a = (xx, P[i0, 0], P[i0, 1]); b = (xx, P[i1, 0], P[i1, 1])
            c = (xx, P[i2, 0], P[i2, 1])
            tris.append((a, b, c) if flip else (a, c, b))
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for t in tris:
            f.write(" facet normal 0 0 0\n  outer loop\n")
            for v in t:
                f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("  endloop\n endfacet\n")
        f.write(f"endsolid {name}\n")
    return len(tris)


def write_stl(h: Concept, path: Path, ns: int = 221, nsec: int = 64):
    sarr = np.linspace(0.0, 1.0, ns)
    secs = [h.full_section(si, n=nsec) for si in sarr]
    return _loft(sarr, secs, h.loa, "hookprobe_concept_hull", path)


def write_pod(h: Concept, path: Path, ns: int = 81, nsec: int = 40):
    ss = np.linspace(h.pod_s0 + 0.004, h.pod_s1 - 0.004, ns)
    secs = [h.pod_section(si, n=nsec) for si in ss]
    keep = [(s_, q) for s_, q in zip(ss, secs) if q is not None]
    ss = np.array([k[0] for k in keep]); secs = [k[1] for k in keep]
    return _loft(ss, secs, h.loa, "hookprobe_concept_pod", path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/exports/hookprobe-concept")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    h = Concept()
    from navalai import mesh_repair as _mr

    def finish(path, name):
        for _ in range(2):
            V, T, rep = _mr.repair(str(path))
            with open(path, "w") as f:
                f.write(f"solid {name}\n")
                for t in T:
                    a, b, c = V[t[0]], V[t[1]], V[t[2]]
                    nn = np.cross(b - a, c - a); ln = np.linalg.norm(nn)
                    nn = nn / ln if ln > 0 else nn
                    f.write(f" facet normal {nn[0]:.6e} {nn[1]:.6e} "
                            f"{nn[2]:.6e}\n  outer loop\n")
                    for v in (a, b, c):
                        f.write(f"   vertex {v[0]:.6f} {v[1]:.6f} "
                                f"{v[2]:.6f}\n")
                    f.write("  endloop\n endfacet\n")
                f.write(f"endsolid {name}\n")
            chk = _mr.diagnose(str(path))
            bad = {k: v for k, v in chk.found.items() if v and k in
                   ("boundary_edges", "nonmanifold_edges",
                    "winding_conflicts", "self_intersections")}
            if not bad:
                break
        return rep.n_tris_after, bad

    hull_stl = out / "hull.stl"
    pod_stl = out / "pod.stl"
    n1 = write_stl(h, hull_stl)
    n2 = write_pod(h, pod_stl)
    t1, bad1 = finish(hull_stl, "hookprobe_concept_hull")
    t2, bad2 = finish(pod_stl, "hookprobe_concept_pod")
    # the combined deliverable: both shells in one file (slicers and snappy
    # both accept multi-solid STL; the strut tab overlaps into the arch roof,
    # which a slicer unions and snappy treats as one wall)
    combo = out / "hookprobe-concept.stl"
    combo.write_text(hull_stl.read_text() + pod_stl.read_text())
    print(f"CONCEPT  L {L} m x B_stern {B_STERN} m")
    print(f"  hull shell: {t1} tris, MANIFOLD: {not bad1} {bad1 or ''}")
    print(f"  pod shell : {t2} tris, MANIFOLD: {not bad2} {bad2 or ''}")
    print(f"  combined  : {combo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
