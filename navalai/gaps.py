"""The gap queue: a finding becomes a work item, not a paragraph.

`docs/GAP-REGISTER.md` is a dated audit record — 2026-08-05, seven independent
audits, every row either measured or marked `[unverified]`. It is excellent and
it is PROSE, which means nothing can be assigned, nothing has a state, and
nothing notices when a row goes stale. That is the same defect the register
itself names in section J: a machine-readable fact copied into a document,
where it cannot be re-derived.

This module is the live mechanism. The register file is NOT deleted and NOT
edited — `import_gap_register()` reads it once and seeds the queue, so its rows
become work items while the document stays what it is, the audit that found
them.

A gap enters one of two ways:

  1. A component hits `unsupported` / `unknown` / `missing` / `failed
     validation` and emits a `GapEvent`. The event carries WHO emitted it, the
     EVIDENCE, WHAT it blocks and how bad it is — an event with none of those
     is a rumour, and `GapEvent` refuses to be constructed without them.
  2. The one-shot import above.

Persistence is `navalai.pipeline.JsonlLog`, the same append-only log the
evolution archive uses. One implementation, one immutability rule: a state
change appends a new record and nothing ever edits or removes a prior one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .pipeline import JsonlLog

_ROOT = Path(__file__).resolve().parents[1]

GAPS_PATH = _ROOT / "data" / "evolution" / "gaps.jsonl"
REGISTER_PATH = _ROOT / "docs" / "GAP-REGISTER.md"


class Severity(str, Enum):
    """The register's own four levels, verbatim from its Severity section."""
    CRITICAL = "CRITICAL"     # the system reports something untrue about itself
    HIGH = "HIGH"             # a plan clause is unmet and its gate reports GREEN
    MED = "MED"               # real defect, bounded blast radius
    LOW = "LOW"               # hygiene, staleness, fragility


_SEVERITY_RANK = {Severity.CRITICAL: 0, Severity.HIGH: 1,
                  Severity.MED: 2, Severity.LOW: 3}


class GapState(str, Enum):
    OPEN = "Open"
    INVESTIGATING = "Investigating"
    PROTOTYPE = "Prototype"
    VERIFIED = "Verified"
    CLOSED = "Closed"


# Forward only, one step at a time. Deliberately no reopen edge: a gap that
# comes back is a NEW finding with new evidence, and filing it as one keeps the
# thing that recurred visible instead of hiding it inside one row's history.
# The register's own A6/A6b pair is the pattern — the correction is a separate
# row that names what it corrects, not an edit to A6.
GAP_STATE_ORDER: tuple[GapState, ...] = tuple(GapState)
_GAP_INDEX = {s: i for i, s in enumerate(GAP_STATE_ORDER)}

# What a component was doing when it found nothing to do it with.
EVENT_KINDS: tuple[str, ...] = ("unsupported", "unknown", "missing",
                                "failed_validation")


class IllegalGapTransition(RuntimeError):
    """The gap lifecycle does not contain this edge."""


@dataclass(frozen=True)
class GapEvent:
    """Emitted by a component that cannot do what it was asked.

    Every field is required and every field is checked. A finding with no
    evidence cannot be reproduced, and a finding that does not say what it
    blocks cannot be prioritised — this repository already has 434 lines of
    register proving both are worth insisting on.
    """

    component: str          # who emitted it, e.g. "navalai.pipeline.check_mesh"
    evidence: str           # what was measured, in words or a path
    blocking: str           # what cannot proceed because of it
    severity: Severity
    kind: str = "failed_validation"
    title: str = ""
    owner: str = "unassigned"
    detail: str = ""

    def __post_init__(self) -> None:
        for name in ("component", "evidence", "blocking"):
            if not str(getattr(self, name)).strip():
                raise ValueError(
                    f"GapEvent.{name} is empty. A finding without it is a "
                    f"rumour: it cannot be reproduced, assigned or closed.")
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"kind {self.kind!r} is not one of {list(EVENT_KINDS)}")
        object.__setattr__(self, "severity", Severity(self.severity))
        if not self.title.strip():
            object.__setattr__(self, "title", f"{self.kind}: {self.blocking}")


