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
# `l_pmb` -> `pmb` + `r_stem` on 2026-08-26 (audit finding, gates report
# §5.2 item 5): the table nudged `l_pmb`, a gene REMOVED from the grammar,
# and `_nudge`'s `if gene not in out: continue` skipped it SILENTLY — so
# the SPEARHEAD and BOX repairs ran without the parallel-midbody lever, and
# neither ever mentioned `r_stem`, the gene grammar.py:355 names "the
# mirror of r_transom; 0 = a pointed bow". `_assert_repair_genes_exist`
# below turns the silent skip into a loud failure forever.
_REPAIR: dict[str, tuple[tuple[str, float], ...]] = {
    # forefoot/beta_bow move WITH the fullness: a full bow needs draft and
    # a moderate V to enclose its area — MEASURED 2026-08-26 on the
    # reference seed: r_stem nudged to 0.14 against forefoot 0.6 refused at
    # section.solve ("area 0.25 m^2 unreachable at draft 0.257 m").
    "SPEARHEAD": (("Cp", +1.0), ("r_transom", +1.0), ("r_stem", +1.0),
                  ("pmb", +1.0), ("x_mb", -0.5), ("forefoot", -1.0),
                  ("beta_bow", -0.5)),
    "BOX": (("Cp", -1.0), ("r_transom", -1.0), ("pmb", -1.0),
            ("r_stem", -0.5)),
    "PLANK": (("sheer_rise", +1.0), ("rocker", +1.0), ("forefoot", +1.0),
              ("D", +0.5)),
    "PYRAMID": (("Cp", +1.0), ("r_transom", +1.0), ("sheer_rise", +1.0)),
    # `dwl` DOES NOT JOIN the plan pathologies, and that is a MEASURED
    # negative result (2026-08-27, the day the design waterline landed).
    # The hand-CHOSEN barge configuration proves dwl is the anti-WAVY-PLAN
    # lever (margin +4.26 -> +0.06), so the obvious move was
    # ("dwl", +1.0) + ("rb_transom", +0.5) on WAIST and WAVY-PLAN — and it
    # made the walk WORSE, 2/8 -> 0/8 wins on the same seeds (with
    # rb_stem added too: still 0/8). Mechanism: a naive dwl step arrives
    # with UNCHOSEN rb targets, and the faired solve then delivers a
    # waterline that deviates from a curve nobody designed — the walk
    # burns its iterations on hulls whose plan the critic likes no
    # better. Using dwl well needs the rb/cwp targets DERIVED from the
    # descriptors (set rb_transom from the delivered transom beam, not
    # nudged blindly), which is repair-table-shaped work for the knuckle
    # slice. Until then: measured better without it.
    "WAIST": (("lcb", -1.0), ("x_mb", -0.5), ("r_transom", -0.5)),
    "WAVY-PLAN": (("r_transom", -0.5), ("lcb", -0.5), ("Cp", +0.5)),
    "PROPORTION": (("BWL", -1.0), ("LWL", +1.0)),
}


def _assert_repair_genes_exist() -> None:
    """A repair that names a gene the grammar no longer has is a silent
    no-op (measured: `l_pmb` sat here from its removal until 2026-08-26).
    Import-time check so a future gene rename fails loudly instead."""
    from . import grammar as _g
    for pathology, nudges in _REPAIR.items():
        for gene, _sign in nudges:
            if gene not in _g.NAMES:
                raise AssertionError(
                    f"_REPAIR[{pathology!r}] names {gene!r}, which is not in "
                    f"grammar.NAMES — a silently skipped repair lever")


_assert_repair_genes_exist()


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


