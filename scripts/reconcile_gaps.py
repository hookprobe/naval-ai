#!/usr/bin/env python3
"""Reconcile the gap queue against the CODE, repeatably.

WHY THIS EXISTS, AND WHAT IT MEASURES.

`navalai.gaps.import_gap_register()` seeded 119 findings from
`docs/GAP-REGISTER.md`, every one of them `Open`. That is the state of the
REGISTER DOCUMENT on 2026-08-05, not the state of the repository: the
2026-08-06 session closed a large fraction of them in code and nothing
propagated the closure, because the register is prose and prose does not
re-derive itself. That is section J's own diagnosis applied to section J's own
queue.

The obvious fix -- read the commit messages and mark the matching rows closed --
reproduces the defect this repository keeps measuring. `run-case.sh` printed
"3 of 3 layers" from the REQUESTED spec table on a mesh with ZERO layers, and
`gate2m.py` printed `VERDICT: PASS` on a DIVERGING grid family because
`gci <= 5.0` is true of -27%. A commit message is a claim of the same kind: a
statement about the code, written next to the code, which nothing re-checks.

So every row here carries a PREDICATE over the checkout instead. A gap is
CLOSED only when a named symbol, test or file demonstrably does the thing the
register says is missing; it is OPEN when the predicate is false, i.e. we
looked and it is still absent; and it is NEEDS-HUMAN when no predicate can be
written at all -- a process audit, a point-in-time observation of a working
tree -- which is reported as such rather than guessed at. Guessing is the
failure mode: a wrongly-CLOSED gap is far more expensive than a wrongly-OPEN
one, because it is the one that stops anyone looking.

The predicates are deliberately written the OTHER WAY ROUND from a test suite.
They do not assert; they answer. A predicate that is false today is not a
failure, it is an open gap with a machine-checkable clearing condition, and the
day someone lands the fix this script notices without being edited.

    python scripts/reconcile_gaps.py                # report only
    python scripts/reconcile_gaps.py --by-priority  # counts by severity
    python scripts/reconcile_gaps.py --apply        # move verified-closed gaps
                                                    # through the lifecycle
    python scripts/reconcile_gaps.py --diff         # rows whose queue state and
                                                    # measured state disagree

`--apply` walks Open -> Investigating -> Prototype -> Verified -> Closed one
legal step at a time (there is no shortcut edge and this script does not add
one), and the Verified note carries the evidence string, because
`GapQueue.advance` refuses a Verified with no measurement -- correctly.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from navalai.gaps import GapQueue, GapState, Severity   # noqa: E402


# ---------------------------------------------------------------------------
# predicate primitives
#
# Text and AST, no import of the module under test. Importing would make the
# reconciliation depend on the optional-dependency environment (capytaine,
# cadquery, mujoco), so a laptop without them would report gaps as open that
# are closed -- an environment fact masquerading as a project fact, which is
# the same category error as `status_of` calling an all-skipped suite GREEN.
# ---------------------------------------------------------------------------

_TEXT_CACHE: dict[tuple[str, str], str] = {}

# The tree the predicates read. Normally the checkout; `--require-committed`
# points it at a `git archive HEAD` export so a closure cannot rest on another
# agent's uncommitted edit. See `head_export()`.
_BASE = _ROOT


@contextmanager
def at_root(path: Path):
    """Run predicates against a different tree (see `head_export`)."""
    global _BASE
    prev, _BASE = _BASE, Path(path)
    try:
        yield
    finally:
        _BASE = prev


def text(rel: str) -> str:
    """File contents, or "" if absent. Absence is a legitimate answer here."""
    key = (str(_BASE), rel)
    if key not in _TEXT_CACHE:
        p = _BASE / rel
        _TEXT_CACHE[key] = p.read_text(encoding="utf-8") if p.is_file() else ""
    return _TEXT_CACHE[key]


def has(rel: str, pattern: str) -> bool:
    """Regex search, MULTILINE.

    MULTILINE by default because almost every question here is about a LINE --
    a `.gitignore` entry, an import, a shell guard. Without it, `^renders/`
    anchors at the start of the whole file and answers "not ignored" about a
    file that is ignored on line 25, which is a false OPEN: the direction that
    wastes a reader's time rather than the direction that hides a defect, but
    still a wrong answer from a predicate that looked right.
    """
    return re.search(pattern, text(rel), re.MULTILINE) is not None


def lacks(rel: str, pattern: str) -> bool:
    return not has(rel, pattern)


_CODE_CACHE: dict[tuple[str, str], str] = {}


def code(rel: str) -> str:
    """A Python file with its COMMENTS and DOCSTRINGS blanked out.

    THE INCIDENT, MEASURED HERE ON 2026-08-06, ON THIS SCRIPT'S FIRST RUN.
    Gap B4 is "payload_kg is a flat 800 kg regardless of crew". Its predicate
    asked, in part, `has("navalai/energy.py", "crew")` -- and energy.py line 19
    reads:

        payload_kg: float = 800.0          # crew + stores + water

    The word is in the COMMENT ON THE DEFECT ITSELF. The predicate returned
    True, the reconciler reported CLOSED, and `--apply` wrote B4 to Closed in
    an append-only log that HAS NO REOPEN EDGE. 332 transitions had to be
    unwound to take it back.

    That is precisely the failure this whole script was written to avoid, and
    it arrived by the same route as every other instance in this repository: a
    report that read the DESCRIPTION of a thing instead of the thing.
    `run-case.sh` read snappy's requested-spec table and printed "3 of 3
    layers" on a mesh with none. Here the description is even more treacherous,
    because the comments in this codebase are unusually good -- every fix
    quotes the defect it fixed, so the vocabulary of every OPEN gap is present,
    verbatim, in the file that would close it.

    So: a predicate about BEHAVIOUR reads `code()`, and only a predicate about
    PROSE (F19's attribution, J8's retraction, J7's supersession markers) reads
    `text()`. Both exist, and the choice is made per row.

    COMMENTS AND DOCSTRINGS, NOT ALL STRINGS. Blanking every string literal was
    the first attempt and it is too blunt: `"carries-target"`, `"length-hint"`
    and `"rules"` are requirement names and dict keys, i.e. code, and half the
    rows below identify a fix by one. The prose surface in this codebase is
    comments and docstrings; inline string literals are data.

    Blanking rather than deleting keeps byte offsets, so `before()` and any
    positional reasoning still line up with the original file.
    """
    key = (str(_BASE), rel)
    if key in _CODE_CACHE:
        return _CODE_CACHE[key]
    src = text(rel)
    if not rel.endswith(".py") or not src:
        _CODE_CACHE[key] = src
        return src
    import io
    import tokenize

    lines = src.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))
    out = list(src)

    def blank(r0: int, c0: int, r1: int, c1: int) -> None:
        if not (1 <= r0 <= len(lines) and 1 <= r1 <= len(lines)):
            return
        for i in range(offs[r0 - 1] + c0, min(offs[r1 - 1] + c1, len(out))):
            if out[i] != "\n":
                out[i] = " "

    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                blank(tok.start[0], tok.start[1], tok.end[0], tok.end[1])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass                       # a file mid-edit: keep what we have
    try:
        for node in ast.walk(ast.parse(src)):
            # A bare string EXPRESSION is a docstring or a block comment
            # pretending to be one. Either way it is prose.
            if (isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                v = node.value
                blank(v.lineno, v.col_offset,
                      v.end_lineno or v.lineno, v.end_col_offset or 0)
    except (SyntaxError, ValueError):
        pass
    _CODE_CACHE[key] = "".join(out)
    return _CODE_CACHE[key]


def has_code(rel: str, pattern: str) -> bool:
    """`has`, but comments and string literals cannot answer. See `code()`."""
    return re.search(pattern, code(rel), re.MULTILINE) is not None


def lacks_code(rel: str, pattern: str) -> bool:
    return not has_code(rel, pattern)


def exists(rel: str) -> bool:
    return (_BASE / rel).exists()


def defines(rel: str, symbol: str) -> bool:
    """Is `symbol` defined at any level of this module's AST?

    AST rather than `grep "def symbol"` so a name inside a docstring, a comment
    or a string literal cannot answer for the code. Several rows below turn on
    exactly that distinction: `navalai/gaps.py` and `docs/GAP-REGISTER.md` both
    QUOTE the missing symbols they are about.
    """
    src = text(rel)
    if not src:
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol:
                return True
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id == symbol:
                return True
    return False


def imports(rel: str, module: str, name: str | None = None) -> bool:
    """Does this module import `module` (optionally the symbol `name`)?"""
    src = text(rel)
    if not src:
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = ("." * (node.level or 0)) + (node.module or "")
            if mod.lstrip(".").endswith(module.lstrip(".")) or mod == module:
                if name is None or any(a.name == name for a in node.names):
                    return True
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.endswith(module) and name is None:
                    return True
    return False


def before(rel: str, first: str, second: str) -> bool:
    """Does `first` occur before `second` in this file?

    Order is load-bearing in `run-case.sh`: the concurrency guard sat AFTER
    `rm -rf constant/polyMesh`, so a refused run had already destroyed the mesh
    it was refusing to solve. A predicate that only asked "is the guard
    present?" would have passed on the broken version.
    """
    src = text(rel)
    a = re.search(first, src, re.MULTILINE)
    b = re.search(second, src, re.MULTILINE)
    return bool(a and b and a.start() < b.start())


def ledger_has(gate: str) -> bool:
    """Is `gate` still carried as expected-red in data/gate-ledger.json?

    The ledger is the executable record of which gates are red. For the two
    compute-bound CFD rows (F16, F17) it is the only honest closure signal
    available to a static check: the gap closes when the gate goes green and
    its entry is removed, which `test_gate_integrity` already enforces in both
    directions.
    """
    p = _BASE / "data" / "gate-ledger.json"
    if not p.is_file():
        return False
    try:
        return gate in json.loads(p.read_text())
    except (ValueError, OSError):
        return False


def any_nonzero_transverse_offset() -> bool:
    """Does any mass producer place an item off centreline?

    Gap E13: the `list` constraint occupies an NSGA-II dimension and reads
    -2.000 on every evaluation because nothing emits a transverse offset. The
    field exists; the producer does not.
    """
    for p in sorted((_BASE / "navalai").rglob("*.py")):
        rel = str(p.relative_to(_BASE))
        for m in re.finditer(r"y_m\s*=\s*([^,\)\n]+)", text(rel)):
            v = m.group(1).strip()
            if v not in ("0.0", "0", "0.0,"):
                return True
    return False


# ---------------------------------------------------------------------------
# the table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Check:
    """One register row and the machine-checkable question that closes it.

    `evidence` names the symbol, test or file that the predicate looks for, in
    the words a reader would need to go and look at it themselves. It is what
    lands in the gap's Verified note, so a closure in `gaps.jsonl` always says
    WHAT was measured -- `GapQueue.advance` refuses a Verified without one.
    """
    source_id: str
    evidence: str
    closed: Callable[[], bool]


# Rows for which NO predicate is honest. Recorded with the reason, never
# guessed. Two are process audits (a claim about commits, a claim about a
# working tree at one instant) and one asks whether dead code is REACHABLE,
# which is a measurement over the parameter space and not a property of the
# text.
NEEDS_HUMAN: dict[str, str] = {
    "J9": "a commit-compliance statistic ('7 of 10 recent commits comply') is "
          "a property of history at one instant, not of the checkout. Its "
          "actionable half IS done -- scripts/gate2m.py now has tests in "
          "tests/test_cfd_reference_parity.py -- but no predicate can re-run "
          "the audit that produced the ratio.",
    "J10": "'uncommitted CFD work sits in the working tree' describes a moment, "
           "not a state a checkout can be asked about. It is also true again "
           "right now for an unrelated reason (concurrent agents), which is "
           "precisely why it cannot be a predicate.",
    "A6b": "recorded as a CORRECTION to A6 rather than a defect of its own. "
           "Its substantive half -- the sigma test lacked RECALL on axes the "
           "kernel ignores -- is closed by the same code as A6 "
           "(surrogate._nn_distance, deliberately unweighted, plus "
           "tests/test_phase3.py::test_support_distance_catches_what_sigma_"
           "alone_misses). Whether a correction row is itself closeable is a "
           "judgement for a human, not a predicate.",
}


CHECKS: tuple[Check, ...] = (
    # -- A. the ladder is not a ladder -------------------------------------
    Check("A1", "navalai/evaluate.py::revalidate escalates to L2 and refuses "
                "L3 with TierRequiresOperator; tests/test_ladder.py "
                "(Gate R3) exercises it",
          lambda: defines("navalai/evaluate.py", "revalidate")
                  and has_code("navalai/evaluate.py", "TierRequiresOperator")
                  and defines("tests/test_ladder.py",
                              "test_revalidate_promotes_to_l2_and_records_it")),
    Check("A2", "navalai/evaluate.py imports navalai.rules (report, "
                "iso12215.assess, iso12217.assess) and 'rules' is a member of "
                "CONSTRAINT_NAMES, so a hull failing ISO 12215-5 is infeasible",
          lambda: imports("navalai/evaluate.py", ".rules")
                  and has_code("navalai/evaluate.py", r'"rules":')
                  and has_code("navalai/evaluate.py", r"CONSTRAINT_NAMES")),
    # NOT `lacks('ev.tier == "L1"')`: the string survives inside the comment
    # that RETRACTS it, so a naive absence test reports this gap open forever
    # for the crime of explaining itself. Ask for the monotone assertion and
    # for the escalation case the equality made unreachable.
    Check("A3", "tests/test_optimize.py asserts tier_rank(ev.tier) >= "
                "tier_rank('L1') instead of equality, and exercises the "
                "escalation the equality made unreachable",
          lambda: has_code("tests/test_optimize.py",
                      r'tier_rank\(ev\.tier\) >= tier_rank\("L1"\)')
                  and has_code("tests/test_optimize.py",
                          r'revalidate\(kept, m, "L2"\)')),
    Check("A4", "a NON-TEST caller of GP.predict_or_escalate / is_ood, i.e. "
                "something in the product that actually escalates",
          lambda: any(has(rel, r"predict_or_escalate|is_ood\(")
                      for rel in ("navalai/evaluate.py", "navalai/optimize.py",
                                  "navalai/agents.py", "ui/server.py",
                                  "navalai/flywheel.py"))),
    Check("A5", "navalai/export.py::refuse_unvalidated, called by export_step, "
                "export_iges and export_dxf",
          lambda: defines("navalai/export.py", "refuse_unvalidated")
                  and has_code("navalai/export.py", r"refuse_unvalidated\(ev,")
                  and has_code("navalai/unroll.py", r"refuse_unvalidated")),
    Check("A6", "surrogate.GP.support_distance + is_ood(support_frac=...), a "
                "support test rather than a bare sigma threshold; "
                "tests/test_phase3.py asserts kept/rejected error separation",
          lambda: defines("navalai/surrogate.py", "support_distance")
                  and has_code("navalai/surrogate.py", r"support_frac")
                  and has_code("tests/test_phase3.py", r"NO SEPARATION")),
    Check("A6c", "GP.fit no longer pins the ARD lengthscale bound at log(10.0), "
                "or reports the saturation it hits",
          lambda: lacks_code("navalai/surrogate.py",
                        r"np\.log\(1e-2\), np\.log\(10\.0\)")),

    # -- B. mission fidelity ------------------------------------------------
    Check("B1", "optimize.HullProblem clamps the LWL search bound to "
                "mission.lwl_hint_m, and translate.py carries a 'length-hint' "
                "Requirement graded against the delivered hull",
          lambda: has_code("navalai/optimize.py", r"mission\.lwl_hint_m")
                  and has_code("navalai/translate.py", r'"length-hint"')),
    Check("B2", "the 'carries-target' Requirement is TWO-SIDED (0.98x..1.10x "
                "of the mission target), so it can fail",
          lambda: has_code("navalai/translate.py", r'"carries-target"')
                  and has_code("navalai/translate.py",
                          r"<= 1\.10 \* m\.displacement_target_kg")),
    Check("B3", "mission.parse_mission strips a THOUSANDS separator before the "
                "decimal-comma replacement, so '6,000 kg' is not 6.000 kg",
          lambda: has_code("navalai/mission.py",
                      r"re\.sub\(r\"\(\?<=\\d\),\(\?=\\d\{3\}")),
    Check("B4", "the weight budget scales payload with mission.crew rather "
                "than carrying a flat 800 kg (limits.CREW_MASS_KG reaching "
                "energy.weight_budget / weight_items)",
          lambda: imports("navalai/energy.py", ".limits", "CREW_MASS_KG")
                  or has_code("navalai/energy.py", r"crew")),
    Check("B5", "something in the objective COSTS length (build cost, "
                "structural scaling, a mooring or lock limit) rather than the "
                "search running to the grammar ceiling",
          lambda: has_code("navalai/optimize.py",
                      r"length_cost|cost_per_m|LOCK_LIMIT|berth_limit")),
    Check("B6", "optimize.py aims GM at a BAND (limits.GM_OVER_BEAM_MAX) "
                "instead of maximising -GM",
          lambda: imports("navalai/optimize.py", ".limits", "GM_OVER_BEAM_MAX")
                  and has_code("navalai/optimize.py", r"gm_mid")),
    Check("B7", "resistance.FN_MICHELL_MAX + Rt.valid, reported by evaluate() "
                "as a violation naming the planing regime",
          lambda: has_code("navalai/resistance.py", r"FN_MICHELL_MAX")
                  and has_code("navalai/evaluate.py", r"FN_MICHELL_MAX")
                  and has_code("navalai/evaluate.py", r"planing regime")),
    Check("B8", "limits.LCB_BAND_PCT_LWL is an entry in the constraint vector",
          lambda: has_code("navalai/limits.py", r"LCB_BAND_PCT_LWL")
                  and has_code("navalai/evaluate.py", r'"lcb":')),
    Check("B9", "grammar.proportion_margins is the shared kernel and evaluate() "
                "re-checks it on the FLOATED state (hs.lwl_eff, hs.b_wl_max)",
          lambda: defines("navalai/grammar.py", "proportion_margins")
                  and has_code("navalai/evaluate.py",
                          r"proportion_margins\(hs\.lwl_eff")),

    # -- C. a number declared twice ----------------------------------------
    Check("C1", "rules.iso12215.select_stock_thickness_m DERIVES the bottom "
                "sheet from the rule, and evaluate() calls it",
          lambda: defines("navalai/rules/iso12215.py", "select_stock_thickness_m")
                  and has_code("navalai/evaluate.py",
                          r"select_stock_thickness_m\(mission\.")),
    Check("C2", "scripts/demo_mission.py passes ev.ply_thickness_m instead of a "
                "fourth, undeclared 20.0 mm",
          lambda: has_code("scripts/demo_mission.py", r"ev\.ply_thickness_m")
                  and lacks_code("scripts/demo_mission.py", r"provided_mm=20\.0")),
    Check("C3", "evaluate() passes the derived t_ply into BOTH weight_budget "
                "and weight_items, so structural mass runs on the same sheet",
          lambda: has_code("navalai/evaluate.py",
                      r"weight_budget\(p\[\"LWL\"\], p\[\"D\"\], shell, deck, "
                      r"mission\.energy, t_ply\)")
                  and has_code("navalai/evaluate.py", r"t_design, t_ply\)")),
    Check("C4", "the scantling rule is fed the FLOATED displacement "
                "(scantling_rules(hs.disp_kg, ...)), which is ISO's mLDC",
          lambda: has_code("navalai/evaluate.py", r"scantling_rules\(hs\.disp_kg")),
    Check("C5", "limits.FRAME_SPACING_M is the one panel span, imported by "
                "rules/iso12215.py AND by engineer.py",
          lambda: has_code("navalai/limits.py", r"FRAME_SPACING_M")
                  and imports("navalai/rules/iso12215.py", "limits", "FRAME_SPACING_M")
                  and imports("navalai/engineer.py", ".limits", "FRAME_SPACING_M")),
    Check("C6", "translate.py imports limits.FREEBOARD_FLOOR_M instead of "
                "keeping a private 0.25",
          lambda: imports("navalai/translate.py", ".limits", "FREEBOARD_FLOOR_M")
                  and lacks_code("navalai/translate.py", r">= 0\.25")),
    Check("C7", "energy.weight_budget builds its VCG from VCG_FRACTION rather "
                "than inlined literals fifteen lines above it",
          lambda: has_code("navalai/energy.py",
                      r"VCG_FRACTION\[name\] \* depth for name, m in masses")),
    Check("C8", "evaluate() calls limits.min_bend_radius_m(t_ply) instead of "
                "recomputing BEND_RADIUS_RATIO * PLY_THICKNESS_M inline",
          lambda: has_code("navalai/evaluate.py", r"min_bend_radius_m\(t_ply\)")
                  and lacks_code("navalai/evaluate.py",
                            r"BEND_RADIUS_RATIO \* PLY_THICKNESS_M")),
    Check("C9", "the undocumented x1.6 shell-area factor is replaced by the "
                "quantity that computes it exactly "
                "(wetted_surface(z_sheer.max()))",
          lambda: lacks_code("navalai/evaluate.py", r"wetted_surface\(0\.0\) \* 1\.6")),
    Check("C10", "limits.CREW_MASS_KG is the one person mass, imported by "
                 "rules/iso12217.py",
          lambda: has_code("navalai/limits.py", r"CREW_MASS_KG")
                  and imports("navalai/rules/iso12217.py", "limits", "CREW_MASS_KG")),
    Check("C11", "scripts/gate2m.py defines no gci() of its own and delegates "
                 "to navalai.cfd.post.gci; a test pins it",
          lambda: lacks_code("scripts/gate2m.py", r"^def gci\(")
                  and has_code("scripts/gate2m.py", r"post\.gci\(")
                  and defines("tests/test_cfd_reference_parity.py",
                              "test_gate2m_has_no_gci_of_its_own")),
    Check("C12", "engineer.WASTE_FACTOR is gone and the sheet count is COUNTED "
                 "off the nested layout",
          lambda: lacks_code("navalai/engineer.py", r"WASTE_FACTOR")
                  and defines("tests/test_manufacturing.py",
                              "test_ply_sheets_is_counted_off_the_layout")),

    # -- D. gates that cannot fail -----------------------------------------
    Check("D1", "gates.Verdict is a typed status, Gate.__post_init__ rejects "
                "anything else, and Gate 0G "
                "(tests/test_gate_integrity.py) pins the GATES list",
          lambda: defines("navalai/gates.py", "Verdict")
                  and has_code("navalai/gates.py", r"is not a Verdict")
                  and defines("tests/test_gate_integrity.py",
                              "test_a_status_cannot_be_renamed_into_passing")),
    Check("D2", "status_of() treats xfail/xpass as failures, and a test pins it",
          lambda: has_code("navalai/gates.py", r"xfailed")
                  and defines("tests/test_gate_integrity.py",
                              "test_xfail_and_xpass_are_failures_not_decorations")),
    Check("D3", "data/baselines.json is committed, and a missing baseline is a "
                "FileNotFoundError refusal rather than an automatic pass",
          lambda: exists("data/baselines.json")
                  and has_code("navalai/flywheel.py",
                          r"raise FileNotFoundError")
                  and has_code("navalai/flywheel.py", r"bootstrap")),
    Check("D4", "flywheel keeps a MONOTONE high-water mark "
                "(best_median_rel_err / best_coverage_2sigma) plus absolute "
                "HARD floors, so the gate is not a ratchet",
          lambda: has_code("navalai/flywheel.py", r"best_median_rel_err")
                  and has_code("navalai/flywheel.py", r"HARD_MIN_COVERAGE_2SIGMA")),
    Check("D5", "flywheel.frozen_suite is not the training draw and "
                "harvest(exclude_heldout=True) keeps the held-out arm held out",
          lambda: defines("navalai/flywheel.py", "frozen_suite")
                  and defines("navalai/flywheel.py", "in_heldout_region")
                  and has_code("navalai/flywheel.py", r"exclude_heldout")),
    Check("D6", "gate2m requires within_band AND gci_is_converged, so the "
                "grid's own uncertainty cannot buy the overlap",
          lambda: defines("scripts/gate2m.py", "gci_is_converged")
                  and has_code("scripts/gate2m.py", r"inside = within_band and converged")),
    Check("D7", "gate2m returns 3 (inconclusive), not 0, from the branch that "
                "prints 'cannot close the gate on its own'",
          lambda: has_code("scripts/gate2m.py",
                           r"cannot close the gate on its own")
                  and has_code("scripts/gate2m.py", r"^        return 3$")),
    Check("D8", "review.is_complete requires a DATED edition per standard, and "
                "edition_defects() names the reasons",
          lambda: defines("navalai/rules/review.py", "edition_defects")
                  and has_code("navalai/rules/review.py", r"editions")
                  and ledger_has("Gate 6R")),
    Check("D9", "reference designs + hand calculations exist, so Gate 6R's "
                "threshold parity could become Gate 6's VERDICT parity",
          lambda: has_code("navalai/rules/review.py",
                      r"REFERENCE_DESIGNS|hand_calculation")),
    Check("D10", "Gate 3's error bar is measured across seeds rather than on "
                 "its one chosen seed (991)",
          lambda: has_code("tests/test_phase3.py",
                      r"parametrize\(\s*\"seed\"|for seed in range\(\d+\).*rel")),
    Check("D11", "the >=99% raw-feasibility clause is recorded where a gate can "
                 "FAIL on it (a ledger row), not only in a prose scope string",
          lambda: ledger_has("Gate 4")),
    Check("D12", "generative._conditioned draws DISJOINT candidate batches "
                 "against a reference cut, and the Gate 4 suite has a control",
          lambda: defines("navalai/generative.py", "_conditioned")
                  and has_code("navalai/generative.py",
                               r"cand = sampler\(batch, s\)")
                  and defines(
                      "tests/test_phase4.py",
                      "test_percentile_is_a_strictness_knob_and_the_docstring_"
                      "now_says_so")),
    Check("D13", "counts() anchors on the pytest TIMING clause as well as the "
                 "count, so stdout cannot spoof a summary line",
          lambda: has_code("navalai/gates.py", r"_SUMMARY_TAIL")
                  and defines("tests/test_gate_integrity.py",
                              "test_stdout_cannot_spoof_the_summary_line")),
    Check("D14", ".github/workflows/gates.yml judges against "
                 "data/gate-ledger.json, so the required check is a variable "
                 "and not a constant red",
          lambda: has(".github/workflows/gates.yml",
                      r"--ledger data/gate-ledger\.json")
                  and defines("navalai/gates.py", "judge_red")),
    # NEGATIVE CONTROL FAILURE, caught by re-running the predicates against
    # 5bbffb7 (the commit the register audited). Both of these reported CLOSED
    # THERE. gates.yml already `cat`-ed requirements-optional.txt and already
    # said the word "--strict" -- in a comment reading "Deliberately NOT
    # --strict here". A predicate that a file satisfies by DISCUSSING the fix
    # is the B4 defect with a different file extension. The anchors are now the
    # install step and the run step.
    Check("D15", "gates.yml has a full-tiers job that INSTALLS "
                 "requirements-optional.txt and RUNS the ladder with --strict",
          lambda: has(".github/workflows/gates.yml",
                      r"pip install -r requirements-optional\.txt")
                  and has(".github/workflows/gates.yml",
                          r"python -m navalai\.gates[^\n]*--strict")),
    Check("D16", "the ladder's pytest invocation passes no -x at all, so the "
                 "printed tail does not understate the damage",
          lambda: lacks_code("navalai/gates.py", r'"-x"')),

    # -- E. physics validity ------------------------------------------------
    Check("E1", "navalai/holtrop.py exists with benchmarks/holtrop_cases.py, "
                "and Gate 1H owns tests/test_holtrop.py",
          lambda: exists("navalai/holtrop.py")
                  and exists("benchmarks/holtrop_cases.py")
                  and has_code("navalai/gates.py", r'Gate\("Gate 1H"')),
    Check("E1b", "Holtrop-Mennen is wired into evaluate() (or an explicit "
                 "envelope guard routes small craft away from it there)",
          lambda: imports("navalai/evaluate.py", "holtrop")),
    Check("E2", "benchmarks/wigley.py carries an INDEPENDENT reference curve, "
                "not a frozen copy of our own output labelled as a regression "
                "anchor",
          lambda: has("benchmarks/wigley.py", r"REFERENCE_CW")
                  and lacks("benchmarks/wigley.py",
                            r"not an independent validation")),
    Check("E3", "evaluate() declares the unaccounted mass as a positioned "
                "MassItem with a 50% sigma, so the mass model sums to the "
                "displacement it floats at",
          lambda: has_code("navalai/evaluate.py", r'id="unaccounted"')
                  and has_code("navalai/evaluate.py", r"unaccounted_frac")),
    Check("E4", "the four tautological constraints are DELETED from "
                "grammar.check and the honest live count is pinned by "
                "tests/test_constraints_honest.py",
          lambda: lacks_code("navalai/grammar.py", r'_rel\("keel\.rocker"')
                  and lacks_code("navalai/grammar.py", r'_rel\("flare\.fold"')
                  and has_code("tests/test_constraints_honest.py",
                               r"the live relational count moved to")),
    Check("E5", "a round-trip of 12+ KNOWN (public-CAD) hulls exists, not just "
                "vector(named(x)) on one hand-picked vector",
          lambda: has_code("tests/test_phase0.py",
                      r"known_hulls|PUBLIC_HULLS|reference_hulls")),
    Check("E6", "grammar.check uses the honest max-twist metric "
                "(Hull.panel_twist_rate) rather than the mean-twist proxy",
          lambda: has_code("navalai/grammar.py", r"panel_twist_rate")),
    Check("E7", "form_factor is fed a consistent state and no longer rides its "
                "0.45 clamp silently",
          lambda: lacks_code("navalai/resistance.py", r"np\.clip\(k, 0\.0, 0\.45\)")),
    Check("E8", "Michell runs the grid it was converged on (a named production "
                "grid, not a default the convergence test never exercises)",
          lambda: has_code("navalai/resistance.py",
                      r"CONVERGED_GRID|PRODUCTION_GRID|grid_converged")),
    Check("E9", "db.add_hull stores the SAME canonical rounded params it "
                "hashes, so two vectors differing by 1e-11 cannot collide",
          lambda: has_code("navalai/db.py",
                      r"add_hull.*\n(.|\n)*?round\(float\(v\), 10\)")),
    Check("E10", "evaluate.is_real_finite turns a non-finite constraint into a "
                 "violation and INFEASIBLE_G, instead of nan > 0.0 being False",
          lambda: defines("navalai/evaluate.py", "is_real_finite")
                  and has_code("navalai/evaluate.py", r"if not is_real_finite\(v\)")),
    Check("E10b", "holtrop.domain_errors() names each impossibility in words "
                  "and total() refuses, so a COMPLEX resistance cannot land in "
                  "a float field",
          lambda: defines("navalai/holtrop.py", "domain_errors")),
    Check("E11", "trim and heel return None where the equilibrium stops "
                 "existing, and the constraint takes INFEASIBLE_G",
          lambda: has_code("navalai/evaluate.py", r"INFEASIBLE_G if trim is None")
                  and has_code("navalai/evaluate.py", r"INFEASIBLE_G if heel is None")),
    Check("E12", "mission.FIELD_RANGES is the one range table and "
                 "MissionSpec.clamp() runs from __post_init__ AND after setattr, "
                 "so parse_mission and ui/server are bounded too",
          lambda: defines("navalai/mission.py", "FIELD_RANGES")
                  and has_code("navalai/mission.py", r"def clamp")
                  and has_code("navalai/mission.py", r"self\.clamp\(\)")),
    Check("E13", "some producer emits a non-zero transverse offset, so the "
                 "'list' constraint carries information",
          any_nonzero_transverse_offset),
    Check("E14", "solve_to_displacement flags or refuses non-convergence "
                 "instead of returning the midpoint after 80 iterations",
          lambda: has_code("navalai/hydrostatics.py",
                      r"did not converge|converged=|ConvergenceError")),
    Check("E15", "translate.grade distinguishes a BROKEN CHECKER from a failed "
                 "design rather than swallowing both in `except Exception`",
          lambda: has_code("navalai/translate.py", r"checker error|CheckerError")),
    Check("E16", "the constraint vector is BUILT from CONSTRAINT_NAMES "
                 "(constraint_vector + ConstraintOrderError), not bound by an "
                 "assert that python -O strips",
          lambda: defines("navalai/evaluate.py", "constraint_vector")
                  and defines("navalai/evaluate.py", "ConstraintOrderError")),
    Check("E17", "NU_WATER is re-derived from rho, wetted_surface accounts for "
                 "longitudinal slope, and offsets_grid includes z = wl",
          lambda: lacks_code("navalai/geometry.py",
                        r"np\.linspace\(1\.0, 0\.0, nz, endpoint=False\)")),
    Check("E18", "no AST node validator is dead (none returns [] "
                 "unconditionally)",
          lambda: text("navalai/hull_ast.py").count("        return []") == 0),

    # -- F. L2 / L3 ---------------------------------------------------------
    Check("F1", "an added-resistance-in-waves routine exists in seakeeping.py "
                "(drift force, heading sweep, Case 2.10 data)",
          lambda: has_code("navalai/seakeeping.py",
                      r"added_resistance|drift_force|heading_sweep")),
    Check("F2", "the BEM solver is constructed with an EXPLICIT method rather "
                "than cpt.BEMSolver() taking the indirect default",
          lambda: has_code("navalai/seakeeping.py", r"BEMSolver\(\s*\w")),
    Check("F3", "the Green-function grid is PINNED rather than correct only "
                "because the library defaults to it",
          lambda: has_code("navalai/seakeeping.py", r"676|Delhommeau\(\s*\w")),
    Check("F4", "SeakeepingResult is actually constructed somewhere, so the "
                "only L2 type carrying uncertainty_rel is not decoration",
          lambda: any(has(rel, r"SeakeepingResult\(")
                      for rel in ("navalai/seakeeping.py", "navalai/evaluate.py",
                                  "ui/server.py", "navalai/agents.py"))),
    Check("F5", "waves.heave_response transforms to ENCOUNTER frequency at "
                "forward speed",
          lambda: has_code("navalai/waves.py", r"encounter|omega_e")),
    Check("F6", "gate2m reports trim in EFD's convention (negative = bow down) "
                "-- the sign the check exists to catch",
          lambda: has_code("scripts/gate2m.py",
                      r"return -math\.degrees\(math\.asin")),
    Check("F7", "case.py raises nLimiterIter off the starved 3 (the named "
                "cause of the timestep-1 divergence) and run_campaign.sh exits "
                "4 on two attempts with no progress, so a crash is not a nap",
          lambda: has_code("navalai/cfd/case.py", r"nLimiterIter [5-9]|nLimiterIter 1\d")
                  and has("scripts/run_campaign.sh", r"exit 4")),
    Check("F8", "the symmetric half-domain doubling is decided in ONE place "
                "(navalai.cfd.post.is_symmetric, applied by settled_drag) that "
                "the post_gci path reads, instead of only gate2m doubling",
          lambda: (defines("navalai/cfd/post.py", "is_symmetric")
                   and has_code("navalai/cfd/post.py",
                           r"factor = 2\.0 if is_symmetric\(case\)"))
                  or defines("scripts/post_gci.py", "_is_symmetric")),
    Check("F9", "post.gci falls back to Roache's Fs=3.0 below first order "
                "instead of clamping p up and SHRINKING the uncertainty",
          lambda: has_code("navalai/cfd/post.py", r"Fs=3\.0")
                  and has_code("navalai/cfd/post.py", r"NOT asymptotic")),
    Check("F10", "run-case.sh makes setFields FATAL and gives checkMesh real "
                 "thresholds (zero-volume, wrong-orientation, skewness)",
          lambda: has("navalai/cfd/run-case.sh", r"FATAL: setFields failed")
                  and has("navalai/cfd/run-case.sh", r"_MQ_ZEROVOL")
                  and has("navalai/cfd/run-case.sh", r"_MQ_SKEW")),
    Check("F11", "the concurrency guard runs BEFORE the mesh is destroyed and "
                 "rebuilt, and MESH_ONLY sweeps are exempt",
          # The anchor is the GUARD ITSELF, not the message: run-case.sh's
          # header comment quotes both "already running" and
          # "rm -rf constant/polyMesh" while explaining the old order, so a
          # prose-matching `before` compares two comments and answers about a
          # file it has not looked at.
          lambda: before("navalai/cfd/run-case.sh",
                         r'if \[ "\$\{MESH_ONLY:-0\}" != "1" \] && solve_running',
                         r"^rm -rf constant/polyMesh")),
    Check("F12", "post.stl_waterplane_properties gives the true I_L, so pitch "
                 "stiffness is rho*g*I_L and not Awp*(L/2)^2",
          lambda: defines("navalai/cfd/post.py", "stl_waterplane_properties")
                  and has_code("navalai/cfd/post.py", r"i_l|I_L|k_theta")
                  and has_code("navalai/cfd/case.py",
                               r"stl_waterplane_properties|awp=")),
    Check("F13", "case.py WARNS when VCG falls back to VCB, instead of "
                 "silently answering a different ship",
          lambda: has_code("navalai/cfd/case.py", r"warnings\.warn\(\s*\n?\s*\"no kg_above_keel")),
    Check("F14", "regenerating a FIXED case removes dynamicMeshDict and "
                 "pointDisplacement, so it stops moving",
          lambda: has_code("navalai/cfd/case.py",
                      r'\(cons / "dynamicMeshDict"\)\.unlink\(missing_ok=True\)')),
    Check("F15", "correctPhi and the setFields boxToFace block are GATED on "
                 "free_motion, so a regenerated fixed case is the recorded "
                 "configuration",
          lambda: has_code("navalai/cfd/case.py",
                      r'correct_phi="correctPhi yes; " if free_motion else ""')
                  and has_code("navalai/cfd/case.py",
                          r"SET_FIELDS_BOX_TO_FACE if free_motion else")),
    # `not ledger_has(...)` alone is true when there is NO LEDGER, which is
    # exactly the state at 5bbffb7 -- so both of these read CLOSED at the
    # audited commit, from a file that had not been written yet. An absent
    # record is not a green gate; it is gap D3's shape ("prior is None -> ok =
    # True"). The ledger must EXIST and not carry the row.
    Check("F16", "Gate 2M is no longer carried as expected-red in an existing "
                 "ledger, i.e. a SETTLED triplet exists and its GCI is computed",
          lambda: exists("data/gate-ledger.json") and not ledger_has("Gate 2M")),
    Check("F17", "Gate 2U is no longer carried as expected-red in an existing "
                 "ledger, i.e. the 'converges' half has a number "
                 "(mesh_robustness.py --solve)",
          lambda: exists("data/gate-ledger.json") and not ledger_has("Gate 2U")),
    Check("F18", "benchmarks/kcs.py records the re-measured -0.267% "
                 "displacement error, not the superseded -0.09%",
          lambda: has_code("benchmarks/kcs.py", r'"displacement_error_pct": -0\.267')),
    # The old "13 groups" string still occurs in kcs.py -- inside the sentence
    # that RETRACTS it. `lacks("13 independent CFD groups")` would therefore
    # report this gap open forever, punishing the file for recording its own
    # correction, which PLM section 3 step 7 requires it to do. The predicate
    # asks for the corrected attribution and for the band to be DERIVED from
    # the rows, which is what makes seven the number that can change.
    Check("F19", "the scatter band is attributed to the SEVEN rows actually "
                 "transcribed in SUBMITTED_CT_FINEST and derived from them",
          lambda: has("benchmarks/kcs.py", r"SEVEN groups")
                  and has("benchmarks/kcs.py",
                          r"min/max over these seven rows")),

    # -- G. manufacturing and rules ----------------------------------------
    Check("G1", "export_dxf emits a HEADER section with $INSUNITS 4 and scales "
                "by 1000, so a shop does not cut a 10 mm part instead of a "
                "10 m one",
          lambda: has_code("navalai/unroll.py", r'"\$INSUNITS"')
                  and has_code("navalai/unroll.py",
                               r"scale = 1000\.0 if units_mm else 1\.0")),
    Check("G2", "there is real nesting: MaxRects packing with rotation, sheet "
                "boundaries, and scarph splitting of oversized panels",
          lambda: defines("navalai/unroll.py", "nest")
                  and has_code("navalai/unroll.py", r"scarph")
                  and defines("tests/test_manufacturing.py",
                              "test_every_placed_part_is_inside_its_sheet_and_overlaps_nothing")),
    Check("G3", "engineer.BomLine gives line items, part list and per-sheet "
                "assignment instead of three aggregate scalars",
          lambda: defines("navalai/engineer.py", "BomLine")
                  and defines("tests/test_manufacturing.py",
                              "test_bom_has_line_items_and_reconciles_with_the_layout")),
    Check("G4", "unroll.refold maps 2-D back to 3-D and refold_deviation_mm "
                "measures the error the plan's clause is about",
          lambda: defines("navalai/unroll.py", "refold")
                  and defines("navalai/unroll.py", "refold_deviation_mm")),
    Check("G5", "developability is judged by the RULING twist test with a "
                "hyperbolic-paraboloid negative control, not by a chord "
                "residual that any smooth surface passes",
          lambda: defines("navalai/unroll.py", "ruling_twist")
                  and defines("tests/test_manufacturing.py",
                              "test_hypar_negative_control_fails_developability")
                  and defines("tests/test_manufacturing.py",
                              "test_true_developables_have_zero_ruling_twist")),
    Check("G6", "export lofts the VALIDATED discretisation (n_stations defaults "
                "to hull.n_stations) and writes an export_receipt",
          lambda: defines("navalai/export.py", "export_receipt")
                  and has_code("navalai/export.py",
                          r"n_stations = hull\.n_stations if n_stations is None")),
    Check("G7", "ES-TRIN exists as executable checkers -- the Solar Liveaboard "
                "(Danube) SKU requires it",
          lambda: any(has(str(p.relative_to(_BASE)), r"(?i)es-?trin")
                      for p in sorted((_BASE / "navalai" / "rules").glob("*.py")))),
    Check("G8", "ISO 12217-3 is implemented, or a SCOPE GUARD stops sub-6 m "
                "hulls being assessed by 12217-1, which does not govern them",
          lambda: has_code("navalai/rules/iso12217.py", r"12217-3")
                  or exists("navalai/rules/iso12217_3.py")),

    # -- H. uncertainty -----------------------------------------------------
    Check("H1", "no badge sigma is a bare declared fraction of its own value "
                "(the Wh/NM 0.30x is the last one)",
          lambda: lacks_code("navalai/evaluate.py", r"en\.wh_per_nm \* 0\.30")),
    Check("H2", "the mass model's real sigma reaches Evaluation, and KG "
                "uncertainty reaches GM",
          lambda: has_code("navalai/evaluate.py",
                      r'"displacement": \("L1", agg\.sigma_kg')
                  and has_code("navalai/evaluate.py", r'"GM": \("L1", agg\.sigma_kg')),
    Check("H3", "ui/server.py badges every served quantity through _q(value, "
                "tier, sigma, basis) instead of bare floats",
          lambda: defines("ui/server.py", "_q")
                  and has_code("ui/server.py", r'"basis"')
                  and has_code("ui/server.py", r"it\.sigma_kg")),

    # -- I. learning spine --------------------------------------------------
    Check("I1", "co-kriging is fitted from REAL high-fidelity provenance rows "
                "(a tier above L1) rather than the synthetic Forrester pair",
          lambda: has_code("navalai/flywheel.py", r"CoKriging")
                  or has_code("navalai/db.py", r'training_matrix\(.*"L2"')),
    Check("I2", "rho is selected by the KOH likelihood (_koh_nll) rather than "
                "an absolute LOO-RMSE that tracks |delta| scale",
          lambda: defines("navalai/surrogate.py", "_koh_nll")
                  and has_code("navalai/surrogate.py", r"RhoDegenerate")),
    Check("I3", "CoKriging.is_ood consults the LF GP as well as the delta GP",
          lambda: has_code("navalai/surrogate.py",
                      r"self\.gp_lo\.is_ood\(X, sigma_frac, support_frac\)")),
    Check("I4", "batch_infill normalises by the CANDIDATE box (bounds=) and "
                "raises InfillStarved rather than silently returning fewer",
          lambda: defines("navalai/surrogate.py", "InfillStarved")
                  and has_code("navalai/surrogate.py", r"bounds: tuple \| None")),
    Check("I5", "a calibration metric exists beyond the single coverage "
                "assertion that accepts 75% of a 2-sigma band",
          lambda: has_code("navalai/surrogate.py",
                      r"def calibration|def coverage_curve|def pit_")),
    Check("I6", "the GMM EM has a convergence check, starved-component "
                "reseeding/pruning and a scale-aware covariance floor",
          lambda: has_code("navalai/generative.py",
                           r"converged = True")
                  and has_code("navalai/generative.py", r"reseed_count\[j\] \+= 1")
                  # the SCALE-AWARE floor is the one that bites: a flat 1e-6*I
                  # on parameters spanning LWL [4,20] and rocker [0,0.6] was
                  # already rank-deficient at the shipped default.
                  and has_code("navalai/generative.py",
                               r"floor = reg \* np\.diag")
                  and has_code("navalai/generative.py",
                               r"_em\(X, k, iters, seed \+ r")),
    Check("I7", "from_latent REPORTS when it returned the anchor "
                "(DecodeInfo.anchor_rate) and bisects toward the feasible "
                "boundary instead of silently handing back a training hull",
          lambda: defines("navalai/generative.py", "DecodeInfo")
                  and has_code("navalai/generative.py", r"def anchor_rate")
                  and has_code("navalai/generative.py", r"n_bisect")),
    Check("I8", "HullGenerator is a Protocol with a SECOND implementation "
                "(PPCAGenerator) behind it, so the diffusion slot is an "
                "interface and not a description of one class",
          lambda: has_code("navalai/generative.py", r"class HullGenerator\(Protocol\)")
                  and defines("navalai/generative.py", "PPCAGenerator")
                  and defines("navalai/generative.py", "make_generator")),
    Check("I9", "every interactive endpoint is measured against the p95 bar, "
                "not just /eval, and ui/server prefits at serve()",
          lambda: defines("ui/server.py", "prefit")
                  and defines("tests/test_phase4.py",
                              "test_every_interactive_endpoint_meets_the_p95_bar_not_just_eval")),
    Check("I10", "Gate 7 clause 2 is implemented: flywheel.cycle_time measures "
                 "mission -> validated hull and wall clock is gated against a "
                 "monotone best",
          lambda: defines("navalai/flywheel.py", "cycle_time")
                  and has_code("navalai/flywheel.py", r"best_wall_clock_s")),
    Check("I11", "the frozen benchmark is built from benchmarks/ plus a "
                 "held-out design-space wedge, not sample_valid(25, seed=4242)",
          lambda: has_code("navalai/flywheel.py", r"from benchmarks\.")
                  and defines("navalai/flywheel.py", "benchmark_integrity")),
    Check("I12", "flywheel.transform_for routes a signed quantity away from "
                 "np.log, so 'gm' does not produce NaNs",
          lambda: defines("navalai/flywheel.py", "transform_for")
                  and defines("navalai/flywheel.py", "Transform")),
    Check("I13", "Gate 4 clause 3 has an artifact: a recorded non-expert "
                 "session producing a hull that passes the full ladder",
          lambda: has_code("tests/test_phase4.py", r"non-expert|unassisted")),
    Check("I14", "the surrogate spine has a CONSUMER: ui/server imports "
                 "surrogate or flywheel",
          lambda: imports("ui/server.py", "surrogate")
                  or imports("ui/server.py", "flywheel")),

    # -- J. documentation, process, reproducibility -------------------------
    Check("J1", "data/gate-ledger.json is the ONLY home of a Gate 2M "
                "measurement, enforced by "
                "test_no_document_restates_a_gate_2m_figure",
          lambda: exists("data/gate-ledger.json")
                  and defines("tests/test_gate_integrity.py",
                              "test_no_document_restates_a_gate_2m_figure")),
    Check("J2", "README's gate table is GENERATED by gates.readme_block() and "
                "a test fails when file and runner disagree; all six honesty "
                "rules are present",
          lambda: defines("navalai/gates.py", "readme_block")
                  and has("README.md", r"BEGIN GATE TABLE")
                  and defines("tests/test_gate_integrity.py",
                              "test_the_readme_carries_all_six_honesty_rules")),
    Check("J3", "Gate 6R's state is single-sourced: the RED row and the ledger "
                "entry agree, and the README table is regenerated from the "
                "runner rather than hand-edited",
          lambda: has_code("navalai/gates.py",
                      r'Gate\("Gate 6R", .*\n?\s*status=Verdict\.RED')
                  and ledger_has("Gate 6R")
                  and defines("tests/test_gate_integrity.py",
                              "test_the_readme_gate_table_agrees_with_the_runner")),
    Check("J4", "requirements.txt is PINNED with lower and upper bounds, so a "
                "numeric bar can tell a regression from a minor bump",
          lambda: all(re.search(r">=.*,<", line)
                      for line in text("requirements.txt").splitlines()
                      if line.strip() and not line.startswith("#"))
                  and text("requirements.txt").strip() != ""),
    Check("J5", "data/benchmark_geom/CHECKSUMS.json is committed with "
                "scripts/fetch_benchmark_geom.py, and Gate 2G makes the skip "
                "LOUD",
          lambda: exists("data/benchmark_geom/CHECKSUMS.json")
                  and exists("scripts/fetch_benchmark_geom.py")
                  and has_code("navalai/gates.py", r'Gate\("Gate 2G"')),
    Check("J6", "renders/ and data/exports/ are gitignored build artifacts, "
                "not tracked files re-modified by every test run",
          lambda: has(".gitignore", r"^renders/")
                  and has(".gitignore", r"^data/exports/")),
    Check("J7", "ALIGNMENT.md's superseded findings are struck through WITH "
                "the superseding measurement beside them (PLM section 3 step 7)",
          lambda: has("ALIGNMENT.md", r"SUPERSEDED")
                  and has("ALIGNMENT.md", r"~~")),
    # Same shape as F19: MACBOOK.md still contains "93 passed, 14 GREEN gates"
    # because it now says the file PROMISED that "long after both had moved".
    # A retraction is not a restatement.
    Check("J8", "MACBOOK.md asserts no test or gate count of its own, records "
                "the retraction of the old one, and points at the runner",
          lambda: has("MACBOOK.md",
                      r'promised "93 passed, 14 GREEN gates" long after')
                  and has("MACBOOK.md", r"navalai\.gates")),
)


# ---------------------------------------------------------------------------
# running it
# ---------------------------------------------------------------------------

CLOSED, OPEN, NEEDS = "CLOSED", "OPEN", "NEEDS-HUMAN"


@dataclass(frozen=True)
class Row:
    source_id: str
    verdict: str
    evidence: str


def reconcile() -> list[Row]:
    """One row per register finding, worst case first in file order.

    Every source_id in the queue must appear here exactly once, and nothing may
    appear that is not in the queue -- `tests/test_reconcile_gaps.py` pins both
    directions. A reconciliation that silently skips rows reports a smaller
    register than the one on disk, which is the defect `_split_row` already
    learned in `navalai/gaps.py`.
    """
    rows: list[Row] = []
    for chk in CHECKS:
        try:
            ok = bool(chk.closed())
        except Exception as e:                       # a broken predicate is not
            rows.append(Row(chk.source_id, NEEDS,    # a closed gap
                            f"predicate raised {type(e).__name__}: {e}"))
            continue
        rows.append(Row(chk.source_id, CLOSED if ok else OPEN, chk.evidence))
    for sid, why in NEEDS_HUMAN.items():
        rows.append(Row(sid, NEEDS, why))
    return rows


@contextmanager
def head_export():
    """`git archive HEAD` into a scratch tree, for a COMMITTED-only reading.

    THE INCIDENT: this script was written while three other agents worked in
    the same tree, and it measured gap A4 ("is_ood has two call sites, both in
    tests -- nothing escalates") as CLOSED. It was correct about the file on
    disk: `flywheel.py` had grown a `predict_or_escalate` caller minutes
    earlier. It was UNCOMMITTED, in another agent's file, and could still have
    been reverted -- so closing A4 on it would have recorded a closure whose
    evidence might never exist, in an APPEND-ONLY log with no reopen edge. That
    is the expensive direction: a wrongly-closed gap stops anyone looking.

    So `--apply` closes only what is CLOSED against HEAD as well. Work in
    flight is reported, by name, as exactly that. `git archive` is used rather
    than `git stash` or `git checkout` for the reason CLAUDE.md gives: a stash
    in this repository once swept up three concurrent agents' uncommitted work.
    """
    import subprocess
    import tarfile
    import tempfile

    with tempfile.TemporaryDirectory(prefix="navalai-head-") as tmp:
        tar = Path(tmp) / "head.tar"
        with tar.open("wb") as fh:
            subprocess.run(["git", "archive", "HEAD"], cwd=_ROOT, stdout=fh,
                           check=True)
        dest = Path(tmp) / "tree"
        dest.mkdir()
        with tarfile.open(tar) as t:
            t.extractall(dest, filter="data")
        yield dest


def _queue_index(queue: GapQueue) -> dict[str, object]:
    return {g.source_id: g for g in queue.all() if g.source_id}


def report(rows: list[Row], queue: GapQueue, by_priority: bool = False,
           diff_only: bool = False) -> None:
    idx = _queue_index(queue)
    print(f"{'row':6} {'severity':9} {'measured':11} {'queue':14} evidence")
    print("-" * 100)
    for r in rows:
        gap = idx.get(r.source_id)
        sev = gap.severity.value if gap else "?"
        state = gap.state.value if gap else "NOT IN QUEUE"
        agree = ((r.verdict == CLOSED and state == GapState.CLOSED.value)
                 or (r.verdict != CLOSED and state != GapState.CLOSED.value))
        if diff_only and agree:
            continue
        print(f"{r.source_id:6} {sev:9} {r.verdict:11} {state:14} "
              f"{r.evidence[:120]}")

    print()
    if by_priority:
        order = [Severity.CRITICAL, Severity.HIGH, Severity.MED, Severity.LOW]
        print(f"{'severity':10} {'closed':>7} {'open':>6} {'needs-human':>12} {'total':>6}")
        print("-" * 46)
        tot = {v: 0 for v in (CLOSED, OPEN, NEEDS)}
        for sev in order:
            c = {v: 0 for v in (CLOSED, OPEN, NEEDS)}
            for r in rows:
                gap = idx.get(r.source_id)
                if gap and gap.severity is sev:
                    c[r.verdict] += 1
                    tot[r.verdict] += 1
            print(f"{sev.value:10} {c[CLOSED]:7} {c[OPEN]:6} {c[NEEDS]:12} "
                  f"{sum(c.values()):6}")
        print("-" * 46)
        print(f"{'TOTAL':10} {tot[CLOSED]:7} {tot[OPEN]:6} {tot[NEEDS]:12} "
              f"{sum(tot.values()):6}")
    else:
        n = {v: sum(1 for r in rows if r.verdict == v) for v in (CLOSED, OPEN, NEEDS)}
        print(f"{len(rows)} rows: {n[CLOSED]} closed, {n[OPEN]} open, "
              f"{n[NEEDS]} needs-human")


# The lifecycle has no shortcut edge and this script does not invent one: a gap
# walks Open -> Investigating -> Prototype -> Verified -> Closed, one legal
# transition per append, and the Verified step carries the evidence because
# `advance` refuses a Verified with no note. Four records per closure is the
# price of an append-only log that can be replayed into the same states.
_PATH_TO_CLOSED = (GapState.INVESTIGATING, GapState.PROTOTYPE,
                   GapState.VERIFIED, GapState.CLOSED)


def apply(rows: list[Row], queue: GapQueue) -> list[str]:
    """Move every measured-CLOSED gap to Closed. Returns the ids moved."""
    idx = _queue_index(queue)
    moved: list[str] = []
    for r in rows:
        if r.verdict != CLOSED:
            continue
        gap = idx.get(r.source_id)
        if gap is None or gap.state is GapState.CLOSED:
            continue
        note = f"reconcile_gaps.py: {r.evidence}"
        for target in _PATH_TO_CLOSED:
            if gap.state is target:
                continue
            queue.advance(gap.id, target, note=note)
        moved.append(f"{r.source_id} ({gap.id})")
    return moved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="move measured-CLOSED gaps through the lifecycle")
    ap.add_argument("--by-priority", action="store_true",
                    help="counts by severity")
    ap.add_argument("--diff", action="store_true",
                    help="only rows where the queue and the code disagree")
    ap.add_argument("--gaps", default=None,
                    help="path to a gaps.jsonl (default: the project's)")
    ap.add_argument("--no-require-committed", action="store_true",
                    help="allow --apply to close on uncommitted evidence "
                         "(default: refuse; see head_export)")
    args = ap.parse_args(argv)

    queue = GapQueue(args.gaps) if args.gaps else GapQueue()
    rows = reconcile()
    report(rows, queue, by_priority=args.by_priority, diff_only=args.diff)

    if args.apply:
        if not args.no_require_committed:
            with head_export() as head:
                with at_root(head):
                    committed = {r.source_id for r in reconcile()
                                 if r.verdict == CLOSED}
            in_flight = [r.source_id for r in rows
                         if r.verdict == CLOSED and r.source_id not in committed]
            if in_flight:
                print(f"\nCLOSED in the working tree but NOT at HEAD, so not "
                      f"closed here: {', '.join(in_flight)}")
                print("  (uncommitted evidence may still be reverted; the gap "
                      "log has no reopen edge)")
            rows = [r if (r.verdict != CLOSED or r.source_id in committed)
                    else Row(r.source_id, OPEN, r.evidence + "  [evidence is "
                             "uncommitted work in flight; not closed]")
                    for r in rows]
        moved = apply(rows, queue)
        print(f"\nmoved to Closed: {len(moved)}")
        for m in moved:
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
