"""Gate 1b: NSGA-II produces a real Pareto front of feasible hulls."""

import pathlib

import pytest

import numpy as np

from navalai import grammar
from navalai.evaluate import evaluate, revalidate, tier_rank
from navalai.mission import MissionSpec
from navalai.optimize import pareto_front


def test_small_pareto_run_yields_feasible_diverse_front():
    m = MissionSpec(displacement_target_kg=6000, cruise_speed_kn=5)
    res = pareto_front(m, pop=24, gens=8, seed=3)
    assert len(res.X) >= 3, "front collapsed"
    # Every returned design must re-validate through the ladder (honesty rule 2).
    #
    # THIS ASSERTION USED TO READ `ev.tier == "L1"`, under this same comment
    # citing honesty rule 2 — so the one test in the repository that claimed to
    # enforce "any kept design re-validates UP the ladder" would have FAILED the
    # moment a kept design actually escalated. It pinned the ceiling it was
    # supposed to be raising, and it passed for the same reason the gap existed:
    # `Evaluation.tier` was "L1" in 100% of ~2000 evaluations because nothing in
    # the product could reach L2 at all.
    #
    # The invariant rule 2 actually asserts is MONOTONE PROMOTION: a
    # re-validated design's badge may move up the ladder and must never move
    # down.
    whs = []
    for x in res.X:
        ev = evaluate(x, m)
        assert ev.ok, ev.violations
        assert tier_rank(ev.tier) >= tier_rank("L1"), (
            f"a kept design came back at {ev.tier} — the ladder was not run")
        whs.append(ev.energy.wh_per_nm)
    # objective actually spans a range (front, not a point)
    assert max(whs) > min(whs) * 1.02
    # all in-bounds
    assert (res.X >= grammar.LOW - 1e-9).all() and (res.X <= grammar.HIGH + 1e-9).all()

    # And the escalated case, which the old assertion made unreachable: a kept
    # design taken up the ladder reports the HIGHER tier, and every L1 finding
    # it was kept for survives the promotion.
    pytest.importorskip("capytaine")
    kept = evaluate(res.X[0], m)
    up = revalidate(kept, m, "L2")
    assert tier_rank(up.tier) > tier_rank(kept.tier)
    assert up.tier == "L2" and up.ok == kept.ok
    assert up.g == kept.g


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
    # The ban is on RE-DECLARING a limit, not on consuming one. The original
    # check listed "gm_floor(" because optimize.py used to compute its own GM
    # bar; now it IMPORTS gm_floor from limits.py to build the GM band, which
    # is the behaviour this test exists to enforce. Banning the call as well as
    # the literal would forbid the fix.
    for hard in ("0.25 -", "80.0 * 0.015"):
        assert hard not in src, f"optimize.py re-declares a limit: {hard}"
    assert "from .limits import" in src, (
        "optimize.py must take its bars from limits.py, not restate them")


# ===========================================================================
# V3.0 — GOVERNANCE REACHES THE SEARCH, NOT ONLY THE LADDER
#
# The governance kernel compiles ONE constitution into TWO outputs (BuildPlan 3
# §2.2). Until this wiring landed the ladder consumed output (2) and NOTHING
# consumed output (1): `HullProblem` read the bare `CONSTRAINT_NAMES` and
# `grammar.LOW/HIGH`, so a compiled policy could be passed to `evaluate` all day
# and NSGA-II would still spend its budget generating hulls the constitution
# forbids. MEASURED below: 143 of 192 individuals over the 11.9 m ceiling.
# ===========================================================================

_GOV_MISSION = MissionSpec(displacement_target_kg=6000, cruise_speed_kn=5)