@dataclass
class Gap:
    id: str                       # G-NNN
    title: str
    severity: Severity            # the priority
    owner: str
    evidence: str
    component: str
    blocking: str
    kind: str
    state: GapState = GapState.OPEN
    detail: str = ""
    source_id: str | None = None  # the register row this came from, e.g. "B9"
    history: list[tuple[str, float, str]] = field(default_factory=list)

    @property
    def priority(self) -> int:
        """0 = CRITICAL. Sorts a queue without anyone typing an order twice."""
        return _SEVERITY_RANK[self.severity]

    @property
    def is_closed(self) -> bool:
        return self.state is GapState.CLOSED


def legal_gap_targets(state: GapState) -> frozenset[GapState]:
    i = _GAP_INDEX[state]
    return frozenset() if i + 1 >= len(GAP_STATE_ORDER) else frozenset(
        {GAP_STATE_ORDER[i + 1]})


class GapQueue:
    """Append-only queue of gaps, replayed from `data/evolution/gaps.jsonl`."""

    def __init__(self, log: JsonlLog | str | Path | None = None) -> None:
        if log is None:
            log = GAPS_PATH
        self.log = log if isinstance(log, JsonlLog) else JsonlLog(log)
        self._gaps: dict[str, Gap] = {}
        self._by_source: dict[str, str] = {}
        for rec in self.log.read():
            self._apply(rec)

    # -- writing ----------------------------------------------------------

    def next_id(self) -> str:
        n = 0
        for gid in self._gaps:
            m = re.fullmatch(r"G-(\d+)", gid)
            if m:
                n = max(n, int(m.group(1)))
        return f"G-{n + 1:03d}"

    def emit(self, event: GapEvent, source_id: str | None = None) -> Gap:
        """File a gap for `event`. Returns the existing one if already filed.

        Idempotent on `source_id` so the register import is a one-shot that can
        be re-run: seeding 110 findings twice would double the queue and make
        the count meaningless, which is the sort of thing that turns a work
        list back into prose.
        """
        if source_id and source_id in self._by_source:
            return self._gaps[self._by_source[source_id]]
        gid = self.next_id()
        rec = {"kind": "open", "gap_id": gid, "title": event.title,
               "severity": event.severity.value, "owner": event.owner,
               "evidence": event.evidence, "component": event.component,
               "blocking": event.blocking, "event_kind": event.kind,
               "detail": event.detail, "source_id": source_id,
               "state": GapState.OPEN.value}
        self._apply(self.log.append(rec))
        return self._gaps[gid]

    def advance(self, gap_id: str, to: GapState, note: str = "") -> Gap:
        gap = self.get(gap_id)
        if to not in legal_gap_targets(gap.state):
            raise IllegalGapTransition(
                f"{gap_id}: {gap.state.value} -> {to.value} is not legal. "
                f"Legal: {sorted(s.value for s in legal_gap_targets(gap.state)) or ['(none: closed)']}. "
                f"A gap moves forward one step at a time; there is no reopen "
                f"edge, a recurrence is a new gap with new evidence.")
        if to is GapState.VERIFIED and not note.strip():
            raise IllegalGapTransition(
                f"{gap_id}: Verified requires a note saying what was measured. "
                f"'Verified' with no measurement is the claim this whole queue "
                f"exists to stop being made.")
        self._apply(self.log.append({"kind": "state", "gap_id": gap_id,
                                     "state": to.value, "note": note}))
        return self._gaps[gap_id]

    def assign(self, gap_id: str, owner: str) -> Gap:
        if not owner.strip():
            raise ValueError("owner is empty; 'unassigned' is the honest value")
        self.get(gap_id)
        self._apply(self.log.append({"kind": "assign", "gap_id": gap_id,
                                     "owner": owner}))
        return self._gaps[gap_id]

    # -- replay -----------------------------------------------------------

    def _apply(self, rec: Mapping[str, Any]) -> None:
        gid = rec["gap_id"]
        kind = rec["kind"]
        if kind == "open":
            gap = Gap(id=gid, title=rec["title"],
                      severity=Severity(rec["severity"]), owner=rec["owner"],
                      evidence=rec["evidence"], component=rec["component"],
                      blocking=rec["blocking"], kind=rec["event_kind"],
                      state=GapState.OPEN, detail=rec.get("detail", ""),
                      source_id=rec.get("source_id"),
                      history=[(GapState.OPEN.value, rec.get("utc", 0.0), "")])
            self._gaps[gid] = gap
            if gap.source_id:
                self._by_source[gap.source_id] = gid
        elif kind == "state":
            gap = self._gaps[gid]
            gap.state = GapState(rec["state"])
            gap.history.append((rec["state"], rec.get("utc", 0.0),
                                rec.get("note", "")))
        elif kind == "assign":
            self._gaps[gid].owner = rec["owner"]
        else:
            raise ValueError(f"unknown gap record kind {kind!r} in {self.log.path}")

    # -- reading ----------------------------------------------------------

    def get(self, gap_id: str) -> Gap:
        try:
            return self._gaps[gap_id]
        except KeyError:
            raise KeyError(f"no gap {gap_id!r} in {self.log.path}") from None

    def all(self) -> list[Gap]:
        return list(self._gaps.values())

    def by_state(self, state: GapState) -> list[Gap]:
        return [g for g in self._gaps.values() if g.state is state]

    def by_source(self, source_id: str) -> Gap | None:
        gid = self._by_source.get(source_id)
        return self._gaps[gid] if gid else None

    def open_queue(self) -> list[Gap]:
        """Everything not yet Closed, worst first, then by id."""
        return sorted((g for g in self._gaps.values() if not g.is_closed),
                      key=lambda g: (g.priority, g.id))


