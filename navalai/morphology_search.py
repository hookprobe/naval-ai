"""GENERATE -> INSPECT -> CLASSIFY -> MUTATE: the loop, without a network.

WHY THERE IS NO NEURAL NETWORK IN HERE, and why that is the point.

The obvious architecture for this problem is a learned one: a PointNet
autoencoder over reference hulls, a StyleGAN whose latent space is inverted
from reference images, an MLP mapping that latent to CAD parameters, and
Bayesian optimisation over the result. Every piece of that is sound and none of
it can be trained today, for a reason that is a MEASUREMENT rather than an
opinion:

    the entire real-geometry corpus on disk is 58 hulls -- 51 Delft yachts,
    one Series 60, one Wigley, five Fridsma planing models, one container
    ship -- which is effectively ONE morphological family.

A latent space fitted to that learns "Delft yacht", badly. Ship-D reports the
same failure from the other end: 30,000 parametric hulls still contain a great
many shapes no naval architect would recognise, so volume alone does not buy
plausibility. The missing ingredient is a VALIDATED manifold, not a bigger
sample.

So this module closes the loop using the DETERMINISTIC critic
(`navalai.morphology.critique`) as the fitness signal. It needs no training
data, and — this is the part that matters — every iteration it runs is a
labelled example: genome, descriptors, verdict, and the named reason. Running
it is how the corpus for a learned critic gets built. The negative examples
this project needs cannot be downloaded; they have to be generated, and they
are generated here.

MUTATION IS DIRECTED, NEVER BLIND. A rejected hull names the descriptor that
failed and the bar it missed, and `_nudge` moves the genes known to drive that
descriptor in the direction that would fix it. Blind mutation on a 16-gene
vector against an 89% rejection rate is a random walk.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import grammar
from .geometry import GeometryError, Hull
from .morphology import Critique, Descriptors, critique, describe, from_hull

# Which genes move which descriptor, and in which direction, to REPAIR a
# failure. Signs are +1 to increase the gene when the pathology fires.
# Derived from the kernel's own construction, not from a fit:
#   beam_carried  rises with a fuller SAC (Cp) and fuller ends (r_transom)
#   plan_waist    is a non-monotone SAC; moving the target LCB and the
#                 max-area station apart relieves it
#   depth_variation rises with sheer_rise, rocker and forefoot
#   convexity     improves as the ends stop fighting the middle
_REPAIR: dict[str, tuple[tuple[str, float], ...]] = {
    "SPEARHEAD": (("Cp", +1.0), ("r_transom", +1.0), ("l_pmb", +1.0),
                  ("x_mb", -0.5)),
    "BOX": (("Cp", -1.0), ("r_transom", -1.0), ("l_pmb", -1.0)),
    "PLANK": (("sheer_rise", +1.0), ("rocker", +1.0), ("forefoot", +1.0),
              ("D", +0.5)),
    "PYRAMID": (("Cp", +1.0), ("r_transom", +1.0), ("sheer_rise", +1.0)),
    "WAIST": (("lcb", -1.0), ("x_mb", -0.5), ("r_transom", -0.5)),
    "WAVY-PLAN": (("r_transom", -0.5), ("lcb", -0.5), ("Cp", +0.5)),
    "PROPORTION": (("BWL", -1.0), ("LWL", +1.0)),
}


@dataclass
class Candidate:
    genome: dict
    ok: bool
    score: float
    pathologies: tuple[str, ...]
    reasons: tuple[str, ...]
    descriptors: dict = field(default_factory=dict)
    engineering: str = "not-run"

    def as_record(self) -> dict:
        d = asdict(self)
        d["pathologies"] = list(self.pathologies)
        d["reasons"] = list(self.reasons)
        return d


def _clip(g: dict) -> dict:
    lo = {n: float(v) for n, v in zip(grammar.NAMES, grammar.LOW)}
    hi = {n: float(v) for n, v in zip(grammar.NAMES, grammar.HIGH)}
    return {k: float(min(hi[k], max(lo[k], v))) for k, v in g.items() if k in lo}


def inspect(genome: dict) -> Candidate | None:
    """Build, describe and judge one genome. None when the kernel refuses it."""
    g = _clip(genome)
    try:
        x = grammar.vector(g)
        rep = grammar.check(x)
        hull = Hull(x)
        d = describe(from_hull(hull))
    except (GeometryError, ValueError, ZeroDivisionError, KeyError):
        return None
    c = critique(d)
    return Candidate(genome=g, ok=bool(c.ok and rep.ok), score=float(c.score),
                     pathologies=c.pathologies,
                     reasons=tuple(str(f) for f in c.findings),
                     descriptors=d.as_dict(),
                     engineering="L0-ok" if rep.ok else "L0-fail")


def _nudge(genome: dict, cand: Candidate, step: float,
           rng: np.random.Generator) -> dict:
    """Move the genes that drive the descriptors this hull actually failed."""
    lo = {n: float(v) for n, v in zip(grammar.NAMES, grammar.LOW)}
    hi = {n: float(v) for n, v in zip(grammar.NAMES, grammar.HIGH)}
    out = dict(genome)
    moved = False
    for p in cand.pathologies:
        for gene, sign in _REPAIR.get(p, ()):
            if gene not in out:
                continue
            span = hi[gene] - lo[gene]
            out[gene] += sign * step * span * (0.5 + rng.random())
            moved = True
    if not moved:                      # nothing known to repair it: explore
        for gene in rng.choice(list(out), size=max(1, len(out) // 4),
                               replace=False):
            span = hi[gene] - lo[gene]
            out[gene] += rng.normal(0.0, 0.5 * step) * span
    return _clip(out)


def search(seed_genome: dict, iterations: int = 400, step: float = 0.12,
           rng: np.random.Generator | None = None,
           journal: Path | str | None = None) -> tuple[Candidate | None, list[Candidate]]:
    """Hill-climb toward morphological plausibility, recording EVERY attempt.

    Returns `(best, archive)`. The archive is the training corpus: accepted and
    rejected alike, each with its descriptors and the named reason it failed.
    """
    rng = rng or np.random.default_rng(0)
    cur = inspect(seed_genome)
    archive: list[Candidate] = []
    best = cur if (cur and cur.ok) else None
    cur_score = cur.score if cur else -1.0

    for _ in range(iterations):
        base = cur.genome if cur else _clip(seed_genome)
        trial = _nudge(base, cur, step, rng) if cur else _clip(seed_genome)
        cand = inspect(trial)
        if cand is None:
            continue
        archive.append(cand)
        # THE CLIMB STAYS INSIDE THE FEASIBLE SET. MEASURED before this guard:
        # 7 of 16 seeds ended with "no L0-valid neighbour" -- the hill-climb had
        # followed the morphology score into a region where the algebraic gate
        # refuses everything, and then had nowhere to go. Morphological
        # plausibility is not worth having on an object the grammar rejects, so
        # an L0 failure never becomes the current point ONCE A FEASIBLE POINT
        # IS HELD. The first version of this guard simply skipped every
        # infeasible candidate, which FROZE a search whose seed was itself
        # infeasible -- the rate went 56% -> 12%, worse than doing nothing,
        # because `cur` could never move off a starting point it was not
        # allowed to leave. So: explore freely until the first feasible hull is
        # found, then never step back out. Rejected hulls are still ARCHIVED --
        # a rejected hull is training data, which is why this loop records
        # rather than discards.
        feasible = cand.engineering == "L0-ok"
        have = cur is not None and cur.engineering == "L0-ok"
        if have and not feasible:
            continue          # never step OUT of the feasible set
        if feasible and not have:
            cur, cur_score = cand, cand.score      # first foothold: take it
        elif cand.score > cur_score or (cand.score == cur_score
                                        and rng.random() < 0.3):
            cur, cur_score = cand, cand.score
        if cand.ok and (best is None or cand.score >= best.score):
            best = cand

    if journal:
        p = Path(journal)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as fh:
            for c in archive:
                fh.write(json.dumps(c.as_record()) + "\n")
    return best, archive
