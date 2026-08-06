"""Gate SG-R: the gap queue is reconciled against the CODE, not against prose.

`navalai.gaps` turns `docs/GAP-REGISTER.md` into work items. It cannot turn
them into TRUE work items: it seeded all 119 findings as `Open`, which was the
register document's state on 2026-08-05 and not the repository's — roughly
seventy of them had been closed in code by the following day and nothing
propagated it. `scripts/reconcile_gaps.py` is the propagation, and this suite
is what stops it becoming the thing it was written to replace.

The failure it guards against is specific and this repository has measured it
twice: a report that reads its own REQUEST instead of the RESULT. `run-case.sh`
printed "3 of 3 layers" off snappy's requested-spec table on a mesh with zero
layers; `gate2m.py` printed `VERDICT: PASS` on a diverging family because
`gci <= 5.0` is true of -27%. A reconciler that matched commit messages, or
that let `docs/GAP-REGISTER.md` — which QUOTES every missing symbol by name —
answer for the code, would be the same defect a third time.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from navalai.gaps import GapQueue, GapState, Severity   # noqa: E402
from navalai.pipeline import JsonlLog                   # noqa: E402


def _load():
    """Import scripts/reconcile_gaps.py (a script, not a package member)."""
    spec = importlib.util.spec_from_file_location(
        "reconcile_gaps_under_test", _ROOT / "scripts" / "reconcile_gaps.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # dataclasses needs it importable
    spec.loader.exec_module(mod)
    return mod


rg = _load()


# ---------------------------------------------------------------------------
# coverage: every finding is answered, and nothing is invented
# ---------------------------------------------------------------------------

def _queue_source_ids() -> set[str]:
    q = GapQueue()
    return {g.source_id for g in q.all() if g.source_id}


def test_every_queued_finding_gets_an_answer():
    """No row may be silently skipped.

    `navalai.gaps._split_row` learned this: a parser that dropped the three
    rows containing an escaped pipe reported a SMALLER register than the one on
    disk — two HIGH and one CRITICAL finding, gone, with the importer saying
    "names no level". A reconciler that answers 100 of 119 has the same shape.
    """
    answered = {c.source_id for c in rg.CHECKS} | set(rg.NEEDS_HUMAN)
    missing = _queue_source_ids() - answered
    assert not missing, f"queued findings with no verdict: {sorted(missing)}"


def test_nothing_is_answered_that_was_never_filed():
    answered = {c.source_id for c in rg.CHECKS} | set(rg.NEEDS_HUMAN)
    extra = answered - _queue_source_ids()
    assert not extra, f"verdicts for findings that are not in the queue: {sorted(extra)}"


def test_no_finding_is_answered_twice():
    ids = [c.source_id for c in rg.CHECKS] + list(rg.NEEDS_HUMAN)
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"two verdicts for one finding: {sorted(dupes)}"


def test_every_check_carries_evidence_that_could_be_a_verified_note():
    """`GapQueue.advance` refuses `Verified` with an empty note, deliberately:
    "Verified with no measurement is the claim this whole queue exists to stop
    being made." An evidence string that cannot serve as that note would make
    the closure path fail at the last step, or tempt someone to loosen it."""
    for c in rg.CHECKS:
        assert c.evidence.strip(), f"{c.source_id}: no evidence string"
        assert len(c.evidence) > 30, (
            f"{c.source_id}: evidence {c.evidence!r} is too thin to send "
            f"a reader to the code")


def test_needs_human_rows_say_WHY_no_predicate_exists():
    for sid, why in rg.NEEDS_HUMAN.items():
        assert len(why) > 60, f"{sid}: 'needs human' with no reason is a shrug"


# ---------------------------------------------------------------------------
# the primitives, and the ways they have been wrong
# ---------------------------------------------------------------------------

def test_no_predicate_raises():
    """A predicate that throws must be reported NEEDS-HUMAN, never CLOSED —
    and it should not be throwing in the first place."""
    for c in rg.CHECKS:
        try:
            c.closed()
        except Exception as e:            # pragma: no cover - a real failure
            pytest.fail(f"{c.source_id} predicate raised {type(e).__name__}: {e}")


def test_a_raising_predicate_degrades_to_needs_human_not_closed():
    boom = rg.Check("X1", "a predicate that explodes",
                    lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    orig = rg.CHECKS
    try:
        rg.CHECKS = (boom,)
        rows = {r.source_id: r for r in rg.reconcile()}
    finally:
        rg.CHECKS = orig
    assert rows["X1"].verdict == rg.NEEDS
    assert "RuntimeError" in rows["X1"].evidence


def test_has_is_multiline_so_a_line_anchor_means_a_line():
    """MEASURED while writing this file: `^renders/` without re.MULTILINE
    anchors at the start of the WHOLE FILE, so gap J6 reported OPEN against a
    `.gitignore` that ignores `renders/` on line 25."""
    assert rg.has(".gitignore", r"^renders/")
    assert rg.has(".gitignore", r"^data/exports/")


def test_defines_reads_the_AST_not_the_prose():
    """`docs/GAP-REGISTER.md` names every missing symbol, and so do the
    docstrings of the modules that fixed them. If `defines` were a grep, the
    register would be able to close its own findings by quoting them."""
    assert rg.defines("navalai/gaps.py", "GapQueue")
    # present only inside strings/comments in this module, never defined here
    assert not rg.defines("navalai/gaps.py", "select_stock_thickness_m")
    assert not rg.defines("navalai/limits.py", "select_stock_thickness_m")
    assert rg.defines("navalai/rules/iso12215.py", "select_stock_thickness_m")


def test_before_compares_the_code_not_the_comment_that_describes_it():
    """`run-case.sh`'s header quotes both `rm -rf constant/polyMesh` and the
    concurrency message while EXPLAINING the old broken order, so a
    prose-matching `before` compares two comments and answers about a file it
    has not read. Gap F11's predicate anchors on the guard statement itself."""
    assert rg.before("navalai/cfd/run-case.sh",
                     r'if \[ "\$\{MESH_ONLY:-0\}" != "1" \] && solve_running',
                     r"^rm -rf constant/polyMesh")
    assert not rg.before("navalai/cfd/run-case.sh",
                         r"^rm -rf constant/polyMesh",
                         r'if \[ "\$\{MESH_ONLY:-0\}" != "1" \] && solve_running')


