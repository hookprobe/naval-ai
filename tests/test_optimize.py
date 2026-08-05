"""Gate 1b: NSGA-II produces a real Pareto front of feasible hulls."""

import pathlib

import pytest

import numpy as np

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
from navalai.optimize import pareto_front


def test_small_pareto_run_yields_feasible_diverse_front():
    m = MissionSpec(displacement_target_kg=6000, cruise_speed_kn=5)
    res = pareto_front(m, pop=24, gens=8, seed=3)
    assert len(res.X) >= 3, "front collapsed"
    # every returned design must re-validate through the ladder (honesty rule 2)
    whs = []
    for x in res.X:
        ev = evaluate(x, m)
        assert ev.tier == "L1" and ev.ok, ev.violations
        whs.append(ev.energy.wh_per_nm)
    # objective actually spans a range (front, not a point)
    assert max(whs) > min(whs) * 1.02
    # all in-bounds
    assert (res.X >= grammar.LOW - 1e-9).all() and (res.X <= grammar.HIGH + 1e-9).all()


def test_optimizer_gm_floor_matches_the_rules_tier():
    """PLM platform law: a product may configure the kernel, never bypass a
    gate. The GM floor was hard-coded TWICE — 0.35 m in optimize.py and, for
    category C, 0.45 m in ISO 12217 — and the copies drifted. NSGA-II
    optimised to its own 0.35 bar and returned a GM 0.40 m hull: feasible by
    its constraint, and then FAILED R-GM at the rules gate. The optimizer was
    not "starving stability" — GM is both an objective and a constraint there.
    It hit exactly the bar it was given, and the bar was wrong.

    It no longer HAS its own bar: constraint values come from evaluate(), so
    the optimizer and the rules tier cannot hold different numbers. This test
    asserts that path end to end rather than an attribute that can be deleted.
    """
    import numpy as np

    from navalai.evaluate import CONSTRAINT_NAMES, evaluate
    from navalai.mission import MissionSpec, parse_mission
    from navalai.optimize import HullProblem, LatentHullProblem
    from navalai.rules.iso12217 import gm_floor
    from tests.test_phase0 import mid_params

    x = np.array(mid_params())
    for cat in ("A", "B", "C", "D"):
        m = parse_mission(f"a 10 metre solar boat, 3 tonnes, category {cat}")
        assert m.design_category == cat
        ev = evaluate(x, m)
        # g_gm = floor - GM, so the floor the optimizer is held to is recoverable
        assert ev.g["gm"] + ev.gm_m == pytest.approx(gm_floor(cat)), cat
    assert gm_floor("C") == 0.45

    # and the optimizer must consume exactly that vector, in that order
    p = HullProblem(MissionSpec(design_category="C"))
    assert p.n_ieq_constr == len(CONSTRAINT_NAMES)

    class _G:
        W = np.zeros((15, 8))

    assert LatentHullProblem(MissionSpec(design_category="C"),
                             _G()).n_ieq_constr == len(CONSTRAINT_NAMES)
    src = pathlib.Path(
        __file__).parents[1].joinpath("navalai/optimize.py").read_text()
    for hard in ("0.25 -", "80.0 * 0.015", "gm_floor("):
        assert hard not in src, f"optimize.py re-declares a limit: {hard}"
