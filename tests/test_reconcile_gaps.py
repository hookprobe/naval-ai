"""Gate SG-R: the gap queue is reconciled against the CODE, not against prose.

`navalai.gaps` turns `docs/GAP-REGISTER.md` into work items. It cannot turn
them into TRUE work items: it seeded every finding as `Open`, which was the
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
import re
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from navalai.gaps import (GapQueue, GapState, Severity,   # noqa: E402
                          import_gap_register)
from navalai.gates import GATES                          # noqa: E402
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

def _answered() -> set[str]:
    """Every finding this script has a verdict for, of any kind.

    RETIRED belongs here for the same reason NEEDS-HUMAN does: it is an ANSWER.
    What it must never be folded into is CLOSED — that distinction is asserted
    separately, below.
    """
    return {c.source_id for c in rg.CHECKS} | set(rg.NEEDS_HUMAN) | set(rg.RETIRED)


def _queue_source_ids(tmp_path=None) -> set[str]:
    """The filed findings, from the live queue or reconstructed if absent.

    THE REASON THIS IS NOT JUST `GapQueue()`: `data/evolution/` is gitignored,
    so on a fresh clone the queue is EMPTY and this set is empty — and a
    coverage assertion over an empty set passes while verifying nothing. That is
    gap D3's shape ("prior is None -> ok = True") rebuilt inside the suite that
    guards against it, and this repository has already shipped it once in this
    very file (`not ledger_has("Gate 2M")` was true of a ledger that did not
    exist). The findings are committed in docs/GAP-REGISTER.md, so the honest
    move is to reconstruct rather than to skip.
    """
    q = GapQueue()
    if not q.all():
        assert tmp_path is not None, "reconstruction needs a scratch path"
        q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
        import_gap_register(queue=q)
    ids = {g.source_id for g in q.all() if g.source_id}
    assert len(ids) == 123, (
        f"{len(ids)} findings in the queue, expected the register's 123. An "
        f"under-populated queue makes every coverage assertion below vacuous.")
    return ids


def test_every_queued_finding_gets_an_answer(tmp_path):
    """No row may be silently skipped.

    `navalai.gaps._split_row` learned this: a parser that dropped the three
    rows containing an escaped pipe reported a SMALLER register than the one on
    disk — two HIGH and one CRITICAL finding, gone, with the importer saying
    "names no level". A reconciler that answers 100 of 119 has the same shape.
    """
    missing = _queue_source_ids(tmp_path) - _answered()
    assert not missing, f"queued findings with no verdict: {sorted(missing)}"


def test_nothing_is_answered_that_was_never_filed(tmp_path):
    extra = _answered() - _queue_source_ids(tmp_path)
    assert not extra, f"verdicts for findings that are not in the queue: {sorted(extra)}"


def test_no_finding_is_answered_twice():
    ids = ([c.source_id for c in rg.CHECKS] + list(rg.NEEDS_HUMAN)
           + list(rg.RETIRED))
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


def test_n6_is_needs_human_and_says_why_it_is_neither_gateable_nor_retirable():
    """N6 was the second gap-id namespace `docs/BUILD-PLAN.md` §15.2 item 1
    recorded as existing "only in CLAUDE.md" — no register row, no predicate,
    no gate, no count. Section N of the register files it.

    NEEDS-HUMAN is a JUDGEMENT and this pins the two halves of it, because the
    dangerous move would have been to pick one of the other two dispositions
    for tidiness:

    * not RETIRED — that verdict is reserved for a proposition about a MOMENT
      (J9's sliding git window, J10's one working tree), and "this committed
      sentence presents a measurement as current" is a property of the
      committed text, i.e. of a checkout. Retiring a live finding is the
      expensive direction: it stops anyone looking.
    * not a GATE — `runs/` is gitignored, so "does every cited run directory
      exist?" is GREEN on the Mac simulation node and RED on every fresh
      clone. That is gap D3's shape (an environment fact scored as a project
      fact), which is exactly what N6 is about.
    """
    assert "N6" in rg.NEEDS_HUMAN
    why = rg.NEEDS_HUMAN["N6"]
    assert "NOT retirable" in why and "not gateable either" in why.lower()
    assert "CLEARING CONDITION" in why, (
        "a NEEDS-HUMAN with no clearing condition is a permanent shrug")
    assert "N6" not in rg.RETIRED, "a live finding was filed as a retirement"
    rows = {r.source_id: r for r in rg.reconcile()}
    assert rows["N6"].verdict == rg.NEEDS
    assert rows["N6"].verdict != rg.CLOSED


def test_apply_never_closes_the_needs_human_row(tmp_path):
    """`--apply` writes into an append-only log with no reopen edge, and
    NEEDS-HUMAN means "no predicate can honestly answer this". Closing one
    would record a verdict nothing measured — B4's incident, which cost 332
    unwound transitions, in its most deliberate form."""
    q, gid = _queue_with(tmp_path, source_id="N6")
    rg.apply([rg.Row("N6", rg.NEEDS, rg.NEEDS_HUMAN["N6"])], q)
    assert q.get(gid).state is GapState.OPEN


# ---------------------------------------------------------------------------
# gap <-> gate linkage: a NAME is not a LINK
# ---------------------------------------------------------------------------
#
# MEASURED 2026-08-11 by walking this script's AST (docs/BUILD-PLAN.md §15.2
# item 3, P0-3): of 120 `Check` rows, 14 named a gate somewhere inside their
# evidence string and only 7 were machine-linked — five through `ledger_has()`,
# plus E1 and J5 grepping `navalai/gates.py` for a `Gate("Gate X"` literal.
# EIGHT named a gate that nothing verified. `Check` had exactly three fields,
# `Gate` had none pointing back, there was no mapping table and no test, so
# "which gap blocks which gate" was a question the repository could not answer.

_GATE_IN_PROSE = re.compile(r"\bGate [\w.-]+")


def _gates_named_in(evidence: str) -> set[str]:
    """Gate names a READER would take out of an evidence string.

    Trailing punctuation is stripped because the strings are English: "(Gate
    R3) exercises it", "Gate 6R's state", "Gate 2G makes the skip LOUD".
    """
    return {m.group(0).rstrip(".,;:-") for m in _GATE_IN_PROSE.finditer(evidence)}


def test_every_gate_a_check_names_exists_in_the_gate_registry():
    """P0-3's bar. A `gate` value that does not resolve is worse than none:
    it looks like a link and answers nothing, which is this repository's oldest
    defect class wearing a new hat (an absence rendered as a result).

    It runs in BOTH directions against `navalai/gates.py` — the field must name
    a real row, and a gate named in prose must be a real row too — so renaming
    a gate breaks the register loudly instead of orphaning the rows that point
    at it.
    """
    known = {g.name for g in GATES}
    assert len(known) == len(GATES), "duplicate gate names in GATES"

    for c in rg.CHECKS:
        if c.gate is not None:
            assert c.gate in known, (
                f"{c.source_id}.gate = {c.gate!r} is not a row in "
                f"navalai.gates.GATES. Known: {sorted(known)}")
        for named in _gates_named_in(c.evidence):
            assert named in known, (
                f"{c.source_id}'s evidence names {named!r}, which is not a row "
                f"in navalai.gates.GATES — a citation nothing can follow")


def test_a_check_that_names_a_gate_in_prose_also_carries_it_as_a_field():
    """The drift guard, and the reason the field is not just documentation.

    Prose and field must not come apart: a row that names a gate in its
    evidence and leaves `gate` unset is back to the pre-P0-3 state for that
    row, invisibly. The direction is one-way on purpose — D9 names two gates
    ("Gate 6R's threshold parity could become Gate 6's VERDICT parity") and the
    gate the row is ABOUT is Gate 6 — so the requirement is that `gate` is SET
    and is one of the gates the evidence names.
    """
    unlinked = []
    for c in rg.CHECKS:
        named = _gates_named_in(c.evidence)
        if not named:
            continue
        if c.gate is None or c.gate not in named:
            unlinked.append(f"{c.source_id}: names {sorted(named)}, gate={c.gate!r}")
    assert not unlinked, (
        "these rows name a gate in prose that the `gate` field does not carry, "
        "so nothing can follow the link:\n  " + "\n  ".join(unlinked))

    # THE GUARD, FIRED. A test that only shows the current table is clean says
    # nothing about detection (docs/LESSONS.md defect class 3), and the state
    # it must detect is the one every one of these rows was in this morning:
    # a gate named in prose, no field, nothing linking them.
    stray = rg.Check("X1", "closed when Gate 0G pins the GATES list, and when "
                           "Gate 9Z (which does not exist) is green",
                     lambda: True)
    assert stray.gate is None, "the field must default to unlinked, not to a guess"
    assert _gates_named_in(stray.evidence) == {"Gate 0G", "Gate 9Z"}
    assert "Gate 9Z" not in {g.name for g in GATES}, (
        "the unresolvable name in this control became real; pick another")


def test_the_linkage_covers_the_fourteen_rows_the_audit_counted():
    """The census the field was added for, pinned so it cannot regress to prose.

    G4 is the fifteenth and it names no gate in its evidence — until 2026-08-11
    there was none to name. `eacb9ce` created Gate 6D and its ledger entry
    opens "GAP G4", so the link is the ledger's own statement rather than an
    inference, and it is the one this whole field exists to make queryable: G4
    is now the register row that says which gate is red.
    """
    linked = {c.source_id: c.gate for c in rg.CHECKS if c.gate is not None}
    assert linked == {
        "A1": "Gate R3", "D1": "Gate 0G", "D9": "Gate 6", "D10": "Gate 3",
        "D11": "Gate 4F", "D12": "Gate 4", "E1": "Gate 1H", "F16": "Gate 2M",
        "F17": "Gate 2U", "G4": "Gate 6D", "I10": "Gate 7", "I13": "Gate 4",
        "J1": "Gate 2M", "J3": "Gate 6R", "J5": "Gate 2G"}

    # The map is many-to-one and that is information, not a defect: two rows
    # are about Gate 4 and two about Gate 2M.
    from collections import Counter
    assert Counter(linked.values())["Gate 4"] == 2
    assert Counter(linked.values())["Gate 2M"] == 2


# ---------------------------------------------------------------------------
# retirement (PLM.md section 3 step 7) — and the thing it must never look like
# ---------------------------------------------------------------------------

def test_a_retired_row_says_why_it_is_not_a_property_of_a_checkout():
    """PLM section 3 step 7: "removed with a note, never left ambiguous".

    The note is the whole of the retirement. J9 ("7 of 10 recent commits
    comply") and J10 ("uncommitted CFD work sits in the working tree") are
    propositions about a MOMENT — one about a sliding window of git history,
    one about one machine at one instant — so no predicate over a checkout can
    answer them stably, in either direction. That is a different claim from "we
    have not written the predicate yet", which is what NEEDS-HUMAN means, and
    the note is where the difference is stated.
    """
    assert set(rg.RETIRED) == {"J9", "J10"}, (
        "retiring a row is a judgement, not a cleanup; a new one needs its own "
        "note and its own commit")
    for sid, why in rg.RETIRED.items():
        assert len(why) > 200, f"{sid}: a retirement with a one-liner is a shrug"
        assert "NOT A PROPERTY OF THE CHECKOUT" in why, (
            f"{sid}: state the reason it cannot be a predicate, or it reads as "
            f"'we gave up'")


def test_a_retired_row_never_reads_as_fixed():
    """THE HAZARD, and the only reason RETIRED is a separate verdict.

    A reader scanning for what is left to do sees a column. If retirement
    landed in the CLOSED column the two rows would read as work someone did,
    and nothing was done to the code at all — the propositions were withdrawn.
    """
    rows = {r.source_id: r for r in rg.reconcile()}
    for sid in rg.RETIRED:
        assert rows[sid].verdict == rg.RETIRED_V
        assert rows[sid].verdict != rg.CLOSED
    assert rg.RETIRED_V not in (rg.CLOSED, rg.OPEN, rg.NEEDS)


def test_apply_never_closes_a_retired_row(tmp_path):
    """`--apply` writes into an append-only log with NO REOPEN EDGE. A
    retirement written there as a closure is permanent and is a lie about the
    code. B4 cost 332 unwound transitions for one wrong Closed."""
    q, gid = _queue_with(tmp_path, source_id="J9")
    rg.apply([rg.Row("J9", rg.RETIRED_V, rg.RETIRED["J9"])], q)
    assert q.get(gid).state is GapState.OPEN


def test_the_summary_counts_retired_in_its_own_column(tmp_path, capsys):
    q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    import_gap_register(queue=q)
    rg.report(rg.reconcile(), q)
    out = capsys.readouterr().out
    assert f"{len(rg.RETIRED)} retired" in out
    assert "retired != fixed" in out, (
        "the count is not enough — the word 'retired' beside a list of closures "
        "is read as 'done' at a glance")


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
# 5bbffb7". Every one of its original 119 findings was true of that tree, so a
# predicate that reports CLOSED there cannot tell a fix from the defect it
# fixed. This is the same idea as
# `test_hypar_negative_control_fails_developability` in the manufacturing
# suite: a metric with no negative control is not a metric.
#
# The rows added AFTER that audit (section T, 2026-08-07) are held to the same
# bar and it is not a courtesy: 5bbffb7 predates `suite_fingerprint`,
# `bootstrap` and `scripts/make_baseline.py` entirely, so an ABSENCE test
# (`lacks_code`) for any of the three would read CLOSED on a tree where the
# guard does not exist at all. That is why T1-T3's predicates are written as
# positive conjunctions.
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

def test_a6b_asks_for_the_recall_MEASUREMENT_not_merely_for_a_support_test(tmp_path):
    """A6b was NEEDS-HUMAN on the grounds that it is "a correction to A6,
    closed by the same code". If that were true it would not be a finding, and
    its predicate would be indistinguishable from A6's — so this doctors a copy
    of the tree the way `tests/test_pipeline.py` doctors a copy of
    `run-case.sh`, and requires the two verdicts to come apart.

    A6's clearing condition is that a support test EXISTS. A6b's is that the
    support test is MEASURED against a restricted training support, because
    A6b's finding is that the original experiment drew training and query hulls
    from the same box and so contained no out-of-distribution query at all.
    Remove the recall bar and only A6b may notice.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "navalai").mkdir()
    src = (_ROOT / "tests" / "test_phase3.py").read_text()
    doctored = src.replace("assert r_new >= r_old + 0.10",
                           "assert True   # the recall bar, removed")
    assert doctored != src, "the recall assertion moved; re-aim this control"
    (tmp_path / "tests" / "test_phase3.py").write_text(doctored)
    (tmp_path / "navalai" / "surrogate.py").write_text(
        (_ROOT / "navalai" / "surrogate.py").read_text())

    a6 = next(c for c in rg.CHECKS if c.source_id == "A6")
    a6b = next(c for c in rg.CHECKS if c.source_id == "A6b")
    with rg.at_root(tmp_path):
        assert a6.closed(), (
            "A6 should still read closed here — the support test is untouched")
        assert not a6b.closed(), (
            "A6b closed on a tree with no recall measurement, i.e. it is "
            "answering A6's question a second time")


