"""STL forensics — what the MESHER is handed, measured on the triangles.

WHY THIS EXISTS. `navalai.cfd.case.stl_watertight_report` answers exactly one
question — is the surface a closed 2-manifold with consistent winding — and it
answers it well. It is silent on every other way a triangulation can be a bad
input to snappyHexMesh: sliver triangles, 200:1 aspect ratios, facets coarser
than the cell that has to snap to them, and SELF-INTERSECTIONS, which a closed,
correctly-wound manifold can have and which `stl_watertight_report` cannot see
by construction (it keys on edge counts, and a surface that passes through
itself still gives every edge exactly two faces).

The motivating observation, and the reason the module is written as a
measurement rather than a fix (docs/LESSONS.md: "we have twice shipped a
mechanism the data later refuted"): four grammar hulls whose mesh outcomes
differ came out of `hull_to_stl` with EXACTLY 5244 triangles each, across a 3x
range of enclosed volume, all four reported watertight/outward/0 open edges/0
winding conflicts. Whatever separates them, `stl_watertight_report` cannot see
it. This module measures the rest of the surface so the question can be settled
by AUC rather than by story.

NOTHING HERE IS A GATE AND NOTHING HERE CHANGES THE PIPELINE. `validate_stl`
returns numbers; `auc` and `family_wise_p` score them; the interpretation lives
in `docs/research/STL.md`. No threshold in this file is enforced anywhere.

CONFIGURATION, SAID OUT LOUD (docs/LESSONS.md defect class 6): the triangulation
a metric is measured on is an argument, never an assumption. This module
measures at nx=80, nz=16 (5244 triangles) because that is where the observation
above was made, and it takes both as ARGUMENTS (`nx_default`, `nz_default`) so
the configuration travels with the number.

`hull_to_stl`'S BARE DEFAULT IS NO LONGER 80x16, AND THIS PARAGRAPH SAID IT WAS
UNTIL 2026-08-13. The girth default is now derived from the hull's bilge shape
(`case.stl_girth_resolution`): 16 for a hard chine, 96 for a fillet. A fixed 16
under-enclosed a filleted hull by 0.71% against the 0.35% bar that
`tests/test_end_to_end_flow.py` applies to it. The 5244 figure is therefore a
HISTORICAL observation at a named triangulation, not a description of what the
function returns today — which is exactly the distinction this paragraph exists
to enforce, and it had drifted in its own file. The SHIPPED case is whatever
`stl_resolution` returns for that hull — at scale 1.0 that is nx=600, nz=120
(288956 triangles), because the unclamped request is 811 for every hull and the
600 ceiling binds. Those are different surfaces and a finding on one is not a
finding on the other. Every dict this module returns carries `nx`/`nz`.
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------
# Reading the surface
# --------------------------------------------------------------------------


def load_stl(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Parse an ascii STL into (verts (N,3) float, tris (M,3) int), WELDED.

    Reads the file `snappyHexMesh` will read, not the array it came from, so a
    defect introduced by the `%.6e` formatting in `hull_to_stl` is visible.
    Welding is exact-on-the-written-decimal, which is what `triSurfaceMesh`
    does at its default merge tolerance for coordinates that came from a
    shared grid point.
    """
    xs: list[tuple[float, float, float]] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            xs.append(tuple(float(v) for v in line.split()[1:4]))
    raw = np.asarray(xs, dtype=float)
    if raw.size == 0 or len(raw) % 3:
        raise ValueError(f"{path}: {len(raw)} vertex lines is not a whole "
                         "number of triangles")
    return weld(raw, np.arange(len(raw)).reshape(-1, 3))


def mesh_of_hull(hull, nx: int, nz: int) -> tuple[np.ndarray, np.ndarray]:
    """(verts, tris) for `hull` at `nx` x `nz`, WELDED.

    Delegates to `Hull.closed_mesh` — the ONE definition of the CFD surface —
    and only welds its output. `closed_mesh` emits three fresh vertices per
    triangle (`vid` appends unconditionally), so 288956 triangles arrive as
    866868 vertex rows; topology is undefined until they are merged.
    """
    verts, tris = hull.closed_mesh(nx=nx, nz=nz)
    return weld(np.asarray(verts, dtype=float), np.asarray(tris, dtype=int))


