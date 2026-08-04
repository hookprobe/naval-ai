"""Generate OpenFOAM resistance cases (single or GCI triplet).

Usage (on the Mac, any shell):
  python scripts/make_case.py --out runs/smoke --speed 2.57 --end-time 5
  python scripts/make_case.py --out runs/gci --speed 2.57 --triplet
Then, inside an `openfoam` session:
  navalai/cfd/run-case.sh runs/smoke 8
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai import grammar
from navalai.cfd.case import write_resistance_case
from navalai.geometry import Hull

REFERENCE = {
    "LWL": 10.0, "BWL": 3.2, "T": 0.55, "D": 1.55, "beta_mid": 8.0,
    "beta_bow": 30.0, "p_bow": 2.2, "p_stern": 3.0, "x_mb": 0.55,
    "r_transom": 0.75, "rocker": 0.15, "forefoot": 0.85, "flare": 10.0,
    "sheer_rise": 0.18, "beta_len": 0.35,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--end-time", type=float, default=40.0)
    ap.add_argument("--np", type=int, default=8, dest="np_procs")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--triplet", action="store_true",
                    help="write coarse/medium/fine at r=sqrt(2) for GCI")
    ap.add_argument("--stl", help="external hull STL (KCS/JBC calibration); "
                                  "metres, WL at z=0, x in [0, LWL]")
    ap.add_argument("--lwl", type=float,
                    help="waterline length [m], required with --stl")
    args = ap.parse_args()

    if args.stl:
        if not args.lwl:
            ap.error("--stl requires --lwl")
        from navalai.cfd.case import write_resistance_case_from_stl

        def gen(out, s):
            return write_resistance_case_from_stl(
                args.stl, args.lwl, args.speed, out, args.end_time, s,
                args.np_procs)
    else:
        hull = Hull(grammar.vector(REFERENCE))

        def gen(out, s):
            return write_resistance_case(hull, args.speed, out,
                                         args.end_time, s, args.np_procs)

    if args.triplet:
        for name, s in (("coarse", 1.0), ("medium", 2 ** 0.5), ("fine", 2.0)):
            meta = gen(Path(args.out) / name, s)
            print(f"{name}: {meta['bg_cells']} bg cells -> {args.out}/{name}")
    else:
        meta = gen(args.out, args.scale)
        print(f"case: {meta['bg_cells']} bg cells -> {args.out}")


if __name__ == "__main__":
    main()
