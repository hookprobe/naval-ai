"""Centreplane slice of alpha.water — is the water where it should be?

Written after a wave-field render showed a hull-shaped mass of shredded
interface. A surface render cannot distinguish "the free surface is breaking
up" from "the hull interior is flooded", and those have completely different
causes. A slice answers it in one look.

  /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
      scripts/render_slice.py runs/kcs out.png [y-position]
"""

from __future__ import annotations

import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    CellDatatoPointData, ColorBy, CreateView, GetColorTransferFunction,
    GetScalarBar, OpenFOAMReader, SaveScreenshot, Show, Slice,
)


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: pvbatch render_slice.py <case> <out.png> [y]")
    case, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    ypos = float(sys.argv[3]) if len(sys.argv) > 3 else 0.001
    stub = case / "case.foam"
    stub.touch()

    r = OpenFOAMReader(registrationName="c", FileName=str(stub))
    r.CaseType = "Reconstructed Case"
    r.MeshRegions = ["internalMesh"]
    r.CellArrays = ["alpha.water", "p_rgh", "U"]
    r.UpdatePipeline()
    t = list(r.TimestepValues or [0.0])[-1]
    r.UpdatePipeline(t)

    p2c = CellDatatoPointData(registrationName="c2p", Input=r)
    p2c.CellDataArraytoprocess = ["alpha.water"]

    sl = Slice(registrationName="mid", Input=p2c)
    sl.SliceType = "Plane"
    sl.SliceType.Origin = [0.0, ypos, 0.0]
    sl.SliceType.Normal = [0.0, 1.0, 0.0]

    view = CreateView("RenderView")
    view.ViewSize = [1900, 800]
    view.Background = [0.10, 0.11, 0.14]
    view.UseColorPaletteForBackground = 0
    view.OrientationAxesVisibility = 1
    view.InteractionMode = "2D"

    d = Show(sl, view)
    d.Representation = "Surface"
    ColorBy(d, ("POINTS", "alpha.water"))
    lut = GetColorTransferFunction("alpha.water")
    lut.ApplyPreset("Cool to Warm", True)
    lut.RescaleTransferFunction(0.0, 1.0)
    d.SetScalarBarVisibility(view, True)
    bar = GetScalarBar(lut, view)
    bar.Title, bar.ComponentTitle = "alpha.water", "1 = water, 0 = air"

    b = sl.GetDataInformation().GetBounds()
    cam = view.GetActiveCamera()
    cam.SetFocalPoint((b[0] + b[1]) / 2, ypos, (b[4] + b[5]) / 2)
    cam.SetPosition((b[0] + b[1]) / 2, ypos - 10.0, (b[4] + b[5]) / 2)
    cam.SetViewUp(0, 0, 1)
    view.ResetCamera()
    view.StillRender()
    SaveScreenshot(str(out), view, ImageResolution=[1900, 800])
    print(f"wrote {out} (t = {t}, y = {ypos})")


if __name__ == "__main__":
    main()
