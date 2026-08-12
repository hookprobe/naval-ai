#!/usr/bin/env python3
"""Reconcile the gap queue against the CODE, repeatably.

WHY THIS EXISTS, AND WHAT IT MEASURES.

`navalai.gaps.import_gap_register()` seeded 122 findings from
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
    python scripts/reconcile_gaps.py --rebuild      # reconstruct the queue from
                                                    # scratch (see below)

`--apply` walks Open -> Investigating -> Prototype -> Verified -> Closed one
legal step at a time (there is no shortcut edge and this script does not add
one), and the Verified note carries the evidence string, because
`GapQueue.advance` refuses a Verified with no measurement -- correctly.

THE QUEUE DOES NOT SURVIVE A CLONE, AND THAT IS THE DESIGN
----------------------------------------------------------

`data/evolution/gaps.jsonl` is gitignored, so a fresh checkout has no queue at
all and every one of the recorded closures is absent from it. That was filed as
a finding (register section R) and it has the shape this repository keeps
measuring -- gap D3 (`data/baselines.json` untracked, so the first retrain
always deployed) and gap J5 (benchmark geometry ignored, so a validation
silently skipped). The obvious fix is to track the file. It was considered and
REJECTED, for three measured reasons:

1. THE LOG IS DERIVED, NOT AUTHORED. Every one of the 83 closures in it was
   written by `--apply` from a predicate in this file over code that IS
   tracked. Committing it stores a conclusion next to its own evidence, which
   is this codebase's recurring defect (a number declared twice) in its most
   expensive form: when the two disagree the log is the one that is wrong, and
   `test_no_gap_is_closed_in_the_queue_while_the_code_says_it_is_open` exists
   because that can happen.
2. IT WOULD CONFLICT ON EVERY CONCURRENT EDIT, UNRESOLVABLY. It is append-only
   with four records per closure, and `GapQueue.next_id` mints ids by scanning
   the log it has -- so two agents closing two different gaps both mint G-120,
   and neither side of the merge can be taken. `data/exports/*` and `renders/`
   already taught this repository the cheaper version of the lesson: tracked
   files that the tooling rewrites dirtied the tree on every test run,
   conflicted on every cherry-pick, and provoked an unasked `git checkout --`.
   `tests/test_pipeline.py::test_the_default_archive_path_is_gitignored` pins
   the ignore for the archive beside it.
3. WHAT MUST SURVIVE A CLONE ALREADY DOES. The findings are
   `docs/GAP-REGISTER.md` (tracked) and their verdicts are the predicates below
   (tracked). The jsonl is a JOURNAL of applying one to the other.

So the queue is treated as a CACHE with two properties instead:

  RECONSTRUCTIBLE  `--rebuild` re-imports the register and re-applies every
                   measured closure. It is idempotent -- `GapQueue.emit` is
                   idempotent on source_id and `apply` skips already-Closed
                   rows -- so it is safe on a populated queue too.
  LOUD             an absent or empty queue is a banner and a non-zero exit,
                   never an empty report. A missing record reading as "nothing
                   to see" is exactly gap D3's shape, and this script has
                   already made that error once: `not ledger_has("Gate 2M")`
                   was TRUE when no ledger existed, so an absent record scored
                   as a green gate inside the tool built to catch that.
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

from navalai.gaps import (GapQueue, GapState, Severity,   # noqa: E402
                          import_gap_register)


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


def func_code(rel: str, name: str) -> str:
    """The source of ONE function, comments and docstrings blanked. "" if absent.

    A file-wide `has_code` cannot tell "the fix landed inside
    `suite_fingerprint`" from "the token appears somewhere in flywheel.py", and
    flywheel.py is 900 lines that discuss the frozen suite's targets constantly
    -- `frozen_suite` returns `y`, `retrain` scores against it, `_metrics`
    consumes it. That is the same hazard `code()` exists for, one level finer:
    the vocabulary of the gap is present, as CODE, in functions that are not the
    one the gap is about.

    `code()` BLANKS rather than deletes precisely so a slice like this lines up
    with the AST's offsets into the original text.
    """
    src = text(rel)
    if not src:
        return ""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ""
    blanked = code(rel)
    offs = [0]
    for ln in blanked.splitlines(keepends=True):
        offs.append(offs[-1] + len(ln))
    for node in ast.walk(tree):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name):
            end_line = node.end_lineno or node.lineno
            if end_line >= len(offs):
                continue
            start = offs[node.lineno - 1] + node.col_offset
            end = offs[end_line - 1] + (node.end_col_offset or 0)
            return blanked[start:end]
    return ""


def _fingerprint_covers_targets() -> bool:
    """Does the frozen suite's IDENTITY hash reach its own y values? (gap T1)

    Read from `func_code`, not from the module, because `suite_fingerprint`'s
    docstring states the target-blindness in the exact words a fix would use --
    "Coordinates, not TARGETS, on purpose" -- and `frozen_suite` two functions
    above it returns `(X, y, labels)` in plain code. Either would answer for a
    guard that does not exist. B4 cost 332 unwound transitions for that mistake
    in its comment-shaped form.

    Two conjuncts because one is not the guard: the targets must be a PARAMETER
    of the fingerprint and they must reach the hash. A signature that accepts
    `y` and ignores it is target-blind with a longer signature.
    """
    fn = func_code("navalai/flywheel.py", "suite_fingerprint")
    return bool(re.search(r"def suite_fingerprint\([^)]*\b(y|targets)\b", fn)
                and re.search(r"h\.update\(.*\b(y|targets)\b", fn))


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

    `gate` is the row in `navalai.gates.GATES` this finding is about, and it
    exists because the link was PROSE ONLY. RE-COUNTED 2026-08-11 by walking
    this file's AST (docs/BUILD-PLAN.md section 15.2 item 3): of 120 rows, 14
    named a gate somewhere inside `evidence` and only 7 were machine-linked --
    five through `ledger_has()`, plus E1 and J5 grepping `navalai/gates.py` for
    a `Gate("Gate X"` literal. EIGHT named a gate that nothing verified, and
    there was no field on `Check`, no field on `Gate`, no mapping table and no
    test, so the question "which gap blocks which gate" could not be asked.

    A NAME IS NOT A LINK, which is why the field ships with two assertions in
    `tests/test_reconcile_gaps.py` rather than one: every value here must
    resolve to a real row in `GATES` (a renamed gate then breaks the register
    instead of silently orphaning it), and every row whose `evidence` names a
    gate must SET `gate`, to one of the gates it names -- so the prose and the
    field cannot drift apart, which is the defect this field was added to end.
    The second is one-directional on purpose: D9's evidence names TWO gates
    ("Gate 6R's threshold parity could become Gate 6's VERDICT parity") and
    the gate the row is ABOUT is Gate 6.

    It is deliberately NOT a claim about the gate's colour. Gate 6D is RED and
    Gate 0G is GREEN and both are legitimate values; the field says "this row
    is about that gate", nothing more. `status_of` and `data/gate-ledger.json`
    own the colour, and `ledger_has()` remains the only predicate that reads a
    gate's STATE.
    """
    source_id: str
    evidence: str
    closed: Callable[[], bool]
    gate: str | None = None