#: THE AFT-MUTATION PRIOR (CFD audit P2-14, finding R2). MEASURED on the
#: hookprobe campaign: v1 -> v2 -> v3 fell 3034 -> 2998 -> 2966 N under
#: AFT edits (transom clearance, eased shoulder), monotonically, and the
#: family is wave-dominated — pressure is 78-83% of total drag on every
#: bluff/hybrid anchor in the book against 39% on the slender benchmark.
#:
#: WHAT THIS MAY AND MAY NOT DO. Each of those steps is 1.1-1.2%, INSIDE
#: the +/-2.5% window scatter, and v2 carries 19% more cells than v3 —
#: `cfd_kb.compare` refuses the pair outright. So the magnitude is not a
#: prediction and must never reach a score. The DIRECTION is safe for
#: exactly one job: deciding what a blind search TRIES FIRST. A prior that
#: only reorders proposals cannot make a wrong hull win; it can only find
#: the right one sooner, and if the prior is wrong the search still
#: explores everything and pays a little more for it.
_AFT_GENES = ("r_transom", "beta_transom", "beta_run", "rb_transom",
              "rocker", "tun_w", "tun_crown", "tun_len")

#: How much likelier an aft gene is to be picked when the blind explorer
#: fires on a bluff-sterned hull. DECLARED, basis approx: the campaign
#: gives a direction, not a weight. 3x is chosen to bias the draw without
#: starving the other genes.
#:
#: THE ARITHMETIC IN THIS COMMENT WENT STALE ONE ARITY EVENT AFTER IT WAS
#: WRITTEN (found 2026-09-01 by the end-to-end integration audit). It read
#: "at 8 aft genes of 34, uniform gives them 24% of picks and this gives
#: 49%" — correct at N_PARAMS 34, and `ch2_z`/`ch2_y` took the grammar to
#: 36 the same week. At 36 the true figures are 22.2% uniform and 46.2%
#: weighted. A number in a comment cannot be recomputed by the reader, so
#: `test_the_aft_prior_share_is_what_the_comment_claims` recomputes both
#: from `grammar.N_PARAMS` and fails when the arity moves again — the same
#: discipline the rest of this repository applies to numbers in code.
#:
#: `split_w` / `split_len` are aft features and are deliberately NOT in
#: `_AFT_GENES`: no production stream draws the split stern at all
#: (Gate REACHABILITY), so weighting them would bias the draw toward genes
#: that are pinned at zero.
AFT_EXPLORE_WEIGHT = 3.0


def aft_prior_shares() -> tuple[float, float]:
    """(uniform share, weighted share) of picks that land on an aft gene.

    What the weighting BUYS, recomputed rather than remembered — see the
    comment on `AFT_EXPLORE_WEIGHT` for the arity event that made this a
    function instead of a sentence.
    """
    n = grammar.N_PARAMS
    k = len(_AFT_GENES)
    w = AFT_EXPLORE_WEIGHT
    return k / n, (w * k) / (w * k + (n - k))


#: A stern is "bluff" when the SAC still carries area at the transom.
#: CALIBRATED on the one anchor that has BOTH a genome and a measured
#: force split: houseboat19 (`data/exports/houseboat19/genome.json`,
#: `runs/hb19_7kn`) reads sac_transom 0.4401 with 77.9% pressure drag.
#: The slender benchmark sits far below. 0.30 is a declared threshold
#: between them, not a measured boundary — nobody has run the sweep — and
#: it is safe to declare because being wrong costs search order and
#: nothing else.
BLUFF_SAC_TRANSOM = 0.30


def is_bluff_stern(descriptors: dict) -> bool:
    """Does this hull belong to the family R2 was measured on?"""
    v = descriptors.get("sac_transom")
    return v is not None and float(v) >= BLUFF_SAC_TRANSOM


