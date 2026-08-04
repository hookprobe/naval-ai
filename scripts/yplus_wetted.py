"""Wetted-only y+ on the hull — the honest wall-function check.

The yPlus function object reports min/max/average over the WHOLE hull patch,
which includes the deck and topsides. Those faces sit in AIR, where y+ is
meaningless, and they dominate the statistics: on the coarse own-hull grid the
patch average of 7508 inverts to a 177 mm first cell and the max of 61420 to
1446 mm, both LARGER than the 104 mm local hull cell. Only the min (41.8, i.e.
a 0.985 mm cell against a 0.706 mm target) reflected the wetted, layered
surface.

This masks the patch by alpha.water and reports y+ over the WET faces only, so
"are the wall functions valid?" gets a real answer instead of a caveat.

Run with ParaView's python (NOT the project venv):
  /Applications/ParaView-6.1.1.app/Contents/bin/pvbatch \
      scripts/yplus_wetted.py runs/gci/coarse [alpha-threshold]
"""

from __future__ import annotations

import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    CellDatatoPointData, ExtractBlock, MergeBlocks, OpenFOAMReader,
    Threshold, servermanager,
)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: pvbatch yplus_wetted.py <case-dir> [alpha-threshold]")
    case = Path(sys.argv[1]).resolve()
    alpha_min = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    stub = case / "case.foam"
    stub.touch()

    reader = OpenFOAMReader(registrationName="case", FileName=str(stub))
    reader.CaseType = "Reconstructed Case"
    reader.MeshRegions = ["patch/hull"]
    reader.CellArrays = ["yPlus", "alpha.water"]
    reader.UpdatePipeline()
    times = list(reader.TimestepValues or [0.0])
    t = times[-1]
    reader.UpdatePipeline(t)

    hull = MergeBlocks(registrationName="hull", Input=reader)
    hull.UpdatePipeline(t)

    def values(src, field):
        src.UpdatePipeline(t)
        d = servermanager.Fetch(src)
        arr = d.GetCellData().GetArray(field) if d else None
        if arr is None:
            return []
        return [arr.GetValue(i) for i in range(arr.GetNumberOfTuples())]

    def stats(src, field, label):
        v = sorted(values(src, field))
        if not v:
            print(f"  {label:22} (no {field} on the patch)")
            return None
        n = len(v)
        mean = sum(v) / n

        def pct(p):
            return v[min(int(p / 100.0 * n), n - 1)]

        # the only number that decides whether the wall model is being used
        # inside its range of validity
        in_band = sum(1 for x in v if 30.0 <= x <= 300.0) / n * 100.0
        print(f"  {label:22} faces {n:7d}  min {v[0]:8.1f}  med {pct(50):9.1f}  "
              f"p90 {pct(90):10.1f}  max {v[-1]:11.1f}  mean {mean:10.1f}")
        print(f"  {'':22} within 30<=y+<=300: {in_band:5.1f}% of faces")
        return mean

    print(f"case : {case}")
    print(f"time : {t}   alpha.water >= {alpha_min} counts as WET\n")
    stats(hull, "yPlus", "whole hull patch")

    wet = Threshold(registrationName="wet", Input=hull)
    wet.Scalars = ["CELLS", "alpha.water"]
    wet.LowerThreshold = alpha_min
    wet.UpperThreshold = 1.5
    wet.ThresholdMethod = "Between"
    stats(wet, "yPlus", f"WETTED (alpha>={alpha_min})")

    dry = Threshold(registrationName="dry", Input=hull)
    dry.Scalars = ["CELLS", "alpha.water"]
    dry.LowerThreshold = -0.5
    dry.UpperThreshold = alpha_min
    dry.ThresholdMethod = "Between"
    stats(dry, "yPlus", "dry (deck/topsides)")

    print("\nWall functions are intended for roughly 30 <= y+ <= 300.")
    print("Judge the WETTED row: the dry row is air and carries no meaning.")


if __name__ == "__main__":
    main()
