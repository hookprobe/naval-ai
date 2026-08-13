"""How far a TRIANGULATION is from the hull the grammar defines.

ONE definition of "deviation", used for every surface compared in
`docs/research/BLENDER.md`, so the current path, a Blender rebuild, a
subdivided cage and a voxel remesh are scored by the same ruler.

    deviation = max over probe points P on the ANALYTIC surface of the
                distance from P to the NEAREST POINT of the triangulation,
                binned by x/Lwl into ten bins centred 0.05 ... 0.95

DIRECTION MATTERS AND IS STATED: probes lie on the analytic surface and the
distance is measured TO the mesh. That is "how much of the hull did the mesh
fail to reach", which is the question a chorded knuckle answers badly. The
other direction ("how far off the hull did the mesh wander") is reported
separately by `surface_report` as `mesh_to_analytic`, because a voxel remesh
can inflate a surface outward and a one-sided metric would not see it.

~~VALIDATED AGAINST THE PUBLISHED STAGE A TABLE rather than asserted. Commit
bbf1a47 recorded hull 14's post-fix row as

    x/L   0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
          0.01  0.11  0.36  0.83  1.36 23.53  1.29  2.62  3.03 102.92

and this module reproduces 0.01 / 0.11 / 0.36 / 0.83 / 1.37 / 23.54 / ...~~

**THE STAGE A TABLE IS VOID AS A CALIBRATION, 2026-08-13.** It is a table for
ONE HULL — `sample_valid(25, MissionSpec(), seed=0)[14]` on the FIFTEEN-
parameter genome — and plates P1/P2 took the genome to sixteen (`p_bow` and
`p_stern` dropped; `Cp`, `lcb` and `roundness` added). Index 14 of that call
is now a different boat, so there is no arithmetic that carries the row
across; this is `admissibility.CALIBRATION_GENOME_N_PARAMS` in a second
place, and `tests/test_blender_hull.py` states it as a PROBE on
`grammar.N_PARAMS` rather than as prose, so it un-asserts itself if the
genome ever goes back.

What survives the genome change is the METHOD, and it is kept: the peak in
the x_mb bin is attained exactly at x = x_mb*L, so whether a probe lands on
it depended on the probe count (23.50 / 23.07 / 23.50 at 801 / 2001 / 4001
stations). `analytic_probe_points` INSERTS x_mb into the probe abscissae, and
the bin then reads the same value at all three densities. A metric whose value
depends on how finely you sampled it is not a metric; the fix is to sample the
feature, not to pick a number.

The ruler's live fence is therefore a CONVERGENCE statement, which no genome
can stale: deviation -> 0 as the triangulation is refined toward the analytic
surface. `tests/test_blender_hull.py` holds it, together with a re-measured
table for the shipped 600x120 path.
"""

from __future__ import annotations

import numpy as np

from ..geometry import (Hull, design_waterline, sample_section,
                        station_geometry)
from ..grammar import named

#: Probe density. 2001 longitudinal stations x 61 section parameters = 242121
#: points, ~2.4 s per hull against a 289k-triangle surface via trimesh. The
#: bins are unchanged at 801x41 and 4001x81 (see module docstring), so this is
#: converged, not merely affordable.
PROBE_NX = 2001
PROBE_NT = 61

#: Ten bins of width 0.1 in x/Lwl, reported by their centres 0.05 ... 0.95 —
#: the same bins commit bbf1a47 published, so the numbers are comparable.
N_BINS = 10


def _section_points(hull: Hull, xs: np.ndarray, nt: int) -> np.ndarray:
    """(len(xs), 2*nt-1, 3) points ON the analytic section at each x in `xs`.

    Delegates the SHAPE to `geometry.sample_section`, which is the one
    definition of it. See `analytic_probe_points` for why this is not a
    keel -> chine -> sheer straight-leg walk any more.
    """
    zk, yc, zc, ys, zs = station_geometry(hull.params, xs)
    y_wl = design_waterline(hull.params, xs)
    rho = hull.roundness
    out = np.empty((len(xs), 2 * nt - 1, 3))
    for i in range(len(xs)):
        out[i, :, 0] = xs[i]
        out[i, :, 1:] = sample_section((0.0, zk[i]), (yc[i], zc[i]),
                                       (ys[i], zs[i]), (y_wl[i], 0.0),
                                       rho, nt - 1, nt - 1)
    return out


