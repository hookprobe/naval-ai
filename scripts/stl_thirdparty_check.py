#!/usr/bin/env python
"""INDEPENDENT third-party validation of the exported hull STLs.

WHY THIS EXISTS (2026-08-12). The project owner opened the 25 exported hulls in
3D-printing software and reported that "some intersections look odd to the eye
-- very odd corners, surfaces". Our own `stl_watertight_report` calls all 25
CLEAN: 0 open/non-manifold edges, 0 winding conflicts, watertight, outward
normals. Both observations cannot be complete, and the reason is that our
checker tests exactly three things -- edge closure, directed-edge winding and
the signed volume. It CANNOT see self-intersection, degenerate slivers,
duplicate geometry, or a facet that misses the analytic surface. A surface can
be closed, manifold and correctly wound and still intersect itself.

So this script asks the SAME questions of three established libraries that have
nothing to do with this repository -- trimesh, PyMeshLab and Open3D -- plus the
triangle-quality and faceting measurements that neither our checker nor those
libraries make. It is DIAGNOSTIC ONLY.

IT DOES NOT REPAIR ANYTHING, BY DESIGN. A repaired STL is no longer the genome
the optimiser proposed: if a repairer fills a hole or deletes self-intersecting
triangles, the evolutionary loop is evaluating a shape it did not generate.
Open3D's `remove_non_manifold_edges()` deletes triangles until the edge is
manifold, which on a hull is "repair by deleting part of the boat". The only
mutation this script performs is MERGING COINCIDENT VERTICES, which moves no
geometry -- and it is mandatory, not optional, because `hull_to_stl` emits one
vertex record per triangle corner (15732 records for 5244 triangles) and every
topology question is meaningless on an unmerged soup. That is measured and
reported rather than assumed; see `--report-unmerged`.

Three phases:
  1. per-hull third-party metrics, incl. self-intersection, which nothing in
     this repository tests, and a volume cross-check against our own
     `stl_watertight_report` signed volume (two independent implementations
     disagreeing is itself a finding);
  2. do any of them SEPARATE the meshing failures recorded in
     data/gate2u-cap7-mesh.json?  AUC with an exact Mann-Whitney p-value and a
     Holm-Bonferroni family-wise correction. 29 of our own geometry metrics
     were already scored this way and the best was AUC 0.842 at p = 0.21 --
     NOT significant. A null result here is reported as a null result;
  3. THE BOW, which is where the owner says the problem is. The stem taper
     `y_sheer = ys * w**0.15` has derivative ~ w**-0.85, i.e. UNBOUNDED as
     breadth goes to zero, and the plan-form `w` switches equation at x_mb with
     a slope jump. Both are prime suspects and both are measured here as
     DISTRIBUTIONS over all 25 hulls, not as a pass/fail.

A note on what a null result in phase 2 does and does not mean, because this
script was written after that distinction was got wrong once: a defect present
in EVERY hull is INVISIBLE TO CORRELATION BY CONSTRUCTION -- there is no
contrast group, so it scores AUC 0.500 however harmful it is. "Does not
separate failures from passes" is not "harmless". Phase 3 therefore reports
distributions and severities, and the closing recommendation is an INTERVENTION
experiment, because an intervention is the only test a universal defect admits.

This is a script, not a test: it adds no gate row. It reads the STLs and
data/gate2u-cap7-mesh.json and writes nothing but its own report.

    python scripts/stl_thirdparty_check.py
    python scripts/stl_thirdparty_check.py --json /tmp/stl3p.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULT_STL_DIR = Path.home() / "Documents" / "naval-ai-stl"
CAP7 = REPO / "data" / "gate2u-cap7-mesh.json"
BACKOFF = REPO / "data" / "gate2u-campaign-backoff-mesh.json"

# The campaign these STLs belong to. Recorded in the JSON they are scored
# against; restated here only so the script can REFUSE a mismatched pairing.
CAMPAIGN_SEED = 0
CAMPAIGN_SPEED = 2.57
CAMPAIGN_SCALE = 1.0


# --------------------------------------------------------------------------
# library availability -- REPORTED, never assumed
# --------------------------------------------------------------------------

def library_status() -> dict:
    """What is actually importable. An absent library is said out loud."""
    out = {}
    for name in ("trimesh", "pymeshlab", "open3d", "scipy"):
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", None)
            if ver is None and name == "pymeshlab":
                ver = "installed (module exposes no __version__)"
            out[name] = str(ver or "installed")
        except Exception as exc:                       # pragma: no cover
            out[name] = f"MISSING ({type(exc).__name__})"
    return out


# --------------------------------------------------------------------------
# triangle quality -- our own numpy, on the MERGED mesh
# --------------------------------------------------------------------------

def triangle_quality(V: np.ndarray, F: np.ndarray) -> dict:
    """Per-triangle angles, areas and the normalised aspect ratio R/(2r).

    R/(2r) = circumradius / (2 x inradius) is 1 for an equilateral triangle and
    grows without bound for a sliver; it is the standard shape measure and it
    is scale-invariant, which matters here because the 25 hulls span 6.8-18.7 m
    and an absolute edge length would just be measuring length.
    """
    P = V[F]                                    # (M,3,3)
    e = np.stack([P[:, 2] - P[:, 1],
                  P[:, 0] - P[:, 2],
                  P[:, 1] - P[:, 0]], axis=1)   # edge opposite each vertex
    L = np.linalg.norm(e, axis=2)               # (M,3) side lengths
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0],
                                         P[:, 2] - P[:, 0]), axis=1)
    a, b, c = L[:, 0], L[:, 1], L[:, 2]
    peri = a + b + c
    with np.errstate(divide="ignore", invalid="ignore"):
        # law of cosines at each vertex
        cosA = (b**2 + c**2 - a**2) / (2 * b * c)
        cosB = (c**2 + a**2 - b**2) / (2 * c * a)
        cosC = (a**2 + b**2 - c**2) / (2 * a * b)
        ang = np.degrees(np.arccos(np.clip(np.stack([cosA, cosB, cosC], 1),
                                           -1.0, 1.0)))
        aspect = a * b * c * peri / (16.0 * area**2)   # R/(2r)
    ang = np.where(np.isfinite(ang), ang, 0.0)
    aspect = np.where(np.isfinite(aspect), aspect, np.inf)
    return {"area": area, "min_angle": ang.min(axis=1),
            "max_angle": ang.max(axis=1), "aspect": aspect,
            "max_edge": L.max(axis=1), "min_edge": L.min(axis=1),
            "centroid": P.mean(axis=1)}


# --------------------------------------------------------------------------
# per-hull measurement
# --------------------------------------------------------------------------

def measure(path: Path, lwl: float, report_unmerged: bool = False) -> dict:
    import trimesh
    import open3d as o3d
    import pymeshlab

    from navalai.cfd.case import stl_watertight_report

    rec: dict = {"file": path.name}

    # ---- OUR checker, for the cross-check ---------------------------------
    ours = stl_watertight_report(path)
    rec["ours_watertight"] = bool(ours["watertight"])
    rec["ours_open_nonmanifold_edges"] = int(ours["open_or_nonmanifold_edges"])
    rec["ours_winding_conflicts"] = int(ours["winding_conflicts"])
    rec["ours_signed_volume"] = float(ours["signed_volume"])
    rec["n_tris"] = int(ours["n_tris"])

    # ---- trimesh ----------------------------------------------------------
    raw = trimesh.load(path, process=False, force="mesh")
    rec["vertex_records_raw"] = int(len(raw.vertices))
    m = trimesh.load(path, process=True, force="mesh")
    V = np.asarray(m.vertices, float)
    F = np.asarray(m.faces, int)
    rec["vertices_merged"] = int(len(V))
    rec["duplicate_vertex_records"] = rec["vertex_records_raw"] - len(V)
    rec["tm_watertight"] = bool(m.is_watertight)
    rec["tm_winding_consistent"] = bool(m.is_winding_consistent)
    rec["tm_is_volume"] = bool(m.is_volume)
    rec["tm_euler"] = int(m.euler_number)
    rec["tm_volume"] = float(m.volume)
    rec["tm_area"] = float(m.area)
    rec["tm_components"] = int(m.body_count)
    rec["tm_unreferenced_vertices"] = int(len(V) - len(np.unique(F)))
    srt = np.sort(F, axis=1)
    _, inv, cnt = np.unique(srt, axis=0, return_inverse=True, return_counts=True)
    rec["duplicate_faces"] = int((cnt[inv] > 1).sum())

    if report_unmerged:
        rec["tm_watertight_unmerged"] = bool(raw.is_watertight)

    # ---- triangle quality -------------------------------------------------
    q = triangle_quality(V, F)
    rec["_q"] = q
    med_area = float(np.median(q["area"]))
    rec["degenerate_faces_1e10"] = int((q["area"] < 1e-10).sum())
    rec["near_degenerate_faces"] = int((q["area"] < 1e-6 * med_area).sum())
    rec["min_angle_min_deg"] = float(q["min_angle"].min())
    rec["min_angle_p01_deg"] = float(np.percentile(q["min_angle"], 1))
    rec["slivers_lt1deg"] = int((q["min_angle"] < 1.0).sum())
    rec["slivers_lt5deg"] = int((q["min_angle"] < 5.0).sum())
    rec["aspect_max"] = float(q["aspect"].max())
    rec["aspect_p99"] = float(np.percentile(q["aspect"], 99))
    rec["aspect_median"] = float(np.median(q["aspect"]))
    rec["area_ratio_max_min"] = float(q["area"].max() / max(q["area"].min(), 1e-30))

    # Dihedral (adjacent-normal) angles, from trimesh's own adjacency.
    #
    # SPLIT BY EDGE DIRECTION, and the first version of this script did not,
    # which made the metric useless: the chine, the keel and the deck edge are
    # DESIGNED hard edges running longitudinally, they carry 85-115 degrees at
    # EVERY station including midship, and they buried the thing being looked
    # for. A bend across a TRANSVERSE edge (one lying in a station plane) is
    # the longitudinal curvature of the shell -- corrugation, a stem kink, a
    # slope jump at x_mb -- and that is the signal. Classified by the shared
    # edge's own direction, not by any assumption about mesh ordering.
    adj = np.asarray(m.face_adjacency, int)
    dih = np.degrees(np.asarray(m.face_adjacency_angles, float))
    ae = np.asarray(m.face_adjacency_edges, int)
    ev = V[ae[:, 1]] - V[ae[:, 0]]
    with np.errstate(invalid="ignore", divide="ignore"):
        ex_frac = np.abs(ev[:, 0]) / np.maximum(np.linalg.norm(ev, axis=1), 1e-30)
    transverse = ex_frac < 0.30
    rec["_adj"] = adj
    rec["_dih"] = dih
    rec["_transverse"] = transverse
    rec["dihedral_max_deg"] = float(dih.max()) if len(dih) else float("nan")
    rec["dihedral_p99_deg"] = float(np.percentile(dih, 99)) if len(dih) else float("nan")
    rec["dihedral_mean_deg"] = float(dih.mean()) if len(dih) else float("nan")
    dt = dih[transverse]
    rec["transverse_edges"] = int(transverse.sum())
    rec["dihedral_T_max_deg"] = float(dt.max()) if len(dt) else float("nan")
    rec["dihedral_T_p99_deg"] = float(np.percentile(dt, 99)) if len(dt) else float("nan")

    # ---- Open3D -----------------------------------------------------------
    o = o3d.io.read_triangle_mesh(str(path))
    if report_unmerged:
        rec["o3d_watertight_unmerged"] = bool(o.is_watertight())
        rec["o3d_selfint_pairs_unmerged"] = int(
            len(np.asarray(o.get_self_intersecting_triangles())))
    o.remove_duplicated_vertices()
    rec["o3d_edge_manifold"] = bool(o.is_edge_manifold(allow_boundary_edges=False))
    rec["o3d_vertex_manifold"] = bool(o.is_vertex_manifold())
    rec["o3d_orientable"] = bool(o.is_orientable())
    rec["o3d_watertight"] = bool(o.is_watertight())
    rec["o3d_nonmanifold_edges"] = int(
        len(np.asarray(o.get_non_manifold_edges(allow_boundary_edges=False))))
    rec["o3d_nonmanifold_vertices"] = int(
        len(np.asarray(o.get_non_manifold_vertices())))
    si = np.asarray(o.get_self_intersecting_triangles())
    rec["o3d_selfint_pairs"] = int(len(si))
    rec["o3d_selfint_faces"] = int(len(np.unique(si))) if len(si) else 0
    # LOCALISE them: open3d indexes into its own merged triangle array, which
    # is `hull_to_stl`'s face order (the reader preserves it), so the centroid
    # x of the same index in the trimesh mesh is the same triangle. Verified by
    # comparing the two face-centroid arrays elementwise; see --check-order.
    rec["_selfint_faces_idx"] = np.unique(si) if len(si) else np.array([], int)
    o_cent = np.asarray(o.vertices)[np.asarray(o.triangles)].mean(axis=1)
    rec["_o3d_centroid"] = o_cent

    # ---- PyMeshLab --------------------------------------------------------
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(path))
    ms.meshing_remove_duplicate_vertices()
    topo = ms.get_topological_measures()
    rec["pml_non_two_manifold_edges"] = int(topo["non_two_manifold_edges"])
    rec["pml_non_two_manifold_vertices"] = int(topo["non_two_manifold_vertices"])
    rec["pml_boundary_edges"] = int(topo["boundary_edges"])
    rec["pml_holes"] = int(topo["number_holes"])
    rec["pml_components"] = int(topo["connected_components_number"])
    rec["pml_genus"] = int(topo["genus"])
    rec["pml_unreferenced_vertices"] = int(topo["unreferenced_vertices"])
    ms.compute_selection_by_self_intersections_per_face()
    rec["pml_selfint_faces"] = int(ms.current_mesh().selected_face_number())
    geo = ms.get_geometric_measures()
    rec["pml_volume"] = float(geo.get("mesh_volume", float("nan")))
    rec["pml_area"] = float(geo.get("surface_area", float("nan")))

    # ---- volume cross-check ----------------------------------------------
    v_ours = rec["ours_signed_volume"]
    rec["vol_disagree_ours_vs_trimesh_pct"] = 100.0 * abs(
        rec["tm_volume"] - v_ours) / max(abs(v_ours), 1e-12)
    rec["vol_disagree_pml_vs_trimesh_pct"] = 100.0 * abs(
        rec["pml_volume"] - rec["tm_volume"]) / max(abs(rec["tm_volume"]), 1e-12)

    rec["lwl"] = float(lwl)
    return rec


def tri_tri_distance(PA: np.ndarray, PB: np.ndarray) -> float:
    """Minimum distance between two triangles, as a convex QP in barycentrics.

    ADJUDICATES the disagreement between Open3D and PyMeshLab. Two triangles
    intersect if and only if this distance is zero, so it settles the question
    without trusting either library's predicate -- and it has to be settled,
    because "SELF-INTERSECTING FACE COUNT" is the headline number this whole
    exercise exists to produce and the two implementations do not agree on it.

    ||lambda.A - mu.B||^2 over the two barycentric simplices is convex, so
    SLSQP from a few starts finds the global minimum.
    """
    from scipy.optimize import minimize

    def f(t):
        lam = np.array([t[0], t[1], 1 - t[0] - t[1]])
        mu = np.array([t[2], t[3], 1 - t[2] - t[3]])
        return float(np.sum((lam @ PA - mu @ PB) ** 2))

    cons = [{"type": "ineq", "fun": (lambda t, k=k: t[k])} for k in range(4)]
    cons += [{"type": "ineq", "fun": lambda t: 1 - t[0] - t[1]},
             {"type": "ineq", "fun": lambda t: 1 - t[2] - t[3]}]
    best = np.inf
    for x0 in ([1 / 3, 1 / 3, 1 / 3, 1 / 3], [1, 0, 0, 1], [0, 1, 1, 0]):
        r = minimize(f, x0, constraints=cons, method="SLSQP",
                     options={"maxiter": 500, "ftol": 1e-18})
        best = min(best, f(r.x))
    return float(np.sqrt(max(best, 0.0)))


def adjudicate_selfint(path: Path) -> dict:
    """Every Open3D-reported pair, re-measured by distance. Returns the verdict."""
    import open3d as o3d
    o = o3d.io.read_triangle_mesh(str(path))
    o.remove_duplicated_vertices()
    V = np.asarray(o.vertices)
    T = np.asarray(o.triangles)
    si = np.asarray(o.get_self_intersecting_triangles())
    out = {"reported": int(len(si)), "confirmed": 0, "distances": []}
    for a, b in si:
        d = tri_tri_distance(V[T[a]], V[T[b]])
        out["distances"].append(d)
        if d <= 1e-9:
            out["confirmed"] += 1
    return out


# --------------------------------------------------------------------------
# phase 3: the bow
# --------------------------------------------------------------------------

# Bands as a FRACTION of LWL, measured from the transom (x=0). "stem" is the
# last 2% because that is where `w**0.15` does its damage: w falls to zero at
# x=L, and w**0.15 has derivative w**-0.85, so 98% of the taper's shape change
# happens in the last few percent of the length.
BANDS = {"stem_0.98_1.00": (0.98, 1.0001),
         "bow_0.90_1.00": (0.90, 1.0001),
         "fore_0.70_0.90": (0.70, 0.90),
         "mid_0.40_0.60": (0.40, 0.60)}


def bow_metrics(rec: dict) -> dict:
    """Triangle quality by longitudinal band, and the bow/midship RATIO."""
    q = rec["_q"]
    lwl = rec["lwl"]
    u = q["centroid"][:, 0] / lwl
    out: dict = {}
    per_band = {}
    for name, (lo, hi) in BANDS.items():
        sel = (u >= lo) & (u < hi)
        n = int(sel.sum())
        if n == 0:
            per_band[name] = {"n": 0}
            continue
        per_band[name] = {
            "n": n,
            "aspect_med": float(np.median(q["aspect"][sel])),
            "aspect_max": float(q["aspect"][sel].max()),
            "min_angle_med": float(np.median(q["min_angle"][sel])),
            "min_angle_min": float(q["min_angle"][sel].min()),
            "area_med": float(np.median(q["area"][sel])),
            "max_edge_med": float(np.median(q["max_edge"][sel])),
            "slivers_lt5deg": int((q["min_angle"][sel] < 5.0).sum()),
        }
    out["bands"] = per_band

    mid = per_band.get("mid_0.40_0.60", {})
    for band in ("stem_0.98_1.00", "bow_0.90_1.00"):
        b = per_band.get(band, {})
        if b.get("n") and mid.get("n"):
            key = band.split("_")[0]
            out[f"aspect_ratio_{key}_over_mid"] = b["aspect_med"] / mid["aspect_med"]
            out[f"minangle_ratio_{key}_over_mid"] = (
                b["min_angle_med"] / max(mid["min_angle_med"], 1e-9))
            out[f"area_ratio_{key}_over_mid"] = b["area_med"] / max(mid["area_med"], 1e-30)

    # dihedral spike: where along the hull, and how far aft does it reach.
    # TRANSVERSE edges only -- see the note in measure().
    adj, dih, tr = rec["_adj"], rec["_dih"], rec["_transverse"]
    if tr.any():
        u_pair = 0.5 * (u[adj[:, 0]] + u[adj[:, 1]])[tr]
        d = dih[tr]
        smid = (u_pair >= 0.40) & (u_pair < 0.60)
        out["dihedral_max_mid"] = float(d[smid].max()) if smid.any() else float("nan")
        out["dihedral_med_mid"] = float(np.median(d[smid])) if smid.any() else float("nan")
        sstem = u_pair >= 0.98
        out["dihedral_max_stem"] = float(d[sstem].max()) if sstem.any() else float("nan")
        out["dihedral_stem_over_mid"] = (out["dihedral_max_stem"] /
                                         max(out["dihedral_max_mid"], 1e-9))
        # profile in 2% bins, max transverse dihedral per bin
        edges = np.arange(0.0, 1.0001, 0.02)
        prof = np.array([float(d[(u_pair >= lo) & (u_pair < hi)].max())
                         if ((u_pair >= lo) & (u_pair < hi)).any() else np.nan
                         for lo, hi in zip(edges[:-1], edges[1:])])
        out["_dihedral_profile"] = (edges[:-1], prof)
        # How far aft the spike extends: scanning AFT from the stem, the last
        # bin still above 2x the midship maximum. 2x, not 3x, and stated as a
        # threshold rather than hidden -- the first version used 3x the
        # ALL-EDGE midship max, which is ~110 degrees on every hull because of
        # the chine, so the threshold was 330 degrees and could never fire on a
        # quantity bounded by 180. A bar nothing can cross is not a bar.
        thr = 2.0 * out["dihedral_max_mid"]
        aft = 1.0
        for lo, v in zip(edges[:-1][::-1], prof[::-1]):
            if np.isfinite(v) and v > thr:
                aft = float(lo)
            else:
                break
        out["dihedral_spike_aft_extent_u"] = aft
        out["dihedral_spike_threshold_deg"] = float(thr)
        out["dihedral_spike_extent_pct_lwl"] = 100.0 * (1.0 - aft)

    # self-intersections, localised
    idx = rec["_selfint_faces_idx"]
    if len(idx):
        cu = rec["_o3d_centroid"][idx, 0] / lwl
        out["selfint_u_min"] = float(cu.min())
        out["selfint_u_max"] = float(cu.max())
        out["selfint_u_med"] = float(np.median(cu))
        out["selfint_frac_forward_of_0.90"] = float((cu >= 0.90).mean())
    return out


def faceting_error(params: np.ndarray, nx: int = 80, n_stations: int = 41,
                   n_probe: int = 4001) -> dict:
    """How far the STL's surface is from the hull the grammar DEFINES.

    Two distinct errors, and they compound:

      E1  the 41-station polyline against the ANALYTIC closed form. `Hull`
          evaluates `station_geometry` at 41 stations and `_section_at`
          LINEARLY INTERPOLATES between them, so the surface the mesher sees is
          already piecewise linear in x at 41 knots. `edge_curves`' docstring
          already records that a cubic spline through those stations is 94.95mm
          off on the SHEER because of the w**0.15 taper; this is the same
          measurement for the linear interpolant the mesh actually uses.

      E2  the 80-sample mesh chords against that 41-station polyline. nx=80
          over 40 intervals does NOT align with the station knots -- j*40 =
          i*79 has no solution but the endpoints -- so every one of the 39
          interior kinks is straddled by a chord and cut off. This is why the
          facets alternate in size and why the surface reads as corrugated.

    Returns both in millimetres with the x/LWL where they peak.
    """
    from navalai import grammar
    from navalai.geometry import station_geometry

    L = grammar.named(params)["LWL"]

    st = np.linspace(0.0, L, n_stations)
    xs = np.linspace(0.0, L, nx)
    probe = np.linspace(0.0, L, n_probe)

    zk_s, yc_s, zc_s, ys_s, zs_s = station_geometry(params, st)
    zk_p, yc_p, zc_p, ys_p, zs_p = station_geometry(params, probe)

    out = {"lwl": float(L),
           "dx_station_m": float(L / (n_stations - 1)),
           "dx_mesh_m": float(L / (nx - 1))}
    u_probe = probe / L
    fwd = u_probe >= 0.95
    for tag, cs, cp in (("sheer", ys_s, ys_p), ("chine", yc_s, yc_p)):
        lin = np.interp(probe, st, cs)
        e1 = np.abs(lin - cp)
        out[f"E1_{tag}_max_mm"] = float(e1.max() * 1000.0)
        out[f"E1_{tag}_max_at_u"] = float(probe[int(e1.argmax())] / L)
        # E2: the mesh samples the piecewise-linear station surface at xs and
        # joins those samples with chords.
        samp = np.interp(xs, st, cs)
        chord = np.interp(probe, xs, samp)
        e2 = np.abs(chord - lin)
        out[f"E2_{tag}_max_mm"] = float(e2.max() * 1000.0)
        out[f"E2_{tag}_max_at_u"] = float(probe[int(e2.argmax())] / L)
        # total, against the analytic hull
        et = np.abs(chord - cp)
        out[f"Etot_{tag}_max_mm"] = float(et.max() * 1000.0)
        out[f"Etot_{tag}_max_at_u"] = float(probe[int(et.argmax())] / L)
        # SPLIT forward of 0.95 from the rest. Hull 23's E1 peaks at u=0.43,
        # nowhere near the stem, and lumping the two together would have
        # attributed a midbody defect (the sheer clamp, below) to the bow.
        out[f"E1_{tag}_fwd95_mm"] = float(e1[fwd].max() * 1000.0)
        out[f"E1_{tag}_aft95_mm"] = float(e1[~fwd].max() * 1000.0)

    # THE SHEER CLAMP. `station_geometry` computes the sheer half-breadth as
    # ys = y_chine + (z_sheer - z_chine)*tan(flare) and then applies
    # np.maximum(ys, 0.0). `flare` may be NEGATIVE (tumblehome), and when the
    # tumblehome over the freeboard exceeds the chine half-breadth the raw ys
    # goes negative and the clamp puts the DECK EDGE ON THE CENTRELINE. The
    # topsides then fold together and the deck lid has zero width. This is a
    # geometry defect, not a meshing one, and it is invisible to every
    # closure/winding check because the folded surface is still closed.
    ys_raw_p = yc_p + (zs_p - zc_p) * math.tan(math.radians(grammar.named(params)["flare"]))
    neg = ys_raw_p < 0.0
    out["sheer_clamped_frac"] = float(neg.mean())
    out["sheer_clamped_u_min"] = float(u_probe[neg].min()) if neg.any() else float("nan")
    out["sheer_clamped_u_max"] = float(u_probe[neg].max()) if neg.any() else float("nan")
    # clamped anywhere ABAFT the last 2%, i.e. not merely the stem point
    out["sheer_clamped_abaft_098"] = float((neg & (u_probe < 0.98)).mean())

    # THE x_mb CORNER. The plan-form `w` switches equation at x_mb:
    #   aft  w = r + (1-r)(x/xm)^p_stern     -> dw/dx = (1-r) p_stern / xm
    #   fwd  w = 1 - ((x-xm)/(L-xm))^p_bow   -> dw/dx = 0  (for p_bow > 1)
    # so dy/dx JUMPS at x_mb and the waterline carries a genuine C1 crease
    # running vertically through the whole section. Measured as the change in
    # plan-form direction, in degrees, on the chine and on the sheer.
    p = grammar.named(params)
    xm = p["x_mb"] * L
    h = 1e-4 * L
    for tag, arr_i in (("chine", 1), ("sheer", 3)):
        aft = station_geometry(params, np.array([xm - 2 * h, xm - h]))[arr_i]
        fwd = station_geometry(params, np.array([xm + h, xm + 2 * h]))[arr_i]
        s_aft = (aft[1] - aft[0]) / h
        s_fwd = (fwd[1] - fwd[0]) / h
        out[f"xmb_kink_{tag}_deg"] = float(abs(
            math.degrees(math.atan(s_aft) - math.atan(s_fwd))))
    out["xmb_u"] = float(p["x_mb"])

    # the taper's own derivative, sampled just aft of the stem
    out["p_bow"] = p["p_bow"]
    out["beta_len_frac"] = p["beta_len"]
    out["x_mb"] = p["x_mb"]
    out["flare_deg"] = p["flare"]
    out["beta_bow_deg"] = p["beta_bow"]
    dx = probe[1] - probe[0]
    dys = np.gradient(ys_p, dx)
    out["dysheer_dx_at_stem"] = float(abs(dys[-2]))
    out["dysheer_dx_at_mid"] = float(abs(dys[n_probe // 2]))
    # BOW BLUNTNESS. The half-breadth one mesh cell aft of the stem, and the
    # entrance half-angle that implies at the sheer. w**0.15 means 60% of the
    # full breadth arrives within the first cell for a typical p_bow, so the
    # sheer line has a near-vertical tangent at the stem -- the hull IS blunt
    # there, and the STL is reproducing it faithfully rather than adding it.
    y1 = float(np.interp(L - out["dx_mesh_m"], probe, ys_p))
    out["y_sheer_one_dx_aft_m"] = y1
    out["stem_halfangle_1dx_deg"] = float(
        math.degrees(math.atan2(y1, out["dx_mesh_m"])))
    ys_full = float(np.interp(0.85 * L, probe, ys_p))
    out["y_sheer_1dx_over_ys85"] = y1 / max(ys_full, 1e-9)
    return out


# --------------------------------------------------------------------------
# phase 2: AUC + exact Mann-Whitney + Holm
# --------------------------------------------------------------------------

def auc_and_p(values: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """AUC of `values` against boolean `labels`, and an exact two-sided p.

    AUC is reported in [0,1] with 1.0 = the metric is HIGH on failures; the
    caller decides whether to fold it. The p-value is the exact Mann-Whitney
    two-sided value -- with 6 positives in 25 the normal approximation is not
    usable and a Gaussian p here would be a made-up number.
    """
    from scipy import stats
    x = np.asarray(values, float)
    ok = np.isfinite(x)
    if ok.sum() < len(x):
        return float("nan"), float("nan")
    pos, neg = x[labels], x[~labels]
    if len(pos) == 0 or len(neg) == 0 or np.ptp(x) == 0:
        return float("nan"), float("nan")
    ties = len(np.unique(x)) < len(x)
    try:
        u, p = stats.mannwhitneyu(pos, neg, alternative="two-sided",
                                  method="asymptotic" if ties else "exact")
    except ValueError:
        u, p = stats.mannwhitneyu(pos, neg, alternative="two-sided",
                                  method="asymptotic")
    return float(u / (len(pos) * len(neg))), float(p)


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni adjusted p-values, family-wise over the metric set."""
    idx = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(idx):
        run = max(run, (m - rank) * pvals[i])
        adj[i] = min(run, 1.0)
    return list(adj)


