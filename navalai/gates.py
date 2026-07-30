"""The gate ladder, one command: python3 -m navalai.gates

Prints the honest status of every phase gate. GREEN gates are enforced by the
pytest suites (this runner re-executes them); METAL-GATED entries name exactly
what hardware/software the remaining evidence needs — never faked green.
"""

from __future__ import annotations

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
    ("Gate 2M", "KCS/JBC OpenFOAM calibration w/ per-case GCI",
     None, "METAL-GATED: needs an OpenFOAM machine (navalai/cfd templates ready)"),
    ("Gate 6R", "ISO threshold parity vs licensed standard text",
     None, "REVIEW-GATED: qualified-reviewer parity on basis='approx' values"),
]


def main() -> int:
    failures = 0
    print(f"{'gate':8} {'scope':45} status")
    print("-" * 78)
    for name, scope, suite, blocked in GATES:
        if suite is None:
            print(f"{name:8} {scope:45} {blocked}")
            continue
        r = subprocess.run([sys.executable, "-m", "pytest", suite, "-q",
                            "--no-header", "-x"], capture_output=True, text=True)
        ok = r.returncode == 0
        failures += 0 if ok else 1
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(f"{name:8} {scope:45} {'GREEN' if ok else 'RED'}  ({tail})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