# Rows for which NO predicate is honest. Recorded with the reason, never
# guessed.
#
# It was EMPTY from 2026-08-07 (its three occupants were resolved that day: two
# RETIRED below, one re-filed with a predicate) until N6 was filed on
# 2026-08-11. The category was kept through that empty period precisely because
# "no predicate can honestly be written" is a legitimate answer the next finding
# might need, and deleting it would make the next reconciler guess instead. A
# row here is reported NEEDS-HUMAN and is never closed by `--apply`.
NEEDS_HUMAN: dict[str, str] = {
    "N6": "THE PREDICATE WOULD HAVE TO READ PROSE SEMANTICS. N6 is 'a "
          "document quotes a number from a run directory that "
          "clean-runs.sh --purge has since deleted, and the sentence is not "
          "deleted with it'. The half that is mechanisable IS mechanised and "
          "is asserted: a watermark lives only in data/gate-ledger.json, and "
          "tests/test_gate_integrity.py::"
          "test_the_gate2m_ledger_entry_points_at_something_real refuses an "
          "entry that cites a directory which is not there -- which is why "
          "Gate 2M's watermark is the string 'NONE' rather than a sixth "
          "circulating figure. What is left is the question a regex cannot "
          "ask: is THIS sentence vouching for evidence it has not checked? "
          "It is NOT retirable, and that distinction is the whole of this "
          "category: J9 and J10 are propositions about a MOMENT (a sliding "
          "window of git log, one working tree at one instant), whereas 'this "
          "committed sentence presents a measurement as current' is a "
          "property of the committed text, i.e. of a checkout. It is not "
          "gateable either: runs/ is a gitignored build artifact, so a gate "
          "asking 'does every cited run directory exist?' is GREEN on the Mac "
          "simulation node and RED on every fresh clone -- an environment "
          "fact wearing a project fact's colour, which is gap D3's shape. "
          "CLEARING CONDITION (recorded so this is not a permanent shrug, and "
          "it is a decision for a human, not an agent): either documents must "
          "state per cited run directory whether it still exists -- then this "
          "becomes a text predicate and gets one -- or the ledger's guard is "
          "ruled to be the whole mechanism, and the sentence in CLAUDE.md "
          "saying 'this file has no such enforcement, so it is on the writer' "
          "is corrected by its owner. See docs/GAP-REGISTER.md section N.",
}