def test_the_section_T_predicates_can_flip_and_T1_comes_apart_from_T2(tmp_path):
    """A predicate that cannot fail on the defect cannot verify the fix — and
    the mirror of it: a predicate that cannot PASS on the fix is a permanent
    OPEN wearing a clearing condition.

    RE-AIMED 2026-08-12, when T1-T3 landed. It used to doctor the tree in the
    CLOSING direction because all three read OPEN; both are closed now, so it
    doctors in the OPENING direction instead. The requirement is unchanged and
    it is the load-bearing one: T1 and T2 must COME APART. T2 is stated in the
    register as a consequence of T1, and a predicate that merely re-asked T1's
    question would answer T1 twice and T2 never.

    They come apart because the two fixes landed in different files. T1 is
    closed by `targets_fingerprint` being RECORDED in data/baselines.json —
    the row's own second arm, an equivalent targets guard — and T2 by the
    bootstrap drop no longer being conditioned on a target-blind id in
    flywheel.py. Remove either and only its own row notices.
    """
    (tmp_path / "navalai").mkdir()
    (tmp_path / "data").mkdir()
    src = (_ROOT / "navalai" / "flywheel.py").read_text()
    base = (_ROOT / "data" / "baselines.json").read_text()
    unconditional = "    if prior is not None and bootstrap:"
    assert unconditional in src, "the bootstrap branch moved; re-aim this control"
    assert '"targets_fingerprint"' in base, (
        "the committed baseline records no targets fingerprint; re-aim this "
        "control")

    t1 = next(c for c in rg.CHECKS if c.source_id == "T1")
    t2 = next(c for c in rg.CHECKS if c.source_id == "T2")

    def _plant(flywheel_src: str, baseline_text: str):
        (tmp_path / "navalai" / "flywheel.py").write_text(flywheel_src)
        (tmp_path / "data" / "baselines.json").write_text(baseline_text)
        rg._TEXT_CACHE.clear()
        rg._CODE_CACHE.clear()

    # (0) the tree as committed: both closed. Without this the control could
    #     be passing because the predicates never close on anything.
    _plant(src, base)
    with rg.at_root(tmp_path):
        assert t1.closed() and t2.closed()

    # (a) the targets guard is removed from the baseline and NOTHING ELSE
    #     changes: T1 re-opens, T2 stays closed. `suite_fingerprint` is still
    #     target-blind, so T1's first arm cannot rescue it.
    _plant(src, base.replace("targets_fingerprint", "targets_removed"))
    with rg.at_root(tmp_path):
        assert not t1.closed(), (
            "T1 stayed closed with no targets guard anywhere — it is "
            "answering some other question")
        assert t2.closed(), (
            "T2 re-opened on a change to the baseline file, i.e. it is "
            "answering T1's question")

    # (b) the bootstrap drop goes back to being conditioned on the target-blind
    #     id, and the baseline keeps its targets guard: T2 re-opens, T1 stays
    #     closed. This is the deadlock the row is about, restored verbatim.
    _plant(src.replace(unconditional,
                       '    if (prior is not None and bootstrap\n'
                       '            and prior.get("suite_fingerprint") != fp):'),
           base)
    with rg.at_root(tmp_path):
        assert not t2.closed(), (
            "T2 stayed closed with the deadlock condition restored")
        assert t1.closed(), (
            "T1 re-opened on a change to flywheel.py's bootstrap branch, i.e. "
            "it is answering T2's question")

    rg._TEXT_CACHE.clear()
    rg._CODE_CACHE.clear()


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


