"""Phase 1 baseline optimizer: NSGA-II directly on grammar parameters (pymoo).

BuildPlan: "Baseline optimizer: NSGA-II directly on grammar parameters (no
learning needed yet)." Objectives are mission-level: energy per mile, build
material, stability margin. Constraints come from the ladder itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from . import grammar
from .energy import shell_area_m2
from .evaluate import CONSTRAINT_NAMES, INFEASIBLE_G, evaluate
from .geometry import Hull
from .limits import GM_OVER_BEAM_MAX, gm_floor
from .mission import MissionSpec


def _score(x, mission: MissionSpec, policy, names, provenance=None):
    """One design through the ladder -> (F_row, G_row), or None to REJECT.

    THE ONE SCORING BODY for both problems (they had drifted into two
    transcribed copies — R0.2e). None means "leave the caller's infeasible
    defaults standing" (F = 1e9, G = INFEASIBLE_G), the same Fitness = inf
    pattern the L0 reject has always used.

    `ev.ok` IS CONSULTED (R0.2a — audit G6-01). The refusal classes that are
    deliberately NOT constraint rows — `early` (speed outside the L1 model),
    the multihull stability refusal, the manning refusals — used to leave
    every g row satisfied, so NSGA-II ranked the design FEASIBLE and a
    multihull front arrived 100% ok=False (audit G6-02). They are still not
    rows: the E4 finding stands (a constant row carries no gradient while
    occupying a dimension, and would change the vector's shape for
    monohulls). Instead a design that is refused WITHOUT a positive g row is
    rejected outright here. A design whose refusal IS a g row keeps its row —
    that is the gradient NSGA-II descends out of the infeasible region — and
    constraint domination already keeps it from dominating any feasible one.
    """
    ev = evaluate(x, mission, policy=policy, provenance=provenance)
    if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
        return None
    if not ev.ok and not any(ev.g[k] > 0.0 for k in names if k in ev.g):
        return None
    hull = Hull(x)
    # Build material is the VESSEL's, not one moulded surface's (R0.2c —
    # audit: the inline copy missed the hull count). `shell_area_m2` is the
    # single home of the planked-to-the-sheer integral (gap C9); the bridge
    # deck contributes nothing because the genome does not carry one, which
    # is already a recorded caveat in `ev.vessel`.
    n_hulls = int(ev.vessel.get("n_hulls", 1))
    build_area = n_hulls * (shell_area_m2(hull) + hull.deck_area())
    # GM is a BAND, not a maximisation target — above ~0.20*B it is a hazard
    # (GM/B 0.82 gave a 1.5 s roll period on a boat sold as a dayboat). The
    # band middle uses the FLOATED beam (R0.2d — the design chine beam is not
    # the beam the metacentre was computed from). The monohull floor is the
    # only floor that exists; a multihull cannot reach this line until a
    # sourced multihull criterion lands (R2.2), because its stability refusal
    # has no g row and is rejected above.
    gm_mid = 0.5 * (gm_floor(mission.design_category)
                    + GM_OVER_BEAM_MAX * float(ev.hydro.b_wl_max))
    f_row = (ev.energy.wh_per_nm, build_area, abs(ev.gm_m - gm_mid))
    g_row = [ev.g[k] for k in names]
    return f_row, g_row


class HullProblem(Problem):
    """3 objectives: min Wh/NM, min build panel area (m^2), GM toward a BAND.
    Inequality constraints (g <= 0) are the ladder's own — CONSTRAINT_NAMES —
    plus, when a compiled constitution is passed, that policy's appended rows.
    """

    def __init__(self, mission: MissionSpec, length_tol: float = 0.10,
                 policy=None, provenance=None):
        self.mission = mission
        # WHAT THE SEARCH TOUCHED IS RECORDED (R0.2f — audit: three provenance
        # mechanisms existed and the optimizer wrote to none of them). None
        # keeps the un-recorded run identical to what it always was.
        self.provenance = provenance
        # GOVERNANCE REACHES THE SEARCH, NOT ONLY THE LADDER (BuildPlan 3 §2.2).
        # `policy` is an optional COMPILED constitution
        # (`navalai.policy.compile_policy` / `reference_policy`). It is
        # keyword-usable, defaults to None, and every line that touches it sits
        # behind `if policy is not None` — so an ungoverned run executes the
        # identical code it executed before governance existed, which is what
        # Gate V3.0(d) has to mean for the optimizer as well as for `evaluate`.
        #
        # A compiled policy supplies BOTH of the compiler's outputs here:
        #   (1) `box(category)` becomes xl/xu, so `LOA <= 12 m` is a BOUND the
        #       population is constructed inside. MEASURED on the reference SKU
        #       at category C (pop 24, 8 generations, seed 5): the ungoverned
        #       search drew 143 of 192 individuals above the 11.9 m ceiling and
        #       floated every one of them through L1 before `policy_legal`
        #       rejected it; the governed search drew 0. A bound checked only on
        #       the returned front is a rejection wearing a bound's name.
        #   (2) `constraint_names()` sizes and fills G, so the policy rows
        #       constrain NSGA-II exactly the way the ladder's own rows do —
        #       the same reason `CONSTRAINT_NAMES` is read here and not
        #       re-listed.
        self.policy = policy
        self.constraint_names = (tuple(CONSTRAINT_NAMES) if policy is None
                                 else tuple(policy.constraint_names()))
        # THE MISSION'S LENGTH IS A SEARCH BOUND, not decoration.
        # `lwl_hint_m` was parsed, range-clamped, prompted for and asserted in
        # two tests while being READ BY NOTHING. Measured end to end: a mission
        # saying "10 m" produced an 18.58 m hull (+86%), "5 m" produced 15.57 m
        # (+211%), and 0 of 40 Pareto members were within 10% of the stated
        # length. The cause is structural: Wh/NM falls monotonically with
        # length and nothing in the objective costs length, so the search runs
        # to the grammar's 20 m ceiling every time.
        xl, xu = grammar.LOW.copy(), grammar.HIGH.copy()
        if policy is not None:
            # The grammar's own bounds go IN and the governed ones come out.
            # `box` only ever moves an edge inward (max on the low edge, min on
            # the high), so this cannot widen the search — the ratchet law on
            # output (1).
            xl, xu = policy.box(mission.design_category,
                                low=xl, high=xu).as_bounds()
        # The widest box that survives governance. The hint is clamped against
        # THIS, not against the grammar, so the two compose by INTERSECTION:
        # whichever of hint and policy is tighter on an edge wins, and a hint
        # that would widen a governed edge cannot, because `min`/`max` below
        # start from the governed value.
        box_lo, box_hi = xl.copy(), xu.copy()
        hint = mission.lwl_hint_m
        if hint:
            i = grammar.NAMES.index("LWL")
            xl[i] = max(xl[i], hint * (1.0 - length_tol))
            xu[i] = min(xu[i], hint * (1.0 + length_tol))
            if xl[i] > xu[i]:
                # The hint's window does not meet the box at all — a 16 m hint
                # under an 11.9 m ceiling. There is no intersection to take, so
                # the hint is dropped and the BOX stands. Dropping the box
                # instead would let a mission string loosen governance, and
                # falling back to `grammar.LOW/HIGH` (which is what this line
                # did when the grammar was the only box) would do exactly that.
                xl[i], xu[i] = box_lo[i], box_hi[i]
        # Constraint values (and therefore the GM floor, the freeboard floor
        # and the bend limit) come from evaluate() — see CONSTRAINT_NAMES, plus
        # the compiled policy's appended rows when there is one.
        super().__init__(n_var=grammar.N_PARAMS, n_obj=3,
                         n_ieq_constr=len(self.constraint_names),
                         xl=xl, xu=xu)

    def _evaluate(self, X, out, *_args, **_kwargs):
        names = self.constraint_names
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(names)), INFEASIBLE_G)
        for i, x in enumerate(X):
            # Constraints come from the ladder itself, so a check added there
            # (trim and list, most recently) constrains the search immediately
            # instead of producing optima the ladder then rejects. With a
            # compiled policy `names` is CONSTRAINT_NAMES + that policy's rows,
            # in `Evaluation.g_names` order, so a governance row constrains
            # NSGA-II by the same mechanism and with no second code path.
            scored = _score(x, self.mission, self.policy, names,
                            provenance=self.provenance)
            if scored is not None:
                F[i], Gc[i] = scored
        out["F"] = F
        out["G"] = Gc


class LatentHullProblem(Problem):
    """Same objectives/constraints as HullProblem, explored in the 8-D genome
    (original plan Phase 4: 'the optimizer explores the latent space')."""

    def __init__(self, mission: MissionSpec, genome, z_range: float = 2.5,
                 policy=None, provenance=None):
        self.mission = mission
        self.genome = genome
        self.provenance = provenance
        # Output (2) only, and the asymmetry is the point rather than an
        # omission: the decision variables here are the 8-D genome, and the
        # parameter box is a box in GRAMMAR space. `genome.decode` is what
        # produces the parameters, so there is no bound on z that expresses
        # `LWL <= 11.9 m`. This is precisely the case the compiler's docstring
        # names — "a design can enter the ladder from a saved genome, a latent
        # decode or a hand-written array, none of which passed through the box"
        # — and it is why the policy emits a ROW as well as a bound. Here the
        # row is the whole of the enforcement, so it does the whole of the work.
        self.policy = policy
        self.constraint_names = (tuple(CONSTRAINT_NAMES) if policy is None
                                 else tuple(policy.constraint_names()))
        q = genome.W.shape[1]
        super().__init__(n_var=q, n_obj=3,
                         n_ieq_constr=len(self.constraint_names),
                         xl=-z_range * np.ones(q), xu=z_range * np.ones(q))

    def _evaluate(self, Z, out, *_args, **_kwargs):
        X = self.genome.decode(Z)              # gate-projected to feasibility
        names = self.constraint_names
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(names)), INFEASIBLE_G)
        for i, x in enumerate(X):
            scored = _score(x, self.mission, self.policy, names,
                            provenance=self.provenance)
            if scored is not None:
                F[i], Gc[i] = scored
        out["F"] = F
        out["G"] = Gc


@dataclass
class ParetoResult:
    X: np.ndarray
    F: np.ndarray          # (wh_per_nm, build_area_m2, |GM - band middle|)
    n_evals: int


def _front(res, n_var: int) -> tuple[np.ndarray, np.ndarray]:
    """(X, F) as float arrays — EMPTY when the run found nothing feasible.

    pymoo returns `res.X is None` when no individual satisfied every
    constraint, and `np.atleast_2d(None)` is an OBJECT array holding one None.
    That is a front of one design whose every parameter is None: it has a
    length, it indexes, and it reaches the caller looking like a result. It was
    reachable before governance and is reachable more often after it, because a
    compiled policy is exactly what makes the feasible set small enough to miss
    at a small budget — MEASURED on the reference SKU at category C, pop 16 /
    5 gens, seed 5. An empty front says "no feasible design" in a way a `for`
    loop can act on; the None row says it in a TypeError three call frames
    later, which is where this was found.

    Wherever a real front exists this is `np.atleast_2d` and nothing else, so
    an ungoverned run that found designs returns bit-identical arrays.
    """
    if res.X is None:
        return np.zeros((0, n_var)), np.zeros((0, 3))
    return np.atleast_2d(res.X), np.atleast_2d(res.F)


def pareto_front(mission: MissionSpec, pop: int = 40, gens: int = 30,
                 seed: int = 1, policy=None, provenance=None) -> ParetoResult:
    """`policy` is an optional compiled constitution; None is the ungoverned
    search, unchanged. `provenance` is an optional `db.Provenance`; every
    ladder evaluation the search makes is recorded to it (R0.2f). See
    `HullProblem.__init__`."""
    problem = HullProblem(mission, policy=policy, provenance=provenance)
    algo = NSGA2(pop_size=pop)
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    X, F = _front(res, problem.n_var)
    return ParetoResult(X, F, pop * gens)


def pareto_front_latent(mission: MissionSpec, genome, pop: int = 40,
                        gens: int = 30, seed: int = 1,
                        policy=None, provenance=None) -> ParetoResult:
    """NSGA-II in the 8-D genome; returns decoded (feasible) designs."""
    problem = LatentHullProblem(mission, genome, policy=policy,
                                provenance=provenance)
    algo = NSGA2(pop_size=pop)
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    Z, F = _front(res, problem.n_var)
    if len(Z) == 0:
        return ParetoResult(np.zeros((0, grammar.N_PARAMS)), F, pop * gens)
    return ParetoResult(genome.decode(Z), F, pop * gens)