# Rows RETIRED under PLM.md section 3 step 7 ("dead parameters, superseded
# stand-ins, stale rules: removed with a note, never left ambiguous").
#
# A retired row is NOT a fixed row, and this script must never let one read as
# one: `RETIRED` is its own verdict, it is counted in its own column, and
# `apply()` will not move it -- the gap log has no reopen edge, so writing a
# retirement into it as a closure would be permanent and wrong.
#
# The test for admission is narrow. Both rows below assert something about a
# MOMENT IN HISTORY rather than about a checkout, so no predicate over the code
# can answer them stably -- not "we have not written the predicate yet" but
# "the proposition is not about the thing the predicate reads". That is what
# separates a retirement from a NEEDS-HUMAN: a NEEDS-HUMAN row is still a gap
# awaiting a human's judgement, a retired row is not a gap.
RETIRED: dict[str, str] = {
    "J9": "NOT A PROPERTY OF THE CHECKOUT. '7 of 10 recent commits comply with "
          "PLM section 3 step 4' is a statistic over a sliding window of git "
          "history: it re-answers itself every commit, it was already stale "
          "when the register was written, and 'fixing' it is not something a "
          "tree can be in the state of. Its ACTIONABLE half was separable and "
          "IS done -- the row's own evidence sentence is 'scripts/gate2m.py "
          "has no test of its own', and it now has "
          "tests/test_cfd_reference_parity.py (Gate 2R), including "
          "test_gate2m_has_no_gci_of_its_own. What remains is a process audit, "
          "which is what code review and the pre-push hook are for. Retired "
          "2026-08-07; if commit-message compliance is to be enforced it "
          "should be filed as a NEW finding naming a mechanism (a hook), not "
          "kept as a ratio nobody can re-derive.",
    "J10": "NOT A PROPERTY OF THE CHECKOUT. 'Uncommitted CFD work sits in the "
           "working tree' describes one machine at one instant. It is true "
           "again right now, for an unrelated reason (concurrent agents), and "
           "will be true again tomorrow -- a condition that no fix can move to "
           "false is not a gap, it is a fact about how work happens here. Its "
           "real content -- that a document read as truth may describe "
           "uncommitted code -- is already mechanised and is where it belongs: "
           "`head_export()` in this file refuses to close a gap on evidence "
           "that is not committed, after doing exactly that for A4 on another "
           "agent's in-flight edit. Retired 2026-08-07.",
}


