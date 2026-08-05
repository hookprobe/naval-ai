"""Gate 2M verdict: KCS C_T against the Tokyo-2015 tank data, with per-case GCI.

`post_gci.py` computes the grid-convergence index but stops there — nothing
turned it into a PASS/FAIL against the experiment, so the gate's own criterion
lived only in prose. This script is that criterion, executable.

It refuses to produce a verdict it cannot support:
  - a grid whose force history has not SETTLED (drift > 5% over the last fifth)
    is reported and excluded, because an unconverged number is not a result;
  - fewer than three grids gives a C_T comparison but NO GCI, and says so;
  - a symmetric case has its force DOUBLED (half the hull is meshed), which is
    the single easiest way to be exactly 2x wrong and never notice.

  python scripts/gate2m.py runs/kcs_gci
  python scripts/gate2m.py runs/kcs_sym          # single grid, no GCI
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import benchmarks.kcs as KCS
from navalai.cfd import post

RHO = 998.8            # kg/m^3, the value the forces FO is told
SETTLE_TOL = 0.05      # 5% drift over the last fifth => not settled


def read_info(case: Path) -> dict:
    out: dict = {}
    for line in (case / "case.info").read_text().splitlines():
        if "=" in line and not line.startswith(("NOTE", "run:", "Gate")):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def grid_result(case: Path) -> dict | None:
    """Settled mean drag and C_T for one grid, or None if it has no usable data."""
    try:
        t, fx = post.parse_forces(post.forces_path(case))
    except FileNotFoundError:
        return None
    t, fx = np.asarray(t, float), np.asarray(fx, float)
    if len(t) < 20:
        return None

    info = read_info(case)
    n = max(len(fx) // 5, 1)
    last, prev = fx[-n:].mean(), fx[-2 * n:-n].mean()
    drift = abs(last - prev) / max(abs(last), 1e-12)

    drag = abs(last)
    if info.get("symmetric", "False") == "True":
        # Half the hull is meshed, so the patch integral is half the force.
        drag *= 2.0

    lwl = float(info["lwl"])
    speed = float(info["speed_ms"])
    # Wetted surface of the FULL hull from the same STL the case was built on.
    stl = case / "constant" / "triSurface" / "hull.stl"
    s_wetted = post.stl_wetted_area(str(stl), waterline=0.0) if stl.exists() else float("nan")
    ct = drag / (0.5 * RHO * s_wetted * speed ** 2) if s_wetted == s_wetted else float("nan")

    return {
        "name": case.name, "cells": int(info.get("cells_bg", 0)),
        "t_end": float(t[-1]), "drag_n": drag, "ct": ct, "drift": drift,
        "settled": drift <= SETTLE_TOL, "s_wetted": s_wetted,
        "speed": speed, "lwl": lwl,
    }


def gci(f1: float, f2: float, f3: float, r12: float, r23: float) -> dict:
    """Roache GCI on three grids, fine->coarse f1,f2,f3. r are refinement ratios."""
    e12, e23 = f2 - f1, f3 - f2
    if abs(e12) < 1e-15 or e12 * e23 <= 0:
        return {"p": float("nan"), "gci_fine_pct": float("nan"),
                "note": "oscillatory or zero change — Richardson does not apply"}
    p = math.log(abs(e23 / e12)) / math.log(r12)
    f_ext = f1 + e12 / (r12 ** p - 1.0)
    gci_fine = 1.25 * abs(e12 / f1) / (r12 ** p - 1.0) * 100.0
    return {"p": p, "f_extrapolated": f_ext, "gci_fine_pct": gci_fine, "note": ""}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/kcs_gci")
    cases = [root] if (root / "system").is_dir() else [
        d for n in ("coarse", "medium", "fine") if (d := root / n).is_dir()]
    if not cases:
        sys.exit(f"no case or triplet under {root}")

    rows = [r for c in cases if (r := grid_result(c))]
    if not rows:
        sys.exit(f"no force data yet under {root}")

    lo, hi = KCS.scatter_band()
    print(f"Gate 2M — KCS resistance, Fn {KCS.DESIGN_FN}, "
          f"U {KCS.DESIGN_SPEED} m/s, Lpp {KCS.LPP} m")
    print(f"EFD (KRISO): C_T = {KCS.EFD['ct']:.4e}   "
          f"Tokyo-2015 scatter {lo:.3e} .. {hi:.3e}\n")
    print(f"{'grid':>8} {'bg cells':>9} {'t_end':>7} {'drag N':>9} "
          f"{'C_T':>10} {'E%D':>7} {'drift':>7}  settled")
    print("-" * 74)
    for r in rows:
        print(f"{r['name']:>8} {r['cells']:9d} {r['t_end']:7.1f} "
              f"{r['drag_n']:9.1f} {r['ct']:10.4e} "
              f"{KCS.error_vs_efd(r['ct']):+7.1f} {100*r['drift']:6.1f}%  "
              f"{'yes' if r['settled'] else 'NO'}")

    usable = [r for r in rows if r["settled"]]
    if not usable:
        print("\nVERDICT: NO RESULT — no grid has settled "
              f"(drift <= {100*SETTLE_TOL:.0f}%). Extend --end-time.")
        return 2

    if len(usable) < 3:
        r = usable[-1]
        inside = lo <= r["ct"] <= hi
        print(f"\n{len(usable)} settled grid(s): C_T comparison only, NO GCI. "
              "A single grid carries no discretisation uncertainty, so this "
              "cannot close the gate on its own.")
        print(f"VERDICT: {'inside' if inside else 'OUTSIDE'} the scatter band "
              f"({KCS.error_vs_efd(r['ct']):+.1f}% vs EFD)")
        return 0 if inside else 1

    fine, med, coarse = usable[-1], usable[-2], usable[-3]
    r12 = (med["cells"] / fine["cells"]) ** (1 / 3)
    r23 = (coarse["cells"] / med["cells"]) ** (1 / 3)
    g = gci(fine["ct"], med["ct"], coarse["ct"], 1 / r12 if r12 < 1 else r12,
            1 / r23 if r23 < 1 else r23)
    print(f"\nrefinement ratios measured from cell counts: "
          f"r12 {r12:.4f}  r23 {r23:.4f}")
    if g["note"]:
        print(f"GCI: {g['note']}")
        print("VERDICT: NO RESULT — the triplet is not a convergent family.")
        return 2
    print(f"observed order p = {g['p']:.2f}   "
          f"extrapolated C_T = {g['f_extrapolated']:.4e}   "
          f"GCI(fine) = {g['gci_fine_pct']:.2f}%")

    ct, unc = fine["ct"], g["gci_fine_pct"] / 100.0 * fine["ct"]
    inside = (ct + unc) >= lo and (ct - unc) <= hi
    print(f"\nC_T = {ct:.4e} +/- {unc:.2e} (GCI)   "
          f"E%D = {KCS.error_vs_efd(ct):+.1f}%")
    print(f"VERDICT: {'PASS' if inside else 'FAIL'} — "
          f"{'overlaps' if inside else 'does not overlap'} the Tokyo-2015 "
          f"scatter band {lo:.3e}..{hi:.3e}")
    if not inside:
        print("Recorded as measured. Do NOT widen the band to make it pass "
              "(honesty rule 6).")
    return 0 if inside else 1


if __name__ == "__main__":
    raise SystemExit(main())
