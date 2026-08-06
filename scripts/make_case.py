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
from navalai.cfd.case import (layer_spec, motion_from_geometry,
                              write_resistance_case)
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

        def gen(out, s, n_layers=None):
            return write_resistance_case_from_stl(
                args.stl, args.lwl, args.speed, out, args.end_time, s,
                args.np_procs, symmetric=args.symmetric,
                                         free_motion=motion,
                                         lts=False if args.transient else None,
                                         n_layers=n_layers)
    else:
        hull = Hull(grammar.vector(REFERENCE))

        def gen(out, s, n_layers=None):
            return write_resistance_case(hull, args.speed, out,
                                         args.end_time, s, args.np_procs,
                                         symmetric=args.symmetric,
                                         lts=False if args.transient else None,
                                         n_layers=n_layers)

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
        ordered = list(zip(("coarse", "medium", "fine"),
                           sorted(scales) if args.anchor == "fine" else scales))
        # THE WALL MODEL IS PINNED AT THE ANCHOR, ONCE, AND HANDED TO EVERY
        # MEMBER. case.info has always claimed the wall model is held fixed
        # across the triplet, and the first-layer THICKNESS was — but the layer
        # COUNT is derived from the local hull cell, which scales with nx.
        # MEASURED on a symmetric KCS triplet before this change: 7 / 6 / 5
        # layers, i.e. the prism stack thinned by 43% across the family, so the
        # observed order p was measuring the near-wall mesh and the outer mesh
        # at the same time.
        #
        # THE ANCHOR IS THE FINEST GRID, NOT scale 1.0, AND THAT IS FORCED.
        # A fixed first layer and a fixed count give a stack of fixed HEIGHT in
        # metres, while the hull cell it extrudes into halves under refinement.
        # MEASURED on KCS at base 57: pinning the coarse grid's 7 layers gave a
        # 34.2 mm stack against the fine grid's 17.96 mm hull cell — ratio 1.90
        # — and `write_resistance_case` refuses above 1.2, because that is the
        # configuration that killed interFoam with deltaT collapsing to 1e-23.
        # The finest member is the binding constraint, so it sets the count and
        # every coarser grid inherits a stack that comfortably fits.
        anchor = max(s for _n, s in ordered)
        lwl = args.lwl if args.stl else float(Hull(grammar.vector(REFERENCE)).x[-1])
        probe = layer_spec(lwl, args.speed, anchor)
        pinned = probe["n_layers"]
        print(f"triplet: n_layers PINNED at {pinned} (finest scale {anchor:g}), "
              f"first layer {probe['first_layer_m'] * 1e3:.3f} mm — both held "
              f"constant, so the GCI bounds OUTER-flow discretisation only")
        built = []
        for name, s in ordered:
            meta = gen(Path(args.out) / name, s, n_layers=pinned)
            built.append(meta)
            print(f"{name}: {meta['bg_cells']} bg cells "
                  f"({meta['nx']}x{meta['ny']}) -> {args.out}/{name}")
        # THE FAMILY'S UNIFORMITY IS MEASURED HERE, WHERE IT IS STILL CHEAP TO
        # FIX. Richardson extrapolation assumes ONE systematically refined
        # family, and post_gci.py already warns when the two steps disagree —
        # but by then the grids have been solved. MEASURED: `--anchor coarse`
        # at base 57 gives 57/81/114, all multiples of 3, so ny = nx/3 is exact
        # and the spread is 0.03%; `--anchor fine` gives 28/40/57, which are
        # not, and the spread is 1.9%. That is still usable and still measured
        # downstream, but it should not be a surprise found three days later.
        c, m, f = (b["bg_cells"] for b in built)
        r12, r23 = (m / c) ** (1 / 3), (f / m) ** (1 / 3)
        spread = 100.0 * abs(r23 - r12) / max(r12, r23)
        print(f"family: r12 {r12:.4f}  r23 {r23:.4f}  spread {spread:.2f}%"
              + ("" if spread <= 1.0 else
                 "  <-- the two refinement steps disagree; r is MEASURED from "
                 "cell counts downstream, but a uniform family is what "
                 "Richardson assumes. --anchor coarse gives 0.03%."))
    else:
        meta = gen(args.out, args.scale)
        print(f"case: {meta['bg_cells']} bg cells -> {args.out}")


if __name__ == "__main__":
    main()
