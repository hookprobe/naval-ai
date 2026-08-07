"""Stage E gate: the surrogate predicts from the 8-D genome; NSGA-II explores
the latent space and matches the raw-parameter front at equal budget."""

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.latent import Genome
from navalai.mission import MissionSpec
from navalai.optimize import pareto_front, pareto_front_latent
from navalai.surrogate import GP


@pytest.fixture(scope="module")
def data():
    m = MissionSpec()
    X, y = sample_valid(200, m, seed=51)
    return m, X, y, Genome.fit(X)


TEST_DRAWS = (77, 78, 79, 80, 81, 82, 83, 84, 85, 86)


def test_latent_gp_predicts_from_8d_genome(data):
    """Original plan Phase 4: 'predict wave resistance ... purely from the
    8-D latent genome'. Gate: the 8-D genome costs surrogate accuracy but not
    all of it — median error under 0.40, and under 2.5x the full 15-parameter
    GP measured on the SAME hulls.

    THE MEDIAN OF 30 TEST HULLS IS NOT THE MEDIAN OF THE POPULATION, and this
    test used to assert the 0.40 bar against exactly one 30-hull draw
    (`sample_valid(30, m, seed=77)`). MEASURED 2026-08-07, one fixed genome
    (train seed 51), ten independent 30-hull draws through the same two GPs:

        test seed  77    78    79    80    81    82    83    84    85    86
        latent    .432  .416  .434  .343  .419  .324  .240  .275  .356  .283

    FOUR of the ten sit above 0.40. Seed 77 is one of them. The bar was a coin
    flip on the test draw and it had been landing heads.

    Gap E6 (max panel twist instead of mean) is what flipped this particular
    coin — swap `grammar.check` back to the pre-E6 implementation and seed 77
    reads 0.307 — but E6 did not degrade the latent GP. MEASURED over ten
    independent (train, test) seed PAIRS, pre-E6 against E6: median 0.343 vs
    0.361, and 3 of 10 pairs above 0.40 in BOTH. Pre-E6's worst pair (0.451)
    is worse than E6's worst (0.432). The 13.7% of design volume E6 removes
    does not show up here at all.

    So the fix is the STATISTIC, not the bar and not the model. The median is
    taken over 300 pooled test hulls (ten draws), which IS stable: across ten
    independent training draws the pooled figure reads

        min 0.3205   median 0.3345   max 0.3759   0 of 10 above 0.40

    against a full-parameter pooled median of 0.168-0.198, i.e. a ratio of
    1.78-1.98. The 0.40 bar does not move; the ratio bar TIGHTENS from 3.5x to
    2.5x, which the single-draw form could not have carried (its per-draw
    ratios reached 3.16). Pooling costs ~8 s.
    """
    m, X, y, genome = data
    gp_full = GP.fit(X, np.log(y), seed=1)
    gp_lat = GP.fit(genome.encode(X), np.log(y), seed=1)
    rel_full, rel_lat = [], []
    for seed in TEST_DRAWS:
        Xt, yt = sample_valid(30, m, seed=seed)
        rel_full += list(np.abs(np.exp(gp_full.predict(Xt)[0]) - yt) / yt)
        rel_lat += list(np.abs(np.exp(gp_lat.predict(genome.encode(Xt))[0])
                               - yt) / yt)
    assert len(rel_lat) == 30 * len(TEST_DRAWS)
    med_f, med_l = float(np.median(rel_full)), float(np.median(rel_lat))
    # MEASURED FINDING (recorded in ALIGNMENT.md): compressing 15 params to
    # the 8-D genome costs ~2x surrogate accuracy (pooled median 0.33 against
    # 0.17 full). The original plan's 8-D assumption has a real price.
    assert med_l < 0.40, f"latent GP pooled median rel err {med_l:.3f}"
    assert med_l < 2.5 * med_f, f"latent {med_l:.3f} vs full {med_f:.3f}"


def test_latent_front_feasible_and_competitive(data):
    m, _X, _y, genome = data
    res_lat = pareto_front_latent(m, genome, pop=20, gens=8, seed=5)
    res_raw = pareto_front(m, pop=20, gens=8, seed=5)
    assert len(res_lat.X) >= 3
    for x in res_lat.X:
        assert grammar.check(x).ok            # decoded designs all feasible
    best_lat = min(evaluate(x, m).energy.wh_per_nm for x in res_lat.X
                   if evaluate(x, m).energy)
    best_raw = min(evaluate(x, m).energy.wh_per_nm for x in res_raw.X
                   if evaluate(x, m).energy)
    # equal budget: latent search must land within 20% of raw-parameter search
    assert best_lat < 1.20 * best_raw, f"latent {best_lat:.0f} vs raw {best_raw:.0f}"


def test_latent_front_spans_designs(data):
    """A front, not one point — asserted over SEEDS, at a budget big enough for
    the property to exist.

    IT USED TO BE ONE SEED AT pop=16/gens=6, and MEASURED that budget produces
    a front of 3 to 8 members whose LWL spread is a lottery: across seeds
    (9, 5, 3, 11, 21, 42) the standard deviation reads
    0.072 / 2.334 / 0.352 / 0.355 / 2.733 / 3.294. Seed 9 is the one that lands
    at 0.072, and it was the seed the test used.

    IT WAS ALSO MEASURING THE WRONG THING. `Genome.decode`'s projection used to
    substitute a nearby TRAINING HULL for an infeasible latent point (gap I7),
    so part of the front's apparent diversity was the training set showing
    through the decoder rather than the search finding designs. With the
    projection now minimal and honest, the same six seeds at pop=16/gens=6 read
    0.072 / 2.334 / 0.352 / 0.355 / 2.733 / 3.294 against 0.311 / 0.321 /
    2.684 / 2.382 / 3.864 / 2.321 before — median 1.026 against 2.352. RECORDED
    per honesty rule 6: the honest decoder costs latent-front diversity at a
    tiny budget, and that is a real measured consequence, not a bug.

    So the budget moves to where the property is actually testable and the
    THRESHOLD does not move down: pop=24/gens=12 gives fronts of 13-24 members
    and a minimum spread of 0.810 over the same six seeds — 8x the original
    0.1 bar. Every seed is asserted, not one.
    """
    m, _X, _y, genome = data
    for seed in (9, 11, 21):
        res = pareto_front_latent(m, genome, pop=24, gens=12, seed=seed)
        lwls = res.X[:, 0]
        assert len(res.X) >= 10, f"seed {seed}: front of {len(res.X)}"
        assert lwls.std() > 0.4, (   # measured minimum 0.810 over six seeds
            f"seed {seed}: LWL spread {lwls.std():.3f} — a point, not a front")