def test_a_comment_cannot_close_a_gap():
    """THE MEASURED INCIDENT, 2026-08-06, on this script's first `--apply`.

    Gap B4 is "payload_kg is a flat 800 kg regardless of crew". Its predicate
    included `has("navalai/energy.py", "crew")` — and energy.py line 19 is:

        payload_kg: float = 800.0          # crew + stores + water

    The word occurs in the COMMENT DESCRIBING THE DEFECT. B4 was reported
    CLOSED and written to Closed in an append-only log with no reopen edge;
    332 transitions had to be unwound.

    The hazard is structural, not careless: every fix in this codebase quotes
    the defect it fixed, so the vocabulary of every OPEN gap is present
    verbatim in the file that would close it. `code()` is the answer, and this
    is the assertion that keeps it true.
    """
    assert rg.has("navalai/energy.py", r"crew"), "the comment is still there"
    assert not rg.has_code("navalai/energy.py", r"crew"), (
        "a comment about crew mass would close gap B4 again")
    b4 = next(c for c in rg.CHECKS if c.source_id == "B4")
    assert not b4.closed(), (
        "B4 is OPEN: nothing scales payload_kg with mission.crew")


def test_a_docstring_cannot_close_a_gap_either():
    """`navalai/surrogate.py` opens by NAMING gap A4 — 'is_ood() had TWO call
    sites in the whole repository and both were in tests'. `navalai/evaluate.py`
    likewise recounts the ladder gaps in its module docstring. Prose that
    describes an absence must not be able to answer for its presence."""
    assert rg.has("navalai/evaluate.py", r"was imported outside the tests")
    assert not rg.has_code("navalai/evaluate.py", r"was imported outside the tests")


def test_an_inline_string_is_data_and_still_counts_as_code():
    """The opposite error, and the reason `code()` blanks docstrings and
    comments rather than every string: requirement names and dict keys ARE the
    code. Blanking all strings made gaps B1, B2 and A2 unclosable."""
    assert rg.has_code("navalai/translate.py", r'"carries-target"')
    assert rg.has_code("navalai/translate.py", r'"length-hint"')


