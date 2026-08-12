#!/usr/bin/env python
"""Measure Blender-built hull surfaces against the CURRENT path and the
ANALYTIC hull. Writes one JSON per hull; prints the tables that go into
`docs/research/BLENDER.md`.

    python scripts/blender_compare.py --hulls 4 8 14 --out data/blender

WHAT THE BASELINE ACTUALLY IS, because the brief that commissioned this called
it "the CadQuery STL" and it is not. `navalai/cfd/case.py::hull_to_stl`
triangulates `Hull.closed_mesh` directly in numpy and writes ascii STL itself.
`cadquery` appears in this repository ONLY in `navalai/export.py`, for STEP and
IGES. No STL on the CFD path has ever been through OpenCascade, so "Blender vs
CadQuery" is not the comparison available; "Blender vs the analytic
triangulation" is, and that is what this script measures.

Variants, all at the SHIPPED resolution `write_resistance_case` uses for each
hull (`stl_resolution` clamps every hull in this batch to 600x120):

    current              Hull.closed_mesh, welded  -- the shipped surface
    blender-grid         the same grid rebuilt in Blender and exported
    blender-voxel-<v>    blender-grid + Remesh(VOXEL, v) before export
    blender-subsurf-<n>  a COARSE cage (41 x 16) + n levels Catmull-Clark

Nothing here is a gate and nothing here changes the pipeline.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from navalai.blender.metrics import surface_report
from navalai.blender.run import build_via_blender, blender_version
from navalai.blender.spec import shipped_resolution
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.stl_forensics import load_stl, mesh_of_hull

#: The cage the subdivision arm starts from: `Hull.n_stations` (41) in x, and
#: nz=16, which is `hull_to_stl`'s own default section count. Chosen so the
#: cage is a plausible hand-editable control mesh rather than a resampling of
#: the shipped one — a 600x120 cage subdivided is not a designer's cage.
SUBSURF_CAGE = (41, 16)

#: Crease bar for the subdivision arms, in degrees of NORMAL JUMP. Not a new
#: threshold: `navalai/cfd/case.py::SURFACE_FEATURES` writes `includedAngle
#: 150` for `surfaceFeatureExtract`, which marks an edge whose faces meet at
#: under 150 deg, i.e. whose normals differ by more than 30. An edge that is a
#: feature to the mesher is an edge that gets a crease here.
CREASE_ANGLE_DEG = 30.0

#: `stl_forensics.self_intersections` costs ~15 s at 289k triangles and scales
#: with the candidate-pair count. Above this the strict check is SKIPPED and
#: reported as "-", never as 0 — the surfaceCheck arm still covers those
#: surfaces (`scripts/blender_foamcheck.py`).
SELFINT_TRI_CAP = 400_000


def hull_batch(idx: list[int]) -> dict[int, Hull]:
    X, _ = sample_valid(25, MissionSpec(), seed=0)
    return {i: Hull(X[i]) for i in idx}


def run_hull(i: int, hull: Hull, out: Path, voxels: list[float],
             subsurfs: list[int], selfint: bool) -> dict:
    nx, nz = shipped_resolution(hull)
    rows: list[dict] = []
    receipts: dict = {}

    t0 = time.time()
    V, T = mesh_of_hull(hull, nx, nz)
    build_s = time.time() - t0
    r = surface_report(hull, V, T, "current", nz=nz, with_selfint=selfint)
    r["build_s"] = build_s
    r["nx"], r["nz"] = nx, nz
    # the shipped path writes this exact surface; size it the same way
    from navalai.cfd.case import hull_to_stl
    cur_stl = out / f"hull{i:02d}_current.stl"
    hull_to_stl(hull, cur_stl, nx=nx, nz=nz)
    r["stl_bytes"] = cur_stl.stat().st_size
    rows.append(r)

    def blender_arm(label, bnx, bnz, subsurf=0, voxel=None, crease=None):
        stl = out / f"hull{i:02d}_{label}.stl"
        rec = build_via_blender(hull, stl, bnx, bnz, subsurf=subsurf,
                                voxel=voxel, workdir=out,
                                crease_angle_deg=crease)
        receipts[label] = rec
        Vv, Tt = load_stl(stl)
        rr = surface_report(hull, Vv, Tt, label,
                            nz=bnz if (subsurf == 0 and voxel is None) else None,
                            with_selfint=selfint and len(Tt) <= SELFINT_TRI_CAP)
        rr["build_s"] = rec["wall_s"]
        rr["stl_bytes"] = rec["stl_bytes"]
        rr["nx"], rr["nz"] = bnx, bnz
        rr["coord_roundtrip_max_m"] = rec["coord_roundtrip_max_m"]
        rows.append(rr)

    blender_arm("blender-grid", nx, nz)
    for v in voxels:
        blender_arm(f"blender-voxel-{v:g}", nx, nz, voxel=v)
    for s in subsurfs:
        blender_arm(f"blender-subsurf-{s}", SUBSURF_CAGE[0], SUBSURF_CAGE[1],
                    subsurf=s)
        # ... and the same with Blender's OWN feature-preservation switched on.
        # Measuring default Catmull-Clark alone would be a strawman: it cannot
        # keep a knuckle by construction, but Blender's subdivision honours
        # per-edge creases and the pipeline's own 30 deg feature bar marks
        # exactly the chine, keel, deck edge and transom corner.
        blender_arm(f"blender-subsurf-{s}-creased", SUBSURF_CAGE[0],
                    SUBSURF_CAGE[1], subsurf=s, crease=CREASE_ANGLE_DEG)
    # Catmull-Clark on the SHIPPED cage, not a coarse one. This is the arm
    # that isolates subdivision's non-interpolating property from cage
    # coarseness: the cage points here lie ON the analytic surface to 1e-12 m,
    # so anything the subdivided surface loses, subdivision took.
    blender_arm("blender-subsurf-1-finecage", nx, nz, subsurf=1)
    blender_arm("blender-subsurf-1-finecage-creased", nx, nz, subsurf=1,
                crease=CREASE_ANGLE_DEG)

    doc = {"hull": i, "lwl_m": float(hull.x[-1]), "nx": nx, "nz": nz,
           "chine_row": hull.chine_row(nz),
           "blender": blender_version(), "rows": rows, "receipts": receipts}
    (out / f"hull{i:02d}.json").write_text(json.dumps(doc, indent=1))
    return doc


def print_tables(docs: list[dict]) -> None:
    for d in docs:
        print(f"\n=== hull {d['hull']}  Lwl {d['lwl_m']:.3f} m  "
              f"grid {d['nx']}x{d['nz']}  chine_row {d['chine_row']} ===")
        print(f"{'surface':<32}{'tris':>9}{'verts':>9}{'MB':>7}"
              f"{'wtr':>5}{'selfX':>7}{'featE':>7}{'vol m3':>10}"
              f"{'maxdev':>9}{'m2a':>8}{'chine':>8}")
        for r in d["rows"]:
            print(f"{r['label']:<32}{r['n_tris']:>9}{r['n_verts']:>9}"
                  f"{r['stl_bytes']/1e6:>7.1f}"
                  f"{('Y' if r['watertight'] else 'N'):>5}"
                  f"{('-' if r.get('n_self_intersections') is None else r['n_self_intersections']):>7}"
                  f"{r['n_feature_edges']:>7}"
                  f"{r['signed_volume_m3']:>10.3f}"
                  f"{r['deviation']['overall_max_mm']:>9.2f}"
                  f"{r['mesh_to_analytic']['max_mm']:>8.2f}"
                  f"{r['chine']['median_deg']:>8.1f}")
        print("\n  max analytic->mesh deviation [mm] by x/L bin")
        print("  " + f"{'x/L':<32}" + "".join(f"{c:>8.2f}"
              for c in d["rows"][0]["deviation"]["bin_centres"]))
        for r in d["rows"]:
            print("  " + f"{r['label']:<32}"
                  + "".join(f"{v:>8.2f}" for v in r["deviation"]["max_mm"]))
        offs = d["rows"][0]["chine"]["offsets_m"]
        print(f"\n  chine dihedral [deg], median over {d['rows'][0]['chine']['n_stations']}"
              f" stations, vs offset from the chine [m]"
              f"  (analytic {d['rows'][0]['chine']['analytic_median_deg']:.1f})")
        print("  " + f"{'offset m':<32}" + "".join(f"{o:>8.4g}" for o in offs))
        for r in d["rows"]:
            print("  " + f"{r['label']:<32}"
                  + "".join(f"{v:>8.1f}" for v in r["chine"]["sweep_median_deg"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hulls", type=int, nargs="+", default=[4, 8, 14])
    ap.add_argument("--out", default="data/blender")
    ap.add_argument("--voxels", type=float, nargs="*",
                    default=[0.05, 0.025, 0.0125])
    ap.add_argument("--subsurf", type=int, nargs="*", default=[1, 2, 3])
    ap.add_argument("--no-selfint", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    hulls = hull_batch(a.hulls)
    docs = [run_hull(i, hulls[i], out, a.voxels, a.subsurf, not a.no_selfint)
            for i in a.hulls]
    print_tables(docs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