class _RecordingHullProblem:
    """Every X NSGA-II ever asks to be evaluated, captured.

    A mixin rather than a fixture because the DRAWS are the thing under test:
    checking the returned front would only prove the front complies, and a
    bound that is checked on the front is a REJECTION wearing a bound's name.
    pymoo evaluates every offspring it creates, so what arrives at `_evaluate`
    is the whole population history.
    """

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.seen = []

    def _evaluate(self, X, out, *a, **k):
        self.seen.append(np.array(X, dtype=float, copy=True))
        super()._evaluate(X, out, *a, **k)

    def drawn(self):
        return np.vstack(self.seen)


def _run(problem, pop, gens, seed):
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.optimize import minimize
    from pymoo.termination import get_termination
    return minimize(problem, NSGA2(pop_size=pop),
                    get_termination("n_gen", gens), seed=seed, verbose=False)


def test_the_policy_box_prunes_the_population_it_never_rejects_it():
    """BuildPlan 3 §2.2: "LOA <= 12 m becomes a bound, not a rejection".

    `tests/test_policy.py::test_the_length_ceiling_is_a_bound_and_not_a_rejection`
    proves that of the BOX. This proves it of the SEARCH, which is where the
    budget is actually spent, and it asserts on every individual NSGA-II
    generated rather than on the front it returned.

    MEASURED, pop 24 x 8 generations, seed 5, reference SKU at category C:

        ungoverned   143 of 192 individuals above the 11.9 m ceiling
        governed       0 of 192

    Those 143 were not free. Each one was floated through L1 hydrostatics and
    an energy model before `policy_legal` rejected it — the search paid full
    price for a design the constitution had already forbidden. That is the
    difference between a bound and a rejection, in evaluations.
    """
    from navalai.optimize import HullProblem
    from navalai.policy import reference_policy

    class Rec(_RecordingHullProblem, HullProblem):
        pass

    cp = reference_policy()
    i = grammar.NAMES.index("LWL")
    ceiling = cp.box(_GOV_MISSION.design_category).high[i]
    assert ceiling == pytest.approx(11.9)

    governed = Rec(_GOV_MISSION, policy=cp)
    _run(governed, 24, 8, 5)
    drawn = governed.drawn()
    over = int((drawn[:, i] > ceiling).sum())
    assert over == 0, (
        f"{over} of {len(drawn)} individuals were GENERATED above the "
        f"{ceiling} m ceiling — the box is being applied as a rejection")
    # and not by accident of a search that stayed short anyway
    assert drawn[:, i].max() > 0.9 * ceiling

    plain = Rec(_GOV_MISSION)
    _run(plain, 24, 8, 5)
    plain_drawn = plain.drawn()
    assert len(plain_drawn) == len(drawn)
    assert (plain_drawn[:, i] > ceiling).sum() > 0.25 * len(plain_drawn), (
        "the ungoverned search no longer wanders over the ceiling, so this "
        "test can no longer tell a bound from a rejection — pick a bound that "
        "still bites before trusting the governed half")