def test_a_missing_file_answers_absent_rather_than_raising():
    assert rg.text("navalai/does_not_exist.py") == ""
    assert not rg.has("navalai/does_not_exist.py", r".")
    assert not rg.defines("navalai/does_not_exist.py", "anything")


# ---------------------------------------------------------------------------
# the closure path
# ---------------------------------------------------------------------------

def _queue_with(tmp_path, source_id: str = "Z9") -> tuple[GapQueue, str]:
    from navalai.gaps import GapEvent
    q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    g = q.emit(GapEvent(component="test", evidence="e", blocking="b",
                        severity=Severity.HIGH, title="a filed finding"),
               source_id=source_id)
    return q, g.id


def test_apply_walks_the_lifecycle_one_legal_step_at_a_time(tmp_path):
    """There is no Open -> Closed edge and this script must not invent one.
    The intermediate states are what let a reader see that a closure was
    reasoned about rather than asserted."""
    q, gid = _queue_with(tmp_path)
    rows = [rg.Row("Z9", rg.CLOSED, "navalai/x.py::thing does the missing thing")]
    moved = rg.apply(rows, q)
    assert moved and gid in moved[0]
    gap = q.get(gid)
    assert gap.state is GapState.CLOSED
    states = [h[0] for h in gap.history]
    assert states == ["Open", "Investigating", "Prototype", "Verified", "Closed"]


def test_the_verified_step_records_the_evidence_it_was_closed_on(tmp_path):
    q, gid = _queue_with(tmp_path)
    ev = "navalai/rules/iso12215.py::select_stock_thickness_m derives the sheet"
    rg.apply([rg.Row("Z9", rg.CLOSED, ev)], q)
    notes = {state: note for state, _utc, note in q.get(gid).history}
    assert ev in notes["Verified"], (
        "a closure whose record cannot say WHAT was measured is the rumour "
        "this queue exists to refuse")


def test_apply_never_closes_an_open_or_needs_human_row(tmp_path):
    """The whole point. A wrongly-closed gap is more expensive than a wrongly
    open one, because it is the one that stops anyone looking."""
    for verdict in (rg.OPEN, rg.NEEDS):
        q, gid = _queue_with(tmp_path / verdict)
        rg.apply([rg.Row("Z9", verdict, "still absent")], q)
        assert q.get(gid).state is GapState.OPEN


def test_apply_is_idempotent(tmp_path):
    q, gid = _queue_with(tmp_path)
    rows = [rg.Row("Z9", rg.CLOSED, "navalai/x.py::thing does the missing thing")]
    assert rg.apply(rows, q)
    assert rg.apply(rows, q) == [], "a second run must not re-append transitions"
    assert q.get(gid).state is GapState.CLOSED


def test_the_log_replays_to_the_same_states(tmp_path):
    """Append-only means the file IS the state. If a replay disagreed with the
    in-memory queue, the closures would live only in this process."""
    q, gid = _queue_with(tmp_path)
    rg.apply([rg.Row("Z9", rg.CLOSED, "navalai/x.py::thing is present")], q)
    again = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    assert again.get(gid).state is GapState.CLOSED


# ---------------------------------------------------------------------------
# the negative control
# ---------------------------------------------------------------------------

# The register's own header: "seven independent audits of the live checkout at
# 5bbffb7". Every one of its 119 findings was true of that tree, so a predicate
# that reports CLOSED there cannot tell a fix from the defect it fixed. This is
# the same idea as `test_hypar_negative_control_fails_developability` in the
# manufacturing suite: a metric with no negative control is not a metric.
AUDIT_BASELINE = "5bbffb7"


def _export(ref: str):
    import subprocess
    import tarfile
    import tempfile

    if subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"],
                      cwd=_ROOT, capture_output=True).returncode != 0:
        pytest.skip(f"{ref} is not in this clone's history (shallow clone?)")
    tmp = tempfile.TemporaryDirectory()
    tar = pathlib.Path(tmp.name) / "t.tar"
    with tar.open("wb") as fh:
        subprocess.run(["git", "archive", ref], cwd=_ROOT, stdout=fh, check=True)
    dest = pathlib.Path(tmp.name) / "tree"
    dest.mkdir()
    with tarfile.open(tar) as t:
        t.extractall(dest, filter="data")
    return tmp, dest


