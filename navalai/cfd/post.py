"""OpenFOAM forces post-processing + grid-convergence (GCI) — testable
WITHOUT OpenFOAM (synthetic force files in tests; real files on the metal).

Research grounding: 'the uncertainty number you report depends materially on
which V&V method you implement' (Islam & Guedes Soares 2019) — so the method
is named in the output: Roache GCI, factor-of-safety 1.25, Richardson p.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_NUM = re.compile(r"[-+0-9.eE]+")


def parse_forces(path: str | Path):
    """Parse an OpenFOAM force.dat: rows 'time (fx fy fz) (fx fy fz) ...'.

    Returns (t, fx_total) with pressure+viscous x-components summed.
    """
    t, fx = [], []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        nums = [float(x) for x in _NUM.findall(line)]
        if len(nums) < 7:
            continue
        t.append(nums[0])
        # Column layout, from the file's own header:
        #   Time | total_x total_y total_z | pressure_x .. | viscous_x ..
        # so the drag is column 1. This previously read `nums[1] + nums[4]`,
        # i.e. total_x + pressure_x — DOUBLE-COUNTING the pressure term, while
        # the comment claimed "pressure-x + viscous-x". It inflated every drag
        # this project has reported: KCS C_t read 9.33e-3 against OpenFOAM's own
        # forceCoeffs value of 4.26e-3, and the own-hull triplet was wrong by
        # the same mechanism. Cross-check any change here against forceCoeffs.
        fx.append(nums[1])
    return np.array(t), np.array(fx)


def parse_forces_components(path: str | Path):
    """(t, pressure_x, viscous_x) — the split the total hides.

    Kept separate from parse_forces so the components are read from their OWN
    columns (4 and 7) rather than inferred, which is how they got confused in
    the first place.
    """
    t, fp, fv = [], [], []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        nums = [float(x) for x in _NUM.findall(s)]
        if len(nums) < 10:
            continue
        t.append(nums[0])
        fp.append(nums[4])
        fv.append(nums[7])
    return np.array(t), np.array(fp), np.array(fv)


def forces_path(case: str | Path) -> Path:
    """Force history for a case, merging every RESTART artefact into one file.

    OpenFOAM produces restart fragments in TWO different ways, and missing
    either one reports a fragment as the whole run:

    1. A run resumed at a later time writes a fresh
       postProcessing/forces/<restart-time>/force.dat.
    2. A run restarted at the SAME start time does NOT overwrite force.dat —
       it writes force_0.dat, then force_1.dat, beside it.

    (2) bit us on KCS: force.dat held 18 lines from a run that had DIVERGED
    (t=0.44542 repeated with forces escalating 1e11 -> 1e18 -> 1e24) while the
    live 266-line run sat in force_0.dat next to it, and forces_path returned
    the corpse. Both are collected here; where two files cover the same time,
    the later-written one wins, because that is the run that superseded it.
    """
    root = Path(case) / "postProcessing" / "forces"
    segs = sorted(root.glob("*/force*.dat"),
                  key=lambda p: (float(p.parent.name), _restart_index(p)))
    segs = [s for s in segs if s.name != "force.merged.dat"]
    if not segs:
        raise FileNotFoundError(f"no force*.dat under {root}")
    if len(segs) == 1:
        return segs[0]

    rows: dict[float, str] = {}
    for seg in segs:
        seg_rows: dict[float, str] = {}
        for line in seg.read_text().splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                seg_rows[float(_NUM.findall(s)[0])] = s
            except (IndexError, ValueError):
                continue
        if not seg_rows:
            continue
        # RESTART SEMANTICS: a run that starts at t0 invalidates everything
        # from t0 onward — those samples belong to an attempt that was
        # superseded. Merging by per-sample overwrite is not enough: the dead
        # KCS run had diverged at t=0.44542 (1e24 N) and the live re-run never
        # sampled that exact instant, so the garbage survived the merge and sat
        # in the record as the largest force in the history.
        t0 = min(seg_rows)
        rows = {t: r for t, r in rows.items() if t < t0}
        rows.update(seg_rows)
    merged = root / "force.merged.dat"
    merged.write_text("\n".join(rows[t] for t in sorted(rows)) + "\n")
    return merged


def _restart_index(p: Path) -> int:
    """Order force.dat < force_0.dat < force_1.dat ... by write order."""
    stem = p.stem
    if "_" not in stem:
        return -1
    try:
        return int(stem.rsplit("_", 1)[1])
    except ValueError:
        return -1


def mean_resistance(path: str | Path, tail_frac: float = 0.3) -> tuple[float, float]:
    """(mean, std) of drag over the final tail_frac of the run (settled).

    A raw sample mean over a file. It is NOT the settledness rule — that is
    `settled_drag`, which time-averages, tests the COMPONENTS and reports why.
    Kept because the low-level parse/average is worth testing on its own.
    """
    t, fx = parse_forces(path)
    if len(t) < 10:
        raise ValueError("force history too short")
    cut = t[0] + (1.0 - tail_frac) * (t[-1] - t[0])
    seg = fx[t >= cut]
    return float(np.mean(seg)), float(np.std(seg))


# ===========================================================================
# ONE settledness rule, ONE cell count, ONE symmetric doubling.
#
# scripts/post_gci.py and scripts/gate2m.py were two independent
# post-processors over the same files, and they DISAGREED on all three. All of
# the following was MEASURED on the recorded runs on 2026-08-06, before any of
# it moved here:
#
#   * CELL COUNT.  post_gci read checkMesh's `cells:` and FELL BACK to
#     case.info's `cells_bg=`; gate2m read `cells_bg` only. Those are different
#     quantities — the meshed count and the background block spec — and on
#     these runs they differ by ~16x (beach: 222444 vs 13608). `post_gci.py
#     runs/kcs_gci2` mixed one of each inside a single ratio and printed
#         cells 243354 / 38000 / 108864
#         measured refinement ratio 0.538 (c->m), 1.420 (m->f)
#     i.e. a grid that gets COARSER under refinement, from a family generated
#     at sqrt(2). gate2m, on the same directory, got 1.410 / 1.418.
#   * SETTLEDNESS.  post_gci split the last 30% in half; gate2m compared the
#     last fifth to the previous fifth BY SAMPLE INDEX. On runs/kcs_gci2/coarse
#     that is 2.1% drift (post_gci: settled) against 10.9% (gate2m: NOT
#     settled) — same file, same instant, two verdicts.
#   * DOUBLING.  gate2m doubled a symmetric case's force; post_gci acquired the
#     same rule later and independently.
#
# The rules below are the ones that survived, and each is CHOSEN, with the
# measurement that chose it recorded next to it.
# ===========================================================================

# The settled window is the LAST FIFTH of the record, and drift is measured
# against the fifth before it. That is gate2m's definition — the one that
# prints the Gate 2M verdict and the one `navalai.pipeline.check_cfd`
# documents — so it wins over post_gci's tail/2 split. It is applied BY TIME
# here, not by sample index: dt is adaptive, so an index window over-weights
# exactly the instants where the solver was struggling. MEASURED on runs/beach,
# where the two disagree materially: 3.34% drift by index, 5.77% by time.
TAIL_FRAC = 0.2

# Drift above which a force history has not settled. MIRRORED as SETTLE_TOL in
# scripts/gate2m.py because navalai/pipeline.py reads that literal out of that
# file by regex; tests/test_settled_drag.py fences the two together.
DRIFT_TOL = 0.05

# Batches the settled window is split into for the standard error of its mean.
# This is the drift test's own fifth-split, generalised from 2 windows to 5 —
# see `settled_drag` for the measurement that made 2 insufficient.
N_BATCHES = 5

# A domain the free stream has not yet crossed still contains its initial
# condition, so no average over it can be stationary. Physics, not a tuned
# constant. The TARGET for a KCS resistance number is 5.0 (75 s); anything
# between is reported as under-run.
FLOW_THROUGH_FLOOR = 1.0
FLOW_THROUGH_TARGET = 5.0

# Two refinement steps that differ by more than this are not one family, and
# Richardson extrapolation does not apply to them. Both scripts had this check
# with this number; it now has one home.
FAMILY_SPREAD_TOL_PCT = 5.0

# Samples required in the settled window. Drift compares two window means and
# the batch error splits one of them five ways; below this there is no
# statistic, only noise. runs/val_coarse holds FOUR samples (a solve that
# diverged at t=0.0072) and must never produce a mean.
MIN_WINDOW_SAMPLES = 20


class ForceHistoryError(ValueError):
    """This case cannot yield a drag number, and says why.

    A dedicated type so a caller can tell "no data" from "unusable data"
    without a broad `except ValueError` swallowing a file-read failure as
    well — the same lesson `WaterplaneError` records.
    """


class CellCountError(ValueError):
    """The mesh size could not be MEASURED for this case.

    Never substitute another quantity for it. `${VAR:-0}` has already cost this
    project a run, and the cells_bg fallback above cost it a refinement ratio
    of 0.538.
    """


def read_case_info(case: str | Path) -> dict:
    """`case.info` as a dict. One parser; there were three.

    Only `key=value` lines with a bare identifier key are receipts. That rule
    drops the prose lines (`Gate 2M = KCS/JBC resistance ...` has a SPACE in
    its key) without a per-prefix blacklist that has to be kept in step with
    whatever the generator writes next.
    """
    out: dict = {}
    p = Path(case) / "case.info"
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k.isidentifier():
            out[k] = v.strip()
    return out


def is_symmetric(case: str | Path) -> bool:
    """True when case.info records a half domain. A missing receipt is FULL.

    THE ONE PLACE THIS IS DECIDED. A symmetric case meshes half the hull, so
    its patch integral is half the force — "the single easiest way to be
    exactly 2x wrong and never notice", and post_gci.py was exactly 2x wrong
    for as long as it had no symmetric handling at all.
    """
    return read_case_info(case).get("symmetric", "False").strip().lower() == "true"


def cell_count(case: str | Path) -> int:
    """Cells in the mesh that was SOLVED, from checkMesh. No fallback.

    checkMesh runs last in run-case.sh — after castellation, snapping, the
    z-only refineMesh rounds and the layer pass — so its `cells:` is the mesh
    the solver saw. `cells_bg` in case.info is the background block SPEC, ~16x
    smaller, and the two are not interchangeable: post_gci.py mixed them inside
    one refinement ratio and reported 0.538 for a sqrt(2) family (see the block
    comment above). An unmeasurable count raises; it never defaults.
    """
    log = Path(case) / "log.checkMesh"
    if log.exists():
        for line in log.read_text().splitlines():
            if line.strip().startswith("cells:"):
                try:
                    return int(line.split()[-1])
                except ValueError:
                    break
    raise CellCountError(
        f"no checkMesh cell count under {case}. The mesh size is MEASURED from "
        f"log.checkMesh, never taken from case.info's cells_bg — that is the "
        f"background block spec, not the mesh, and substituting it produced a "
        f"refinement ratio of 0.538 on a sqrt(2) family.")


def _time_average(t: np.ndarray, y: np.ndarray) -> float:
    """Trapezoidal time-average. dt is adaptive; a sample mean is not one."""
    if len(t) < 2:
        return float(np.mean(y))
    return float(np.trapezoid(y, t) / (t[-1] - t[0]))


def _batch_error(t: np.ndarray, y: np.ndarray) -> float:
    """Standard error of the window mean by BATCH MEANS (N_BATCHES batches).

    Why not the drift test alone: drift compares TWO adjacent windows, so an
    oscillation whose period is close to the window length puts both windows at
    the same phase and cancels itself out of the comparison. That is not a
    hypothetical.

    MEASURED on runs/val_coarse5 (1.33 flow-throughs) at a 0.40 tail: drift on
    the TOTAL is 0.3% and the worst component drift is 2.9% — inside the 5% bar
    on every component — while the batch error of the pressure component is
    17.5%. On runs/beach at a 0.25 tail: worst drift 1.2%, batch error 5.5%.
    Both are runs this repository has drawn conclusions from.

    That oscillation is not noise and its period is now known independently:
    a tank mode at **5.53 s**, measured from the free surface rather than the
    forces (docs/research/CFD.md section 1). val_coarse5's settled window is
    3.94 s — SHORTER THAN ONE CYCLE — so its mean is a phase sample whatever
    the drift between two such windows happens to say. The batch error is what
    reports that, and it needs no period estimator to do it: batch means of a
    window that cannot average one cycle simply do not agree.

    Equal-TIME batches; NaN if any batch is too thin to average, which is a
    refusal upstream, never a pass.
    """
    edges = np.linspace(t[0], t[-1], N_BATCHES + 1)
    means = []
    for i in range(N_BATCHES):
        m = (t >= edges[i]) & (t <= edges[i + 1])
        if int(m.sum()) < 2:
            return float("nan")
        means.append(_time_average(t[m], y[m]))
    return float(np.std(means, ddof=1) / math.sqrt(N_BATCHES))


def settled_drag(case: str | Path, *, drift_tol: float = DRIFT_TOL,
                 tail_frac: float = TAIL_FRAC) -> dict:
    """The settled drag of ONE case, and whether it is settled at all.

    THE single home for: reading the force history, choosing the averaging
    window, doubling a symmetric case, and deciding stationarity. Both
    scripts/post_gci.py and scripts/gate2m.py call it and neither may re-derive
    any of it.

    Stationarity is THREE conditions, and all must hold:

      1. `flow_throughs >= FLOW_THROUGH_FLOOR`. A domain the free stream has
         not crossed still holds its initial condition. MEASURED on runs/beach
         at 0.70: 3.3% drift on the total, and the gate printed a C_T.
      2. `drift <= drift_tol` on the TOTAL **and on the PRESSURE and VISCOUS
         components separately**. The drift test used to be applied to the
         total only, and the total is dominated by the viscous part, which is
         the stable one — so the component that is actually wrong was free to
         move underneath a passing number. MEASURED on runs/lts: total drift
         4.5% (the old rule: SETTLED, and the gate reported C_T = 1.1995e-02
         from it) against 7.5% on the pressure component.
      3. `batch error <= drift_tol` on each component — the guard against an
         oscillation that aliases with the two-window drift comparison. See
         `_batch_error` for the two recorded runs where it, and only it, fires.

    Returns a dict; `settled` is the verdict, `reasons` says what failed and
    `method` names the rule so the reader never has to infer it. Values in
    newtons are the FULL hull (doubled for a symmetric case). Signs are as
    OpenFOAM writes them — a hull towed toward -x has a negative x-force — so
    resistance is `abs(drag_n)`.

    Raises ForceHistoryError when there is no usable history at all. That is a
    refusal, not a zero.
    """
    case = Path(case)
    try:
        fpath = forces_path(case)
    except FileNotFoundError as exc:
        raise ForceHistoryError(str(exc)) from exc

    t, fx = parse_forces(fpath)
    tc, fp, fv = parse_forces_components(fpath)
    if len(t) < 2:
        raise ForceHistoryError(
            f"{fpath} holds {len(t)} usable row(s); there is no history here")
    if len(tc) != len(t):
        raise ForceHistoryError(
            f"{fpath} has {len(t)} total rows but {len(tc)} with a "
            f"pressure/viscous split. The components are what the settledness "
            f"rule tests, so a file without them cannot be judged.")

    span = float(t[-1] - t[0])
    if span <= 0:
        raise ForceHistoryError(f"{fpath} spans no time (t[0] == t[-1])")
    cut = t[-1] - tail_frac * span
    prev_cut = t[-1] - 2.0 * tail_frac * span
    prev2_cut = t[-1] - 3.0 * tail_frac * span
    win = t >= cut
    prev = (t >= prev_cut) & (t < cut)
    # The third-from-last window exists ONLY for the convergence trend of an
    # under-settled run (see `outcome` below); it never moves the settled
    # verdict and it may legitimately be too thin to measure.
    prev2 = (t >= prev2_cut) & (t < prev_cut)
    n_win, n_prev = int(win.sum()), int(prev.sum())
    if n_win < MIN_WINDOW_SAMPLES or n_prev < MIN_WINDOW_SAMPLES:
        raise ForceHistoryError(
            f"{case.name}: the settled window holds {n_win} samples and the "
            f"one before it {n_prev}; {MIN_WINDOW_SAMPLES} are required in "
            f"each. A drift between two means of a handful of samples is "
            f"noise, not a stationarity test. (runs/val_coarse holds 4 samples "
            f"in total, from a solve that diverged at t=0.0072.)")

    parts = {"total": fx, "pressure": fp, "viscous": fv}
    for name, arr in parts.items():
        seg = arr[win]
        if not np.isfinite(seg).all():
            raise ForceHistoryError(
                f"{case.name}: the {name} force is not finite over the settled "
                f"window. A diverged solve is not a small number, and it must "
                f"never be averaged into one.")

    tw = t[win]
    window_s = float(tw[-1] - tw[0])
    factor = 2.0 if is_symmetric(case) else 1.0
    total_avg = factor * _time_average(tw, fx[win])
    ref = max(abs(total_avg), 1e-12)

    means, drifts, errors = {}, {}, {}
    for name, arr in parts.items():
        means[name] = factor * _time_average(tw, arr[win])
        drifts[name] = abs(means[name]
                           - factor * _time_average(t[prev], arr[prev])) / ref
        errors[name] = factor * _batch_error(tw, arr[win]) / ref
    # Drift one step EARLIER (prev vs prev2), for the trend. NaN when the
    # record is too short to hold a third window — unmeasured, never zero.
    if int(prev2.sum()) >= MIN_WINDOW_SAMPLES:
        prev_drift = max(
            abs(factor * _time_average(t[prev], arr[prev])
                - factor * _time_average(t[prev2], arr[prev2])) / ref
            for arr in parts.values())
    else:
        prev_drift = float("nan")

    info = read_case_info(case)
    try:
        lwl = float(info["lwl"])
        speed = float(info["speed_ms"])
    except (KeyError, ValueError) as exc:
        raise ForceHistoryError(
            f"{case.name}: case.info has no usable lwl/speed_ms, so neither "
            f"C_T nor the flow-through count can be MEASURED. Both are part of "
            f"the verdict; neither has a default.") from exc

    from .case import _DOMAIN_LENGTH_L          # one domain proportion, in case.py
    domain_assumed = "domain_length_m" not in info
    dom_len = float(info.get("domain_length_m", 0.0) or 0.0) or _DOMAIN_LENGTH_L * lwl
    # LTS PSEUDO-TIME IS NOT TIME (the Mac's 2026-08-19 honesty seam: the
    # coarse KCS printed "134.09 flow-throughs" from pseudo-iterations
    # divided by a domain length in metres — fiction wearing a unit). An
    # LTS case is detected from its own fvSchemes; its flow-through count
    # is NaN — not applicable, never a number — which by IEEE comparison
    # also disarms the flow-through floor and the under-run note, both of
    # which are statements about REAL time the free stream spent crossing.
    fvs = case / "system" / "fvSchemes"
    pseudo_time = fvs.exists() and "localEuler" in fvs.read_text()
    # A MIXED HISTORY IS NOT REAL TIME FROM t=0 (the Mac's 2026-08-19 tail
    # seam): the hybrid lane restarts an LTS spin-up as a transient tail,
    # switching fvSchemes to Euler — so the schemes say real-time while the
    # merged record's HEAD is pseudo-iterations, and t[-1]/domain prints a
    # fictional 136 flow-throughs. The tail's start is recorded in
    # case.info as `transient_tail_from=` (the hybrid runbook writes it);
    # with the receipt, flow-throughs count real seconds from THERE. A
    # mixed history WITHOUT the receipt (Euler schemes over a log that
    # still carries LTS's "Flow time scale" prints) is NaN — unmeasured,
    # never a number.
    tail_from = None
    ti = info.get("transient_tail_from")
    if ti is not None:
        try:
            tail_from = float(ti)
        except (TypeError, ValueError):
            tail_from = None
    if pseudo_time:
        flow_throughs = float("nan")
    elif tail_from is not None:
        flow_throughs = max(0.0, float(t[-1]) - tail_from) * speed / dom_len
    else:
        lg = case / "log.interFoam"
        mixed = lg.exists() and "Flow time scale min/max" in lg.read_text()
        flow_throughs = (float("nan") if mixed
                         else float(t[-1]) * speed / dom_len)

    stl = case / "constant" / "triSurface" / "hull.stl"
    if stl.exists():
        s_wetted = stl_wetted_area(stl, 0.0)
        ct = resistance_coefficient(total_avg, s_wetted, speed)
    else:
        s_wetted, ct = float("nan"), float("nan")

    try:
        cells: int | None = cell_count(case)
    except CellCountError:
        cells = None

    reasons: list[str] = []
    if flow_throughs < FLOW_THROUGH_FLOOR:
        reasons.append(
            f"{flow_throughs:.2f} of a flow-through (floor "
            f"{FLOW_THROUGH_FLOOR:.1f}) — the free stream has not crossed the "
            f"domain, so it still holds its initial condition")
    for name in parts:
        if not math.isfinite(drifts[name]) or drifts[name] > drift_tol:
            reasons.append(f"{name} drift {100*drifts[name]:.1f}% > "
                           f"{100*drift_tol:.0f}%")
    for name in parts:
        if not math.isfinite(errors[name]):
            reasons.append(
                f"{name} batch error could not be measured (a batch of the "
                f"settled window holds fewer than 2 samples)")
        elif errors[name] > drift_tol:
            reasons.append(
                f"{name} batch error {100*errors[name]:.1f}% > "
                f"{100*drift_tol:.0f}% — the window mean is not reproducible "
                f"across the window, which drift alone cannot see")

    drift = max(drifts.values())
    # THE OUTCOME TAXONOMY (2026-08-19, the one-mesh receipt-4 ruling). The
    # Mac's section-H check produced a run with EVERY solvability receipt
    # green — full budget, no FATAL, tau healthy, forces converging at
    # sd 1.2% — and drift 5.25% against the 5% bar. Calling that FAIL is the
    # h18 lesson mirrored: there a divergence hid in the timeout column;
    # here a converging-but-slow run would hide in the fail column. A budget
    # is a resource cap, not a physics verdict, so the vocabulary carries
    # three outcomes and THE BAR DOES NOT MOVE:
    #   settled        — every condition inside the bar.
    #   under-settled  — the ONLY failures are drift/batch-error AND the
    #                    drift is DECLINING window-over-window (measured
    #                    against the third-from-last window, never assumed).
    #                    The designed response is ONE counted same-size
    #                    budget extension (record settle_extensions=N in
    #                    case.info and resume); still over the bar after
    #                    the extension -> a genuine fail against the bar.
    #   unsettled      — anything else: flow-through under-run, non-finite,
    #                    unmeasurable batch, or drift that is not shrinking.
    only_drift_reasons = bool(reasons) and all(
        ("drift" in r or "batch error" in r) for r in reasons)
    converging = math.isfinite(prev_drift) and drift < prev_drift
    if not reasons:
        outcome = "settled"
    elif only_drift_reasons and converging:
        outcome = "under-settled"
    else:
        outcome = "unsettled"
    method = (
        f"time-averaged over the last {100*tail_frac:.0f}% "
        f"(t={tw[0]:.4g}..{tw[-1]:.4g} s, {n_win} samples); drift vs the "
        f"preceding window and a {N_BATCHES}-batch standard error, BOTH "
        f"applied to total/pressure/viscous, bar {100*drift_tol:.0f}%; "
        f"flow-through floor {FLOW_THROUGH_FLOOR:.1f}"
        + ("; symmetric case doubled" if factor == 2.0 else ""))

    return {
        "name": case.name, "case": str(case),
        "drag_n": total_avg, "pressure_n": means["pressure"],
        "viscous_n": means["viscous"],
        "std_n": factor * float(np.std(fx[win])),
        "drift": drift, "drift_total": drifts["total"],
        "drift_pressure": drifts["pressure"], "drift_viscous": drifts["viscous"],
        "error_total": errors["total"], "error_pressure": errors["pressure"],
        "error_viscous": errors["viscous"],
        "settled": not reasons, "reasons": tuple(reasons),
        "outcome": outcome, "prev_drift": prev_drift,
        "symmetric": factor == 2.0, "cells": cells,
        "flow_throughs": flow_throughs, "domain_assumed": domain_assumed,
        "pseudo_time": pseudo_time,
        "t_end": float(t[-1]), "window_s": window_s, "n_window": n_win,
        "ct": ct, "s_wetted_m2": s_wetted, "speed": speed, "lwl": lwl,
        "method": method,
    }


def _mser_truncate(t: np.ndarray, y: np.ndarray,
                   n_grid: int = 20) -> int:
    """MSER-class truncation index: drop the initial transient by choosing
    the cut that minimises the standard error of the REMAINING mean.

    The classic MSER statistic on a time-weighted record: for each candidate
    cut on a coarse grid, SE^2 ~ var(remaining) / n_remaining. The cut that
    minimises it marks where deleting more data stops buying stationarity.
    A minimising cut in the LAST QUARTER of the record is the estimator's
    own refusal: the record is transient-dominated and no stationary mean
    exists inside it.
    """
    n = len(t)
    best_i, best_se = 0, float("inf")
    for k in range(n_grid):
        i = int(n * k / n_grid)
        if n - i < 16:
            break
        seg = y[i:]
        se = float(np.var(seg) / max(len(seg), 1))
        if se < best_se:
            best_se, best_i = se, i
    return best_i


def estimate_settled_mean(t: np.ndarray, y: np.ndarray,
                          confidence: float = 0.95) -> dict:
    """Stationary-mean ESTIMATE with a confidence interval — the operator's
    fix #1 (2026-08-20): settledness as estimation, not waiting.

    The windowed-drift bar time-averages until a crude statistic goes
    quiet, so a broadband oscillation (the measured ~9% batch behaviour;
    the 5.53 s tank mode) must AVERAGE OUT before the bar passes — flow-
    throughs bought to shrink a variance term. A batch-means estimator
    reports mean +/- CI at stated confidence from the record it HAS:

      1. MSER-class truncation drops the initial transient (and REFUSES a
         record whose best cut sits in its last quarter — still transient);
      2. time-weighted batch means (adaptive dt: batches are equal TIME
         spans, means by trapezoid) with the batch count halved until the
         batch means' lag-1 autocorrelation is inside +-0.3 — the
         oscillation's correlation time sets the batch size, no period
         estimator needed (tank_resonance refuted a coherent single mode:
         broadband variance modelling, not harmonic subtraction);
      3. a t-interval on the surviving batches; fewer than 8 independent
         batches is a REFUSAL (the record cannot support a statistic),
         never a smaller divisor.

    Returns {mean, ci_half, rel_ci, n_batches, truncated_frac, method} or
    {refused: why}. THE BAR IS NOT MOVED by this function: the consumer
    still holds 5%, now as "the 95% CI half-width is inside 5% of the
    mean" — a strictly stronger statement than a point drift.
    """
    from scipy import stats as _stats  # scipy ships with the stack
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    if len(t) < 32:
        return {"refused": f"{len(t)} samples cannot support truncation + "
                           f"8 independent batches"}
    i0 = _mser_truncate(t, y)
    if i0 > 0.75 * len(t):
        return {"refused": "MSER truncation lands in the record's last "
                           "quarter — the signal is transient-dominated and "
                           "holds no stationary mean to estimate"}
    tt, yy = t[i0:], y[i0:]
    span = float(tt[-1] - tt[0])
    if span <= 0.0:
        return {"refused": "truncated record spans no time"}
    k = 32
    while k >= 8:
        edges = tt[0] + span * np.arange(k + 1) / k
        means = []
        for j in range(k):
            m = (tt >= edges[j]) & (tt <= edges[j + 1])
            if m.sum() < 2:
                means = None
                break
            means.append(_time_average(tt[m], yy[m]))
        if means is None:
            k //= 2
            continue
        means = np.asarray(means)
        d = means - means.mean()
        denom = float((d * d).sum())
        rho1 = (float((d[:-1] * d[1:]).sum()) / denom) if denom > 0 else 0.0
        if abs(rho1) <= 0.3:
            mean = float(means.mean())
            se = float(means.std(ddof=1) / math.sqrt(k))
            tcrit = float(_stats.t.ppf(0.5 + confidence / 2.0, k - 1))
            ci = tcrit * se
            return {"mean": mean, "ci_half": ci,
                    "rel_ci": ci / max(abs(mean), 1e-12),
                    "n_batches": k, "lag1_rho": rho1,
                    "truncated_frac": i0 / len(t),
                    "confidence": confidence,
                    "method": (f"MSER truncation ({100*i0/len(t):.0f}% "
                               f"dropped) + {k} time-weighted batch means "
                               f"(lag-1 rho {rho1:+.2f}) + t-interval at "
                               f"{100*confidence:.0f}%")}
        k //= 2
    return {"refused": "batch means stay autocorrelated (|rho1| > 0.3) down "
                       "to 8 batches — the record is shorter than the "
                       "oscillation's correlation time can support"}


def settled_estimate(case: str | Path, rel_bar: float = DRIFT_TOL,
                     confidence: float = 0.95) -> dict:
    """The ESTIMATION route to a settled drag — beside settled_drag, never
    replacing it. Same components discipline (total AND pressure AND
    viscous must each carry a CI inside the bar), same 5% number, stronger
    meaning: a 95% CI, not a point drift. Refusals are the estimator's own.
    """
    case = Path(case)
    fpath = forces_path(case)
    t, fx = parse_forces(fpath)
    tc, fp, fv = parse_forces_components(fpath)
    if len(t) != len(tc):
        return {"refused": "total and component histories disagree in length"}
    factor = 2.0 if is_symmetric(case) else 1.0
    out: dict = {"parts": {}, "settled": True, "reasons": []}
    for name, arr in (("total", fx), ("pressure", fp), ("viscous", fv)):
        est = estimate_settled_mean(t, factor * arr, confidence)
        out["parts"][name] = est
        if "refused" in est:
            out["settled"] = False
            out["reasons"].append(f"{name}: {est['refused']}")
        elif est["rel_ci"] > rel_bar:
            out["settled"] = False
            out["reasons"].append(
                f"{name}: CI half-width {100*est['rel_ci']:.1f}% of the "
                f"mean exceeds {100*rel_bar:.0f}%")
    if out["settled"]:
        out["drag_n"] = out["parts"]["total"]["mean"]
        out["ci_half_n"] = out["parts"]["total"]["ci_half"]
    out["method"] = ("batch-means estimation (see parts[*].method); the "
                     "windowed-drift settled_drag remains the conservative "
                     "route and neither bar moved")
    return out


# ===========================================================================
# STAGE 2 OF THE VALIDATION LADDER — the SMOKE SOLVE, classified.
# The Mac runner produces it (run-case.sh's future SMOKE_ONLY=N mode: the
# first ~200 LTS iterations of the REAL interFoam solve, checkpoint kept);
# this is the fortress-side pure-Python reading of what it left behind.
# ===========================================================================

# THE TAU BAR IS run-case.sh's LIVE-ABORT BAR — one number, two parsers that
# must never disagree. The shell's guard (run-case.sh, the run_solver
# early-abort block) is `awk -v v="$_fts" 'BEGIN{exit !(v + 0 < 1e-12)}'`,
# re-based 2026-08-18 on the Mac's paired dataset: solved floor 7.8e-6 (five
# hulls), worst divergence 4.356e-18 (h18) — ~5.9 and ~5.6 orders of margin.
# tests/test_smoke_verdict.py fences this literal against the shell's.
SMOKE_TAU_FLOOR = 1e-12

# Solver-death markers: solve_one()'s set (scripts/mesh_robustness.py), the
# one calibrated on campaign hull 2 — whose log carries NO "--> FOAM FATAL"
# line, only sigFpe::sigHandler and "exited on signal 4". NEVER match the
# bare substring "Floating point": every interFoam banner prints "trapFpe:
# Floating point exception trapping enabled", which once read a clean 0.5 s
# run as a crash.
_SMOKE_DEATH_MARKERS = ("--> FOAM FATAL", "sigFpe::sigHandler",
                        "exited on signal", "Illegal instruction")

# The exact line heads the existing parsers key on: run-case.sh's live-abort
# awk matches "^Flow time scale min\/max = " and takes field 6 (the min, with
# its trailing comma stripped); solve_one/settled_drag read "^Time = " and
# the same tau line. Matching the same heads is what keeps this verdict and
# the shell's from ever disagreeing about one log.
_SMOKE_TIME_PREFIX = "Time = "
_SMOKE_TAU_PREFIX = "Flow time scale min/max = "


def smoke_verdict(case_dir: str | Path, n_iters: int = 200) -> dict:
    """Classify a SMOKE SOLVE — the first `n_iters` LTS iterations of the
    real interFoam solve — from `log.interFoam` (the same log location
    `settled_drag`'s mixed-history seam and mesh_robustness.solve_one read).

    The two recorded incidents this stage exists to catch at ~3 min price:

      * h2 — a mesh that passed EVERY checkMesh bar (0 zero-volume cells,
        0 wrongly-oriented faces, skew 6.95) reached LTS iteration 104 and
        DIED with sigFpe in GAMGSolver::scale, discovered at a 323 s solve
        price. checkMesh is measured blind to the class; the smoke solve is
        not, because the death is inside the first ~200 iterations.
      * h18 — the local flow time scale collapsed to 4.356e-18 s (twelve
        orders below every solved hull) and the run burned its full 2700 s
        budget into the timeout column.

    Verdicts — every dict carries the receipts it read (iterations_seen,
    min_tau/min_tau_iteration if any tau was printed, taus_seen), and every
    refusal carries the iteration it fired at:

      promoted      — the log reaches n_iters iterations, EVERY printed flow
                      time scale >= SMOKE_TAU_FLOOR (run-case.sh's bar), the
                      force history exists and is finite over the window, and
                      no death marker appears.
      refused-tau   — some printed tau fell below the bar (min + iteration
                      recorded). The h18 class, priced at ~3 min not 2700 s.
      refused-fatal — solver death (FPE/signal/FOAM FATAL) or a non-finite
                      force line, with the iteration. The h2 class.
      unmeasured    — the log is absent or shorter than n_iters with no death
                      marker, or the tau prints / force history could not be
                      read. NEVER promoted: an unmeasurable case reading as a
                      pass is this repo's defect class 1 (`${VAR:-0}`).

    Refusals fire in LOG ORDER — the earliest event in the window is the
    cause, the discipline classify() already applies to stages.
    """
    case = Path(case_dir)
    log = case / "log.interFoam"
    out: dict = {"case": str(case), "n_iters": n_iters,
                 "iterations_seen": 0, "taus_seen": 0,
                 "min_tau": None, "min_tau_iteration": None}
    if not log.exists():
        out.update(verdict="unmeasured",
                   why=f"no log.interFoam under {case} — the smoke stage "
                       f"never ran here; unmeasured, never promoted")
        return out

    it = 0
    for line in log.read_text().splitlines():
        if line.startswith(_SMOKE_TIME_PREFIX):
            if it >= n_iters:
                break                     # the smoke window is fully consumed
            it += 1
            out["iterations_seen"] = it
            continue
        if line.startswith(_SMOKE_TAU_PREFIX):
            # the shell's $6-with-comma-stripped, in Python
            raw = line[len(_SMOKE_TAU_PREFIX):].split(",")[0].strip()
            try:
                tau = float(raw)
            except ValueError:
                out.update(verdict="unmeasured",
                           why=f"unparseable tau at iteration {it}: {line!r}"
                               f" — an unreadable bar is unmeasured, never "
                               f"assumed healthy")
                return out
            out["taus_seen"] += 1
            if out["min_tau"] is None or tau < out["min_tau"]:
                out["min_tau"], out["min_tau_iteration"] = tau, it
            if tau < SMOKE_TAU_FLOOR:
                out.update(verdict="refused-tau", iteration=it,
                           why=f"flow time scale {tau:.4g} s fell below the "
                               f"{SMOKE_TAU_FLOOR:g} s bar at iteration {it} "
                               f"(run-case.sh's live-abort bar; the h18 "
                               f"class: 4.356e-18 for 2700 s)")
                return out
            continue
        if any(m in line for m in _SMOKE_DEATH_MARKERS):
            out.update(verdict="refused-fatal", iteration=it,
                       why=f"solver death at iteration {it}: "
                           f"{line.strip()[:120]!r} (the h2 class: died "
                           f"iteration 104 on a bar-passing mesh)")
            return out

    # Forces, through THE module's own reader (forces_path/parse_forces) so
    # a restart-merged history is handled the one recorded way. Under LTS the
    # time column IS the iteration count, so the window is the first n_iters
    # rows and a bad row's time value names the iteration.
    try:
        t, fx = parse_forces(forces_path(case))
    except FileNotFoundError:
        t = fx = None
    if fx is not None and len(fx):
        seg_t, seg_f = t[:n_iters], fx[:n_iters]
        bad = np.flatnonzero(~np.isfinite(seg_f))
        if bad.size:
            k = int(bad[0])
            out.update(verdict="refused-fatal", iteration=float(seg_t[k]),
                       why=f"non-finite force at iteration {seg_t[k]:g} — a "
                           f"diverged solve is not a number to be averaged")
            return out

    if it < n_iters:
        out.update(verdict="unmeasured",
                   why=f"log holds {it} of the {n_iters} smoke iterations "
                       f"and carries no death marker — truncated or still "
                       f"in flight; unmeasured, never promoted")
        return out
    if out["taus_seen"] == 0:
        out.update(verdict="unmeasured",
                   why="no 'Flow time scale' print anywhere in the window — "
                       "this is not an LTS smoke log, so the tau bar was "
                       "never measured; unmeasured, never promoted")
        return out
    if fx is None or not len(fx):
        out.update(verdict="unmeasured",
                   why="no readable force history — finite forces are part "
                       "of the promotion bar and were not measured")
        return out
    out["verdict"] = "promoted"
    return out


def family_refinement(coarse: int | None, medium: int | None,
                      fine: int | None) -> dict:
    """The refinement ratio of a triplet, MEASURED from its cell counts.

    Assuming r = sqrt(2) is what the nz-snapping incident punished: the
    generator was quietly producing 1.297 and 1.368 while post_gci assumed
    sqrt(2), and the report came out p = nan, GCI 58.5%. So there is no assumed
    default here — a missing count raises.

    Both scripts computed this, and they even used the label `r12` for opposite
    steps (post_gci: coarse->medium; gate2m: fine->medium). The steps are named
    here.
    """
    counts = {"coarse": coarse, "medium": medium, "fine": fine}
    missing = [k for k, v in counts.items() if not v]
    if missing:
        raise CellCountError(
            f"no measured cell count for: {', '.join(missing)}. The refinement "
            f"ratio is the whole basis of a GCI; it is MEASURED from the grids "
            f"or it is not reported.")
    r_cm = (medium / coarse) ** (1 / 3)
    r_mf = (fine / medium) ** (1 / 3)
    spread = 100.0 * abs(r_mf - r_cm) / max(r_cm, r_mf)
    return {"r_coarse_to_medium": r_cm, "r_medium_to_fine": r_mf,
            "spread_pct": spread, "r": (r_cm * r_mf) ** 0.5,
            "one_family": spread <= FAMILY_SPREAD_TOL_PCT,
            "cells": (coarse, medium, fine)}


def stl_wetted_area(path: str | Path, waterline: float = 0.0) -> float:
    """Submerged area [m^2] of an ascii STL, triangles clipped at z=waterline.

    Gate 2M compares C_t against the Tokyo-2015 scatter, and C_t needs the
    wetted surface the CFD actually saw — taking it from the STL (the same
    geometry snappy meshed) keeps it honest for external benchmark hulls,
    where no analytic hull object exists to ask.
    """
    verts: list = []
    tris: list = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append([float(v) for v in s.split()[1:4]])
            if len(verts) == 3:
                tris.append(np.array(verts))
                verts = []

    total = 0.0
    for tri in tris:
        # Sutherland-Hodgman clip of the triangle against the half-space z<=wl
        poly: list = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            a_in, b_in = a[2] <= waterline, b[2] <= waterline
            if a_in:
                poly.append(a)
            if a_in != b_in:
                t = (waterline - a[2]) / (b[2] - a[2])
                poly.append(a + t * (b - a))
        if len(poly) < 3:
            continue
        p = np.array(poly)
        # fan triangulation of the (planar, convex) clipped polygon
        for i in range(1, len(p) - 1):
            total += 0.5 * float(np.linalg.norm(
                np.cross(p[i] - p[0], p[i + 1] - p[0])))
    return total


def _read_stl_tris(path: str | Path) -> list:
    """Ascii STL -> list of triangles, each a 3-tuple of (x, y, z) tuples.

    C-10, the semantics NAMED: vertices are ROUNDED TO 7 DECIMALS at parse
    time, so coordinates that differ below 1e-7 weld into one shared tuple.
    This is a different weld from `stl_forensics.load_stl`, which merges
    exact-on-the-written-decimal (what triSurfaceMesh does for shared grid
    points) and returns (verts, tris) index arrays instead of tuple soup.
    The repair pipeline below WANTS the rounding: it compares vertex tuples
    by equality (weld/cap/mirror), and `%.6e`-formatted floats reparsed
    through `float()` can disagree in the last digit. Two parsers, two
    declared jobs — do not merge them by making one lie about the other's
    tolerance.
    """
    verts: list = []
    tris: list = []
    for line in Path(path).read_text().splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append(tuple(round(float(v), 7) for v in s.split()[1:4]))
            if len(verts) == 3:
                tris.append(tuple(verts))
                verts = []
    return tris


def _write_stl(tris, path: str | Path, name: str = "hull") -> None:
    """Write triangles through THE one facet emitter (C-10).

    This body used to be a hand-copied second emitter loop — exactly the
    copy `case._tris_to_ascii_stl`'s G7.1 factoring exists to prevent. It
    now delegates, so facet formatting, normal recomputation and the
    degenerate-normal fallback have one home. `name` is accepted for
    signature compatibility and ignored: the emitter writes `solid hull`,
    and no caller passes anything else (grep 2026-08-18: all three internal
    call sites and tests use the default).
    """
    from .case import _tris_to_ascii_stl
    p = np.asarray(tris, float).reshape(-1, 3)
    Path(path).write_bytes(
        _tris_to_ascii_stl(p, np.arange(len(p)).reshape(-1, 3)))


def weld_vertices(src: str | Path, dst: str | Path, tol: float = 2e-4) -> dict:
    """Merge vertices closer than `tol` and drop the triangles that collapse.

    Sliver triangles are what snappyHexMesh turns into ZERO-VOLUME cells, and
    interFoam then dies on the first timestep. They are inherent to a sewn
    NURBS tessellation: the Tokyo-2015 KCS half body carries 8 triangles below
    quality 1e-3 straight out of the IGES, where patches with mismatched
    tessellation meet. Welding coincident-ish vertices removes the cause
    instead of asking the mesher to cope with it.

    Quality here is 4*sqrt(3)*A / sum(edge^2): 1 for equilateral, 0 for
    degenerate. Note that a max-edge/min-edge ratio does NOT detect these —
    three nearly COLLINEAR vertices have unremarkable edge lengths and no area.
    """
    tris = _read_stl_tris(src)
    # grid-snap to a lattice of size tol, then use the lattice cell as identity
    def key(v):
        return (round(v[0] / tol), round(v[1] / tol), round(v[2] / tol))

    rep: dict = {}
    for t in tris:
        for v in t:
            rep.setdefault(key(v), v)

    welded, dropped = [], 0
    for t in tris:
        p = tuple(rep[key(v)] for v in t)
        a, b, c = (np.array(v) for v in p)
        area = np.linalg.norm(np.cross(b - a, c - a)) / 2
        if len(set(p)) < 3 or area < 1e-12:
            dropped += 1
            continue
        welded.append(p)
    _write_stl(welded, dst)
    return {"n_tris": len(welded), "dropped": dropped,
            "vertices_merged": sum(1 for t in tris for v in t
                                   if rep[key(v)] != v)}


def mirror_half_hull(src: str | Path, dst: str | Path,
                     snap_tol: float = 1e-4) -> dict:
    """Mirror a half hull about y=0 into a full hull, SNAPPING the centreplane.

    MEASURED on the Tokyo-2015 KCS half body: its centreline vertices are not
    exactly on y=0 but scatter over -5.0e-6 .. +1.53e-5 m, with 49 of them on
    the wrong side of the plane. Mirroring that as-is makes the two halves
    interpenetrate by a few microns, which every topological check passes —
    watertight, manifold, no duplicates, correct enclosed volume — while
    snappyHexMesh produces 14 zero-volume cells, 73 wrongly oriented faces and
    non-orthogonality 148.9, and interFoam dies on the first timestep.

    Snapping |y| < snap_tol to exactly zero makes the seam shared rather than
    crossed. Mirrored triangles get REVERSED winding so normals stay outward,
    and triangles that collapse on snapping are dropped.
    """
    tris = _read_stl_tris(src)
    snapped, dropped = [], 0
    for tri in tris:
        p = [(x, 0.0 if abs(y) < snap_tol else y, z) for x, y, z in tri]
        a, b, c = (np.array(v) for v in p)
        if np.linalg.norm(np.cross(b - a, c - a)) / 2 < 1e-14:
            dropped += 1                      # collapsed on the plane
            continue
        snapped.append(tuple(p))

    out = list(snapped)
    for tri in snapped:
        m = [(x, -y, z) for x, y, z in tri]
        if all(abs(v[1]) < 1e-15 for v in tri):
            continue                          # lies in the plane: no twin
        out.append((m[0], m[2], m[1]))        # reversed winding -> outward
    _write_stl(out, dst)
    return {"n_tris": len(out), "dropped_degenerate": dropped,
            "half_tris": len(snapped)}


def _triangulate_polygon(pts, u, v, normal):
    """Ear-clip a planar polygon, returning outward-oriented triangles.

    A centroid FAN is only valid for a convex loop. On a ship deck outline —
    which is not convex — fan triangles cross outside the polygon and the STL
    becomes SELF-INTERSECTING: measured, the fan turned a clean sewn KCS half
    hull ("Surface is not self-intersecting") into one with 5 intersections,
    and snappy then degraded catastrophically as cells shrank enough to
    resolve them (149 zero-volume cells and 938 wrongly oriented faces at
    refinement level 4-5, versus 10 and 55 at level 2-3). Ear clipping keeps
    every triangle inside the polygon by construction.
    """
    P = np.array([[np.dot(p - pts[0], u), np.dot(p - pts[0], v)] for p in pts])
    # orient CCW in the (u, v) frame so the "ear" test has a fixed sign
    area2 = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                for i in range(len(P)))
    idx = list(range(len(pts)))
    if area2 < 0:
        idx.reverse()

    def cross2(o, a, b):
        return ((P[a][0] - P[o][0]) * (P[b][1] - P[o][1])
                - (P[a][1] - P[o][1]) * (P[b][0] - P[o][0]))

    def inside(a, b, c, p):
        d1, d2, d3 = cross2(a, b, p), cross2(b, c, p), cross2(c, a, p)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    out, guard = [], 0
    while len(idx) > 3 and guard < 10 * len(pts):
        guard += 1
        for k in range(len(idx)):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            if cross2(a, b, c) <= 0:                      # reflex, not an ear
                continue
            if any(inside(a, b, c, m) for m in idx if m not in (a, b, c)):
                continue
            out.append((a, b, c))
            idx.pop(k)
            break
        else:
            break                                        # no ear: give up
    if len(idx) == 3:
        out.append(tuple(idx))

    tris = []
    for a, b, c in out:
        t = [pts[a], pts[b], pts[c]]
        if np.dot(np.cross(t[1] - t[0], t[2] - t[0]), normal) < 0:
            t = [t[0], t[2], t[1]]
        tris.append(tuple(tuple(float(x) for x in p) for p in t))
    return tris


def cap_planar_holes(src: str | Path, dst: str | Path,
                     planar_tol: float = 1e-4,
                     only_axis: int | None = None,
                     only_value: float = 0.0,
                     only_tol: float = 1e-3) -> dict:
    """Close planar openings in a triangulated surface (deck, transom, ...).

    External benchmark geometry arrives as a trimmed-surface model, not a
    solid: the Tokyo-2015 KCS IGES is a half body open at the deck. CFD needs a
    CLOSED manifold or the mesher floods the interior — the same lesson the
    own-hull STL taught (198 open edges, first Mac smoke run).

    Each boundary loop is triangulated as a fan from its centroid, with the
    cap normal oriented away from the body centroid so windings stay outward.
    Non-planar loops are refused rather than silently fudged.
    """
    tris = _read_stl_tris(src)
    from collections import Counter, defaultdict

    edges: Counter = Counter()
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted(e))] += 1
    boundary = [e for e, n in edges.items() if n == 1]
    # On a HALF hull the boundary is one L-shaped loop spanning the
    # centreplane AND the deck, so it is genuinely non-planar. Only the deck
    # needs capping — the symmetry patch closes the centreplane — hence the
    # option to cap just the loop lying in one plane.
    if only_axis is not None:
        boundary = [e for e in boundary
                    if all(abs(p[only_axis] - only_value) < only_tol
                           for p in e)]

    # chain boundary edges into closed loops
    adj: dict = defaultdict(list)
    for a, b in boundary:
        adj[a].append(b)
        adj[b].append(a)
    unused = set(boundary)
    loops: list = []
    while unused:
        a, b = next(iter(unused))
        unused.discard((a, b))
        loop = [a, b]
        while True:
            cur = loop[-1]
            nxt = None
            for cand in adj[cur]:
                e = tuple(sorted((cur, cand)))
                if e in unused:
                    nxt = cand
                    unused.discard(e)
                    break
            if nxt is None:
                break
            if nxt == loop[0]:
                break
            loop.append(nxt)
        if len(loop) >= 3:
            loops.append(loop)

    body_c = np.array([p for t in tris for p in t]).mean(axis=0)
    capped = list(tris)
    made = 0
    for loop in loops:
        pts = np.array(loop)
        c = pts.mean(axis=0)
        # plane fit: smallest singular vector is the normal
        _, sv, vt = np.linalg.svd(pts - c)
        if sv[-1] / max(sv[0], 1e-12) > planar_tol * 100:
            raise ValueError(
                f"boundary loop of {len(loop)} points is not planar "
                f"(flatness {sv[-1]:.3e}); refusing to cap it blindly")
        n = vt[-1]
        if np.dot(n, c - body_c) < 0:      # point the cap outward
            n = -n
        for tri in _triangulate_polygon(pts, vt[0], vt[1], n):
            capped.append(tri)
            made += 1

    _write_stl(capped, dst)
    return {"loops_capped": len(loops), "triangles_added": made,
            "n_tris": len(capped)}


def resistance_coefficient(drag: float, wetted_area: float, speed: float,
                           rho: float | None = None) -> float:
    """C_t = R_t / (0.5 rho S U^2) — the form Tokyo-2015 reports.

    rho defaults to the density the forces function object is TOLD, which lives
    at `navalai.cfd.case._RHO_WATER`. It used to be retyped as a default here
    and again as `RHO` in scripts/gate2m.py — two more copies of the literal
    that tests/test_cfd_reference_parity.py already fences inside case.py, and
    the gate's copy was the one that divided every reported C_T.
    """
    if wetted_area <= 0 or speed <= 0:
        raise ValueError("wetted_area and speed must be positive")
    if rho is None:
        from .case import _RHO_WATER
        rho = _RHO_WATER
    return abs(drag) / (0.5 * rho * wetted_area * speed ** 2)


@dataclass(frozen=True)
class GCIReport:
    f_fine: float
    f_extrapolated: float     # Richardson estimate at h -> 0
    p_observed: float         # observed convergence order
    gci_fine_pct: float       # Roache GCI (Fs=1.25), percent of fine value
    method: str


def gci(f_coarse: float, f_medium: float, f_fine: float,
        refinement: float = 2.0 ** 0.5) -> GCIReport:
    """Roache GCI from three systematically refined grids (r = h_c/h_f)."""
    e21 = f_medium - f_fine
    e32 = f_coarse - f_medium
    if abs(e21) < 1e-12 or e32 * e21 <= 0:
        # oscillatory or converged-to-machine: report conservative bound
        spread = max(abs(e21), abs(e32))
        return GCIReport(f_fine, f_fine, float("nan"),
                         100.0 * 1.25 * spread / max(abs(f_fine), 1e-12),
                         "oscillatory: spread bound, Fs=1.25")
    p_raw = math.log(abs(e32 / e21)) / math.log(refinement)
    # THE LOW-END CLAMP WAS ANTI-CONSERVATIVE. Raising a below-first-order p up
    # to 0.5 SHRINKS the reported uncertainty, because GCI ~ 1/(r^p - 1).
    # MEASURED on an exact Richardson triplet at r=sqrt(2) with true p=0.1: the
    # analytic GCI is 6.392% and this function reported 1.191% — an
    # understatement of 5.37x, in precisely the direction that lets a barely
    # converging triplet claim the <=2.5% bar. Roache's own recommendation for
    # a poorly-behaved p is to fall back to first order with the SAFER factor
    # Fs = 3.0, so that is what fires, and the method string says which rule
    # was used. The high-end clamp is conservative and stays.
    if p_raw < 1.0:
        # Keep the OBSERVED order and raise the safety factor. Substituting
        # p = 1 here was still anti-conservative: at p_obs = 0.1 it reported
        # 1.306% against an analytic 6.392%, because 1/(r^p - 1) collapses as p
        # rises. The observed p with Fs = 3.0 gives 15.3% — larger than the
        # Fs=1.25 figure, which is the point: a triplet below first order is
        # not in the asymptotic range and its uncertainty must not look small.
        # p is floored only to keep the denominator finite.
        p, fs = max(p_raw, 0.05), 3.0
        rule = f"p_obs={p_raw:.2f}<1, NOT asymptotic -> Fs=3.0"
    else:
        p, fs, rule = min(p_raw, 4.0), 1.25, "Richardson p (capped at 4), Fs=1.25"
    f_exact = f_fine - e21 / (refinement**p - 1.0)
    gci_pct = 100.0 * fs * abs(e21 / f_fine) / (refinement**p - 1.0)
    return GCIReport(f_fine, f_exact, p, gci_pct, f"Roache GCI, {rule}")


class WaterplaneError(ValueError):
    """The waterplane could not be closed from this geometry.

    A dedicated type so callers can fall back on a GEOMETRY problem without
    also swallowing a file-read failure. Learned the hard way: a binary STL
    raised UnicodeDecodeError, which is a ValueError, which a broad
    `except ValueError` upstream absorbed into a silent fallback.
    """


def stl_waterplane_properties(path, waterline: float = 0.0) -> dict:
    """Waterplane area, LCF and LONGITUDINAL second moment about it.

    Why this exists: the pitch restoring stiffness of a floating body is
    rho*g*I_L, and `sixdof_properties` was approximating I_L as Awp*(L/2)^2.
    MEASURED on the KCS STL: true I_L = 19.854 m^4 giving k_theta = 194539
    N.m/rad, against the approximation's 771030 — **3.96x too stiff**. That put
    the pitch damper at zeta 0.597 instead of the intended 0.30, roughly
    doubling settling time on a run already budgeted in days.

    Method: the closed waterplane is recovered from the hull surface by the
    divergence theorem rather than by cutting the mesh. For the submerged
    volume V bounded by hull + cap, integrating div(F) with F = (0,0,1) gives
    A_wp = -sum(A_i n_z,i) over the HULL triangles below the waterline, because
    the cap's own contribution is what we are solving for. The same trick with
    F = (0,0,x^2) yields the second moment about x=0; the parallel axis then
    moves it to the centre of flotation.
    """
    tris = np.asarray(_read_stl_tris(path), float)
    tris = tris - np.array([0.0, 0.0, waterline])

    kept = []
    for tri in tris:
        z = tri[:, 2]
        if (z <= 0).all():
            kept.append(tri)
            continue
        if (z > 0).all():
            continue
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if a[2] <= 0:
                poly.append(a)
            if (a[2] <= 0) != (b[2] <= 0):
                f = a[2] / (a[2] - b[2])
                poly.append(a + f * (b - a))
        for i in range(1, len(poly) - 1):
            kept.append(np.array([poly[0], poly[i], poly[i + 1]]))
    if not kept:
        raise WaterplaneError("no submerged geometry below the waterline")

    T = np.asarray(kept)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n2 = np.cross(b - a, c - a)          # 2 * area * unit normal
    nz = n2[:, 2] * 0.5                  # signed area projected on z
    xbar = (a[:, 0] + b[:, 0] + c[:, 0]) / 3.0

    awp = -float(nz.sum())
    if awp <= 0:
        raise WaterplaneError(f"non-physical waterplane area {awp:.6g} m^2")
    # int(x) over a triangle IS area * centroid — exact, because x is linear.
    lcf = -float((nz * xbar).sum()) / awp
    # int(x^2) is NOT area * centroid^2. The exact quadrature over a triangle is
    # A * (sum xi^2 + sum_{i<j} xi xj) / 6; using the centroid squared
    # understated a 4 x 2 m box's I_L as 3.556 m^4 against the closed-form
    # B*L^3/12 = 10.667 — a factor of 3, and in the unsafe direction for a
    # stiffness. Caught by the box anchor, which is why the anchor exists.
    x1, x2, x3 = a[:, 0], b[:, 0], c[:, 0]
    x2_quad = (x1 * x1 + x2 * x2 + x3 * x3
               + x1 * x2 + x1 * x3 + x2 * x3) / 6.0
    i_x0 = -float((nz * x2_quad).sum())
    i_l = i_x0 - awp * lcf ** 2
    return {"awp_m2": awp, "lcf": lcf, "i_l_m4": max(i_l, 1e-12)}


def stl_submerged_properties(path, waterline: float = 0.0,
                             trim_deg: float = 0.0,
                             x_pivot: float = 0.0) -> dict:
    """Submerged volume and its centroid (LCB/TCB/VCB) from a closed STL.

    Why this exists rather than a published LCB percentage: the KCS STL spans
    0..7.7165 m against an Lpp of 7.2786 m — the bulbous bow and the rudder
    reach beyond the perpendiculars — so "-1.48% Lpp from midship" cannot be
    located in this file's coordinates without knowing where the perpendiculars
    fall. The geometry knows, so ask it.

    Method: divergence theorem over the hull triangles BELOW the waterline,
    clipped at it. The waterplane cap can be skipped entirely, which is what
    makes this simple: on that cap the outward normal is +z, so it contributes
    (1/3)(r.n) = z/3 = 0 to the volume, and n_x = n_y = 0 kills its contribution
    to the x and y centroid integrals. Only VCB needs the cap, and it gets it
    because z = waterline there is a constant, handled analytically below.

    `trim_deg` (R2.1): the ladder now floats a TRIMMED attitude, and a level
    clip of an upright STL is a different boat from the one the ladder
    validated. Positive = bow (larger x) down, the ladder's convention; the
    mesh is rigidly rotated about the y-axis through (`x_pivot`, waterline)
    into the floating attitude before the level clip — rigid equivalence to
    clipping the upright mesh at the tilted plane. With trim, the centroid
    is reported in the ROTATED (floating-attitude) frame.

    Returns {volume_m3, lcb, tcb, vcb} with centroid in the STL's own frame.
    """
    tris = np.asarray(_read_stl_tris(path), float)
    tris = tris - np.array([0.0, 0.0, waterline])      # waterline -> z = 0
    if trim_deg:
        cth = np.cos(np.radians(trim_deg))
        sth = np.sin(np.radians(trim_deg))
        xr = tris[..., 0] - x_pivot
        zr = tris[..., 2]
        tris = tris.copy()
        tris[..., 0] = cth * xr + sth * zr + x_pivot
        tris[..., 2] = -sth * xr + cth * zr

    kept = []
    for tri in tris:
        z = tri[:, 2]
        if (z <= 0).all():
            kept.append(tri)
            continue
        if (z > 0).all():
            continue
        # Sutherland-Hodgman against the half-space z <= 0, then fan-triangulate
        poly = []
        for i in range(3):
            a, b = tri[i], tri[(i + 1) % 3]
            if a[2] <= 0:
                poly.append(a)
            if (a[2] <= 0) != (b[2] <= 0):
                f = a[2] / (a[2] - b[2])
                poly.append(a + f * (b - a))
        for i in range(1, len(poly) - 1):
            kept.append(np.array([poly[0], poly[i], poly[i + 1]]))

    if not kept:
        raise ValueError("no submerged geometry below the waterline")
    T = np.asarray(kept)
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    n = np.cross(b - a, c - a)                       # 2 * area * unit normal

    vol = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    # int x dV = 1/24 * sum n_x * [(a+b)^2 + (b+c)^2 + (c+a)^2]  (componentwise)
    moment = (n * ((a + b) ** 2 + (b + c) ** 2 + (c + a) ** 2)).sum(axis=0) / 24.0
    centroid = moment / (2.0 * vol)

    return {"volume_m3": abs(vol),
            "lcb": float(centroid[0]), "tcb": float(centroid[1]),
            "vcb": float(centroid[2]) + waterline}