CHECKS: tuple[Check, ...] = (
    # -- A. the ladder is not a ladder -------------------------------------
    Check("A1", "navalai/evaluate.py::revalidate escalates to L2 and refuses "
                "L3 with TierRequiresOperator; tests/test_ladder.py "
                "(Gate R3) exercises it",
          lambda: defines("navalai/evaluate.py", "revalidate")
                  and has_code("navalai/evaluate.py", "TierRequiresOperator")
                  and defines("tests/test_ladder.py",
                              "test_revalidate_promotes_to_l2_and_records_it"),
          gate="Gate R3"),
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
    # `has_code`, not `has`: A4 asks whether the PRODUCT escalates, which is a
    # question about behaviour, and `navalai/surrogate.py`'s module docstring
    # opens by NAMING this gap -- "is_ood() had TWO call sites in the whole
    # repository and both were in tests". Every file in the tuple below is one
    # a fix would land in AND one whose comments discuss the defect. MEASURED
    # 2026-08-11 before the conversion, both forms on all five files: only
    # flywheel.py matches and it matches in both, so no verdict moved. The
    # conversion buys that it cannot move by an edit to a comment.
    Check("A4", "a NON-TEST caller of GP.predict_or_escalate / is_ood, i.e. "
                "something in the product that actually escalates",
          lambda: any(has_code(rel, r"predict_or_escalate|is_ood\(")
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
    # RE-FILED 2026-08-07. A6b was parked as NEEDS-HUMAN on the grounds that it
    # is "a CORRECTION to A6, and whether a correction row is itself closeable
    # is a judgement". That was the wrong reading of it, and it cost the row its
    # verdict: A6b's own text ends "so the sigma test was not as broken as A6
    # implies -- WHAT IT LACKED WAS RECALL", which is a defect of its own with a
    # different clearing condition from A6's. A6 is closed by a support test
    # EXISTING; A6b is closed only by that test being MEASURED against a
    # restricted training support, because A6b's finding is that the original
    # experiment drew training and query hulls from the same box and therefore
    # contained no out-of-distribution query at all -- nothing can separate an
    # empty set. A predicate that reads "does a support test exist" would answer
    # A6 twice and A6b never.
    #
    # So the three things this predicate insists on are the three the finding
    # names: the training support is RESTRICTED (GP.fit on X[inside], not X),
    # RECALL on the excluded region is computed for sigma alone and for sigma
    # plus support, and the support term is required to IMPROVE it by a margin.
    # All three are read out of `code()`, because "recall" appears verbatim in
    # the docstrings of both surrogate.is_ood and the test itself.
    Check("A6b", "the missing half of the sigma test is RECALL, and "
                "tests/test_phase3.py::test_support_distance_catches_what_"
                "sigma_alone_misses measures it on a RESTRICTED training "
                "support (GP.fit(X[inside]), queries outside it) and requires "
                "the support term to raise it by >= 0.10",
          lambda: defines("tests/test_phase3.py",
                          "test_support_distance_catches_what_sigma_alone_misses")
                  and has_code("tests/test_phase3.py", r"GP\.fit\(X\[inside\]")
                  and has_code("tests/test_phase3.py",
                               r"r_new = \(both & out\)\.sum\(\) / out\.sum\(\)")
                  and has_code("tests/test_phase3.py",
                               r"assert r_new >= r_old \+ 0\.10")),
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
                              "test_a_status_cannot_be_renamed_into_passing"),
          gate="Gate 0G"),
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
                      r"REFERENCE_DESIGNS|hand_calculation"),
          gate="Gate 6"),
    Check("D10", "Gate 3's error bar is measured across seeds rather than on "
                 "its one chosen seed (991)",
          lambda: has_code("tests/test_phase3.py",
                      r"parametrize\(\s*\"seed\"|for seed in range\(\d+\).*rel"),
          gate="Gate 3"),
    # BOTH HALVES, deliberately. A ledger entry alone is a record no gate reads;
    # a RED row alone fails CI with no owner, no watermark and no expiry. The
    # clause is only recorded WHERE A GATE CAN FAIL ON IT when the two exist
    # together -- which is also why `ledger_has` is not asked on its own here:
    # at 5bbffb7 there was no ledger file at all, and every question of the form
    # "is X absent from the ledger" answered YES from a file that did not exist.
    Check("D11", "the >=99% raw-feasibility clause is Gate 4F -- a typed RED "
                 "row in navalai/gates.py WITH a data/gate-ledger.json "
                 "watermark, owner and review_by -- instead of a sentence in "
                 "Gate 4's prose scope; tests/test_red_by_record.py is the fence",
          lambda: ledger_has("Gate 4F")
                  and has_code("navalai/gates.py", r'Gate\("Gate 4F"')
                  and exists("tests/test_red_by_record.py"),
          gate="Gate 4F"),
    Check("D12", "generative._conditioned draws DISJOINT candidate batches "
                 "against a reference cut, and the Gate 4 suite has a control",
          lambda: defines("navalai/generative.py", "_conditioned")
                  and has_code("navalai/generative.py",
                               r"cand = sampler\(batch, s\)")
                  and defines(
                      "tests/test_phase4.py",
                      "test_percentile_is_a_strictness_knob_and_the_docstring_"
                      "now_says_so"),
          gate="Gate 4"),
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
                  and has_code("navalai/gates.py", r'Gate\("Gate 1H"'),
          gate="Gate 1H"),
    # `imports(..., "holtrop")` ALONE CANNOT TELL THE TWO ARMS APART, and they
    # are opposite fixes: one calls the method, the other measures that it does
    # not apply. It also closed on a bare import line, which is defect class 8
    # aimed at a module name instead of a comment. Tightened 2026-08-12 in the
    # commit that landed the guard arm, and run against the pre-fix tree where
    # evaluate.py imports no holtrop symbol at all, so it still reads OPEN
    # there. Both arms are accepted; each requires a CALL, not a name.
    Check("E1b", "Holtrop-Mennen is wired into evaluate() (or an explicit "
                 "envelope guard routes small craft away from it there)",
          lambda: imports("navalai/evaluate.py", "holtrop")
                  and (has_code("navalai/evaluate.py",
                                r"holtrop_envelope_violations\(")
                       or has_code("navalai/evaluate.py",
                                   r"holtrop\.total\(|holtrop_total\("))),
    Check("E2", "benchmarks/wigley.py carries an INDEPENDENT reference curve, "
                "not a frozen copy of our own output labelled as a regression "
                "anchor",
          # THE TWO CLAUSES ARE DIFFERENT KINDS AND ARE READ DIFFERENTLY.
          #
          # Clause 1 is about a SYMBOL, so it reads `has_code`. It is the
          # sharpest of the three P0-4 conversions: `REFERENCE_CW` also occurs
          # in a COMMENT at benchmarks/wigley.py:197 -- inside the sentence
          # that DIAGNOSES the disease it had -- so on `has` this clause would
          # survive the constant itself being deleted. MEASURED 2026-08-11:
          # both forms are True today (the constant is at :239), so the
          # conversion moved no verdict; it removed a way for the row to stop
          # being able to fail.
          #
          # Clause 2 is deliberately LEFT ON `lacks` (docs/BUILD-PLAN.md
          # section 15.2 item 4). It asks whether the file CONFESSES "not an
          # independent validation" -- a claim about PROSE, like F19's
          # attribution and J7's supersession markers. An absence predicate
          # read through `code()` is blind to the very comment it is looking
          # for: write that confession into a docstring and `lacks_code` still
          # answers True, i.e. the gap would read CLOSED on a file that admits
          # in its own words that it is open. `code()`'s docstring states the
          # law -- the choice is made per row, not by pattern.
          lambda: has_code("benchmarks/wigley.py", r"REFERENCE_CW")
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
    # THE PREDICATE WAS STALE, NOT THE CODE (measured 2026-08-12). It matched
    # `round(float(v), 10)` occurring somewhere AFTER the text `add_hull`, and
    # it went false for two reasons that are both the FIX: the decimal count is
    # now the named constant `CANON_DECIMALS`, and the rounding moved OUT of
    # `add_hull` into the shared `canonical()` that `hull_id` also calls —
    # which is the entire point of the fix, since the collision came from the
    # address and the payload rounding in different places. A predicate that
    # requires the duplicate arrangement in order to report the duplicate
    # removed is a predicate that can only ever be wrong.
    #
    # It now asks the behaviour: ONE canonical form, hashed by `hull_id` and
    # stored by `add_hull`. Run against the pre-fix tree that reads FALSE
    # (add_hull stored `json.dumps(params.tolist())`), so it can fail on the
    # defect. tests/test_phase0.py::test_the_stored_hull_row_is_the_vector_
    # that_was_hashed is the behavioural fence beside it.
    Check("E9", "db.add_hull stores the SAME canonical rounded params it "
                "hashes, so two vectors differing by 1e-11 cannot collide",
          lambda: defines("navalai/db.py", "canonical")
                  and bool(re.search(r"canonical\(params\)",
                                     func_code("navalai/db.py", "hull_id")))
                  and bool(re.search(r"json\.dumps\(canonical\(params\)\)",
                                     func_code("navalai/db.py", "add_hull")))
                  and defines("tests/test_phase0.py",
                              "test_the_stored_hull_row_is_the_vector_that_"
                              "was_hashed")),
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
    # `has_code`, not `has`: "is CONSTRUCTED somewhere" is a behaviour claim,
    # and a docstring saying "SeakeepingResult() is never called" would close
    # it -- gap B4's exact shape, where the word sat in the comment ON the
    # defect. MEASURED 2026-08-11, both forms on all four files: seakeeping.py
    # matches in both, the other three in neither. No verdict moved.
    Check("F4", "SeakeepingResult is actually constructed somewhere, so the "
                "only L2 type carrying uncertainty_rel is not decoration",
          lambda: any(has_code(rel, r"SeakeepingResult\(")
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
          lambda: exists("data/gate-ledger.json") and not ledger_has("Gate 2M"),
          gate="Gate 2M"),
    Check("F17", "Gate 2U is no longer carried as expected-red in an existing "
                 "ledger, i.e. the 'converges' half has a number "
                 "(mesh_robustness.py --solve)",
          lambda: exists("data/gate-ledger.json") and not ledger_has("Gate 2U"),
          gate="Gate 2U"),
    Check("F18", "benchmarks/kcs.py records the re-measured -0.267% "
                 "displacement error, not the superseded -0.09%",
          lambda: has_code("benchmarks/kcs.py", r'"displacement_error_pct": -0\.267')),
    # The old "13 groups" string still occurs in kcs.py -- inside the sentence
    # that RETRACTS it. `lacks("13 independent CFD groups")` would therefore
    # report this gap open forever, punishing the file for recording its own
    # correction, which PLM section 3 step 7 requires it to do. The predicate
    # asks for the corrected attribution and for the band to be DERIVED from
    # the rows, which is what makes seven the number that can change.
    #
    # BOTH CLAUSES STAY ON `has`, AND THIS IS NOT AN OVERSIGHT. P0-4 converts
    # A4, F4 and E2's first clause to `has_code`; applying the same sweep here
    # would be wrong, because F19 is a claim about an ATTRIBUTION -- what the
    # file SAYS the band is derived from -- and both strings live in comments
    # at benchmarks/kcs.py:136-141 ON PURPOSE. MEASURED 2026-08-11, both forms:
    # `has` True / `has_code` False on each clause, so converting would flip a
    # correctly-closed row to OPEN forever and punish the file for carrying its
    # own correction. A blanket has()->has_code() pass breaks exactly the rows
    # that document this project's retractions.
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
                  and defines("navalai/unroll.py", "refold_deviation_mm"),
          # G4's evidence names no gate, and until 2026-08-11 there was none to
          # name. Commit eacb9ce created Gate 6D and its ledger entry opens
          # "GAP G4", so the link is the ledger's own statement rather than a
          # guess -- and it is exactly the linkage this field exists to make
          # queryable: G4 is now the row that says which gate is red.
          gate="Gate 6D"),
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
                  and has_code("navalai/flywheel.py", r"best_wall_clock_s"),
          gate="Gate 7"),
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
          lambda: has_code("tests/test_phase4.py", r"non-expert|unassisted"),
          gate="Gate 4"),
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
                              "test_no_document_restates_a_gate_2m_figure"),
          gate="Gate 2M"),
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
                              "test_the_readme_gate_table_agrees_with_the_runner"),
          gate="Gate 6R"),
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
                  and has_code("navalai/gates.py", r'Gate\("Gate 2G"'),
          gate="Gate 2G"),
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

    # -- T. the frozen benchmark has no guard on its own y values ------------
    #
    # THESE THREE WERE INVISIBLE TO THIS TABLE UNTIL 2026-08-11. Section T
    # shipped on 2026-08-07 with the header `| id | finding | where | severity |`
    # and `import_gap_register` accepts a findings table only on
    # `cells[0] == "ID"` plus a `"Sev"` column, both case-sensitive. So T1, T2
    # and T3 were never filed, never answered here, and appeared in no count --
    # the import reported 119 findings from a register holding 122, and the
    # coverage tests in tests/test_reconcile_gaps.py passed, because they
    # compare this table against the QUEUE and the queue was missing the same
    # three rows. A guard that reads its own input cannot notice input it never
    # read. The register already carried the OVER-import direction (a mis-headed
    # table that DOUBLE-imported, 119 -> 121, caught by a test); the UNDER-import
    # direction is now caught by
    # tests/test_gaps.py::test_a_gradeable_table_the_importer_cannot_see_is_fatal.
    Check("T1", "the frozen suite's identity covers its TARGETS: "
                "flywheel.suite_fingerprint takes the suite's y and reaches the "
                "hash with it, so a physics change that moves the frozen y "
                "values cannot leave the fingerprint identical -- or an "
                "equivalent targets guard is recorded in data/baselines.json. "
                "MEASURED at the finding: the production Michell grid went "
                "41x14 -> 161x28, the frozen targets moved up to -4.2% "
                "(294.99 -> 282.55 Wh/NM) and the fingerprint stayed "
                "f37529748d22c684 either side",
          lambda: _fingerprint_covers_targets()
                  or has("data/baselines.json",
                         r'"(suite_)?targets?_(fingerprint|sha256)"')),
    # NOT `lacks_code(... "!= fp")`: at the audit baseline flywheel.py has no
    # bootstrap branch AT ALL, so an absence test reads CLOSED on the tree the
    # defect was measured on -- the negative control's whole point. Both arms
    # below are positive.
    Check("T2", "the documented regeneration route cannot deadlock. Either the "
                "fingerprint covers the targets (T1), so a physics change makes "
                "retrain's bootstrap branch fire and drop the stale mark, or "
                "the drop stops being conditioned on a fingerprint mismatch at "
                "all (`if prior is not None and bootstrap:` in "
                "flywheel.retrain). Today it is conditioned on `!= fp`, and fp "
                "is target-blind, so a harder-to-learn physics change would "
                "leave all three quantities refused against the very file "
                "make_baseline.py exists to replace",
          lambda: _fingerprint_covers_targets()
                  or bool(re.search(r"if prior is not None and bootstrap:",
                                    func_code("navalai/flywheel.py", "retrain")))),
    # T5 records that the OWNER'S DECISION between these two routes is still
    # owed, and this predicate does not pre-empt it: it accepts either, and it
    # reports OPEN until one of them is in the code. An owner deciding is not a
    # thing a checkout can be in the state of; the resulting mark is.
    Check("T3", "the deployment ratchet is applied to a ROBUST statistic: "
                "scripts/make_baseline.py measures the mark over a SEED "
                "ENSEMBLE (a plural seed constant it iterates), records that "
                "statistic and its spread in data/baselines.json, and "
                "flywheel.retrain compares against the recorded ensemble "
                "statistic or derives its tolerance from the recorded spread -- "
                "instead of a single-seed 60-hull retrain against a best-of-8 "
                "120-hull minimum (measured spread 2.7x at n=60, 4.6x at n=120, "
                "tolerance 1.25x; 3 of 8 honest seeds cleared it)",
          lambda: has_code("scripts/make_baseline.py",
                           r"\b(HARVEST_SEEDS|ENSEMBLE_SEEDS|SEEDS)\b")
                  and has("data/baselines.json",
                          r'"(ensemble_median_rel_err|median_rel_err_seeds|'
                          r'seed_spread|seeds)"')
                  and has_code("navalai/flywheel.py",
                               r"ensemble_median_rel_err|median_rel_err_seeds|"
                               r"seed_spread")),
)


