"""python -m navalai.design_report — the human face of the screening engine.

Certify one design against its mission and print the report a builder can
act on: verdict, why, the speed curve with its validity bands, loading
states, stability with assumptions, buildability, and whether the design is
worth CFD. `--json` writes the full machine-readable certification beside
the prose. No CFD is run, ever, by this command.

Usage:
    python -m navalai.design_report --case d
    python -m navalai.design_report --mission "6 tonne solar boat, 10 m, \
5 knots, category C" [--json out.json]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

import numpy as np

from . import formcheck
from .certify import certify
from .mission import parse_mission
from .reference import reference_params


def _fmt_q(name: str, q) -> str:
    sig = f" ± {q.sigma:.3g}" if q.sigma else ""
    return f"  {name:14s} {q.value:10.3f} {q.unit:6s}{sig}   [{q.tier}] {q.basis}"


def report(cert) -> str:
    lines = []
    lines.append(f"VERDICT: {cert.verdict}"
                 + ("" if cert.regime_supported else "  (regime unsupported)"))
    lines.append(f"regime:  {cert.regime} — supported={cert.regime_supported}")
    for r in cert.reasons:
        lines.append(f"  - {r}")
    lines.append("")
    lines.append("QUANTITIES (value/unit/tier/sigma/basis):")
    for k, q in cert.quantities.items():
        lines.append(_fmt_q(k, q))
    lines.append("")
    lines.append("SPEED CURVE (validity-banded; unsupported points are not "
                 "physics):")
    for p in cert.speed_curve:
        wh = f"{p.wh_per_nm:8.1f}" if p.wh_per_nm is not None else "     ---"
        lines.append(f"  {p.v_ms:5.2f} m/s  Fn {p.fn:4.2f}  "
                     f"Rt {p.rt_n:8.1f}±{p.sigma_rt_n:6.1f} N  "
                     f"Wh/NM {wh}  {p.validity}")
    lines.append("")
    lines.append("LOADING MATRIX:")
    for name, st in cert.loading.items():
        if "refused" in st:
            lines.append(f"  {name:16s} REFUSED: {st['refused'][:70]}")
        elif "unknown" in st:
            lines.append(f"  {name:16s} UNKNOWN: {st['unknown'][:70]}")
        else:
            tr = st["trim_deg"]
            lines.append(
                f"  {name:16s} disp {st['displacement_kg']:8.0f} kg  "
                f"draft {st['draft_m']:.3f} m  "
                f"trim {tr if tr is None else round(tr, 2)!s:>6} deg  "
                f"GM {st['gm_m'] if st['gm_m'] is None else round(st['gm_m'], 3)!s:>7} m  "
                f"fb {st['freeboard_m']:.2f} m  ok={st['ok']}")
    lines.append("")
    lines.append("STABILITY:")
    for k, v in cert.stability.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("BUILDABILITY (preliminary, not scantlings):")
    for k, v in cert.buildability.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"CFD candidacy: {cert.cfd_candidate}")
    lines.append("")
    lines.append("ASSUMPTIONS (every one is load-bearing):")
    for a in cert.assumptions:
        lines.append(f"  * {a}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="navalai.design_report")
    ap.add_argument("--case", choices=[c.key for c in formcheck.CASES],
                    help="a deterministic vessel case (formcheck.CASES)")
    ap.add_argument("--mission", help="a mission brief to parse")
    ap.add_argument("--reference", action="store_true",
                    help="certify the REFERENCE HULL against --mission "
                         "instead of designing for it. Without this, "
                         "--mission runs the search and reports a design.")
    ap.add_argument("--no-gz", action="store_true",
                    help="skip the righting-arm solve (faster)")
    ap.add_argument("--json", help="write the machine-readable result here")
    ap.add_argument("--constitution", choices=("none", "kit-line-v3"),
                    default="none",
                    help="compile a governing constitution and apply its "
                         "APPENDED constraint rows. Default 'none' so no "
                         "number this command already printed moves silently; "
                         "'kit-line-v3' is the sheet-plywood CNC kit line "
                         "(navalai.policy.reference_policy)")
    args = ap.parse_args(argv)

    policy = None
    if args.constitution != "none":
        from navalai.policy import reference_policy
        policy = reference_policy()
        print(f"constitution: {policy.constitution.name} "
              f"({len(policy.rows)} appended constraint row(s))")

    if args.case:
        case = {c.key: c for c in formcheck.CASES}[args.case]
        params, mission = np.asarray(case.params), case.mission
        print(f"case {case.key}: {case.title}")
    elif args.mission:
        mission = parse_mission(args.mission)
        print("mission:", args.mission)
        if args.reference:
            # THE REFERENCE HULL, BECAUSE IT WAS ASKED FOR -- and said loudly.
            params = reference_params()
            print("geometry: THE REFERENCE HULL, not a design for this brief."
                  "\n          Every number below, INCLUDING THE VERDICT, is "
                  "about that hull.\n          Drop --reference to design for "
                  "the brief instead.")
        else:
            # MISSION -> DESIGN. Until 2026-09-02 this branch used the
            # reference hull unconditionally and `--reference` -- a flag
            # declared, documented and NEVER READ -- selected nothing.
            #
            # MEASURED by the end-to-end flow check: the brief "8 m plywood
            # cabin launch, 6 knots, 1.8 tonne" printed a full report headed
            # by that brief, reporting a 2643 kg hull (a 1.8 t brief) with
            # `VERDICT: REFUSE` and violations -- B/T 12.60 outside its band,
            # beam_carried 0.122 -- that belong to the REFERENCE HULL and not
            # to anything the user asked for. One parenthetical line said so;
            # forty lines of numbers did not. A reader takes REFUSE to mean
            # "your boat is bad" when it means "the reference hull does not
            # meet your brief", and that is the worst kind of true statement.
            #
            # The product's design route is a SEARCH (`pareto_front`), the
            # same one `ui/server.py` serves. The CLI face now runs it.
            from navalai.optimize import pareto_front
            print("designing for this brief (NSGA-II, pop 48 x 30 gens) ...")
            res = pareto_front(mission, pop=48, gens=30, seed=0)
            X = np.atleast_2d(res.X) if res.X is not None else np.empty((0, 0))
            if not len(X):
                # A REFUSAL IS A RESULT. It carries the row tally that
                # explains it, exactly as the design feed's does.
                print("VERDICT: REFUSE — no design satisfied this brief.")
                print(" ", res.why_empty())
                print("\nThis is the product saying no, with reasons. Pass "
                      "--reference to certify the reference hull against the "
                      "brief anyway.")
                return 2
            # WHICH design, and WHY that one, stated rather than implied: the
            # front is 3-objective (min Wh/NM, min panel area, min build
            # area) and there is no single best point on a Pareto front. The
            # CLI reports the lowest-energy corner because energy is the
            # objective the briefs are written in; the others are on the
            # front and reachable through the UI.
            j = int(np.argmin(np.atleast_2d(res.F)[:, 0]))
            params = X[j]
            print(f"geometry: DESIGNED for this brief — {len(X)} designs on "
                  f"the Pareto front, reporting the lowest-energy one "
                  f"(objective 1 of 3: Wh/NM, panel area, build area)")
    else:
        ap.error("need --case or --mission")

    cert = certify(params, mission, with_gz=not args.no_gz, policy=policy)
    print(report(cert))
    if args.json:
        def _default(o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            if isinstance(o, (np.floating, np.integer)):
                return float(o)
            if isinstance(o, np.ndarray):
                return o.tolist()
            return str(o)
        with open(args.json, "w") as fh:
            json.dump(dataclasses.asdict(cert), fh, indent=1,
                      default=_default)
        print(f"\nmachine-readable certification -> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