def analytic_probe_points(hull: Hull, nx: int = PROBE_NX,
                          nt: int = PROBE_NT) -> np.ndarray:
    """(N, 3) points ON the analytic moulded surface, starboard side.

    Evaluates `station_geometry` — the ONE definition of the moulded surface's
    edge curves — at `nx` abscissae PLUS x_mb*Lwl, and samples the SECTION
    SHAPE FUNCTION (`geometry.sample_section`) at `nt` parameters per panel.
    These are points on the hull the grammar defines, not on any mesh of it:
    the stations are NOT the 41 knots `Hull` samples, so a probe generally
    falls between two of them and sees the linear-in-x interpolation error too.

    THE PROBES USED TO BE A STRAIGHT-LEG WALK keel -> chine -> sheer, and
    plate P2 made that the WRONG SURFACE. `roundness` fillets the bilge with a
    quadratic Bezier, so a probe stepped linearly from the keel point to the
    chine point lies INSIDE the hull by the depth of the fillet, and the
    distance from it to the (correct) triangulation is the fillet, not a mesh
    error.

    MEASURED 2026-08-13 on `sample_valid(25, MissionSpec(), seed=0)[14]`
    (roundness 0.327, Lwl 13.705 m) at the shipped 600x120, max analytic-to-
    mesh deviation in mm by x/L bin:

        x/L         0.05  0.15  0.25  0.35  0.45  0.55  0.65  0.75  0.85  0.95
        straight   28.89 34.70 37.05 37.21 34.99 43.64 34.92 34.92 30.83 21.70
        sampled     7.09  0.66  1.07  0.79  2.53 33.95  2.04  1.40  2.11  3.04

    A ruler reading 30-40 mm of "error" in EVERY bin on a mesh that is right
    is defect class 1 turned inside out: a quantity that could not be measured
    (this ruler had no way to express a radiused bilge) scored as a measured
    one, and the number it produced was the design gene. The flat ~35 mm floor
    is the tell — a real triangulation error varies along the hull; a constant
    one is the metric describing a shape difference it invented.

    At `roundness == 0` `sample_section` IS the old two-segment linear
    interpolation, bit for bit (its own contract, fenced at 1e-12 by
    `tests/test_geometry_kernel.py`), so nothing about the hard-chine numbers
    in `docs/research/BLENDER.md` moves.

    Starboard only. The surface is mirror-symmetric and every triangulation
    compared here is built symmetric, so probing both sides doubles the cost
    and cannot change a max.
    """
    L = float(hull.x[-1])
    xs = np.unique(np.concatenate([np.linspace(0.0, L, nx),
                                   [named(hull.params)["x_mb"] * L]]))
    return _section_points(hull, xs, nt).reshape(-1, 3)


