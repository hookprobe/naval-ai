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

from navalai.cfd.case import (layer_backoff_ladder, layer_spec,
                              write_resistance_case)
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec


def mesh_one(case: Path, np_procs: int = 1, mesh_only: bool = True,
             timeout: float = 7200, parse_only: bool = False) -> dict:
    """blockMesh + surfaceFeatureExtract + snappyHexMesh + checkMesh.

    With `mesh_only=False` the SAME invocation goes on to solve, and
    `solve_one()` below only PARSES what it left behind. That is not a tidy-up:
    MEASURED 2026-08-11, calling the runner twice (once with MESH_ONLY=1, then
    again to solve) re-meshed every hull FROM SCRATCH, because MESH_ONLY exits
    before decomposePar and so leaves no `processor0/` for the resume branch to
    find. Every hull in the campaign paid the mesh cost twice — 76 s of the
    ~7 min budget per hull, thrown away, on a machine that thermal-sleeps under
    sustained load.
    """
    # Run THE pipeline, not a copy of it. This used to inline
    # blockMesh+snappy+checkMesh, which silently diverged the day meshing became
    # staged (refine -> snap -> z-refine -> layers): it would have measured a
    # layerless mesh and reported it as the unattended success rate.
    runner = Path(__file__).resolve().parents[1] / "navalai/cfd/run-case.sh"
    env = {**os.environ}
    if mesh_only:
        env["MESH_ONLY"] = "1"
    t0 = time.time()
    timed_out, rc = False, -1
    try:
        if not parse_only:                 # --reclassify reads, never runs
            rc = subprocess.run(
                ["openfoam", str(runner), str(case), str(np_procs)],
                capture_output=True, timeout=timeout, env=env).returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        # subprocess kills the `openfoam` wrapper, NOT the mpirun ranks it
        # exec'd. An orphaned interFoam then owns the box AND trips
        # run-case.sh's own concurrency guard (`pgrep -x interFoam`), so every
        # remaining hull in the batch exits 3 and the campaign records a wall
        # of failures that are really one hung case.
        for name in ("interFoam", "mpirun", "snappyHexMesh"):
            subprocess.run(["pkill", "-x", name], capture_output=True)
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
    # TWO COUNTS, ONE DEFECT, AND THE GATE AND THE RECORD READ DIFFERENT ONES.
    # checkMesh prints the face-pyramid CHECK and then writes the SET, and they
    # are not the same number. MEASURED 2026-08-11 on campaign hull 0:
    #     ***Error in face pyramids: 128 faces are incorrectly oriented.
    #     <<Writing 92 faces with incorrect orientation to set wrongOrientedFaces
    # and on hull 4, 55 against 38. This harness read the CHECK line (128) while
    # `run-case.sh`'s fatal bar reads the SET line (92) — and the bar itself was
    # calibrated on SET counts (5 solves, 10 dies, 73 dies). So the harness was
    # grading a different quantity from the one the gate enforces, and a hull
    # sitting between them (say 6 in the check, 5 in the set) would be RUN by
    # the pipeline and recorded as FAILED by the measurement of the pipeline.
    # The bar's quantity wins; the other is recorded rather than discarded, so
    # the discrepancy stays visible.
    wrong_n = grab(r"Writing (\d+) faces with incorrect orientation",
                   cast=int, default=0)
    wrong_pyr = grab(r"Error in face pyramids: (\d+) faces are incorrectly",
                     cast=int, default=0)
    cells = grab(r"cells:\s+(\d+)", cast=int, default=-1)
    # LAYER COVERAGE: TWO `hull ...` TABLES, AND THIS READ THE REQUESTED ONE.
    #
    # snappy prints the layer SPEC before extrusion and the ACHIEVED result
    # after, and they have different columns:
    #
    #   patch faces  layers  avg thickness[m]                  (NF == 5)
    #                        near-wall overall
    #   hull  49032    10     0.00243   0.0631
    #
    #   patch faces  layers          overall thickness          (NF == 6)
    #                target   mesh    [m]      [%]
    #   hull  49032    10       4.71   0.0416   66
    #
    # The old regex captured four groups after `hull` and took group 2 as the
    # layer count. In the SPEC table group 2 is the requested count; in the
    # ACHIEVED table group 2 is the `target` column — the requested count
    # again. So both matches carried the same number, `max()` could only ever
    # return it, and MEASURED 2026-08-11 on /tmp/probe_lts (lwl 15.0, n=10)
    # this reported `layer% 100.0` for a hull patch that achieved a mean of
    # 4.71 of 10 layers, i.e. 47.1%. That is the REQUESTED SPEC PRINTED UNDER
    # THE LABEL OF THE ACHIEVED RESULT — the defect class `run-case.sh` fixed
    # in itself on 2026-08-06 (its "first 5.68 m" incident), in a harness that
    # never got the same fix, and it was the single number this campaign was
    # meant to grade layer insertion by.
    #
    # Tables are now told apart by FIELD COUNT, the achieved count comes from
    # the NF==6 table's `mesh` column, and the denominator is the count this
    # case ASKED for rather than the module-wide cap _MAX_LAYERS (which was
    # wrong for every hull whose derived count is not 10).
    spec = re.findall(r"^hull\s+(\d+)\s+(\d+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*$",
                      sn, re.M)
    got = re.findall(r"^hull\s+(\d+)\s+(\d+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)"
                     r"\s+([\d.eE+-]+)\s*$", sn, re.M)
    n_req = int(spec[-1][1]) if spec else (int(got[-1][1]) if got else -1)
    n_got = float(got[-1][2]) if got else -1.0
    # An unmeasurable coverage is REFUSED, not scored as 0 or as 100 — see
    # docs/LESSONS.md defect class 1. -1.0 is the "not measured" sentinel and
    # the taxonomy below reads it as such.
    layer_pct = (100.0 * n_got / n_req) if (got and n_req > 0) else -1.0
    return {
        "cells": cells,
        "zero_volume_cells": zero,
        "wrong_oriented": wrong_n,
        "wrong_oriented_pyramid_check": wrong_pyr,
        "non_ortho_max": grab(r"non-orthogonality Max: ([\d.]+)", default=-1.0),
        "max_skewness": grab(r"Max skewness = ([\d.]+)", default=-1.0),
        "failed_checks": grab(r"Failed (\d+) mesh checks", cast=int, default=0),
        "layers_requested": n_req,
        "layers_achieved": n_got,
        "layer_pct": layer_pct,
        "seconds": round(time.time() - t0, 1),
        "runner_exit": rc,
        "timed_out": timed_out,
        # PROXY bar, kept for continuity with the earlier 75% measurement.
        "meshed": zero == 0 and wrong_n == 0 and cells > 0,
        # THE BAR THE PIPELINE ACTUALLY ENFORCES, which is not the same bar.
        # `run-case.sh` refuses at >0 zero-volume, >5 wrongly-oriented or >20
        # skewness; the proxy above demands ZERO wrongly-oriented faces. So a
        # mesh with 1-5 of them is RUN by the pipeline and recorded as FAILED
        # by the measurement of the pipeline — MEASURED 2026-08-11 on back-off
        # hull 8 (0 zero-volume, skew 5.89, proxy FAILED). Reporting only the
        # proxy understates the mesh rate against the gate's own definition;
        # reporting only this one breaks continuity with the 75% watermark.
        # Both are recorded, and the watermark is the SOLVE rate, which is the
        # conjunction the plan's clause actually asks for and is free of this
        # ambiguity entirely.
        "meshed_runner_bar": (zero == 0 and wrong_n <= 5 and cells > 0
                              and 0 <= (grab(r"Max skewness = ([\d.]+)",
                                             default=-1.0) or -1.0) <= 20.0),
        # WHICH SURFACE THIS ROW MEASURED. MEASURED 2026-08-12: not one of the
        # five gate2u-*.json artifacts recorded it, and commit bbf1a47 (the
        # chine onto a grid row) changed `navalai/geometry.py` and therefore
        # every hull's STL. So every rate on record — 23/25, 20/25, the cap-3,
        # cap-5 and cap-7 batches — describes a surface that no longer exists,
        # and NO FIELD IN THE ARTIFACT SAYS SO. That is LESSONS.md defect
        # class 5 (citing evidence that no longer exists) made structural: the
        # record cannot be checked against the code, in either direction.
        #
        # The datum already existed per case — `case.info` carries stl_sha256,
        # which is what gate2m.py matches against CHECKSUMS.json to refuse a
        # case that is not KCS. The campaign simply never carried it up into
        # its own row, so the one artifact that gets QUOTED was the one that
        # could not be verified.
        "stl_sha256": _case_stl_sha(case),
    }