# ---------------------------------------------------------------------------
# One-shot import of docs/GAP-REGISTER.md
# ---------------------------------------------------------------------------

@dataclass
class ImportReport:
    imported: list[Gap] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)   # (row id, why)

    @property
    def n_rows_seen(self) -> int:
        return len(self.imported) + len(self.already_present) + len(self.skipped)


_MD_STRIP = re.compile(r"\*\*|__|`|\*(?=\S)|(?<=\S)\*")
_SEV_IN_CELL = re.compile(r"\b(CRITICAL|HIGH|MED|LOW)\b")
_ROW_ID = re.compile(r"^[A-Z]\d+[a-z]?(\s*\(.*\))?$")


def _clean(cell: str) -> str:
    return _MD_STRIP.sub("", cell).strip()


def _split_row(line: str) -> list[str]:
    """Split a markdown row on UNESCAPED pipes.

    A naive `.split("|")` shifts every column right of a `\\|`, and three rows
    carry one inside their prose (`setFields … \\|\\| true`, `GM 0.15\\|v\\|+0.05`,
    `rho tracks \\|delta\\|`). MEASURED before the fix: F10, H1 and I2 imported
    with a fragment of their own Finding text where the severity should be, so
    the importer reported "names no level" and skipped three real findings —
    two HIGH and one CRITICAL. A parser that drops rows it mis-split reports a
    smaller register than the one on disk.
    """
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.replace("\\|", "|").strip() for c in cells]