def weld(verts: np.ndarray, tris: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Merge bit-identical vertices; returns (verts, tris) re-indexed."""
    uniq, inv = np.unique(verts, axis=0, return_inverse=True)
    return uniq, np.asarray(inv, dtype=int).reshape(-1)[tris.reshape(-1)].reshape(-1, 3)


# --------------------------------------------------------------------------
# Per-triangle and per-edge quantities
# --------------------------------------------------------------------------


def triangle_quantities(V: np.ndarray, T: np.ndarray) -> dict:
    """Areas, edge lengths, minimum angle and aspect ratio, per triangle.

    ASPECT RATIO is longest edge / (2*sqrt(3) * inradius) — NORMALISED so that
    an equilateral triangle scores exactly 1.0 and a sliver grows without
    bound. NOT longest/shortest edge, which is 1.0 for a needle folded back on
    itself and therefore cannot see the worst facet shape there is. The
    normalisation is fenced by `tests/test_stl_forensics.py`, because an
    unnormalised version reads sqrt(3) = 1.732 on a perfect triangle and any
    bar quoted against it would be wrong by that factor.
    """
    p0, p1, p2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    e = np.stack([np.linalg.norm(p1 - p0, axis=1),
                  np.linalg.norm(p2 - p1, axis=1),
                  np.linalg.norm(p0 - p2, axis=1)], axis=1)
    cr = np.cross(p1 - p0, p2 - p0)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    s = 0.5 * e.sum(axis=1)
    # inradius = area / s ; aspect = longest / (2*sqrt(3) * inradius)
    inr = np.divide(area, np.where(s > 0, s, 1.0))
    aspect = np.divide(e.max(axis=1),
                       np.where(inr > 0, 2.0 * math.sqrt(3.0) * inr, np.nan))
    # smallest angle sits opposite the shortest edge; law of cosines
    a = np.sort(e, axis=1)
    den = 2.0 * a[:, 1] * a[:, 2]
    cosmin = np.divide(a[:, 1] ** 2 + a[:, 2] ** 2 - a[:, 0] ** 2,
                       np.where(den > 0, den, np.nan))
    ang = np.degrees(np.arccos(np.clip(cosmin, -1.0, 1.0)))
    return {"area": area, "edges": e, "aspect": aspect, "min_angle_deg": ang,
            "centroid": (p0 + p1 + p2) / 3.0, "normal_raw": cr}


def edge_table(T: np.ndarray) -> dict:
    """Undirected edge topology, vectorised.

    Returns `uv` (E,2) sorted endpoint pairs, `count` (E,) incident-triangle
    counts, and `t0`/`t1` (E,) triangle indices (`t1` is -1 where count != 2).
    A dict-of-lists version of this cost ~2 s per hull at the shipped 288956
    triangles, which is 50 s over the 25-hull batch for topology alone.
    """
    a = T[:, [0, 1, 2]].reshape(-1)
    b = T[:, [1, 2, 0]].reshape(-1)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    tri = np.repeat(np.arange(len(T)), 3)
    order = np.lexsort((hi, lo))
    lo, hi, tri = lo[order], hi[order], tri[order]
    new = np.empty(len(lo), dtype=bool)
    new[0] = True
    new[1:] = (lo[1:] != lo[:-1]) | (hi[1:] != hi[:-1])
    gid = np.cumsum(new) - 1
    E = int(gid[-1]) + 1
    count = np.bincount(gid, minlength=E)
    first = np.nonzero(new)[0]
    t0 = tri[first]
    t1 = np.full(E, -1, dtype=int)
    two = count == 2
    t1[two] = tri[first[two] + 1]
    return {"uv": np.stack([lo[first], hi[first]], axis=1), "count": count,
            "t0": t0, "t1": t1}


def normal_jumps(V: np.ndarray, T: np.ndarray,
                 et: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(angle_deg, edge_midpoint_x) over every MANIFOLD edge.

    The angle between the two incident face normals — the quantity
    `surfaceFeatureExtract` thresholds. OpenFOAM's `includedAngle A` marks an
    edge when the angle BETWEEN THE FACES is below A, i.e. when this normal
    deviation exceeds 180 - A. The case writes `includedAngle 150`, so the bar
    is 30 degrees (`navalai/cfd/case.py::SURFACE_FEATURES`).
    """
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    ln = np.linalg.norm(n, axis=1)
    n = np.divide(n, np.where(ln > 1e-300, ln, 1.0)[:, None])
    e = et if et is not None else edge_table(T)
    two = e["count"] == 2
    if not two.any():
        return np.zeros(0), np.zeros(0)
    ii, jj = e["t0"][two], e["t1"][two]
    ang = np.degrees(np.arccos(np.clip(np.sum(n[ii] * n[jj], axis=1), -1.0, 1.0)))
    ang[(ln[ii] <= 1e-300) | (ln[jj] <= 1e-300)] = np.nan
    uv = e["uv"][two]
    return ang, 0.5 * (V[uv[:, 0], 0] + V[uv[:, 1], 0])


def feature_edges(V: np.ndarray, T: np.ndarray, included_angle: float = 150.0,
                  et: dict | None = None) -> dict:
    """Replicate `surfaceFeatureExtract extractFromSurface`.

    Returns the edge set snappy is handed as `hull.eMesh` and refines to
    `_HULL_REFINE[1]`. An OPEN or NON-MANIFOLD edge is always a feature edge in
    OpenFOAM regardless of angle; here the hull is closed, so in practice this
    is the dihedral test alone — but the open/non-manifold count is returned so
    a surface that is not closed cannot be silently scored as if it were.
    """
    e = et if et is not None else edge_table(T)
    ang, xm = normal_jumps(V, T, e)
    bar = 180.0 - included_angle
    is_feat = np.isfinite(ang) & (ang > bar)
    other = int(np.sum(e["count"] != 2))
    uv = e["uv"][e["count"] == 2][is_feat]
    lens = np.linalg.norm(V[uv[:, 0]] - V[uv[:, 1]], axis=1) if len(uv) else np.zeros(0)
    return {"included_angle_deg": included_angle, "normal_jump_bar_deg": bar,
            "n_manifold_edges": int(np.sum(e["count"] == 2)),
            "n_feature_edges": int(is_feat.sum()) + other,
            "n_nonmanifold_or_open_edges": other,
            "feature_edge_total_length_m": float(lens.sum()),
            "feature_angle_deg": ang[is_feat],
            "feature_x": xm[is_feat],
            "all_jump_deg": ang, "all_jump_x": xm}


# --------------------------------------------------------------------------
# Self-intersection
# --------------------------------------------------------------------------


def _segment_hits_triangle(P: np.ndarray, Q: np.ndarray, A: np.ndarray,
                           B: np.ndarray, C: np.ndarray,
                           eps: float) -> np.ndarray:
    """Vectorised Moller-Trumbore, STRICT interior, segment parameter in (0,1).

    Strictness is what makes this usable on a welded lofted surface: adjacent
    facets share whole edges and touch at vertices everywhere, and a test that
    counts boundary contact reports the entire hull as self-intersecting.
    """
    e1, e2 = B - A, C - A
    d = Q - P
    h = np.cross(d, e2)
    a = np.sum(e1 * h, axis=1)
    ok = np.abs(a) > eps
    f = np.divide(1.0, np.where(ok, a, 1.0))
    s = P - A
    u = f * np.sum(s * h, axis=1)
    q = np.cross(s, e1)
    v = f * np.sum(d * q, axis=1)
    t = f * np.sum(e2 * q, axis=1)
    return (ok & (u > eps) & (v > eps) & (u + v < 1.0 - eps)
            & (t > eps) & (t < 1.0 - eps))


def self_intersections(V: np.ndarray, T: np.ndarray,
                       cell: float | None = None,
                       max_pairs: int = 40_000_000) -> dict:
    """Count triangle pairs that pass THROUGH each other.

    Broad phase is a uniform spatial hash over triangle AABBs; narrow phase is
    six strict segment-triangle tests per candidate pair. Pairs sharing a
    vertex are dropped before the narrow phase.

    THE FAILURE MODE OF THIS FUNCTION IS FALSE NEGATIVES, and it is stated
    rather than defaulted (docs/LESSONS.md defect class 1): coplanar overlaps
    are NOT detected by a segment test, so `coplanar_candidate_pairs` is
    returned separately and a caller must not read 0 intersections as proof of
    a clean surface without also reading that. If the broad phase exceeds
    `max_pairs` the function returns `complete: False` and the count is a LOWER
    BOUND — it does not silently truncate into a passing number.
    """
    q = triangle_quantities(V, T)
    P = V[T]                                    # (M,3,3)
    lo, hi = P.min(axis=1), P.max(axis=1)
    med = float(np.median(q["edges"]))
    h = cell if cell and cell > 0 else max(4.0 * med, 1e-9)
    gl = np.floor(lo / h).astype(np.int64)
    gh = np.floor(hi / h).astype(np.int64)
    span = gh - gl + 1
    n_entries = int(span.prod(axis=1).sum())
    if n_entries > max_pairs:
        return {"complete": False, "n_self_intersecting_pairs": -1,
                "candidate_pairs": -1, "coplanar_candidate_pairs": -1,
                "note": f"broad phase would need {n_entries} entries; NOT MEASURED"}

    # Bucket assignment. The common case (a triangle inside one grid cell) is
    # done with array ops; only the few wide facets — the deck lid and transom
    # cap span the FULL BEAM in one quad — fall through to the Python loop.
    single = (span == 1).all(axis=1)
    keys = [gl[single]]
    tids = [np.nonzero(single)[0]]
    for t in np.nonzero(~single)[0]:
        gx, gy, gz = (np.arange(gl[t, d], gh[t, d] + 1) for d in range(3))
        blk = np.stack(np.meshgrid(gx, gy, gz, indexing="ij"), axis=-1).reshape(-1, 3)
        keys.append(blk)
        tids.append(np.full(len(blk), t, dtype=int))
    K = np.concatenate(keys, axis=0)
    tid = np.concatenate(tids, axis=0)
    _, cellid = np.unique(K, axis=0, return_inverse=True)
    cellid = np.asarray(cellid).reshape(-1)
    order = np.argsort(cellid, kind="stable")
    cellid, tid = cellid[order], tid[order]
    bounds = np.nonzero(np.concatenate([[True], cellid[1:] != cellid[:-1], [True]]))[0]
    lo_i, hi_i = bounds[:-1], bounds[1:]
    sizes = hi_i - lo_i
    keep = sizes > 1
    if int((sizes[keep] * (sizes[keep] - 1) // 2).sum()) > max_pairs:
        return {"complete": False, "n_self_intersecting_pairs": -1,
                "candidate_pairs": -1, "coplanar_candidate_pairs": -1,
                "note": "candidate set exceeded max_pairs; NOT MEASURED"}
    chunks = []
    for a, b in zip(lo_i[keep], hi_i[keep]):
        g = tid[a:b]
        i, j = np.triu_indices(len(g), 1)
        chunks.append(np.stack([g[i], g[j]], axis=1))
    if not chunks:
        return {"complete": True, "n_self_intersecting_pairs": 0,
                "candidate_pairs": 0, "coplanar_candidate_pairs": 0,
                "pairs": [], "note": ""}
    pr = np.concatenate(chunks, axis=0)
    pr = np.unique(np.sort(pr, axis=1), axis=0)
    cand = pr
    # drop pairs sharing a vertex — adjacency is not self-intersection
    ta, tb = T[pr[:, 0]], T[pr[:, 1]]
    shares = np.zeros(len(pr), dtype=bool)
    for k in range(3):
        for m in range(3):
            shares |= ta[:, k] == tb[:, m]
    pr = pr[~shares]
    if len(pr) == 0:
        return {"complete": True, "n_self_intersecting_pairs": 0,
                "candidate_pairs": len(cand), "coplanar_candidate_pairs": 0,
                "pairs": [], "note": ""}

    eps = 1e-12
    A0, A1, A2 = V[T[pr[:, 0], 0]], V[T[pr[:, 0], 1]], V[T[pr[:, 0], 2]]
    B0, B1, B2 = V[T[pr[:, 1], 0]], V[T[pr[:, 1], 1]], V[T[pr[:, 1], 2]]
    hit = np.zeros(len(pr), dtype=bool)
    for (S0, S1, C0, C1, C2) in (
            (A0, A1, B0, B1, B2), (A1, A2, B0, B1, B2), (A2, A0, B0, B1, B2),
            (B0, B1, A0, A1, A2), (B1, B2, A0, A1, A2), (B2, B0, A0, A1, A2)):
        hit |= _segment_hits_triangle(S0, S1, C0, C1, C2, eps)
    # coplanar candidates the segment test is blind to
    na = np.cross(A1 - A0, A2 - A0)
    nb = np.cross(B1 - B0, B2 - B0)
    lna = np.linalg.norm(na, axis=1)
    lnb = np.linalg.norm(nb, axis=1)
    good = (lna > 0) & (lnb > 0)
    cop = np.zeros(len(pr), dtype=bool)
    cop[good] = (np.linalg.norm(np.cross(na[good], nb[good]), axis=1)
                 / (lna[good] * lnb[good])) < 1e-9
    return {"complete": True,
            "n_self_intersecting_pairs": int(hit.sum()),
            "candidate_pairs": int(len(cand)),
            "coplanar_candidate_pairs": int(cop.sum()),
            "pairs": pr[hit][:200].tolist(), "note": ""}


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def _pct(a: np.ndarray, p: float) -> float:
    return float(np.percentile(a, p)) if a.size else float("nan")


def _along_x(x: np.ndarray, v: np.ndarray, lwl: float, nbins: int = 20,
             how: str = "max") -> list[float]:
    """`v` reduced into `nbins` equal bins of x/LWL — where a metric lives."""
    if x.size == 0:
        return [float("nan")] * nbins
    idx = np.clip((x / max(lwl, 1e-9) * nbins).astype(int), 0, nbins - 1)
    out = []
    for b in range(nbins):
        s = v[idx == b]
        s = s[np.isfinite(s)]
        if s.size == 0:
            out.append(float("nan"))
        elif how == "max":
            out.append(float(s.max()))
        elif how == "median":
            out.append(float(np.median(s)))
        else:
            out.append(float(s.sum()))
    return out


def validate_stl(source, hull_cell_m: float | None = None,
                 lwl: float | None = None, nbins: int = 20,
                 nx: int | None = None, nz: int | None = None,
                 do_self_intersection: bool = True) -> dict:
    """Everything measurable about the surface handed to snappyHexMesh.

    `source` is a path to an ascii STL, or a (verts, tris) pair already welded
    by `mesh_of_hull`. `hull_cell_m` is the cell the surface will actually snap
    to — pass `navalai.admissibility._pipeline_scales(...)["cell"]`, which
    derives it from `_HULL_REFINE` and `_NX_BASE` rather than restating them.
    Omit it and every `*_over_cell` entry is `None`, never a default: an
    unmeasurable value is not a good one (docs/LESSONS.md defect class 1).
    """
    if isinstance(source, (str, Path)):
        V, T = load_stl(source)
    else:
        V, T = source
        V, T = np.asarray(V, dtype=float), np.asarray(T, dtype=int)
    q = triangle_quantities(V, T)
    e = q["edges"]
    L = float(lwl) if lwl else float(V[:, 0].max() - V[:, 0].min())
    et = edge_table(T)
    ang, xm = normal_jumps(V, T, et)
    feat = feature_edges(V, T, 150.0, et)

    cent_x = q["centroid"][:, 0]
    emax = e.max(axis=1)
    zero = q["area"] <= 0.0
    degen = ~np.isfinite(q["min_angle_deg"]) | (q["min_angle_deg"] < 1.0)
    tri_keys = Counter(tuple(sorted(t)) for t in T.tolist())
    dup_tris = sum(n - 1 for n in tri_keys.values() if n > 1)

    rep = {
        "nx": nx, "nz": nz, "lwl_m": L,
        "n_tris": int(len(T)), "n_verts": int(len(V)),
        "hull_cell_m": hull_cell_m,
        # --- edges
        "edge_min_m": float(e.min()), "edge_median_m": float(np.median(e)),
        "edge_p95_m": _pct(e, 95), "edge_max_m": float(e.max()),
        # --- triangle shape
        "min_angle_deg": float(np.nanmin(q["min_angle_deg"])),
        "min_angle_p1_deg": _pct(q["min_angle_deg"][np.isfinite(q["min_angle_deg"])], 1),
        "aspect_max": float(np.nanmax(q["aspect"])),
        "aspect_p95": _pct(q["aspect"][np.isfinite(q["aspect"])], 95),
        "aspect_median": float(np.nanmedian(q["aspect"])),
        "area_min_m2": float(q["area"].min()), "area_max_m2": float(q["area"].max()),
        "area_median_m2": float(np.median(q["area"])),
        "n_zero_area_tris": int(zero.sum()),
        "n_degenerate_tris": int(degen.sum()),
        "n_duplicate_tris": int(dup_tris),
        "n_duplicate_verts_welded": int(3 * len(T) - len(V)),
        # --- curvature / creases
        "normal_jump_max_deg": float(np.nanmax(ang)) if ang.size else float("nan"),
        "normal_jump_p99_deg": _pct(ang[np.isfinite(ang)], 99),
        "normal_jump_median_deg": float(np.nanmedian(ang)) if ang.size else float("nan"),
        "frac_edges_jump_over_30deg": float(np.mean(ang > 30.0)) if ang.size else float("nan"),
        "frac_edges_jump_over_60deg": float(np.mean(ang > 60.0)) if ang.size else float("nan"),
        # --- feature edges (Phase 3)
        "n_feature_edges": feat["n_feature_edges"],
        "feature_edge_total_length_m": feat["feature_edge_total_length_m"],
        "feature_edge_density_per_m": feat["feature_edge_total_length_m"] / max(L, 1e-9),
        "n_nonmanifold_or_open_edges": feat["n_nonmanifold_or_open_edges"],
        # --- distribution along x
        "x_bins": nbins,
        "edge_max_along_x": _along_x(cent_x, emax, L, nbins, "max"),
        "aspect_max_along_x": _along_x(cent_x, q["aspect"], L, nbins, "max"),
        "min_angle_min_along_x": [(-v if np.isfinite(v) else v) for v in
                                  _along_x(cent_x, -q["min_angle_deg"], L, nbins, "max")],
        "jump_max_along_x": _along_x(xm, ang, L, nbins, "max"),
        "feature_edges_along_x": _along_x(feat["feature_x"],
                                          np.ones_like(feat["feature_x"]),
                                          L, nbins, "sum"),
        "x_of_max_edge": float(cent_x[np.argmax(emax)]) / max(L, 1e-9),
        "x_of_max_aspect": float(cent_x[np.nanargmax(q["aspect"])]) / max(L, 1e-9),
    }
    if hull_cell_m:
        c = float(hull_cell_m)
        over = emax / c
        rep.update({
            "edge_over_cell_median": float(np.median(e / c)),
            "edge_over_cell_p95": _pct(e / c, 95),
            "edge_over_cell_max": float(over.max()),
            "frac_tris_coarser_than_cell": float(np.mean(over > 1.0)),
            "frac_tris_over_4_cells": float(np.mean(over > 4.0)),
            "edge_over_cell_max_along_x": _along_x(cent_x, over, L, nbins, "max"),
            "frac_coarse_along_x": _along_x(cent_x, (over > 1.0).astype(float),
                                            L, nbins, "median"),
        })
    else:
        for k in ("edge_over_cell_median", "edge_over_cell_p95",
                  "edge_over_cell_max", "frac_tris_coarser_than_cell",
                  "frac_tris_over_4_cells"):
            rep[k] = None

    if do_self_intersection:
        si = self_intersections(V, T, cell=4.0 * float(np.median(e)))
        rep["self_intersection"] = {k: v for k, v in si.items() if k != "pairs"}
        rep["n_self_intersecting_pairs"] = si["n_self_intersecting_pairs"]
        rep["self_intersection_complete"] = si["complete"]
    else:
        rep["self_intersection"] = {"complete": False, "note": "not requested"}
        rep["n_self_intersecting_pairs"] = None
        rep["self_intersection_complete"] = False
    return rep


# --------------------------------------------------------------------------
# Scoring — AUC with a family-wise permutation correction
# --------------------------------------------------------------------------


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """P(score of a positive > score of a negative), ties counted as 0.5.

    Mann-Whitney U / (n1 n0). Returns nan when either class is empty or the
    scores are not finite — never 0.5, because "could not be computed" and
    "computed and found to be chance" are different answers and this repo has
    paid for conflating them.
    """
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels).astype(bool)
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    if y.sum() == 0 or (~y).sum() == 0:
        return float("nan")
    from scipy.stats import rankdata
    r = rankdata(s)
    n1 = int(y.sum())
    return float((r[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * (len(s) - n1)))


def family_wise_p(metrics: dict[str, np.ndarray], labels: np.ndarray,
                  n_perm: int = 20000, seed: int = 0) -> dict:
    """Permutation p-value for max |AUC - 0.5| over the WHOLE family.

    The correction LAYERS.md §2.1 used, applied to a different family. It is
    the only honest way to report a best-of-N AUC: with 25 hulls, 6 positives
    and 30 metrics, an AUC of 0.85 arises by chance often enough that quoting
    it uncorrected is a finding about the number of metrics tried.

    Returns the per-metric AUC, the family-wise p of the family MAXIMUM, and a
    per-metric family-wise p (the probability that the family maximum under the
    null reaches at least THAT metric's deviation) — which is the number a
    reader wants beside each row.
    """
    names = list(metrics)
    y = np.asarray(labels).astype(bool)
    n, n1 = len(y), int(y.sum())
    if n1 == 0 or n1 == n:
        raise ValueError("labels must contain both classes")
    from scipy.stats import rankdata
    R = np.zeros((len(names), n))
    usable = np.ones(len(names), dtype=bool)
    for k, nm in enumerate(names):
        v = np.asarray(metrics[nm], dtype=float)
        if v.shape != (n,) or not np.isfinite(v).all() or np.ptp(v) == 0:
            usable[k] = False
            continue
        R[k] = rankdata(v)
    obs = np.array([auc(np.asarray(metrics[nm], dtype=float), y)
                    if usable[k] else np.nan for k, nm in enumerate(names)])
    dev = np.abs(obs - 0.5)
    rng = np.random.default_rng(seed)
    Ru = R[usable]
    denom = n1 * (n - n1)
    base = n1 * (n1 + 1) / 2.0
    null = np.empty(n_perm)
    for i in range(n_perm):
        pick = rng.permutation(n)[:n1]
        a = (Ru[:, pick].sum(axis=1) - base) / denom
        null[i] = np.abs(a - 0.5).max()
    fw = {nm: float((np.sum(null >= dev[k]) + 1) / (n_perm + 1))
          if np.isfinite(dev[k]) else float("nan")
          for k, nm in enumerate(names)}
    best = int(np.nanargmax(dev)) if np.isfinite(dev).any() else -1
    return {"auc": {nm: float(obs[k]) for k, nm in enumerate(names)},
            "family_wise_p": fw, "n_metrics_in_family": int(usable.sum()),
            "n_perm": n_perm,
            "best_metric": names[best] if best >= 0 else None,
            "best_auc": float(obs[best]) if best >= 0 else float("nan"),
            "best_family_wise_p": fw[names[best]] if best >= 0 else float("nan")}


# --------------------------------------------------------------------------
# The correlation study
# --------------------------------------------------------------------------

# The five recorded Gate 2U mesh campaigns. READ ONLY; this module never
# writes them. `cap7` is the arm at the SHIPPED configuration (_MAX_LAYERS 7,
# rung 0) and is the labelling every AUC below is against unless stated.
_CAMPAIGNS = ("data/gate2u-cap7-mesh.json", "data/gate2u-cap5-mesh.json",
              "data/gate2u-cap3-mesh.json", "data/gate2u-campaign-backoff-mesh.json",
              "data/gate2u-campaign-baseline.json")


def runner_bar_fails(row: dict) -> bool:
    """The bar `navalai/cfd/run-case.sh` actually enforces on a mesh.

    0 zero-volume cells, <= 5 wrongly-oriented faces, 0 <= max skewness <= 20.
    A negative skewness is `mesh_robustness.py`'s sentinel for "not measured"
    and is a FAILURE here, not a pass (docs/LESSONS.md defect class 1).
    """
    sk = row.get("max_skewness", -1.0)
    return (row.get("zero_volume_cells", 1) > 0 or row.get("wrong_oriented", 99) > 5
            or not (0.0 <= sk <= 20.0))


def campaign_labels(root: str | Path = ".") -> dict:
    """Per-hull outcome labels assembled from the recorded campaigns."""
    import json
    root = Path(root)
    arms = {}
    for f in _CAMPAIGNS:
        p = root / f
        if p.exists():
            arms[Path(f).stem] = json.loads(p.read_text())
    cap7 = {r["hull"]: r for r in arms["gate2u-cap7-mesh"]["rows"]}
    tried: dict[int, dict[int, bool]] = {}
    for name, d in arms.items():
        for r in d["rows"]:
            tried.setdefault(r["hull"], {})[r.get("n_layers_used", -1)] = \
                not runner_bar_fails(r)
    return {
        "cap7_fails_runner_bar": {h: runner_bar_fails(r) for h, r in cap7.items()},
        "cap7_fails_strict": {h: not r["meshed"] for h, r in cap7.items()},
        "no_admissible_rung": {h: (len(v) >= 3 and not any(v.values()))
                               for h, v in tried.items()},
        "rungs_tried": {h: dict(sorted(v.items())) for h, v in tried.items()},
    }


def study(n: int = 25, seed: int = 0, speed: float = 2.57, scale: float = 1.0,
          nx_default: int = 80, nz_default: int = 16, root: str | Path = ".",
          n_perm: int = 20000) -> dict:
    """Phase 1-3: measure every seed-`seed` hull's STL and score it.

    Measures at TWO triangulations — the one the case writes
    (`stl_resolution`, nx=600/nz=120 at scale 1.0) and the 80x16 grid the
    observation that started this pass was made on, which the pipeline does not
    use.

    80x16 WAS `hull_to_stl`'s bare default when this was written and is not any
    more (see the module header): the girth count is now derived from the
    hull's bilge shape. Both are still ARGUMENTS here, so this function keeps
    measuring the grid the finding belongs to rather than silently following a
    default that has moved underneath it — pass `nz_default` explicitly to
    measure anything else.
    """
    from .admissibility import _pipeline_scales
    from .evaluate import sample_valid
    from .geometry import Hull
    from .mission import MissionSpec

    X, _ = sample_valid(n, MissionSpec(), seed=seed)
    hulls, rows = [], []
    for i in range(n):
        h = Hull(np.asarray(X[i], dtype=float))
        lwl = float(h.x[-1])
        sc = _pipeline_scales(lwl, speed, scale)
        rep_ship = validate_stl(mesh_of_hull(h, sc["nx"], sc["nz"]),
                                hull_cell_m=sc["cell"], lwl=lwl,
                                nx=sc["nx"], nz=sc["nz"])
        rep_def = validate_stl(mesh_of_hull(h, nx_default, nz_default),
                               hull_cell_m=sc["cell"], lwl=lwl,
                               nx=nx_default, nz=nz_default)
        rows.append({"hull": i, "lwl": lwl, "cell": sc["cell"],
                     "stack": sc["stack"], "n_layers": sc["n_layers"],
                     "shipped": rep_ship, "default80x16": rep_def})
        hulls.append(h)

    lab = campaign_labels(root)
    fam = _feature_family(rows)
    out = {"n": n, "seed": seed, "speed": speed, "scale": scale,
           "rows": rows, "labels": lab, "metrics": {k: list(v) for k, v in fam.items()}}
    for name in ("cap7_fails_runner_bar", "cap7_fails_strict", "no_admissible_rung"):
        y = np.array([bool(lab[name].get(i, False)) for i in range(n)])
        if y.sum() == 0 or y.sum() == n:
            out[name] = {"note": "labelling has one class only; NOT SCORED"}
            continue
        out[name] = family_wise_p(fam, y, n_perm=n_perm, seed=seed)
        out[name]["n_positive"] = int(y.sum())
        out[name]["positives"] = [int(i) for i in np.nonzero(y)[0]]
    return out


def _feature_family(rows: list[dict]) -> dict[str, np.ndarray]:
    """The metric family scored by AUC. Declared in ONE place so the
    family-wise correction is over exactly the family that was looked at."""
    def col(f):
        return np.array([float(f(r)) for r in rows])

    S = lambda r, k: r["shipped"][k]      # noqa: E731
    D = lambda r, k: r["default80x16"][k]  # noqa: E731
    fam = {
        "edge_median_over_cell": col(lambda r: S(r, "edge_over_cell_median")),
        "edge_p95_over_cell": col(lambda r: S(r, "edge_over_cell_p95")),
        "edge_max_over_cell": col(lambda r: S(r, "edge_over_cell_max")),
        "frac_tris_coarser_than_cell": col(lambda r: S(r, "frac_tris_coarser_than_cell")),
        "frac_tris_over_4_cells": col(lambda r: S(r, "frac_tris_over_4_cells")),
        "edge_max_m": col(lambda r: S(r, "edge_max_m")),
        "edge_min_over_cell": col(lambda r: S(r, "edge_min_m") / r["cell"]),
        "aspect_max": col(lambda r: S(r, "aspect_max")),
        "aspect_p95": col(lambda r: S(r, "aspect_p95")),
        "aspect_median": col(lambda r: S(r, "aspect_median")),
        "min_angle_deg": col(lambda r: S(r, "min_angle_deg")),
        "min_angle_p1_deg": col(lambda r: S(r, "min_angle_p1_deg")),
        "n_degenerate_tris": col(lambda r: S(r, "n_degenerate_tris")),
        "frac_degenerate_tris": col(lambda r: S(r, "n_degenerate_tris") / S(r, "n_tris")),
        "area_max_over_cell2": col(lambda r: S(r, "area_max_m2") / r["cell"] ** 2),
        "area_min_over_cell2": col(lambda r: S(r, "area_min_m2") / r["cell"] ** 2),
        "n_zero_area_tris": col(lambda r: S(r, "n_zero_area_tris")),
        "n_duplicate_tris": col(lambda r: S(r, "n_duplicate_tris")),
        "normal_jump_max_deg": col(lambda r: S(r, "normal_jump_max_deg")),
        "normal_jump_p99_deg": col(lambda r: S(r, "normal_jump_p99_deg")),
        "normal_jump_median_deg": col(lambda r: S(r, "normal_jump_median_deg")),
        "frac_edges_jump_over_30deg": col(lambda r: S(r, "frac_edges_jump_over_30deg")),
        "frac_edges_jump_over_60deg": col(lambda r: S(r, "frac_edges_jump_over_60deg")),
        "n_feature_edges": col(lambda r: S(r, "n_feature_edges")),
        "feature_edge_length_over_lwl": col(
            lambda r: S(r, "feature_edge_total_length_m") / r["lwl"]),
        "feature_edge_length_over_cell": col(
            lambda r: S(r, "feature_edge_total_length_m") / r["cell"]),
        "feature_edges_transom_decile": col(lambda r: S(r, "feature_edges_along_x")[0]),
        "feature_edges_bow_decile": col(lambda r: S(r, "feature_edges_along_x")[-1]),
        "feature_edge_x_concentration": col(
            lambda r: max(S(r, "feature_edges_along_x"))
            / max(1.0, float(np.mean(S(r, "feature_edges_along_x"))))),
        "n_self_intersecting_pairs": col(lambda r: S(r, "n_self_intersecting_pairs")),
        "jump_max_transom_decile": col(lambda r: S(r, "jump_max_along_x")[0]),
        "jump_max_bow_decile": col(lambda r: S(r, "jump_max_along_x")[-1]),
        "aspect_max_transom_decile": col(lambda r: S(r, "aspect_max_along_x")[0]),
        "aspect_max_bow_decile": col(lambda r: S(r, "aspect_max_along_x")[-1]),
        "edge_over_cell_bow_decile": col(
            lambda r: S(r, "edge_over_cell_max_along_x")[-1]),
        # the DEFAULT triangulation, where the 5244-triangle observation was made
        "default_edge_median_over_cell": col(lambda r: D(r, "edge_over_cell_median")),
        "default_aspect_max": col(lambda r: D(r, "aspect_max")),
        "default_n_tris": col(lambda r: D(r, "n_tris")),
        # size, as a control: if a size effect exists it must beat these
        "lwl": col(lambda r: r["lwl"]),
        "stack_over_cell": col(lambda r: r["stack"] / r["cell"]),
    }
    return fam



# --------------------------------------------------------------------------
# Phase 4: look at the triangles
# --------------------------------------------------------------------------


def _edge_segments(V: np.ndarray, T: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(E,2,3) unique undirected edge segments, and their lengths."""
    et = edge_table(T)
    uv = et["uv"]
    seg = np.stack([V[uv[:, 0]], V[uv[:, 1]]], axis=1)
    return seg, np.linalg.norm(seg[:, 1] - seg[:, 0], axis=1)


def render_facets(hull, path, nx: int, nz: int, cell: float,
                  title: str = "", dpi: int = 200):
    """Six orthographic wireframe panels of the ACTUAL triangulation.

    Top / side / front / isometric of the whole hull, then true-scale zooms on
    the last and first 7% of the length — the stem and the transom cap, the two
    places `closed_mesh` builds something structurally different from the
    shell. The zooms are coloured by edge length in units of the level-
    `_HULL_REFINE[1]` hull cell, which is the ratio `case.py`'s own comment
    says must be below 1 ("the STL must be FINER than the cells that snap to
    it") and which the whole-hull panels cannot show because at 600x120 an
    individual facet is sub-pixel.

    No decimation anywhere: a picture of facet density that dropped facets
    would be a picture of the decimation.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    V, T = mesh_of_hull(hull, nx, nz)
    seg, ln = _edge_segments(V, T)
    L = float(V[:, 0].max() - V[:, 0].min())
    ca, sa = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))

    def proj(p, how):
        if how == "top":
            return p[..., [0, 1]]
        if how == "side":
            return p[..., [0, 2]]
        if how == "front":
            return p[..., [1, 2]]
        u = p[..., 0] * ca - p[..., 1] * ca
        v = (p[..., 0] + p[..., 1]) * sa + p[..., 2]
        return np.stack([u, v], axis=-1)

    fig, ax = plt.subplots(2, 3, figsize=(16.5, 8.0))
    for a, how, lab in zip(ax[0], ("top", "side", "front"),
                           ("top (x-y)", "side (x-z)", "front (y-z)")):
        a.add_collection(LineCollection(proj(seg, how), linewidths=0.04,
                                        colors="k", alpha=0.55, rasterized=True))
        a.set_title(lab, fontsize=9)
    ax[1, 0].add_collection(LineCollection(proj(seg, "iso"), linewidths=0.04,
                                           colors="k", alpha=0.55, rasterized=True))
    ax[1, 0].set_title("isometric", fontsize=9)

    x0 = V[:, 0].min()
    for a, (lo, hi, lab) in zip(ax[1, 1:], ((0.93, 1.001, "stem, last 7% of L"),
                                            (-0.001, 0.07, "transom, first 7% of L"))):
        xm = 0.5 * (seg[:, 0, 0] + seg[:, 1, 0])
        m = ((xm - x0) / L >= lo) & ((xm - x0) / L <= hi)
        lc = LineCollection(proj(seg[m], "iso"), linewidths=0.25,
                            array=np.log10(np.maximum(ln[m] / cell, 1e-3)),
                            cmap="viridis", rasterized=True)
        lc.set_clim(-1.0, 2.0)
        a.add_collection(lc)
        a.set_title(f"{lab} — colour = log10(edge / hull cell)", fontsize=8)
        fig.colorbar(lc, ax=a, fraction=0.04)

    for a in ax.ravel():
        a.set_aspect("equal")
        a.autoscale_view()
        a.tick_params(labelsize=6)
    fig.suptitle(title or f"{nx}x{nz} = {len(T)} triangles, "
                          f"hull cell {cell * 1000:.1f} mm", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return {"n_tris": int(len(T)), "n_edges": int(len(seg)),
            "edge_over_cell_median": float(np.median(ln) / cell)}


def _main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--perm", type=int, default=20000)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", default="-")
    a = ap.parse_args(argv)
    res = study(a.n, a.seed, a.speed, a.scale, root=a.root, n_perm=a.perm)
    txt = json.dumps(res, indent=1, default=float)
    if a.json == "-":
        print(txt)
    else:
        Path(a.json).write_text(txt)
    return 0


if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(_main())
