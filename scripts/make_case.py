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
from navalai.cfd.case import motion_from_geometry, write_resistance_case
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
    ap.add_argument("--free-motion", action="store_true",
                help="release the hull in heave and pitch (sinkage and trim). "
                     "KCS Case 2.1 is towed FREE, so a fixed solve answers a "
                     "different question than the tank measured.")
    ap.add_argument("--kg", type=float, default=None,
                help="VCG above keel [m]. The only mass property a hull shape "
                     "cannot supply; defaults to VCB (neutral) if omitted.")
    ap.add_argument("--transient", action="store_true",
                help="force real-time transient even for a fixed hull. LTS is "
                     "the default for fixed cases because it is ~30x cheaper, "
                     "but it is WRONG for wave-making: MEASURED pressure drag "
                     "14.5x the expected wave component vs 2.6-4.2x transient.")
    ap.add_argument("--symmetric", action="store_true",
                help="half domain on y=0 (type symmetry). The hull is symmetric, so the other half computes a mirror image and tells us nothing: HALF the cells "
                     "for the same answer.")
    ap.add_argument("--np", type=int, default=8, dest="np_procs")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--anchor", choices=("coarse", "fine"), default="coarse",
                help="which end of the GCI family scale 1.0 is. 'fine' builds "
                     "DOWNWARD (cheap: the costly grid is one you already have); "
                     "'coarse' builds upward (~12x more expensive).")
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
                args.np_procs, symmetric=args.symmetric,
                                         free_motion=motion,
                                         lts=False if args.transient else None)
    else:
        hull = Hull(grammar.vector(REFERENCE))

        def gen(out, s):
            return write_resistance_case(hull, args.speed, out,
                                         args.end_time, s, args.np_procs,
                                         symmetric=args.symmetric,
                                         lts=False if args.transient else None)

    motion = None
    if args.free_motion:
        if not args.stl:
            sys.exit("--free-motion currently needs --stl (mass and LCB come "
                     "from the geometry)")
        motion = motion_from_geometry(args.stl, args.lwl, args.symmetric,
                                      kg_above_keel=args.kg)
        print(f"free motion: mass {motion['mass']:.1f} kg, "
              f"CoG ({motion['cog_x']:.3f}, {motion['cog_y']:.3f}, "
              f"{motion['cog_z']:.3f}), Iyy {motion['iyy']:.0f} kg m^2")

    if args.triplet:
        # GCI depends on the RATIO between grids, not their absolute size, so
        # the family is built DOWNWARD from the finest grid that is affordable
        # rather than upward from an arbitrary coarse one. Upward from scale 1
        # costs ~12x the coarse grid (medium ~3x, fine ~8x); downward costs
        # ~1.5x, because the expensive grid is the one already paid for.
        # `--anchor fine` therefore makes scale 1.0 the FINE grid.
        scales = {"fine": (1.0, 2 ** -0.5, 0.5),
                  "coarse": (1.0, 2 ** 0.5, 2.0)}[args.anchor]
        for name, s in zip(("coarse", "medium", "fine"),
                           sorted(scales) if args.anchor == "fine" else scales):
            meta = gen(Path(args.out) / name, s)
            print(f"{name}: {meta['bg_cells']} bg cells -> {args.out}/{name}")
    else:
        meta = gen(args.out, args.scale)
        print(f"case: {meta['bg_cells']} bg cells -> {args.out}")


if __name__ == "__main__":
    main()
