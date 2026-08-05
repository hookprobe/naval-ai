"""Unattended-meshing robustness: the plan's Gate 2 criterion, measured.

`NavalArchAI-BuildPlan.md` Phase 2 requires ">=95% of a 200-random-valid-hull
batch meshes and converges unattended", and Risk #1 names unattended CFD
robustness "the largest unknown". Nothing measured it: no test in the repo runs
OpenFOAM at all, so the criterion sat unverified while the gate table looked
healthy.

This samples valid hulls from the grammar and MESHES each one
(blockMesh + snappyHexMesh + checkMesh, no solve — meshing is ~2 min, a solve
is hours). A hull counts as meshed only if checkMesh reports no zero-volume
cells: those are what kill interFoam on the first timestep, so a mesh carrying
them has not "meshed unattended" in any useful sense.

  python scripts/mesh_robustness.py --n 10 [--scale 1.0] [--keep]

Reduced N is honest as long as N is reported — it is a lower-bound estimate of
the batch success rate, not the plan's full 200-hull figure.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.cfd.case import write_resistance_case
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec


def mesh_one(case: Path, np_procs: int = 1) -> dict:
    """blockMesh + surfaceFeatureExtract + snappyHexMesh + checkMesh."""
    sh = (f"blockMesh -case {case} > {case}/l.bm 2>&1; "
          f"surfaceFeatureExtract -case {case} > {case}/l.sf 2>&1; "
          f"snappyHexMesh -overwrite -case {case} > {case}/l.sn 2>&1; "
          f"checkMesh -case {case} > {case}/l.cm 2>&1")
    t0 = time.time()
    subprocess.run(["openfoam", "bash", "-c", sh], capture_output=True,
                   timeout=7200)
    cm = (case / "l.cm").read_text() if (case / "l.cm").exists() else ""
    sn = (case / "l.sn").read_text() if (case / "l.sn").exists() else ""

    def grab(pat, text=None, cast=float, default=None):
        m = re.search(pat, text if text is not None else cm)
        return cast(m.group(1)) if m else default

    zero = grab(r"Writing (\d+) zero volume cells", cast=int, default=0)
    layers = re.findall(r"Added \d+ out of \d+ cells \(([\d.]+)%\)", sn)
    return {
        "cells": grab(r"cells:\s+(\d+)", cast=int, default=-1),
        "zero_volume_cells": zero,
        "wrong_oriented": grab(r"Writing (\d+) faces with incorrect orientation",
                               cast=int, default=0),
        "non_ortho_max": grab(r"non-orthogonality Max: ([\d.]+)", default=-1.0),
        "max_skewness": grab(r"Max skewness = ([\d.]+)", default=-1.0),
        "failed_checks": grab(r"Failed (\d+) mesh checks", cast=int, default=0),
        "layer_pct": max((float(a) for a in layers), default=-1.0),
        "seconds": round(time.time() - t0, 1),
        # the bar: zero-volume cells kill interFoam on the first timestep
        "meshed": zero == 0 and grab(r"cells:\s+(\d+)", cast=int, default=-1) > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None, help="where cases go (temp if unset)")
    ap.add_argument("--keep", action="store_true", help="keep failing cases")
    ap.add_argument("--json", default=None, help="write the full record here")
    args = ap.parse_args()

    root = Path(args.out) if args.out else Path("/tmp/mesh_robustness")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    mission = MissionSpec()
    X, _ = sample_valid(args.n, mission, seed=args.seed)
    print(f"meshing {len(X)} valid hulls at scale {args.scale} "
          f"(plan bar: >=95% of 200)\n")
    print(f"{'#':>3} {'cells':>9} {'layer%':>7} {'zeroVol':>8} {'skew':>8} "
          f"{'sec':>6}  verdict")
    print("-" * 62)

    rows = []
    for i, x in enumerate(X):
        case = root / f"h{i:03d}"
        try:
            write_resistance_case(Hull(x), args.speed, case, end_time=1.0,
                                  scale=args.scale, np_procs=1)
            r = mesh_one(case)
        except Exception as exc:                       # generation itself failed
            r = {"cells": -1, "zero_volume_cells": -1, "layer_pct": -1.0,
                 "max_skewness": -1.0, "seconds": 0.0, "meshed": False,
                 "error": repr(exc)[:120]}
        r["hull"] = i
        rows.append(r)
        print(f"{i:3d} {r['cells']:9d} {r['layer_pct']:7.1f} "
              f"{r['zero_volume_cells']:8d} {r['max_skewness']:8.2f} "
              f"{r['seconds']:6.1f}  {'ok' if r['meshed'] else 'FAILED'}")
        if r["meshed"] and not args.keep:
            shutil.rmtree(case, ignore_errors=True)

    ok = sum(1 for r in rows if r["meshed"])
    rate = 100.0 * ok / max(len(rows), 1)
    print("-" * 62)
    print(f"meshed unattended: {ok}/{len(rows)} = {rate:.1f}%   "
          f"(plan bar >=95% on 200 hulls; this is N={len(rows)})")
    if rate < 95.0:
        print("BELOW THE BAR — recorded, not softened. "
              "See PLM.md roadmap: unattended-meshing robustness.")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"n": len(rows), "scale": args.scale, "speed": args.speed,
             "success_pct": rate, "bar_pct": 95.0, "rows": rows}, indent=2))
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
