"""Gate R3: the ladder is a ladder — a kept design can be climbed, the badge it
carries names the solver that actually ran, and a tier we cannot compute here is
refused rather than faked.

The incident this whole file exists for: an AST import graph of the package
found that `navalai.seakeeping` was imported outside the tests by exactly ONE
caller — a print-only spot-check in `scripts/demo_mission.py` — and
`navalai.cfd` only by operator CLIs. `Evaluation.tier` read "L1" in 100% of
~2000 evaluations. Honesty rule 2, "any kept design re-validates up the ladder",
therefore had no implementation anywhere in the product.
"""

import pathlib
import re

import numpy as np
import pytest

from navalai import db
from navalai.evaluate import (TIER_ORDER, Evaluation, TierRefusal,
                              TierRequiresOperator, evaluate, revalidate,
                              tier_rank)
from navalai.mission import MissionSpec
from tests.test_phase0 import mid_params

_PKG = pathlib.Path(__file__).parents[1] / "navalai"


def test_l2_is_reachable_from_the_ladder_not_only_from_a_demo():
    """A source scan, because the defect was structural: the module existed,
    the tests exercised it, and no product code path could reach it. Import it
    from `evaluate` or the tier is decoration."""
    src = (_PKG / "evaluate.py").read_text()
    assert re.search(r"import\s+seakeeping", src), (
        "evaluate.py must be able to dispatch to L2; if this import moved, "
        "move this test with it — do not delete it")
    # and the dispatcher must be exported as a verb, not left as a private hook
    assert callable(revalidate)


def test_tier_rank_orders_the_ladder_and_distrusts_unknown_badges():
    assert [tier_rank(t) for t in TIER_ORDER] == [0, 1, 2, 3]
    # 'L1-INVALID' is what evaluate() badges a resistance number outside the
    # Michell envelope. It is NOT an L1 result and must never compare as one.
    assert tier_rank("L1-INVALID") < tier_rank("L0")
    assert tier_rank("nonsense") < 0


def test_revalidate_refuses_a_design_that_has_no_l1_state():
    """The ladder is climbed, not skipped: escalating an L0 failure would mean
    running a BEM on a hull the algebraic gate already rejected."""
    m = MissionSpec()
    bad = np.array(mid_params())
    bad[0] = 1.0                                   # LWL below the grammar floor
    ev = evaluate(bad, m)
    assert ev.tier == "L0" and not ev.ok
    with pytest.raises(TierRefusal) as e:
        revalidate(ev, m, "L2")
    assert "L1 state" in str(e.value)


def test_revalidate_never_demotes():
    """Monotone promotion is the invariant. `revalidate(..., 'L1')` on a design
    already at L1 (or higher) is a no-op, not a step back down the ladder."""
    m = MissionSpec()
    x = np.array(mid_params())
    ev = evaluate(x, m)
    for target in ("L0", "L1"):
        out = revalidate(ev, m, target)
        assert tier_rank(out.tier) >= tier_rank(ev.tier)
        assert out.tier == ev.tier
    with pytest.raises(ValueError):
        revalidate(ev, m, "L9")


def test_l3_refuses_in_process_and_names_the_operator_route():
    """L3 is a multi-hour supervised OpenFOAM campaign — on this hardware the
    KCS case is ~6 h on 10 ranks and is killed by thermal sleep, which is why
    `run_campaign.sh` exists. There is no truthful way to answer an in-process
    call with an L3 number, and the dishonest way (fall back to L1, badge it
    L3) is exactly what this refusal forecloses."""
    m = MissionSpec()
    ev = evaluate(np.array(mid_params()), m)
    with pytest.raises(TierRequiresOperator) as e:
        revalidate(ev, m, "L3")
    msg = str(e.value)
    assert "scripts/make_case.py" in msg          # the route, not just a "no"
    assert ev.tier == "L1", "a refused escalation must not mutate the input"


def test_evaluation_carries_its_own_genome():
    """A kept design used to be an Evaluation the caller had to keep paired
    with a loose parameter array by hand; there was nothing to re-validate."""
    x = np.array(mid_params())
    ev = evaluate(x, MissionSpec())
    assert ev.params is not None
    assert np.allclose(ev.params, x)
    with pytest.raises(TierRefusal):
        revalidate(Evaluation(True, "L1"), MissionSpec(), "L2")


