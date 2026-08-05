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
    ap.add_argument("--deflection", type=float, default=0.001,
                    help="mesh chord tolerance [m]. MEASURED on KCS: 0.004 and 0.001 both give a non-self-intersecting surface once sewn, 0.002 does not (4 intersections); 0.001 also resolves the bulbous bow.")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--x-shift", type=float, default=0.0)
    ap.add_argument("--z-shift", type=float, default=0.0)
    ap.add_argument("--sew-tol", type=float, default=1e-3,
                    help="sew adjacent NURBS patches within this tolerance "
                         "[m] BEFORE meshing (0 disables). The Tokyo-2015 KCS "
                         "IGES ships 194 unsewn patches, so without this each "
                         "patch tessellates independently and the STL has "
                         "hundreds of open edges along shared boundaries "
                         "(measured: 450, of which 397 were patch seams).")
    ap.add_argument("--mirror-y", action="store_true",
                    help="mirror about y=0 to build a full hull from a half "
                         "hull (the KCS distribution is a half body)")
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

    if args.mirror_y:
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
        from OCP.TopoDS import TopoDS_Builder, TopoDS_Compound
        m = gp_Trsf()
        m.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)))
        other = BRepBuilderAPI_Transform(shape, m, True).Shape()
        comp = TopoDS_Compound()
        b = TopoDS_Builder()
        b.MakeCompound(comp)
        b.Add(comp, shape)
        b.Add(comp, other)
        shape = comp

    if args.sew_tol > 0:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
        sew = BRepBuilderAPI_Sewing(args.sew_tol)
        sew.Add(shape)
        sew.Perform()
        shape = sew.SewedShape()

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
