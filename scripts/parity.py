#!/usr/bin/env python3
"""CROSS-MACHINE PARITY — do fortress001 and the Mac still agree?

WHY THIS EXISTS, and it is a measured answer to a measured problem.

The two machines DO NOT AGREE BITWISE, and that has now been established
twice, independently, weeks apart:

  * the h011/h012 investigation measured `stl_sha256` non-portable — 13 of
    one hull's 3,467,472 printed `%.6e` numbers sit within 1e-12 of a
    rounding boundary, so the hash moves across platforms while the
    geometry does not;
  * the Mac's 2026-08-20 suite run failed a geometry equality fence that
    PASSES on x86-64, by exactly one ulp (`62 of 514 elements differ,
    worst |diff| 1.110e-16`) — the same arithmetic under a different SIMD
    and FMA schedule, which IEEE-754 permits.

So the naive check — run it on both and compare exactly — reports a
failure every time and teaches everyone to ignore it. And the naive
alternative — read the other machine's report — is what produced the
2026-08-20 P0 incident, where a transcribed `1.110e-16` lost its exponent,
became "metre-scale, not float noise", and nearly sent both machines
hunting a defect that did not exist.

WHAT ACTUALLY CAUGHT DEFECTS on 2026-08-20 was neither: it was each
machine EXECUTING the other's claim and re-deriving the one number that
mattered. The Mac ran fortress's Block 3 arms and found arm A was a straw
man; it re-ran the cases after fortress's wave-floor fix and found the fix
was in a module the case writer never calls; fortress re-tested the Mac's
proposed crossover mechanism and refuted it. None of those needed the
other machine's prose. All of them needed its NUMBERS, produced here.

So: this emits a RECEIPT of what this machine computes, at declared
tolerance, with the platform stamped on it — and diffs two receipts,
classifying every difference as PLATFORM (inside what IEEE allows between
these architectures) or REGRESSION (outside it, and therefore about the
code). Seconds to run, against 35 minutes for the suite.

USAGE
    python3 scripts/parity.py --emit  > parity-$(uname -m).json
    python3 scripts/parity.py --compare parity-x86_64.json parity-arm64.json

WHAT IT IS NOT: a replacement for the test suite. The suite asks whether
the code is right; this asks whether the two machines still mean the same
thing by it. A green parity with a red suite is a consistent pair of
wrong answers, and the header says so on every receipt.
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from navalai.contract import evaluate_hull                    # noqa: E402
from navalai import grammar
from navalai.mission import MissionSpec                       # noqa: E402

#: Relative tolerance below which a difference is attributed to the
#: PLATFORM rather than to the code.
#:
#: 1e-12, and the two anchors that bracket it are both measured rather than
#: assumed. BELOW: the largest cross-architecture disagreement this project
#: has measured is one ulp — 1.110e-16 relative at unit scale, four orders
#: inside this bar, so genuine platform noise is never reported as a
#: regression. ABOVE: the smallest real defect this project has caught was
#: a 2x reference-area error (`forceCoeffs wrong by exactly 2x on every
#: symmetric run`), twelve orders outside it, so no real defect hides
#: underneath. The band between is empty in every measurement taken so far,
#: which is what makes the classification safe rather than convenient.
#:
#: A quantity that legitimately accumulates error — an iterative solve —
#: can exceed this honestly. `solve_equilibrium` converges to tol = 1e-3,
#: so attitude-derived quantities are compared at that tolerance instead;
#: see `_TOL_BY_KEY`.
PLATFORM_REL_TOL = 1e-12

#: Quantities whose own solver tolerance is looser than the platform bar.
#: MEASURED 2026-08-20: categories A and B of the same hull differ by five
#: MICRONS on the downflooding height (0.8836405 against 0.8836354 m,
#: 5.7e-6 relative) purely because two equilibrium attitudes were solved
#: separately. Comparing those at 1e-12 across machines would report the
#: solver's own convergence as a cross-machine regression.
_TOL_BY_KEY = {
    "trim": 2e-3, "list": 2e-3, "freeboard_min": 2e-3,
    "lcb_pct": 2e-3, "gm": 2e-3, "draft": 2e-3,
}

#: The designs the receipt covers. Fixed genomes, so the comparison is of
#: MACHINES and not of samplers: a receipt that drew its own hulls would
#: differ between runs for reasons that have nothing to do with either box.
def _cases() -> list[tuple[str, np.ndarray, MissionSpec]]:
    from navalai.mission import MissionSpec as MS
    out: list[tuple[str, np.ndarray, MS]] = []

    # 1. the reference hull the whole repository is pinned against
    from tests.test_phase0 import mid_params
    out.append(("reference", grammar.pad_genome(mid_params()), MS()))

    # 2. the kit reference — the first hull that is BOTH certifiable and
    #    sheet-buildable, and therefore the one a product claim rests on
    # PADDED to this tree's arity. These genomes were written at 16 genes and
    # are still the same hulls; without the pad the grammar refuses them for
    # WIDTH and seven of the eight parity cases come back REFUSED, which reads
    # as a cross-machine disagreement and is nothing of the kind.
    out.append(("kit-reference", grammar.pad_genome([
        12.24464859, 3.105685017, 0.55, 1.55, 0.6392941018, -1.0,
        0.4760097448, 0.3, 9.039289126, 9.039289126, 0.35, 0.0,
        0.15, 0.0, 0.0, 0.18]), MS()))

    # 3-6. the size-band coverage hulls and the two named forms, at the
    #      cruise speeds they were generated for. These are the hulls the
    #      Mac meshes, so they are the ones whose numbers must agree.
    p = Path(__file__).resolve().parents[1] / "data" / "coverage-band-hulls.json"
    if p.exists():
        d = json.loads(p.read_text())
        src = list(d.get("bands", {}).items()) + \
            list(d.get("named_forms", {}).items())
        for name, rec in src:
            g = grammar.pad_genome(rec["genome"])
            kn = rec.get("cruise_speed_kn")
            out.append((f"coverage:{name}",
                        g, MS(cruise_speed_kn=kn) if kn else MS()))
    return out


def _flatten(prefix: str, obj, into: dict) -> None:
    """Every finite number in the receipt, keyed by its path."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else str(k), v, into)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _flatten(f"{prefix}[{i}]", v, into)
    elif isinstance(obj, bool):
        into[prefix] = obj                      # before the numeric branch
    elif isinstance(obj, (int, float)):
        f = float(obj)
        into[prefix] = f if math.isfinite(f) else str(obj)
    elif isinstance(obj, str):
        into[prefix] = obj


