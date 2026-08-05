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
    """Force history for a case, merging every RESTART artefact into one file.

    OpenFOAM produces restart fragments in TWO different ways, and missing
    either one reports a fragment as the whole run:

    1. A run resumed at a later time writes a fresh
       postProcessing/forces/<restart-time>/force.dat.
    2. A run restarted at the SAME start time does NOT overwrite force.dat —
       it writes force_0.dat, then force_1.dat, beside it.

    (2) bit us on KCS: force.dat held 18 lines from a run that had DIVERGED
    (t=0.44542 repeated with forces escalating 1e11 -> 1e18 -> 1e24) while the
    live 266-line run sat in force_0.dat next to it, and forces_path returned
    the corpse. Both are collected here; where two files cover the same time,
    the later-written one wins, because that is the run that superseded it.
    """
    root = Path(case) / "postProcessing" / "forces"
    segs = sorted(root.glob("*/force*.dat"),
                  key=lambda p: (float(p.parent.name), _restart_index(p)))
    segs = [s for s in segs if s.name != "force.merged.dat"]
    if not segs:
        raise FileNotFoundError(f"no force*.dat under {root}")
    if len(segs) == 1:
        return segs[0]

    rows: dict[float, str] = {}
    for seg in segs:
        seg_rows: dict[float, str] = {}
        for line in seg.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                seg_rows[float(_NUM.findall(s)[0])] = s
            except (IndexError, ValueError):
                continue
        if not seg_rows:
            continue
        # RESTART SEMANTICS: a run that starts at t0 invalidates everything
        # from t0 onward — those samples belong to an attempt that was
        # superseded. Merging by per-sample overwrite is not enough: the dead
        # KCS run had diverged at t=0.44542 (1e24 N) and the live re-run never
        # sampled that exact instant, so the garbage survived the merge and sat
        # in the record as the largest force in the history.
        t0 = min(seg_rows)
        rows = {t: r for t, r in rows.items() if t < t0}
        rows.update(seg_rows)
    merged = root / "force.merged.dat"
    merged.write_text("\n".join(rows[t] for t in sorted(rows)) + "\n")
    return merged


def _restart_index(p: Path) -> int:
    """Order force.dat < force_0.dat < force_1.dat ... by write order."""
    stem = p.stem
    if "_" not in stem:
        return -1
    try:
        return int(stem.rsplit("_", 1)[1])
    except ValueError:
        return -1


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
    p_raw = math.log(abs(e32 / e21)) / math.log(refinement)
    # THE LOW-END CLAMP WAS ANTI-CONSERVATIVE. Raising a below-first-order p up
    # to 0.5 SHRINKS the reported uncertainty, because GCI ~ 1/(r^p - 1).
    # MEASURED on an exact Richardson triplet at r=sqrt(2) with true p=0.1: the
    # analytic GCI is 6.392% and this function reported 1.191% — an
    # understatement of 5.37x, in precisely the direction that lets a barely
    # converging triplet claim the <=2.5% bar. Roache's own recommendation for
    # a poorly-behaved p is to fall back to first order with the SAFER factor
    # Fs = 3.0, so that is what fires, and the method string says which rule
    # was used. The high-end clamp is conservative and stays.
    if p_raw < 1.0:
        # Keep the OBSERVED order and raise the safety factor. Substituting
        # p = 1 here was still anti-conservative: at p_obs = 0.1 it reported
        # 1.306% against an analytic 6.392%, because 1/(r^p - 1) collapses as p
        # rises. The observed p with Fs = 3.0 gives 15.3% — larger than the
        # Fs=1.25 figure, which is the point: a triplet below first order is
        # not in the asymptotic range and its uncertainty must not look small.
        # p is floored only to keep the denominator finite.
        p, fs = max(p_raw, 0.05), 3.0
        rule = f"p_obs={p_raw:.2f}<1, NOT asymptotic -> Fs=3.0"
    else:
        p, fs, rule = min(p_raw, 4.0), 1.25, "Richardson p (capped at 4), Fs=1.25"
    f_exact = f_fine - e21 / (refinement**p - 1.0)
    gci_pct = 100.0 * fs * abs(e21 / f_fine) / (refinement**p - 1.0)
    return GCIReport(f_fine, f_exact, p, gci_pct, f"Roache GCI, {rule}")


class WaterplaneError(ValueError):
    """The waterplane could not be closed from this geometry.

    A dedicated type so callers can fall back on a GEOMETRY problem without
    also swallowing a file-read failure. Learned the hard way: a binary STL
    raised UnicodeDecodeError, which is a ValueError, which a broad
    `except ValueError` upstream absorbed into a silent fallback.
    """


