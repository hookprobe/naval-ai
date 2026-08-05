"""OpenFOAM forces post-processing + grid-convergence (GCI) — testable
WITHOUT OpenFOAM (synthetic force files in tests; real files on the metal).

Research grounding: 'the uncertainty number you report depends materially on
which V&V method you implement' (Islam & Guedes Soares 2019) — so the method
is named in the output: Roache GCI, factor-of-safety 1.25, Richardson p.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_NUM = re.compile(r"[-+0-9.eE]+")


def parse_forces(path: str | Path):
    """Parse an OpenFOAM force.dat: rows 'time (fx fy fz) (fx fy fz) ...'.

    Returns (t, fx_total) with pressure+viscous x-components summed.
    """
    t, fx = [], []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        nums = [float(x) for x in _NUM.findall(line)]
        if len(nums) < 7:
            continue
        t.append(nums[0])
        # Column layout, from the file's own header:
        #   Time | total_x total_y total_z | pressure_x .. | viscous_x ..
        # so the drag is column 1. This previously read `nums[1] + nums[4]`,
        # i.e. total_x + pressure_x — DOUBLE-COUNTING the pressure term, while
        # the comment claimed "pressure-x + viscous-x". It inflated every drag
        # this project has reported: KCS C_t read 9.33e-3 against OpenFOAM's own
        # forceCoeffs value of 4.26e-3, and the own-hull triplet was wrong by
        # the same mechanism. Cross-check any change here against forceCoeffs.
        fx.append(nums[1])
    return np.array(t), np.array(fx)


def parse_forces_components(path: str | Path):
    """(t, pressure_x, viscous_x) — the split the total hides.

    Kept separate from parse_forces so the components are read from their OWN
    columns (4 and 7) rather than inferred, which is how they got confused in
    the first place.
    """
    t, fp, fv = [], [], []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        nums = [float(x) for x in _NUM.findall(s)]
        if len(nums) < 10:
            continue
        t.append(nums[0])
        fp.append(nums[4])
        fv.append(nums[7])
    return np.array(t), np.array(fp), np.array(fv)


def forces_path(case: str | Path) -> Path:
    """Force history for a case, merging RESTART segments into one file.

    A run interrupted by thermal sleep and resumed writes a fresh
    postProcessing/forces/<restart-time>/force.dat; reading only the `0/`
    directory would silently analyse the pre-crash fragment and report it as
    the whole run. Segments are concatenated in time order and later samples
    win where they overlap (the resumed run recomputed them).
    """
    root = Path(case) / "postProcessing" / "forces"
    segs = sorted((d for d in root.glob("*/force.dat")),
                  key=lambda p: float(p.parent.name))
    if not segs:
        raise FileNotFoundError(f"no force.dat under {root}")
    if len(segs) == 1:
        return segs[0]

    rows: dict[float, str] = {}
    for seg in segs:
        for line in seg.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                rows[float(_NUM.findall(s)[0])] = s
            except (IndexError, ValueError):
                continue
    merged = root / "force.merged.dat"
    merged.write_text("\n".join(rows[t] for t in sorted(rows)) + "\n")
    return merged


def mean_resistance(path: str | Path, tail_frac: float = 0.3) -> tuple[float, float]:
    """(mean, std) of drag over the final tail_frac of the run (settled)."""
    t, fx = parse_forces(path)
    if len(t) < 10:
        raise ValueError("force history too short")
    cut = t[0] + (1.0 - tail_frac) * (t[-1] - t[0])
    seg = fx[t >= cut]
    return float(np.mean(seg)), float(np.std(seg))


def stl_wetted_area(path: str | Path, waterline: float = 0.0) -> float:
    """Submerged area [m^2] of an ascii STL, triangles clipped at z=waterline.

    Gate 2M compares C_t against the Tokyo-2015 scatter, and C_t needs the
    wetted surface the CFD actually saw — taking it from the STL (the same
    geometry snappy meshed) keeps it honest for external benchmark hulls,
    where no analytic hull object exists to ask.
    """
    verts: list = []
    tris: list = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append([float(v) for v in s.split()[1:4]])
            if len(verts) == 3:
                tris.append(np.array(verts))
                verts = []

    total = 0.0
    for tri in tris:
        # Sutherland-Hodgman clip of the triangle against the half-space z<=wl
        poly: list = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            a_in, b_in = a[2] <= waterline, b[2] <= waterline
            if a_in:
                poly.append(a)
            if a_in != b_in:
                t = (waterline - a[2]) / (b[2] - a[2])
                poly.append(a + t * (b - a))
        if len(poly) < 3:
            continue
        p = np.array(poly)
        # fan triangulation of the (planar, convex) clipped polygon
        for i in range(1, len(p) - 1):
            total += 0.5 * float(np.linalg.norm(
                np.cross(p[i] - p[0], p[i + 1] - p[0])))
    return total


def _read_stl_tris(path: str | Path) -> list:
    verts: list = []
    tris: list = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append(tuple(round(float(v), 7) for v in s.split()[1:4]))
            if len(verts) == 3:
                tris.append(tuple(verts))
                verts = []
    return tris


def _write_stl(tris, path: str | Path, name: str = "hull") -> None:
    out = [f"solid {name}"]
    for tri in tris:
        p = np.array(tri)
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-14 else np.array([0.0, 0.0, 1.0])
        out.append(f" facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        out.append("  outer loop")
        for v in p:
            out.append(f"   vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}")
        out.append("  endloop")
        out.append(" endfacet")
    out.append(f"endsolid {name}")
    Path(path).write_text("\n".join(out))


def weld_vertices(src: str | Path, dst: str | Path, tol: float = 2e-4) -> dict:
    """Merge vertices closer than `tol` and drop the triangles that collapse.

    Sliver triangles are what snappyHexMesh turns into ZERO-VOLUME cells, and
    interFoam then dies on the first timestep. They are inherent to a sewn
    NURBS tessellation: the Tokyo-2015 KCS half body carries 8 triangles below
    quality 1e-3 straight out of the IGES, where patches with mismatched
    tessellation meet. Welding coincident-ish vertices removes the cause
    instead of asking the mesher to cope with it.

    Quality here is 4*sqrt(3)*A / sum(edge^2): 1 for equilateral, 0 for
    degenerate. Note that a max-edge/min-edge ratio does NOT detect these —
    three nearly COLLINEAR vertices have unremarkable edge lengths and no area.
    """
    tris = _read_stl_tris(src)
    # grid-snap to a lattice of size tol, then use the lattice cell as identity
    def key(v):
        return (round(v[0] / tol), round(v[1] / tol), round(v[2] / tol))

    rep: dict = {}
    for t in tris:
        for v in t:
            rep.setdefault(key(v), v)

    welded, dropped = [], 0
    for t in tris:
        p = tuple(rep[key(v)] for v in t)
        a, b, c = (np.array(v) for v in p)
        area = np.linalg.norm(np.cross(b - a, c - a)) / 2
        if len(set(p)) < 3 or area < 1e-12:
            dropped += 1
            continue
        welded.append(p)
    _write_stl(welded, dst)
    return {"n_tris": len(welded), "dropped": dropped,
            "vertices_merged": sum(1 for t in tris for v in t
                                   if rep[key(v)] != v)}


def mirror_half_hull(src: str | Path, dst: str | Path,
                     snap_tol: float = 1e-4) -> dict:
    """Mirror a half hull about y=0 into a full hull, SNAPPING the centreplane.

    MEASURED on the Tokyo-2015 KCS half body: its centreline vertices are not
    exactly on y=0 but scatter over -5.0e-6 .. +1.53e-5 m, with 49 of them on
    the wrong side of the plane. Mirroring that as-is makes the two halves
    interpenetrate by a few microns, which every topological check passes —
    watertight, manifold, no duplicates, correct enclosed volume — while
    snappyHexMesh produces 14 zero-volume cells, 73 wrongly oriented faces and
    non-orthogonality 148.9, and interFoam dies on the first timestep.

    Snapping |y| < snap_tol to exactly zero makes the seam shared rather than
    crossed. Mirrored triangles get REVERSED winding so normals stay outward,
    and triangles that collapse on snapping are dropped.
    """
    tris = _read_stl_tris(src)
    snapped, dropped = [], 0
    for tri in tris:
        p = [(x, 0.0 if abs(y) < snap_tol else y, z) for x, y, z in tri]
        a, b, c = (np.array(v) for v in p)
        if np.linalg.norm(np.cross(b - a, c - a)) / 2 < 1e-14:
            dropped += 1                      # collapsed on the plane
            continue
        snapped.append(tuple(p))

    out = list(snapped)
    for tri in snapped:
        m = [(x, -y, z) for x, y, z in tri]
        if all(abs(v[1]) < 1e-15 for v in tri):
            continue                          # lies in the plane: no twin
        out.append((m[0], m[2], m[1]))        # reversed winding -> outward
    _write_stl(out, dst)
    return {"n_tris": len(out), "dropped_degenerate": dropped,
            "half_tris": len(snapped)}


def _triangulate_polygon(pts, u, v, normal):
    """Ear-clip a planar polygon, returning outward-oriented triangles.

    A centroid FAN is only valid for a convex loop. On a ship deck outline —
    which is not convex — fan triangles cross outside the polygon and the STL
    becomes SELF-INTERSECTING: measured, the fan turned a clean sewn KCS half
    hull ("Surface is not self-intersecting") into one with 5 intersections,
    and snappy then degraded catastrophically as cells shrank enough to
    resolve them (149 zero-volume cells and 938 wrongly oriented faces at
    refinement level 4-5, versus 10 and 55 at level 2-3). Ear clipping keeps
    every triangle inside the polygon by construction.
    """
    P = np.array([[np.dot(p - pts[0], u), np.dot(p - pts[0], v)] for p in pts])
    # orient CCW in the (u, v) frame so the "ear" test has a fixed sign
    area2 = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                for i in range(len(P)))
    idx = list(range(len(pts)))
    if area2 < 0:
        idx.reverse()

    def cross2(o, a, b):
        return ((P[a][0] - P[o][0]) * (P[b][1] - P[o][1])
                - (P[a][1] - P[o][1]) * (P[b][0] - P[o][0]))

    def inside(a, b, c, p):
        d1, d2, d3 = cross2(a, b, p), cross2(b, c, p), cross2(c, a, p)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    out, guard = [], 0
    while len(idx) > 3 and guard < 10 * len(pts):
        guard += 1
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if cross2(a, b, c) <= 0:                      # reflex, not an ear
                continue
            if any(inside(a, b, c, m) for m in idx if m not in (a, b, c)):
                continue
            out.append((a, b, c))
            idx.pop(k)
            break
        else:
            break                                        # no ear: give up
    if len(idx) == 3:
        out.append(tuple(idx))

    tris = []
    for a, b, c in out:
        t = [pts[a], pts[b], pts[c]]
        if np.dot(np.cross(t[1] - t[0], t[2] - t[0]), normal) < 0:
            t = [t[0], t[2], t[1]]
        tris.append(tuple(tuple(float(x) for x in p) for p in t))
    return tris


def cap_planar_holes(src: str | Path, dst: str | Path,
                     planar_tol: float = 1e-4,
                     only_axis: int | None = None,
                     only_value: float = 0.0,
                     only_tol: float = 1e-3) -> dict:
    """Close planar openings in a triangulated surface (deck, transom, ...).

    External benchmark geometry arrives as a trimmed-surface model, not a
    solid: the Tokyo-2015 KCS IGES is a half body open at the deck. CFD needs a
    CLOSED manifold or the mesher floods the interior — the same lesson the
    own-hull STL taught (198 open edges, first Mac smoke run).

    Each boundary loop is triangulated as a fan from its centroid, with the
    cap normal oriented away from the body centroid so windings stay outward.
    Non-planar loops are refused rather than silently fudged.
    """
    tris = _read_stl_tris(src)
    from collections import Counter, defaultdict

    edges: Counter = Counter()
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
    boundary = [e for e, n in edges.items() if n == 1]
    # On a HALF hull the boundary is one L-shaped loop spanning the
    # centreplane AND the deck, so it is genuinely non-planar. Only the deck
    # needs capping — the symmetry patch closes the centreplane — hence the
    # option to cap just the loop lying in one plane.
    if only_axis is not None:
        boundary = [e for e in boundary
                    if all(abs(p[only_axis] - only_value) < only_tol
                           for p in e)]

    # chain boundary edges into closed loops
    adj: dict = defaultdict(list)
    for a, b in boundary:
        adj[a].append(b)
        adj[b].append(a)
    unused = set(boundary)
    loops: list = []
    while unused:
        a, b = next(iter(unused))
        unused.discard((a, b))
        loop = [a, b]
        while True:
            cur = loop[-1]
            nxt = None
            for cand in adj[cur]:
                e = tuple(sorted((cur, cand)))
                if e in unused:
                    nxt = cand
                    unused.discard(e)
                    break
            if nxt is None:
                break
            if nxt == loop[0]:
                break
            loop.append(nxt)
        if len(loop) >= 3:
            loops.append(loop)

    body_c = np.array([p for t in tris for p in t]).mean(axis=0)
    capped = list(tris)
    made = 0
    for loop in loops:
        pts = np.array(loop)
        c = pts.mean(axis=0)
        # plane fit: smallest singular vector is the normal
        _, sv, vt = np.linalg.svd(pts - c)
        if sv[-1] / max(sv[0], 1e-12) > planar_tol * 100:
            raise ValueError(
                f"boundary loop of {len(loop)} points is not planar "
                f"(flatness {sv[-1]:.3e}); refusing to cap it blindly")
        n = vt[-1]
        if np.dot(n, c - body_c) < 0:      # point the cap outward
            n = -n
        for tri in _triangulate_polygon(pts, vt[0], vt[1], n):
            capped.append(tri)
            made += 1

    _write_stl(capped, dst)
    return {"loops_capped": len(loops), "triangles_added": made,
            "n_tris": len(capped)}


def resistance_coefficient(drag: float, wetted_area: float, speed: float,
                           rho: float = 998.8) -> float:
    """C_t = R_t / (0.5 rho S U^2) — the form Tokyo-2015 reports."""
    if wetted_area <= 0 or speed <= 0:
        raise ValueError("wetted_area and speed must be positive")
    return abs(drag) / (0.5 * rho * wetted_area * speed ** 2)


@dataclass(frozen=True)
class GCIReport:
    f_fine: float
    f_extrapolated: float     # Richardson estimate at h -> 0
    p_observed: float         # observed convergence order
    gci_fine_pct: float       # Roache GCI (Fs=1.25), percent of fine value
    method: str


def gci(f_coarse: float, f_medium: float, f_fine: float,
        refinement: float = 2.0 ** 0.5) -> GCIReport:
    """Roache GCI from three systematically refined grids (r = h_c/h_f)."""
    e21 = f_medium - f_fine
    e32 = f_coarse - f_medium
    if abs(e21) < 1e-12 or e32 * e21 <= 0:
        # oscillatory or converged-to-machine: report conservative bound
        spread = max(abs(e21), abs(e32))
        return GCIReport(f_fine, f_fine, float("nan"),
                         100.0 * 1.25 * spread / max(abs(f_fine), 1e-12),
                         "oscillatory: spread bound, Fs=1.25")
    p = math.log(abs(e32 / e21)) / math.log(refinement)
    p = min(max(p, 0.5), 4.0)              # clamp to sane observed orders
    f_exact = f_fine - e21 / (refinement**p - 1.0)
    gci_pct = 100.0 * 1.25 * abs(e21 / f_fine) / (refinement**p - 1.0)
    return GCIReport(f_fine, f_exact, p, gci_pct,
                     "Roache GCI, Fs=1.25, Richardson p (clamped 0.5..4)")