def analytic_closed_points(hull: Hull, nx: int = 401, nt: int = 41,
                           ns: int = 41) -> np.ndarray:
    """(N, 3) points on the FULL CLOSED analytic surface: shell + deck lid +
    transom cap, both sides.

    Needed because `mesh_to_analytic_mm` asks "how far off the hull did this
    mesh wander", and the answer must not count a legitimate DECK vertex as a
    wanderer. MEASURED, and this is why the function exists rather than being
    an elaboration: scored against the shell-only cloud, a voxel remesh and a
    subdivided cage both read ~1704 mm, which is not a surface error — it is
    half the beam, i.e. the distance from a point in the middle of the deck to
    the nearest point on the SHELL. Two different surfaces reading the same
    1.70 m is the signature of measuring the wrong thing.

    The stem cap is not included: at x = Lwl the sectional area curve a(x)
    reaches 0, so y_chine and y_sheer are both 0 and the station collapses to a
    segment of the centreline, which the shell cloud already contains.

    THE TRANSOM CAP IS SAMPLED FROM `sample_section` TOO, for the same reason
    `analytic_probe_points` is: it used to be the straight-leg walk, so on a
    radiused bilge the cap's cloud was cut across the fillet and a legitimate
    transom vertex read as a wanderer.
    """
    L = float(hull.x[-1])
    xs = np.linspace(0.0, L, nx)
    _zk, _yc, _zc, ys, zs = station_geometry(hull.params, xs)
    out = [analytic_probe_points(hull, nx, nt)]
    # deck lid: flat strip at z_sheer between the two sheer lines
    for s in np.linspace(-1.0, 1.0, ns):
        out.append(np.stack([xs, ys * s, zs], axis=1))
    # transom cap: the x = 0 section, filled laterally
    sec = _section_points(hull, xs[:1], nt)[0]
    sec_y, sec_z = sec[:, 1], sec[:, 2]
    for s in np.linspace(-1.0, 1.0, ns):
        out.append(np.stack([np.zeros_like(sec_y), sec_y * s, sec_z], axis=1))
    P = np.vstack(out)
    return np.vstack([P, P * np.array([1.0, -1.0, 1.0])])


def _proximity(V: np.ndarray, T: np.ndarray):
    """trimesh proximity query over (V, T). Raises if trimesh is absent.

    trimesh 5.0.0 is installed on this node and commit b91bbf3 already relies
    on it for the self-intersection adjudication, so this is not a new
    dependency. It is imported lazily so `navalai.blender` stays importable
    where it is not.
    """
    import trimesh
    return trimesh.Trimesh(vertices=np.asarray(V, dtype=float),
                           faces=np.asarray(T, dtype=int), process=False)


def deviation_by_xl(hull: Hull, V: np.ndarray, T: np.ndarray,
                    nx: int = PROBE_NX, nt: int = PROBE_NT,
                    n_bins: int = N_BINS) -> dict:
    """Max analytic-to-mesh deviation [mm] per x/Lwl bin, plus the overall max.

    Returns `bin_centres`, `max_mm` (len n_bins), `overall_max_mm`,
    `overall_max_at_u`, `rms_mm` and `n_probes`.
    """
    import trimesh
    L = float(hull.x[-1])
    P = analytic_probe_points(hull, nx, nt)
    m = _proximity(V, T)
    _, d, _ = trimesh.proximity.closest_point(m, P)
    u = P[:, 0] / L
    idx = np.clip(np.digitize(u, np.linspace(0.0, 1.0, n_bins + 1)) - 1,
                  0, n_bins - 1)
    per = []
    for b in range(n_bins):
        sel = idx == b
        per.append(float(d[sel].max() * 1000.0) if sel.any() else float("nan"))
    k = int(np.argmax(d))
    return {"bin_centres": [(b + 0.5) / n_bins for b in range(n_bins)],
            "max_mm": per,
            "overall_max_mm": float(d.max() * 1000.0),
            "overall_max_at_u": float(u[k]),
            "rms_mm": float(np.sqrt(np.mean(d ** 2)) * 1000.0),
            "n_probes": int(len(P))}


def mesh_to_analytic_mm(hull: Hull, V: np.ndarray, T: np.ndarray,
                        nx: int = 401, nt: int = 41, ns: int = 41) -> dict:
    """THE OTHER DIRECTION: max distance from a mesh vertex to the CLOSED
    analytic surface, in mm.

    One-sided deviation is buyable. A surface that stops short of a knuckle
    scores badly on `deviation_by_xl`, and a surface that bulges OUTSIDE the
    hull — which is what a voxel remesh does at any voxel comparable to the
    local thickness — can score acceptably on it while being nowhere near the
    boat. This is the direction that catches that.

    Approximates the analytic surface by the point cloud of
    `analytic_closed_points`, so it is an UPPER BOUND accurate to the cloud's
    spacing, which is reported as `cloud_spacing_x_mm`. It is not exact and is
    not presented as exact.
    """
    from scipy.spatial import cKDTree
    P = analytic_closed_points(hull, nx, nt, ns)
    d, _ = cKDTree(P).query(np.asarray(V, dtype=float))
    L = float(hull.x[-1])
    return {"max_mm": float(d.max() * 1000.0),
            "p999_mm": float(np.percentile(d, 99.9) * 1000.0),
            "rms_mm": float(np.sqrt(np.mean(d ** 2)) * 1000.0),
            "at_u": float(V[int(np.argmax(d)), 0] / L),
            "cloud_spacing_x_mm": float(L / (nx - 1) * 1000.0),
            "n_cloud": int(len(P))}