def test_the_policy_rows_constrain_the_front_and_exclude_a_ladder_ok_hull():
    """Output (2) reaching NSGA-II, and not decoratively.

    Two halves, and the second is the one that matters:

      1. every member of the governed front satisfies every policy row, and
      2. the UNGOVERNED front, at the same budget and seed, contains hulls that
         are fully L1-feasible and policy-INFEASIBLE — so the governed run is
         excluding real, ladder-passing designs rather than agreeing with a
         search that was already compliant.

    MEASURED, pop 24 x 10, seed 3: 10 of the 12 ungoverned front members are
    ladder-feasible and policy-infeasible.

    HALF 2's WITNESS NO LONGER COMES OUT OF THE SEARCH, and the reason is a
    measurement, not a preference. CI run 31611386179 (ubuntu-latest) failed
    here with "every witness is out of the box" while this Mac passed on the
    same commit, same seed, same budget. The count and the identity of the
    front members are not stable across the aarch64/Accelerate ↔
    x86-64/OpenBLAS boundary, and the reason they are not is structural: an
    NSGA-II generation ranks the population by DOMINATION, which is a discrete
    decision taken on continuous inputs, and ten of those in sequence turn a
    last-bit difference into a different trajectory. MEASURED over seeds 1-20
    at this budget, the in-box witness count is 0 on ELEVEN of them and
    exactly 1 on seed 3 — so the assertion was riding on a single design that
    a different libm is free to move.

    `_in_box_witnesses` below asserts the same claim off a well-conditioned
    computation instead: uniform draws inside the box (PCG64 is bit-identical
    everywhere) evaluated directly, no sort, no trajectory. See its docstring
    for the measurement.
    """
    from navalai.evaluate import evaluate as ev_
    from navalai.optimize import pareto_front
    from navalai.policy import reference_policy

    cp = reference_policy()
    m = _GOV_MISSION

    governed = pareto_front(m, pop=24, gens=10, seed=3, policy=cp)
    # KNOWN FRAGILE, kept because it is measured to hold at THIS seed on both
    # platforms and because lowering a bar that is passing is not a fix: over
    # seeds 1-20 the governed front is under 3 members on eight of them. If
    # this ever fails, it is the same trajectory chaos described above and not
    # a collapse of the governed search — re-measure across seeds before
    # touching it, and read what it actually guards (the loop below is vacuous
    # on an empty front).
    assert len(governed.X) >= 3, "governed front collapsed"
    for x in governed.X:
        ev = ev_(x, m, policy=cp)
        assert ev.g_names == cp.constraint_names()
        for row in cp.rows:
            assert ev.g[row] <= 0.0, f"{row} violated on a returned design"
        assert ev.ok, ev.violations

    def excluded(front):
        """Designs the ladder accepts and the constitution does not."""
        return [x for x in front if ev_(x, m).ok and not ev_(x, m, policy=cp).ok]

    plain = pareto_front(m, pop=24, gens=10, seed=3)
    witnesses = excluded(plain.X)
    assert witnesses, (
        "the ungoverned front contains no ladder-feasible, policy-infeasible "
        "design, so this budget cannot show that the rows bite")
    # The witness the box could NEVER have caught: INSIDE the parameter box and
    # rejected by a row. Without one of these the rows would only be agreeing
    # with the bound, and the wiring of output (2) would be untested. Taken
    # from a well-conditioned draw rather than from the front — see the
    # docstring and `_in_box_witnesses`.
    found = _in_box_witnesses(m, cp)
    assert found, (
        "no draw inside the box is ladder-feasible and policy-infeasible, so "
        "this test cannot tell the rows from the bound — it is the box being "
        "proven twice")
    for x, ev in found:
        assert cp.box(m.design_category).contains(x)
        assert ev_(x, m).ok, "the ladder must ACCEPT it, or it is not a witness"
        tripped = [r for r in cp.rows if ev.g[r] > 0.0]
        assert tripped == ["policy_energy"], (
            f"the in-box witness must fail a row the BOUND has no edge for; "
            f"this one trips {tripped}")
    # ...and not by a hair, or a last-bit difference would erase the claim the
    # way it erased the front-derived one.
    assert max(float(ev.g["policy_energy"]) for _, ev in found) > 0.1
    # The same property, counted on the governed front: none.
    assert excluded(governed.X) == []