def _bounds(bounds):
    """(lo, hi) gene dicts — the caller's box, or the grammar's.

    THE CLIMB MUST SEARCH INSIDE THE BOX IT WILL BE JUDGED IN. MEASURED
    2026-09-01 by the end-to-end integration audit: `optimize._DrawBoxSampling`
    climbed seeds to plausibility and then ran `np.clip(X, problem.xl,
    problem.xu)` to force them into the MISSION's box (LWL 14.4-17.6 and
    BWL 3.6-4.4 for a "16 m x 4 m" brief, plus the Froude window on Cp). The
    climb reached plausibility on 9 of 9 seeds and the clip destroyed ALL
    NINE — so the initial population was 0 of 24 shape-plausible for exactly
    the missions the climb was added to serve, under a comment claiming "half
    the initial population is climbed to plausibility".

    Repairing a hull and then moving it is not repairing it. `bounds` is
    None everywhere the climb is used standalone, which keeps the grammar box
    and every recorded archive unchanged.
    """
    if bounds is None:
        return ({n: float(v) for n, v in zip(grammar.NAMES, grammar.LOW)},
                {n: float(v) for n, v in zip(grammar.NAMES, grammar.HIGH)})
    lo, hi = bounds
    return ({n: float(v) for n, v in zip(grammar.NAMES, lo)},
            {n: float(v) for n, v in zip(grammar.NAMES, hi)})


def _clip(g: dict, bounds=None) -> dict:
    lo, hi = _bounds(bounds)
    out = {k: float(min(hi[k], max(lo[k], v))) for k, v in g.items() if k in lo}
    # PROJECT (Cp, lcb) INTO THE DELIVERABLE BANDS (2026-08-26). Since
    # `sac_exponents` inverts the actual a(x) with pmb/r_stem, a nudge that
    # raises Cp while holding lcb can ask for a curve the family cannot
    # deliver; `inspect` then returns None and — measured on the archive
    # test — every trial of a 60-iteration search died silently, archiving
    # NOTHING. A repair operator that mutates a design target keeps the
    # companion target consistent, the same way a designer re-fairs LCB
    # after a Lackenby shift.
    if "Cp" in out:
        from .geometry import GeometryError, cp_band, lcb_band
        b_lo, b_hi = cp_band(out.get("LWL", 10.0), out.get("x_mb", 0.5),
                             out.get("r_transom", 0.3),
                             out.get("r_stem", 0.0), out.get("pmb", 0.0))
        eps = 1e-3 * max(b_hi - b_lo, 1e-6)
        out["Cp"] = float(min(min(b_hi - eps, hi["Cp"]),
                              max(max(b_lo + eps, lo["Cp"]), out["Cp"])))
        if "lcb" in out:
            try:
                l_lo, l_hi = lcb_band(out.get("LWL", 10.0),
                                      out.get("x_mb", 0.5),
                                      out.get("r_transom", 0.3), out["Cp"],
                                      out.get("r_stem", 0.0),
                                      out.get("pmb", 0.0))
                eps = 1e-2 * max(l_hi - l_lo, 1e-6)
                out["lcb"] = float(min(min(l_hi - eps, hi["lcb"]),
                                       max(max(l_lo + eps, lo["lcb"]),
                                           out["lcb"])))
            except GeometryError:
                pass                      # Cp at a band edge; check() decides
    return out


def inspect(genome: dict, family: str | None = None,
            bounds=None) -> Candidate | None:
    """Build, describe and judge one genome. None when the kernel refuses it.

    `family` IS THE MISSION'S, and it must be, because the bars differ.
    MEASURED 2026-09-01 by the end-to-end integration audit: this function
    judged by the GENERAL (monohull-calibrated) bands while
    `evaluate`'s `shape` constraint row — the row this whole repair operator
    exists to satisfy — judges by `_FAMILY_BAR[mission.hull_family]`. On a
    barge those differ on exactly the three descriptors the barge row was
    added to relax: plan_waist 0.12 vs 0.02, waterline_convexity 0.70 vs
    0.80, pmb_frac 0.98 vs 0.90. So the repair was climbing toward a
    criterion the ladder does not use — and toward the very monohull bars
    that `morphology._FAMILY_BAR` records as having made "every houseboat
    mission's shape row unsatisfiable BY CONSTRUCTION".

    None (the default) keeps the general bands, so every existing caller and
    every recorded archive is unchanged.
    """
    g = _clip(genome, bounds)
    try:
        x = grammar.vector(g)
        rep = grammar.check(x)
        hull = Hull(x)
        d = describe(from_hull(hull))
    except (GeometryError, ValueError, ZeroDivisionError, KeyError):
        return None
    c = critique(d, family=family)
    return Candidate(genome=g, ok=bool(c.ok and rep.ok), score=float(c.score),
                     pathologies=c.pathologies,
                     reasons=tuple(str(f) for f in c.findings),
                     descriptors=d.as_dict(),
                     engineering="L0-ok" if rep.ok else "L0-fail")


