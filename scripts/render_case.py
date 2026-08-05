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
    ExtractBlock, GetColorTransferFunction, GetScalarBar, Hide, MergeBlocks,
    OpenFOAMReader, ResampleToImage, SaveScreenshot, Show, Threshold,
)


def main() -> None:
    if len(sys.argv) < 3:
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
    # MERGE FIRST. Contouring the multiblock directly shredded the surface into
    # overlapping facets and ParaView warned "vtkPolyhedron ... cannot be
    # contoured" — the hanging-node cells refineMesh leaves are polyhedra, and
    # cell->point interpolation across block boundaries has no neighbours to
    # interpolate from. Merging to a single unstructured grid first fixes both,
    # and restricting to internalMesh keeps the hull patch out of the isosurface
    # (a wall face sitting at alpha 0.5 otherwise contours as free surface).
    interior = ExtractBlock(registrationName="interior", Input=reader)
    interior.Selectors = ["/Root/internalMesh"]
    interior.UpdatePipeline()
    b = interior.GetDataInformation().GetBounds()

    # RESAMPLE, do not contour the native mesh. refineMesh leaves hanging-node
    # cells; ParaView cannot contour them ("vtkPolyhedron ... cannot be
    # contoured") and emits garbage facets, producing a shredded mass covering
    # exactly the refinement-box footprint while the unrefined far field showed
    # a clean Kelvin pattern. MergeBlocks did not fix it and Tetrahedralize did
    # not fix it.
    #
    # It is a RENDERING failure, not a physics one — MEASURED on the same field:
    # 2.6 interface cells per column (a clean VOF interface is 2-4), 45.4% water
    # / 50.7% air, alpha bounded to -6e-5..1. Interpolating onto a uniform grid
    # sidesteps cell topology entirely, and an isosurface of a regular grid is
    # exact. Sampling is set from the free-surface cell size so the resample
    # never invents detail the mesh does not carry.
    # The domain is 4.5 Lwl long, so this recovers Lwl without being told it.
    # Sample a thin band about z=0: the waves live in ~+/-0.05 Lwl and sampling
    # the whole tank both wastes resolution and drags in the free-stream.
    lwl = (b[1] - b[0]) / 4.5
    zc = 0.06 * lwl
    res = ResampleToImage(registrationName="uniform", Input=interior)
    res.UseInputBounds = 0
    res.SamplingBounds = [b[0], b[1], b[2], b[3], -zc, zc]
    # Sized to the FREE-SURFACE CELL, not to the image: the mesh carries ~150 mm
    # cells over a 4.5 Lwl domain, i.e. ~220 real samples in x. 700 x 470 x 160
    # was 52 M points, which simply never finished while the solver held the
    # cores — and it could not have shown detail the mesh does not contain.
    nx = 320
    res.SamplingDimensions = [
        nx,
        max(int(nx * (b[3] - b[2]) / (b[1] - b[0])), 32),
        56,
    ]
    res.UpdatePipeline()

    # MASK THE INVALID POINTS. ResampleToImage writes alpha = 0 at every sample
    # OUTSIDE the mesh — beyond the tank walls and, critically, INSIDE THE HULL.
    # Contouring that gives a spurious alpha=0.5 sheet wrapped around the
    # sampling box and around the hull: the rectangular maroon slab. vtkValidPointMask
    # is 1 only where the sample actually landed in a cell.
    valid = Threshold(registrationName="valid", Input=res)
    valid.Scalars = ["POINTS", "vtkValidPointMask"]
    valid.LowerThreshold, valid.UpperThreshold = 0.5, 1.5
    valid.ThresholdMethod = "Between"

    p2c = valid
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
    # This used to fail with "invalid association string 'NONE'" from
    # ColorBy(disp, None), was caught, and printed a one-line note. The result
    # was a wave field rendered with NO HULL IN IT — so a broken interface at
    # the hull and a missing hull looked identical, which is precisely the
    # distinction the picture exists to make. Solid colour is set directly, and
    # a failure here is now FATAL rather than a footnote.
    # The block path is NOT the MeshRegions name. The reader lists the region
    # as "patch/hull", but the composite tree puts it under /Root/boundary/hull
    # — MEASURED: /Root/patch/hull yields 0 cells, /Root/boundary/hull yields
    # 22881, which matches snappy's layer table face count exactly. Try the
    # known spellings rather than hard-coding one that happens to work today.
    hull, n_hull = None, 0
    for sel in ("/Root/boundary/hull", "/Root/patch/hull", "/Root/hull"):
        hull = ExtractBlock(registrationName="hull", Input=reader)
        hull.Selectors = [sel]
        hull.UpdatePipeline()
        n_hull = hull.GetDataInformation().GetNumberOfCells()
        if n_hull:
            print(f"hull block: {sel}")
            break
    if n_hull == 0:
        sys.exit("FATAL: hull patch extracted 0 cells — check MeshRegions "
                 "and the block selector; refusing to render a CFD field "
                 "with no geometry in it")
    hdisp = Show(hull, view)
    hdisp.Representation = "Surface"
    hdisp.ColorArrayName = ["POINTS", ""]
    hdisp.AmbientColor = hdisp.DiffuseColor = [0.82, 0.83, 0.86]
    hdisp.Ambient, hdisp.Diffuse = 0.35, 0.85
    print(f"hull      : {n_hull} faces")

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
