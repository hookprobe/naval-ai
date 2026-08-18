"""EXPERIMENT (forensics section-26, C-25): the lifecycle FSM is unwired —
no production caller constructs it; the live lane is
mission -> evaluate -> certify -> manifest -> case (LIVE_SYSTEM_MAP.md).
The MDO spine: one genome, one lifecycle, exactly one terminal state.The MDO spine: one genome, one lifecycle, exactly one terminal state.

"The AI coordinates. Physics decides." Nothing in this module computes a
hydrostatic, a resistance or a mesh. It records WHERE a genome is, refuses a
transition the lifecycle does not allow, and delegates every verdict to the
deterministic component that owns it:

    geometry      `navalai.grammar.check`              (L0 algebraic gate)
    STL           `navalai.cfd.case.stl_watertight_report`
    hydrostatics  `navalai.evaluate.evaluate` -> `Evaluation.g`
    mesh          the bars in `navalai/cfd/run-case.sh`, READ from that file
    cfd           `SETTLE_TOL` in `scripts/gate2m.py`, READ from that file

The four numbers this module needs and does not own (0 zero-volume cells,
5 incorrectly-oriented faces, 20 max skewness, 5% settling drift) are EXTRACTED
from the shipped guards at call time rather than restated here. CLAUDE.md rule
3: a number lives in exactly one place. This repository has already shipped a
15 mm ply that failed its own scantling rule and `forceCoeffs` wrong by exactly
2x, both from a constant declared twice; a fourth copy of the mesh bar would be
the same defect with a new label. `tests/test_pipeline.py` asserts that this
file contains no literal copy of them.

WHY A SPINE AT ALL. The gap register's section A is one finding repeated: the
ladder is not a ladder. `evaluate`, `optimize` and `agents` reach `seakeeping:
no, cfd: no, surrogate: no, rules: no`, and `Evaluation.tier` read "L1" in 100%
of ~2000 evaluations. There was no object that could say "this genome went to
MESHING and never came back". This is that object, and its central invariant is
that there is no such genome: every one ends in exactly one terminal state.
"""

from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from . import db, grammar

_ROOT = Path(__file__).resolve().parents[1]

# Gitignored: this is a machine's own history, not a shared artefact. See the
# `data/evolution/` entry in .gitignore and gap J6 (build artefacts that became
# tracked dirtied the tree on every run and conflicted on every cherry-pick).
ARCHIVE_PATH = _ROOT / "data" / "evolution" / "archive.jsonl"


# ---------------------------------------------------------------------------
# The genome
# ---------------------------------------------------------------------------

class GenomeError(ValueError):
    """The parameter vector is not one this grammar can name."""


@dataclass(frozen=True)
class Genome:
    """A hull, named by its own contents.

    THE PARAMETER SET IS `navalai.grammar.PARAMS` AND IS NOT RESTATED HERE.
    That tuple is the single source: `optimize.HullProblem` takes its search box
    from `grammar.LOW/HIGH` and `n_var` from `grammar.N_PARAMS`, and
    `geometry.Hull` reads the same vector positionally. A spine that carried its
    own field list would be a sixteenth place for the design vector to drift,
    which is the defect class CLAUDE.md names first.

    The id is CONTENT-DERIVED, via `db.hull_id` — the same function that keys
    the provenance database — so the same parameters name the same genome here,
    in `data/navalai.sqlite3`, and in anything that joins the two. A second
    hashing scheme would mean the spine and the provenance record disagreed
    about which hull they were describing.
    """

    params: tuple[float, ...]
    label: str = ""

    def __post_init__(self) -> None:
        p = tuple(float(v) for v in self.params)
        if len(p) != grammar.N_PARAMS:
            raise GenomeError(
                f"genome has {len(p)} parameters, the grammar has "
                f"{grammar.N_PARAMS} ({', '.join(grammar.NAMES)})")
        if not all(math.isfinite(v) for v in p):
            raise GenomeError(
                f"genome carries a non-finite parameter: {p!r}. A hull that "
                f"cannot be written down cannot be validated, and nan is never "
                f"a value (see evaluate.is_real_finite).")
        object.__setattr__(self, "params", p)

    @classmethod
    def from_vector(cls, x: Sequence[float] | np.ndarray, label: str = "") -> Genome:
        return cls(tuple(float(v) for v in np.asarray(x, dtype=float).ravel()), label)

    @classmethod
    def from_named(cls, d: Mapping[str, float], label: str = "") -> Genome:
        return cls.from_vector(grammar.vector(dict(d)), label)

    @property
    def id(self) -> str:
        return db.hull_id(np.asarray(self.params, dtype=float))

    def vector(self) -> np.ndarray:
        return np.asarray(self.params, dtype=float)

    def named(self) -> dict[str, float]:
        return grammar.named(self.vector())


