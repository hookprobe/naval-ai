"""Gate tests for the gap queue (`navalai.gaps`).

PLM.md §3 step 4: code + gate test in the same change, and the comment names
the motivating incident.

INCIDENT (MEASURED here, 2026-08-06). The first importer split the register's
markdown rows on every `|`, and three rows carry an ESCAPED pipe inside their
prose — `setFields … \\|\\| true`, `GM 0.15\\|v\\|+0.05`, `rho tracks \\|delta\\|`.
Every column right of the escape shifted, so the severity cell of F10, H1 and I2
came back holding a fragment of their own Finding text. The importer then said
"names no level" and SKIPPED THREE REAL FINDINGS — two HIGH and one MED —
reporting 116 work items from a register that holds 119. A parser that silently
drops rows it mis-split reports a smaller register than the one on disk, which
is the same class of defect as scoring an unmeasured metric as perfect: an
absence rendered as a result.

The second lesson, tested below: the two rows that are GENUINELY not findings
(B10 `*(decision input)*` and F20 `—`, "no defect — recorded so it is not
re-litigated") are skipped AND NAMED, never assigned a guessed severity.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path

import pytest

from navalai.gaps import (EVENT_KINDS, GAP_STATE_ORDER, GapEvent,
                          GapQueue, GapState, IllegalGapTransition,
                          REGISTER_PATH, Severity, from_stage_check,
                          import_gap_register, legal_gap_targets)
from navalai.pipeline import LogTruncated, Stage, Terminal, check_mesh

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def queue(tmp_path) -> GapQueue:
    return GapQueue(tmp_path / "gaps.jsonl")


def _event(**kw) -> GapEvent:
    base = dict(component="navalai.cfd.post", evidence="measured drift 12.4%",
                blocking="Gate 2M verdict", severity=Severity.HIGH)
    base.update(kw)
    return GapEvent(**base)


# ---------------------------------------------------------------------------
# An event must be a finding, not a rumour
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["component", "evidence", "blocking"])
def test_an_event_without_who_what_or_why_is_refused(field):
    # A finding with no evidence cannot be reproduced and a finding that does
    # not say what it blocks cannot be prioritised. `docs/GAP-REGISTER.md` is
    # 434 lines of demonstration that both are worth insisting on.
    with pytest.raises(ValueError):
        _event(**{field: "   "})


def test_an_event_kind_outside_the_four_is_refused():
    assert EVENT_KINDS == ("unsupported", "unknown", "missing", "failed_validation")
    for kind in EVENT_KINDS:
        assert _event(kind=kind).kind == kind
    with pytest.raises(ValueError):
        _event(kind="probably_fine")


def test_a_failed_stage_check_becomes_a_gap_event_and_a_passing_one_does_not():
    """The wiring: a genome that dies at a stage leaves a work item too."""
    died = check_mesh({"zero_volume_cells": 0, "wrong_oriented_faces": 10,
                       "max_skewness": 42.9417})
    ev = from_stage_check(died, genome_id="abc123")
    assert ev.kind == "failed_validation"
    assert "max_skewness" in ev.evidence and "42.9417" in ev.evidence
    assert "abc123" in ev.blocking and Stage.MESHING.value in ev.blocking
    assert died.terminal is Terminal.FAILED_MESH
    ok = check_mesh({"zero_volume_cells": 0, "wrong_oriented_faces": 0,
                     "max_skewness": 8.93076})
    with pytest.raises(ValueError):
        from_stage_check(ok)          # a queue that accepts successes is noise


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def test_the_gap_lifecycle_is_forward_only_one_step_at_a_time(queue):
    assert [s.value for s in GAP_STATE_ORDER] == \
        ["Open", "Investigating", "Prototype", "Verified", "Closed"]
    gap = queue.emit(_event())
    assert gap.id == "G-001" and gap.state is GapState.OPEN
    with pytest.raises(IllegalGapTransition):            # skipping a state
        queue.advance(gap.id, GapState.VERIFIED, note="looks fine")
    queue.advance(gap.id, GapState.INVESTIGATING)
    with pytest.raises(IllegalGapTransition):            # backwards
        queue.advance(gap.id, GapState.OPEN)
    with pytest.raises(IllegalGapTransition):            # standing still
        queue.advance(gap.id, GapState.INVESTIGATING)
    queue.advance(gap.id, GapState.PROTOTYPE)
    queue.advance(gap.id, GapState.VERIFIED, note="re-ran: drift 1.2%, settled")
    queue.advance(gap.id, GapState.CLOSED)
    assert queue.get(gap.id).is_closed
    with pytest.raises(IllegalGapTransition):            # closed is closed
        queue.advance(gap.id, GapState.OPEN)
    assert legal_gap_targets(GapState.CLOSED) == frozenset()


def test_verified_without_a_measurement_is_refused(queue):
    """'Verified' with nothing measured is the claim this queue exists to stop.

    CLAUDE.md rule 1: a measurement beats a document, and a document beats an
    intention. Three claims in that file were false until someone re-ran them.
    """
    gap = queue.emit(_event())
    queue.advance(gap.id, GapState.INVESTIGATING)
    queue.advance(gap.id, GapState.PROTOTYPE)
    with pytest.raises(IllegalGapTransition):
        queue.advance(gap.id, GapState.VERIFIED)
    with pytest.raises(IllegalGapTransition):
        queue.advance(gap.id, GapState.VERIFIED, note="   ")
    queue.advance(gap.id, GapState.VERIFIED, note="MEASURED: 0 of 200 recur")


def test_ids_are_unique_and_the_priority_order_is_derived_not_typed(queue):
    for sev in (Severity.LOW, Severity.CRITICAL, Severity.MED, Severity.HIGH):
        queue.emit(_event(severity=sev, title=f"{sev.value} thing"))
    assert [g.id for g in queue.all()] == ["G-001", "G-002", "G-003", "G-004"]
    assert [g.severity for g in queue.open_queue()] == [
        Severity.CRITICAL, Severity.HIGH, Severity.MED, Severity.LOW]
    queue.advance("G-002", GapState.INVESTIGATING)       # CRITICAL, still open
    queue.emit(_event(severity=Severity.CRITICAL))
    assert queue.open_queue()[0].id == "G-002"           # ties break by id


# ---------------------------------------------------------------------------
# Append-only, same rule as the archive
# ---------------------------------------------------------------------------

def test_the_gap_queue_is_append_only(queue):
    gap = queue.emit(_event())
    snapshot = queue.log.path.read_bytes()
    queue.advance(gap.id, GapState.INVESTIGATING)
    queue.assign(gap.id, "cfd-engineer")
    after = queue.log.path.read_bytes()
    assert after.startswith(snapshot), "a state change rewrote a prior record"
    assert len(after) > len(snapshot)
    assert not hasattr(queue.log, "update") and not hasattr(queue.log, "delete")
    # A state change appends; the ORIGINAL open record still says Open.
    first = queue.log.read()[0]
    assert first["kind"] == "open" and first["state"] == "Open"
    assert queue.get(gap.id).state is GapState.INVESTIGATING


def test_the_queue_replays_from_the_file(queue):
    a = queue.emit(_event(severity=Severity.CRITICAL), source_id="X9")
    queue.advance(a.id, GapState.INVESTIGATING)
    queue.assign(a.id, "verification")
    queue.emit(_event(severity=Severity.LOW))
    fresh = GapQueue(queue.log.path)
    assert len(fresh.all()) == 2
    reloaded = fresh.get(a.id)
    assert reloaded.state is GapState.INVESTIGATING
    assert reloaded.owner == "verification"
    assert fresh.by_source("X9").id == a.id
    assert fresh.next_id() == "G-003"


def test_a_shortened_queue_is_refused(queue):
    queue.emit(_event())
    queue.emit(_event())
    text = queue.log.path.read_text()
    queue.log.path.write_text(text.splitlines()[0] + "\n")
    with pytest.raises(LogTruncated):
        queue.emit(_event())


# ---------------------------------------------------------------------------
# The one-shot import of docs/GAP-REGISTER.md
# ---------------------------------------------------------------------------

def test_the_register_imports_as_work_items_not_prose(queue):
    """123 findings become a queue. MEASURED counts, so a silent drop shows up.

    The register's own severity definitions are the priorities; the count per
    level is asserted because a parser that quietly loses rows is the incident
    this file's docstring describes.

    119 -> 122 on 2026-08-11: section T (T1 HIGH, T2 MED, T3 HIGH) shipped on
    2026-08-07 with the header `| id | finding | where | severity |` and was
    invisible to this importer for four days. See
    `test_a_gradeable_table_the_importer_cannot_see_is_fatal` below.

    122 -> 123, same day: section N files `N6` (MED). It is the gap id that
    `docs/BUILD-PLAN.md` §15.2 item 1 recorded as existing "only in CLAUDE.md"
    — no register row, no predicate, no gate, no count. It is answered
    NEEDS-HUMAN rather than closed, and section N argues why it is neither
    gateable (`runs/` is gitignored, so the verdict would be a property of one
    machine) nor retirable (unlike J9/J10 it IS a property of the committed
    text).
    """
    report = import_gap_register(queue=queue)
    by_sev = collections.Counter(g.severity for g in report.imported)
    assert len(report.imported) == 123
    assert by_sev == {Severity.CRITICAL: 20, Severity.HIGH: 56,
                      Severity.MED: 36, Severity.LOW: 11}
    a1 = queue.by_source("A1")
    assert a1 is not None
    assert a1.severity is Severity.CRITICAL
    assert a1.state is GapState.OPEN
    assert "L2/L3 unreachable" in a1.title
    assert "evaluate.py" in a1.evidence
    assert a1.component == "docs/GAP-REGISTER.md#A1"
    # OWNER IS NEVER INFERRED. PLM §4 lists six roles; the register's section
    # headings are topics, not roles, and mapping one onto the other would be a
    # guess wearing a name.
    assert {g.owner for g in report.imported} == {"unassigned"}


def test_the_escaped_pipe_rows_import_with_their_real_severity(queue):
    """The measured incident: F10, H1 and I2 were dropped by a naive split.

    Each carries an escaped pipe inside its prose, which shifted every column
    to its right, so the severity cell held Finding text and the row was
    skipped as ungradeable. Three real findings — two HIGH, one MED — went
    missing from a 119-row register that reported 116.
    """
    import_gap_register(queue=queue)
    for source_id, sev in (("F10", Severity.HIGH), ("H1", Severity.MED),
                           ("I2", Severity.HIGH)):
        gap = queue.by_source(source_id)
        assert gap is not None, f"register row {source_id} was dropped again"
        assert gap.severity is sev
    # And the escape is unescaped in the text, not left as a literal backslash.
    assert "\\|" not in queue.by_source("F10").detail


def test_a_row_the_importer_cannot_grade_is_named_never_guessed(queue):
    """B10 and F20 are not findings, and inventing a severity for them would be
    the same move as scoring an unmeasured metric as perfect. They are skipped
    WITH A REASON, so a reader can see what the import chose not to file."""
    report = import_gap_register(queue=queue)
    skipped = dict(report.skipped)
    assert set(skipped) == {"B10", "F20"}
    for row, why in skipped.items():
        assert "names no level" in why
        assert queue.by_source(row) is None
    assert report.n_rows_seen == 125


def test_the_closure_table_is_not_imported_as_open_work(queue):
    """Section J's `| ID | Closed by | Mechanism |` table records gaps that were
    FIXED. It has no Sev column, and importing it would file eight closed
    defects as open ones."""
    import_gap_register(queue=queue)
    # J1 appears TWICE in the register: once in section J's findings table
    # (CRITICAL — five Gate 2M figures in circulation) and once in the closure
    # table below it. Exactly one gap, from the finding.
    assert sum(1 for g in queue.all() if g.source_id == "J1") == 1
    assert queue.by_source("J1").severity is Severity.CRITICAL
    assert all("Closed by" not in g.blocking for g in queue.all())
    # Section K's `| Phase | Deliverable | Status |` table has no ID column and
    # must contribute nothing either.
    assert not [g for g in queue.all() if (g.source_id or "").startswith("K")]


# ---------------------------------------------------------------------------
# UNDER-import: the direction nothing was watching
# ---------------------------------------------------------------------------

# The header section T shipped with on 2026-08-07, verbatim. It is fed to the
# guard below so the guard is demonstrably FIRING and not merely present —
# LESSONS defect class 3: "every threshold ships with a test feeding it the
# VERBATIM input it must reject."
BROKEN_T_HEADER = "| id | finding | where | severity |"


def _gradeable_headers_the_importer_cannot_see(md: str) -> list[tuple[int, str]]:
    """Header rows a HUMAN reads as a findings table and the importer skips.

    `import_gap_register`'s contract is exactly two things and both are
    case-sensitive: the first cell is `ID`, and some column name contains
    `Sev`. Anything with an id-ish first cell AND a sev-ish column that fails
    that contract is a table of findings which imports as NOTHING — no gap, no
    `skipped` entry, no count anywhere.

    Deliberately NOT a check that every table imports: section J's
    `| ID | Closed by | Mechanism |` closure record and section K's
    `| Phase | Deliverable | Status |` are correctly not findings, and the
    existing tests pin that they contribute nothing.
    """
    out: list[tuple[int, str]] = []
    for n, raw in enumerate(md.splitlines(), 1):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [re.sub(r"\*\*|__|`|\*", "", c).strip()
                 for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if not cells:
            continue
        looks_gradeable = (cells[0].lower() == "id"
                           and any(c.lower().startswith("sev") for c in cells[1:]))
        importer_sees = (cells[0] == "ID" and any("Sev" in c for c in cells))
        if looks_gradeable and not importer_sees:
            out.append((n, line))
    return out


def test_a_gradeable_table_the_importer_cannot_see_is_fatal(tmp_path, queue):
    """THE MEASURED INCIDENT, 2026-08-07 to 2026-08-11.

    Section T was added with `| id | finding | where | severity |`. The
    importer requires `cells[0] == "ID"` and a `"Sev"` column, case-sensitively,
    so T1, T2 and T3 — a HIGH that defeats the mechanism Gate 7 depends on, a
    MED and a second HIGH — were never filed, had no predicate in
    `scripts/reconcile_gaps.py`, and were in no count. The import reported 119
    findings from a register holding 122.

    The guard that existed ran in ONE direction only: the register records a
    mis-headed table that DOUBLE-imported and grew the queue 119 -> 121, and a
    test caught it. Nothing caught UNDER-import, and under-import is the more
    expensive half — a row imported twice is visible twice, a row never
    imported is invisible once and forever, which is this repository's oldest
    defect class (an absence rendered as a result) applied to its own work
    queue.
    """
    # 1. the real register: nothing gradeable may be invisible.
    invisible = _gradeable_headers_the_importer_cannot_see(
        REGISTER_PATH.read_text(encoding="utf-8"))
    assert invisible == [], (
        f"these tables in docs/GAP-REGISTER.md look like findings and import "
        f"as NOTHING: {invisible}. Normalise the header to "
        f"`| ID | ... | Sev |`; a finding the queue never saw is a finding "
        f"nobody owns.")

    # 2. and the guard FIRES on the verbatim header that hid T1-T3.
    broken = tmp_path / "BROKEN-REGISTER.md"
    broken.write_text(
        "## T · a findings table the importer cannot see\n\n"
        f"{BROKEN_T_HEADER}\n|---|---|---|---|\n"
        "| **T1** | a real HIGH finding | `navalai/flywheel.py` | **HIGH** |\n",
        encoding="utf-8")
    flagged = _gradeable_headers_the_importer_cannot_see(
        broken.read_text(encoding="utf-8"))
    assert [line for _n, line in flagged] == [BROKEN_T_HEADER], (
        "the guard did not fire on the exact header that caused the incident")

    # 3. the failure it describes is real in BOTH directions: nothing filed,
    #    and nothing even reported as skipped, which is why no count moved.
    report = import_gap_register(md_path=broken, queue=queue)
    assert report.imported == [] and report.skipped == []
    assert report.n_rows_seen == 0
    assert queue.by_source("T1") is None


def test_section_T_is_in_the_queue_with_its_own_severities(queue):
    """The fix, pinned. T1 is a HIGH: `suite_fingerprint` hashes the frozen
    suite's coordinates and labels but NOT its targets, so when the production
    Michell grid moved 41x14 -> 161x28 the frozen targets moved up to -4.2%
    (294.99 -> 282.55 Wh/NM) and the fingerprint stayed f37529748d22c684 either
    side — the guard Gate 7's ratchet depends on cannot see its own benchmark
    move."""
    import_gap_register(queue=queue)
    for source_id, sev in (("T1", Severity.HIGH), ("T2", Severity.MED),
                           ("T3", Severity.HIGH)):
        gap = queue.by_source(source_id)
        assert gap is not None, f"register row {source_id} is not in the queue"
        assert gap.severity is sev
    assert "suite_fingerprint" in queue.by_source("T1").detail


def test_the_import_is_a_one_shot_that_can_be_re_run(queue):
    first = import_gap_register(queue=queue)
    second = import_gap_register(queue=queue)
    assert len(second.imported) == 0
    assert len(second.already_present) == len(first.imported)
    assert len(queue.all()) == len(first.imported)
    # ...and across a fresh reader too, because the queue is replayed.
    assert len(GapQueue(queue.log.path).all()) == len(first.imported)


def test_the_import_does_not_touch_the_register_file(queue):
    """GAP-REGISTER.md is a DATED AUDIT RECORD and stays one.

    PLM §3 step 7: superseded material is removed with a note, never left
    ambiguous — and the register's own J7 row struck rows through WITH the
    superseding measurement beside them rather than deleting them. An importer
    that edited its source would destroy the thing it is reading.
    """
    before = hashlib.sha256(REGISTER_PATH.read_bytes()).hexdigest()
    import_gap_register(queue=queue)
    assert hashlib.sha256(REGISTER_PATH.read_bytes()).hexdigest() == before


def test_the_register_still_exists_and_is_still_the_audit_record():
    # It is explicitly NOT deleted by this module landing.
    assert REGISTER_PATH.exists()
    text = REGISTER_PATH.read_text()
    assert "Audited 2026-08-05" in text


# ---------------------------------------------------------------------------
# gap J1, applied to DOCUMENTS: a watermark has one home
# ---------------------------------------------------------------------------
#
# THE MEASURED INCIDENT, 2026-08-11. Commit `eacb9ce` created Gate 6D and wrote
# its watermark into `data/gate-ledger.json`. `ALIGNMENT.md`'s STEP/IGES/DXF row
# went on stating the same deviation in prose AND went on saying "no ledger row
# owns the clause" — a sentence that stopped being true the moment the ledger
# row was written. The same file also quoted Gate 4F's watermark. Two ledger
# numbers, in a document, with no owner and no expiry.
#
# The fence that would have caught it did not exist. `tests/test_red_by_record.py
# ::test_no_scope_or_detail_carries_a_measurement_the_ledger_owns` protects GATE
# ROWS in `navalai/gates.py` — in both directions, including "a watermark must
# not have been copied out of the ledger into the registry". NOTHING protected
# DOCUMENTS. `tests/test_gate_integrity.py::test_no_document_restates_a_gate_2m
# _figure` is the closest thing, and it is a hand-maintained list of SUPERSEDED
# Gate 2M strings: it can only ever name figures somebody already noticed.
#
# This is the general form: for every LIVE ledger watermark, the same five
# documents must not restate it.

_LEDGER_PATH = _ROOT / "data" / "gate-ledger.json"

# The same five files `test_no_document_restates_a_gate_2m_figure` scans, for
# the same reason. `docs/` is deliberately NOT scanned: `docs/GAP-REGISTER.md`
# is an immutable audit record and `docs/BUILD-PLAN.md` quotes measurements IN
# ORDER TO ARGUE ABOUT THEM, which is doing their job.
_WATERMARK_DOCS = ("ALIGNMENT.md", "PLM.md", "README.md", "MACBOOK.md",
                   "CLAUDE.md")

# Watermarks whose decimal form cannot be searched for as a bare number, with
# the reason. An entry here is NOT an exemption from the rule — it is a record
# that the rule cannot be MEASURED for that row, which `docs/LESSONS.md` defect
# class 1 says must be stated rather than defaulted to a pass. The assertions
# below require every key to still be a real, still-unsearchable ledger row, so
# a new non-distinctive watermark FAILS this test rather than quietly going
# uncovered.
_UNSEARCHABLE_WATERMARKS: dict[str, str] = {
    "Gate 6R": "the watermark is 0 — 'editions recorded, of 2 required'. A "
               "one-digit literal cannot be told apart from a line number, a "
               "count, a version or a decimal fragment anywhere in 40 KB of "
               "house rules, so a search for it would fire on everything and "
               "the fence would be turned off. Gate 6R's clearing condition "
               "costs no compute (a reviewer writes two dated editions into "
               "REVIEW['editions']), so this is expected to be short-lived.",
}


def _searchable_watermarks() -> dict[str, tuple[str, re.Pattern[str]]]:
    """{gate: (literal, pattern)} for every watermark a document could restate.

    Scope is the ledger's OWN watermark values and nothing else, because the
    false-positive direction is what kills a fence like this. Two deliberate
    narrowings, both measured:

    * STRING watermarks are skipped. Gate 2M's is the sentence "NONE — no
      reproducible measurement exists", and a document repeating THAT is
      pointing at the ledger, which is the behaviour this test wants.
    * The exact decimal literal only — no percent-suffixed short form.
      MEASURED 2026-08-11: extending the search to `75%` (Gate 2U's 75.0)
      fires on `CLAUDE.md:754`, "the GCI triplet budget in it is wrong by 75%",
      which has nothing to do with Gate 2U. The cost of the narrowing is
      stated rather than hidden: a document that writes Gate 2U's watermark as
      "75%" is NOT caught by this test.
    """
    out: dict[str, tuple[str, re.Pattern[str]]] = {}
    for gate, entry in json.loads(_LEDGER_PATH.read_text()).items():
        if gate.startswith("_"):
            continue
        wm = entry.get("watermark")
        if isinstance(wm, bool) or not isinstance(wm, (int, float)):
            continue
        lit = repr(wm)
        if sum(c.isdigit() for c in lit) < 3:      # see _UNSEARCHABLE_WATERMARKS
            continue
        # Bounded on both sides so 1225.7, 225.75 and 225.7e-3 do not match a
        # watermark of 225.7. This is the whole difference between a fence and
        # a nuisance.
        out[gate] = (lit, re.compile(r"(?<![\d.])" + re.escape(lit) + r"(?![\d])"))
    return out


def _documents_restating_a_watermark(text: str) -> list[str]:
    return [f"{gate} watermark {lit}"
            for gate, (lit, pat) in _searchable_watermarks().items()
            if pat.search(text)]


# ALIGNMENT.md, VERBATIM, as it stood at commit `eacb9ce` — the state this test
# was written to reject. Both offending sentences are here: the STEP/IGES/DXF
# row's restatement of Gate 6D's watermark (and its now-false claim that no
# ledger row owns the clause), and the red-gate roster's restatement of Gate
# 4F's. A guard that was never made to fire is not a guard (docs/LESSONS.md
# defect class 3), so the fixture is the real text and not a paraphrase.
PRE_FIX_ALIGNMENT_TEXT = (
    "**ONE SUB-CLAUSE IS STILL OPEN and is not softened here:** the panels are "
    "exportable but not yet refoldable to the hull — MEASURED max "
    "\\|refold − hull\\| 141.0 mm (bottom) and 225.7 mm (topside) against a "
    "5 mm bar, and it does not refine away (143.8 / 206.1 mm at 161 stations). "
    "... but Gate 6M is GREEN and no ledger row owns the clause, which is "
    "Gate 4F's shape before it was split out.\n"
    "  **2M, 2U, 6R and 4F** — Gate 4F (raw generative feasibility, watermark "
    "79.33%\n  against a ≥99% bar, measured 2026-08-07) was missing from this "
    "roster.\n")


def test_the_watermark_fence_fires_on_the_verbatim_text_that_motivated_it():
    """The guard, run against the input it exists to reject."""
    offenders = _documents_restating_a_watermark(PRE_FIX_ALIGNMENT_TEXT)
    assert sorted(offenders) == ["Gate 4F watermark 79.33",
                                 "Gate 6D watermark 225.7"], offenders

    # ...and it does NOT fire on the pointer that replaced them, which is the
    # other half of a usable fence: the fix must be expressible.
    fixed = ("the clause is now **Gate 6D**, whose watermark, bar, owner and "
             "review_by live in `data/gate-ledger.json`; Gate 4F likewise. "
             "141 panels, 5 mm of glue and 79 frames are not watermarks.")
    assert _documents_restating_a_watermark(fixed) == []


def test_no_document_restates_a_ledger_watermark():
    """Gap J1's rule, generalised from Gate 2M to every ledger row.

    A measurement in a document has no owner, no `review_by` and nothing that
    fails when it goes stale — which is how five Gate 2M figures came to be in
    circulation. The ledger has all three. So the ledger states the number and
    the document points at the ledger.
    """
    for name in _WATERMARK_DOCS:
        offenders = _documents_restating_a_watermark(
            (_ROOT / name).read_text(encoding="utf-8"))
        assert not offenders, (
            f"{name} restates {offenders}. One number, one home: put it in "
            f"data/gate-ledger.json and point at the gate row. The ledger "
            f"carries the units, the bar, the owner and the review_by; a "
            f"sentence carries none of them and cannot fail.")


def test_a_watermark_this_fence_cannot_search_for_is_named_not_ignored():
    """An unmeasurable metric is FATAL, never a default (LESSONS class 1).

    `_searchable_watermarks` drops any watermark with fewer than three digits,
    because a bare `0` matches everything. Dropping it SILENTLY would be the
    `${_MQ_SKEW:-0}` defect: failure to measure scored as a pass. So every
    dropped row must be named with a reason, and every named row must still be
    a real, still-unsearchable ledger entry — an exemption that outlives its
    cause is a hole nobody can see.
    """
    ledger = {k: v for k, v in json.loads(_LEDGER_PATH.read_text()).items()
              if not k.startswith("_")}
    searchable = _searchable_watermarks()

    dropped = {g for g, e in ledger.items()
               if isinstance(e.get("watermark"), (int, float))
               and not isinstance(e.get("watermark"), bool)
               and g not in searchable}
    assert dropped == set(_UNSEARCHABLE_WATERMARKS), (
        f"numeric watermarks this fence cannot search for: {sorted(dropped)}; "
        f"named as such: {sorted(_UNSEARCHABLE_WATERMARKS)}. Name the new one "
        f"with its reason, or the rule silently stops covering it.")
    for gate, why in _UNSEARCHABLE_WATERMARKS.items():
        assert gate in ledger, f"{gate} left the ledger; drop this exemption"
        assert len(why) > 60, f"{gate}: an exemption with no reason is a shrug"

    # And the rule is actually covering something: this is not a table of
    # exemptions with an empty fence behind it.
    assert len(searchable) >= 3, sorted(searchable)
