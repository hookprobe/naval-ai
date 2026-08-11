"""The Design Evidence Graph: why every number in a design is the number it is.

    Requirement -> Decision -> Assumption -> Experiment -> Evidence -> Confidence

`db.Provenance` already records WHAT was computed (genome, tier, solver, value,
sigma). It does not record WHY a design is shaped the way it is: which
requirement forced which decision, which assumption that decision rests on, and
which experiment, if any, ever checked it. That gap is where an optimiser
becomes a black box — the hull is a vector of numbers with a fitness score and
no account of itself.

WHAT THIS BUYS THAT A RESULTS TABLE DOES NOT
============================================
One query, `unsupported()`: every decision with no path to any evidence. That
is the list of things the design believes for no recorded reason. On any real
project it is never empty, and it is the honest agenda.

The second query is `explain()`: the chain behind one node, which is what turns
"L/B was set to 9.5" into a sentence a reviewer can argue with.

Confidence propagates by the weakest link, deliberately. A decision resting on
a 97% experiment and a 60% assumption is a 60% decision — averaging them would
let a pile of cheap confirmations bury one load-bearing guess, which is exactly
the failure this project's honesty rules exist to prevent (rule 1: every
quantity carries its tier and sigma; a graph that averaged them away would
launder a tier-0 assumption into a tier-3 result).

THE TIER VOCABULARY IS CLOSED, AND IT WAS NOT
=============================================
MEASURED 2026-08-11 (adversarial re-audit, `91c0086`; recorded as the one
defect exposed by the "land the evidence graph before RUN" argument,
`docs/BUILD-PLAN.md` §17.1.1): `Node.tier` was a free-form `str` defaulting to
`""`, constrained by nothing. The whole trick this project uses to stop a claim
outranking its evidence is `evaluate.tier_rank`, which ranks a badge it does not
recognise at **-1, below L0**, so it can never be promoted by a `>=` comparison.
A node that spells its tier anything at all — `"CFD"`, `"l3"`, `"sea trial"`, or
nothing — never meets that check, because the check is applied to the ladder's
own spellings.

So a real-boat observation was admissible **under any spelling**, and the
default said the safest thing available: nothing at all. That is defect class 1
in `docs/LESSONS.md` — an unmeasurable value scored as a passing one — applied to
provenance instead of to a mesh metric.

Closed here, BEFORE the first observation row exists, which was the point: once
telemetry lands, the vocabulary is being fixed under a deadline by whoever is
ingesting it. `EvidenceTier` is the enumeration; `ALLOWED_TIERS` says which kind
of node may carry which tier; and `support()` refuses an EXPERIMENT of one
ORIGIN producing EVIDENCE of the other, which is the laundering the graph exists
to prevent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class EvidenceTier(str, Enum):
    """The CLOSED set of things a node may claim about where its number came from.

    NOT A SECOND VOCABULARY. Every member below is a spelling that already
    exists in this codebase, and the one that does not (`M1`) is the value
    `docs/BUILD-PLAN.md` §17.1.1 requires to exist before RUN:

        NA          nothing is claimed. A requirement, a decision and an
                    assumption are not measurements of anything, and saying so
                    is the point — this is the EXPLICIT form of the old `""`
                    default, admissible only where it is the honest answer.
        L0..L3      the ladder, `evaluate.TIER_ORDER`, in that order.
        R           ISO/ES-TRIN rules-as-code (`weights._TIERS`, `db.py`
                    `result.tier`). An ASSESSMENT AID, honesty rule 5.
        E, F        ergonomics, flotation/survivability (`weights._TIERS`,
                    `arrangement.py` emits `tier="E"`).
        S1          surrogate (`flywheel.SURROGATE_TIER`), DELIBERATELY outside
                    `TIER_ORDER` so `tier_rank("S1")` is -1.
        M1          measured on a real vessel in service. The ONE value that
                    means that; see the note below.
        L{n}-INVALID  the badge guard's downgrade (`evaluate.py:638`). Enumerated
                    rather than derived so that `node.tier == EvidenceTier.L3`
                    is FALSE for a downgraded result: an invalid L3 that
                    compares equal to a valid one inside the model would
                    re-open the hole one layer down.

    WHY THIS ENUM IS DECLARED HERE AND NOT IMPORTED FROM `evaluate`. Two
    reasons, and the second is the load-bearing one:
    (1) The ladder is only four of these members; `evaluate.TIER_ORDER` is the
        ladder and must not grow to hold `E`, `F`, `S1` or `M1`, because
        `tier_rank` derives "unknown, therefore -1" from NOT being in it.
    (2) The next planned change to this module is populating the graph FROM
        `evaluate()` + `db.Provenance` (BUILD-PLAN §4.3), which makes
        `evaluate -> evidence` an import edge. Adding `evidence -> evaluate`
        now would make that a cycle.
    The agreement is therefore policed by a test rather than by an import:
    `tests/test_stageG.py::test_evidence_tiers_are_the_project_vocabulary_not_a_second_one`
    pins `L0..L3` against `TIER_ORDER` in order, `S1` against
    `flywheel.SURROGATE_TIER`, `E/F/R` against `weights._TIERS`, and asserts
    every non-ladder member ranks -1. Same fence as
    `tests/test_limits_single_source.py`, for the same defect class.

    ON `M1` RANKING -1. A real measurement is not "worse than L0". It is
    INCOMMENSURABLE with the simulation ladder, and -1 is how this codebase
    already spells that (`S1`). A sea trial of one vessel does not discharge a
    requirement for an L3 verification of another, and an L3 run does not
    discharge a requirement for a measurement; comparing them is the delta
    engine's job (BUILD-PLAN §8.1), done explicitly, never by `>=`.
    """

    NA = "NA"

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    R = "R"
    E = "E"
    F = "F"
    S1 = "S1"
    M1 = "M1"

    # Only the three the badge guard is MEASURED to emit (`evaluate.py:615,638`
    # over badges carrying L1/L2/L3). L0, R, E, F, S1 and M1 get an `-INVALID`
    # member when a producer is measured to emit one — a closed vocabulary means
    # that addition is a reviewed change, which is the property being bought.
    L1_INVALID = "L1-INVALID"
    L2_INVALID = "L2-INVALID"
    L3_INVALID = "L3-INVALID"


class Origin(str, Enum):
    """Where a tier's number physically came from.

    Named `Origin`, not `Provenance`, because `db.Provenance` is a different
    thing (a record of WHAT was computed) and two meanings for one word in one
    project is how the wrong one gets imported.
    """

    NONE = "none"           # NA: no number is being claimed
    COMPUTED = "computed"   # a solver, a rule check or a surrogate produced it
    OBSERVED = "observed"   # an instrument on a real vessel produced it


# Every member is listed. A tier added to the enum without a row here is a
# KeyError at the first edge that touches it, not a quiet default — the enum
# exists to make classification mandatory, so its own table may not have a
# fallback (`docs/LESSONS.md` defect class 1).
ORIGIN: dict[EvidenceTier, Origin] = {
    EvidenceTier.NA: Origin.NONE,
    EvidenceTier.L0: Origin.COMPUTED,
    EvidenceTier.L1: Origin.COMPUTED,
    EvidenceTier.L2: Origin.COMPUTED,
    EvidenceTier.L3: Origin.COMPUTED,
    EvidenceTier.R: Origin.COMPUTED,
    EvidenceTier.E: Origin.COMPUTED,
    EvidenceTier.F: Origin.COMPUTED,
    EvidenceTier.S1: Origin.COMPUTED,
    EvidenceTier.M1: Origin.OBSERVED,
    EvidenceTier.L1_INVALID: Origin.COMPUTED,
    EvidenceTier.L2_INVALID: Origin.COMPUTED,
    EvidenceTier.L3_INVALID: Origin.COMPUTED,
}

# A tier that asserts something about a quantity. Everything except NA.
CLAIM_TIERS: frozenset[EvidenceTier] = frozenset(EvidenceTier) - {EvidenceTier.NA}

# An `-INVALID` badge is a property of a RESULT, never of the run that produced
# it: a solve does not execute "at tier L3-INVALID".
INVALID_TIERS: frozenset[EvidenceTier] = frozenset(
    t for t in EvidenceTier if t.value.endswith("-INVALID"))


class Kind(str, Enum):
    REQUIREMENT = "requirement"   # what the mission demands
    DECISION = "decision"         # a choice made about the design
    ASSUMPTION = "assumption"     # something taken as true without evidence
    EXPERIMENT = "experiment"     # a run that was actually performed
    EVIDENCE = "evidence"         # a result, with its tier and sigma


# Which kinds may support which. A requirement cannot be justified BY a
# decision — that is circular, and it is the most common way a design argument
# quietly becomes self-supporting ("we chose 9.5 because we need 25 kn, and we
# need 25 kn because we chose 9.5").
ALLOWED_SUPPORT: dict[Kind, frozenset[Kind]] = {
    Kind.DECISION: frozenset({Kind.REQUIREMENT, Kind.EVIDENCE, Kind.ASSUMPTION,
                              Kind.DECISION}),
    Kind.EVIDENCE: frozenset({Kind.EXPERIMENT}),
    Kind.EXPERIMENT: frozenset({Kind.DECISION, Kind.ASSUMPTION, Kind.REQUIREMENT}),
    Kind.ASSUMPTION: frozenset({Kind.EVIDENCE, Kind.REQUIREMENT}),
    Kind.REQUIREMENT: frozenset(),
}


# Which kinds may carry which tiers. Same shape as ALLOWED_SUPPORT above, and
# the same argument: a structural rule enforced at construction beats a
# convention enforced by review.
#
# A REQUIREMENT, a DECISION and an ASSUMPTION are NOT measurements. "Raise L/B
# to 9.5" is a choice; it has no fidelity, and letting it wear `L3` would let a
# decision inherit the authority of a solve nobody ran. An ASSUMPTION is by
# definition the thing taken as true WITHOUT evidence — its doubt is carried by
# `confidence`, which is exactly what caps everything built on it. If one of
# these turns out to have a tier, it is not that kind of node: a sourced number
# is EVIDENCE with an EXPERIMENT behind it, and making that conversion explicit
# is the graph doing its job.
ALLOWED_TIERS: dict[Kind, frozenset[EvidenceTier]] = {
    Kind.REQUIREMENT: frozenset({EvidenceTier.NA}),
    Kind.DECISION: frozenset({EvidenceTier.NA}),
    Kind.ASSUMPTION: frozenset({EvidenceTier.NA}),
    Kind.EXPERIMENT: CLAIM_TIERS - INVALID_TIERS,
    Kind.EVIDENCE: CLAIM_TIERS,
}


@dataclass
class Node:
    """One node. `tier` is REQUIRED and typed — there is no permissive default.

    It sits before `confidence` because a field without a default cannot follow
    one with a default; that ordering is load-bearing, not cosmetic. Every
    caller uses `EvidenceGraph.add(**kw)`, so no positional call site moved.

    Validation lives in `__setattr__`, not in `add()` and not only at
    construction, because there are THREE doors and a guard on one of them is
    not a guard:
      - `add()`, the API;
      - `from_json`, which rebuilds nodes with `Node(**d)` straight from a
        file — so a check on the construction API alone would be bypassed by
        anything that had once been written to disk;
      - assignment, since this class is deliberately mutable (the existing
        tests revise a `confidence` in place) and `n.tier = "sea trial"` would
        otherwise walk straight past a `__post_init__`.
    """

    id: str
    kind: Kind
    text: str
    tier: EvidenceTier             # required: an unclassified node is an error
    confidence: float = 1.0        # 0..1, this node's OWN confidence
    value: float | None = None
    sigma: float | None = None
    meta: dict = field(default_factory=dict)
    supports: list[str] = field(default_factory=list)   # ids this node justifies

    def __setattr__(self, name: str, value) -> None:
        if name == "kind":
            try:
                value = Kind(value)
            except ValueError:
                raise ValueError(
                    f"{self.id!r}: unknown node kind {value!r}; "
                    f"allowed: {[k.value for k in Kind]}") from None
        elif name == "tier":
            try:
                value = EvidenceTier(value)
            except ValueError:
                raise ValueError(
                    f"{self.id!r}: {value!r} is not an evidence tier. The "
                    f"vocabulary is CLOSED: {[t.value for t in EvidenceTier]}. "
                    f"A tier this graph does not know ranks -1 nowhere, because "
                    f"it never reaches tier_rank at all.") from None
        # The pair check runs on the PROSPECTIVE value, before the assignment
        # lands. Checking afterwards raised correctly and still left the bad
        # tier on the node — a refused write that sticks is worse than no
        # guard, because the exception says it did not happen. (Caught by
        # `test_the_tier_cannot_be_reassigned_out_of_the_vocabulary_after_
        # construction`, which is why it asserts the old value survives.)
        # `__init__` assigns in field order, so `kind` lands before `tier`
        # exists; the check waits until both are known.
        if name in ("kind", "tier"):
            kind = value if name == "kind" else getattr(self, "kind", None)
            tier = value if name == "tier" else getattr(self, "tier", None)
            if kind is not None and tier is not None \
                    and tier not in ALLOWED_TIERS[kind]:
                raise ValueError(
                    f"{self.id!r}: a {kind.value} may not carry tier "
                    f"{tier.value!r}; allowed: "
                    f"{sorted(t.value for t in ALLOWED_TIERS[kind])}")
        object.__setattr__(self, name, value)

    @property
    def origin(self) -> Origin:
        """Computed, observed, or claiming nothing."""
        return ORIGIN[self.tier]


class EvidenceGraph:
    """Append-mostly DAG. Cycles are rejected at insertion, not discovered later."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    # --- construction ------------------------------------------------------
    def add(self, node_id: str, kind: Kind, text: str, **kw) -> Node:
        """Add a node. `tier=` is REQUIRED (see `Node`); omitting it is a
        TypeError from the dataclass, which is the single place the field is
        declared. It is not defaulted here — a default in the API would be a
        second declaration of the same rule, and the permissive default is the
        defect being closed."""
        if node_id in self.nodes:
            raise ValueError(f"duplicate node id {node_id!r}")
        n = Node(id=node_id, kind=kind, text=text, **kw)
        self.nodes[node_id] = n
        return n

    def support(self, supporter: str, supported: str) -> None:
        """Record that `supporter` is part of the justification for `supported`."""
        for i in (supporter, supported):
            if i not in self.nodes:
                raise KeyError(i)
        s, t = self.nodes[supporter], self.nodes[supported]
        if s.kind not in ALLOWED_SUPPORT[t.kind]:
            raise ValueError(
                f"a {s.kind.value} may not support a {t.kind.value} "
                f"({supporter!r} -> {supported!r}); allowed: "
                f"{sorted(k.value for k in ALLOWED_SUPPORT[t.kind])}")
        # An EXPERIMENT is the only thing that may support EVIDENCE (above), so
        # this one edge is where a number acquires its provenance — and it is
        # the only place laundering can happen without anyone writing a false
        # sentence. A simulation cannot yield an observation and an instrument
        # cannot yield a solver result; either would let the delta engine
        # compare a number against itself and report agreement.
        if t.kind is Kind.EVIDENCE and s.kind is Kind.EXPERIMENT:
            if s.origin is not t.origin:
                raise ValueError(
                    f"{s.origin.value} experiment {supporter!r} ({s.tier.value}) "
                    f"may not produce {t.origin.value} evidence {supported!r} "
                    f"({t.tier.value})")
        # Edges run supporter -> supported. Adding one closes a cycle exactly
        # when the SUPPORTER is already reachable FROM the supported node.
        # (Written the other way round first, which detected nothing: the new
        # edge's own endpoint was never on the far side of the search.)
        if supporter == supported:
            raise ValueError(f"cycle: {supporter!r} cannot support itself")
        if supporter in self._reachable(supported):
            raise ValueError(f"cycle: {supported!r} already supports "
                             f"{supporter!r} transitively")
        if supported not in s.supports:
            s.supports.append(supported)

    def _reachable(self, start: str) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            cur = stack.pop()
            for nxt in self.nodes[cur].supports:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    def supporters(self, node_id: str) -> list[Node]:
        return [n for n in self.nodes.values() if node_id in n.supports]

    # --- the queries that make it worth having -----------------------------
    def confidence(self, node_id: str) -> float:
        """Weakest-link confidence: the minimum over the node and ALL ancestors.

        A node with no supporters is worth its own confidence — which for an
        ASSUMPTION is the point: an unevidenced assumption caps everything
        built on it, and that cap is visible from the top of the design.

        Written as an explicit ancestor SET rather than as a recursion with a
        path-visited guard. The recursive form was correct here (the visited
        set tracked the current path, and the graph is a DAG by construction,
        so a diamond simply recomputed a shared ancestor to the same value) —
        but it could not be shown correct at a glance, it was exponential in a
        deep diamond, and a reviewer read its `return 1.0` guard as silently
        crediting shared subgraphs with perfect confidence. Since the result is
        a minimum over a reachable set, it is path-INDEPENDENT, so computing
        the set once is both obviously right and linear.
        """
        if node_id not in self.nodes:
            raise KeyError(node_id)
        return min([self.nodes[i].confidence
                    for i in self._ancestors(node_id) | {node_id}])

    def _ancestors(self, node_id: str) -> set[str]:
        """Everything that transitively justifies `node_id`."""
        seen: set[str] = set()
        stack = [node_id]
        while stack:
            for s in self.supporters(stack.pop()):
                if s.id not in seen:
                    seen.add(s.id)
                    stack.append(s.id)
        return seen

    def unsupported(self, kind: Kind = Kind.DECISION) -> list[Node]:
        """Nodes of `kind` with no path to any EVIDENCE. The honest agenda."""
        out = []
        for n in self.nodes.values():
            if n.kind is not kind:
                continue
            if not self._has_evidence(n.id, frozenset()):
                out.append(n)
        return out

    def _has_evidence(self, node_id: str, seen: frozenset[str]) -> bool:
        if node_id in seen:
            return False
        for s in self.supporters(node_id):
            if s.kind is Kind.EVIDENCE:
                return True
            if self._has_evidence(s.id, seen | {node_id}):
                return True
        return False

    def explain(self, node_id: str, depth: int = 0) -> str:
        """The justification chain behind one node, as readable text."""
        n = self.nodes[node_id]
        pad = "  " * depth
        head = f"{pad}{n.kind.value.upper():11s} {n.text}"
        if n.value is not None:
            head += f"  [{n.value:.4g}"
            head += f" +/- {n.sigma:.3g}" if n.sigma is not None else ""
            # `.value`, never the member: on 3.12 an f-string of a str-mixin
            # enum renders "EvidenceTier.L3", and the badge in a report has to
            # be the badge the rest of the project greps for.
            head += (f", {n.tier.value}]" if n.tier is not EvidenceTier.NA
                     else "]")
        head += f"  (conf {self.confidence(node_id) * 100:.1f}%)"
        parts = [head]
        for s in self.supporters(node_id):
            parts.append(self.explain(s.id, depth + 1))
        return "\n".join(parts)

    # --- persistence -------------------------------------------------------
    def to_json(self) -> str:
        # Both enums are written as their VALUE. `asdict` copies the member
        # through, and `json.dumps` of a str-mixin enum happens to emit the
        # value today — relying on that would make the file format depend on a
        # detail of the enum's mixin, so it is spelled out.
        return json.dumps(
            {i: {**asdict(n), "kind": n.kind.value, "tier": n.tier.value}
             for i, n in self.nodes.items()},
            indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "EvidenceGraph":
        """Rebuild from JSON. The tier is re-validated on the way IN.

        A file is an untrusted boundary: it may have been written by an older
        build, hand-edited, or produced by whatever ingests telemetry. Both
        enums are therefore parsed by `Node.__post_init__`, so an unknown tier
        fails here rather than becoming a `str` that no comparison recognises.
        Nothing is coerced or dropped: a node this vocabulary cannot express is
        refused, because expressing it approximately is the laundering.
        """
        g = cls()
        for i, d in json.loads(text).items():
            g.nodes[i] = Node(**dict(d))
        return g

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceGraph":
        return cls.from_json(Path(path).read_text())