# ---------------------------------------------------------------------------
# running it
# ---------------------------------------------------------------------------

CLOSED, OPEN, NEEDS = "CLOSED", "OPEN", "NEEDS-HUMAN"

# A RETIRED row is not a fixed row. It gets its own verdict string, its own
# column in every summary this script prints, and no path into `apply()` --
# because the one thing that must never happen is a retirement being read as a
# closure by someone scanning for what is left to do.
RETIRED_V = "RETIRED"
VERDICTS = (CLOSED, OPEN, NEEDS, RETIRED_V)


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
    for sid, why in RETIRED.items():
        rows.append(Row(sid, RETIRED_V, why))
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
        print(f"{'severity':10} {'closed':>7} {'open':>6} {'needs-human':>12} "
              f"{'retired':>8} {'total':>6}")
        print("-" * 55)
        tot = {v: 0 for v in VERDICTS}
        for sev in order:
            c = {v: 0 for v in VERDICTS}
            for r in rows:
                gap = idx.get(r.source_id)
                if gap and gap.severity is sev:
                    c[r.verdict] += 1
                    tot[r.verdict] += 1
            print(f"{sev.value:10} {c[CLOSED]:7} {c[OPEN]:6} {c[NEEDS]:12} "
                  f"{c[RETIRED_V]:8} {sum(c.values()):6}")
        print("-" * 55)
        print(f"{'TOTAL':10} {tot[CLOSED]:7} {tot[OPEN]:6} {tot[NEEDS]:12} "
              f"{tot[RETIRED_V]:8} {sum(tot.values()):6}")
    else:
        n = {v: sum(1 for r in rows if r.verdict == v) for v in VERDICTS}
        # "retired" is spelled out rather than folded into a total, because the
        # whole hazard of retirement is that it looks like completion at a
        # glance. A retired row is NOT fixed; nothing was done to the code.
        print(f"{len(rows)} rows: {n[CLOSED]} closed, {n[OPEN]} open, "
              f"{n[NEEDS]} needs-human, {n[RETIRED_V]} retired "
              f"(retired != fixed: see RETIRED in this file for why each one "
              f"is not a property of the checkout)")


