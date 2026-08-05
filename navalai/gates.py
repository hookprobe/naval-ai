"""The gate ladder, one command: python3 -m navalai.gates

Prints the honest status of every phase gate. GREEN gates are enforced by the
pytest suites (this runner re-executes them); METAL-GATED entries name exactly
what hardware/software the remaining evidence needs — never faked green.
"""

from __future__ import annotations

import re
import subprocess
import sys

GATES = [
    ("Gate 0", "grammar/geometry/DB", "tests/test_phase0.py", None),
    ("Gate 1", "L1 physics + Wigley anchor + <50ms", "tests/test_phase1.py", None),
    ("Gate 1b", "NSGA-II Pareto front", "tests/test_optimize.py", None),
    ("Gate 2", "Capytaine BEM (Hulme anchor)", "tests/test_phase2.py", None),
    ("Gate 3", "surrogate spine (Forrester + L1 GP)", "tests/test_phase3.py", None),
    ("Gate 4", "generative + slider p95<100ms", "tests/test_phase4.py", None),
    ("Gate 5", "mission translation + LLM seam", "tests/test_phase5.py", None),
    ("Gate 6", "rules-as-code mechanics", "tests/test_phase6.py", None),
    ("Gate 7", "flywheel + regression gate", "tests/test_phase7.py", None),
    ("Gate B", "grammar AST + bend radius + 8-D genome", "tests/test_stageB.py", None),
    ("Gate C", "agentic PLM network + engineer + STEP/IGES", "tests/test_stageC.py", None),
    ("Gate D", "waves/RAO response + dynamics + CFD post", "tests/test_stageD.py", None),
    ("Gate E", "latent-space evolution + latent GP", "tests/test_stageE.py", None),
    ("Gate F", "panel unroll/DXF + Pareto dash + handoff receipt",
     "tests/test_stageF.py", None),
    ("Gate 2M", "KCS/JBC OpenFOAM calibration w/ per-case GCI",
     None, "RED (re-measured 2026-08-05 after fixing a force-parser bug): "
     "C_t 4.283e-3 vs EFD 3.711e-3 = -15.4%, still outside the Tokyo-2015 "
     "scatter 3.620-3.733e-3 (needs -14.7% to reach its top). The earlier "
     "-151% figure was OUR double-counting bug, not the CFD. Remaining gap is "
     "an ordinary coarse-mesh RANS error: 306k cells, y+ median 2475, fixed "
     "sinkage/trim where Case 2.1 is free. No GCI triplet yet."),
    ("Gate 2U", "unattended meshing (plan: >=95% of a 200-hull batch)",
     None, "RED (measured 2026-08-05, N=8): 75.0% meshed unattended. 2 of 8 "
     "hulls produced zero-volume cells or wrongly oriented faces, both of "
     "which kill interFoam on timestep 1. BuildPlan Risk #1. "
     "Re-measure: scripts/mesh_robustness.py --n 200"),
    ("Gate 6R", "ISO threshold parity vs licensed standard text",
     None, "REVIEW-GATED: qualified-reviewer parity on basis='approx' values"),
]


def counts(output: str) -> dict:
    """Parse pytest's summary line into {passed, failed, skipped, errors}."""
    out = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for line in reversed(output.strip().splitlines()):
        found = re.findall(r"(\d+) (passed|failed|skipped|error|errors)", line)
        if found:
            for n, what in found:
                out[what.rstrip("s") if what != "passed" else "passed"] = int(n)
            break
    return out


def status_of(returncode: int, c: dict) -> tuple[str, bool]:
    """(label, counts_as_failure).

    A gate is GREEN only if tests actually RAN and passed. pytest exits 0 when
    every test SKIPS — so a machine without capytaine would have reported
    "Gate 2 GREEN" while verifying nothing. That is precisely the soft-green
    the honesty rules forbid, so a suite that ran nothing is SKIPPED, never
    GREEN, and --strict makes it a failure (use that in CI).
    """
    if returncode != 0 or c["failed"] or c["error"]:
        return "RED", True
    if c["passed"] == 0:
        return "SKIPPED (no tests ran — missing dependency?)", False
    if c["skipped"]:
        return f"GREEN ({c['skipped']} skipped)", False
    return "GREEN", False


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    strict = "--strict" in argv          # CI: skipped gates are not acceptable
    # --suites-only: judge ONLY the pytest-backed gates. The pre-push hook uses
    # this so it blocks REGRESSIONS (a suite going red) without blocking every
    # push on gates that are known, measured and recorded red (2M, 2U). Making
    # the hook unusable is how you train people to --no-verify, which is worse
    # than either. CI runs WITHOUT it, so the red gates stay visible there.
    suites_only = "--suites-only" in argv
    failures = skipped_gates = red_gates = 0
    print(f"{'gate':8} {'scope':45} status")
    print("-" * 78)
    for name, scope, suite, blocked in GATES:
        if suite is None:
            print(f"{name:8} {scope:45} {blocked}")
            # A RED row is a gate that RAN and missed its bar. It must fail the
            # runner, or CI goes green with Gate 2M at -151% vs EFD and the
            # pre-push "BLOCKED: a gate is RED" message can never fire.
            # METAL/REVIEW-gated rows are different: they are honestly
            # unverifiable here, so they do not fail.
            if not suites_only and str(blocked).strip().upper().startswith("RED"):
                red_gates += 1
            continue
        r = subprocess.run([sys.executable, "-m", "pytest", suite, "-q",
                            "--no-header", "-x"], capture_output=True, text=True)
        c = counts(r.stdout)
        label, is_fail = status_of(r.returncode, c)
        failures += 1 if is_fail else 0
        if label.startswith("SKIPPED"):
            skipped_gates += 1
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(f"{name:8} {scope:45} {label}  ({tail})")
    if red_gates:
        print(f"\n{red_gates} gate(s) RED — ran and missed their bar. "
              "A failing gate is information; never soften it to pass.")
    if skipped_gates:
        print(f"\n{skipped_gates} gate(s) ran no tests. "
              f"{'FAILING (--strict).' if strict else 'Install the optional deps to verify them.'}")
    return 1 if (failures or red_gates or (strict and skipped_gates)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