def best_possible_p(n_pos: int, n_neg: int) -> float:
    """The smallest two-sided exact p a PERFECT separator could achieve.

    Stated before any ranking, because with 2 positives in 16 the answer is
    0.0167 and no metric, however perfect, can be significant after a
    family-wise correction over 30 of them. Reporting a null result without
    this number would let a reader mistake "underpowered" for "refuted".
    """
    return min(1.0, 2.0 / math.comb(n_pos + n_neg, min(n_pos, n_neg)))


# --------------------------------------------------------------------------
# the intervention arithmetic (phase 3 closing recommendation)
# --------------------------------------------------------------------------

def taper_intervention(params: np.ndarray) -> dict:
    """What a BOUNDED-derivative stem taper would cost in hydrostatics.

    A geometry change that improves meshing while moving the hydrostatics is a
    different boat, not a fix -- so the displacement / wetted-area / LCB deltas
    are computed BEFORE anyone proposes the change.

    Method: build the Hull, then substitute the sheer half-breadth array in
    place and re-run the PRODUCTION integrator (`hydrostatics.solve`). Nothing
    is reimplemented, so this cannot drift from the real hydrostatics -- which
    is the whole point, since a second copy of the displacement integral is
    exactly the defect class this repo keeps producing.

    Candidates, both with bounded dy/dx at w -> 0:
      smoothstep  ys * (3w^2 - 2w^3)
      cosine      ys * 0.5*(1 - cos(pi*w))
    """
    from navalai import hydrostatics
    from navalai.geometry import Hull

    base = Hull(np.asarray(params, float))
    h0 = hydrostatics.solve(base)
    # NOTE: this volume is the IMMERSED volume at the design waterline, which
    # is not the trimesh/PyMeshLab volume of the closed STL (that one includes
    # everything up to the deck). Two different quantities, said out loud
    # because they appear in the same report.
    out = {"volume_m3": h0.volume, "wetted_m2": h0.wetted,
           "lcb_m": h0.lcb, "lcb_pct": h0.lcb_pct_lwl, "awp_m2": h0.awp}
    wv = _w_from(base)
    ys_raw = np.where(wv > 1e-12, base.y_sheer / np.maximum(wv, 1e-12) ** 0.15,
                      base.y_sheer)
    # THE THIRD CANDIDATE IS THE ONE THAT MATTERS, and it exists because the
    # first two turn out not to be local. w**0.15 is applied over the WHOLE
    # length, not just at the stem: at w = 0.5 it is already 0.90 and at
    # w = 0.3 it is 0.83, so the taper narrows the sheer by 10-17% along most
    # of the hull. Replacing the envelope wholesale therefore changes the
    # whole boat, which is why smoothstep costs up to 12.7% of displacement.
    # `blend` keeps w**0.15 exactly wherever w >= W0 and only straightens the
    # last stretch, so the derivative is bounded by W0**0.15 / W0 and the
    # geometry change is confined to the few percent of LWL where the taper
    # was actually pathological.
    W0 = 0.25

    def _blend(t):
        t = np.clip(t, 0.0, 1.0)
        return np.where(t >= W0, t ** 0.15, (t / W0) * W0 ** 0.15)

    for name, f in (("smoothstep", lambda t: 3 * t**2 - 2 * t**3),
                    ("cosine", lambda t: 0.5 * (1 - np.cos(np.pi * t))),
                    ("blend", _blend)):
        alt = Hull(np.asarray(params, float))
        alt.y_sheer = ys_raw * f(np.clip(wv, 0.0, 1.0))
        h1 = hydrostatics.solve(alt)
        # SECTIONAL AREA CURVE: the shape of the displacement distribution, not
        # just its total. Two hulls can share a volume and resist differently.
        a0 = 2.0 * base.hydro_arrays()[0]
        a1 = 2.0 * alt.hydro_arrays()[0]
        amax = max(float(a0.max()), 1e-12)
        out[name] = {
            "d_volume_pct": 100.0 * (h1.volume - h0.volume) / max(h0.volume, 1e-12),
            "d_wetted_pct": 100.0 * (h1.wetted - h0.wetted) / max(h0.wetted, 1e-12),
            "d_lcb_pct_lwl": h1.lcb_pct_lwl - h0.lcb_pct_lwl,
            "d_awp_pct": 100.0 * (h1.awp - h0.awp) / max(h0.awp, 1e-12),
            "d_sac_max_pct_amax": 100.0 * float(np.abs(a1 - a0).max()) / amax,
            "d_sac_max_at_u": float(base.x[int(np.abs(a1 - a0).argmax())] /
                                    max(base.x[-1], 1e-12)),
        }
    return out