# --------------------------------------------------------------------------
# The chine, which is the feature Stage A fixed to 1e-9 m
# --------------------------------------------------------------------------


def chine_dihedral_analytic(hull: Hull, n: int = 600) -> np.ndarray:
    """Angle [deg] between the two panel normals at the chine, ANALYTICALLY.

    The reference the mesh is judged against. Both panels are straight
    segments in the section plane and ruled in x, so the normal jump across
    the chine is a property of the hull, not of any triangulation.

    IT IS A PROPERTY OF A KNUCKLE, SO IT REFUSES A RADIUSED BILGE — NaN, not a
    number. Plate P2's `roundness` replaces the corner with a quadratic Bezier
    whose two control legs are exactly the K -> C and C -> S segments this
    function differences, so the formula keeps returning the angle of a corner
    THE SURFACE NO LONGER HAS.

    MEASURED 2026-08-13 on `sample_valid(25, MissionSpec(), seed=0)[14]`
    (roundness 0.327): this function returned **84.90 deg** while
    `chine_dihedral_measured` on the correct 600x120 triangulation of the same
    hull read **0.53 deg** 5 mm off the bilge — and the 0.53 was right. It is
    the control arm of `tests/test_blender_hull.py::
    test_a_005_voxel_remesh_destroys_the_chine` that caught it, by asserting
    the two agree; had that arm not existed, a round-bilge hull would have
    been reported as a destroyed chine on every surface including the shipped
    one. Returning the corner angle anyway is defect class 1: a quantity this
    function cannot measure on this hull, scored as a measurement.

    A round bilge's sharpness is what `chine_dihedral_measured`'s OFFSET SWEEP
    reports, and that metric needs no analytic corner to be read.
    """
    if hull.roundness > 0.0:
        return np.full(int(n), np.nan)
    L = float(hull.x[-1])
    xs = np.linspace(0.0, L, n)
    zk, yc, zc, ys, zs = station_geometry(hull.params, xs)
    K = np.stack([xs, np.zeros_like(xs), zk], axis=1)
    C = np.stack([xs, yc, zc], axis=1)
    S = np.stack([xs, ys, zs], axis=1)
    tx = np.gradient(C, xs, axis=0)
    n_lo = np.cross(tx, C - K)
    n_hi = np.cross(tx, S - C)
    n_lo /= np.maximum(np.linalg.norm(n_lo, axis=1), 1e-300)[:, None]
    n_hi /= np.maximum(np.linalg.norm(n_hi, axis=1), 1e-300)[:, None]
    return np.degrees(np.arccos(np.clip(np.sum(n_lo * n_hi, axis=1),
                                        -1.0, 1.0)))


#: Offsets from the chine, IN METRES, at which the dihedral is probed. The
#: owner's proposal is a 0.05 m voxel, so 0.05 must be one of them and the
#: sweep must bracket it. THIS IS THE POINT OF THE SWEEP: at 5% of the panel
#: girth (~75 mm on these hulls) a voxel-remeshed chine still reads 71.7 deg,
#: because a rounded edge measured far enough away from it still looks sharp.
#: A single offset is not a measurement of sharpness; the SHAPE of the sweep
#: is (a true knuckle is flat across all offsets, a rounded one collapses as
#: the offset approaches the rounding radius).
CHINE_OFFSETS_M = (0.005, 0.0125, 0.025, 0.05, 0.10)