# The lifecycle has no shortcut edge and this script does not invent one: a gap
# walks Open -> Investigating -> Prototype -> Verified -> Closed, one legal
# transition per append, and the Verified step carries the evidence because
# `advance` refuses a Verified with no note. Four records per closure is the
# price of an append-only log that can be replayed into the same states.
_PATH_TO_CLOSED = (GapState.INVESTIGATING, GapState.PROTOTYPE,
                   GapState.VERIFIED, GapState.CLOSED)


def apply(rows: list[Row], queue: GapQueue) -> list[str]:
    """Move every measured-CLOSED gap to Closed. Returns the ids moved.

    ONLY `CLOSED`. An OPEN row is a live gap, a NEEDS-HUMAN row is a live gap
    awaiting judgement, and a RETIRED row is not a gap at all -- but none of the
    three has been FIXED, and the queue's `Closed` state means fixed. There is
    no reopen edge, so a wrong move here is permanent: the B4 incident cost 332
    unwound transitions.
    """
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


# The banner for an absent queue. It is deliberately not a warning line: this
# script's job is to answer "what is still open", and answering it from an empty
# queue produces a report in which every row reads NOT IN QUEUE -- which a
# reader skims as "nothing to do" rather than "nothing was read". `not
# ledger_has("Gate 2M")` returning True from a ledger that did not exist is the
# same error, made by this same file, and it is why the exit code is non-zero.
EMPTY_QUEUE = """\
================================================================================
THE GAP QUEUE IS EMPTY OR ABSENT: {path}

`data/evolution/` is gitignored ON PURPOSE (see this file's module docstring),
so a fresh clone has no queue and none of the recorded closures. That is not a
loss: the findings live in docs/GAP-REGISTER.md and the verdicts are the
predicates in this file, both of which are committed. The queue is a cache of
applying one to the other, and it is rebuilt with one command:

    python scripts/reconcile_gaps.py --rebuild

Nothing below has been read from a queue. An empty queue is reported as empty,
never as "no gaps".
================================================================================"""