def _w_from(hull) -> np.ndarray:
    """The plan-form fullness `w` at the hull's own stations.

    Re-derived from the grammar parameters exactly as `station_geometry` does.
    It is NOT a second copy of the hull surface: nothing downstream consumes
    it, it exists only so the intervention harness can divide the taper back
    out of `y_sheer` and substitute a different envelope.
    """
    from navalai import grammar
    p = grammar.named(hull.params)
    L, xm = p["LWL"], p["x_mb"] * p["LWL"]
    x = hull.x
    w = np.empty_like(x)
    fwd = x >= xm
    w[fwd] = 1.0 - ((x[fwd] - xm) / (L - xm)) ** p["p_bow"]
    aft = ~fwd
    w[aft] = p["r_transom"] + (1.0 - p["r_transom"]) * (x[aft] / xm) ** p["p_stern"]
    return np.clip(w, 0.0, 1.0)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def load_labels() -> dict:
    cap7 = json.loads(CAP7.read_text())
    back = json.loads(BACKOFF.read_text())
    rows = {r["hull"]: r for r in cap7["rows"]}
    brows = {r["hull"]: r for r in back["rows"]}
    return {"cap7": rows, "backoff": brows,
            "cap7_meta": {k: v for k, v in cap7.items() if k != "rows"},
            "backoff_meta": {k: v for k, v in back.items() if k != "rows"}}


