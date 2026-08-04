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


def cell_count(case: Path) -> int | None:
    """Cells actually meshed (checkMesh), falling back to the background count.

    GCI is only meaningful on a systematically refined family, so the ratio is
    MEASURED here. Assuming r = sqrt(2) while the generator quietly produced
    1.30 and 1.37 is precisely how a triplet reports a number it has not
    earned (the nz-snapping incident).
    """
    log = case / "log.checkMesh"
    if log.exists():
        for line in log.read_text().splitlines():
            if line.strip().startswith("cells:"):
                return int(line.split()[-1])
    info = case / "case.info"
    if info.exists():
        for line in info.read_text().splitlines():
            if line.startswith("cells_bg="):
                return int(line.split("=")[1])
    return None


def yplus_report(case: Path) -> str | None:
    """Last y+ line for the hull patch, if the yPlus function object ran.

    The build plan specifies wall functions at y+ ~ 30 (SJTU KCS pipeline).
    Only ~46% of hull faces take prism layers once the free surface is graded,
    so y+ is measured rather than assumed: y+ in the buffer layer (5-30) is
    where wall functions are least valid and skin friction goes quietly wrong.
    """
    root = case / "postProcessing" / "yPlus"
    if not root.is_dir():
        return None
    files = sorted(root.glob("*/yPlus.dat"), key=lambda p: float(p.parent.name))
    if not files:
        return None
    rows = [ln for ln in files[-1].read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]
    return rows[-1].strip() if rows else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="triplet root dir (contains coarse/medium/fine)")
    ap.add_argument("--tail", type=float, default=0.3,
                    help="settled fraction of the run to average (default 0.3)")
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--refinement", type=float, default=None,
                    help="grid refinement ratio r; default: MEASURED from the "
                         "actual cell counts rather than assumed")
    args = ap.parse_args()

    from navalai.cfd.post import parse_forces
    import numpy as np

    means = {}
    print(f"{'grid':8} {'mean drag [N]':>14} {'std [N]':>10} {'drift %':>8}")
    print("-" * 46)
    from navalai.cfd.post import forces_path
    for g in GRIDS:
        try:
            f = forces_path(Path(args.root) / g)          # merges restarts
        except FileNotFoundError:
            print(f"{g:8} MISSING (no forces under {args.root}/{g})")
            continue
        mean, std = mean_resistance(f, args.tail)
        means[g] = mean
        # settledness: drift between the two halves of the averaging tail;
        # > ~5% means the run is not stationary yet -> extend end-time
        t, fx = parse_forces(f)
        cut = t[0] + (1.0 - args.tail) * (t[-1] - t[0])
        seg_t, seg = t[t >= cut], fx[t >= cut]
        half = seg_t[0] + 0.5 * (seg_t[-1] - seg_t[0])
        m1, m2 = np.mean(seg[seg_t < half]), np.mean(seg[seg_t >= half])
        drift = 100.0 * abs(m2 - m1) / max(abs(mean), 1e-9)
        flag = "" if drift < 5.0 else "  <-- NOT SETTLED"
        print(f"{g:8} {mean:14.1f} {std:10.1f} {drift:8.1f}{flag}")

    # wall-function validity, per grid (time patch min max average)
    yp = {g: yplus_report(Path(args.root) / g) for g in GRIDS}
    if any(yp.values()):
        print("\ny+ on hull (time patch min max average):")
        for g in GRIDS:
            print(f"  {g:8} {yp[g] or 'not reported'}")
        print("  NOTE: read the MIN. The hull patch includes deck/topsides,")
        print("  which are dry; their y+ is meaningless and dominates max/avg.")

    # measured refinement ratio, per step, from the real cell counts
    counts = {g: cell_count(Path(args.root) / g) for g in GRIDS}
    refinement = args.refinement
    if all(counts.get(g) for g in GRIDS):
        r12 = (counts["medium"] / counts["coarse"]) ** (1 / 3)
        r23 = (counts["fine"] / counts["medium"]) ** (1 / 3)
        print(f"\ncells                        : "
              f"{counts['coarse']} / {counts['medium']} / {counts['fine']}")
        print(f"measured refinement ratio    : "
              f"{r12:.3f} (c->m), {r23:.3f} (m->f)")
        spread = 100.0 * abs(r23 - r12) / max(r12, r23)
        if spread > 5.0:
            print(f"  <-- WARNING: ratios differ by {spread:.1f}% — this is NOT a "
                  "systematically refined family; GCI below is not trustworthy")
        if refinement is None:
            refinement = (r12 * r23) ** 0.5
    if refinement is None:
        refinement = 2.0 ** 0.5
        print("\n(cell counts unavailable — falling back to assumed r = sqrt(2))")

    if len(means) == 3:
        rep = gci(means["coarse"], means["medium"], means["fine"], refinement)
        print(f"refinement ratio used        : {refinement:.3f}")
        print(f"\nRichardson extrapolated drag : {rep.f_extrapolated:.1f} N")
        print(f"observed order p             : {rep.p_observed:.2f}")
        print(f"GCI (fine grid)              : {rep.gci_fine_pct:.2f} %")
        print(f"method                       : {rep.method}")
        drag = abs(rep.f_fine)
        print(f"\nfine-grid drag @ {args.speed} m/s : {abs(rep.f_fine):.1f} N "
              f"(+/- {rep.gci_fine_pct / 100 * drag:.1f} N grid uncertainty)")

        # C_t is the form Tokyo-2015 reports, so Gate 2M is judged on it
        stl = Path(args.root) / "fine" / "constant" / "triSurface" / "hull.stl"
        if stl.exists():
            from navalai.cfd.post import (resistance_coefficient,
                                          stl_wetted_area)
            s_wet = stl_wetted_area(stl, 0.0)
            ct = resistance_coefficient(drag, s_wet, args.speed)
            band = rep.gci_fine_pct / 100 * ct
            print(f"wetted surface (STL, z<0)    : {s_wet:.3f} m^2")
            print(f"C_t (fine)                   : {ct:.5e} "
                  f"(+/- {band:.2e} from grid uncertainty)")
        print("compare: L1 Michell+ITTC tier prediction for the same hull/speed "
              "via navalai.evaluate")
    else:
        print("\n(run all three grids for the GCI report)")


if __name__ == "__main__":
    main()