def test_the_queue_is_the_123_findings_the_register_holds(tmp_path):
    """Guard against a re-import doubling the queue, which would make every
    count in the report meaningless. `GapQueue.emit` is idempotent on
    source_id; this is the assertion that it stayed that way.

    It reads the LIVE log only if this checkout has one. It used to read it
    unconditionally and would therefore have died with FileNotFoundError on a
    fresh clone — the very defect the tests below are about, sitting in the
    assertion that counts the queue.

    119 -> 122 on 2026-08-11, then 122 -> 123 the same day when section N filed
    `N6`. This assertion is DOUBLE-ENTRY ONLY — it was
    written against the over-import direction (a mis-headed table that grew the
    queue 119 -> 121) and a number it verifies from below cannot notice a row
    the importer never read. Section T's three findings hid under it for four
    days; the direction it does not cover is now covered by
    `tests/test_gaps.py::test_a_gradeable_table_the_importer_cannot_see_is_fatal`.
    """
    q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    rep = import_gap_register(queue=q)
    assert len(rep.imported) == 123, (
        f"{len(rep.imported)} findings imported from docs/GAP-REGISTER.md, "
        f"expected 123")

    live = _ROOT / "data" / "evolution" / "gaps.jsonl"
    if not live.exists():
        pytest.skip("no live queue in this checkout (gitignored; --rebuild it)")
    recs = [json.loads(line) for line in live.read_text().splitlines()
            if line.strip()]
    opened = [r for r in recs if r["kind"] == "open"]
    assert len(opened) == 123, f"{len(opened)} findings filed, expected 123"
    assert len({r["gap_id"] for r in recs}) == len({r["gap_id"] for r in opened})


