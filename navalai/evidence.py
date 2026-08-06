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
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


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


@dataclass
class Node:
    id: str
    kind: Kind
    text: str
    confidence: float = 1.0        # 0..1, this node's OWN confidence
    tier: str = ""                 # L0/L1/L2/L3/R where applicable
    value: float | None = None
    sigma: float | None = None
    meta: dict = field(default_factory=dict)
    supports: list[str] = field(default_factory=list)   # ids this node justifies


class EvidenceGraph:
    """Append-mostly DAG. Cycles are rejected at insertion, not discovered later."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    # --- construction ------------------------------------------------------
    def add(self, node_id: str, kind: Kind, text: str, **kw) -> Node:
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
            head += f", {n.tier}]" if n.tier else "]"
        head += f"  (conf {self.confidence(node_id) * 100:.1f}%)"
        parts = [head]
        for s in self.supporters(node_id):
            parts.append(self.explain(s.id, depth + 1))
        return "\n".join(parts)

    # --- persistence -------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(
            {i: {**asdict(n), "kind": n.kind.value} for i, n in self.nodes.items()},
            indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "EvidenceGraph":
        g = cls()
        for i, d in json.loads(text).items():
            d = dict(d)
            d["kind"] = Kind(d["kind"])
            g.nodes[i] = Node(**d)
        return g

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceGraph":
        return cls.from_json(Path(path).read_text())
