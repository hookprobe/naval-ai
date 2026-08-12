#!/usr/bin/env python
"""Can ParaView contour a refineMesh hanging-node mesh, and what could Blender
be handed if it could?

    /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
        scripts/blender_isosurface_probe.py runs/stageA_h4_n7 /tmp/probe

WHY THIS EXISTS RATHER THAN A QUOTE. `CLAUDE.md` records that
`scripts/render_case.py` "produces noise on any case with `_REFINE_ROUNDS > 0`
... MergeBlocks, Tetrahedralize and ResampleToImage+mask were all tried and all
failed". `scripts/render_case.py` as committed USES ResampleToImage plus a
`vtkValidPointMask` threshold and documents it AS THE FIX ("an isosurface of a
regular grid is exact"). Those two statements cannot both be current, and this
repository's rule is that a measurement beats a document.

It could not be settled on a real wave field: MEASURED 2026-08-12, no run in
`runs/` carries both `constant/polyMesh` AND a solved time directory —
`clean-runs.sh` trimmed the mesh out of `kcs_s1`, `kcs`, `kcs_iso` and
`gci/*`, and the 25 `zbf_*` / `stageA_*` directories that still have a mesh
are MESH-ONLY builds from the Gate 2U layer campaign with no solution on them.

So this probes the MECHANISM on a mesh-only case, where the right answer is
known independently: `0/alpha.water` is the setFields initial condition, a step
at z = 0, so the alpha = 0.5 isosurface must be the FLAT PLANE z = 0 and
nothing else. Any shredding, doubled facet or stray sheet is the contouring
defect, visible against an exactly known truth.

Three routes are timed and measured, in the order they would be preferred:

  A. Contour the native (multiblock, hanging-node) mesh   -- what "cannot be
     contoured" refers to
  B. MergeBlocks then contour
  C. ResampleToImage + valid-point mask then contour      -- what render_case.py
     actually does

Each is scored by planarity: max |z| over the isosurface points, which is 0 for
the correct answer and grows with every spurious facet. That is a number, not a
look at a picture — the same reason `docs/research/CFD.md` prefers a measured
period to an eyeballed one.

The PLY written by route C is what Blender would import; Blender reads no
OpenFOAM and no VTK, so whichever route wins is a PREREQUISITE for a Cycles
render, not an alternative to one.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from paraview.simple import (  # type: ignore
    CellDatatoPointData, Contour, ExtractBlock, MergeBlocks, OpenFOAMReader,
    ResampleToImage, SaveData, Threshold,
)


def _stats(src, label, secs):
    src.UpdatePipeline()
    di = src.GetDataInformation()
    n = di.GetNumberOfPoints()
    if not n:
        print(f"{label:<34} points 0  -- NO SURFACE  ({secs:.1f}s)")
        return {"label": label, "n_points": 0, "max_abs_z": None,
                "seconds": secs}
    b = di.GetBounds()
    maxz = max(abs(b[4]), abs(b[5]))
    print(f"{label:<34} points {n:>9}  max|z| {maxz:9.5f} m  "
          f"cells {di.GetNumberOfCells():>9}  ({secs:.1f}s)")
    return {"label": label, "n_points": int(n), "max_abs_z": float(maxz),
            "n_cells": int(di.GetNumberOfCells()), "seconds": secs}


def main() -> int:
    if len(sys.argv) < 3:
        sys.exit("usage: pvbatch blender_isosurface_probe.py <case> <outdir>")
    case, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not (case / "constant" / "polyMesh").is_dir():
        sys.exit(f"FATAL: {case} has no constant/polyMesh — this probe needs a "
                 "mesh, and refusing is the point (an absent mesh must not be "
                 "reported as a clean contour)")

    stub = case / "case.foam"
    stub.touch()
    reader = OpenFOAMReader(registrationName="case", FileName=str(stub))
    reader.CaseType = "Reconstructed Case"
    reader.MeshRegions = ["internalMesh"]
    reader.CellArrays = ["alpha.water"]
    # alpha.water is a CELL field. Contour needs POINT data, and asking for it
    # without saying so returns "Contour array is null" and an EMPTY surface —
    # which would read as "route A produced nothing" when the truth is "route A
    # was never given the array". Measured that way first; recorded so the next
    # reader does not repeat it.
    reader.Createcelltopointfiltereddata = 1
    reader.UpdatePipeline()
    print(f"case   : {case}")
    print(f"times  : {list(reader.TimestepValues or [0.0])}")

    interior = ExtractBlock(registrationName="interior", Input=reader)
    interior.Selectors = ["/Root/internalMesh"]
    interior.UpdatePipeline()
    b = interior.GetDataInformation().GetBounds()
    print(f"bounds : {tuple(round(v, 3) for v in b)}")
    print("\nTRUTH: 0/alpha.water is the setFields step at z=0, so the "
          "alpha=0.5 isosurface\n       is the plane z=0. max|z| is the "
          "error, in metres.\n")

    rows = []

    t0 = time.time()
    a_p = CellDatatoPointData(registrationName="a_p", Input=interior)
    a_p.CellDataArraytoprocess = ["alpha.water"]
    a = Contour(registrationName="A", Input=a_p)
    a.ContourBy = ["POINTS", "alpha.water"]
    a.Isosurfaces = [0.5]
    rows.append(_stats(a, "A native multiblock contour", time.time() - t0))

    t0 = time.time()
    mb = MergeBlocks(registrationName="mb", Input=interior)
    b_p = CellDatatoPointData(registrationName="b_p", Input=mb)
    b_p.CellDataArraytoprocess = ["alpha.water"]
    bb = Contour(registrationName="B", Input=b_p)
    bb.ContourBy = ["POINTS", "alpha.water"]
    bb.Isosurfaces = [0.5]
    rows.append(_stats(bb, "B MergeBlocks then contour", time.time() - t0))

    t0 = time.time()
    lwl = (b[1] - b[0]) / 4.5
    zc = 0.06 * lwl
    res = ResampleToImage(registrationName="uniform", Input=interior)
    res.UseInputBounds = 0
    res.SamplingBounds = [b[0], b[1], b[2], b[3], -zc, zc]
    nx = 320
    res.SamplingDimensions = [nx,
                              max(int(nx * (b[3] - b[2]) / (b[1] - b[0])), 32),
                              56]
    valid = Threshold(registrationName="valid", Input=res)
    valid.Scalars = ["POINTS", "vtkValidPointMask"]
    valid.LowerThreshold, valid.UpperThreshold = 0.5, 1.5
    valid.ThresholdMethod = "Between"
    c = Contour(registrationName="C", Input=valid)
    c.ContourBy = ["POINTS", "alpha.water"]
    c.Isosurfaces = [0.5]
    rows.append(_stats(c, "C ResampleToImage+mask contour", time.time() - t0))

    ply = out / "freeSurface_C.ply"
    try:
        SaveData(str(ply), proxy=c)
        print(f"\nPLY for Blender: {ply}  {ply.stat().st_size} bytes")
    except Exception as exc:                                # noqa: BLE001
        print(f"\nPLY export FAILED: {exc}")

    import json
    (out / "isosurface_probe.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
