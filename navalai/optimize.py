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
from .evaluate import CONSTRAINT_NAMES, evaluate
from .geometry import Hull
from .limits import GM_OVER_BEAM_MAX, gm_floor
from .mission import MissionSpec


class HullProblem(Problem):
    """3 objectives: min Wh/NM, min build panel area (m^2), GM toward a BAND.
    Inequality constraints (g <= 0) are the ladder's own — CONSTRAINT_NAMES."""

    def __init__(self, mission: MissionSpec, length_tol: float = 0.10):
        self.mission = mission
        # THE MISSION'S LENGTH IS A SEARCH BOUND, not decoration.
        # `lwl_hint_m` was parsed, range-clamped, prompted for and asserted in
        # two tests while being READ BY NOTHING. Measured end to end: a mission
        # saying "10 m" produced an 18.58 m hull (+86%), "5 m" produced 15.57 m
        # (+211%), and 0 of 40 Pareto members were within 10% of the stated
        # length. The cause is structural: Wh/NM falls monotonically with
        # length and nothing in the objective costs length, so the search runs
        # to the grammar's 20 m ceiling every time.
        xl, xu = grammar.LOW.copy(), grammar.HIGH.copy()
        hint = mission.lwl_hint_m
        if hint:
            i = grammar.NAMES.index("LWL")
            xl[i] = max(xl[i], hint * (1.0 - length_tol))
            xu[i] = min(xu[i], hint * (1.0 + length_tol))
            if xl[i] > xu[i]:                 # hint outside the grammar box
                xl[i], xu[i] = grammar.LOW[i], grammar.HIGH[i]
        # Constraint values (and therefore the GM floor, the freeboard floor
        # and the bend limit) come from evaluate() — see CONSTRAINT_NAMES.
        super().__init__(n_var=grammar.N_PARAMS, n_obj=3, n_ieq_constr=len(CONSTRAINT_NAMES),
                         xl=xl, xu=xu)

    def _evaluate(self, X, out, *_args, **_kwargs):
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(CONSTRAINT_NAMES)), 1e3)
        for i, x in enumerate(X):
            ev = evaluate(x, self.mission)
            if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
                continue  # Fitness = inf pattern: cheap reject stays worst
            hull = Hull(x)
            build_area = hull.wetted_surface(float(hull.z_sheer.max())) + hull.deck_area()
            # GM is a BAND, not a maximisation target. Maximising it is not
            # a naval-architecture goal — above ~0.20*B it is a hazard, and it
            # produced GM/B 0.82 with a 1.5 s roll period on a boat sold as a
            # dayboat. The objective is now distance from the middle of the
            # band, pulling the search toward a comfortable boat.
            b_wl = 2.0 * float(hull.y_chine.max())
            gm_mid = 0.5 * (gm_floor(self.mission.design_category)
                            + GM_OVER_BEAM_MAX * b_wl)
            F[i] = (ev.energy.wh_per_nm, build_area, abs(ev.gm_m - gm_mid))
            # Constraints come from the ladder itself, so a check added there
            # (trim and list, most recently) constrains the search immediately
            # instead of producing optima the ladder then rejects.
            Gc[i] = [ev.g[k] for k in CONSTRAINT_NAMES]
        out["F"] = F
        out["G"] = Gc


class LatentHullProblem(Problem):
    """Same objectives/constraints as HullProblem, explored in the 8-D genome
    (original plan Phase 4: 'the optimizer explores the latent space')."""

    def __init__(self, mission: MissionSpec, genome, z_range: float = 2.5):
        self.mission = mission
        self.genome = genome
        q = genome.W.shape[1]
        super().__init__(n_var=q, n_obj=3, n_ieq_constr=len(CONSTRAINT_NAMES),
                         xl=-z_range * np.ones(q), xu=z_range * np.ones(q))

    def _evaluate(self, Z, out, *_args, **_kwargs):
        X = self.genome.decode(Z)              # gate-projected to feasibility
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), len(CONSTRAINT_NAMES)), 1e3)
        for i, x in enumerate(X):
            ev = evaluate(x, self.mission)
            if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
                continue
            hull = Hull(x)
            build_area = hull.wetted_surface(float(hull.z_sheer.max())) + hull.deck_area()
            # GM is a BAND, not a maximisation target. Maximising it is not
            # a naval-architecture goal — above ~0.20*B it is a hazard, and it
            # produced GM/B 0.82 with a 1.5 s roll period on a boat sold as a
            # dayboat. The objective is now distance from the middle of the
            # band, pulling the search toward a comfortable boat.
            b_wl = 2.0 * float(hull.y_chine.max())
            gm_mid = 0.5 * (gm_floor(self.mission.design_category)
                            + GM_OVER_BEAM_MAX * b_wl)
            F[i] = (ev.energy.wh_per_nm, build_area, abs(ev.gm_m - gm_mid))
            # Constraints come from the ladder itself, so a check added there
            # (trim and list, most recently) constrains the search immediately
            # instead of producing optima the ladder then rejects.
            Gc[i] = [ev.g[k] for k in CONSTRAINT_NAMES]
        out["F"] = F
        out["G"] = Gc


@dataclass
class ParetoResult:
    X: np.ndarray
    F: np.ndarray          # (wh_per_nm, build_area, -gm)
    n_evals: int


def pareto_front(mission: MissionSpec, pop: int = 40, gens: int = 30,
                 seed: int = 1) -> ParetoResult:
    problem = HullProblem(mission)
    algo = NSGA2(pop_size=pop)
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    X = np.atleast_2d(res.X)
    F = np.atleast_2d(res.F)
    return ParetoResult(X, F, pop * gens)


def pareto_front_latent(mission: MissionSpec, genome, pop: int = 40,
                        gens: int = 30, seed: int = 1) -> ParetoResult:
    """NSGA-II in the 8-D genome; returns decoded (feasible) designs."""
    problem = LatentHullProblem(mission, genome)
    algo = NSGA2(pop_size=pop)
    res = minimize(problem, algo, get_termination("n_gen", gens), seed=seed,
                   verbose=False)
    Z = np.atleast_2d(res.X)
    return ParetoResult(genome.decode(Z), np.atleast_2d(res.F), pop * gens)