def import_gap_register(md_path: str | Path | None = None,
                        queue: GapQueue | None = None) -> ImportReport:
    """Seed the queue from the register's finding tables.

    Only tables with a `Sev` column are findings. Section J's
    `| ID | Closed by | Mechanism |` table is a CLOSURE record, not a list of
    open work, and importing it would file eight already-fixed defects as open
    gaps.

    A row whose severity cell names no level is SKIPPED AND NAMED, never
    guessed at. Row B10 is `*(decision input)*`, not a finding, and inventing a
    severity for it would be the same move as scoring an unmeasured metric as
    perfect. `ImportReport.skipped` carries every one with the reason.

    OWNER IS NOT INFERRED. PLM.md §4 lists six roles and the register's section
    headings are topics, not roles; mapping one onto the other would be a
    guess wearing a name. Everything imports as `unassigned` and a human
    assigns it.
    """
    path = Path(md_path) if md_path else REGISTER_PATH
    q = queue if queue is not None else GapQueue()
    report = ImportReport()
    header: list[str] | None = None
    section = ""

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = _clean(line[3:])
            header = None
            continue
        if not line.startswith("|"):
            header = None
            continue
        cells = _split_row(line)
        if set("".join(cells)) <= set("-: "):        # the |---|---| separator
            continue
        if cells and cells[0].strip() == "ID":
            header = [_clean(c) for c in cells]
            continue
        if not header or "Sev" not in header:
            continue
        row_id = _clean(cells[0])
        if not _ROW_ID.match(row_id):
            continue
        row_id = row_id.split("(")[0].strip()
        by_name = dict(zip(header, cells))
        sev_cell = by_name.get("Sev", "")
        m = _SEV_IN_CELL.search(_clean(sev_cell))
        if not m:
            report.skipped.append(
                (row_id, f"severity cell {_clean(sev_cell)!r} names no level — "
                         f"not a finding, or a level this importer will not guess"))
            continue
        if q.by_source(row_id) is not None:
            report.already_present.append(row_id)
            continue
        finding = _clean(by_name.get("Finding", ""))
        clause = _clean(by_name.get("Plan clause", ""))
        evidence = _clean(by_name.get("Evidence", "")) or "see docs/GAP-REGISTER.md"
        title = finding.split(". ")[0][:180] or f"register row {row_id}"
        gap = q.emit(GapEvent(
            component=f"docs/GAP-REGISTER.md#{row_id}",
            evidence=evidence,
            blocking=clause or section or "unstated in the register",
            severity=Severity(m.group(1)),
            kind="failed_validation",
            title=f"{row_id}: {title}",
            owner="unassigned",
            detail=finding,
        ), source_id=row_id)
        report.imported.append(gap)
    return report


def from_stage_check(check, genome_id: str = "",
                     severity: Severity = Severity.MED) -> GapEvent:
    """Turn a FAILED `pipeline.StageCheck` into a gap event.

    This is the wiring between the two halves of the spine: a genome that dies
    at a stage leaves a terminal record in the archive AND a work item in the
    queue, so a failure is a thing someone owns rather than a line in a log.
    Refuses a passing check — filing a gap for something that worked is how a
    queue stops meaning anything.
    """
    if check.ok:
        raise ValueError(
            f"{check.name} passed; there is no gap to file. A queue that "
            f"accepts successes is a queue nobody reads.")
    return GapEvent(
        component=f"navalai.pipeline.check_{check.name}",
        evidence="; ".join(check.reasons),
        blocking=(f"genome {genome_id} at stage {check.stage.value}"
                  if genome_id else f"stage {check.stage.value}"),
        severity=Severity(severity),
        kind="failed_validation",
        title=f"{check.name} check failed at {check.stage.value}",
        detail=repr(dict(check.evidence)),
    )


def emit(event: GapEvent, queue: GapQueue | None = None) -> Gap:
    """Module-level convenience for a component that has no queue handle."""
    return (queue if queue is not None else GapQueue()).emit(event)


__all__ = [
    "EVENT_KINDS", "GAPS_PATH", "GAP_STATE_ORDER", "Gap", "GapEvent",
    "GapQueue", "GapState", "IllegalGapTransition", "ImportReport",
    "REGISTER_PATH", "Severity", "emit", "from_stage_check",
    "import_gap_register", "legal_gap_targets",
]
