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
        fx.append(nums[1] + nums[4])       # pressure-x + viscous-x
    return np.array(t), np.array(fx)


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


def cap_planar_holes(src: str | Path, dst: str | Path,
                     planar_tol: float = 1e-4) -> dict:
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
        for i in range(len(loop)):
            a, b = pts[i], pts[(i + 1) % len(loop)]
            tri = (tuple(c), tuple(a), tuple(b))
            if np.dot(np.cross(a - c, b - c), n) < 0:
                tri = (tuple(c), tuple(b), tuple(a))
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
