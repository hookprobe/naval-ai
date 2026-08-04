"""Post-process a GCI triplet: tail-averaged drag per grid + Roache GCI.

Usage (any shell, venv active):
  python scripts/post_gci.py runs/gci
  python scripts/post_gci.py runs/gci --tail 0.3 --speed 2.57
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.cfd.post import gci, mean_resistance

GRIDS = ("coarse", "medium", "fine")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="triplet root dir (contains coarse/medium/fine)")
    ap.add_argument("--tail", type=float, default=0.3,
                    help="settled fraction of the run to average (default 0.3)")
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--refinement", type=float, default=2.0 ** 0.5)
    args = ap.parse_args()

    means = {}
    print(f"{'grid':8} {'mean drag [N]':>14} {'std [N]':>10}")
    print("-" * 36)
    for g in GRIDS:
        f = Path(args.root) / g / "postProcessing" / "forces" / "0" / "force.dat"
        if not f.exists():
            print(f"{g:8} MISSING ({f})")
            continue
        mean, std = mean_resistance(f, args.tail)
        means[g] = mean
        print(f"{g:8} {mean:14.1f} {std:10.1f}")

    if len(means) == 3:
        rep = gci(means["coarse"], means["medium"], means["fine"],
                  args.refinement)
        print(f"\nRichardson extrapolated drag : {rep.f_extrapolated:.1f} N")
        print(f"observed order p             : {rep.p_observed:.2f}")
        print(f"GCI (fine grid)              : {rep.gci_fine_pct:.2f} %")
        print(f"method                       : {rep.method}")
        drag = abs(rep.f_fine)
        print(f"\nfine-grid drag @ {args.speed} m/s : {abs(rep.f_fine):.1f} N "
              f"(+/- {rep.gci_fine_pct / 100 * drag:.1f} N grid uncertainty)")
        print("compare: L1 Michell+ITTC tier prediction for the same hull/speed "
              "via navalai.evaluate")
    else:
        print("\n(run all three grids for the GCI report)")


if __name__ == "__main__":
    main()
