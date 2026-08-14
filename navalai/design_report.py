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
                    help="certify the reference hull against --mission")
    ap.add_argument("--no-gz", action="store_true",
                    help="skip the righting-arm solve (faster)")
    ap.add_argument("--json", help="write the machine-readable result here")
    args = ap.parse_args(argv)

    if args.case:
        case = {c.key: c for c in formcheck.CASES}[args.case]
        params, mission = np.asarray(case.params), case.mission
        print(f"case {case.key}: {case.title}")
    elif args.mission:
        mission = parse_mission(args.mission)
        params = reference_params()
        print("mission:", args.mission)
        print("geometry: the reference hull (pass --case for a specific "
              "vessel)")
    else:
        ap.error("need --case or --mission")

    cert = certify(params, mission, with_gz=not args.no_gz)
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
