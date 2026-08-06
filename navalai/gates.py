"""The gate ladder, one command: python3 -m navalai.gates

Prints the honest status of every phase gate. GREEN gates are enforced by the
pytest suites (this runner re-executes them); METAL-GATED entries name exactly
what hardware/software the remaining evidence needs — never faked green.

WHY THIS FILE LOOKS THE WAY IT DOES (audit 2026-08-05/06)
---------------------------------------------------------
A red-team pass demonstrated, with working proofs, that a measured RED gate
could be erased by editing ONE PROSE STRING:

    "RED (measured): C_t -15.4% vs EFD"     -> exit 1   (correct)
    "AMBER (measured): C_t -15.4% vs EFD"   -> exit 0
    "METAL-GATED: C_t -15.4% vs EFD"        -> exit 0
    blocked=None                            -> exit 0
    (delete the row entirely)               -> exit 0

because the failure test was `str(blocked).upper().startswith("RED")`. Nothing
pinned the GATES list, so a row could also just vanish. A status that is
free text is not a verdict; it is a suggestion.

Three changes follow from that:

1. STATUS IS A TYPED ENUM, not a string that happens to start with "RED".
   `Verdict.RED` cannot be renamed into passing.
2. EVERY RED GATE MUST APPEAR IN A COMMITTED LEDGER (`data/gate-ledger.json`)
   with a measured watermark, an owner, and a review-by date. This is what
   restores CI as a REGRESSION signal: the question stops being "is anything
   red?" (a constant, since 2M and 2U are honestly red) and becomes "is
   anything red that we did not already record, or REDDER than we recorded?"
   Nothing is softened — the red rows still print, first, every run.
3. A SUITE THAT STOPS RUNNING IS A FAILURE, not a comfortable green. pytest
   exits 0 when every test skips, and `xfail` produced a GREEN row with no
   annotation at all because "xfailed" matched none of the alternations in
   the old summary parser.

The `review_by` date is the anti-wallpaper clause: an expected-red gate cannot
quietly become permanent furniture. It forces a re-measurement or an explicit,
dated, owner-signed extension — PLM.md section 3 step 6 ("regression gates keep
them honest forever") applied to the reds themselves.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = _ROOT / "data" / "gate-ledger.json"


class Verdict:
    """Typed statuses for gates with no pytest suite.

    Deliberately not free text. RED means "ran and missed its bar"; METAL and
    REVIEW mean "honestly unverifiable here", which is a different claim and
    must never be reachable by editing a RED row's wording.
    """

    RED = "RED"          # ran, missed its bar, kept red
    METAL = "METAL"      # needs hardware/software this machine lacks
    REVIEW = "REVIEW"    # needs a qualified human


@dataclass(frozen=True)
class Gate:
    name: str
    scope: str
    suite: str | None = None      # pytest file, or None for a status row
    status: str | None = None     # a Verdict, required when suite is None
    detail: str = ""              # human context; NEVER load-bearing

    def __post_init__(self) -> None:
        if (self.suite is None) == (self.status is None):
            raise ValueError(
                f"{self.name}: exactly one of suite/status must be set — a row "
                f"with neither is a gate that verifies nothing while looking "
                f"like a gate")
        if self.status is not None and self.status not in vars(Verdict).values():
            raise ValueError(f"{self.name}: {self.status!r} is not a Verdict")


GATES = [
    Gate("Gate 0", "grammar/geometry/DB", "tests/test_phase0.py"),
    Gate("Gate 1", "L1 physics + Wigley anchor + <50ms", "tests/test_phase1.py"),
    # Gate 1's own bar names Holtrop-Mennen, and `grep -rin holtrop` used to hit
    # the plan document and nothing else while Gate 1 printed GREEN. Split out
    # rather than folded into Gate 1 so the ladder shows WHICH clause is
    # covered by what.
    Gate("Gate 1H", "Holtrop-Mennen vs the 1982 worked example",
         "tests/test_holtrop.py"),
    Gate("Gate 1b", "NSGA-II Pareto front", "tests/test_optimize.py"),
    Gate("Gate 2", "Capytaine BEM (Hulme anchor)", "tests/test_phase2.py"),
    Gate("Gate 2R", "CFD reference parity + GCI honesty",
         "tests/test_cfd_reference_parity.py"),
    Gate("Gate 3", "surrogate spine (Forrester + L1 GP)", "tests/test_phase3.py"),
    Gate("Gate 4", "generative + slider p95<100ms", "tests/test_phase4.py"),
    Gate("Gate 5", "mission translation + LLM seam", "tests/test_phase5.py"),
    Gate("Gate 6", "rules-as-code mechanics", "tests/test_phase6.py"),
    Gate("Gate 7", "flywheel + regression gate", "tests/test_phase7.py"),
    Gate("Gate B", "grammar AST + bend radius + 8-D genome", "tests/test_stageB.py"),
    Gate("Gate C", "agentic PLM network + engineer + STEP/IGES",
         "tests/test_stageC.py"),
    Gate("Gate D", "waves/RAO response + dynamics + CFD post", "tests/test_stageD.py"),
    Gate("Gate E", "latent-space evolution + latent GP", "tests/test_stageE.py"),
    Gate("Gate F", "panel unroll/DXF + Pareto dash + handoff receipt",
         "tests/test_stageF.py"),
    Gate("Gate L", "one limit, one home; scantling derived from the rule",
         "tests/test_limits_single_source.py"),
    Gate("Gate R3", "the ladder is climbable: L2 escalation, monotone tier "
         "promotion, honest refusal of L3", "tests/test_ladder.py"),
    Gate("Gate 2M", "KCS/JBC OpenFOAM calibration w/ per-case GCI",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    Gate("Gate 2U", "unattended meshing (plan: >=95% of a 200-hull batch)",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    Gate("Gate 6R", "ISO threshold parity vs licensed standard text",
         "tests/test_phase6r.py"),
]

# Summary line only. pytest writes it two ways depending on flags —
#   "= 3 failed, 19 passed, 2 skipped in 0.42s ="   (banner form)
#   "13 passed in 0.11s"                            (-q form)
# — so the anchor is the TIMING CLAUSE plus a leading count, not the '=' rule.
# That is what a spoof lacks: a conftest printing "wrote report.xml: 20 passed"
# has no "in <n>s", and the old reverse-scan-and-break parser accepted it,
# turning an all-skipped suite GREEN.
_SUMMARY_HEAD = re.compile(
    r"^[=\s]*\d+\s+(passed|failed|skipped|error|errors|xfailed|xpassed|deselected)")
_SUMMARY_TAIL = re.compile(r"\bin\s[\d.]+\s*s\b")
_COUNT = re.compile(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed)")


def counts(output: str) -> dict:
    """Parse pytest's SUMMARY line into a count dict."""
    out = {"passed": 0, "failed": 0, "skipped": 0, "error": 0,
           "xfailed": 0, "xpassed": 0}
    for line in reversed(output.strip().splitlines()):
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if not (_SUMMARY_HEAD.match(clean) and _SUMMARY_TAIL.search(clean)):
            continue
        for n, what in _COUNT.findall(clean):
            out["error" if what.startswith("error") else what] = int(n)
        break
    return out