def test_revalidate_promotes_to_l2_and_records_it(tmp_path):
    """The Gate R3 bar: a kept design's provenance shows an L2 row superseding
    its L1 row, and the L2 badge carries a MEASURED sigma.

    The sigma is the worst mesh-to-mesh change in heave added mass across the
    frequency set (seakeeping.py names mesh sensitivity as mandatory), not a
    declared fraction. MEASURED on the reference hull: 190 -> 378 panels moves
    A33 by 0.54%, and the whole escalation costs ~0.7 s — cheap enough that
    re-validating a kept design is routine rather than an event.
    """
    pytest.importorskip("capytaine")
    m = MissionSpec()
    x = np.array(mid_params())
    prov = db.Provenance(tmp_path / "p.sqlite3")

    ev1 = evaluate(x, m, provenance=prov)
    # THIS USED TO READ `ev1.tier == "L1" and ev1.ok`, AND THE `ok` HALF IS
    # STILL FALSE — recorded, not softened (honesty rule 6). WHICH constraint
    # holds it there changed on 2026-08-13, and both halves of the change are
    # information:
    #
    #   LCB, which used to be the single violation, now PASSES. Gap B8 added
    #   the +-3 %LWL band (`limits.LCB_BAND_PCT_LWL`) and the reference hull
    #   floated at -5.36 %LWL, out of band, because LCB was an emergent output
    #   of fifteen shape knobs. Plate P1 made `lcb` a GENE the sectional area
    #   curve is solved to deliver; the hull asks for -1.0 and floats at -1.68.
    #   See tests/test_constraints_honest.py, which carries the measurement.
    #
    #   BEND RADIUS now fails, at 0.954 m against the 1.68 m cold-bend limit
    #   for the rule-derived 21 mm bottom. **THE BAR IS NOT THE QUESTIONABLE
    #   PART — THE METRIC IS**, and it is recorded here because this is where
    #   it first bites. `Hull.min_bend_radius()` takes a central-difference
    #   curvature along the keel and chine, and the chine has a TANGENT BREAK
    #   at the max-area station (the sectional area curve's two branches meet
    #   there with different slopes, and so does the flare envelope). A central
    #   difference straddling a corner measures the corner divided by the step,
    #   so the number DIVERGES as the station count rises. MEASURED on the
    #   reference hull, stations 21 -> 641:
    #
    #       plate-P1/P2 kernel   1.777  0.954  0.515  0.277  0.148  0.078
    #       pre-rebuild kernel   4.184  2.239  1.147  0.578  0.289  0.145
    #
    #   Both halve with every doubling. The pre-rebuild hull ALSO fails the
    #   1.2 m limit from 81 stations up; it passed at the shipped 41 only
    #   because the sampling was coarse enough to blur the corner. So this is
    #   not a regression the rebuild introduced — it is a pre-existing
    #   ill-posed metric (docs/LESSONS.md defect class 1: a quantity that is a
    #   function of its sampling, scored against a bar in metres) that the
    #   rebuild's sharper knuckle pushed across the line at the configuration
    #   the product actually runs. It is REPORTED, not worked around: neither
    #   `min_bend_radius` nor `limits.min_bend_radius_m` is touched here.
    #
    # What this test is FOR is escalation, and escalation does not require
    # feasibility: an infeasible design that a user asks to re-validate must
    # still climb, or the ladder would only ever be run on hulls that need it
    # least. What the test does assert is that the L1 verdict SURVIVES the
    # promotion unchanged (`ev2.ok == ev1.ok` below).
    assert ev1.tier == "L1"
    assert len(ev1.violations) == 1 and "bend radius" in ev1.violations[0], \
        ev1.violations
    # RE-MEASURED 2026-08-14 (R2.1, solved trim equilibrium): at the
    # attitude the boat actually takes, LCB stands under LCG at
    # -0.81 %LWL (was -1.68 at the level float).
    assert ev1.hydro.lcb_pct_lwl == pytest.approx(-0.81, abs=0.05)
    assert ev1.g["lcb"] < 0.0
    ev2 = revalidate(ev1, m, "L2", provenance=prov)

    assert tier_rank(ev2.tier) > tier_rank(ev1.tier)
    assert ev2.tier == "L2"
    # the L1 findings survive the promotion; the badge is superseded, not the
    # evaluation
    assert ev2.ok == ev1.ok and ev2.gm_m == ev1.gm_m
    assert ev2.badges["heave_added_mass"][0] == "L2"
    assert ev2.badges["displacement"][0] == "L1"    # not re-badged by L2
    assert 0.0 < ev2.seakeeping["uncertainty_rel"] < 0.10
    assert ev2.badges["heave_added_mass"][1] > 0.0

    # physics limit (the same one Gate 2 anchors): a small boat follows a long
    # wave, so |RAO| -> 1 as omega -> 0
    assert ev2.seakeeping["rao_heave"][0] == pytest.approx(1.0, abs=0.15)
    assert all(a > 0 for a in ev2.seakeeping["added_mass_heave"])

    hid = db.hull_id(x)
    tiers = {row[0] for row in prov.results(hid)}
    assert tiers == {"L1", "L2"}
    l2 = prov.results(hid, "L2")
    assert l2, "no L2 provenance row — the escalation left no history"
    for _tier, solver, _q, value, unc, _meta in l2:
        assert solver == "capytaine"
        assert value is not None and unc is not None and unc >= 0.0


def test_a_genome_can_be_escalated_in_one_call(tmp_path):
    """Passing the genome runs L0->L1->L2 and records both rows, which is what
    makes "the L2 row supersedes its own L1 row" checkable in provenance."""
    pytest.importorskip("capytaine")
    m = MissionSpec()
    x = np.array(mid_params())
    prov = db.Provenance(tmp_path / "p.sqlite3")
    ev = revalidate(x, m, "L2", provenance=prov)
    assert ev.tier == "L2"
    rows = prov.results(db.hull_id(x))
    assert {r[0] for r in rows} == {"L1", "L2"}