def _in_box_witnesses(mission, cp, n_draws: int = 1500):
    """Designs INSIDE the policy box that the ladder accepts and a policy ROW
    refuses — the thing the parameter bound structurally cannot produce.

    WHY DRAWS AND NOT THE FRONT. This is the same claim the caller used to
    take off the ungoverned Pareto front, moved onto a computation that is a
    function of its inputs. Uniform draws from a PCG64 stream are bit-identical
    on every platform, `evaluate` is well-conditioned here (a 1-ULP move in a
    decision variable changes every objective and constraint by at most 2.6e-14
    relative), and no sort or trajectory sits between the draw and the verdict.
    An NSGA-II front has all three problems.

    MEASURED on this tree, 1500 draws from `default_rng(0)` inside
    `reference_policy().box`, reference SKU at category C: **9** witnesses, and
    ALL NINE trip `policy_energy` alone — the box has no edge for a solar
    fraction, which is exactly the row half of the kernel doing work the bound
    cannot do. Their `policy_energy` margins span +0.329 to +0.887, i.e. they
    are nowhere near the sign change, so the claim cannot be lost to a
    different libm. Cost: 1.9 s. The first witness is LWL 10.56 m.

    Returns [(x, evaluation_under_policy)]; the caller asserts the properties.
    """
    from navalai.evaluate import evaluate as ev_

    box = cp.box(mission.design_category)
    rng = np.random.default_rng(0)
    out = []
    for _ in range(n_draws):
        x = box.low + rng.random(len(box.low)) * (box.high - box.low)
        if not ev_(x, mission).ok:
            continue
        ev = ev_(x, mission, policy=cp)
        if not ev.ok:
            out.append((x, ev))
    return out


def test_with_no_policy_the_search_is_the_search_it_always_was():
    """THE COMPATIBILITY CLAUSE, and it is checked on the three things that
    could have changed rather than on a golden array: the bounds, the
    constraint columns, and the call into `evaluate`.

    A run of NSGA-II is a deterministic function of (xl, xu, F, G, seed), so
    equality on all four is equality on the front — which is why the fixed-seed
    front assertion at the end is a consequence and not the evidence.
    """
    from navalai.evaluate import CONSTRAINT_NAMES, evaluate
    from navalai.optimize import HullProblem, pareto_front
    from tests.test_phase0 import mid_params

    p = HullProblem(_GOV_MISSION)
    assert p.policy is None
    assert p.constraint_names == tuple(CONSTRAINT_NAMES)
    assert p.n_ieq_constr == len(CONSTRAINT_NAMES)
    assert (p.xl == grammar.LOW).all() and (p.xu == grammar.HIGH).all()

    # The evaluation the problem performs is the ungoverned one, bit for bit —
    # `policy=None` is `evaluate`'s own default and it takes the same branch.
    x = np.array(mid_params())
    a, b = evaluate(x, _GOV_MISSION), evaluate(x, _GOV_MISSION, policy=None)
    assert a.policy == {} and b.policy == {}
    assert a.g_names == b.g_names == CONSTRAINT_NAMES
    assert all(a.g[k] == b.g[k] for k in CONSTRAINT_NAMES)
    assert a.gm_m == b.gm_m and a.ok == b.ok

    out_default, out_none = {}, {}
    X = np.vstack([x, x * 0.99 + grammar.LOW * 0.01])
    HullProblem(_GOV_MISSION)._evaluate(X, out_default)
    HullProblem(_GOV_MISSION, policy=None)._evaluate(X, out_none)
    assert (out_default["F"] == out_none["F"]).all()
    assert (out_default["G"] == out_none["G"]).all()
    assert out_default["G"].shape == (2, len(CONSTRAINT_NAMES))

    r1 = pareto_front(_GOV_MISSION, pop=16, gens=4, seed=11)
    r2 = pareto_front(_GOV_MISSION, pop=16, gens=4, seed=11, policy=None)
    assert (r1.X == r2.X).all() and (r1.F == r2.F).all()