def emit() -> dict:
    """This machine's answers, with the machine stamped on them."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).resolve().parents[1])).stdout.strip()
    except Exception:                                       # noqa: BLE001
        commit = "unknown"

    values: dict = {}
    verdicts: dict = {}
    for name, genome, mission in _cases():
        try:
            ev = evaluate_hull(genome, mission)
        except Exception as e:                              # noqa: BLE001
            verdicts[name] = f"RAISED {type(e).__name__}: {e}"
            continue
        d = ev.to_dict()
        # verdicts are compared as STRINGS: a machine that disagrees about
        # REFUSED vs MARGINAL has a defect no tolerance can excuse.
        verdicts[name] = "|".join((
            d["status"], d["hull_verdict"], d["model_verdict"],
            d["mesh_verdict"], d["result_verdict"], d["fidelity_tier"],
            ",".join(d["regimes"]), str(d["in_domain"])))
        _flatten(name, {k: v for k, v in d.items()
                        if k not in ("reasons", "warnings", "detail",
                                     "fidelity_why", "genome_sha256")},
                 values)
    return {
        "_README": ("Cross-machine parity receipt. Compare with "
                    "`parity.py --compare a.json b.json`. GREEN PARITY IS "
                    "NOT GREEN TESTS: this says the two machines agree, "
                    "not that either is right."),
        "platform": {
            "machine": platform.machine(),
            "system": platform.system(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "commit": commit,
        "n_cases": len(_cases()),
        "verdicts": verdicts,
        "values": values,
    }


def compare(a: dict, b: dict) -> int:
    """Diff two receipts. Returns a process exit code: 0 = agree."""
    pa, pb = a.get("platform", {}), b.get("platform", {})
    same_arch = pa.get("machine") == pb.get("machine")
    print(f"A: {pa.get('machine')} {pa.get('system')} numpy "
          f"{pa.get('numpy')} @ {a.get('commit')}")
    print(f"B: {pb.get('machine')} {pb.get('system')} numpy "
          f"{pb.get('numpy')} @ {b.get('commit')}")
    if a.get("commit") != b.get("commit"):
        print("\n!! DIFFERENT COMMITS — any difference below may be code, "
              "not platform. Compare the same tree before reading further.")
    print()

    regressions: list[str] = []
    platform_diffs: list[str] = []

    va, vb = a.get("verdicts", {}), b.get("verdicts", {})
    for k in sorted(set(va) | set(vb)):
        if va.get(k) != vb.get(k):
            regressions.append(
                f"VERDICT {k}: {va.get(k)!r} vs {vb.get(k)!r}")

    xa, xb = a.get("values", {}), b.get("values", {})
    only = (set(xa) ^ set(xb))
    for k in sorted(only):
        regressions.append(f"KEY only on one side: {k}")

    for k in sorted(set(xa) & set(xb)):
        u, v = xa[k], xb[k]
        if isinstance(u, (bool, str)) or isinstance(v, (bool, str)):
            if u != v:
                regressions.append(f"{k}: {u!r} vs {v!r}")
            continue
        if u == v:
            continue
        tol = PLATFORM_REL_TOL
        for suffix, t in _TOL_BY_KEY.items():
            if k.endswith(suffix):
                tol = t
                break
        rel = abs(u - v) / max(abs(u), abs(v), 1e-300)
        (platform_diffs if rel <= tol else regressions).append(
            f"{k}: {u!r} vs {v!r}  (rel {rel:.3e}, tol {tol:.0e})")

    n = len(set(xa) & set(xb))
    print(f"{n} numeric keys compared, {len(va)} verdicts")
    if platform_diffs:
        label = ("same architecture — a difference here is NOT expected"
                 if same_arch else "cross-architecture, IEEE-legal")
        print(f"\nPLATFORM-CLASS differences ({len(platform_diffs)}) "
              f"[{label}]:")
        for d in platform_diffs[:10]:
            print(f"  {d}")
        if len(platform_diffs) > 10:
            print(f"  ... and {len(platform_diffs) - 10} more")
    if regressions:
        print(f"\nREGRESSION-CLASS differences ({len(regressions)}) — these "
              f"are about the CODE:")
        for d in regressions[:20]:
            print(f"  {d}")
        if len(regressions) > 20:
            print(f"  ... and {len(regressions) - 20} more")
        print("\nPARITY: FAILED")
        return 1
    print("\nPARITY: OK" + ("" if not platform_diffs else
                            " (platform-class differences only)"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true",
                    help="print this machine's receipt as JSON")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="diff two receipts")
    args = ap.parse_args()
    if args.compare:
        return compare(json.loads(Path(args.compare[0]).read_text()),
                       json.loads(Path(args.compare[1]).read_text()))
    if args.emit:
        json.dump(emit(), sys.stdout, indent=1, sort_keys=True)
        print()
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