_REGEN_PROBE = """
import sys, json, pathlib
sys.path.insert(0, sys.argv[1])
import numpy as np
from navalai.evaluate import sample_valid
from navalai.mission import MissionSpec
from navalai.cfd.case import hull_to_stl
from navalai.geometry import Hull
out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
X, _ = sample_valid(25, MissionSpec(), seed=int(sys.argv[2]))
sha = [hull_to_stl(Hull(np.asarray(X[i], float)), out / ("hull%02d_regen.stl" % i))
       for i in range(len(X))]
print(json.dumps(sha))
"""


_IDENTITY_PROBE = """
import sys, json, hashlib, tempfile, pathlib
sys.path.insert(0, sys.argv[1])
import numpy as np
from navalai.evaluate import sample_valid
from navalai.mission import MissionSpec
from navalai.cfd.case import hull_to_stl
from navalai.geometry import Hull
X, _ = sample_valid(25, MissionSpec(), seed=int(sys.argv[2]))
tmp = pathlib.Path(tempfile.mkdtemp())
out = {"sha": [], "params": [list(map(float, x)) for x in X]}
for i in range(len(X)):
    out["sha"].append(hull_to_stl(Hull(np.asarray(X[i], float)), tmp / f"h{i}.stl"))
print(json.dumps(out))
"""