def rebuild(queue: GapQueue, rows: list[Row]) -> tuple[int, list[str]]:
    """Reconstruct the queue from the two committed sources.

    docs/GAP-REGISTER.md supplies the findings; the predicates above supply
    their verdicts. Returns (findings imported, gap ids moved to Closed).

    Idempotent by construction: `GapQueue.emit` returns the existing gap for a
    source_id it has already filed, and `apply` skips a gap that is already
    Closed. Running it on a populated queue is therefore a no-op, which is what
    makes it safe to reach for when you are not sure what state you are in.
    """
    report_ = import_gap_register(queue=queue)
    return len(report_.imported), apply(rows, queue)


def committed_only(rows: list[Row]) -> list[Row]:
    """Downgrade closures whose evidence is not yet committed. See head_export."""
    with head_export() as head:
        with at_root(head):
            committed = {r.source_id for r in reconcile() if r.verdict == CLOSED}
    in_flight = [r.source_id for r in rows
                 if r.verdict == CLOSED and r.source_id not in committed]
    if in_flight:
        print(f"\nCLOSED in the working tree but NOT at HEAD, so not closed "
              f"here: {', '.join(in_flight)}")
        print("  (uncommitted evidence may still be reverted; the gap log has "
              "no reopen edge)")
    return [r if (r.verdict != CLOSED or r.source_id in committed)
            else Row(r.source_id, OPEN, r.evidence + "  [evidence is "
                     "uncommitted work in flight; not closed]")
            for r in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="move measured-CLOSED gaps through the lifecycle")
    ap.add_argument("--rebuild", action="store_true",
                    help="reconstruct the queue from docs/GAP-REGISTER.md plus "
                         "the predicates in this file, then apply the measured "
                         "closures (idempotent)")
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

    if args.rebuild:
        if not args.no_require_committed:
            rows = committed_only(rows)
        n, moved = rebuild(queue, rows)
        print(f"rebuilt {queue.log.path}: {n} findings imported from "
              f"{'docs/GAP-REGISTER.md'}, {len(moved)} closed from the "
              f"measured verdicts")
        report(reconcile(), queue, by_priority=args.by_priority)
        return 0

    if not queue.all():
        print(EMPTY_QUEUE.format(path=queue.log.path))
        report(rows, queue, by_priority=args.by_priority, diff_only=args.diff)
        return 2

    report(rows, queue, by_priority=args.by_priority, diff_only=args.diff)

    if args.apply:
        if not args.no_require_committed:
            rows = committed_only(rows)
        moved = apply(rows, queue)
        print(f"\nmoved to Closed: {len(moved)}")
        for m in moved:
            print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