def _nudge(genome: dict, cand: Candidate, step: float,
           rng: np.random.Generator, bounds=None) -> dict:
    """Move the genes that drive the descriptors this hull actually failed.

    The STEP is scaled by the span of the box the caller is searching in, not
    of the grammar: with a mission box of LWL 14.4-17.6 m, a step sized on the
    grammar's 2.5-24 m span moves 2.6 m and saturates an edge on every move.
    """
    lo, hi = _bounds(bounds)
    out = dict(genome)
    moved = False
    for p in cand.pathologies:
        for gene, sign in _REPAIR.get(p, ()):
            if gene not in out:
                # A 16-key seed predates the post-hoc genes; the repair's
                # whole point is to hand it exactly those levers (r_stem is
                # THE anti-spearhead gene). Seed the gene at its proven
                # no-op default and nudge from there.
                if gene in grammar.POST_HOC_DEFAULTS:
                    out[gene] = float(grammar.POST_HOC_DEFAULTS[gene])
                else:
                    continue
            span = hi[gene] - lo[gene]
            out[gene] += sign * step * span * (0.5 + rng.random())
            moved = True
    if not moved:                      # nothing known to repair it: explore
        genes, k = list(out), max(1, len(out) // 4)
        if is_bluff_stern(cand.descriptors):
            # AFT FIRST on the family the campaign measured. Weighted draw
            # ONLY on this branch: an unweighted `rng.choice` and a
            # `p=uniform` one do not consume the stream identically, so
            # every non-bluff search stays bit-identical to what the
            # archives already hold.
            w = np.array([AFT_EXPLORE_WEIGHT if g in _AFT_GENES else 1.0
                          for g in genes], float)
            picked = rng.choice(genes, size=k, replace=False, p=w / w.sum())
        else:
            picked = rng.choice(genes, size=k, replace=False)
        for gene in picked:
            span = hi[gene] - lo[gene]
            out[gene] += rng.normal(0.0, 0.5 * step) * span
    return _clip(out, bounds)


def _derived_dwl(genome: dict, hull=None) -> dict | None:
    """The SMART dwl move: design the waterline the hull already has, faired.

    The recorded negative result above stands — nudging `dwl` blindly hands
    the joint solve targets nobody chose, and the walk got WORSE (2/8 ->
    0/8). The move that works is the one a designer would make: read the
    DELIVERED plan off the hull, then set the designed curve's parameters
    to match it — same transom ratio, same stem ratio, same waterplane
    fullness. The designed family is convex/unimodal BY CONSTRUCTION, so
    the delivered plan is replaced by the nearest FAIR member of the
    ordinate family: the wiggles the critic names as WAIST / WAVY-PLAN are
    exactly what this subtracts, while beam, fullness and displacement
    stay what they were (the SAC is untouched and remains the area
    contract).

    Returns the candidate genome, or None when the genome already has dwl
    authority or the hull cannot be built.
    """
    from . import grammar as _g
    import numpy as _np
    if float(genome.get("dwl", 0.0) or 0.0) > 0.0:
        return None
    try:
        from .geometry import Hull as _Hull
        h = hull if hull is not None else _Hull(_g.vector(genome))
        y = _np.asarray(h.y_wl, float)
        y_max = float(y.max())
        if y_max <= 1e-9:
            return None
        b = y / y_max
        L = float(h.x[-1] - h.x[0])
        cwp = float(_np.trapezoid(b, h.x) / L)     # plan fullness, measured
        out = dict(genome)
        out["dwl"] = 1.0
        out["rb_transom"] = float(_np.clip(b[0], 0.0, 0.95))
        out["rb_stem"] = float(_np.clip(b[-1], 0.0, 0.5))
        out["cwp_x"] = float(_np.clip(cwp - float(genome["Cp"]),
                                      -0.20, 0.25))
        return _clip(out)
    except Exception:                              # noqa: BLE001 — a move,
        return None                                # not a verdict


def search(seed_genome: dict, iterations: int = 400, step: float = 0.12,
           rng: np.random.Generator | None = None,
           journal: Path | str | None = None,
           family: str | None = None,
           bounds=None) -> tuple[Candidate | None, list[Candidate]]:
    """Hill-climb toward morphological plausibility, recording EVERY attempt.

    Returns `(best, archive)`. The archive is the training corpus: accepted and
    rejected alike, each with its descriptors and the named reason it failed.

    `family` is the MISSION's hull family and is handed to every `inspect`
    call, so the climb optimises the SAME criterion `evaluate`'s `shape` row
    scores — see `inspect` for the measurement that made this necessary.
    None keeps the general bands and every recorded archive unchanged.
    """
    rng = rng or np.random.default_rng(0)
    cur = inspect(seed_genome, family, bounds)
    archive: list[Candidate] = []
    best = cur if (cur and cur.ok) else None
    cur_score = cur.score if cur else -1.0

    # THE DERIVED-dwl OPENING MOVE (Phase 3): when the seed's findings are
    # plan-shaped, try designing the waterline it already has ONCE, before
    # any random walk — deterministic, cheap (one extra inspect), and
    # measured to be the move the blind nudge could not make.
    if cur is not None and cur.pathologies and (
            {"WAIST", "WAVY-PLAN", "SPEARHEAD"} & set(cur.pathologies)):
        smart = _derived_dwl(cur.genome if cur else seed_genome)
        if smart is not None:
            cand = inspect(smart, family, bounds)
            if cand is not None:
                archive.append(cand)
                if cand.engineering == "L0-ok" and cand.score > cur_score:
                    cur, cur_score = cand, cand.score
                if cand.ok and (best is None or cand.score >= best.score):
                    best = cand

    for _it in range(iterations):
        base = cur.genome if cur else _clip(seed_genome)
        # THE DERIVED MOVE RETRIES MID-WALK (measured: with the opening
        # move only, 12 of 18 losing walks ended at dwl = 0 — their SEED's
        # derived candidate failed, but the walk then moved the fullness
        # genes and never got a second chance to design the waterline the
        # EVOLVED hull has). Every 40th iteration, same conditions as the
        # opening move, deterministic, no RNG consumed.
        if (_it % 40 == 39 and cur is not None and cur.pathologies
                and {"WAIST", "WAVY-PLAN", "SPEARHEAD"} & set(cur.pathologies)
                and float(cur.genome.get("dwl", 0.0) or 0.0) == 0.0):
            smart = _derived_dwl(cur.genome)
            if smart is not None:
                cand = inspect(smart, family, bounds)
                if cand is not None:
                    archive.append(cand)
                    if (cand.engineering == "L0-ok"
                            and cand.score > cur_score):
                        cur, cur_score = cand, cand.score
                    if cand.ok and (best is None
                                    or cand.score >= best.score):
                        best = cand
        trial = (_nudge(base, cur, step, rng, bounds) if cur
                 else _clip(seed_genome, bounds))
        cand = inspect(trial, family, bounds)
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
