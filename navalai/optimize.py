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
from .evaluate import evaluate
from .geometry import Hull
from .mission import MissionSpec


class HullProblem(Problem):
    """3 objectives: min Wh/NM, min build panel area (m^2), max GM (as -GM).
    2 inequality constraints (g <= 0): freeboard floor, GM floor."""

    def __init__(self, mission: MissionSpec):
        self.mission = mission
        super().__init__(n_var=grammar.N_PARAMS, n_obj=3, n_ieq_constr=2,
                         xl=grammar.LOW, xu=grammar.HIGH)

    def _evaluate(self, X, out, *_args, **_kwargs):
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), 2), 1e3)
        for i, x in enumerate(X):
            ev = evaluate(x, self.mission)
            if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
                continue  # Fitness = inf pattern: cheap reject stays worst
            hull = Hull(x)
            build_area = hull.wetted_surface(float(hull.z_sheer.max())) + hull.deck_area()
            F[i] = (ev.energy.wh_per_nm, build_area, -ev.gm_m)
            Gc[i] = (0.25 - ev.hydro.freeboard_min, 0.35 - ev.gm_m)
        out["F"] = F
        out["G"] = Gc


class LatentHullProblem(Problem):
    """Same objectives/constraints as HullProblem, explored in the 8-D genome
    (original plan Phase 4: 'the optimizer explores the latent space')."""

    def __init__(self, mission: MissionSpec, genome, z_range: float = 2.5):
        self.mission = mission
        self.genome = genome
        q = genome.W.shape[1]
        super().__init__(n_var=q, n_obj=3, n_ieq_constr=2,
                         xl=-z_range * np.ones(q), xu=z_range * np.ones(q))

    def _evaluate(self, Z, out, *_args, **_kwargs):
        X = self.genome.decode(Z)              # gate-projected to feasibility
        F = np.full((len(X), 3), 1e9)
        Gc = np.full((len(X), 2), 1e3)
        for i, x in enumerate(X):
            ev = evaluate(x, self.mission)
            if ev.tier == "L0" or ev.hydro is None or ev.energy is None:
                continue
            hull = Hull(x)
            build_area = hull.wetted_surface(float(hull.z_sheer.max())) + hull.deck_area()
            F[i] = (ev.energy.wh_per_nm, build_area, -ev.gm_m)
            Gc[i] = (0.25 - ev.hydro.freeboard_min, 0.35 - ev.gm_m)
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