def _case_stl_sha(case: Path) -> str:
    """The `stl_sha256` this case was generated from, or the honest refusal.

    Returns "UNRECORDED" rather than "" or None: an empty string compares equal
    to another empty string, so two batches meshed from DIFFERENT unknown
    surfaces would silently agree. The whole point of the field is to refuse
    that comparison, and a sentinel that quietly satisfies it is defect class 1
    reintroduced in the fix for defect class 5.
    """
    info = case / "case.info"
    if not info.exists():
        return "UNRECORDED"
    for line in info.read_text().splitlines():
        if line.startswith("stl_sha256="):
            return line.split("=", 1)[1].strip() or "UNRECORDED"
    return "UNRECORDED"


def solve_one(case: Path) -> dict:
    """Did interFoam actually run on this mesh? — the gate's REAL bar.

    PARSE ONLY. `mesh_one(..., mesh_only=False)` has already run the pipeline
    end to end; this reads what it left behind. It used to invoke the runner a
    SECOND time, which re-meshed the hull from scratch (see mesh_one).

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
    log = case / "log.interFoam"
    text = log.read_text() if log.exists() else ""
    times = [float(m) for m in re.findall(r"^Time = ([\d.eE+-]+)", text, re.M)]
    end = float(subprocess.run(
        ["openfoam", "foamDictionary", "-entry", "endTime", "-value",
         str(case / "system/controlDict")],
        capture_output=True, text=True).stdout.strip() or 0)
    reached = times[-1] if times else 0.0
    # deltaT collapsing while Courant stays high is CLAUDE.md's documented
    # pathological-cell signature, and it is the difference between "this mesh
    # is bad" and "the numerics need tuning". Record the smallest deltaT the
    # controller reached so the taxonomy can tell them apart instead of
    # counting both as "did not finish". Under LTS there is no global deltaT
    # line at all, which is itself worth knowing.
    dts = [float(m) for m in re.findall(r"^deltaT = ([\d.eE+-]+)", text, re.M)]
    # A DIVERGENCE IS NOT A "--> FOAM FATAL", AND SAYING SO COSTS THE DIAGNOSIS.
    # MEASURED 2026-08-11 on campaign hull 2 (lwl 10.804, 812282 cells, a mesh
    # that passed EVERY checkMesh bar — 0 zero-volume, 0 wrongly-oriented, skew
    # 6.95): interFoam reached LTS iteration 104 and then died with
    #   Foam::sigFpe::sigHandler -> GAMGSolver::scale
    #   prterun noticed that process rank 7 ... exited on signal 4
    # There is no "--> FOAM FATAL" line anywhere in that log, so a detector
    # keyed on it reports `fatal: false` and the verdict comes out
    # "solver-stopped-short" — which reads like a timeout and sends the next
    # session looking at the wall clock. It was a floating-point divergence:
    # force coefficients at 1e200 and continuity error 1.59e94.
    #
    # Under LTS there is also no `deltaT =` line to watch collapse; the
    # equivalent signal is the LOCAL time scale, and it had fallen to 8.6e-105.
    # That is the same pathological-cell signature CLAUDE.md documents for the
    # transient path, expressed in the only quantity LTS has.
    crashed = ("sigFpe::sigHandler" in text or "exited on signal" in text
               or "Illegal instruction" in text)
    fts = [float(m) for m in re.findall(
        r"^Flow time scale min/max = ([\d.eE+-]+)", text, re.M)]
    return {
        "solve_end_time": end,
        "solve_reached": reached,
        "solve_steps": len(times),
        "min_deltaT": min(dts) if dts else -1.0,
        "min_flow_time_scale": min(fts) if fts else -1.0,
        "fatal": "--> FOAM FATAL" in text,
        "crashed": crashed,
        "solves": (bool(end) and reached >= end - 1e-9
                   and "--> FOAM FATAL" not in text and not crashed),
    }


def classify(r: dict) -> str:
    """WHY this hull failed, by MECHANISM. The percentage is one number; the
    grouping is what tells the next session where to spend a day.

    Order matters: the pipeline stops at its first refusal, so the earliest
    stage that refused is the cause, and the later fields are simply absent.
    """
    if r.get("error"):
        return "generation"                 # write_resistance_case itself threw
    if r.get("timed_out"):
        return "timeout"
    if r.get("cells", -1) <= 0:
        if r.get("layer_pass_failed"):
            return "layer-pass-failed"
        # MEASURED 2026-08-12, campaign hull 5: `why: mesh-build-failed` with
        # `cells: -1`, `max_skewness: -1.0` -- yet `runner_exit: 0`,
        # `solve_attempted: true`, `solve_reached: 2000.0` of a 2000-iteration
        # LTS run in 1108.6 s, `crashed: false`, `fatal: false` and a healthy
        # `min_flow_time_scale` of 1.05e-05. A mesh that failed to BUILD cannot
        # then be solved on for 2000 iterations.
        #
        # run-case.sh's checkMesh bar is FATAL, so interFoam starting at all is
        # proof the mesh was built AND cleared that bar. What failed here is the
        # PARSE of the checkMesh receipt, not the mesh -- and blaming the mesh
        # sends the next session to snappy for a problem in a grep.
        #
        # This does NOT promote hull 5 to `ok`: `meshed` still requires
        # `cells > 0`, so the rate is unchanged and the mesh stays unverified.
        # Note `zero_volume_cells` and `wrong_oriented` read 0 on this row while
        # `cells`/`non_ortho_max`/`max_skewness` read -1: some fields default to
        # a PASSING zero when unparsed, which is defect class 1 and is why the
        # honest label here is "unparsed" rather than either verdict.
        if (r.get("runner_exit") == 0 and r.get("solve_attempted")
                and r.get("solve_steps", 0) > 0):
            return "checkmesh-unparsed"
        # checkMesh never ran: snappy or the layer pass died first.
        return "mesh-build-failed"
    if r.get("zero_volume_cells", 0) > 0:
        return "checkmesh-zero-volume"
    if r.get("wrong_oriented", 0) > 5:
        return "checkmesh-wrong-oriented"
    sk = r.get("max_skewness", -1.0)
    if sk < 0:
        return "checkmesh-unparsed"         # unmeasurable is a failure, not a 0
    if sk > 20.0:
        return "checkmesh-skewness"
    if not r.get("solve_requested"):
        # Mesh-only run: the mesh passed every bar and no solve was asked for.
        # This used to fall through to "mesh-refused-unclassified", which named
        # a REFUSAL for a mesh that was accepted — a verdict string saying the
        # opposite of what happened, on the cheap half of the campaign.
        return "meshed-no-solve-requested"
    if not r.get("solve_attempted"):
        # A solve WAS asked for and interFoam never started: run-case.sh
        # refused between checkMesh and setFields (e.g. the layer pass, or
        # setFields itself). Not a mesh-quality refusal — those returned above.
        return "runner-refused-before-solver"
    if r.get("solves"):
        return "ok"
    if r.get("solve_steps", 0) == 0:
        return "solver-died-on-startup"
    if r.get("crashed") or r.get("fatal"):
        # An FPE in the GAMG p_rgh solve with the time scale collapsing is the
        # documented pathological-cell signature; anything else that raised a
        # signal is still a divergence, not a short run.
        return "solver-diverged"
    if 0 <= r.get("min_deltaT", -1.0) < 1e-12:
        return "solver-deltaT-collapse"     # pathological cell, per CLAUDE.md
    # LTS HAS NO deltaT, SO THE GUARD ABOVE COULD NEVER FIRE ON AN LTS RUN.
    # MEASURED 2026-08-11: hull 19 was labelled `solver-stopped-short` -- which
    # reads like a timeout -- while it had DIVERGED. Its force history is
    # unambiguous: steady at ~2.7e3 N through iteration 410, then 5.0e7 ->
    # 3.4e16 -> 8.9e20 -> 4.3e28, ending at 3.7e71 N with cumulative continuity
    # error -5.9e26. The blow-up began ~560 iterations before the process was
    # signalled, so the SIGTERM did not cause it.
    #
    # Under LTS `parse_forces` records min_flow_time_scale and NOTHING READ IT.
    # `min_deltaT` is -1.0 on every LTS run, and -1.0 fails the `0 <=` test, so
    # the deltaT guard is dead code there. That is this repo's defect class 1 --
    # an unmeasurable value scored as a benign one -- and it mislabelled TWO
    # divergences (campaign hull 2 and hull 19) as short runs.
    #
    # The local flow time scale IS the LTS analogue of deltaT: a pathological
    # cell degrades its own local step instead of killing the run. MEASURED
    # across four solves it is monotone in mesh skewness over 35 orders of
    # magnitude -- skew 2.87 -> 2.12e-05, 14.26 -> 2.11e-12, 17.57 -> 2.48e-40 --
    # and the two that solved sit at 1e-05 while the divergence sits at 1e-40.
    # The bar is 1e-20: far below any solved run, far above the diverged one,
    # and NOT interpolated between them.
    fts = r.get("min_flow_time_scale", -1.0)
    if 0 <= fts < 1e-20:
        return "solver-lts-time-scale-collapse"
    return "solver-stopped-short"


def _trim(case: Path) -> None:
    """Drop the bulky mesh/field data, KEEP every log and case.info.

    A campaign of 25 hulls at ~600k cells each is ~40 GB of `processor*` and
    `constant/polyMesh` if nothing is dropped, on a machine whose `runs/` was
    cut from 3.6 GB to 652 MB the same week. The logs are what the taxonomy is
    computed from and they are kilobytes — deleting the whole case (what this
    script used to do on success) destroys the evidence for the number it just
    printed, which is docs/LESSONS.md defect class 5 committed in advance.
    """
    for sub in ("constant/polyMesh", "constant/extendedFeatureEdgeMesh"):
        shutil.rmtree(case / sub, ignore_errors=True)
    for d in case.glob("processor*"):
        shutil.rmtree(d, ignore_errors=True)
    # The eMesh cache is regenerable; hull.stl is the GEOMETRY THAT FAILED and
    # it is the one artefact a later session cannot reconstruct from the logs.
    # (It is reconstructible from (seed, index) through sample_valid, which is
    # why this is cheap insurance rather than a correctness requirement.)
    for d in case.glob("constant/triSurface/*.eMesh"):
        d.unlink(missing_ok=True)
    for d in case.iterdir():
        if d.is_dir() and d.name not in ("0", "0.orig", "system", "constant",
                                         "postProcessing"):
            try:
                float(d.name)
            except ValueError:
                continue
            shutil.rmtree(d, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=2.57)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None, help="where cases go (temp if unset)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the meshes too (default keeps logs + case.info "
                         "and drops processor*/polyMesh/time dirs)")
    ap.add_argument("--json", default=None, help="write the full record here")
    ap.add_argument("--solve", type=float, default=0.0,
                    help="also SOLVE each case and report the rate that "
                         "actually RUNS (the gate's real bar). The value is an "
                         "endTime in seconds for a transient case; for the LTS "
                         "default the generator substitutes its own iteration "
                         "budget and this number is INERT — see --transient.")
    ap.add_argument("--transient", action="store_true",
                    help="solve in real time instead of LTS. LTS is what the "
                         "generator picks for a fixed hull and it is ~30x "
                         "cheaper, but 'time' there is a pseudo-iteration "
                         "count, so --solve 2 does NOT mean 2 seconds.")
    ap.add_argument("--np", type=int, default=1, dest="np_procs",
                    help="ranks for interFoam. np=10 is the MEASURED optimum "
                         "on the Mac simulation node (np=5 -> 212.7 s, np=10 "
                         "-> 127.2 s, np=15 -> 153.1 s on the same slice); "
                         "meshing is serial either way. The default of 1 is "
                         "what this harness silently used for its whole life.")
    ap.add_argument("--cap-layers", type=int, default=0, dest="cap_layers",
                    help="cap the DERIVED prism-layer count at N (n = min("
                         "derived, N)). ONE VARIABLE, for a controlled arm: "
                         "same seed, same geometry, same refinement, only the "
                         "requested layer count moves. 0 = no cap, the shipped "
                         "derivation.")
    ap.add_argument("--layer-backoff", type=int, default=0, dest="layer_backoff",
                    help="on a checkMesh REFUSAL, re-generate with a lower "
                         "prism-layer count and re-mesh, up to this many extra "
                         "attempts (see navalai.cfd.case.layer_backoff_ladder). "
                         "DEFAULT 0 = the pipeline as it ships, which is what "
                         "the ledger watermark must be measured against. A "
                         "mesh costs ~80 s, so each rung is cheap; a SOLVE is "
                         "~28 min, so a rung that avoids a wasted solve is "
                         "free.")
    ap.add_argument("--timeout", type=float, default=3600.0,
                    help="wall-clock ceiling per hull [s]; a hull that hits it "
                         "is recorded as 'timeout', not as a pass")
    ap.add_argument("--reclassify", action="store_true",
                    help="run NOTHING: re-parse the logs already in --out and "
                         "rewrite --json. Exists because the taxonomy is a "
                         "READING of the logs, not a measurement separate from "
                         "them — when a mechanism turns out to be misnamed "
                         "(campaign hull 2's FPE was reported as "
                         "'solver-stopped-short', which reads like a timeout), "
                         "the fix must be re-derivable from the evidence "
                         "instead of re-run for hours or hand-edited into the "
                         "record.")
    ap.add_argument("--resume", action="store_true",
                    help="keep an existing --out tree and skip hulls already "
                         "recorded in --json. This Mac thermal-sleeps under "
                         "sustained load, so a campaign that cannot be resumed "
                         "is a campaign that may never produce a number.")
    args = ap.parse_args()

    root = Path(args.out) if args.out else Path("/tmp/mesh_robustness")
    done: dict[int, dict] = {}
    if args.resume and args.json and Path(args.json).exists():
        prev = json.loads(Path(args.json).read_text())
        done = {r["hull"]: r for r in prev.get("rows", [])}
        print(f"resuming: {len(done)} hull(s) already recorded in {args.json}")
    elif not args.resume and not args.reclassify:
        # --reclassify MUST NOT WIPE THE TREE IT IS ABOUT TO READ.
        # MEASURED 2026-08-11, and it cost a finished campaign: `--reclassify`
        # went down this branch (it is not `--resume`), `shutil.rmtree` deleted
        # all 25 case directories, the reparse then found nothing, and the run
        # wrote `{"n": 0, "rows": []}` OVER the 19/25 record it was invoked to
        # correct. A read-only mode that begins by deleting its input is not a
        # read-only mode, and the empty result it produced was written out as
        # if it were a measurement — LESSONS defect class 1 twice in one
        # command. The refusal below is the second half of the fix.
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    mission = MissionSpec()
    X, _ = sample_valid(args.n, mission, seed=args.seed)
    regime = "transient" if args.transient else "LTS (pseudo-steady)"
    print(f"meshing {len(X)} valid hulls at scale {args.scale} "
          f"(plan bar: >=95% of 200)")
    print(f"solve: {'yes, ' + regime if args.solve else 'no'}, "
          f"np={args.np_procs}, timeout {args.timeout:g} s/hull\n")
    print(f"{'#':>3} {'cells':>9} {'layer%':>7} {'zeroVol':>8} {'skew':>8} "
          f"{'sec':>6}  verdict")
    print("-" * 78)

    rows = []
    for i, x in enumerate(X):
        case = root / f"h{i:03d}"
        if args.reclassify:
            if not (case / "log.checkMesh").exists() and \
                    not (case / "log.snappy").exists():
                continue
            r = mesh_one(case, mesh_only=True, timeout=0, parse_only=True)
            r["solve_attempted"] = (case / "log.interFoam").exists()
            if args.solve:
                r.update(solve_one(case))
            r["hull"] = i
            r["solve_requested"] = bool(args.solve)
            r["lwl"] = round(float(Hull(x).x[-1]), 3)
            r["why"] = classify(r)
            rows.append(r)
            print(f"{i:3d} {r['cells']:9d} {r['layer_pct']:7.1f} "
                  f"{r['zero_volume_cells']:8d} {r['max_skewness']:8.2f} "
                  f"{r['seconds']:6.1f}  {'ok' if r['meshed'] else 'FAILED'}"
                  f"  [{r['why']}]")
            continue
        if i in done:
            rows.append(done[i])
            continue
        try:
            # THE LAYER-COUNT LADDER. rung 0 is the DERIVED count, i.e. exactly
            # what the pipeline does today; --layer-backoff adds the rungs
            # below it. Default 0 rungs, so the as-shipped rate stays
            # measurable and the two configurations are never confused.
            spec = layer_spec(float(Hull(x).x[-1]), args.speed, args.scale)
            # rung 0 is the DERIVED count, or the cap if --cap-layers asked for
            # one. `None` means "let the generator derive it", which is the
            # shipped behaviour and must stay reachable so the control arm is
            # the real thing rather than a re-derivation of it.
            rung0 = (min(spec["n_layers"], args.cap_layers)
                     if args.cap_layers else None)
            # CEILING = the UNCLAMPED bridging count. The ladder searches
            # BOTH directions now (it descended only, and could not reach the
            # n=8 / n=6 / n=10 that hulls 10, 12 and 18 respectively need), so
            # it needs an upper bound as well as the floor. n_ideal is that
            # bound: above it the near-wall cell cannot support the stack.
            rungs = [rung0] + layer_backoff_ladder(
                rung0 or spec["n_layers"],
                ceiling=spec.get("n_ideal") or spec["n_layers"],
            )[:args.layer_backoff]
            for attempt, n_lay in enumerate(rungs):
                # WIPE THE PREVIOUS RUNG'S LOGS. run-case.sh truncates the
                # ones it writes, but a rung that dies EARLIER than the last
                # one leaves the earlier rung's log.checkMesh in place, and
                # mesh_one would then grade this mesh from the previous mesh's
                # receipt — a receipt outliving the mesh that produced it, the
                # incident that made run-case.sh rewrite case.info instead of
                # appending to it.
                for stale in case.glob("log.*"):
                    stale.unlink(missing_ok=True)
                # AND THE DECOMPOSITION, OR THE RUNNER RESUMES INSTEAD OF
                # MEASURING. run-case.sh takes its resume branch whenever
                # `processor0/` and a polyMesh exist, and that branch runs
                # interFoam and exits BEFORE checkMesh — by design, because it
                # exists for this Mac's thermal sleeps. MEASURED 2026-08-11 on
                # campaign hull 5: an interrupted attempt left a checkpoint, the
                # rerun resumed it, and the hull SOLVED to 2000/2000 while its
                # mesh metrics came back unmeasurable (cells -1, skew -1) and
                # the verdict printed `mesh-build-failed` next to `RUNS`. Two
                # contradictory answers about one hull, and the mesh half of the
                # gate silently uncounted.
                #
                # Gate 2U measures mesh-AND-converge FROM SCRATCH, so the unit
                # of resumption is the HULL (the --json record), not the
                # timestep. A nap now costs one hull, which is the trade that
                # keeps the two halves of the verdict about the same mesh.
                for proc in case.glob("processor*"):
                    shutil.rmtree(proc, ignore_errors=True)
                write_resistance_case(Hull(x), args.speed, case,
                                      end_time=args.solve or 1.0,
                                      scale=args.scale, np_procs=args.np_procs,
                                      lts=False if args.transient else None,
                                      n_layers=n_lay)
                r = mesh_one(case, np_procs=args.np_procs,
                             mesh_only=not args.solve, timeout=args.timeout)
                r["layer_attempts"] = attempt + 1
                r["n_layers_used"] = n_lay if n_lay else spec["n_layers"]
                r["n_layers_derived"] = spec["n_layers"]
                # Back off only on a MESH refusal. A mesh that passed the bars
                # and then failed in the SOLVER is a different defect and
                # re-meshing it with fewer layers would be answering a question
                # nobody asked — and would hide it behind a retry.
                if (r["zero_volume_cells"] == 0 and r["wrong_oriented"] <= 5
                        and 0 <= r["max_skewness"] <= 20.0 and r["cells"] > 0):
                    break
            r["layer_pass_failed"] = (case / "log.snappy.layers").exists() and \
                not (case / "log.checkMesh").exists()
            if args.solve:
                # The runner refuses to solve a mesh that failed its own bars
                # (0 zero-volume / <=5 wrongly-oriented / skew <=20) and exits
                # 1 before setFields. That refusal IS a Gate 2U failure, and it
                # must not be reported as a solver crash: `solve_attempted`
                # separates "the solver was never reached" from "the solver was
                # reached and died", which are different repairs.
                r["solve_attempted"] = (case / "log.interFoam").exists()
                r.update(solve_one(case))
        except Exception as exc:                       # generation itself failed
            r = {"cells": -1, "zero_volume_cells": -1, "layer_pct": -1.0,
                 "max_skewness": -1.0, "seconds": 0.0, "meshed": False,
                 "error": repr(exc)[:200]}
        r["hull"] = i
        r["solve_requested"] = bool(args.solve)
        r["lwl"] = round(float(Hull(x).x[-1]), 3)
        r["why"] = classify(r)
        rows.append(r)
        print(f"{i:3d} {r['cells']:9d} {r['layer_pct']:7.1f} "
              f"{r['zero_volume_cells']:8d} {r['max_skewness']:8.2f} "
              f"{r['seconds']:6.1f}  {'ok' if r['meshed'] else 'FAILED'}"
              + (f"  {'RUNS' if r.get('solves') else 'no-run'}"
                 f" (t={r.get('solve_reached', 0):.4g}/"
                 f"{r.get('solve_end_time', 0):.4g})" if args.solve else "")
              + f"  [{r['why']}]", flush=True)
        if not args.keep:
            _trim(case)
        # THE RECORD IS WRITTEN AFTER EVERY HULL, NOT AT THE END. A campaign
        # that only writes its JSON on the last line loses everything to the
        # 'Thermal Emergency Sleep' this machine is documented to take under
        # sustained load — and losing hull 23 of 25 costs the whole run.
        if args.json:
            _write_json(args, rows)

    ok = sum(1 for r in rows if r["meshed"])
    rate = 100.0 * ok / max(len(rows), 1)
    if args.solve:
        sok = sum(1 for r in rows if r.get("solves"))
        srate = 100.0 * sok / max(len(rows), 1)
        print(f"SOLVES ({regime}): {sok}/{len(rows)} = {srate:.1f}%  "
              f"(the gate's real bar)")
        print(f"clean-checkMesh proxy:   {ok}/{len(rows)} = {rate:.1f}%  "
              f"(reported for continuity with the earlier 75% figure)")
    print("-" * 78)
    print(f"meshed unattended: {ok}/{len(rows)} = {rate:.1f}%   "
          f"(plan bar >=95% on 200 hulls; this is N={len(rows)})")
    # THE TAXONOMY, NOT JUST THE PERCENTAGE. A rate says how bad; the grouping
    # says what to fix, and it is the half that survives the next pipeline
    # change.
    tax: dict[str, list] = {}
    for r in rows:
        tax.setdefault(r.get("why", "?"), []).append(r["hull"])
    print("\nfailure taxonomy (hull ids):")
    for why in sorted(tax, key=lambda k: (-len(tax[k]), k)):
        print(f"  {len(tax[why]):3d}  {why:<28} {tax[why]}")
    if rate < 95.0:
        print("BELOW THE BAR — recorded, not softened. "
              "See PLM.md roadmap: unattended-meshing robustness.")
    if args.reclassify and not rows:
        # AN EMPTY REPARSE IS A FAILURE TO MEASURE, NOT A MEASUREMENT OF ZERO.
        # This is the half that turned a deleted tree into a WRITTEN record:
        # the reparse found no logs and `{"n": 0, "success_pct": 0.0}` went to
        # disk over a finished 19/25 campaign. `success_pct` of a zero-hull
        # batch is not 0%, it is undefined, and writing it out is the
        # `${_MQ_SKEW:-0}` defect with a JSON file instead of an awk default.
        print(f"REFUSING to write {args.json}: --reclassify found no parsable "
              f"logs under {root}. That is 'I could not measure this', which "
              f"is not the same as 'the rate is 0%' — and the existing record "
              f"is left untouched rather than overwritten with a zero.")
        return 2
    if args.json:
        _write_json(args, rows)
        print(f"wrote {args.json}")
    return 0


def _write_json(args, rows) -> None:
    ok = sum(1 for r in rows if r["meshed"])
    sok = sum(1 for r in rows if r.get("solves"))
    tax: dict[str, int] = {}
    for r in rows:
        tax[r.get("why", "?")] = tax.get(r.get("why", "?"), 0) + 1
    Path(args.json).write_text(json.dumps(
        {"n": len(rows), "scale": args.scale, "speed": args.speed,
         "seed": args.seed, "np": args.np_procs,
         "regime": "transient" if args.transient else "LTS",
         "solve_requested": args.solve,
         "success_pct": 100.0 * ok / max(len(rows), 1),
         "solve_pct": (100.0 * sok / max(len(rows), 1)) if args.solve else None,
         "bar_pct": 95.0, "taxonomy": tax, "rows": rows}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
