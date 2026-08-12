#!/usr/bin/env python
"""What the EXISTING unroller measures on hulls 4/8/14 — the baseline any
Blender flattening proposal has to beat.

    python scripts/blender_unroll_survey.py

THIS SCRIPT WRITES NO PANELS AND EXPORTS NOTHING. It calls `navalai.unroll`
and reports its numbers, because the question the owner asked ("should the
Blender path own manufacturing unfold, e.g. via the Export Paper Model
add-on?") is answerable from measurements this repository can already take,
and answering it by building a second unroller first would be the answer.

`navalai/unroll.py` is READ-ONLY here. A SECOND unrolling implementation would
be this repository's signature defect — and that module's own docstring
records what it cost the last time it had two developability metrics: the one
that printed the verdict (`dev_error_rel`, an O(h^2) chord residual) passed a
doubly-ruled hyperbolic paraboloid at 6.5e-4 against a 5e-3 bar. What
separates a developable surface from one is `ruling_twist`, which does not
shrink under refinement.

Material, from `navalai/limits.py` and not from anyone's assumption:
PLY_THICKNESS_M 0.015, BEND_RADIUS_RATIO 80 -> a 1.2 m minimum cold-bend
radius in marine plywood. Rigid sheet, developable-only. Nothing here stretches
to fit, which is why the hull is chined with ruled panels in the first place.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.limits import BEND_RADIUS_RATIO, PLY_THICKNESS_M
from navalai.mission import MissionSpec
from navalai.unroll import (SHEET_L_M, SHEET_W_M, hull_panels, min_strakes,
                            refold_deviation_mm, refold_surface_deviation_mm,
                            ruling_twist)


def survey(i: int, hull: Hull) -> dict:
    rows = []
    for family in ("constant-x", "developable"):
        for panel in hull_panels(hull, rulings=family):
            tw = ruling_twist(panel.src_a, panel.src_b)
            rows.append({
                "hull": i,
                "requested_family": family,
                "chosen_family": panel.rulings,
                "panel": panel.name,
                "ruling_twist_max": float(np.max(tw)),
                "ruling_twist_median": float(np.median(tw)),
                "refold_edge_mm": float(np.max(refold_deviation_mm(panel))),
                "refold_surface_mm": float(
                    refold_surface_deviation_mm(hull, panel)),
                "min_strakes": int(min_strakes(panel, PLY_THICKNESS_M)),
            })
    return {"hull": i, "lwl_m": float(hull.x[-1]), "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hulls", type=int, nargs="+", default=[4, 8, 14])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    X, _ = sample_valid(25, MissionSpec(), seed=0)

    print(f"marine ply {PLY_THICKNESS_M*1000:.0f} mm, bend-radius ratio "
          f"{BEND_RADIUS_RATIO:.0f} -> min cold-bend radius "
          f"{PLY_THICKNESS_M*BEND_RADIUS_RATIO:.2f} m; "
          f"sheet {SHEET_W_M} x {SHEET_L_M} m")
    print(f"\n{'hull':>5}{'panel':>15}{'family':>13}{'chosen':>13}"
          f"{'twist max':>11}{'twist med':>11}{'edge mm':>10}{'surf mm':>10}"
          f"{'strakes':>9}")
    docs = []
    for i in a.hulls:
        d = survey(i, Hull(X[i]))
        docs.append(d)
        for r in d["rows"]:
            print(f"{r['hull']:>5}{r['panel']:>15}{r['requested_family']:>13}"
                  f"{r['chosen_family']:>13}{r['ruling_twist_max']:>11.4f}"
                  f"{r['ruling_twist_median']:>11.4f}{r['refold_edge_mm']:>10.1f}"
                  f"{r['refold_surface_mm']:>10.1f}{r['min_strakes']:>9}")
    if a.out:
        Path(a.out).write_text(json.dumps(docs, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