def test_the_length_hint_and_the_policy_box_compose_by_intersection():
    """Register row B1 (the mission's length is a search bound) and BuildPlan 3
    §2.2 (the policy box) both narrow LWL, and they must COMPOSE — the tighter
    of the two on each edge, never one replacing the other.

    MEASURED, reference SKU at category C (policy ceiling 11.9 m):

        hint      ungoverned        governed
        8 m       [7.20,  8.80]     [7.20,  8.80]   hint is tighter, hint wins
        11 m      [9.90, 12.10]     [9.90, 11.90]   split: hint low, policy high
        16 m      [14.40, 17.60]    [4.00, 11.90]   disjoint: the box stands
        none      [4.00, 20.00]     [4.00, 11.90]
    """
    from navalai.optimize import HullProblem
    from navalai.policy import reference_policy

    cp = reference_policy()
    i = grammar.NAMES.index("LWL")
    t = grammar.NAMES.index("T")

    def bounds(hint, policy):
        m = MissionSpec(displacement_target_kg=6000, cruise_speed_kn=5,
                        lwl_hint_m=hint)
        p = HullProblem(m, policy=policy)
        return float(p.xl[i]), float(p.xu[i]), float(p.xu[t])

    # the hint is tighter than the policy on BOTH edges — the hint wins, and
    # the policy still owns the draft ceiling it alone declares
    assert bounds(8.0, cp)[:2] == pytest.approx((7.2, 8.8))
    assert bounds(8.0, cp)[2] == pytest.approx(1.10)
    assert bounds(8.0, None)[:2] == pytest.approx((7.2, 8.8))

    # the hint is LOOSER than the policy on the high edge and tighter on the
    # low one — the intersection takes one edge from each
    assert bounds(11.0, None)[:2] == pytest.approx((9.9, 12.1))
    assert bounds(11.0, cp)[:2] == pytest.approx((9.9, 11.9))

    # a hint with no intersection at all: the BOX stands and the hint is
    # dropped. The other way round, a mission string would loosen governance.
    assert bounds(16.0, None)[:2] == pytest.approx((14.4, 17.6))
    lo, hi, _ = bounds(16.0, cp)
    assert (lo, hi) == pytest.approx((float(grammar.LOW[i]), 11.9))
    assert hi <= cp.box("C").high[i]

    assert bounds(None, cp)[:2] == pytest.approx((float(grammar.LOW[i]), 11.9))
    assert bounds(None, None)[:2] == pytest.approx(
        (float(grammar.LOW[i]), float(grammar.HIGH[i])))


def test_the_latent_search_gets_the_rows_because_it_cannot_get_the_box():
    """The genome decodes into grammar space, so no bound on z expresses
    `LWL <= 11.9 m`. That is the case the compiler's docstring names — a design
    entering the ladder from a latent decode never passed through the box — and
    it is why the kernel emits a row as well as a bound. Here the row is the
    whole of the enforcement."""
    from navalai.evaluate import CONSTRAINT_NAMES
    from navalai.optimize import LatentHullProblem
    from navalai.policy import reference_policy

    cp = reference_policy()

    class _G:
        W = np.zeros((grammar.N_PARAMS, 8))

    plain = LatentHullProblem(_GOV_MISSION, _G())
    gov = LatentHullProblem(_GOV_MISSION, _G(), policy=cp)
    assert plain.n_ieq_constr == len(CONSTRAINT_NAMES)
    assert gov.n_ieq_constr == len(cp.constraint_names())
    assert gov.constraint_names[:len(CONSTRAINT_NAMES)] == tuple(CONSTRAINT_NAMES)
    assert (plain.xl == gov.xl).all() and (plain.xu == gov.xu).all()


def test_a_search_that_found_nothing_feasible_returns_an_EMPTY_front():
    """pymoo sets `res.X = None` when no individual satisfied every
    constraint, and `np.atleast_2d(None)` is an OBJECT array holding one None —
    a front of one design whose every parameter is None. It has a length, it
    indexes, and it reaches the caller looking like a result; the failure
    surfaces as a TypeError several frames away, which is where this was found.

    MEASURED: the reference SKU at pop 16 x 5 generations, seed 5, returns
    exactly this — governance is what makes the feasible set small enough to
    miss at a small budget, so the wiring in this file is what makes the trap
    reachable in practice.
    """
    from navalai.optimize import _front

    class _Res:
        X = None
        F = None

    X, F = _front(_Res(), grammar.N_PARAMS)
    assert X.shape == (0, grammar.N_PARAMS) and F.shape == (0, 3)
    assert X.dtype == float and len(X) == 0
    for _ in X:                      # a caller's loop simply does not run
        raise AssertionError("empty front iterated")