def verify_identity(files: dict[int, Path], ref: str | None = "HEAD") -> dict:
    """Are these STLs the ones `sample_valid(25, MissionSpec(), seed=0)` emits?

    A metric measured on a file nobody can regenerate is not evidence. Checked
    by sha256 of the bytes, which is the same identity `case.info` records.

    Regenerated from a GIT REF (default HEAD) in a scratch directory OUTSIDE
    the repository, in a subprocess, not from the working tree. This is not
    fussiness: while this script was being written a concurrent agent had an
    uncommitted change to `Hull.closed_mesh` in the tree, and the working-tree
    check flipped from 25/25 to 0/25 mid-session. The STLs are the ones the
    gate2u cap-7 campaign meshed, so the ref that reproduces them is the ref
    the campaign ran at -- checking against whatever happens to be uncommitted
    would report a live edit as a corrupt artefact. `git archive`, never
    `git stash`; other agents may hold work in this tree.
    """
    import subprocess

    src = REPO
    tmpdir = None
    if ref:
        tmpdir = Path(tempfile.mkdtemp(prefix="stl3p_ref_"))
        arch = subprocess.run(["git", "archive", ref], cwd=REPO,
                              capture_output=True)
        if arch.returncode != 0:
            return {"matched": -1, "differed": [], "params": {},
                    "ref": ref, "error": arch.stderr.decode()[:200]}
        subprocess.run(["tar", "-x", "-C", str(tmpdir)], input=arch.stdout,
                       check=True)
        src = tmpdir
    probe = subprocess.run([sys.executable, "-c", _IDENTITY_PROBE, str(src),
                            str(CAMPAIGN_SEED)], capture_output=True, cwd=str(src))
    if probe.returncode != 0:
        return {"matched": -1, "differed": [], "params": {}, "ref": ref,
                "error": probe.stderr.decode()[-400:]}
    got = json.loads(probe.stdout.decode().strip().splitlines()[-1])
    res = {"matched": 0, "differed": [], "params": {},
           "ref": ref or "working tree"}
    for i, path in sorted(files.items()):
        if got["sha"][i] == hashlib.sha256(path.read_bytes()).hexdigest():
            res["matched"] += 1
        else:
            res["differed"].append(i)
        res["params"][i] = np.asarray(got["params"][i], float)
    return res


