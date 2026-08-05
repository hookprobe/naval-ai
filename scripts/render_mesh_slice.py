"""Transverse mesh slice — LOOK at the cells, do not infer them from checkMesh.

The 2026-08-05 blocker was a 38:1 background cell that snappy then refined
isotropically, so every level kept the 38:1 shape while the height shrank and
snapping folded cells inside out. checkMesh reported the CONSEQUENCE (zero
volume, wrongly oriented faces) and never the cause. One picture of the cells
at a station through the hull shows it immediately.

  /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
      scripts/render_mesh_slice.py runs/kcs_iso out.png [x-fraction]
"""

from __future__ import annotations

import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    CreateView, Hide, OpenFOAMReader, SaveScreenshot, Show, Slice,
)

case = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
xfrac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

foam = case / f"{case.name}.foam"
foam.touch()
r = OpenFOAMReader(FileName=str(foam))
r.MeshRegions = ["internalMesh"]
r.UpdatePipeline()
b = r.GetDataInformation().GetBounds()

sl = Slice(Input=r)
sl.SliceType.Origin = [b[0] + xfrac * (b[1] - b[0]), 0.0, 0.0]
sl.SliceType.Normal = [1.0, 0.0, 0.0]
sl.UpdatePipeline()

v = CreateView("RenderView")
v.ViewSize = [1600, 1000]
v.Background = [0.10, 0.11, 0.15]
v.OrientationAxesVisibility = 1
d = Show(sl, v)
d.Representation = "Surface With Edges"
d.AmbientColor = [0.55, 0.75, 1.0]
d.DiffuseColor = [0.16, 0.20, 0.30]
d.EdgeColor = [0.75, 0.88, 1.0]
d.LineWidth = 1.0

# Look down -x at the transverse plane, framed on the HULL, not the tank: the
# tank is 30x wider than the boat and a whole-domain view shows nothing.
half_beam = float(sys.argv[4]) if len(sys.argv) > 4 else 1.2
v.CameraPosition = [b[1] + 10.0, 0.5 * half_beam, 0.0]
v.CameraFocalPoint = [sl.SliceType.Origin[0], 0.5 * half_beam, 0.0]
v.CameraViewUp = [0.0, 0.0, 1.0]
v.CameraParallelProjection = 1
v.CameraParallelScale = half_beam
SaveScreenshot(str(out), v, ImageResolution=[1600, 1000])
print(f"wrote {out}  (x = {sl.SliceType.Origin[0]:.2f} m, "
      f"{xfrac:.0%} of {b[0]:.1f}..{b[1]:.1f}, half-beam view {half_beam} m)")