def stl_waterplane_properties(path, waterline: float = 0.0) -> dict:
    """Waterplane area, LCF and LONGITUDINAL second moment about it.

    Why this exists: the pitch restoring stiffness of a floating body is
    rho*g*I_L, and `sixdof_properties` was approximating I_L as Awp*(L/2)^2.
    MEASURED on the KCS STL: true I_L = 19.854 m^4 giving k_theta = 194539
    N.m/rad, against the approximation's 771030 — **3.96x too stiff**. That put
    the pitch damper at zeta 0.597 instead of the intended 0.30, roughly
    doubling settling time on a run already budgeted in days.

    Method: the closed waterplane is recovered from the hull surface by the
    divergence theorem rather than by cutting the mesh. For the submerged
    volume V bounded by hull + cap, integrating div(F) with F = (0,0,1) gives
    A_wp = -sum(A_i n_z,i) over the HULL triangles below the waterline, because
    the cap's own contribution is what we are solving for. The same trick with
    F = (0,0,x^2) yields the second moment about x=0; the parallel axis then
    moves it to the centre of flotation.
    """
    tris = np.asarray(_read_stl_tris(path), float)
    tris = tris - np.array([0.0, 0.0, waterline])

    kept = []
    for tri in tris:
        z = tri[:, 2]
        if (z <= 0).all():
            kept.append(tri)
            continue
        if (z > 0).all():
            continue
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if a[2] <= 0:
                poly.append(a)
            if (a[2] <= 0) != (b[2] <= 0):
                f = a[2] / (a[2] - b[2])
                poly.append(a + f * (b - a))
        for i in range(1, len(poly) - 1):
            kept.append(np.array([poly[0], poly[i], poly[i + 1]]))
    if not kept:
        raise WaterplaneError("no submerged geometry below the waterline")

    T = np.asarray(kept)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n2 = np.cross(b - a, c - a)          # 2 * area * unit normal
    nz = n2[:, 2] * 0.5                  # signed area projected on z
    xbar = (a[:, 0] + b[:, 0] + c[:, 0]) / 3.0

    awp = -float(nz.sum())
    if awp <= 0:
        raise WaterplaneError(f"non-physical waterplane area {awp:.6g} m^2")
    # int(x) over a triangle IS area * centroid — exact, because x is linear.
    lcf = -float((nz * xbar).sum()) / awp
    # int(x^2) is NOT area * centroid^2. The exact quadrature over a triangle is
    # A * (sum xi^2 + sum_{i<j} xi xj) / 6; using the centroid squared
    # understated a 4 x 2 m box's I_L as 3.556 m^4 against the closed-form
    # B*L^3/12 = 10.667 — a factor of 3, and in the unsafe direction for a
    # stiffness. Caught by the box anchor, which is why the anchor exists.
    x1, x2, x3 = a[:, 0], b[:, 0], c[:, 0]
    x2_quad = (x1 * x1 + x2 * x2 + x3 * x3
               + x1 * x2 + x1 * x3 + x2 * x3) / 6.0
    i_x0 = -float((nz * x2_quad).sum())
    i_l = i_x0 - awp * lcf ** 2
    return {"awp_m2": awp, "lcf": lcf, "i_l_m4": max(i_l, 1e-12)}


def stl_submerged_properties(path, waterline: float = 0.0) -> dict:
    """Submerged volume and its centroid (LCB/TCB/VCB) from a closed STL.

    Why this exists rather than a published LCB percentage: the KCS STL spans
    0..7.7165 m against an Lpp of 7.2786 m — the bulbous bow and the rudder
    reach beyond the perpendiculars — so "-1.48% Lpp from midship" cannot be
    located in this file's coordinates without knowing where the perpendiculars
    fall. The geometry knows, so ask it.

    Method: divergence theorem over the hull triangles BELOW the waterline,
    clipped at it. The waterplane cap can be skipped entirely, which is what
    makes this simple: on that cap the outward normal is +z, so it contributes
    (1/3)(r.n) = z/3 = 0 to the volume, and n_x = n_y = 0 kills its contribution
    to the x and y centroid integrals. Only VCB needs the cap, and it gets it
    because z = waterline there is a constant, handled analytically below.

    Returns {volume_m3, lcb, tcb, vcb} with centroid in the STL's own frame.
    """
    tris = np.asarray(_read_stl_tris(path), float)
    tris = tris - np.array([0.0, 0.0, waterline])      # waterline -> z = 0

    kept = []
    for tri in tris:
        z = tri[:, 2]
        if (z <= 0).all():
            kept.append(tri)
            continue
        if (z > 0).all():
            continue
        # Sutherland-Hodgman against the half-space z <= 0, then fan-triangulate
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if a[2] <= 0:
                poly.append(a)
            if (a[2] <= 0) != (b[2] <= 0):
                f = a[2] / (a[2] - b[2])
                poly.append(a + f * (b - a))
        for i in range(1, len(poly) - 1):
            kept.append(np.array([poly[0], poly[i], poly[i + 1]]))

    if not kept:
        raise ValueError("no submerged geometry below the waterline")
    T = np.asarray(kept)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(b - a, c - a)                       # 2 * area * unit normal

    vol = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    # int x dV = 1/24 * sum n_x * [(a+b)^2 + (b+c)^2 + (c+a)^2]  (componentwise)
    moment = (n * ((a + b) ** 2 + (b + c) ** 2 + (c + a) ** 2)).sum(axis=0) / 24.0
    centroid = moment / (2.0 * vol)

    return {"volume_m3": abs(vol),
            "lcb": float(centroid[0]), "tcb": float(centroid[1]),
            "vcb": float(centroid[2]) + waterline}
