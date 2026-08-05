"""Render an STL surface so geometry defects are SEEN, not inferred.

Written after a long debugging spiral on the KCS hull in which every diagnosis
came from numeric checks (watertightness, manifoldness, triangle quality) that
the surface passed while snappyHexMesh kept producing zero-volume cells. Look
at the surface first.

  /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
      scripts/render_stl.py hull.stl out.png [--edges]
"""

from __future__ import annotations

import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    CreateView, STLReader, SaveScreenshot, Show,
)


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: pvbatch render_stl.py <in.stl> <out.png> [--edges]")
    src, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    edges = "--edges" in sys.argv
    out.parent.mkdir(parents=True, exist_ok=True)

    reader = STLReader(registrationName="stl", FileNames=[str(src)])
    reader.UpdatePipeline()

    view = CreateView("RenderView")
    view.ViewSize = [1800, 900]
    view.Background = [0.10, 0.11, 0.14]
    view.UseColorPaletteForBackground = 0
    view.OrientationAxesVisibility = 1

    # Surface normals expose faceting and flipped/creased patches far better
    # than flat shading: a bad patch shows up as a hard shading discontinuity.
    d = Show(reader, view)
    d.Representation = "Surface With Edges" if edges else "Surface"
    d.AmbientColor = d.DiffuseColor = [0.80, 0.82, 0.86]
    if edges:
        d.EdgeColor = [0.15, 0.18, 0.25]
        d.LineWidth = 1.0

    # Explicit camera: "--view side|below|bow|quarter". Auto-framing on a
    # long thin hull picks a useless angle.
    b = reader.GetDataInformation().GetBounds()
    ctr = [(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2]
    L = max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    preset = "quarter"
    for a in sys.argv[3:]:
        if a.startswith("--view"):
            preset = a.split("=", 1)[1] if "=" in a else "quarter"
    pos = {"side":    [ctr[0], ctr[1] + 1.6 * L, ctr[2]],
           "below":   [ctr[0], ctr[1] + 0.5 * L, ctr[2] - 1.3 * L],
           "bow":     [ctr[0] + 1.5 * L, ctr[1] + 0.5 * L, ctr[2] + 0.3 * L],
           "quarter": [ctr[0] - 0.9 * L, ctr[1] + 0.9 * L, ctr[2] - 0.5 * L]}[preset]
    cam = view.GetActiveCamera()
    cam.SetFocalPoint(*ctr)
    cam.SetPosition(*pos)
    cam.SetViewUp(0, 0, 1)
    view.ResetCamera()
    view.StillRender()
    SaveScreenshot(str(out), view, ImageResolution=[1800, 900])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