def test_no_predicate_reports_closed_at_the_commit_the_register_audited():
    """MEASURED when this control was first run: FOUR rows reported CLOSED at
    5bbffb7, from a tree in which all four defects were live.

      D15  `.github/workflows/gates.yml` already contained the word "--strict"
           — in a comment reading "Deliberately NOT --strict here" — and
           already `cat`-ed requirements-optional.txt without installing it.
      D16  the `-x` was written `"--no-header", "-x"`, which the predicate's
           `g.suite, "-x"` pattern never matched in either direction.
      F16  `not ledger_has("Gate 2M")` is TRUE when there is no ledger, and at
           5bbffb7 `data/gate-ledger.json` had not been written. An absent
           record read as a green gate — gap D3's exact shape.
      F17  the same.

    Three of the four would have closed a live gap. This test is what caught
    them, and it is why it stays.
    """
    tmp, dest = _export(AUDIT_BASELINE)
    try:
        with rg.at_root(dest):
            closed = [r.source_id for r in rg.reconcile() if r.verdict == rg.CLOSED]
    finally:
        tmp.cleanup()
    assert not closed, (
        f"these predicates report CLOSED against {AUDIT_BASELINE}, the tree "
        f"every register finding was measured on: {sorted(closed)}. A "
        f"predicate that cannot fail on the defect cannot verify the fix.")


def test_the_closures_are_discriminating_not_merely_true():
    """The other half of the control: a closure must have FLIPPED. If a row
    reads CLOSED both now and at the audit baseline it proves nothing, and this
    would fail before the previous test does if the table were ever seeded with
    trivially-true predicates."""
    tmp, dest = _export(AUDIT_BASELINE)
    try:
        now = {r.source_id: r.verdict for r in rg.reconcile()}
        with rg.at_root(dest):
            then = {r.source_id: r.verdict for r in rg.reconcile()}
    finally:
        tmp.cleanup()
    flipped = [s for s, v in now.items()
               if v == rg.CLOSED and then.get(s) != rg.CLOSED]
    assert len(flipped) == sum(1 for v in now.values() if v == rg.CLOSED)


# ---------------------------------------------------------------------------
# the invariant that matters after this session
# ---------------------------------------------------------------------------

def test_no_gap_is_closed_in_the_queue_while_the_code_says_it_is_open():
    """THE DANGEROUS DIRECTION, and the only one this asserts.

    Queue-Open-but-code-Closed is staleness: someone landed a fix and has not
    run `--apply`. Annoying, visible, harmless — and asserting on it would make
    this suite fail on every concurrent agent's uncommitted work, which trains
    people to ignore it.

    Queue-Closed-but-code-Open is the opposite: a finding that nobody will ever
    look at again because a row says it is handled. The gap log has no reopen
    edge — a recurrence is filed as a NEW gap — so this is the state that has
    to be impossible.
    """
    q = GapQueue()
    by_source = {g.source_id: g for g in q.all() if g.source_id}
    rows = rg.reconcile()
    wrong = [r.source_id for r in rows
             if r.verdict != rg.CLOSED
             and by_source.get(r.source_id)
             and by_source[r.source_id].state is GapState.CLOSED]
    assert not wrong, (
        f"these gaps are Closed in data/evolution/gaps.jsonl while the code "
        f"still shows the defect: {sorted(wrong)}. Either the predicate is "
        f"wrong or the closure was. File a NEW gap; do not edit the log.")


def test_the_queue_is_the_119_findings_the_register_holds():
    """Guard against a re-import doubling the queue, which would make every
    count in the report meaningless. `GapQueue.emit` is idempotent on
    source_id; this is the assertion that it stayed that way."""
    ids = [json.loads(line)["gap_id"]
           for line in (_ROOT / "data" / "evolution" / "gaps.jsonl")
           .read_text().splitlines() if line.strip()]
    opened = [json.loads(line) for line in
              (_ROOT / "data" / "evolution" / "gaps.jsonl").read_text().splitlines()
              if line.strip() and json.loads(line)["kind"] == "open"]
    assert len(opened) == 119, f"{len(opened)} findings filed, expected 119"
    assert len(set(ids)) == len({r["gap_id"] for r in opened})
