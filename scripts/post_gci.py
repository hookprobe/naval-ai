"""Post-process a GCI triplet: settled drag per grid + Roache GCI.

For a NON-BENCHMARK hull. `scripts/gate2m.py` is the same report with the
KRISO acceptance data attached and a PASS/FAIL; both read their numbers from
`navalai.cfd.post.settled_drag`, which is the one place that decides what a
settled drag is.

Usage (any shell, venv active):
  python scripts/post_gci.py runs/gci
  python scripts/post_gci.py runs/gci --speed 2.57

WHAT THIS SCRIPT NO LONGER DECIDES FOR ITSELF, and why (all MEASURED
2026-08-06 on the recorded runs, before the consolidation):

  --tail        The averaging window is part of the settledness rule, not a
                preference, and it was tunable until a run passed. MEASURED on
                runs/val_coarse5: at `--tail 0.4` the drift on the total is
                **0.3%** — this script would have printed no flag at all — on a
                run whose pressure component swings by half its own mean with a
                ~5 s period. The window is now the last fifth, by TIME, and the
                oscillation is caught by a batch-mean error the drift test
                cannot see. See navalai/cfd/post.settled_drag.
  the cell count  It read checkMesh's `cells:` and FELL BACK to case.info's
                `cells_bg=`, which is the background block spec ~16x smaller.
                MEASURED on runs/kcs_gci2, where only the coarse grid had been
                meshed, this script printed
                    cells 243354 / 38000 / 108864
                    measured refinement ratio 0.538 (c->m), 1.420 (m->f)
                — one measured count and two specs inside one ratio, reporting
                a family that gets COARSER under refinement. The count is now
                MEASURED or the GCI is refused.
  r = sqrt(2)   The fallback when counts were unavailable. Assuming sqrt(2) is
                precisely the nz-snapping incident: the generator was producing
                1.297 and 1.368 and the report came out p = nan, GCI 58.5%.
                There is no assumed ratio any more.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.cfd import post

GRIDS = ("coarse", "medium", "fine")


def yplus_report(case: Path) -> str | None:
    """Last y+ line for the hull patch, if the yPlus function object ran.

    The build plan specifies wall functions at y+ ~ 30 (SJTU KCS pipeline).
    Only a fraction of hull faces take prism layers, so y+ is measured rather
    than assumed: y+ in the buffer layer (5-30) is where wall functions are
    least valid and skin friction goes quietly wrong.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="triplet root dir (contains coarse/medium/fine)")
    ap.add_argument("--speed", type=float, default=None,
                    help="reporting speed [m/s]; default: the speed each case "
                         "records in case.info, which is what it was RUN at")
    args = ap.parse_args()
    root = Path(args.root)

    # A single case directory is reported on its own — one grid, so no GCI.
    # gate2m.py has always accepted one; this script printed three MISSING
    # lines and "done" for it.
    single = (root / "system").is_dir()
    grids = {root.name: root} if single else {g: root / g for g in GRIDS}

    results: dict[str, dict] = {}
    print(f"{'grid':12} {'drag [N]':>12} {'std [N]':>9} {'drift %':>8} "
          f"{'batch %':>8} {'flow-thru':>9}  settled")
    print("-" * 72)
    for g, path in grids.items():
        try:
            r = post.settled_drag(path)
        except post.ForceHistoryError as exc:
            print(f"{g:12} NO RESULT — {exc}")
            continue
        results[g] = r
        worst_err = max(r["error_total"], r["error_pressure"], r["error_viscous"])
        print(f"{g:12} {r['drag_n']:12.1f} {r['std_n']:9.1f} "
              f"{100*r['drift']:8.1f} {100*worst_err:8.1f} "
              f"{r['flow_throughs']:9.2f}  "
              f"{'yes' if r['settled'] else 'NO'}")
        for why in r["reasons"]:
            print(f"         <-- {why}")

    if not results:
        print("\nNO RESULT — no grid has a usable force history.")
        return 2
    # The rule is printed, always, so nobody has to infer it from the numbers.
    print(f"\nsettledness: {next(iter(results.values()))['method']}")
    if any(r["domain_assumed"] for r in results.values()):
        print("NOTE: case.info predates `domain_length_m`; the flow-through "
              "count assumes the default domain proportions.")

    # wall-function validity, per grid (time patch min max average)
    yp = {g: yplus_report(p) for g, p in grids.items()}
    if any(yp.values()):
        print("\ny+ on hull (time patch min max average):")
        for g in grids:
            print(f"  {g:12} {yp[g] or 'not reported'}")
        print("  NOTE: read the MIN. The hull patch includes deck/topsides,")
        print("  which are dry; their y+ is meaningless and dominates max/avg.")

    settled = {g: r for g, r in results.items() if r["settled"]}
    if len(settled) < 3:
        print(f"\n{len(settled)} settled grid(s) of {len(grids)}: NO GCI. "
              f"A single grid carries no discretisation uncertainty, and a "
              f"grid that has not settled carries a transient.")
        return 2

    try:
        fam = post.family_refinement(results["coarse"]["cells"],
                                     results["medium"]["cells"],
                                     results["fine"]["cells"])
    except post.CellCountError as exc:
        print(f"\nNO GCI — {exc}")
        return 2
    print(f"\ncells (measured, checkMesh) : "
          f"{fam['cells'][0]} / {fam['cells'][1]} / {fam['cells'][2]}")
    print(f"refinement ratio            : "
          f"{fam['r_coarse_to_medium']:.3f} (c->m), "
          f"{fam['r_medium_to_fine']:.3f} (m->f), spread "
          f"{fam['spread_pct']:.2f}%")
    if not fam["one_family"]:
        print(f"NO GCI — the two refinement steps differ by "
              f"{fam['spread_pct']:.1f}%, so this is not a systematically "
              f"refined family and Richardson does not apply to it. Fix the "
              f"generator; do not average the ratio.")
        return 2

    rep = post.gci(results["coarse"]["drag_n"], results["medium"]["drag_n"],
                   results["fine"]["drag_n"], fam["r"])
    drag = abs(rep.f_fine)
    print(f"refinement ratio used       : {fam['r']:.3f}")
    print(f"\nRichardson extrapolated drag: {rep.f_extrapolated:.1f} N")
    print(f"observed order p            : {rep.p_observed:.2f}")
    print(f"GCI (fine grid)             : {rep.gci_fine_pct:.2f} %")
    print(f"method                      : {rep.method}")

    speed = args.speed or results["fine"]["speed"]
    print(f"\nfine-grid drag @ {speed} m/s : {drag:.1f} N "
          f"(+/- {rep.gci_fine_pct / 100 * drag:.1f} N grid uncertainty)")

    # C_t is the form Tokyo-2015 reports, so Gate 2M is judged on it
    ct = results["fine"]["ct"]
    if ct == ct:
        band = rep.gci_fine_pct / 100 * ct
        print(f"wetted surface (STL, z<0)   : "
              f"{results['fine']['s_wetted_m2']:.3f} m^2")
        print(f"C_t (fine)                  : {ct:.5e} "
              f"(+/- {band:.2e} from grid uncertainty)")
    print("compare: L1 Michell+ITTC tier prediction for the same hull/speed "
          "via navalai.evaluate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