# ---------------------------------------------------------------------------
# The lifecycle
# ---------------------------------------------------------------------------

class Stage(str, Enum):
    NEW = "NEW"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    HYDROSTATICS = "HYDROSTATICS"
    MESHING = "MESHING"
    CFD = "CFD"
    SEA_STATE = "SEA_STATE"
    ERGONOMICS = "ERGONOMICS"
    MANUFACTURING = "MANUFACTURING"
    SCORING = "SCORING"
    ARCHIVED = "ARCHIVED"


class Terminal(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_GEOMETRY = "FAILED_GEOMETRY"
    FAILED_HYDROSTATICS = "FAILED_HYDROSTATICS"
    FAILED_MESH = "FAILED_MESH"
    FAILED_CFD = "FAILED_CFD"
    FAILED_TIMEOUT = "FAILED_TIMEOUT"
    FAILED_RESOURCE = "FAILED_RESOURCE"


# Forward order. A stage may only move to its immediate successor: skipping
# HYDROSTATICS to reach MESHING is how a hull with no floated state gets a mesh
# built for it, which is gap B9 with a bigger compute bill attached.
STAGE_ORDER: tuple[Stage, ...] = tuple(Stage)
_STAGE_INDEX = {s: i for i, s in enumerate(STAGE_ORDER)}

FAILURES: tuple[Terminal, ...] = tuple(t for t in Terminal if t is not Terminal.SUCCESS)


class IllegalTransition(RuntimeError):
    """The lifecycle graph does not contain this edge.

    A real exception rather than a returned False: a caller that ignores a
    False keeps going, and the whole point of the graph is that a genome cannot
    be walked into a state its evidence does not support.
    """


def legal_targets(state: Stage | Terminal) -> frozenset[Stage | Terminal]:
    """Everything reachable from `state` in one step.

    A terminal state has NO successors. That is what makes "exactly one
    terminal state per genome" checkable: reaching one closes the genome, and a
    second terminal would have to come through `transition`, which refuses.
    """
    if isinstance(state, Terminal):
        return frozenset()
    out: set[Stage | Terminal] = set(FAILURES)
    i = _STAGE_INDEX[state]
    if i + 1 < len(STAGE_ORDER):
        out.add(STAGE_ORDER[i + 1])
    else:
        # SUCCESS is only reachable from ARCHIVED — the END of the stage list.
        # Allowing it from anywhere would let a genome be declared a success
        # from NEW, which is the reporting-something-untrue-about-itself
        # failure the register calls CRITICAL.
        out.add(Terminal.SUCCESS)
    return frozenset(out)


def transition(frm: Stage | Terminal, to: Stage | Terminal,
               reason: str = "") -> None:
    """Validate one edge. Raises `IllegalTransition`; returns None on success."""
    if to not in legal_targets(frm):
        raise IllegalTransition(
            f"{frm.value} -> {to.value} is not a legal transition. "
            f"Legal from {frm.value}: "
            f"{sorted(s.value for s in legal_targets(frm)) or ['(none: terminal)']}")
    if isinstance(to, Terminal) and to is not Terminal.SUCCESS and not reason.strip():
        raise IllegalTransition(
            f"{to.value} requires a reason. A failure with no reason is a "
            f"genome abandoned with paperwork — the register's section A "
            f"finding, restated as a data structure.")


# ---------------------------------------------------------------------------
# The append-only log
# ---------------------------------------------------------------------------

class LogTruncated(RuntimeError):
    """The file shrank. Something rewrote history."""


def _plain(v: Any) -> Any:
    """JSON-safe, and LOUD about what it cannot represent.

    Non-finite floats become the STRINGS "nan"/"inf"/"-inf". Two reasons, both
    measured here: a bare `NaN` is not valid JSON (RFC 8259) and was emitted
    over HTTP by this project until gap E10, and a reader that gets a string
    back fails on the arithmetic instead of propagating a nan through a
    comparison that silently answers False.
    """
    if v is None or isinstance(v, (str, bool, int)):
        return v
    if isinstance(v, float):
        if math.isfinite(v):
            return v
        if math.isnan(v):
            return "nan"
        return "inf" if v > 0 else "-inf"
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, np.generic):
        return _plain(v.item())
    if isinstance(v, np.ndarray):
        return [_plain(x) for x in v.tolist()]
    if isinstance(v, Mapping):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_plain(x) for x in v]
    if isinstance(v, Path):
        return str(v)
    raise TypeError(
        f"{type(v).__name__} cannot go into the archive. Record what you "
        f"measured, not the object you measured it with.")


