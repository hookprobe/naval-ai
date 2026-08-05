"""Unattended-meshing robustness: the plan's Gate 2 criterion, measured.

`NavalArchAI-BuildPlan.md` Phase 2 requires ">=95% of a 200-random-valid-hull
batch meshes and converges unattended", and Risk #1 names unattended CFD
robustness "the largest unknown". Nothing measured it: no test in the repo runs
OpenFOAM at all, so the criterion sat unverified while the gate table looked
healthy.

This samples valid hulls from the grammar and MESHES each one
(blockMesh + snappyHexMesh + checkMesh, no solve — meshing is ~2 min, a solve
is hours). A hull counts as meshed only if checkMesh reports neither
zero-volume cells NOR incorrectly oriented faces (negative face pyramids).
Both kill interFoam on the first timestep, so a mesh carrying either has not
"meshed unattended" in any useful sense. Zero-volume alone is not enough: a KCS
mesh at hull refinement (3,4) had none and still died, carrying 18 wrongly
oriented faces.

  python scripts/mesh_robustness.py --n 10 [--scale 1.0] [--keep]

Reduced N is honest as long as N is reported — it is a lower-bound estimate of
the batch success rate, not the plan's full 200-hull figure.
"""

from __future__ import annotations

import argparse
import json
import os
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
    # Run THE pipeline, not a copy of it. This used to inline
    # blockMesh+snappy+checkMesh, which silently diverged the day meshing became
    # staged (refine -> snap -> z-refine -> layers): it would have measured a
    # layerless mesh and reported it as the unattended success rate.
    runner = Path(__file__).resolve().parents[1] / "navalai/cfd/run-case.sh"
    t0 = time.time()
    subprocess.run(["openfoam", str(runner), str(case), str(np_procs)],
                   capture_output=True, timeout=7200,
                   env={**os.environ, "MESH_ONLY": "1"})
    cm = (case / "log.checkMesh").read_text() if (case / "log.checkMesh").exists() else ""
    sn = ""
    for name in ("log.snappy.layers", "log.snappy"):
        if (case / name).exists():
            sn += (case / name).read_text()

    def grab(pat, text=None, cast=float, default=None):
        m = re.search(pat, text if text is not None else cm)
        return cast(m.group(1)) if m else default

    zero = grab(r"Writing (\d+) zero volume cells", cast=int, default=0)
    # Wrongly oriented faces (negative face pyramids) kill interFoam just as
    # reliably as zero-volume cells. MEASURED: a KCS mesh at hull refinement
    # (3,4) reported ZERO zero-volume cells and still died on the first
    # timestep with an FPE — it carried 18 incorrectly oriented faces. Judging
    # "meshed" on zero-volume alone called that mesh clean.
    wrong_n = grab(r"Error in face pyramids: (\d+) faces are incorrectly",
                   cast=int, default=0)
    cells = grab(r"cells:\s+(\d+)", cast=int, default=-1)
    # Layer coverage is the `patch faces layers avg thickness` table snappy
    # prints at the END of the layer pass, as a MEAN LAYER COUNT. The
    # "Added N out of M cells" lines are castellation iterations and read as
    # 0.3% on a patch that is in fact fully layered.
    from navalai.cfd.case import _MAX_LAYERS
    lm = re.findall(r"^hull\s+(\d+)\s+([\d.]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)",
                    sn, re.M)
    layers = [100.0 * float(a[1]) / _MAX_LAYERS for a in lm]
    return {
        "cells": cells,
        "zero_volume_cells": zero,
        "wrong_oriented": wrong_n,
        "non_ortho_max": grab(r"non-orthogonality Max: ([\d.]+)", default=-1.0),
        "max_skewness": grab(r"Max skewness = ([\d.]+)", default=-1.0),
        "failed_checks": grab(r"Failed (\d+) mesh checks", cast=int, default=0),
        "layer_pct": max((float(a) for a in layers), default=-1.0),
        "seconds": round(time.time() - t0, 1),
        # PROXY bar, kept for continuity with the earlier 75% measurement.
        "meshed": zero == 0 and wrong_n == 0 and cells > 0,
    }