def chine_dihedral_measured(hull: Hull, V: np.ndarray, T: np.ndarray,
                            n: int = 400,
                            offsets_m=CHINE_OFFSETS_M) -> dict:
    """Angle [deg] between the mesh's normals either side of the chine, swept
    over ABSOLUTE offsets in metres.

    Works on ANY triangulation, including one with no chine row, which is the
    whole point: a voxel remesh destroys the structured grid, so a metric that
    selects "the chine row" cannot be used to ask whether the chine survived.

    Method: at `n` stations take the analytic chine point, step `off` metres
    away from it along each panel (clamped to 40% of that panel's local girth
    so a collapsing section near the stem cannot step past the keel or the
    sheer), find the triangle nearest each offset point, and take the angle
    between those two face normals.

    `median_deg` is reported at the SMALLEST offset in the sweep and the full
    sweep is in `sweep_median_deg`. Cross-checked against the structured-grid
    measurement on the current STL: the normal jump across the chine-ROW edges
    of `closed_mesh` at 600x120 reads a median of 53.48 / 69.36 / 72.02 deg on
    hulls 4/8/14, which is the 53.5 / 69.4 / 72.0 commit bbf1a47 published.
    """
    import trimesh
    L = float(hull.x[-1])
    xs = np.linspace(0.02 * L, 0.98 * L, n)
    zk, yc, zc, ys, zs = station_geometry(hull.params, xs)
    C = np.stack([xs, yc, zc], axis=1)
    K = np.stack([xs, np.zeros_like(xs), zk], axis=1)
    S = np.stack([xs, ys, zs], axis=1)
    g_lo = np.maximum(np.linalg.norm(K - C, axis=1), 1e-9)
    g_hi = np.maximum(np.linalg.norm(S - C, axis=1), 1e-9)
    m = _proximity(V, T)
    fn = np.asarray(m.face_normals, dtype=float)
    sweep = {}
    for off in offsets_m:
        f_lo = np.minimum(off / g_lo, 0.40)[:, None]
        f_hi = np.minimum(off / g_hi, 0.40)[:, None]
        _, _, t_lo = trimesh.proximity.closest_point(m, C + f_lo * (K - C))
        _, _, t_hi = trimesh.proximity.closest_point(m, C + f_hi * (S - C))
        a = np.degrees(np.arccos(np.clip(
            np.sum(fn[t_lo] * fn[t_hi], axis=1), -1.0, 1.0)))
        sweep[f"{off:g}"] = {"median_deg": float(np.median(a)),
                             "p10_deg": float(np.percentile(a, 10)),
                             "frac_below_30deg": float(np.mean(a < 30.0))}
    ref = chine_dihedral_analytic(hull, n=n)
    first = f"{offsets_m[0]:g}"
    return {"offsets_m": [float(o) for o in offsets_m],
            "sweep": sweep,
            "median_deg": sweep[first]["median_deg"],
            "median_at_offset_m": float(offsets_m[0]),
            "sweep_median_deg": [sweep[f"{o:g}"]["median_deg"]
                                 for o in offsets_m],
            # NaN on a radiused bilge, and the note says why rather than
            # leaving a reader to guess whether the measurement failed or the
            # reference does not exist. See `chine_dihedral_analytic`.
            "analytic_median_deg": float(np.median(ref)),
            "analytic_note": (
                "knuckle reference REFUSED: roundness "
                f"{hull.roundness:.4f} > 0, the corner is filleted away"
                if hull.roundness > 0.0 else "hard chine"),
            "roundness": float(hull.roundness),
            "n_stations": int(n)}