def regenerate(ref: str, out_dir: Path) -> int:
    """Write the 25 STLs from a git REF into `out_dir`. Returns the count.

    EXISTS BECAUSE THE EXPORT DIRECTORY VANISHED MID-SESSION. The 25 files at
    ~/Documents/naval-ai-stl were deleted while this analysis was running, and
    an analysis that depends on an artefact outside the repository which nobody
    can rebuild is not reproducible -- the same shape as gap N6 (prose citing a
    run directory that `clean-runs.sh --purge` had deleted). The files are
    exactly regenerable: verified 25/25 sha256-identical at ref 1059c79 before
    they disappeared, so this restores the artefact rather than approximating
    it. It regenerates from a REF, never from the working tree, because the
    tree may hold another agent's uncommitted change to `closed_mesh`.
    """
    import subprocess

    tmpdir = Path(tempfile.mkdtemp(prefix="stl3p_regen_"))
    arch = subprocess.run(["git", "archive", ref], cwd=REPO, capture_output=True)
    if arch.returncode != 0:
        print(f"REFUSING: git archive {ref} failed: "
              f"{arch.stderr.decode()[:200]}")
        return 0
    subprocess.run(["tar", "-x", "-C", str(tmpdir)], input=arch.stdout, check=True)
    probe = subprocess.run([sys.executable, "-c", _REGEN_PROBE, str(tmpdir),
                            str(CAMPAIGN_SEED), str(out_dir)],
                           capture_output=True, cwd=str(tmpdir))
    if probe.returncode != 0:
        print(f"REFUSING: regeneration at {ref} failed:\n"
              f"{probe.stderr.decode()[-400:]}")
        return 0
    return len(json.loads(probe.stdout.decode().strip().splitlines()[-1]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stl-dir", type=Path, default=DEFAULT_STL_DIR)
    ap.add_argument("--json", type=Path, default=None,
                    help="also write the raw record to this path")
    ap.add_argument("--regen-ref", default=None,
                    help="if --stl-dir does not hold 25 hull*.stl, regenerate "
                         "them from this git ref (e.g. --regen-ref HEAD). "
                         "Regenerates from the ref, never the working tree.")
    ap.add_argument("--identity-ref", default="HEAD",
                    help="git ref to regenerate the hulls from for the sha256 "
                         "identity check (default HEAD; empty string = the "
                         "working tree, which other agents may be editing)")
    ap.add_argument("--no-verify-identity", action="store_true",
                    help="skip regenerating the 25 hulls to confirm the sha256")
    ap.add_argument("--profile", default=None,
                    help="comma-separated hull ids to print a longitudinal "
                         "dihedral profile for, e.g. --profile 4,14,8")
    ap.add_argument("--report-unmerged", action="store_true",
                    help="also report the metrics BEFORE coincident vertices "
                         "are merged (they are meaningless, and that is the "
                         "point -- see the note in the module docstring)")
    args = ap.parse_args()

    libs = library_status()
    print("=" * 78)
    print("THIRD-PARTY STL VALIDATION -- diagnostic only, nothing is repaired")
    print("=" * 78)
    print("\nlibraries actually present in this interpreter:")
    for k, v in libs.items():
        print(f"  {k:<12} {v}")
    missing = [k for k, v in libs.items() if v.startswith("MISSING")]
    if missing:
        print(f"\nREFUSING to run: {', '.join(missing)} unavailable. An "
              "unmeasurable metric is fatal, never a default.")
        return 2

    def collect() -> dict[int, Path]:
        out: dict[int, Path] = {}
        if args.stl_dir.is_dir():
            for f in sorted(args.stl_dir.glob("hull*.stl")):
                out[int(f.name[4:6])] = f
        return out

    files = collect()
    if len(files) != 25 and args.regen_ref:
        print(f"\nfound {len(files)} STLs in {args.stl_dir}; regenerating all "
              f"25 from ref {args.regen_ref}")
        n = regenerate(args.regen_ref, args.stl_dir)
        print(f"  wrote {n} STLs")
        files = collect()
    if len(files) != 25:
        print(f"\nREFUSING: found {len(files)} STLs in {args.stl_dir}, expected "
              "25. Pass --regen-ref HEAD to rebuild them from a git ref.")
        return 2
    print(f"\n{len(files)} STLs in {args.stl_dir}")

    lab = load_labels()
    meta = lab["cap7_meta"]
    if (meta["seed"], meta["scale"]) != (CAMPAIGN_SEED, CAMPAIGN_SCALE):
        print("\nREFUSING: cap7 campaign seed/scale does not match these STLs.")
        return 2

    params = {}
    if not args.no_verify_identity:
        vid = verify_identity(files, args.identity_ref or None)
        params = vid["params"]
        if vid["matched"] < 0:
            print(f"identity: COULD NOT BE MEASURED at ref "
                  f"{args.identity_ref!r} -- {vid.get('error','')}")
            print("  REFUSING to proceed: an unmeasurable check is not a "
                  "passing one.")
            return 2
        print(f"identity: {vid['matched']}/25 sha256-identical to "
              f"hull_to_stl(Hull(sample_valid(25, MissionSpec(), seed=0)[0][i]))"
              f" at ref {vid['ref']}")
        if vid["differed"]:
            print(f"  DIFFER: {vid['differed']} -- these STLs are NOT what "
                  f"{vid['ref']} emits. Either they are stale, or the geometry "
                  "has moved since they were exported. The phase-3 analytic "
                  "numbers are computed from the ref, the phase-1 mesh numbers "
                  "from the files, and mixing them across a geometry change "
                  "would be comparing two different boats.")
    else:
        print("identity: NOT VERIFIED (--no-verify-identity)")

    # ---------------- phase 1 ----------------------------------------------
    recs = {}
    for i, path in sorted(files.items()):
        recs[i] = measure(path, lab["cap7"][i]["lwl"], args.report_unmerged)

    print("\n" + "=" * 78)
    print("PHASE 1 -- per-hull, three independent libraries")
    print("=" * 78)
    print("\nour stl_watertight_report vs trimesh vs Open3D vs PyMeshLab")
    print(f"{'h':>2} {'outcome':<26} {'ours':>5} {'tm_wt':>5} {'wind':>5} "
          f"{'eul':>4} {'o3d_wt':>6} {'nmE':>4} {'nmV':>4} {'SI_o3d':>7} "
          f"{'SI_pml':>7} {'dupF':>5} {'degF':>5}")
    for i, r in sorted(recs.items()):
        why = lab["cap7"][i]["why"].replace("meshed-no-solve-requested", "meshed OK")
        print(f"{i:>2} {why:<26} {str(r['ours_watertight']):>5} "
              f"{str(r['tm_watertight']):>5} {str(r['tm_winding_consistent']):>5} "
              f"{r['tm_euler']:>4} {str(r['o3d_watertight']):>6} "
              f"{r['o3d_nonmanifold_edges']:>4} {r['o3d_nonmanifold_vertices']:>4} "
              f"{r['o3d_selfint_pairs']:>7} {r['pml_selfint_faces']:>7} "
              f"{r['duplicate_faces']:>5} {r['degenerate_faces_1e10']:>5}")

    # ---- the headline, adjudicated ---------------------------------------
    print("\nSELF-INTERSECTION -- the two libraries DISAGREE, so it is settled")
    print("by measuring the true triangle-triangle distance of every reported "
          "pair.")
    adj_tot = adj_conf = 0
    dists: list[float] = []
    for i, r in sorted(recs.items()):
        if r["o3d_selfint_pairs"] or r["pml_selfint_faces"]:
            a = adjudicate_selfint(files[i])
            recs[i]["selfint_confirmed"] = a["confirmed"]
            recs[i]["selfint_min_distance_m"] = (min(a["distances"])
                                                 if a["distances"] else float("nan"))
            adj_tot += a["reported"]
            adj_conf += a["confirmed"]
            dists += a["distances"]
            print(f"  hull {i:>2}: open3d {a['reported']:>2} pairs, "
                  f"pymeshlab {r['pml_selfint_faces']:>2} faces, "
                  f"CONFIRMED {a['confirmed']:>2}, "
                  f"closest pair {min(a['distances']):.4f} m")
        else:
            recs[i]["selfint_confirmed"] = 0
            recs[i]["selfint_min_distance_m"] = float("nan")
    print(f"  TOTAL over 25 hulls: {adj_tot} pairs reported by Open3D, "
          f"0 by PyMeshLab, {adj_conf} CONFIRMED by distance")
    if dists:
        print(f"  the reported pairs are {min(dists)*1000:.0f}-"
              f"{max(dists)*1000:.0f} mm APART -- Open3D's predicate "
              "false-positives on")
        print("  the near-coplanar facet pairs that a near-developable flat "
              "panel is made of.")

    print("\ntriangle quality and volume cross-check "
          "(aspect = R/2r, 1.0 = equilateral)")
    print(f"{'h':>2} {'tris':>5} {'vertRaw':>7} {'vertMrg':>7} {'minAng':>7} "
          f"{'sl<5deg':>7} {'aspP99':>8} {'aspMax':>9} {'dihMax':>7} "
          f"{'vol_tm':>8} {'vol_ours':>9} {'dV%':>7} {'area':>8}")
    for i, r in sorted(recs.items()):
        print(f"{i:>2} {r['n_tris']:>5} {r['vertex_records_raw']:>7} "
              f"{r['vertices_merged']:>7} {r['min_angle_min_deg']:>7.3f} "
              f"{r['slivers_lt5deg']:>7} {r['aspect_p99']:>8.2f} "
              f"{r['aspect_max']:>9.1f} {r['dihedral_max_deg']:>7.2f} "
              f"{r['tm_volume']:>8.3f} {r['ours_signed_volume']:>9.3f} "
              f"{r['vol_disagree_ours_vs_trimesh_pct']:>7.4f} {r['tm_area']:>8.3f}")

    # ---------------- phase 3 (computed here, PRINTED FIRST below) ---------
    bows = {i: bow_metrics(r) for i, r in recs.items()}
    facets = {}
    if params:
        for i in sorted(files):
            facets[i] = faceting_error(params[i])

    print("\n" + "=" * 78)
    print("PHASE 3 -- THE BOW (the owner reports this is where the problem is)")
    print("=" * 78)

    print("\nA. triangle quality by longitudinal band, per hull "
          "(u = x/LWL, 0 = transom)")
    print(f"{'h':>2} {'outc':<9} "
          f"{'stem n':>6} {'stemAsp':>8} {'stemAng':>8} "
          f"{'bow n':>6} {'bowAsp':>8} {'bowAng':>8} "
          f"{'mid n':>6} {'midAsp':>8} {'midAng':>8} "
          f"{'AspRatio':>9} {'AngRatio':>9}")
    for i in sorted(recs):
        b = bows[i]["bands"]
        s, w, m = (b["stem_0.98_1.00"], b["bow_0.90_1.00"], b["mid_0.40_0.60"])
        oc = "FAIL" if not lab["cap7"][i]["meshed_runner_bar"] else "ok"
        print(f"{i:>2} {oc:<9} "
              f"{s.get('n',0):>6} {s.get('aspect_med',float('nan')):>8.2f} "
              f"{s.get('min_angle_med',float('nan')):>8.2f} "
              f"{w.get('n',0):>6} {w.get('aspect_med',float('nan')):>8.2f} "
              f"{w.get('min_angle_med',float('nan')):>8.2f} "
              f"{m.get('n',0):>6} {m.get('aspect_med',float('nan')):>8.2f} "
              f"{m.get('min_angle_med',float('nan')):>8.2f} "
              f"{bows[i].get('aspect_ratio_stem_over_mid',float('nan')):>9.2f} "
              f"{bows[i].get('minangle_ratio_stem_over_mid',float('nan')):>9.3f}")

    print("\nB. LONGITUDINAL bend (dihedral across TRANSVERSE edges only -- the")
    print("   chine, keel and deck edge are designed hard edges and are excluded)")
    print(f"{'h':>2} {'dih_stem':>9} {'dih_mid':>8} {'stem/mid':>9} {'thr(2x)':>8} "
          f"{'spike aft u':>11} {'extent %L':>10} {'sliv<5 stem':>11} {'SI u-range':>14}")
    for i in sorted(recs):
        b = bows[i]
        si = (f"{b['selfint_u_min']:.3f}-{b['selfint_u_max']:.3f}"
              if "selfint_u_min" in b else "none")
        print(f"{i:>2} {b.get('dihedral_max_stem',float('nan')):>9.2f} "
              f"{b.get('dihedral_max_mid',float('nan')):>8.2f} "
              f"{b.get('dihedral_stem_over_mid',float('nan')):>9.2f} "
              f"{b.get('dihedral_spike_threshold_deg',float('nan')):>8.2f} "
              f"{b.get('dihedral_spike_aft_extent_u',float('nan')):>11.3f} "
              f"{b.get('dihedral_spike_extent_pct_lwl',float('nan')):>10.1f} "
              f"{bows[i]['bands']['stem_0.98_1.00'].get('slivers_lt5deg',0):>11} "
              f"{si:>14}")

    if facets:
        print("\nC. how far the STL surface is from the hull the grammar "
              "DEFINES (mm)")
        print("   E1 = 41-station linear interpolation vs the analytic closed "
              "form")
        print("   E2 = the 80-sample mesh chords vs that 41-station polyline")
        print(f"{'h':>2} {'lwl':>7} {'dx_st':>6} {'dx_mesh':>7} "
              f"{'E1sheer':>8} {'@u':>6} {'E2sheer':>8} {'@u':>6} "
              f"{'Etot':>8} {'E1chine':>8} {'dy/dx stem':>11} {'y@1dx':>7}")
        for i in sorted(facets):
            f = facets[i]
            print(f"{i:>2} {f['lwl']:>7.3f} {f['dx_station_m']:>6.3f} "
                  f"{f['dx_mesh_m']:>7.3f} {f['E1_sheer_max_mm']:>8.1f} "
                  f"{f['E1_sheer_max_at_u']:>6.3f} {f['E2_sheer_max_mm']:>8.1f} "
                  f"{f['E2_sheer_max_at_u']:>6.3f} {f['Etot_sheer_max_mm']:>8.1f} "
                  f"{f['E1_chine_max_mm']:>8.1f} {f['dysheer_dx_at_stem']:>11.2f} "
                  f"{f['y_sheer_one_dx_aft_m']:>7.3f}")

        print("\nD. that deviation against the CELL the mesher will use there,")
        print("   and how much breadth arrives within ONE mesh cell of the stem")
        from navalai.cfd.case import layer_spec
        print(f"{'h':>2} {'cell_mm':>8} {'Etot_mm':>8} {'Etot/cell':>9} "
              f"{'dx/cell':>8} {'y@1dx/cell':>10} {'halfang':>8} "
              f"{'y@1dx / y@0.85L':>15}")
        for i in sorted(facets):
            f = facets[i]
            spec = layer_spec(f["lwl"], CAMPAIGN_SPEED, CAMPAIGN_SCALE)
            cell_mm = spec["hull_cell_m"] * 1000.0
            print(f"{i:>2} {cell_mm:>8.1f} {f['Etot_sheer_max_mm']:>8.1f} "
                  f"{f['Etot_sheer_max_mm']/cell_mm:>9.3f} "
                  f"{f['dx_mesh_m']*1000.0/cell_mm:>8.3f} "
                  f"{f['y_sheer_one_dx_aft_m']*1000.0/cell_mm:>10.2f} "
                  f"{f['stem_halfangle_1dx_deg']:>8.2f} "
                  f"{f['y_sheer_1dx_over_ys85']:>15.3f}")

        print("\nE. THE SHEER CLAMP -- np.maximum(ys, 0.0) in station_geometry.")
        print("   Negative flare (tumblehome) can drive the raw sheer "
              "half-breadth below")
        print("   zero; the clamp then puts the DECK EDGE ON THE CENTRELINE. "
              "Closed,")
        print("   manifold, correctly wound -- and folded.")
        any_clamp = False
        for i in sorted(facets):
            f = facets[i]
            if f["sheer_clamped_frac"] > 0:
                any_clamp = True
                print(f"  hull {i:>2}: clamped over {100*f['sheer_clamped_frac']:>5.1f}% "
                      f"of LWL, u = {f['sheer_clamped_u_min']:.3f}-"
                      f"{f['sheer_clamped_u_max']:.3f}, "
                      f"{100*f['sheer_clamped_abaft_098']:>4.1f}% abaft u=0.98, "
                      f"flare = {f['flare_deg']:+.2f} deg")
        if not any_clamp:
            print("  none")

        print("\nF. THE x_mb CORNER -- the plan-form switches equation there, "
              "and dy/dx jumps.")
        print("   This is the SECOND documented suspect and it is a real C1 "
              "crease, at")
        print("   midbody rather than at the bow.")
        print(f"{'h':>2} {'x_mb (u)':>9} {'chine kink deg':>15} "
              f"{'sheer kink deg':>15} {'dih at that bin':>16}")
        for i in sorted(facets):
            f = facets[i]
            prof = bows[i].get("_dihedral_profile")
            dv = float("nan")
            if prof is not None:
                k = int(min(len(prof[1]) - 1, f["xmb_u"] // 0.02))
                dv = prof[1][k]
            print(f"{i:>2} {f['xmb_u']:>9.3f} {f['xmb_kink_chine_deg']:>15.2f} "
                  f"{f['xmb_kink_sheer_deg']:>15.2f} {dv:>16.2f}")

    if args.profile:
        want = [int(s) for s in args.profile.split(",")]
        print("\n" + "=" * 78)
        print(f"LONGITUDINAL PROFILE for hulls {want}")
        print("=" * 78)
        print("max transverse-edge dihedral per 2% of LWL, with the geometric "
              "event at\nthat station named. '*' marks a bin above 2x the "
              "hull's own midship maximum.")
        for i in want:
            if i not in recs:
                print(f"\nhull {i}: not in this batch")
                continue
            f = facets.get(i)
            prof = bows[i].get("_dihedral_profile")
            if prof is None or f is None:
                print(f"\nhull {i}: no profile (identity not verified?)")
                continue
            thr = bows[i]["dihedral_spike_threshold_deg"]
            print(f"\nhull {i}  lwl {f['lwl']:.3f} m  x_mb {f['xmb_u']:.3f}  "
                  f"p_bow {f['p_bow']:.3f}  flare {f['flare_deg']:+.2f} deg  "
                  f"outcome {lab['cap7'][i]['why']}")
            for lo, v in zip(*prof):
                if not np.isfinite(v):
                    continue
                ev = []
                if abs(lo + 0.01 - f["xmb_u"]) < 0.01:
                    ev.append("x_mb: plan-form equation switch, dy/dx jumps "
                              f"{f['xmb_kink_chine_deg']:.1f} deg")
                if abs(lo + 0.01 - 0.70) < 0.01:
                    ev.append("forefoot keel rise begins (C1-continuous)")
                if abs(lo + 0.01 - 0.30) < 0.01:
                    ev.append("rocker begins (C1-continuous)")
                if abs(lo + 0.01 - (1.0 - f["beta_len_frac"])) < 0.01:
                    ev.append("deadrise warp toward the bow begins")
                if lo >= 0.98:
                    ev.append("STEM: w**0.15 taper, dy/dx unbounded")
                if lo < 0.02:
                    ev.append("transom cap")
                mark = "*" if v > thr else " "
                print(f"   u {lo:.2f}-{lo+0.02:.2f} {mark} {v:>7.2f} deg"
                      + ("   " + "; ".join(ev) if ev else ""))

    # ---------------- phase 2 ----------------------------------------------
    print("\n" + "=" * 78)
    print("PHASE 2 -- does any of it SEPARATE the recorded failures?")
    print("=" * 78)

    metrics: dict[str, list[float]] = {}

    def add(name, fn):
        metrics[name] = [fn(i) for i in sorted(recs)]

    for key in ("o3d_selfint_pairs", "o3d_selfint_faces", "pml_selfint_faces",
                "degenerate_faces_1e10", "near_degenerate_faces",
                "duplicate_faces", "slivers_lt1deg", "slivers_lt5deg",
                "min_angle_min_deg", "min_angle_p01_deg", "aspect_max",
                "aspect_p99", "aspect_median", "area_ratio_max_min",
                "dihedral_max_deg", "dihedral_p99_deg", "dihedral_mean_deg",
                "dihedral_T_max_deg", "dihedral_T_p99_deg",
                "tm_volume", "tm_area", "tm_euler", "vertices_merged",
                "vol_disagree_ours_vs_trimesh_pct", "lwl"):
        add(key, lambda i, k=key: float(recs[i][k]))
    add("area_over_vol_23",
        lambda i: recs[i]["tm_area"] / max(recs[i]["tm_volume"], 1e-12) ** (2 / 3))
    for key in ("aspect_ratio_stem_over_mid", "minangle_ratio_stem_over_mid",
                "aspect_ratio_bow_over_mid", "minangle_ratio_bow_over_mid",
                "area_ratio_stem_over_mid", "dihedral_max_stem",
                "dihedral_stem_over_mid", "dihedral_spike_aft_extent_u"):
        add(key, lambda i, k=key: float(bows[i].get(k, float("nan"))))
    add("stem_aspect_max",
        lambda i: bows[i]["bands"]["stem_0.98_1.00"].get("aspect_max", float("nan")))
    add("stem_slivers_lt5",
        lambda i: float(bows[i]["bands"]["stem_0.98_1.00"].get("slivers_lt5deg",
                                                               float("nan"))))
    if facets:
        for key in ("E1_sheer_max_mm", "E2_sheer_max_mm", "Etot_sheer_max_mm",
                    "E1_sheer_fwd95_mm", "E1_sheer_aft95_mm",
                    "E1_chine_max_mm", "dysheer_dx_at_stem", "p_bow", "x_mb",
                    "flare_deg", "beta_bow_deg", "y_sheer_one_dx_aft_m",
                    "stem_halfangle_1dx_deg", "y_sheer_1dx_over_ys85",
                    "sheer_clamped_frac"):
            add(key, lambda i, k=key: float(facets[i][k]))
        # the two deviations NORMALISED by the cell the mesher uses -- the
        # dimensionless form is the one that could plausibly predict a snap
        # failure, since snappy's displacement scales with the cell
        from navalai.cfd.case import layer_spec as _ls
        add("Etot_sheer_over_cell",
            lambda i: facets[i]["Etot_sheer_max_mm"] /
            (_ls(facets[i]["lwl"], CAMPAIGN_SPEED, CAMPAIGN_SCALE)["hull_cell_m"] * 1e3))
        add("y1dx_over_cell",
            lambda i: facets[i]["y_sheer_one_dx_aft_m"] /
            _ls(facets[i]["lwl"], CAMPAIGN_SPEED, CAMPAIGN_SCALE)["hull_cell_m"])

    idx = sorted(recs)
    label_sets = {
        "cap7 runner bar (wo<=5, skew<=20, zeroVol=0)":
            np.array([not lab["cap7"][i]["meshed_runner_bar"] for i in idx]),
        "cap7 strict meshed":
            np.array([not lab["cap7"][i]["meshed"] for i in idx]),
    }
    # the layer-count-INDEPENDENT label: hulls the backoff ladder could not
    # mesh at ANY count it tried. Only 16 hulls were covered, so it is scored
    # over those 16 and the reduced power is stated.
    bcov = sorted(lab["backoff"])
    label_sets["backoff: fails at EVERY layer count (16 hulls)"] = None

    for lname, lvec in label_sets.items():
        if lvec is None:
            sub = [k for k, i in enumerate(idx) if i in lab["backoff"]]
            y = np.array([lab["backoff"][idx[k]]["why"] !=
                          "meshed-no-solve-requested" for k in sub])
            rows_idx = sub
        else:
            y = lvec
            rows_idx = list(range(len(idx)))
        npos, nneg = int(y.sum()), int((~y).sum())
        bp = best_possible_p(npos, nneg)
        print(f"\nlabel: {lname}")
        print(f"  positives {npos} / {npos+nneg}   "
              f"failures = {[idx[rows_idx[k]] for k in range(len(y)) if y[k]]}")
        print(f"  BEST POSSIBLE two-sided exact p for a PERFECT separator: "
              f"{bp:.4g}"
              + ("   <- no metric here can survive a family-wise correction"
                 if bp * len(metrics) > 0.05 else ""))
        scored = []
        for name, vals in metrics.items():
            v = np.array([vals[k] for k in rows_idx], float)
            a, p = auc_and_p(v, y)
            if not np.isfinite(a):
                continue
            scored.append((max(a, 1.0 - a), a, p, name))
        if not scored:
            print("  nothing scoreable")
            continue
        adj = holm([s[2] for s in scored])
        scored = [(s[0], s[1], s[2], adj[k], s[3]) for k, s in enumerate(scored)]
        scored.sort(key=lambda s: -s[0])
        print(f"  family size {len(scored)} metrics; Holm-Bonferroni adjusted")
        print(f"  {'AUC':>6} {'dir':>4} {'p_raw':>9} {'p_holm':>9}  metric")
        for a_fold, a, p, pa, name in scored[:12]:
            print(f"  {a_fold:>6.3f} {'high' if a >= 0.5 else 'low':>4} "
                  f"{p:>9.4f} {pa:>9.4f}  {name}")
        sig = [s for s in scored if s[3] < 0.05]
        print(f"  SIGNIFICANT after correction: "
              f"{[s[4] for s in sig] if sig else 'NONE'}")

    # ---------------- intervention arithmetic ------------------------------
    if params:
        print("\n" + "=" * 78)
        print("INTERVENTION ARITHMETIC -- what a bounded-derivative taper costs")
        print("=" * 78)
        print("A universal defect cannot be tested by correlation. It can only "
              "be tested by\nchanging it and re-meshing the SAME genomes. "
              "These are the hydrostatic deltas\nthat change would introduce, "
              "computed with the production integrator.\n")
        print("ss = smoothstep 3w^2-2w^3, cos = 0.5(1-cos(pi w)); dLCB in "
              "%LWL; dSAC = max change\nin sectional area, as a % of the "
              "midship section. 'vol' is the IMMERSED volume at\nthe design "
              "waterline -- NOT the closed-STL volume in phase 1.\n")
        print(f"{'h':>2} {'vol m3':>8} "
              f"{'ss dV%':>7} {'ss dS%':>7} {'ss dLCB':>8} {'ss dAwp%':>9} "
              f"{'ss dSAC%':>8} {'@u':>7} "
              f"{'cos dV%':>8} {'cos dS%':>8} {'cos dLCB':>9}")
        agg = {"smoothstep": [], "cosine": [], "blend": []}
        for i in sorted(files):
            t = taper_intervention(params[i])
            ss, co = t["smoothstep"], t["cosine"]
            agg["smoothstep"].append(ss)
            agg["cosine"].append(co)
            agg["blend"].append(t["blend"])
            print(f"{i:>2} {t['volume_m3']:>8.3f} "
                  f"{ss['d_volume_pct']:>7.3f} {ss['d_wetted_pct']:>7.3f} "
                  f"{ss['d_lcb_pct_lwl']:>8.4f} {ss['d_awp_pct']:>9.3f} "
                  f"{ss['d_sac_max_pct_amax']:>8.3f} {ss['d_sac_max_at_u']:>7.3f} "
                  f"{co['d_volume_pct']:>8.3f} {co['d_wetted_pct']:>8.3f} "
                  f"{co['d_lcb_pct_lwl']:>9.4f}")
        print("\n  the BLEND candidate -- w**0.15 kept wherever w >= 0.25, "
              "straightened below")
        print(f"  {'h':>2} {'dV%':>8} {'dS%':>8} {'dLCB %LWL':>10} "
              f"{'dAwp%':>8} {'dSAC%':>8}")
        for i in sorted(files):
            bl = agg['blend'][sorted(files).index(i)]
            print(f"  {i:>2} {bl['d_volume_pct']:>8.4f} {bl['d_wetted_pct']:>8.4f} "
                  f"{bl['d_lcb_pct_lwl']:>10.5f} {bl['d_awp_pct']:>8.4f} "
                  f"{bl['d_sac_max_pct_amax']:>8.4f}")
        for k, rows in agg.items():
            print(f"\n  {k}: |dV| max {max(abs(r['d_volume_pct']) for r in rows):.3f}% "
                  f"| |dS| max {max(abs(r['d_wetted_pct']) for r in rows):.3f}% "
                  f"| |dLCB| max {max(abs(r['d_lcb_pct_lwl']) for r in rows):.4f} %LWL "
                  f"| |dAwp| max {max(abs(r['d_awp_pct']) for r in rows):.3f}% "
                  f"| |dSAC| max {max(r['d_sac_max_pct_amax'] for r in rows):.3f}% of Amax")

    if args.json:
        dump = {}
        for i, r in recs.items():
            d = {k: v for k, v in r.items() if not k.startswith("_")}
            d["bow"] = {k: v for k, v in bows[i].items() if not k.startswith("_")}
            if facets:
                d["faceting"] = facets[i]
            dump[str(i)] = d
        args.json.write_text(json.dumps(
            {"libraries": libs, "hulls": dump}, indent=1, default=float))
        print(f"\nraw record: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
