"""Gate 2M verdict: KCS C_T against the Tokyo-2015 tank data, with per-case GCI.

`post_gci.py` computes the grid-convergence index but stops there — nothing
turned it into a PASS/FAIL against the experiment, so the gate's own criterion
lived only in prose. This script is that criterion, executable.

It refuses to produce a verdict it cannot support:
  - a grid whose force history has not SETTLED is reported and excluded,
    because an unconverged number is not a result;
  - fewer than three grids gives a C_T comparison but NO GCI, and says so;
  - a symmetric case has its force DOUBLED (half the hull is meshed), which is
    the single easiest way to be exactly 2x wrong and never notice.

NONE OF THOSE THREE ARE DECIDED HERE ANY MORE. This script and post_gci.py
were two independent post-processors over the same files and they disagreed on
the cell count, on what "settled" means and on the doubling; all of it now
lives in `navalai.cfd.post.settled_drag` and this script READS the verdict.
The disagreement was not academic — MEASURED on runs/kcs_gci2/coarse, post_gci
reported 2.1% drift (settled) where this script reported 10.9% (not settled),
from the same force.dat at the same instant.

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

# The drift bar, MIRRORED from navalai.cfd.post.DRIFT_TOL, which is where the
# settledness rule lives and where this number is applied. It is retyped here
# for exactly one reason: `navalai.pipeline.settle_tolerance()` reads the
# literal out of THIS FILE by regex (`^SETTLE_TOL\s*=\s*([0-9.]+)`), because
# this script is the one that prints the Gate 2M verdict. The two are fenced
# together by tests/test_settled_drag.py, which fails if they ever differ.
# Repointing pipeline at post.DRIFT_TOL would remove the mirror; pipeline.py is
# not this change's to edit.
SETTLE_TOL = 0.05
# The plan's Gate 2 bar is "documented grid uncertainty (target <= ~2.5%, the
# published bar)". 5% is the outer limit we will call converged at all; the
# Tokyo-2015 groups achieved 2.5-3.5%. A triplet whose own GCI exceeds this has
# not earned a verdict, however close its C_T happens to land.
GCI_BAR_PCT = 5.0


read_info = post.read_case_info      # one case.info parser; there were three


def gci_is_converged(gci_pct: float) -> bool:
    """Does this GCI clear the bar — AND is it an uncertainty at all?

    The test used to be the bare `gci <= GCI_BAR_PCT`, which is TRUE of
    -27.027% — the value the old local `gci()` produced for a triplet that was
    DIVERGING under refinement, and it printed VERDICT: PASS and exited 0.
    An uncertainty is a magnitude, so a negative or non-finite one means the
    estimator did not apply. That is a refusal, never a pass.
    """
    return (math.isfinite(gci_pct) and gci_pct >= 0.0
            and gci_pct <= GCI_BAR_PCT)


def benchmark_of(case: Path) -> str | None:
    """Which benchmark hull this case IS, from its own receipts — or None.

    THIS SCRIPT APPLIED `KCS.EFD`, `KCS.scatter_band()` AND `KCS.LPP` TO ANY
    DIRECTORY IT WAS POINTED AT. REPRODUCED: `gate2m.py runs/wigley` — a Wigley
    parabolic hull, Lwl 10.0 m at 2.971 m/s — printed

        Gate 2M — KCS resistance, Fn 0.26, U 2.196 m/s, Lpp 7.2786 m
          wigley  ...  C_T 5.9010e-03   E%D -59.0

    i.e. it scored a hull that has never been in the KRISO tank against KRISO
    tank data, under a header naming a speed the case was not run at. Every
    figure on that line except C_T belonged to a different ship.

    Identity comes from the STL hash, which is what `case.info` already
    records and what `data/benchmark_geom/CHECKSUMS.json` already pins. A
    `benchmark=` line (written by newer cases) is honoured first so a case can
    declare itself without the checksum file being present.
    """
    info = read_info(case)
    declared = info.get("benchmark", "").strip().lower()
    if declared and declared != "unknown":
        return declared
    sha = info.get("stl_sha256", "")
    if not sha:
        return None
    checks = Path(__file__).resolve().parents[1] / "data" / "benchmark_geom" / "CHECKSUMS.json"
    if not checks.exists():
        return None
    import json
    for name, entry in json.loads(checks.read_text()).items():
        if isinstance(entry, dict) and entry.get("sha256") == sha:
            return Path(name).stem.lower()
    return None


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


def grid_result(case: Path) -> dict:
    """One grid's settled drag and C_T — delegated to `post.settled_drag`.

    THIS FUNCTION USED TO CARRY THE RULES ITSELF, and `post_gci.py` carried a
    different set over the same files. All four disagreements were MEASURED
    2026-08-06 before this delegation landed:

      (a) THE WINDOW. It averaged and drifted over the last fifth BY SAMPLE
          INDEX, while post_gci used the halves of a `--tail 0.3` window. On
          runs/kcs_gci2/coarse: 10.9% drift here, 2.1% there — not settled and
          settled, from one file. dt is adaptive, so an index window also
          over-weights the instants where the solver was struggling: on
          runs/beach the same fifth reads 3.34% by index and 5.77% by time.
      (b) THE COMPONENTS. Drift was applied to the TOTAL only, and the total is
          dominated by the viscous part, which is the stable one. MEASURED on
          runs/lts: total drift 4.5%, so this gate called it SETTLED and
          printed C_T = 1.1995e-02 (E%D -223.2) as a comparison — while the
          PRESSURE component was drifting 7.5%. It is now refused.
      (c) THE CELL COUNT. `int(info.get("cells_bg", 0))` — the background block
          SPEC, and a silent 0 when absent, feeding the refinement ratio that
          the whole GCI rests on. It is now MEASURED from checkMesh or the GCI
          is refused. On these runs the two differ by ~16x (beach: 222444
          meshed against 13608 background).
      (d) rho. `RHO = 998.8` was a private retype of `case._RHO_WATER`, and it
          was the copy that divided every C_T this gate has printed.

    Raises post.ForceHistoryError when the case cannot yield a number at all;
    main() prints the reason rather than the old "no force data yet", which was
    also what a DIVERGED solve produced.

    SETTLE_TOL is passed rather than left implicit so that pipeline.py's claim
    — "gate2m.py is the gate that prints the verdict, so its SETTLE_TOL is the
    number" — is TRUE of this script, instead of naming a constant it no longer
    uses. It is fenced equal to post.DRIFT_TOL by tests/test_settled_drag.py.
    """
    return post.settled_drag(case, drift_tol=SETTLE_TOL)


def gci_report(f_fine: float, f_med: float, f_coarse: float,
               refinement: float) -> dict:
    """Roache GCI, delegated to `navalai.cfd.post.gci` — the ONE implementation.

    THIS SCRIPT USED TO CARRY ITS OWN COPY, and the copy was the less careful
    of the two while being the one that printed PASS/FAIL. Three defects, all
    REPRODUCED against the library version before this delegation landed:

      (a) SIGN. It computed `f_ext = f1 + e12/(r^p - 1)` with `e12 = f2 - f1`,
          which is Richardson with the sign inverted. On an exact triplet built
          around f_exact = 3.711e-3 it extrapolated to 3.911e-3 — it moved AWAY
          from the limit by exactly the amount it should have moved toward it,
          and the printed "extrapolated C_T" was the fine grid's error doubled.
      (b) NO SUB-FIRST-ORDER FALLBACK. `post.gci` drops to Roache's safer
          Fs = 3.0 when the observed p is below first order, because 1/(r^p - 1)
          collapses as p rises and Fs = 1.25 then flatters a triplet that is not
          in the asymptotic range. MEASURED at p_true = 0.3: this script said
          3.280% where `post.gci` says 7.872% — a 2.4x UNDERSTATEMENT, in the
          exact direction that lets a sub-first-order family clear the 5% bar.
      (c) NO SIGN GUARD ON THE GCI ITSELF. On a monotone but DIVERGING triplet
          (fine 3.700e-3, medium 4.100e-3, coarse 4.300e-3) it returned
          p = -2.000 and GCI = **-27.027%**, and `gci <= GCI_BAR_PCT` is true of
          a negative number, so Gate 2M printed VERDICT: PASS and exited 0 on a
          family that was getting WORSE under refinement. `post.gci` reports
          1855.435% on the same input.

    The `method` string is printed by the caller, so the reader can see WHICH
    safety rule fired rather than inferring it from the magnitude.
    """
    rep = post.gci(f_coarse, f_med, f_fine, refinement)
    note = ""
    if not math.isfinite(rep.p_observed):
        note = rep.method
    return {"p": rep.p_observed, "f_extrapolated": rep.f_extrapolated,
            "gci_fine_pct": rep.gci_fine_pct, "method": rep.method,
            "note": note}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/kcs_gci")
    cases = [root] if (root / "system").is_dir() else [
        d for n in ("coarse", "medium", "fine") if (d := root / n).is_dir()]
    if not cases:
        sys.exit(f"no case or triplet under {root}")

    # IDENTITY BEFORE JUDGEMENT. Gate 2M is a comparison against KRISO tank
    # data for ONE hull; running it on anything else produces an E%D that is
    # arithmetic without meaning (see `benchmark_of`).
    marks = {benchmark_of(c) for c in cases}
    if marks != {"kcs"}:
        named = ", ".join(sorted(str(m) for m in marks))
        sys.exit(
            f"REFUSING a verdict: {root} is not a KCS case (identified as: "
            f"{named}). Gate 2M compares C_T against the KRISO EFD 3.711e-3 "
            f"and the Tokyo-2015 scatter, both of which belong to KCS at "
            f"Fn 0.26. Judging another hull against them is not a failing "
            f"gate, it is a meaningless number. Use scripts/post_gci.py for "
            f"a non-benchmark case.")

    rows = []
    refused = []
    for c in cases:
        try:
            rows.append(grid_result(c))
        except post.ForceHistoryError as exc:
            # "no force data yet" was also what a DIVERGED solve printed, so the
            # reason is quoted rather than summarised.
            msg = str(exc)
            refused.append(msg if c.name in msg else f"{c.name}: {msg}")
    if not rows:
        sys.exit("no usable force history under "
                 f"{root}:\n  " + "\n  ".join(refused))

    lo, hi = KCS.scatter_band()
    print(f"Gate 2M — KCS resistance, Fn {KCS.DESIGN_FN}, "
          f"U {KCS.DESIGN_SPEED} m/s, Lpp {KCS.LPP} m")
    print(f"EFD (KRISO): C_T = {KCS.EFD['ct']:.4e}   "
          f"Tokyo-2015 scatter {lo:.3e} .. {hi:.3e}\n")
    print(f"{'grid':>12} {'cells':>9} {'t_end':>7} {'flow-thru':>9} "
          f"{'drag N':>9} {'C_T':>10} {'E%D':>7} {'drift':>7}  settled")
    print("-" * 88)
    for r in rows:
        # The cell count is MEASURED (checkMesh) or it is not printed. It used
        # to read `int(case.info cells_bg, default 0)` — a different quantity,
        # ~16x smaller, with a silent 0 when absent, feeding the GCI ratio.
        cells = f"{r['cells']:9d}" if r["cells"] else f"{'n/a':>9}"
        print(f"{r['name']:>12} {cells} {r['t_end']:7.1f} "
              f"{r['flow_throughs']:9.2f} "
              f"{abs(r['drag_n']):9.1f} {r['ct']:10.4e} "
              f"{KCS.error_vs_efd(r['ct']):+7.1f} {100*r['drift']:6.1f}%  "
              f"{'yes' if r['settled'] else 'NO'}")
    for why in refused:
        print(f"NO RESULT: {why}")
    print(f"\nsettledness: {rows[0]['method']}")
    if any(r["domain_assumed"] for r in rows):
        print("NOTE: case.info predates `domain_length_m`; the flow-through "
              "count assumes the default domain proportions.")
    for r in rows:
        for why in r["reasons"]:
            print(f"NOT SETTLED — {r['name']}: {why}")
        if r["settled"] and r["flow_throughs"] < post.FLOW_THROUGH_TARGET:
            print(f"UNDER-RUN: {r['name']} is settled at "
                  f"{r['flow_throughs']:.2f} flow-throughs. The target for a "
                  f"KCS resistance number is "
                  f"{post.FLOW_THROUGH_TARGET:.1f} (75 s). Treat this as a "
                  f"trend, not a result.")

    # Free-motion runs are checked on sinkage and trim as well, since EFD
    # reports both and they are what a fixed-attitude solve gets wrong.
    # Pair by the row's OWN case path: `zip(cases, rows)` silently misaligned
    # the moment any case was refused, attributing one grid's sinkage to
    # another grid's name.
    for r in rows:
        mo = motion_result(Path(r["case"]))
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
        print("\nVERDICT: NO RESULT — no grid has settled. Extend --end-time.")
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

    # `cases` is built coarse, medium, fine and the rows follow it.
    coarse, med, fine = usable[-3], usable[-2], usable[-1]
    # ONE ratio, one family check, one home: `post.family_refinement`. Both
    # scripts computed this, with the label `r12` meaning OPPOSITE steps
    # (post_gci: coarse->medium; here: fine->medium), and this one — the one
    # that prints PASS/FAIL — took its counts from `cells_bg`.
    try:
        fam = post.family_refinement(coarse["cells"], med["cells"], fine["cells"])
    except post.CellCountError as exc:
        print(f"\nGCI: {exc}")
        print("VERDICT: NO RESULT — the refinement ratio is not measurable.")
        return 2
    print(f"\nrefinement ratios measured from checkMesh cell counts: "
          f"{fam['cells'][0]} / {fam['cells'][1]} / {fam['cells'][2]}  ->  "
          f"{fam['r_coarse_to_medium']:.4f} (c->m), "
          f"{fam['r_medium_to_fine']:.4f} (m->f)  (spread "
          f"{fam['spread_pct']:.2f}%, using r = {fam['r']:.4f})")
    if not fam["one_family"]:
        print(f"GCI: the two refinement steps differ by "
              f"{fam['spread_pct']:.1f}% — this is NOT a systematically "
              f"refined family.")
        print("VERDICT: NO RESULT — fix the generator, do not average the ratio.")
        return 2
    g = gci_report(fine["ct"], med["ct"], coarse["ct"], fam["r"])
    if g["note"]:
        print(f"GCI: {g['note']}")
        print("VERDICT: NO RESULT — the triplet is not a convergent family.")
        return 2
    print(f"observed order p = {g['p']:.2f}   "
          f"extrapolated C_T = {g['f_extrapolated']:.4e}   "
          f"GCI(fine) = {g['gci_fine_pct']:.2f}%")
    print(f"GCI method: {g['method']}")

    ct, unc = fine["ct"], g["gci_fine_pct"] / 100.0 * fine["ct"]
    # UNCERTAINTY MUST NEVER WIDEN THE ACCEPTANCE REGION.
    # The old test was overlap of [ct-unc, ct+unc] with the band, with NO cap
    # on the GCI — so a sloppier grid study passed more easily. MEASURED at the
    # recorded C_T: GCI 2.5% -> FAIL, 5% -> FAIL, 12.8% -> FAIL, 15% -> PASS,
    # 100% -> PASS. The Tokyo-2015 groups achieved 2.5-3.5%, i.e. a careful
    # triplet failed where a careless one closed the gate. The bar is now two
    # independent conditions, both of which must hold.
    within_band = lo <= ct <= hi
    # A NEGATIVE OR NON-FINITE GCI IS NOT CONVERGENCE. `gci <= GCI_BAR_PCT` was
    # the whole test, and it is satisfied by -27.027% — the figure the deleted
    # local `gci()` returned for a DIVERGING triplet. An uncertainty is a
    # magnitude; anything that is not a finite non-negative number means the
    # estimator did not apply, which is a refusal, never a pass.
    gci_pct = g["gci_fine_pct"]
    converged = gci_is_converged(gci_pct)
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