def chine_row_normal_jump(hull: Hull, V: np.ndarray, T: np.ndarray,
                          nz: int) -> dict:
    """Normal jump [deg] across the CHINE ROW of a structured `closed_mesh`.

    Only valid on a surface whose vertices still include the analytic chine
    points — i.e. the current path and a Blender rebuild of the same grid, and
    NOT a remeshed or subdivided one. Returns `n_edges` 0 and NaN medians when
    the chine vertices are not present, which is a refusal, not a score.
    """
    from scipy.spatial import cKDTree

    from ..stl_forensics import edge_table, normal_jumps
    L = float(hull.x[-1])
    xs = np.linspace(0.0, L, 600)
    _, yc, zc, _, _ = station_geometry(hull.params, xs)
    chine = np.stack([xs, yc, zc], axis=1)
    d, idx = cKDTree(np.asarray(V, dtype=float)).query(chine)
    if float(d.max()) > 1e-9:
        return {"n_edges": 0, "median_deg": float("nan"),
                "max_deg": float("nan"), "vertex_match_max_m": float(d.max()),
                "note": "chine vertices absent from this surface"}
    et = edge_table(np.asarray(T, dtype=int))
    ang, _ = normal_jumps(np.asarray(V, dtype=float),
                          np.asarray(T, dtype=int), et)
    uv = et["uv"][et["count"] == 2]
    on = np.zeros(len(V), dtype=bool)
    on[idx] = True
    sel = on[uv[:, 0]] & on[uv[:, 1]] & np.isfinite(ang)
    if not sel.any():
        return {"n_edges": 0, "median_deg": float("nan"),
                "max_deg": float("nan"), "vertex_match_max_m": float(d.max())}
    a = ang[sel]
    return {"n_edges": int(sel.sum()), "median_deg": float(np.median(a)),
            "max_deg": float(a.max()),
            "vertex_match_max_m": float(d.max()),
            "nz": int(nz), "chine_row": int(hull.chine_row(nz))}


# --------------------------------------------------------------------------
# One call that produces every number in the comparison table
# --------------------------------------------------------------------------


def surface_report(hull: Hull, V: np.ndarray, T: np.ndarray, label: str,
                   nz: int | None = None, included_angle: float = 150.0,
                   with_selfint: bool = True) -> dict:
    """Every metric `docs/research/BLENDER.md` compares, for one surface.

    Topology, watertightness and feature extraction are delegated to
    `navalai.stl_forensics` — the module that already owns those questions —
    rather than reimplemented. `included_angle` defaults to 150, which is what
    `navalai/cfd/case.py::SURFACE_FEATURES` writes, so the feature counts are
    the pipeline's own and not a second bar.
    """
    from ..stl_forensics import (edge_table, feature_edges, self_intersections,
                                 triangle_quantities)
    V = np.asarray(V, dtype=float)
    T = np.asarray(T, dtype=int)
    et = edge_table(T)
    tq = triangle_quantities(V, T)
    fe = feature_edges(V, T, included_angle, et)
    p0, p1, p2 = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    signed_vol = float(np.sum(np.einsum("ij,ij->i", p0, np.cross(p1, p2))) / 6.0)
    out = {
        "label": label,
        "n_verts": int(len(V)),
        "n_tris": int(len(T)),
        "n_open_edges": int(np.sum(et["count"] == 1)),
        "n_nonmanifold_edges": int(np.sum(et["count"] > 2)),
        "watertight": bool(np.all(et["count"] == 2)),
        "signed_volume_m3": signed_vol,
        "tri_area_min_m2": float(tq["area"].min()),
        "tri_aspect_p99": float(np.percentile(tq["aspect"], 99)),
        "min_angle_deg_p01": float(np.percentile(tq["min_angle_deg"], 1)),
        "feature_included_angle_deg": included_angle,
        "n_feature_edges": int(fe["n_feature_edges"]),
        "feature_edge_length_m": float(fe["feature_edge_total_length_m"]),
        "deviation": deviation_by_xl(hull, V, T),
        "mesh_to_analytic": mesh_to_analytic_mm(hull, V, T),
        "chine": chine_dihedral_measured(hull, V, T),
    }
    if nz is not None:
        out["chine_row_jump"] = chine_row_normal_jump(hull, V, T, nz)
    if with_selfint:
        si = self_intersections(V, T)
        # `complete` False means the pair budget was exhausted, i.e. the count
        # is a LOWER BOUND. Reporting it as a count would score an unfinished
        # search as a clean surface (docs/LESSONS.md defect class 1), so it
        # becomes None and the caller must say so.
        out["n_self_intersections"] = (int(si["n_self_intersecting_pairs"])
                                       if si.get("complete") else None)
        out["selfint_raw"] = {k: v for k, v in si.items()
                              if isinstance(v, (int, float, bool, str))}
    return out
