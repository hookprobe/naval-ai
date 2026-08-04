"""Headless ParaView render of a finished resistance case.

Renders the free surface (alpha.water = 0.5) coloured by wave elevation, with
the hull patch in neutral grey, from an oblique bow-quarter view. Used to eyeball
what the numbers claim: a settled Kelvin wake, a waterline sitting where it
should, and no flooded hull interior.

Run with ParaView's own python (it is NOT the project venv):
  /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
      scripts/render_case.py runs/gci/medium renders/medium.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    Calculator, CellDatatoPointData, ColorBy, Contour, CreateView,
    ExtractBlock, GetColorTransferFunction, GetScalarBar, Hide, OpenFOAMReader,
    SaveScreenshot, Show,
)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: pvbatch render_case.py <case-dir> <out.png>")
    case, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if not (case / "system" / "controlDict").exists():
        sys.exit(f"FATAL: '{case}' is not an OpenFOAM case")
    out.parent.mkdir(parents=True, exist_ok=True)

    # ParaView's OpenFOAM reader wants a .foam stub next to the case.
    stub = case / "case.foam"
    stub.touch()

    reader = OpenFOAMReader(registrationName="case", FileName=str(stub))
    reader.CaseType = "Reconstructed Case"
    reader.MeshRegions = ["internalMesh", "patch/hull"]
    reader.CellArrays = ["alpha.water", "U", "p", "p_rgh"]
    reader.UpdatePipeline()

    times = list(reader.TimestepValues or [0.0])
    latest = times[-1]
    print(f"case      : {case}")
    print(f"times     : {times}")
    print(f"rendering : t = {latest}")

    view = CreateView("RenderView")
    view.ViewSize = [1600, 1000]
    view.OrientationAxesVisibility = 1
    view.Background = [0.13, 0.15, 0.19]
    view.UseColorPaletteForBackground = 0

    # --- free surface: alpha.water = 0.5 iso-surface, coloured by elevation ---
    p2c = CellDatatoPointData(registrationName="c2p", Input=reader)
    p2c.CellDataArraytoprocess = ["alpha.water", "U", "p", "p_rgh"]

    surf = Contour(registrationName="freeSurface", Input=p2c)
    surf.ContourBy = ["POINTS", "alpha.water"]
    surf.Isosurfaces = [0.5]

    elev = Calculator(registrationName="elevation", Input=surf)
    elev.ResultArrayName = "waveElevation"
    elev.Function = "coordsZ"

    disp = Show(elev, view)
    disp.Representation = "Surface"
    ColorBy(disp, ("POINTS", "waveElevation"))
    disp.SetScalarBarVisibility(view, True)
    lut = GetColorTransferFunction("waveElevation")
    lut.ApplyPreset("Cool to Warm (Extended)", True)
    # A few cells at the bow/transom hold the extremes; rescaling to the full
    # range flattens the wake to one colour. Clamp symmetrically so the Kelvin
    # pattern is actually legible (the bar states the clamp).
    clamp = float(sys.argv[3]) if len(sys.argv) > 3 else 0.06
    lut.RescaleTransferFunction(-clamp, clamp)
    bar = GetScalarBar(lut, view)
    bar.Title, bar.ComponentTitle = "wave elevation", f"[m], clamped +/-{clamp}"

    # --- hull patch in neutral grey so the surface reads against it ---
    try:
        hull = ExtractBlock(registrationName="hull", Input=reader)
        hull.Selectors = ["/Root/patch/hull"]
        hdisp = Show(hull, view)
        hdisp.Representation = "Surface"
        ColorBy(hdisp, None)
        hdisp.AmbientColor = hdisp.DiffuseColor = [0.85, 0.86, 0.88]
    except Exception as exc:  # patch naming varies; the surface is the point
        print(f"note: hull patch not rendered ({exc})")

    view.ResetCamera()
    cam = view.GetActiveCamera()
    cam.Elevation(-35)
    cam.Azimuth(35)
    view.ResetCamera()
    cam.Dolly(1.45)
    view.StillRender()

    SaveScreenshot(str(out), view, ImageResolution=[1600, 1000])
    print(f"wrote     : {out}")


if __name__ == "__main__":
    main()