# ---------------------------------------------------------------------------
# the queue does not survive a clone — and that is handled, not ignored
# ---------------------------------------------------------------------------
#
# `data/evolution/` is gitignored deliberately (the reasoning is in
# reconcile_gaps.py's module docstring: the log is DERIVED from two committed
# sources, it is append-only with machine-minted ids so concurrent agents
# produce unresolvable conflicts, and tracked files the tooling rewrites have
# already cost this repository a dirty tree on every test run and an unasked
# `git checkout --`). What that decision owes in return is exactly two
# properties, and these are them.

def test_an_absent_queue_is_loud_and_never_reads_as_no_gaps(tmp_path, capsys):
    """THE FAILURE MODE, stated by this repository three times already: gap D3
    (`data/baselines.json` missing -> `prior is None -> ok = True` -> the first
    retrain always deployed), gap J5 (benchmark geometry ignored -> a validation
    that silently skipped), and this script's own F16/F17 predicates, where
    `not ledger_has("Gate 2M")` was TRUE of a ledger file that did not exist.

    An empty queue must therefore be a banner and a non-zero exit, never a
    report full of blanks that a reader skims as "nothing outstanding".
    """
    rc = rg.main(["--gaps", str(tmp_path / "nowhere" / "gaps.jsonl")])
    out = capsys.readouterr().out
    assert rc != 0, "an absent queue exited 0"
    assert "THE GAP QUEUE IS EMPTY OR ABSENT" in out
    assert "--rebuild" in out, "loud is not enough; it must say how to fix it"