def solve_one(case: Path, np_procs: int = 1) -> dict:
    """Does interFoam actually run on this mesh? — the gate's REAL bar.

    The proxy above (no zero-volume, no wrongly-oriented faces) turned out not
    to predict it in either direction: the KCS case solves happily with 5
    wrongly-oriented faces, and an own-hull mesh with a PERFECT checkMesh
    (0 zero-volume, 0 wrongly-oriented, skew 3.44, 100% layer coverage) is
    reported here alongside it. So measure the thing itself.

    NOTE for whoever writes the next detector: do NOT test for the substring
    "Floating point" in the log. Every interFoam log contains
    "trapFpe: Floating point exception trapping enabled" in its BANNER, which
    made a clean 0.5 s run read as a crash and briefly convinced me the whole
    hull family was unsolvable. Judge by the time actually reached.
    """
    runner = Path(__file__).resolve().parents[1] / "navalai/cfd/run-case.sh"
    t0 = time.time()
    subprocess.run(["openfoam", str(runner), str(case), str(np_procs)],
                   capture_output=True, timeout=7200)
    log = case / "log.interFoam"
    text = log.read_text() if log.exists() else ""
    times = [float(m) for m in re.findall(r"^Time = ([\d.eE+-]+)", text, re.M)]
    end = float(subprocess.run(
        ["openfoam", "foamDictionary", "-entry", "endTime", "-value",
         str(case / "system/controlDict")],
        capture_output=True, text=True).stdout.strip() or 0)
    reached = times[-1] if times else 0.0
    return {
        "solve_end_time": end,
        "solve_reached": reached,
        "solve_steps": len(times),
        "fatal": "--> FOAM FATAL" in text,
        "solve_seconds": round(time.time() - t0, 1),
        "solves": bool(end) and reached >= end - 1e-9 and "--> FOAM FATAL" not in text,
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
    ap.add_argument("--solve", type=float, default=0.0,
                    help="also solve each case to this endTime [s] and report "
                         "the rate that actually RUNS (the gate's real bar)")
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
            write_resistance_case(Hull(x), args.speed, case,
                                  end_time=args.solve or 1.0,
                                  scale=args.scale, np_procs=1)
            r = mesh_one(case)
            if args.solve:
                r.update(solve_one(case))
        except Exception as exc:                       # generation itself failed
            r = {"cells": -1, "zero_volume_cells": -1, "layer_pct": -1.0,
                 "max_skewness": -1.0, "seconds": 0.0, "meshed": False,
                 "error": repr(exc)[:120]}
        r["hull"] = i
        rows.append(r)
        print(f"{i:3d} {r['cells']:9d} {r['layer_pct']:7.1f} "
              f"{r['zero_volume_cells']:8d} {r['max_skewness']:8.2f} "
              f"{r['seconds']:6.1f}  {'ok' if r['meshed'] else 'FAILED'}"
              + (f"  {'RUNS' if r.get('solves') else 'no-run'}"
                 f" (t={r.get('solve_reached', 0):.3g})" if args.solve else ""))
        if r["meshed"] and not args.keep:
            shutil.rmtree(case, ignore_errors=True)

    ok = sum(1 for r in rows if r["meshed"])
    rate = 100.0 * ok / max(len(rows), 1)
    if args.solve:
        sok = sum(1 for r in rows if r.get("solves"))
        srate = 100.0 * sok / max(len(rows), 1)
        print(f"SOLVES to t={args.solve}: {sok}/{len(rows)} = {srate:.1f}%  "
              f"(the gate's real bar)")
        print(f"clean-checkMesh proxy:   {ok}/{len(rows)} = {rate:.1f}%  "
              f"(reported for continuity with the earlier 75% figure)")
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
