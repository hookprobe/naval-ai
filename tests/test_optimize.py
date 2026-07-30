"""Gate 1b: NSGA-II produces a real Pareto front of feasible hulls."""

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