def test_the_queue_is_reconstructible_from_committed_files_alone(tmp_path):
    """The other half. Loud is only acceptable if the fix is one command.

    Reconstruction reads docs/GAP-REGISTER.md for the findings and
    `reconcile_gaps.CHECKS` for their verdicts — both committed — so a fresh
    clone reaches the same partition as the machine that recorded it, WITHOUT
    the log being a tracked file that every agent appends to.
    """
    q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    rows = rg.reconcile()
    n, moved = rg.rebuild(q, rows)
    assert n == 123
    measured_closed = {r.source_id for r in rows if r.verdict == rg.CLOSED}
    assert len(moved) == len(measured_closed)
    got = {g.source_id for g in q.all() if g.state is GapState.CLOSED}
    assert got == measured_closed
    # and nothing that is not CLOSED came along for the ride
    for r in rows:
        if r.verdict != rg.CLOSED:
            assert q.by_source(r.source_id).state is GapState.OPEN


def test_rebuild_is_idempotent(tmp_path):
    """It has to be safe to run when you are not sure what state you are in;
    otherwise nobody runs it. `emit` is idempotent on source_id and `apply`
    skips an already-Closed gap, and this is the assertion that both stay so."""
    q = GapQueue(JsonlLog(tmp_path / "gaps.jsonl"))
    rows = rg.reconcile()
    rg.rebuild(q, rows)
    lines = len((tmp_path / "gaps.jsonl").read_text().splitlines())
    n, moved = rg.rebuild(q, rows)
    assert n == 0 and moved == []
    assert len((tmp_path / "gaps.jsonl").read_text().splitlines()) == lines


def test_the_gitignore_still_says_why_the_queue_is_not_tracked():
    """A decision that is not written down is re-litigated by the next agent,
    who will see a lost queue and track the file. The entry carries the reason
    and the reconstruction command."""
    ignore = (_ROOT / ".gitignore").read_text()
    assert "data/evolution/" in ignore
    assert "reconcile_gaps.py --rebuild" in ignore