class JsonlLog:
    """Append-only JSONL. Nothing here opens the file except to append.

    There is no update method and no delete method, deliberately. A state
    change appends a NEW record; the current state is whatever replaying them
    in order produces. `db.py`'s docstring states the same rule for the
    provenance database ("rows are append-only; re-runs append, never
    overwrite") and this is that rule for the spine.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._committed = self.path.stat().st_size if self.path.exists() else 0

    def append(self, record: Mapping[str, Any]) -> dict:
        rec = dict(_plain(record))
        rec.setdefault("utc", time.time())
        line = json.dumps(rec, sort_keys=True, allow_nan=False) + "\n"
        size = self.path.stat().st_size if self.path.exists() else 0
        if size < self._committed:
            raise LogTruncated(
                f"{self.path} was {self._committed} bytes and is now {size}. "
                f"This log is append-only; a shorter file means a prior record "
                f"was edited or removed, and the replayed state is no longer "
                f"the state that was recorded.")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
        self._committed = size + len(line.encode("utf-8"))
        return rec

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for i, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LogTruncated(
                    f"{self.path}:{i} is not valid JSON ({exc}). A corrupt "
                    f"record is not skipped — replaying the rest would report "
                    f"a state that never existed.") from exc
        return out


# ---------------------------------------------------------------------------
# Replayed state
# ---------------------------------------------------------------------------

@dataclass
class GenomeState:
    genome_id: str
    params: tuple[float, ...]
    stage: Stage
    label: str = ""
    terminal: Terminal | None = None
    terminal_reason: str = ""
    failed_at: Stage | None = None
    history: list[tuple[str, float]] = field(default_factory=list)
    receipts: set[str] = field(default_factory=set)
    artifacts: list[dict] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        return self.terminal is not None

    @property
    def state(self) -> Stage | Terminal:
        return self.terminal if self.terminal is not None else self.stage


# The five conditions, as ONE dispatch table. `cycle_complete()` is `all()` over
# this dict, so the predicate and the list of things it checks cannot drift
# apart — which is the whole reason the list is not written out twice.
_CYCLE_CHECKS: dict[str, Callable[[GenomeState], bool]] = {
    "archive": lambda st: st.terminal is not None,
    "knowledge": lambda st: "knowledge" in st.receipts,
    "mutation_stats": lambda st: "mutation_stats" in st.receipts,
    "gap_queue": lambda st: "gap_queue" in st.receipts,
    "artifacts": lambda st: bool(st.artifacts),
}
CYCLE_REQUIREMENTS: tuple[str, ...] = tuple(_CYCLE_CHECKS)

# The receipts a caller may file by hand. "archive" and "artifacts" are NOT
# among them: they are satisfied by the terminal record and by an actual
# artifact record respectively, so neither can be asserted without the thing
# it asserts existing. A receipt you can file for work you did not do is a
# green light, not a check.
RECEIPT_NAMES: tuple[str, ...] = ("knowledge", "mutation_stats", "gap_queue")


class Pipeline:
    """Drives genomes through the lifecycle and records every step.

    State is held in memory AND reconstructible by replay: `__init__` builds it
    by replaying the file through the same `_apply` every append goes through,
    so there is one interpretation of a record, not two.
    """

    def __init__(self, log: JsonlLog | str | Path | None = None) -> None:
        if log is None:
            log = ARCHIVE_PATH
        self.log = log if isinstance(log, JsonlLog) else JsonlLog(log)
        self._states: dict[str, GenomeState] = {}
        for rec in self.log.read():
            self._apply(rec)

    # -- writing ----------------------------------------------------------

    def _emit(self, record: Mapping[str, Any]) -> dict:
        rec = self.log.append(record)
        self._apply(rec)
        return rec

    def start(self, genome: Genome, evidence: Mapping[str, Any] | None = None) -> GenomeState:
        if genome.id in self._states:
            raise IllegalTransition(
                f"genome {genome.id} is already in the archive at "
                f"{self._states[genome.id].state.value}. A genome is content-"
                f"addressed, so starting it twice is either a duplicate of work "
                f"already recorded or a collision worth knowing about.")
        self._emit({"kind": "stage", "genome_id": genome.id,
                    "params": list(genome.params), "label": genome.label,
                    "state": Stage.NEW.value, "evidence": dict(evidence or {})})
        return self._states[genome.id]

    def advance(self, genome_id: str, to: Stage,
                evidence: Mapping[str, Any] | None = None) -> GenomeState:
        st = self.state(genome_id)
        transition(st.state, to)
        self._emit({"kind": "stage", "genome_id": genome_id, "state": to.value,
                    "evidence": dict(evidence or {})})
        return self._states[genome_id]

    def fail(self, genome_id: str, terminal: Terminal, reason: str,
             evidence: Mapping[str, Any] | None = None) -> GenomeState:
        st = self.state(genome_id)
        transition(st.state, terminal, reason)
        self._emit({"kind": "terminal", "genome_id": genome_id,
                    "state": terminal.value, "reason": reason,
                    "at_stage": st.stage.value, "evidence": dict(evidence or {})})
        return self._states[genome_id]

    def succeed(self, genome_id: str,
                evidence: Mapping[str, Any] | None = None) -> GenomeState:
        st = self.state(genome_id)
        transition(st.state, Terminal.SUCCESS)
        self._emit({"kind": "terminal", "genome_id": genome_id,
                    "state": Terminal.SUCCESS.value, "reason": "",
                    "at_stage": st.stage.value, "evidence": dict(evidence or {})})
        return self._states[genome_id]

    def apply_check(self, genome_id: str, check: StageCheck) -> GenomeState:
        """Fail the genome if `check` failed; otherwise record the evidence.

        The single place a physics verdict becomes a lifecycle event. The check
        chooses the terminal — the coordinator does not get to decide that a
        mesh failure was really a timeout.
        """
        if check.ok:
            self._emit({"kind": "evidence", "genome_id": genome_id,
                        "state": self.state(genome_id).stage.value,
                        "check": check.name, "evidence": dict(check.evidence)})
            return self._states[genome_id]
        return self.fail(genome_id, check.terminal, check.reason,
                         evidence=dict(check.evidence))

    def receipt(self, genome_id: str, name: str,
                detail: Mapping[str, Any] | None = None) -> GenomeState:
        if name not in RECEIPT_NAMES:
            raise ValueError(
                f"{name!r} is not a receipt a caller files by hand; "
                f"choose from {list(RECEIPT_NAMES)}. 'archive' and 'artifacts' "
                f"are satisfied by the records themselves.")
        self.state(genome_id)          # raises if unknown
        self._emit({"kind": "receipt", "genome_id": genome_id, "receipt": name,
                    "evidence": dict(detail or {})})
        return self._states[genome_id]

    def artifact(self, genome_id: str, kind: str, path: str | Path,
                 sha256: str = "", detail: Mapping[str, Any] | None = None) -> GenomeState:
        self.state(genome_id)
        self._emit({"kind": "artifact", "genome_id": genome_id,
                    "artifact": {"kind": kind, "path": str(path),
                                 "sha256": sha256, **dict(detail or {})}})
        return self._states[genome_id]

    # -- replay -----------------------------------------------------------

    def _apply(self, rec: Mapping[str, Any]) -> None:
        gid = rec["genome_id"]
        kind = rec["kind"]
        if gid not in self._states:
            if kind != "stage" or rec.get("state") != Stage.NEW.value:
                raise LogTruncated(
                    f"record for unknown genome {gid} ({kind}/{rec.get('state')}). "
                    f"The first record for a genome must be its NEW stage; "
                    f"replaying from the middle of a life would invent one.")
            self._states[gid] = GenomeState(
                genome_id=gid, params=tuple(rec.get("params", ())),
                stage=Stage.NEW, label=rec.get("label", ""),
                history=[(Stage.NEW.value, rec.get("utc", 0.0))])
            return
        st = self._states[gid]
        if kind == "stage":
            st.stage = Stage(rec["state"])
            st.history.append((rec["state"], rec.get("utc", 0.0)))
        elif kind == "terminal":
            st.terminal = Terminal(rec["state"])
            st.terminal_reason = rec.get("reason", "")
            st.failed_at = Stage(rec["at_stage"]) if rec.get("at_stage") else None
            st.history.append((rec["state"], rec.get("utc", 0.0)))
        elif kind == "receipt":
            st.receipts.add(rec["receipt"])
        elif kind == "artifact":
            st.artifacts.append(dict(rec["artifact"]))
        elif kind == "evidence":
            pass
        else:
            raise LogTruncated(f"unknown record kind {kind!r} in {self.log.path}")

    # -- reading ----------------------------------------------------------

    def state(self, genome_id: str) -> GenomeState:
        try:
            return self._states[genome_id]
        except KeyError:
            raise KeyError(f"no genome {genome_id!r} in {self.log.path}") from None

    def states(self) -> dict[str, GenomeState]:
        return dict(self._states)

    def abandoned(self) -> list[str]:
        """Genome ids with no terminal state.

        THE CENTRAL INVARIANT, as a query. Non-empty at the end of a cycle
        means a genome was walked into a stage and left there, which is exactly
        what nobody could see before this module existed.
        """
        return sorted(g for g, st in self._states.items() if not st.is_terminal)

    def cycle_status(self, genome_id: str) -> dict[str, bool]:
        st = self.state(genome_id)
        return {name: fn(st) for name, fn in _CYCLE_CHECKS.items()}

    def cycle_complete(self, genome_id: str) -> bool:
        """True ONLY when all five conditions hold. Anything else is INCOMPLETE."""
        return all(self.cycle_status(genome_id).values())

    def cycle_missing(self, genome_id: str) -> list[str]:
        return [k for k, v in self.cycle_status(genome_id).items() if not v]


# ---------------------------------------------------------------------------
# Bars this module does not own
# ---------------------------------------------------------------------------

class Unmeasurable(RuntimeError):
    """A guard has no evidence, so it refuses.

    MEASURED 2026-08-06, and the reason this exception exists rather than a
    default: `run-case.sh` read max skewness as `${_MQ_SKEW:-0}`, and the awk
    never matched the line checkMesh actually prints
    (`***Max skewness = 42.9417, 23 highly skew faces detected`). "I could not
    measure this" became "this is perfect", 0 passes every bar, and a mesh with
    skewness 42.94 went to a 10-rank solve that spun 18 minutes at
    deltaT 2.5e-26 producing 61 timesteps all at the same instant.
    """


def _number_from_source(path: Path, pattern: str, what: str) -> float:
    src = path.read_text(encoding="utf-8")
    m = re.search(pattern, src, re.MULTILINE)
    if not m:
        raise Unmeasurable(
            f"could not read the {what} bar out of {path}. The bar lives in "
            f"that file and nowhere else; a copy here would be a second source "
            f"of it, and a guess would be worse than a copy.")
    return float(m.group(1))


@dataclass(frozen=True)
class MeshBars:
    """The checkMesh bars, as `run-case.sh` enforces them. Read, never declared."""
    zero_volume_cells: float
    wrong_oriented_faces: float
    max_skewness: float
    source: str


@lru_cache(maxsize=1)
def mesh_quality_bars(script: str | Path | None = None) -> MeshBars:
    """Extract the three checkMesh bars from the shipped guard.

    Calibration (all in `run-case.sh`'s own comments): 5 incorrectly-oriented
    faces is the largest count MEASURED to solve and 10 is measured to die;
    max skewness 20 is checkMesh's own boundary-face limit, against 6.32-9.64
    on meshes that solved and 42.94 on the one that died at t=0.0072 s.
    """
    p = Path(script) if script else _ROOT / "navalai" / "cfd" / "run-case.sh"
    return MeshBars(
        zero_volume_cells=_number_from_source(
            p, r'"\$_MQ_ZEROVOL"\s+-gt\s+([0-9]+)', "zero-volume cell"),
        wrong_oriented_faces=_number_from_source(
            p, r'"\$_MQ_WRONGOR"\s+-gt\s+([0-9]+)', "incorrectly-oriented face"),
        max_skewness=_number_from_source(
            p, r"s\+0 > ([0-9.]+)\) \? 1 : 0", "max skewness"),
        source=str(p))


@lru_cache(maxsize=1)
def settle_tolerance(script: str | Path | None = None) -> float:
    """Drift over the last fifth above which a force history is NOT settled.

    `scripts/gate2m.py` is the gate that prints the verdict, so its SETTLE_TOL
    is the number. CLAUDE.md: post_gci's drift column > 5% means not settled and
    the result is not to be trusted — one place, read from there.
    """
    p = Path(script) if script else _ROOT / "scripts" / "gate2m.py"
    return _number_from_source(p, r"^SETTLE_TOL\s*=\s*([0-9.]+)", "settling drift")


# ---------------------------------------------------------------------------
# Fail-fast stage checks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StageCheck:
    name: str
    ok: bool
    stage: Stage
    terminal: Terminal | None
    reasons: tuple[str, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @property
    def reason(self) -> str:
        return "; ".join(self.reasons)


def _passed(name: str, stage: Stage, evidence: Mapping[str, Any]) -> StageCheck:
    return StageCheck(name, True, stage, None, (), dict(evidence))


def _failed(name: str, stage: Stage, terminal: Terminal,
            reasons: Iterable[str], evidence: Mapping[str, Any]) -> StageCheck:
    rs = tuple(r for r in reasons if r)
    return StageCheck(name, False, stage, terminal,
                      rs or (f"{name} failed with no reason given",), dict(evidence))


def check_geometry(genome: Genome) -> StageCheck:
    """L0 algebraic gate. `grammar.check` decides; this only records."""
    rep = grammar.check(genome.vector())
    ev = {"violations": list(rep.violations), "n_violations": len(rep.violations)}
    if rep.ok:
        return _passed("geometry", Stage.VALIDATING, ev)
    return _failed("geometry", Stage.VALIDATING, Terminal.FAILED_GEOMETRY,
                   rep.violations, ev)


def check_stl(path: str | Path) -> StageCheck:
    """Closed-manifoldness, from `navalai.cfd.case.stl_watertight_report`.

    CLAUDE.md: an open shell floods the interior, and the report keyed only on
    undirected edges until 397 deck triangles pointing INTO the boat still gave
    every edge a count of 2. Both conditions come back from that function; this
    reads them and refuses, it does not re-derive them.
    """
    from .cfd.case import stl_watertight_report      # local: keeps import light
    p = Path(path)
    if not p.exists():
        return _failed("stl", Stage.GENERATING, Terminal.FAILED_GEOMETRY,
                       [f"no STL at {p}"], {"path": str(p)})
    rep = stl_watertight_report(p)
    reasons = []
    if not rep["watertight"]:
        reasons.append(
            f"STL is not a closed manifold: {rep['open_or_nonmanifold_edges']} "
            f"open/non-manifold edges, {rep['winding_conflicts']} winding "
            f"conflicts")
    if not rep["outward"]:
        reasons.append(f"STL windings are not outward (signed volume "
                       f"{rep['signed_volume']:.6g})")
    if reasons:
        return _failed("stl", Stage.GENERATING, Terminal.FAILED_GEOMETRY,
                       reasons, rep)
    return _passed("stl", Stage.GENERATING, rep)


def check_hydrostatics(genome: Genome, mission) -> StageCheck:
    """The ladder's own inequality vector decides.

    `evaluate.CONSTRAINT_NAMES` / `Evaluation.g` is the ONE vector (g <= 0 is
    feasible) and it already carries the GM floor and the freeboard floor from
    `limits.py`. This function does not know what a GM floor is, and that is
    deliberate: a check added to `evaluate()` constrains this stage
    automatically, the same way it constrains NSGA-II.
    """
    from .evaluate import CONSTRAINT_NAMES, evaluate, is_real_finite
    ev = evaluate(genome.vector(), mission)
    g = dict(ev.g)
    if ev.tier == "L0":
        return _failed("hydrostatics", Stage.HYDROSTATICS,
                       Terminal.FAILED_GEOMETRY, ev.violations,
                       {"tier": ev.tier, "violations": list(ev.violations)})
    evidence = {"tier": ev.tier, "g": {k: g.get(k) for k in CONSTRAINT_NAMES},
                "violations": list(ev.violations)}
    reasons: list[str] = []
    for k in CONSTRAINT_NAMES:
        if k not in g:
            # An absent constraint is not a satisfied one. Same class as the
            # skewness default: no evidence must never read as a pass.
            reasons.append(f"constraint {k!r} was not computed at all")
        elif not is_real_finite(g[k]):
            reasons.append(f"constraint {k!r} is {g[k]!r}, not a finite number")
        elif g[k] > 0.0:
            reasons.append(f"constraint {k!r} violated by {g[k]:+.4g}")
    if reasons:
        return _failed("hydrostatics", Stage.HYDROSTATICS,
                       Terminal.FAILED_HYDROSTATICS, reasons, evidence)
    return _passed("hydrostatics", Stage.HYDROSTATICS, evidence)


_MESH_METRICS = ("zero_volume_cells", "wrong_oriented_faces", "max_skewness")


def _as_measured(value: Any) -> float | None:
    """A number, or None for anything that is not one.

    None means UNMEASURED, and unmeasured is fatal. `"UNPARSED"` is
    `run-case.sh`'s own sentinel for a parse that came back empty and is
    treated the same way.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().upper() == "UNPARSED":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def check_mesh(metrics: Mapping[str, Any],
               bars: MeshBars | None = None) -> StageCheck:
    """checkMesh metrics against the bars in `run-case.sh`.

    AN UNMEASURED METRIC IS FATAL, NEVER A PASSING DEFAULT. That is the whole
    lesson of 2026-08-06: `${_MQ_SKEW:-0}` scored an unreadable skewness as 0,
    0 passes every bar, and the mesh that got through had skewness 42.94 and
    killed the solve at deltaT 2.5e-26. Every one of the three metrics must
    arrive as a finite number or this refuses.

    `bars` is injectable ONLY so a test can point it at a doctored copy of the
    script and prove the verdict follows that file rather than a constant in
    here. Production callers pass nothing.
    """
    bars = bars or mesh_quality_bars()
    evidence: dict[str, Any] = {"bars": {"zero_volume_cells": bars.zero_volume_cells,
                                         "wrong_oriented_faces": bars.wrong_oriented_faces,
                                         "max_skewness": bars.max_skewness,
                                         "source": bars.source}}
    reasons: list[str] = []
    for key in _MESH_METRICS:
        got = _as_measured(metrics.get(key))
        evidence[key] = got if got is not None else "UNMEASURED"
        if got is None:
            reasons.append(
                f"{key} could not be measured ({metrics.get(key)!r}). An "
                f"unmeasured metric is refused, never scored as perfect — a "
                f"default of 0 passes every bar, which is how a mesh with "
                f"skewness 42.94 reached a 10-rank solve.")
            continue
        bar = getattr(bars, key)
        if got > bar:
            reasons.append(f"{key} {got:g} exceeds the bar {bar:g} "
                           f"(from {bars.source})")
    if reasons:
        return _failed("mesh", Stage.MESHING, Terminal.FAILED_MESH,
                       reasons, evidence)
    return _passed("mesh", Stage.MESHING, evidence)


def check_cfd(drift: Any, ct: Any = None, flow_throughs: Any = None) -> StageCheck:
    """A force history that has not settled is not a result.

    `drift` is the fractional change over the last fifth, as `gate2m.py`
    computes it, and the tolerance is read out of that file. `flow_throughs`,
    when given, is refused below 1.0: CLAUDE.md states that any number from
    under one flow-through describes startup, not resistance.
    """
    tol = settle_tolerance()
    d = _as_measured(drift)
    evidence: dict[str, Any] = {"settle_tol": tol,
                                "drift": d if d is not None else "UNMEASURED"}
    reasons: list[str] = []
    if d is None:
        reasons.append(
            f"drift could not be measured ({drift!r}); an unsettled run and an "
            f"unmeasurable one are both refusals, not passes")
    elif d > tol:
        reasons.append(f"drift {d:.4g} over the last fifth exceeds {tol:g} — "
                       f"the run has not settled")
    if ct is not None:
        c = _as_measured(ct)
        evidence["ct"] = c if c is not None else "UNMEASURED"
        if c is None or c <= 0.0:
            reasons.append(f"C_T is {ct!r}, which is not a positive resistance "
                           f"coefficient")
    if flow_throughs is not None:
        f = _as_measured(flow_throughs)
        evidence["flow_throughs"] = f if f is not None else "UNMEASURED"
        if f is None:
            reasons.append(f"flow-throughs could not be measured ({flow_throughs!r})")
        elif f < 1.0:
            reasons.append(f"{f:.3g} flow-throughs describes startup, not "
                           f"resistance")
    if reasons:
        return _failed("cfd", Stage.CFD, Terminal.FAILED_CFD, reasons, evidence)
    return _passed("cfd", Stage.CFD, evidence)


__all__ = [
    "ARCHIVE_PATH", "CYCLE_REQUIREMENTS", "FAILURES", "Genome", "GenomeError",
    "GenomeState", "IllegalTransition", "JsonlLog", "LogTruncated", "MeshBars",
    "Pipeline", "RECEIPT_NAMES", "STAGE_ORDER", "Stage", "StageCheck",
    "Terminal", "Unmeasurable", "check_cfd", "check_geometry",
    "check_hydrostatics", "check_mesh", "check_stl", "legal_targets",
    "mesh_quality_bars", "settle_tolerance", "transition",
]