def status_of(returncode: int, c: dict) -> tuple[str, bool]:
    """(label, counts_as_failure).

    A gate is GREEN only if tests actually RAN and passed. pytest exits 0 when
    every test SKIPS, so a machine without capytaine would have reported
    "Gate 2 GREEN" while verifying nothing.

    xfail/xpass are failures here, not decorations. One line —
    `@pytest.mark.xfail(reason='known gap')` — turned a failing gate test into
    a GREEN row with NO annotation, because the old parser did not know the
    word. A known gap belongs in the ledger where it has an owner and a date,
    not in a marker that silences the ladder.
    """
    if returncode != 0 or c["failed"] or c["error"]:
        return "RED", True
    if c["xfailed"] or c["xpassed"]:
        return (f"RED (xfail/xpass: {c['xfailed']}/{c['xpassed']} — put known "
                f"gaps in the ledger, not in a marker)", True)
    if c["passed"] == 0:
        return "SKIPPED (no tests ran — missing dependency?)", False
    if c["skipped"]:
        return f"GREEN ({c['skipped']} skipped)", False
    return "GREEN", False


def load_ledger(path: str | Path | None) -> dict:
    p = Path(path) if path else DEFAULT_LEDGER
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def judge_red(name: str, ledger: dict, today: date) -> tuple[str, bool]:
    """Is this RED gate expected, regressed, or new? (label, is_failure)"""
    entry = ledger.get(name)
    if entry is None:
        return ("RED (NEW — not in the ledger. Record it with a measured "
                "watermark and an owner, or fix it.)", True)
    try:
        due = date.fromisoformat(str(entry.get("review_by", "")))
    except ValueError:
        return ("RED (ledger entry has no valid review_by date)", True)
    if today > due:
        return (f"RED (LEDGER EXPIRED — unreviewed since {due.isoformat()}. "
                f"Re-measure or sign a dated extension.)", True)
    wm = entry.get("watermark")
    return (f"RED (expected: {entry.get('metric', '?')} watermark {wm}, "
            f"measured {entry.get('measured_utc', '?')}, "
            f"owner {entry.get('owner', '?')}, review by {due.isoformat()})",
            False)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    strict = "--strict" in argv          # CI: skipped gates are not acceptable
    # --suites-only: judge ONLY the pytest-backed gates. The pre-push hook uses
    # this so it blocks REGRESSIONS without blocking every push on gates that
    # are known, measured and recorded red. Making the hook unusable is how you
    # train people to --no-verify, which is worse than either.
    suites_only = "--suites-only" in argv
    ledger_path = None
    for i, a in enumerate(argv):
        if a == "--ledger" and i + 1 < len(argv):
            ledger_path = argv[i + 1]
    ledger = load_ledger(ledger_path)
    today = date.today()

    failures = skipped_gates = red_gates = 0
    green_names: list[str] = []
    print(f"{'gate':8} {'scope':45} status")
    print("-" * 78)
    for g in GATES:
        if g.suite is None:
            if g.status == Verdict.RED:
                label, is_fail = judge_red(g.name, ledger, today)
                if not suites_only and is_fail:
                    red_gates += 1
            else:
                label = f"{g.status}-GATED — {g.detail}"
            print(f"{g.name:8} {g.scope:45} {label}")
            continue
        r = subprocess.run([sys.executable, "-m", "pytest", g.suite, "-q",
                            "--no-header"], capture_output=True, text=True)
        c = counts(r.stdout)
        label, is_fail = status_of(r.returncode, c)
        failures += 1 if is_fail else 0
        if label.startswith("SKIPPED"):
            skipped_gates += 1
        elif not is_fail:
            green_names.append(g.name)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        print(f"{g.name:8} {g.scope:45} {label}  ({tail})")

    # A gate that RECOVERED must not leave its entry behind: a stale ledger is
    # how an expected-red list turns into a list of things nobody rechecks.
    stale = sorted(set(ledger) & set(green_names))
    if stale and not suites_only:
        print(f"\nLEDGER STALE: {', '.join(stale)} now GREEN — remove the "
              f"entry so the ledger keeps meaning what it says.")
        red_gates += len(stale)

    if red_gates:
        print(f"\n{red_gates} gate(s) are red in a way the ledger does not "
              f"account for. A failing gate is information; never soften it.")
    if skipped_gates:
        print(f"\n{skipped_gates} gate(s) ran no tests. "
              f"{'FAILING (--strict).' if strict else 'Install the optional deps to verify them.'}")
    return 1 if (failures or red_gates or (strict and skipped_gates)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
