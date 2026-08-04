"""Convert an IGES hull (Tokyo-2015 KCS/JBC distribution format) to a
watertight-ish STL for the CFD case generator, via the OCP kernel.

Usage:
  python scripts/iges2stl.py KCS.igs kcs.stl --deflection 0.005
  python scripts/iges2stl.py KCS.igs kcs.stl --scale 0.0316456 --z-shift -0.34

Post-conversion, verify and normalise before meshing:
  - units must be METRES (--scale converts, e.g. full->model scale)
  - the design waterline must sit at z=0 (--z-shift)
  - the bow-to-stern extent should span x in [0, LWL] (--x-shift)
Check the result with navalai.cfd.case.stl_watertight_report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("iges")
    ap.add_argument("stl")
    ap.add_argument("--deflection", type=float, default=0.005,
                    help="mesh chord tolerance [m] (smaller = finer STL)")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--x-shift", type=float, default=0.0)
    ap.add_argument("--z-shift", type=float, default=0.0)
    args = ap.parse_args()

    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.IGESControl import IGESControl_Reader
    from OCP.StlAPI import StlAPI_Writer

    reader = IGESControl_Reader()
    if reader.ReadFile(str(args.iges)) != 1:
        raise SystemExit(f"failed to read {args.iges}")
    reader.TransferRoots()
    shape = reader.OneShape()

    if args.scale != 1.0:
        t = gp_Trsf()
        t.SetScaleFactor(args.scale)
        shape = BRepBuilderAPI_Transform(shape, t, True).Shape()
    if args.x_shift or args.z_shift:
        t = gp_Trsf()
        t.SetTranslation(gp_Vec(args.x_shift, 0.0, args.z_shift))
        shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

    BRepMesh_IncrementalMesh(shape, args.deflection, False, 0.5, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = True
    if not writer.Write(shape, str(args.stl)):
        raise SystemExit("STL write failed")

    from navalai.cfd.case import stl_watertight_report
    rep = stl_watertight_report(Path(args.stl))
    print(f"wrote {args.stl}: {rep['n_tris']} tris, "
          f"watertight={rep['watertight']}, volume={rep['signed_volume']:.3f} m^3")
    if not rep["watertight"]:
        print("WARNING: not closed — IGES surface models often need the deck/"
              "transom capped. Inspect in ParaView; snappy may still cope, but "
              "closed is the standard we hold ourselves to.")


if __name__ == "__main__":
    main()
