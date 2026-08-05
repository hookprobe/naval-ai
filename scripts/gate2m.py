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
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import benchmarks.kcs as KCS
from navalai.cfd import post

RHO = 998.8            # kg/m^3, the value the forces FO is told
SETTLE_TOL = 0.05      # 5% drift over the last fifth => not settled
# The plan's Gate 2 bar is "documented grid uncertainty (target <= ~2.5%, the
# published bar)". 5% is the outer limit we will call converged at all; the
# Tokyo-2015 groups achieved 2.5-3.5%. A triplet whose own GCI exceeds this has
# not earned a verdict, however close its C_T happens to land.
GCI_BAR_PCT = 5.0


def read_info(case: Path) -> dict:
    out: dict = {}
    for line in (case / "case.info").read_text().splitlines():
        if "=" in line and not line.startswith(("NOTE", "run:", "Gate")):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def motion_result(case: Path) -> dict | None:
    """Settled sinkage and trim from the sixDoF report, or None if fixed.

    EFD gives both (sinkage -1.394e-2 m, trim -0.169 deg), so a free-motion run
    is checked on three numbers rather than one. They are also the cheapest
    sanity check there is: a hull that sinks the wrong way has a sign error
    somewhere, and no amount of C_T agreement would reveal it.
    """
    log = case / "log.interFoam"
    if not log.exists():
        return None
    text = log.read_text()
    zs = [float(m) for m in re.findall(
        r"Centre of rotation: \([-\d.eE+]+ [-\d.eE+]+ ([-\d.eE+]+)\)", text)]
    # Orientation is row-major; R[0][2] = sin(pitch) for rotation about y.
    sins = [float(m) for m in re.findall(
        r"Orientation: \([-\d.eE+]+ [-\d.eE+]+ ([-\d.eE+]+)", text)]
    if len(zs) < 20 or len(sins) < 20:
        return None
    n = max(len(zs) // 5, 1)
    z0 = zs[0]
    sink = float(np.mean(zs[-n:])) - z0
    sink_prev = float(np.mean(zs[-2 * n:-n])) - z0
    # SIGN. The KCS STL's bow is at +x (verified: half-beam tapers 0.5095 ->
    # 0.0008 over x = 6.1 -> 7.72 with the stem rising to z = 0.4021; the blunt
    # transom is at x = 0), and the inlet is the +x face with U = (-u, 0, 0).
    # Rotation about +y by theta > 0 takes xhat -> (cos, 0, -sin), i.e. BOW
    # DOWN, and R[0][2] = sin(theta) > 0. EFD's convention is negative = bow
    # down, so reporting +asin(R[0][2]) made a physically CORRECT bow-down
    # result print +0.169 deg against EFD -0.169 and score a +200% error.
    # This check exists to catch sign errors; it had one.
    def _trim_of(vals):
        return -math.degrees(math.asin(max(-1.0, min(1.0, float(np.mean(vals))))))

    trim = _trim_of(sins[-n:])
    trim_prev = _trim_of(sins[-2 * n:-n])
    return {
        "sinkage_m": sink, "trim_deg": trim,
        "sink_drift": abs(sink - sink_prev) / max(abs(sink), 1e-9),
        "trim_drift": abs(trim - trim_prev) / max(abs(trim), 1e-9),
    }


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

    # Free-motion runs are checked on sinkage and trim as well, since EFD
    # reports both and they are what a fixed-attitude solve gets wrong.
    for case, r in zip(cases, rows):
        mo = motion_result(case)
        if not mo:
            continue
        print(f"\n{r['name']}: FREE sinkage/trim")
        print(f"  sinkage {mo['sinkage_m']*1e3:+7.2f} mm  "
              f"(EFD {KCS.EFD['sinkage_m']*1e3:+.2f} mm, "
              f"{100*(mo['sinkage_m']-KCS.EFD['sinkage_m'])/abs(KCS.EFD['sinkage_m']):+.1f}%)"
              f"  drift {100*mo['sink_drift']:.1f}%")
        print(f"  trim    {mo['trim_deg']:+7.3f} deg (EFD {KCS.EFD['trim_deg']:+.3f} deg, "
              f"{100*(mo['trim_deg']-KCS.EFD['trim_deg'])/abs(KCS.EFD['trim_deg']):+.1f}%)"
              f"  drift {100*mo['trim_drift']:.1f}%")

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
        # NO VERDICT is not success. This branch has just said in words that it
        # "cannot close the gate on its own" and then returned 0, which is what
        # any CI reads. 3 = inconclusive, distinct from 0 pass and 1 fail.
        return 3

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
    # UNCERTAINTY MUST NEVER WIDEN THE ACCEPTANCE REGION.
    # The old test was overlap of [ct-unc, ct+unc] with the band, with NO cap
    # on the GCI — so a sloppier grid study passed more easily. MEASURED at the
    # recorded C_T: GCI 2.5% -> FAIL, 5% -> FAIL, 12.8% -> FAIL, 15% -> PASS,
    # 100% -> PASS. The Tokyo-2015 groups achieved 2.5-3.5%, i.e. a careful
    # triplet failed where a careless one closed the gate. The bar is now two
    # independent conditions, both of which must hold.
    within_band = lo <= ct <= hi
    converged = g["gci_fine_pct"] <= GCI_BAR_PCT
    inside = within_band and converged
    print(f"\nC_T = {ct:.4e} +/- {unc:.2e} (GCI {g['gci_fine_pct']:.2f}%)   "
          f"E%D = {KCS.error_vs_efd(ct):+.1f}%")
    print(f"  in the Tokyo-2015 band {lo:.3e}..{hi:.3e}: "
          f"{'YES' if within_band else 'NO'}")
    print(f"  GCI <= {GCI_BAR_PCT:.1f}% (published groups achieved 2.5-3.5%): "
          f"{'YES' if converged else 'NO'}")
    print(f"VERDICT: {'PASS' if inside else 'FAIL'}")
    if not inside:
        print("Recorded as measured. Do NOT widen the band, and do NOT let a "
              "coarse grid's own uncertainty buy the overlap (honesty rule 6).")
    return 0 if inside else 1


if __name__ == "__main__":
    raise SystemExit(main())
