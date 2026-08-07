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
    # The row that judges the rows. It was deliberately NOT registered when it
    # was written — "the gate checking the gates is not itself a gate" — which
    # was backwards: it is the one whose disappearance would be least noticed.
    Gate("Gate 0G", "the ladder cannot be talked into passing",
         "tests/test_gate_integrity.py"),
    # Gate 0G's sibling, split out for the reason Gate 1H was: the ladder should
    # show WHICH clause is covered by what. 0G guards the STATUS machinery (a
    # verdict cannot be reworded, a row cannot vanish, a skipped suite is not
    # green). This one guards the boundary between the registry and the ledger:
    # a bar that a green suite MISSES must be a typed RED row with a ledger
    # watermark, never a sentence in a `scope`. Gate 4 carried its miss in prose
    # for a day and nothing could have failed on it (gap D11).
    Gate("Gate 0R", "a missed clause is RED BY RECORD, never prose in a scope",
         "tests/test_red_by_record.py"),
    Gate("Gate 0", "grammar/geometry/DB", "tests/test_phase0.py"),
    Gate("Gate 1", "L1 physics + Wigley anchor + <50ms", "tests/test_phase1.py"),
    # Gate 1's own bar names Holtrop-Mennen, and `grep -rin holtrop` used to hit
    # the plan document and nothing else while Gate 1 printed GREEN. Split out
    # rather than folded into Gate 1 so the ladder shows WHICH clause is
    # covered by what.
    Gate("Gate 1H", "Holtrop-Mennen vs the 1982 worked example",
         "tests/test_holtrop.py"),
    # Split out from Gate 1 for the same reason as Gate 1H: the ladder should
    # show WHICH clause is covered by what. This one owns the "never map
    # undefined onto ideal" family — a non-finite constraint that read as
    # feasible, trim/heel returning their BEST possible value where the
    # equilibrium stopped existing, an inert constraint, an order guard that
    # `python -O` deletes, and two proportions nobody re-checked on the hull
    # that actually floated.
    Gate("Gate 1C", "the constraint vector: complete, ordered, finite, and no "
         "undefined state reported as ideal", "tests/test_constraints_honest.py"),
    # Registered on the suite's behalf, and the scope is its own header line
    # rather than a guess: file ownership put navalai/gates.py with a different
    # agent than tests/test_gapfix_physics.py, and an unregistered suite makes
    # Gate 0G RED for a reason that has nothing to do with the code under test.
    # The register already recorded this coordination cost once, for Gate SR.
    Gate("Gate 1P", "the L1 physics core says what it actually computed",
         "tests/test_gapfix_physics.py"),
    Gate("Gate 1b", "NSGA-II Pareto front", "tests/test_optimize.py"),
    Gate("Gate 2", "Capytaine BEM (Hulme anchor)", "tests/test_phase2.py"),
    Gate("Gate 2R", "CFD reference parity + GCI honesty",
         "tests/test_cfd_reference_parity.py"),
    # Scope re-read against the suite 2026-08-06. It is no longer "Forrester +
    # an L1 GP": test_phase3.py also holds OOD refusal that separates error
    # rather than merely flagging it, the KOH rho estimator and its degeneracy
    # warnings, and the batched-EI diversity filter measured in the CANDIDATE
    # box. A scope line that names half a suite is a registry that under-reports
    # what would be lost if the suite stopped running.
    Gate("Gate 3", "surrogate spine: GP + co-kriging rho, OOD refusal, "
         "batched-EI infill", "tests/test_phase3.py"),
    # The feasibility clause is NOT here. It is Gate 4F, below, because a
    # shortfall stated in this row's `scope` was prose — see that row.
    Gate("Gate 4", "generative + slider p95<100ms (raw feasibility: Gate 4F)",
         "tests/test_phase4.py"),
    Gate("Gate 5", "mission translation + LLM seam", "tests/test_phase5.py"),
    Gate("Gate 6", "rules-as-code mechanics", "tests/test_phase6.py"),
    # Re-read against the suite 2026-08-06. Gate 7 has TWO clauses and the row
    # named neither: the frozen suite is no longer the training draw, the mark
    # is a monotone high-water ratchet, the wall clock (clause 2) is measured
    # and gated, and a MISSING baseline now refuses instead of passing — the
    # last of which is only meaningful because `data/baselines.json` is
    # committed (gap D3; `scripts/make_baseline.py` regenerates it).
    Gate("Gate 7", "flywheel: frozen suite != training draw, monotone "
         "regression mark, wall clock, committed baseline",
         "tests/test_phase7.py"),
    Gate("Gate B", "grammar AST + bend radius + 8-D genome", "tests/test_stageB.py"),
    Gate("Gate C", "agentic PLM network + engineer + STEP/IGES",
         "tests/test_stageC.py"),
    Gate("Gate D", "waves/RAO response + dynamics + CFD post", "tests/test_stageD.py"),
    Gate("Gate E", "latent-space evolution + latent GP", "tests/test_stageE.py"),
    Gate("Gate F", "panel unroll/DXF + Pareto dash + handoff receipt",
         "tests/test_stageF.py"),
    # Carried over from the APSE line when the four parallel branches were
    # consolidated onto master. APSE is the fidelity/similitude work: scale is
    # not a cost variable, fidelity is, and it is measured.
    Gate("Gate G", "APSE: similitude/ITTC-78/cost/planner/evidence",
         "tests/test_stageG.py"),
    # Gate 0G reported tests/test_gapfix_product.py as owned by NO gate while
    # the tests inside it -- the proofs for register rows G7 (ES-TRIN) and G8
    # (the ISO 12217-1 scope guard) -- were FAILING. An unowned suite is outside
    # the ladder, so its failures reddened nothing, and reconcile_gaps.py still
    # reported both rows CLOSED because it measures that the symbol EXISTS
    # rather than that the proof PASSES. Three honesty mechanisms, one blind
    # spot. Registered here so the ladder carries it.
    Gate("Gate 6P", "the product surface: scope guards refuse what does not "
         "govern, and the mission contract binds", "tests/test_gapfix_product.py"),
    Gate("Gate L", "one limit, one home; scantling derived from the rule",
         "tests/test_limits_single_source.py"),
    # Split out of Gate 6, which tested the RULES mechanics only. The
    # manufacturing back end is the other half of the plan's Phase 6 and it
    # was the half with no bar it could fail: no nesting, no BOM, no refold
    # test, and a developability metric that passes a hyperbolic paraboloid.
    # The row already existed; the scope now names the export receipt too,
    # which is a third of what the suite asserts (`export_dxf` nests rather
    # than stacks, a ladder-failing design is REFUSED an export, and STEP/IGES
    # loft the validated discretisation instead of a hard-coded 12 stations).
    # "developability controls" is plural on purpose: the suite carries the
    # POSITIVE controls (cylinder, cone) and the NEGATIVE one (hypar) — a
    # metric with no negative control is not a metric.
    Gate("Gate 6M", "manufacturing back end: nesting, BOM, refold, "
         "developability controls, export receipt",
         "tests/test_manufacturing.py"),
    Gate("Gate R3", "the ladder is climbable: L2 escalation, monotone tier "
         "promotion, honest refusal of L3", "tests/test_ladder.py"),
    # THE SPINE. Gap register section A is one finding restated seven ways: the
    # ladder is not a ladder, and nothing in the product could report a design
    # that entered a stage and never came back (`Evaluation.tier` read "L1" in
    # 100% of ~2000 evaluations). `navalai/pipeline.py` is the object that can,
    # and this row is what makes its central invariant a gate rather than a
    # docstring: every genome ends in EXACTLY ONE terminal state.
    #
    # The suite also owns the "unmeasured is never a pass" rule at the Python
    # level. It is the same rule `run-case.sh` learned on 2026-08-06 when
    # `${_MQ_SKEW:-0}` scored an unreadable skewness as perfect and a mesh at
    # 42.94 reached a 10-rank solve; the three checkMesh bars are READ out of
    # that script rather than restated, and one test doctors a copy of it to
    # prove the verdict follows the file.
    Gate("Gate S", "the MDO spine: one terminal state per genome, append-only "
         "archive, legal-transition graph, unmeasured metric refused",
         "tests/test_pipeline.py"),
    # The register was a document, so nothing could be assigned, nothing had a
    # state, and nothing noticed when a row went stale — section J's own
    # diagnosis, applied to section J's own file. This row guards the live
    # queue: the forward-only lifecycle, the append-only log, and the import
    # that turns docs/GAP-REGISTER.md's 119 findings into work items without
    # editing the audit record it reads.
    Gate("Gate SG", "the gap queue: findings are work items, not prose",
         "tests/test_gaps.py"),
    # A1/A2. `revalidate()` raised TierRequiresOperator UNCONDITIONALLY at L3
    # while its own docstring promised "the result then enters the ladder
    # through the provenance DB as an L3 row" — and nothing read that row. L3
    # is now READ from a recorded campaign and never solved; tier R alone can
    # refuse a design. MEASURED: nine of the ten case directories here lack
    # `domain_length_m` and are refused rather than defaulted.
    Gate("Gate R4", "the ladder is WIRED: every claimed tier reachable from "
         "evaluate(), L3 read from recorded evidence and never solved, tier R "
         "alone can refuse a design",
         "tests/test_ladder_wiring.py"),
    # The queue imported 119 findings ALL marked OPEN — the register document's
    # state, not the codebase's. ~45 were closed by commits nobody told it
    # about. This row guards the reconciliation being a REPEATABLE predicate
    # over the code rather than a one-off edit, and that a gap whose predicate
    # cannot be written reports NEEDS-HUMAN instead of being guessed closed.
    Gate("Gate SR", "gap state is derived from the code, not from prose",
         "tests/test_reconcile_gaps.py"),
    # R5.1. gate2m and post_gci disagreed on the cell count for r (checkMesh
    # with fallback vs cells_bg only) and on what "settled" means (last-fifth
    # by sample vs tail-fraction by time), so one triplet could yield two GCIs.
    # MEASURED 2026-08-06: drift on the TOTAL is dominated by the stable
    # viscous part, so gate2m called runs/beach settled at 0.70 flow-throughs
    # on 3.3% drift while its pressure component swung 1.80x-4.64x.
    Gate("Gate 2S", "one settled_drag: one cell-count rule, one settledness "
         "rule, and a component that oscillates cannot hide under a stable "
         "total", "tests/test_settled_drag.py"),
    # A4. Honesty rule 2 says a surrogate refuses OOD queries; `is_ood()` had
    # two call sites and BOTH WERE TESTS, so in production it extrapolated
    # silently.
    Gate("Gate 4H", "the surrogate refuses what it has not seen, and the "
         "feasibility bar measures the model rather than the sampler",
         "tests/test_surrogate_honesty.py"),
    # R5.5. The pressure component oscillates 0.27x-5.92x its expected value
    # with a domain-scale period while viscous holds at 1.22-1.36x ITTC-57.
    # This row guards the DIAGNOSTIC: a force history too short to resolve a
    # period must REFUSE to report one rather than return a noisy number.
    # RENAMED 2026-08-07: this row landed as a second "Gate 2R", colliding with
    # the CFD reference-parity row above. A gate NAME is the ledger's key —
    # `judge_red`, the stale-entry check and Gate 0G's `reds == ledger` all
    # index by it — and two rows sharing one collapse to a single set member, so
    # a ledger entry could account for a red that was never measured. The suite
    # named no gate in its own docstring, so nothing else moved. Uniqueness is
    # now asserted by tests/test_red_by_record.py rather than left to review.
    Gate("Gate 2T", "tank resonance is diagnosed, and a period is never "
         "claimed from too few cycles", "tests/test_tank_resonance.py"),
    # BuildPlan 2 V2.0. Its bar is provenance, not physics: "constants
    # importable, every one carries source+basis, no bare numbers".
    Gate("Gate V2.0", "refdata spine: every constant carries source + basis",
         "tests/test_refdata.py"),
    # Gap J5. This row exists to make a SKIP LOUD. The KCS geometry is
    # gitignored, so five tests skipped invisibly on every machine but the one
    # that generated the file — a pytest skip is not visible in the gate table,
    # and the table is the project's front door.
    Gate("Gate 2G", "KCS benchmark geometry: present and accepted "
         "(scripts/fetch_benchmark_geom.py)", "tests/test_benchmark_geom.py"),
    # Gap D8. is_complete() now requires a DATED edition per standard, which
    # flips the parity claim red. What remains testable — that basis routes
    # from the record, that no unreviewed basis leaks 'standard', that our own
    # practice values are not blessed — is Gate 6R-mech and stays green.
    Gate("Gate 6R-mech", "review-record mechanics + basis routing",
         "tests/test_phase6r.py"),
    # GAP D11, and HONESTY RULE 6 APPLIED TO THIS FILE'S OWN REGISTRY.
    #
    # Gate 4's suite passes everything it asserts, so the row printed a blanket
    # GREEN while the plan's headline generative bar — "raw draws are >=99%
    # feasible" — was MISSED. The 2026-08-06 fix put the miss in Gate 4's
    # `scope` string, and that was the defect wearing the fix's clothes: this
    # file documents `detail` as "human context; NEVER load-bearing", and a
    # `scope` is no more load-bearing than a `detail`. The measured shortfall
    # could be deleted, softened or left to rot by editing one prose string, and
    # nothing anywhere would fail — which is gap D1 ("RED" -> "AMBER" bought
    # exit 0) surviving in the one place D1's own fix did not reach. MEASURED at
    # the time: the ladder printed GREEN for Gate 4, the ledger had no row for
    # it, and the number got no worse only because nobody re-ran it.
    #
    # So the clause is split into its own typed RED row, the same move as Gate
    # 6R (a clause of Gate 6) and Gate 1H (a clause of Gate 1). It now prints
    # RED first on every run, `judge_red` fails CI if the ledger does not
    # account for it, and `review_by` stops it becoming furniture. THE NUMBERS
    # ARE NOT REPEATED HERE — watermark, model, draw and owner are in
    # data/gate-ledger.json, which is the single home for them (gap J1).
    # tests/test_red_by_record.py is the fence, and it fails if any scope or
    # detail string starts carrying a measurement again.
    Gate("Gate 4F", "raw generative feasibility: UNFILTERED model draws vs the "
         ">=99% bar (BuildPlan Phase 4)",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    Gate("Gate 2M", "KCS/JBC OpenFOAM calibration w/ per-case GCI",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    Gate("Gate 2U", "unattended meshing (plan: >=95% of a 200-hull batch)",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
    Gate("Gate 6R", "ISO threshold parity vs licensed standard text",
         status=Verdict.RED,
         detail="see data/gate-ledger.json for the measured watermark"),
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
        return ("SKIPPED (no tests ran — missing dependency, or absent data "
                "such as data/benchmark_geom/kcs.stl?)"), False
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


# --------------------------------------------------------------- the README
#
# GAP J2. README's gate table was hand-maintained, and every hand-maintained
# copy of a machine-readable fact drifts. MEASURED at the 2026-08-05 audit:
# per-gate test counts stale throughout (Gate 1 said 13 against 22 actual,
# Gate 2 said 4 against 18, Gate D said 12 against 19); NO Gate 2U row at all,
# so a RED gate was invisible in the project's front door; and Gate 2M's row
# carried a prose figure (-151%) that three later commits had superseded.
#
# The fix is not "update the README". It is to stop the README being a second
# source. The table is GENERATED from GATES, and a test fails when the file on
# disk and this function disagree. `--readme --write` performs the update, so
# the failure costs one command rather than a hand edit that will drift again.

README_BEGIN = "<!-- BEGIN GATE TABLE — generated by `python -m navalai.gates --readme` -->"
README_END = "<!-- END GATE TABLE -->"


def collect_counts(root: Path | None = None) -> dict[str, int]:
    """Tests per suite, from pytest's own collection.

    Collection, not execution: it costs ~0.5 s for the whole tree, so the
    README can carry a real count instead of a remembered one.

    A suite whose module-level `importorskip` fires collects ZERO. That is
    reported as 0 and the caller decides — the README test skips rather than
    baking "0 tests" into the file, because a missing optional dependency is
    an environment fact, not a project fact.
    """
    root = root or _ROOT
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/",
                        "--collect-only", "-q", "--no-header"],
                       capture_output=True, text=True, cwd=root)
    out: dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if "::" in line and line.startswith("tests/"):
            out[line.split("::", 1)[0]] = out.get(line.split("::", 1)[0], 0) + 1
    return out


def gate_rows(counts: dict[str, int] | None = None) -> list[tuple[str, str, str]]:
    """(gate, scope, evidence) for every row, in ladder order."""
    rows = []
    for g in GATES:
        if g.suite is None:
            if g.status == Verdict.RED:
                ev = "**RED** — `data/gate-ledger.json`"
            else:
                ev = f"**{g.status}-GATED** — {g.detail}"
        elif counts is None:
            ev = f"`{g.suite}`"
        else:
            n = counts.get(g.suite, 0)
            ev = f"`{g.suite}` ({n} tests)"
        rows.append((g.name, g.scope, ev))
    return rows


def markdown_table(counts: dict[str, int] | None = None) -> str:
    rows = gate_rows(counts)
    lines = ["| Gate | Scope | Verified by |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {e} |" for n, s, e in rows]
    return "\n".join(lines)


def readme_block(counts: dict[str, int] | None = None) -> str:
    return "\n".join([
        README_BEGIN,
        "",
        "Run `python -m navalai.gates` for live status; this table is the",
        "REGISTRY (what is gated by what), regenerated from `navalai/gates.py`.",
        "A RED row's measured watermark, owner and review-by date live in",
        "`data/gate-ledger.json` — never in prose here, which is how five",
        "different Gate 2M numbers came to circulate at once (gap J1).",
        "",
        markdown_table(counts),
        "",
        README_END,
    ])


def write_readme(path: Path, block: str) -> bool:
    """Replace the marked block in README.md. True if the file changed."""
    text = path.read_text()
    i, j = text.find(README_BEGIN), text.find(README_END)
    if i < 0 or j < 0:
        raise SystemExit(f"{path}: gate-table markers not found")
    new = text[:i] + block + text[j + len(README_END):]
    if new == text:
        return False
    path.write_text(new)
    return True


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    strict = "--strict" in argv          # CI: skipped gates are not acceptable
    # --suites-only: judge ONLY the pytest-backed gates. The pre-push hook uses
    # this so it blocks REGRESSIONS without blocking every push on gates that
    # are known, measured and recorded red. Making the hook unusable is how you
    # train people to --no-verify, which is worse than either.
    suites_only = "--suites-only" in argv
    if "--readme" in argv:
        block = readme_block(collect_counts())
        if "--write" in argv:
            changed = write_readme(_ROOT / "README.md", block)
            print("README.md rewritten" if changed else "README.md already current")
        else:
            print(block)
        return 0
    ledger_path = None
    for i, a in enumerate(argv):
        if a == "--ledger" and i + 1 < len(argv):
            ledger_path = argv[i + 1]
    ledger = load_ledger(ledger_path)
    today = date.today()

    failures = skipped_gates = red_gates = 0
    green_names: list[str] = []
    print(f"{'gate':13} {'scope':45} status")
    print("-" * 84)
    for g in GATES:
        if g.suite is None:
            if g.status == Verdict.RED:
                label, is_fail = judge_red(g.name, ledger, today)
                if not suites_only and is_fail:
                    red_gates += 1
            else:
                label = f"{g.status}-GATED — {g.detail}"
            print(f"{g.name:13} {g.scope:45} {label}")
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
        print(f"{g.name:13} {g.scope:45} {label}  ({tail})")

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
        print(f"\n{skipped_gates} gate(s) ran no tests — a missing optional "
              f"dependency, or an artefact this machine does not have (Gate 2G "
              f"needs data/benchmark_geom/kcs.stl; see "
              f"scripts/fetch_benchmark_geom.py). "
              f"{'FAILING (--strict).' if strict else 'Nothing was verified by them.'}")
    return 1 if (failures or red_gates or (strict and skipped_gates)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
