"""Gate 3: co-kriging beats single-fidelity on Forrester; GP honest on our L1
physics; OOD queries escalate; batched EI infill works."""

import statistics
import warnings

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
from navalai.surrogate import (GP, CoKriging, InfillStarved, OODRefusal,
                               RhoDegenerate, batch_infill,
                               expected_improvement, forrester_hi,
                               forrester_lo)


def test_cokriging_beats_kriging_on_forrester():
    """Classic result (Forrester et al. 2007): 4 HF + 11 LF points -> co-kriging
    approximates the HF function far better than kriging on 4 HF alone."""
    X_hi = np.array([[0.0], [0.4], [0.6], [1.0]])
    X_lo = np.linspace(0, 1, 11)[:, None]
    ck = CoKriging.fit(X_lo, forrester_lo(X_lo[:, 0]), X_hi, forrester_hi(X_hi[:, 0]))
    gp = GP.fit(X_hi, forrester_hi(X_hi[:, 0]))
    Xt = np.linspace(0, 1, 200)[:, None]
    yt = forrester_hi(Xt[:, 0])
    rmse_ck = np.sqrt(np.mean((ck.predict(Xt)[0] - yt) ** 2))
    rmse_gp = np.sqrt(np.mean((gp.predict(Xt)[0] - yt) ** 2))
    assert rmse_ck < 0.5 * rmse_gp, f"co-kriging {rmse_ck:.3f} vs kriging {rmse_gp:.3f}"
    assert rmse_ck < 1.5   # function range ~ [-6, 16]: this is a tight fit


def test_gp_interpolates_and_uncertainty_grows_off_data():
    X = np.linspace(0, 1, 8)[:, None]
    y = np.sin(4 * X[:, 0])
    gp = GP.fit(X, y)
    m, s_on = gp.predict(X)
    assert np.allclose(m, y, atol=1e-3)          # interpolation
    _m2, s_off = gp.predict(np.array([[2.5]]))   # far outside [0, 1]
    assert s_off[0] > 10 * max(s_on.max(), 1e-6)  # honesty: sigma explodes off-data


# THE ERROR BAR'S QUERY DRAWS (gap D10). Five seeds, none of them 7: seed 7 is
# the TRAINING draw below, so `sample_valid(35, m, seed=7)` returns the first
# 35 training points and the median relative error is exactly 0.0000 — a
# self-test dressed as a held-out measurement.
L1_QUERY_SEEDS = (991, 992, 993, 994, 995)


@pytest.fixture(scope="module")
def l1_gp():
    """The Gate 3 production GP, fit ONCE.

    MEASURED: the fit is 6.12 s of the 6.89 s the old single-seed test took
    (sample_valid(250) 2.81 s + GP.fit 3.31 s) and each additional query draw
    is 0.39 s. Naively parametrizing the whole test over five seeds would cost
    34 s; behind this fixture it is 8.1 s.
    """
    from navalai.evaluate import sample_valid
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return GP.fit(X, np.log(y), seed=1), m


def _l1_draw(gp, m, seed: int):
    """(median relative error, 2-sigma coverage, n_kept) on one query draw."""
    from navalai.evaluate import sample_valid
    Xt, yt = sample_valid(35, m, seed=seed)
    keep = ~gp.is_ood(Xt, 0.5)
    pred, sigma = gp.predict(Xt[keep])
    rel = np.abs(np.exp(pred) - yt[keep]) / yt[keep]
    within = (np.abs(pred - np.log(yt[keep])) <= 2 * sigma).mean()
    return float(np.median(rel)), float(within), int(keep.sum())


@pytest.mark.parametrize("seed", L1_QUERY_SEEDS)
def test_surrogate_on_l1_physics(l1_gp, seed):
    """GP on log(Wh/NM) over 250 L1-valid hulls, on FIVE held-out draws.

    The clauses that hold on every seed are asserted per seed here; the error
    bar itself is an across-seed statistic and lives in the test below, because
    it is a property of the model and not of one draw.
    """
    gp, m = l1_gp
    med, within, kept = _l1_draw(gp, m, seed)
    assert kept >= 15, "OOD filter rejected almost everything"
    # The COVERAGE bar survives the seed change — MEASURED 0.818-0.968 across
    # the five, against 0.75 — so it stays a per-seed assertion.
    assert within >= 0.75, f"seed {seed}: only {within:.0%} within 2 sigma"
    # An absolute sanity floor that no honest seed comes near (worst 0.234), so
    # this cannot silently become the error bar.
    assert med < 0.35, f"seed {seed}: median rel err {med:.3f}"


def test_the_l1_error_bar_is_measured_across_seeds_and_meets_the_bar(l1_gp):
    """Gap D10: Gate 3's error bar sat on ONE query seed, and that seed did not
    agree with the model.

    RE-MEASURED TWICE ON 2026-08-13 — same training draw (seed 7, n=250), same
    fit (GP.fit(seed=1)), five held-out draws of 35. First after the geometry
    kernel went 15 -> 16 parameters, then after the Michell quadrature grid went
    161x28 -> 241x44:

        query seed   kept    median rel err                      within 2-sigma
                             15-par   16-par   16-par/241x44     (latest)
              991    26/35   0.1056   0.1940   0.1710             0.846
              992    28/35   0.1830   0.1523   0.1471             0.857
              993    28/35   0.2222   0.1693   0.1296             0.893
              994    29/35   0.1798   0.1238   0.0938             0.897
              995    24/35   0.2340   0.1055   0.1849             0.958

        across-seed median   0.1830   0.1523   0.1471
        spread               2.22x    1.84x    1.97x

    MECHANISM, first move: the rebuild dropped `p_bow`/`p_stern` and added
    `Cp`, `lcb` and `roundness`, so prismatic coefficient and LCB are sampled
    DIRECTLY instead of emerging from two plan-form exponents; the Wh/NM
    manifold is smoother in those coordinates. Second move: the coarse Michell
    grid was carrying up to 0.9% of quadrature error across the sectional-area
    tangent break, and removing it removed noise the GP had been fitting.

    THE DIRECTION OF THE D10 OUTLIER FLIPPED AND THE FINDING SURVIVED IT. 991
    was the seed the test pinned and it was the MINIMUM of the five; it is now
    near the top. What D10 is about is not which way the pinned seed leans — it
    is that a single query draw is not a property of the model, and that is
    still measured here: 0.0938 to 0.1849 across five honest draws.

    THE BAR IS NOT MOVED. 0.15 is what Gate 3 claims and it stands.

    *** THE BAR IS MET, AND THE GATE 3E ROW IS RETIRED (2026-08-18). ***

    The row's own clearing contract said "delete it the moment it is met — a
    GREEN gate still listed here is itself a failure", and the caution above
    ("met by less than the seed noise": 0.1471 at 2% margin, spread 1.97x)
    was answered by a second, better measurement before retiring: 0.1323
    across seeds on fortress001, ~12% under the bar, spread 1.45x —
    reproduced at the audit base f0ccc5f, so the improvement is the physics
    campaign's, not an artefact of the day's changes. Retirement history:
    watermark 0.183 (2026-08-12) -> 0.1471 (2026-08-13) -> 0.1323
    (2026-08-18) -> row deleted, gates.py references retired, this test
    re-pointed — the ONE change across three files its previous docstring
    demanded.

    THE DISCIPLINE SURVIVES THE ROW: the bar is still asserted on the MEDIAN
    OF FIVE honest query draws, never one chosen seed (gap D10), and if the
    bar is ever missed again this test fails with instructions to RE-OPEN
    the ledger row with a dated measurement — the same mechanism, both
    directions.
    """
    gp, m = l1_gp
    meds = [_l1_draw(gp, m, s)[0] for s in L1_QUERY_SEEDS]
    across = float(statistics.median(meds))

    # THE BAR, on the across-seed median (gap D10: never one chosen draw).
    assert across <= 0.15, (
        f"the across-seed median error bar is {across:.4f} against Gate 3's "
        f"0.15 bar — the bar is MISSED again. Do not touch this assert:  "
        f"RE-OPEN the Gate 3E ledger row (data/gate-ledger.json) with this "
        f"dated measurement and per-seed table, restore the RED row in "
        f"navalai/gates.py, and re-point this test back to asserting the "
        f"shortfall — the reverse of the 2026-08-18 retirement recorded in "
        f"the docstring.")
    # Local sanity band, both directions: 0.1323 measured; a value under
    # 0.05 is not "a great model", it is a broken measurement (the held-out
    # draw leaking into training, or the OOD filter eating the hard hulls).
    assert 0.05 < across <= 0.15, f"across-seed median {across:.4f}"

    # The spread is a RECEIPT, fenced BOTH directions so the docstring cannot
    # go stale. MEASURED: 2.22x -> 1.84x (rebuilt genome) -> 1.97x (Michell
    # grid) -> 1.45x (2026-08-18, fortress001, the physics-correction
    # campaign). Band covers the two post-campaign measurements (1.45, 1.97)
    # with the doctrine's failure modes still outside it: a degenerate
    # ensemble reads 1.00x and a one-draw pin reads 1.00x too.
    spread = max(meds) / min(meds)
    assert 1.05 < spread < 2.4, (
        f"seed spread moved to {spread:.2f}x — outside every measured value "
        f"(1.45-1.97 post-campaign); re-measure the table above rather than "
        f"widening this")


def test_calibration_is_measured_as_a_curve_with_sharpness_beside_it(l1_gp):
    """Gap I5: the whole calibration evidence for this module was ONE
    assertion, `within >= 0.75`, on a 2-sigma band whose nominal level is
    0.9545.

    One point on the coverage curve cannot separate "the band is too wide in
    the middle" from "the tails are wrong", and coverage alone is GAMEABLE:
    any model hits any coverage target by inflating sigma. This repository has
    already shipped one bar a degenerate answer passed (`gci <= 5.0` is true of
    -27%), so sharpness is measured beside coverage, always.

    RE-MEASURED 2026-08-13 on the Gate 3 GP, held-out draw seed 991, in
    log(Wh/NM) space, twice: once on the rebuilt 16-parameter genome and again
    after the Michell grid refinement (161x28 -> 241x44). The in-support count
    fell with each, 27 -> 29 -> 26:

        nominal            0.500   0.800   0.900   0.9545   0.990
        15-par/161x28 (27) 0.667   0.815   0.926   0.963    1.000
        16-par/161x28 (29) 0.414   0.759   0.897   0.897    0.966
        16-par/241x44 (26) 0.423   0.615   0.808   0.846    0.885

        calibration_error  0.0452 -> 0.0427 -> 0.1135
        sharpness          0.2462 -> 0.2180 -> 0.1832
        PIT KS             0.2268 -> 0.1332 -> 0.1663
        PIT mean           0.4048 -> 0.4635 -> 0.4572

    THE SIGN OF THE MISCALIBRATION FLIPPED AND THEN THE MAGNITUDE GREW. The
    model WAS under-confident at the middle of the curve (0.667 against a
    nominal 0.50); it is now OVER-confident across the WHOLE curve, and the
    2-sigma band that should hold 95.45% of the points holds 84.6%.

    MECHANISM, and it is the same one twice: the band keeps tightening faster
    than the error it has to contain. Sharpness has fallen 26% over the two
    changes (0.2462 -> 0.1832) while the residuals have not fallen as far, so
    calibration_error nearly TRIPLED (0.0427 -> 0.1135) in the same step that
    made the model more ACCURATE — the across-seed median error fell 0.1523 ->
    0.1471 (see the error-bar test above). Accuracy and honesty moved in
    opposite directions, which is exactly the pair this test exists to hold
    apart and exactly what a single coverage assertion cannot show.

    NO BAR FIRES ON THIS and none is invented here (see below), but it is the
    clearest open finding in this file: the Gate 3 GP's uncertainty is now
    materially optimistic and nothing in the ladder is gated on that yet.

    RE-MEASURED 2026-08-19, AND THE OPEN FINDING ABOVE IS RESOLVED — by the
    physics-correction campaign, not by any change to the GP. On the same
    fixture (train seed 7, fit seed 1, query seed 991) the OOD filter now
    keeps 30 of 35 (was 26) and:

        calibration_error  0.1135 -> 0.0156   (7.3x better)
        sharpness          0.1832 -> 0.1802   (essentially unmoved)
        PIT KS             0.1663 -> 0.2171
        coverage           0.500 / 0.800 / 0.867 / 0.933 / 0.967
                           at nominal 0.50 / 0.80 / 0.90 / 0.9545 / 0.99

    The curve is EXACT at the two lower levels and mildly over-confident
    only at the top three. The residuals fell (the 3E bar is now met,
    0.1323 across seeds — see that test's retirement record) while the
    band width stayed put, so the band caught up with the error it has to
    contain. Consequences pinned below: the x2.0 "broken model better
    calibrated than shipped" inversion NO LONGER HOLDS (doubled sigma now
    reads 0.1244 against the honest 0.0156 — 8x worse, the way it should
    be), and the directional claim narrows to the three upper levels.

    AND IT HAS A CONSEQUENCE THAT IS WORTH STATING ON ITS OWN, BECAUSE IT
    WEAKENS ANY TEST THAT USES `calibration_error` AS A DISCRIMINATOR. MEASURED
    below on the same 26 hulls: scaling this model's sigma by 2.0 — a
    deliberately over-hedged model, four times too vague in variance — scores
    `calibration_error` 0.0557 against the production model's 0.1135. THE
    BROKEN MODEL IS TWICE AS WELL CALIBRATED AS THE SHIPPED ONE. That is not a
    quirk of the metric; it is what over-confidence means, and widening a
    too-narrow band moves it towards calibration before it overshoots.

    So `calibration_error` cannot separate "honest" from "over-hedged" any more
    than it can see the SIGN of a miscalibration, and a poisoning or
    regression test that leans on it as its discriminator is weaker than it
    looks. Sharpness is what still separates them — it scales exactly with the
    width that bought the coverage — which is the whole reason this test
    measures the two together and refuses to report either alone.

    The single 2-sigma assertion could not have shown any of it: it read 0.963,
    then 0.897, then 0.846, and passes anything above 0.75 all three times.

    NO BAR IS ASSERTED on these numbers, and that is deliberate. A threshold
    interpolated from the 0.75 that is already known to be the wrong statistic
    would be a guess wearing a number (LESSONS defect class 3); the bar comes
    after someone has looked at what this measures. What IS asserted is that
    the diagnostics can tell a calibrated model from a miscalibrated one, in
    BOTH directions, which is the property a bar would later rest on.
    """
    from navalai.evaluate import sample_valid
    from navalai.surrogate import (COVERAGE_LEVELS, calibration,
                                   coverage_curve, pit_values, sharpness,
                                   _z_for)

    # The z table is DERIVED from the levels, not typed beside them.
    assert _z_for(0.9545) == pytest.approx(2.0, abs=1e-3)
    assert _z_for(0.6827) == pytest.approx(1.0, abs=1e-3)

    gp, m = l1_gp
    Xt, yt = sample_valid(35, m, seed=991)
    keep = ~gp.is_ood(Xt, 0.5)
    Xk, yk = Xt[keep], np.log(yt[keep])
    # 28..32, not == 30: the keep set rides the same BLAS-schedule lottery
    # as the fit it is derived from (measured: one boundary hull flips
    # between runs of identical code).
    assert 28 <= keep.sum() <= 32, f"kept {keep.sum()} of 35 — re-measure"
    n_kept = int(keep.sum())

    rep = calibration(gp, Xk, yk)
    assert rep["n"] == n_kept and rep["levels"] == COVERAGE_LEVELS
    curve = rep["coverage_curve"]
    # abs=0.05, not 0.02: one hull is 1/30 = 0.033 of coverage, and the
    # schedule lottery moves one boundary hull between runs (0.500 vs
    # 0.467 measured at nominal 0.50, identical code).
    for lv, want in ((0.50, 0.500), (0.80, 0.800), (0.90, 0.867),
                     (0.9545, 0.933), (0.99, 0.967)):
        assert curve[lv] == pytest.approx(want, abs=0.05), (
            f"coverage at nominal {lv} moved to {curve[lv]:.3f}; re-measure "
            f"the table above rather than widening this")
    # The RESOLVED-finding claim is the band, not the point: anything under
    # 0.05 is 2x+ better than the old 0.1135 finding; anything under 0.005
    # would be suspicious perfection on 30 hulls. Measured 0.0156.
    assert 0.005 < rep["calibration_error"] < 0.05
    assert rep["sharpness"] == pytest.approx(0.1802, rel=0.05)
    assert rep["pit_ks"] == pytest.approx(0.2171, abs=0.05)
    # RE-MEASURED 2026-08-19: exact at 0.50/0.80, over-confident only at
    # the top three levels — the residual direction that matters for a
    # consumer reading the 2-sigma band.
    assert all(curve[lv] < lv for lv in (0.90, 0.9545, 0.99)), (
        f"the model is no longer over-confident at the upper levels: {curve} "
        f"— re-measure the table above (both directions are findings)")

    # The curve and the standalone helpers cannot disagree about what the
    # model said — they are one computation, not two.
    assert coverage_curve(gp, Xk, yk) == curve
    assert sharpness(gp, Xk) == pytest.approx(rep["sharpness"], rel=1e-12)
    assert np.mean(pit_values(gp, Xk, yk)) == pytest.approx(rep["pit_mean"])

    # THE DIAGNOSTIC IS MADE TO FIRE, BOTH WAYS, on the same data. Neither
    # control is reachable by the old single 2-sigma assertion alone: the
    # inflated model reads 1.000 at 2 sigma and passes `within >= 0.75`
    # comfortably while being four times too vague.
    class _Scaled:
        def __init__(self, inner, f):
            self.inner, self.f = inner, f

        def predict(self, X):
            mu, sg = self.inner.predict(X)
            return mu, sg * self.f

    tight = calibration(_Scaled(gp, 0.25), Xk, yk)
    # THE RATIO BAR WAS 8x AND IS NOW 4x, AND THE CONTROL DID NOT GET WEAKER —
    # THE BASELINE GOT WORSE. Measured across the two changes:
    #
    #     quarter-width model calibration_error  0.5944 -> 0.5904   (-0.7%)
    #     honest model        calibration_error  0.0427 -> 0.1135   (+166%)
    #     ratio                                    13.9x ->   5.2x
    #
    # The numerator is essentially unmoved; the denominator nearly tripled
    # because the honest fit is itself now over-confident (see the docstring).
    # So the deliberately-broken model is refused just as hard in ABSOLUTE
    # terms, which is what the second assertion pins — a ratio alone would
    # have quietly rewarded a worsening baseline.
    assert tight["calibration_error"] > 4.0 * rep["calibration_error"]
    assert tight["calibration_error"] == pytest.approx(0.4956, abs=0.06), (
        "the miscalibrated control's absolute error moved; it is the anchor "
        "that keeps the ratio above from being satisfied by a bad baseline")
    # RE-MEASURED: the quarter-width model's 2-sigma coverage went
    # 0.481 -> 0.241 -> 0.346 -> 0.367 (2026-08-19, kept set now 30).
    assert tight["coverage_curve"][0.9545] == pytest.approx(0.367, abs=0.05)
    assert tight["sharpness"] < 0.3 * rep["sharpness"]

    # THE "TOO VAGUE" CONTROL NO LONGER SEPARATES ON calibration_error, AND
    # THAT IS THE SHARPEST FINDING IN THIS FILE. It used to read
    # `vague["calibration_error"] > 3 * rep["calibration_error"]`. MEASURED
    # 2026-08-13 on the post-grid GP, same 26 in-support hulls:
    #
    #     sigma scale   calibration_error   ratio to honest   sharpness   cov@0.9545
    #     x0.25              0.5904             5.20x           0.0458      0.346
    #     HONEST             0.1135             1.00x           0.1832      0.846
    #     x2.0               0.0557             0.49x           0.3665      0.962
    #     x3.0               0.1326             1.17x           0.5497      1.000
    #     x4.0               0.1480             1.30x           0.7329      1.000
    #
    # A MODEL WITH DELIBERATELY DOUBLED SIGMA IS TWICE AS WELL CALIBRATED AS
    # THE PRODUCTION ONE. The honest GP is over-confident at every level of the
    # curve, so widening it moves it TOWARDS calibration before it overshoots;
    # 4x only just gets back to 1.30x the honest error. The old assertion did
    # not break because the control got weaker — it broke because the baseline
    # it was a ratio against became the miscalibrated model.
    #
    # So the control is re-stated on the two quantities that DO see it, and the
    # finding is asserted instead of the broken ratio. All three can fail: fix
    # the over-confidence and the x2.0 clause breaks and demands a re-measure.
    vague = calibration(_Scaled(gp, 4.0), Xk, yk)
    assert vague["coverage_curve"][0.9545] == pytest.approx(1.0)
    assert vague["sharpness"] == pytest.approx(4.0 * rep["sharpness"], rel=1e-9), (
        "sharpness is what stops a coverage target being bought by widening "
        "the band, and it must scale exactly with the width that bought it")
    doubled = calibration(_Scaled(gp, 2.0), Xk, yk)
    # THE INVERSION RESOLVED (2026-08-19): this assert used to pin the
    # docstring's sharpest finding — a deliberately doubled sigma scoring
    # BETTER than the shipped model (0.0557 vs 0.1135), the signature of an
    # over-confident baseline. The physics campaign fixed the baseline
    # (0.0156), so widening now WORSENS calibration (0.1244, 8x) — the way
    # a healthy metric behaves. Asserted in the healthy direction, with the
    # old direction's message kept as the re-open instruction.
    assert doubled["calibration_error"] > max(
        2.0 * rep["calibration_error"], 0.10), (
        f"a 2x-too-wide model reads {doubled['calibration_error']:.4f} "
        f"against the production {rep['calibration_error']:.4f} — if the "
        f"wide model is again close to (or better than) the honest one, the "
        f"GP has gone back to over-confidence: re-measure the docstring's "
        f"table and re-open the finding, do not re-word this assert.")

    # AN UNMEASURABLE CALIBRATION POINT IS REFUSED, never scored as 0.5.
    class _NoBand:
        def predict(self, X):
            mu, sg = gp.predict(X)
            sg = np.asarray(sg, float).copy()
            sg[0] = 0.0
            return mu, sg

    with pytest.raises(ValueError, match="non-positive or non-finite"):
        calibration(_NoBand(), Xk, yk)


def test_ood_escalation_flag():
    X = grammar.sample(40, np.random.default_rng(3))
    y = X[:, 0] * 2.0 + X[:, 1]
    gp = GP.fit(X, y)
    far = X[0].copy()
    far[0] = grammar.HIGH[0] * 3  # way outside bounds and support
    assert gp.is_ood(far[None, :])[0]
    # ...but tripping on THIS point proves almost nothing, and for a long time
    # it was the entire OOD gate. A hull three times outside the grammar box is
    # rejected by `grammar.check` before any surrogate is consulted. The test
    # below is the one that has to hold.


def test_ood_rejection_separates_error_it_does_not_merely_flag():
    """Gate 3's bar is "OOD queries reliably escalate", and the only evidence
    that a criterion is a support test is that the queries it REJECTS are the
    ones it gets WRONG.

    MEASURED before this test existed, on the Gate 3 GP over 240 held-out
    queries: the sigma-threshold rejected 11 of 240 with a median relative
    error of 0.200 against 0.161 for the ones it kept — and on one of the four
    query seeds the rejected set was the MORE accurate one. It fired at 0.0% on
    in-box queries whose error reached 146%.

    Half of that was the criterion (fixed: `is_ood` now combines the sigma test
    with a distance-to-training-support test). The other half was the PROBE:
    training and query hulls were both drawn uniformly from the same grammar
    box, so the experiment contained no out-of-distribution query at all, and
    nothing can separate an empty set. This test restricts the training support
    the way a real surrogate is restricted — it is trained on wherever the
    optimiser has been — and then asks for the separation.

    MEASURED here: trained on the 100 hulls of a 250-hull sample with
    LWL <= 12 m, 200 fresh queries over the whole box give kept 0.261 against
    rejected 0.885 (3.4x), catching 79% of the queries that are outside the
    training support by construction; the same GP trained on the FULL box —
    where there is nothing to reject — raises a false alarm on only 5.5%.
    """
    from navalai.evaluate import sample_valid
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)
    Xq, yq = sample_valid(200, m, seed=901)

    inside = X[:, 0] <= 12.0                       # index 0 is LWL
    gp = GP.fit(X[inside], np.log(y[inside]), seed=1)
    pred, _s = gp.predict(Xq)
    rel = np.abs(np.exp(pred) - yq) / yq
    ood = gp.is_ood(Xq)
    assert 0.15 < ood.mean() < 0.85, (
        f"rejecting {ood.mean():.0%} is a broken dial, not a criterion")
    med_kept, med_rej = np.median(rel[~ood]), np.median(rel[ood])
    assert med_rej > 2.5 * med_kept, (
        f"NO SEPARATION: kept {med_kept:.3f} vs rejected {med_rej:.3f} — this "
        f"is the exact failure mode the sigma-only test had")
    out = Xq[:, 0] > 12.0
    assert (ood & out).sum() / out.sum() >= 0.65, "misses genuine OOD queries"

    # Control: on a training set that really does span the box there is no OOD
    # to find, and the criterion must not invent one.
    gp_full = GP.fit(X, np.log(y), seed=1)
    assert gp_full.is_ood(Xq).mean() < 0.15


def test_a_saturated_ard_lengthscale_is_reported_and_not_silently_absorbed():
    """Gap A6c: `GP.fit` pinned the ARD bound at log(10.0) and said nothing
    when the optimiser stopped there.

    RE-MEASURED 2026-08-13 on the 16-parameter genome AND AGAIN after the
    Michell grid refinement (`resistance.PRODUCTION_GRID` 161x28 -> 241x44), all
    three on `sample_valid(250, MissionSpec(), seed=7)` with `GP.fit(..., seed=1)`
    on log(Wh/NM). BEFORE is the 15-parameter measurement of 2026-08-12:

        training set        BEFORE                     16-par/161x28   16-par/241x44 (AFTER)
        full box            1 of 15  x_mb              4 of 16         3 of 16  D, beta_len,
                                                                                sheer_rise
        LWL <= 12 m         4 of 15  D, beta_bow,      5 of 16         5 of 16  D, lcb, beta_mid,
                                     p_bow, sheer_rise                          rocker, flare
        beta_mid >= 12 deg  3 of 15  p_stern, x_mb,    6 of 16         6 of 16  lcb, r_transom,
                                     beta_len                                   beta_bow, beta_len,
                                                                                flare, sheer_rise

    RE-MEASURED 2026-08-19 after the physics-correction campaign (trim
    equilibrium, R-TBM one-displacement, energy wiring — the Wh/NM surface
    itself moved, the GP knobs did not):

        full box            3 of 16  D, beta_len, x_mb
        LWL <= 12 m         7 of 16  D, beta_len, beta_mid, flare, lcb,
                                     sheer_rise, x_mb
        beta_mid >= 12 deg  3 of 16  D, beta_len, lcb

    x_mb SATURATES AGAIN on the full box and sheer_rise no longer does —
    the campaign moved which axes carry redundant information, exactly the
    kind of shift this table exists to record. The restricted fit still
    saturates harder (7 > 3), so the pair still demonstrates the claim.

    MECHANISM, first move: `p_bow`/`p_stern` are gone and `Cp`, `lcb` and
    `roundness` are new, so there is one more axis to saturate on and the axes
    themselves are different quantities. Cp and lcb now carry the displacement
    information the two plan-form exponents used to spread across D, x_mb and
    beta_len, so those axes have less left to explain and the optimiser
    flattens them.

    MECHANISM, second move: refining the Michell quadrature across the
    sectional-area tangent break removed a ~0.9% numerical error that varied
    with x_mb, and x_mb STOPPED saturating on the full box — the kernel found
    real signal along it once the noise that was masking the signal went. That
    is the one axis of the four that moved, and it moved in the direction the
    grid change predicts.

    Every one of those is the kernel declaring itself blind along an axis, and
    every one of them was invisible: `fit` returned, nothing was recorded, and
    the predictive sigma the OOD test is built on could not see a query that
    moved only along a saturated input. Defect class 1 with the roles swapped —
    the value was measured, by the optimiser, and then discarded.

    THE ASSERTIONS BELOW NAME AXES, NOT COLUMN INDICES, AND THAT IS THE OTHER
    HALF OF WHAT THIS RE-MEASUREMENT COST. The previous version read
    `gp.ls_at_bound == ((8, "upper"),)` beside `grammar.NAMES[8] == "x_mb"`;
    column 8 is now `beta_mid`, so a genome that changed LENGTH silently
    changed what the assertion was about. That is the same positional read of a
    reordered genome that turned up in the exporter, and a test is exactly the
    wrong place for it. `grammar.NAMES` is the single source and the indices
    are looked up through it.

    The bar is that the report is DERIVED from the fitted lengthscales and the
    same bounds `fit` searched in, so it cannot drift; the negative control is
    a fit that does NOT saturate, which must report nothing.
    """
    from navalai.evaluate import sample_valid
    from navalai.surrogate import ARD_LENGTHSCALE_BOUNDS, ARDSaturation

    lo, hi = ARD_LENGTHSCALE_BOUNDS
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)

    def saturated(gp):
        """The saturated axes BY NAME. Never by column index — see the
        docstring: column 8 meant `x_mb` under the 15-parameter genome and
        means `beta_mid` under this one."""
        return {grammar.NAMES[i] for i, _edge in gp.ls_at_bound}

    # THE GUARD IS MADE TO FIRE, on the production Gate 3 GP itself.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gp = GP.fit(X, np.log(y), seed=1)
    # THE TAIL AXES ARE SCHEDULE-UNSTABLE, MEASURED (2026-08-19): THREE
    # runs of THIS code on this box gave {D, beta_len, x_mb}, {D, beta_len,
    # sheer_rise} and {D, beta_len, sheer_rise, x_mb} — the GP optimum
    # shifts with BLAS thread scheduling and both marginal axes ride the
    # lottery, together or separately. Pinning an exact set is pinning the
    # lottery (the NSGA-II trajectory-pin class this campaign already
    # re-based). The stable core across every observed run: D and beta_len
    # ALWAYS saturate, the extras are only ever drawn from {x_mb,
    # sheer_rise}, and the count stays 3-4 of 16. threadpoolctl is not in
    # the environment, so the fit cannot be made deterministic without
    # changing what it computes.
    sat = saturated(gp)
    assert {"D", "beta_len"} <= sat and 3 <= len(sat) <= 4, (
        f"the stable saturation core moved: {sorted(sat)} — re-measure the "
        f"table in this docstring rather than loosening the assertion")
    assert sat - {"D", "beta_len"} <= {"x_mb", "sheer_rise"}, (
        f"a NEW marginal axis appeared: {sorted(sat)} — outside every "
        f"observed outcome; re-measure the table")
    assert all(e == "upper" for _i, e in gp.ls_at_bound)
    assert gp.ls[grammar.NAMES.index("D")] == pytest.approx(hi, rel=1e-9)
    assert any(issubclass(w.category, ARDSaturation) for w in caught), (
        "the fit saturated and nobody was told")
    rep = gp.saturation_report()
    # The report speaks in INDICES, not in names it does not have — it is a
    # property of the kernel, which has never been told what its columns mean.
    # Checked on a multi-character name: `D` and `T` are single letters and a
    # substring test on them says nothing about anything.
    assert "beta_len" not in rep and not any(a in rep for a in sat - {"D"})
    for i, _e in gp.ls_at_bound:
        assert f"input {i}" in rep, "the report must name every saturated axis"
    assert "blind" in rep
    # THE REPORT COUNTS THE DIMENSIONS THE GP ACTUALLY FITTED. Constant
    # columns are dropped before fitting (see `GP.fit`), so the denominator is
    # the ACTIVE width, not the genome's. Asserting `N_PARAMS` here would be
    # asserting that the GP wastes an ARD lengthscale on a column that never
    # varied.
    _fitted = int(gp.active.sum()) if gp.active is not None else grammar.N_PARAMS
    assert f"{len(gp.ls_at_bound)} of {_fitted}" in rep

    # The restricted fit saturates HARDER, and the report tracks it rather than
    # carrying a number written down once.
    inside = X[:, grammar.NAMES.index("LWL")] <= 12.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ARDSaturation)
        gp_r = GP.fit(X[inside], np.log(y[inside]), seed=1)
    # Same lottery, wider: the restricted fit read 5 axes on 2026-08-13 and
    # 7 on 2026-08-19 under different scheduling. The CLAIM is that
    # restriction saturates HARDER (asserted below) and that the report
    # tracks whatever the fit did — not a particular axis set.
    assert "D" in saturated(gp_r)
    assert all(e == "upper" for _i, e in gp_r.ls_at_bound)
    _fitted_r = (int(gp_r.active.sum()) if gp_r.active is not None
                 else grammar.N_PARAMS)
    assert (f"{len(gp_r.ls_at_bound)} of {_fitted_r}"
            in gp_r.saturation_report())
    assert len(gp_r.ls_at_bound) > len(gp.ls_at_bound), (
        "the restricted fit no longer saturates harder than the full-box one, "
        "so this pair has stopped demonstrating anything")

    # NEGATIVE CONTROL: an interior fit reports NOTHING and warns about
    # nothing. Without this the guard would be a constant.
    with warnings.catch_warnings(record=True) as quiet:
        warnings.simplefilter("always")
        xs = np.linspace(0.0, 1.0, 8)[:, None]
        gp_ok = GP.fit(xs, np.sin(4.0 * xs[:, 0]))
    assert gp_ok.ls_at_bound == ()
    assert gp_ok.saturation_report() == ""
    assert not [w for w in quiet if issubclass(w.category, ARDSaturation)]
    assert lo < gp_ok.ls[0] < hi


def test_support_distance_catches_what_sigma_alone_misses():
    """The distance term earns its place on an axis the KERNEL has decided to
    ignore. ARD lengthscales saturate — MEASURED on this very fit, six of the
    sixteen sit exactly on the optimiser's upper bound (10.0) — and sigma is
    computed through those same lengthscales, so it is blind there. A support
    test that also divided by them would inherit the blindness, which is why
    `_nn_distance` is unweighted.

    THIS TEST READ `X[:, 4]` AND CALLED IT `beta_mid`. Column 4 is `Cp` under
    the rebuilt genome, whose whole range is 0.525-0.71, so `X[:, 4] >= 12.0`
    selected ZERO training rows and the failure arrived as "zero-size array to
    reduction operation minimum" from inside `GP.fit` — a genome-shaped defect
    surfacing as a numpy error three frames away. The axis is now looked up
    through `grammar.NAMES`, which is the single source.

    RE-MEASURED 2026-08-13, training restricted to beta_mid >= 12 deg (109 of
    250 rows), 200 queries of which 117 are outside the restriction. BEFORE is
    the 15-parameter measurement:

        BEFORE  sigma only        58/200 rejected, kept 0.200, rej 0.354, recall 0.47
                sigma + distance  82/200 rejected, kept 0.180, rej 0.354, recall 0.63
        AFTER   sigma only        78/200 rejected, kept 0.171, rej 0.254, recall 0.67
                sigma + distance  88/200 rejected, kept 0.166, rej 0.254, recall 0.72

    THE MARGIN COLLAPSED FROM +0.16 RECALL TO +0.05, AND THE REASON IS THAT THE
    SIGMA HALF GOT BETTER, NOT THAT THE DISTANCE HALF GOT WORSE. sigma-only
    recall went 0.47 -> 0.67, so there are only 39 missed rows left for the
    distance term to find where there were 62, and a +0.10 improvement on a
    0.67 base is a third of the remaining headroom.

    THE BAR IS +0.10 AND IT STAYS AT +0.10. THIS ASSERTION WAS BRIEFLY LOWERED
    TO `approx(0.051, abs=0.03)` ON 2026-08-13 AND THAT WAS WRONG — it is the
    clearing condition of gap register row A6b, so lowering it does not record
    a smaller improvement, it silently CLOSES A6b on a bar the code does not
    meet. Honesty rule 6: never soften a failing threshold to make it pass, a
    failing gate is information. The measurement is kept in this docstring and
    A6b stays OPEN with +0.0513 recorded against its +0.10 condition. If the
    right answer is that +0.10 was never the right condition, that is a
    re-verdict of the REGISTER ROW, argued on its own terms and dated — not a
    number quietly edited in the fence that enforces it.

    An independent read-only audit on 2026-08-13 reached the same conclusion
    from the other side, and found something worse in the process: the
    reconcile predicate for A6b matches this test's ASSERTION TEXT, never an
    executed measurement, so at HEAD — where `X[:, 4]` selects zero rows and
    `GP.fit` dies — it scored A6b CLOSED on a test that CANNOT RUN. The
    positional-genome defect had landed inside the fence rather than the code.
    The `grammar.NAMES` lookup below is the fix for that half and it stays.

    The guard still FIRES, which is the separate question from whether the bar
    is met: deleting `_nn_distance` from `is_ood` makes both criteria identical
    and the delta exactly 0.000, which the `r_new > r_old` assertion refuses.
    Measured at the LWL <= 12 m and LWL <= 10 m restrictions the delta is 0.000
    in both, with sigma-only recall already at 0.96 and 0.99 — those probes
    have no headroom left at all and are not usable as evidence either way.
    """
    from navalai.evaluate import sample_valid
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)
    Xq, yq = sample_valid(200, m, seed=901)

    i_beta = grammar.NAMES.index("beta_mid")
    inside = X[:, i_beta] >= 12.0
    assert inside.sum() >= 20, (
        f"only {int(inside.sum())} training rows survive the beta_mid "
        f"restriction; this probe needs a fit, not an empty matrix")
    gp = GP.fit(X[inside], np.log(y[inside]), seed=1)
    pred, sig = gp.predict(Xq)
    rel = np.abs(np.exp(pred) - yq) / yq
    out = Xq[:, i_beta] < 12.0

    sigma_only = sig > 0.6 * np.sqrt(gp.var)
    both = gp.is_ood(Xq)
    r_old = (sigma_only & out).sum() / out.sum()
    r_new = (both & out).sum() / out.sum()
    assert r_new > r_old, (
        f"the distance term adds nothing: recall {r_old:.2f} -> {r_new:.2f}")
    # Gap register A6b's clearing condition. RESTORED after being briefly
    # lowered to approx(0.051, abs=0.03) — see the docstring. This is EXPECTED
    # TO FAIL at +0.0513, and that failure is the honest state of A6b, not a
    # broken test. Do not widen it; either close the gap or re-verdict the row.
    assert r_new >= r_old + 0.10, (
        f"support-distance recall gain is {r_new - r_old:+.4f} "
        f"({r_old:.4f} -> {r_new:.4f}) against gap A6b's +0.10 clearing "
        f"condition. A6b is OPEN. The sigma half improved (0.47 -> 0.67), so "
        f"the headroom shrank — that is an argument for RE-VERDICTING A6b on "
        f"the register with a dated measurement, and it is NOT a licence to "
        f"lower this number, which is the only thing enforcing the row.")
    # and it must not buy that recall by keeping worse hulls
    assert np.median(rel[~both]) <= np.median(rel[~sigma_only]) + 1e-9


def test_predict_or_escalate_never_badges_an_unsupported_query():
    """`is_ood()` had TWO call sites in the whole repository and BOTH were in
    tests. It flagged; nothing escalated and nothing refused, so Gate 3's
    "OOD queries reliably escalate to L2/L3" had no implementation at all.
    """
    X = np.linspace(0.0, 1.0, 12)[:, None]
    gp = GP.fit(X, forrester_hi(X[:, 0]))

    v, tier, s = gp.predict_or_escalate(np.array([0.47]))
    assert tier == "S1" and np.isfinite(v) and s > 0.0

    with pytest.raises(OODRefusal) as e:
        gp.predict_or_escalate(np.array([4.0]))
    assert e.value.distance > e.value.threshold      # says WHY, not just no

    calls = []

    def truth(x):
        calls.append(float(x[0]))
        return float(forrester_hi(x)[0]), 0.0

    v, tier, s = gp.predict_or_escalate(np.array([4.0]), escalate_fn=truth)
    # the badge names the solver that actually produced the number
    assert tier == "L1" and calls == [4.0]
    assert v == pytest.approx(float(forrester_hi(np.array([4.0]))[0]))

    # vector form: supported rows keep the surrogate badge, unsupported rows do
    # not, and no row comes back with a badge nothing computed
    vals, tiers, _sg = gp.predict_or_escalate(
        np.array([[0.47], [4.0]]), escalate_fn=truth)
    assert list(tiers) == ["S1", "L1"]


def test_cokriging_ood_consults_the_low_fidelity_gp():
    """`CoKriging.is_ood` returned `self.gp_delta.is_ood(X)` — it never asked
    the low-fidelity GP, whose mean is multiplied by rho into every prediction
    the model makes.

    DEMONSTRATED here: low-fidelity data confined to x in [0, 0.5],
    high-fidelity spanning [0, 1]. At x = 0.7, 0.8 and 0.9 the rho-carrying
    term is extrapolating (`gp_lo.is_ood` all True) while the delta-GP has
    neighbours (`gp_delta.is_ood` all False), so the old code answered "in
    support" for a prediction half of which was a guess.

    RECORDED (honesty rule 6): this fixture now also trips the `RhoDegenerate`
    identifiability warning, and that is CORRECT, not incidental. `forrester_lo`
    restricted to [0, 0.5] is nearly flat there, so `m_lo` over the HF points is
    almost constant, LF/HF correlation is -0.236, and rho beats rho=0 by 0.52
    nats. rho genuinely is not identified from this data; the fixture is built
    to strand the LF GP and it succeeds at that in both senses. The warning is
    asserted here so it cannot go quiet without a test noticing.
    """
    X_lo = np.linspace(0.0, 0.5, 11)[:, None]
    X_hi = np.linspace(0.0, 1.0, 11)[:, None]
    with pytest.warns(RhoDegenerate, match="NOT IDENTIFIED"):
        ck = CoKriging.fit(X_lo, forrester_lo(X_lo[:, 0]),
                           X_hi, forrester_hi(X_hi[:, 0]))
    probes = np.array([[0.7], [0.8], [0.9]])
    assert ck.gp_lo.is_ood(probes).all()
    assert not ck.gp_delta.is_ood(probes).any(), (
        "the trap this test encodes has moved; re-derive it before relaxing")
    assert ck.is_ood(probes).all()
    with pytest.raises(OODRefusal):
        ck.predict_or_escalate(probes[0])


def test_batched_ei_infill_targets_minimum():
    X = np.array([[0.0], [0.25], [0.5], [0.75], [1.0]])
    gp = GP.fit(X, forrester_hi(X[:, 0]))
    cand = np.linspace(0, 1, 101)[:, None]
    idx = batch_infill(gp, cand, float(forrester_hi(X[:, 0]).min()), k=3)
    assert len(idx) == 3
    picks = cand[idx, 0]
    assert np.min(np.abs(picks[:, None] - picks[None, :])
                  + np.eye(3)) > 0.03          # spread, not clustered
    ei = expected_improvement(gp, cand, float(forrester_hi(X[:, 0]).min()))
    assert ei[idx[0]] == pytest.approx(ei.max())


# ---------------------------------------------------------------------------
# I2 — rho was selected by the WRONG criterion
# ---------------------------------------------------------------------------

def _rho_case(n_hi: int, lf_lo: float = 0.0, lf_hi: float = 1.0, n_lo: int = 21):
    X_lo = np.linspace(lf_lo, lf_hi, n_lo)[:, None]
    X_hi = np.linspace(0.0, 1.0, n_hi)[:, None]
    return X_lo, forrester_lo(X_lo[:, 0]), X_hi, forrester_hi(X_hi[:, 0])


def test_rho_recovers_a_known_ar1_coefficient_and_does_not_drift_with_data():
    """`CoKriging.fit` scanned rho and kept the one minimising the delta-GP's
    ABSOLUTE leave-one-out RMSE, under a comment claiming that was "the KOH MLE
    spirit". LOO-RMSE carries the units of delta, so it is minimised by
    whichever rho makes the residual SMALL — a residual-magnitude minimiser,
    not an estimator, and it behaved like one.

    `forrester_lo` is an EXACT AR(1) partner of `forrester_hi` with
    rho_true = 2.0 (`lo = 0.5*hi + 10(x-0.5) - 5`), so the right answer is known
    to the last digit. MEASURED, |rho_hat - 2.0|:

        n_hi    old (LOO-RMSE)    new (joint KOH log-likelihood)
           6        0.0663              0.0045
           8        0.0401              0.0004
          10        0.0018              0.0001
          12        0.0227              0.0003
          15        0.0491              0.0001
          20        0.0790              0.0001
          25        0.0991              0.0013

    The old column is non-monotone and then walks steadily AWAY from the truth
    as data is added — the one thing an estimator may never do. That is the
    property this test pins: not just accuracy at one n, but that MORE DATA
    DOES NOT MAKE IT WORSE. The old criterion fails both arms.
    """
    errs = {}
    for n_hi in (6, 10, 15, 25):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RhoDegenerate)  # must not warn here
            ck = CoKriging.fit(*_rho_case(n_hi))
        errs[n_hi] = abs(ck.rho - 2.0)
        assert ck.rho_warning == ""
        assert ck.rho_evidence > 5.0, (
            f"n_hi={n_hi}: an exact AR(1) partner must be worth many nats "
            f"over rho=0, got {ck.rho_evidence:.2f}")
    assert max(errs.values()) < 0.02, errs
    assert errs[25] <= errs[6] + 1e-9, (
        f"recovery DEGRADES with data: {errs} — this is the old criterion's "
        f"signature (0.0663 at n=6 walking to 0.0991 at n=25)")


def test_rho_is_scale_free():
    """A coefficient in `f_hi = rho*f_lo + delta` is dimensionless: multiply
    both fidelities by 1000 and rho must not move. A criterion built on the
    absolute size of the residual has no reason to obey that; the likelihood
    does, because the process variance is profiled."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RhoDegenerate)
        X_lo, y_lo, X_hi, y_hi = _rho_case(12)
        a = CoKriging.fit(X_lo, y_lo, X_hi, y_hi).rho
        b = CoKriging.fit(X_lo, 1000 * y_lo, X_hi, 1000 * y_hi).rho
    assert abs(a - b) < 1e-3, f"rho moved {a:.4f} -> {b:.4f} under a pure rescale"


def test_rho_does_not_collapse_when_the_lf_model_is_confined_but_informative():
    """THE CASE THE REGISTER FILED: broad high fidelity, narrow low fidelity —
    which is the situation every real campaign is in, because the cheap model
    is run where the expensive one has not been.

    MEASURED with the old criterion, LF = `forrester_lo` on a sub-interval and
    HF spanning [0, 1]:

        LF span    n_hi    old rho
        [0, 0.3]     12    -0.6422
        [0, 0.4]     12    -0.7209
        [0, 0.35]    16    -0.4281
        [0.3, 1.0]   20    +2.6574 (and the register's own probe hit  0.0000)

    A negative rho against a positively-correlated partner means the fit is
    SUBTRACTING the cheap model, and rho = 0 discards it outright — in both
    cases while still calling itself co-kriging and emitting nothing.

    Here the LF data is confined to [0.3, 1.0] but genuinely informative
    (LF/HF correlation +0.857). MEASURED after the fix: rho = 2.18 against a
    truth of 2.0, worth 8.36 nats over rho = 0, no warning, and the co-kriging
    RMSE beats single-fidelity kriging on the same HF points (0.0014 vs
    0.0017) — which is the product claim, not just the coefficient.
    """
    X_lo, y_lo, X_hi, y_hi = _rho_case(20, lf_lo=0.3, lf_hi=1.0, n_lo=9)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RhoDegenerate)
        ck = CoKriging.fit(X_lo, y_lo, X_hi, y_hi)
    assert ck.lf_hf_corr > 0.5
    assert abs(ck.rho) > 0.5, f"rho collapsed to {ck.rho:.4f}"
    assert ck.rho > 0, "sign-flipped a positively-correlated low-fidelity model"
    assert ck.rho_evidence > 2.0
    assert ck.rho_warning == ""

    Xt = np.linspace(0, 1, 200)[:, None]
    yt = forrester_hi(Xt[:, 0])
    gp = GP.fit(X_hi, y_hi)
    assert (np.sqrt(np.mean((ck.predict(Xt)[0] - yt) ** 2))
            < np.sqrt(np.mean((gp.predict(Xt)[0] - yt) ** 2)))


def test_a_useless_low_fidelity_model_is_announced_not_swallowed():
    """The register's complaint was not only that rho was wrong, it was "with
    NO DIAGNOSTIC". A scalar rho with no provenance is how rho = -0.64 on a
    positively-correlated partner went unnoticed.

    Two degenerate shapes, both MEASURED:
      - LF replaced by white noise: the fitted rho ranges over
        +2.22 / -2.36 / +4.02 / +0.45 / -1.63 across five seeds — pure noise
        fitting — and beats rho=0 by 0.06 to 0.96 nats, i.e. not at all.
      - LF a constant: rho is structurally unidentifiable (`rho * const` is
        absorbed by the delta-GP's mean) and the old scan ran out to
        rho = 2,378,233.8, which then multiplies the LF sigma into every
        prediction and makes every query out of support.
    """
    X_lo = np.linspace(0, 1, 21)[:, None]
    X_hi = np.linspace(0, 1, 12)[:, None]
    y_hi = forrester_hi(X_hi[:, 0])

    for seed in range(5):
        noise = np.random.default_rng(seed).standard_normal(21)
        with pytest.warns(RhoDegenerate, match="NOT IDENTIFIED"):
            ck = CoKriging.fit(X_lo, noise, X_hi, y_hi)
        assert ck.rho_evidence < 2.0 and ck.rho_warning
        with pytest.raises(ValueError, match="co-kriging refused"):
            CoKriging.fit(X_lo, noise, X_hi, y_hi, strict=True)

    const = np.full(21, 3.0) + 1e-9 * np.random.default_rng(0).standard_normal(21)
    with pytest.warns(RhoDegenerate, match="CONSTANT"):
        ck = CoKriging.fit(X_lo, const, X_hi, y_hi)
    assert ck.rho == 0.0, "an unidentifiable rho must be 0, not 2.4e6"


# ---------------------------------------------------------------------------
# I4 — batched infill was defeated exactly where it exists
# ---------------------------------------------------------------------------

def test_infill_diversity_is_measured_in_the_candidate_box_not_the_training_span():
    """The mutual-distance filter normalised with `gp._norm`, i.e. by the span
    of the few HIGH-FIDELITY TRAINING points. You infill where you have NOT
    been, so that span is systematically narrower than the candidate box, and
    the error runs in the dangerous direction: a small training span INFLATES
    every normalised distance, the filter passes everything, and the batch
    collapses onto the EI peak.

    MEASURED, HF points drawn on [0.40, 0.55], candidates on [0, 1],
    min_dist = 0.05, k = 5 — delivered minimum separation:

        n_candidates    old      new
                  21    0.0500   0.0500
                  51    0.0200   0.0600
                 101    0.0100   0.0500
                 201    0.0100   0.0500

    The requested separation is 0.05 and the old delivered separation falls to
    the candidate grid spacing: at 101 candidates it picked 0.36, 0.37, 0.63,
    0.64, 0.65 — two experiments billed as five expensive runs. Note the bug
    HIDES on a coarse grid, where the grid itself enforces the spacing; the
    original gate test used 101 candidates but only k=3 and a 0.03 bar.
    """
    rng = np.random.default_rng(0)
    X_hi = rng.uniform(0.40, 0.55, (8, 1))
    gp = GP.fit(X_hi, forrester_hi(X_hi[:, 0]))
    y_best = float(forrester_hi(X_hi[:, 0]).min())
    for n_cand in (51, 101, 201):
        cand = np.linspace(0, 1, n_cand)[:, None]
        picks = np.sort(cand[batch_infill(gp, cand, y_best, k=5, min_dist=0.05), 0])
        gap = float(np.min(np.abs(picks[:, None] - picks[None, :])
                           + 1e9 * np.eye(len(picks))))
        assert gap >= 0.05 - 1e-9, (
            f"n_cand={n_cand}: asked for 0.05 separation, delivered {gap:.4f} "
            f"at {picks} — the filter is rounding, not filtering")


def test_a_short_infill_batch_raises_instead_of_shrinking_the_compute_plan():
    """It returned a short array and said nothing. MEASURED on a 51-point
    candidate grid at min_dist 0.05: asked 20/40/60, got 20/40/51 under the
    training-span normalisation and 17 under the honest one. A caller sizes a
    cluster booking on k; a batch that quietly halves is a compute plan that
    quietly halves."""
    rng = np.random.default_rng(0)
    X_hi = rng.uniform(0.40, 0.55, (8, 1))
    gp = GP.fit(X_hi, forrester_hi(X_hi[:, 0]))
    cand = np.linspace(0, 1, 51)[:, None]
    assert len(batch_infill(gp, cand, 0.0, k=10)) == 10
    with pytest.raises(InfillStarved) as e:
        batch_infill(gp, cand, 0.0, k=40)
    assert e.value.k == 40 and 0 < len(e.value.chosen) < 40
    short = batch_infill(gp, cand, 0.0, k=40, strict=False)
    assert len(short) == len(e.value.chosen)


def test_infill_bounds_override_a_candidate_set_that_does_not_span_the_box():
    """A candidate set drawn as a random SAMPLE need not reach the box corners,
    so inferring the box from it slightly over-states the spacing. `bounds=`
    is the explicit escape hatch, and it must actually bind."""
    rng = np.random.default_rng(1)
    X_hi = rng.uniform(0.40, 0.55, (8, 1))
    gp = GP.fit(X_hi, forrester_hi(X_hi[:, 0]))
    cand = np.sort(rng.uniform(0.2, 0.8, (200, 1)), axis=0)
    picks = np.sort(cand[batch_infill(gp, cand, 0.0, k=4, min_dist=0.1,
                                      bounds=(np.array([0.0]), np.array([1.0]))), 0])
    gap = float(np.min(np.abs(picks[:, None] - picks[None, :])
                       + 1e9 * np.eye(len(picks))))
    assert gap >= 0.1 - 1e-9, picks


def test_min_dist_is_a_euclidean_norm_and_does_not_bind_per_axis_in_15d():
    """DOCUMENTATION DEFECT, PINNED SO IT CANNOT SILENTLY BECOME A BEHAVIOUR
    ONE. `batch_infill`'s docstring said `min_dist` was "a fraction of the
    CANDIDATE BOX per axis". It is applied as `np.linalg.norm`, and in ONE
    dimension those are the same sentence — which is why the 1-D table in that
    docstring is honest and the design-space case was not covered at all.

    MEASURED in the 15-D grammar box, k=5 from 400 uniform candidates:

        min_dist requested   picks change?   min PER-AXIS gap   min EUCLIDEAN
              0.05               —               0.00121           1.1945
              0.10           identical           0.00121           1.1945
              0.20           identical           0.00121           1.1945
              0.50           identical           0.00121           1.1945
              1.00           identical           0.00121           1.1945
              1.50             changed           0.00172           1.5202
              2.00           k drops to 3        0.00984           2.0133

    The same five points come back for every request across a twentyfold range:
    random points in a 15-cube are already ~1.2 apart in norm, so the bar is
    INERT, and two picks 0.0012 of an axis apart — a tenth of a millimetre of
    beam — are billed as two experiments. The behaviour was NOT changed: a
    per-axis (Chebyshev) test would alter every caller's batch and nobody has
    measured what that does to infill quality. The docstring now says
    "EUCLIDEAN" and carries this table; this test holds the measurement, so a
    later behaviour change has to come with a new one.
    """
    from navalai import grammar

    rng = np.random.default_rng(3)
    d = len(grammar.LOW)
    C = rng.uniform(grammar.LOW, grammar.HIGH, size=(400, d))
    Xtr = rng.uniform(grammar.LOW, grammar.HIGH, size=(30, d))
    y = Xtr[:, 0] * 0.3 + rng.normal(0, 0.1, 30)
    gp = GP.fit(Xtr, y, seed=0)

    picks = {md: tuple(batch_infill(gp, C, float(y.min()), k=5, min_dist=md,
                                    strict=False))
             for md in (0.05, 0.1, 0.2, 0.5, 1.0)}
    assert len({p for p in picks.values()}) == 1, (
        "min_dist now discriminates between 0.05 and 1.0 in 15-D — the "
        "behaviour changed and the docstring's table must be re-measured")

    lo, hi = C.min(0), C.max(0)
    span = np.where(hi - lo < 1e-12, 1.0, hi - lo)
    Pn = (C[list(picks[0.05])] - lo) / span
    per_axis, euclid = [], []
    for i in range(len(Pn)):
        for j in range(i + 1, len(Pn)):
            per_axis.append(float(np.abs(Pn[i] - Pn[j]).min()))
            euclid.append(float(np.linalg.norm(Pn[i] - Pn[j])))
    assert min(per_axis) < 0.05, (
        f"the requested 0.05 now binds per axis (min gap {min(per_axis):.5f}); "
        f"the documented measurement is stale")
    assert min(euclid) > 1.0

    # ...and it DOES bind, as a norm, once it is asked for in the right units.
    #
    # THE RIGHT UNITS DEPEND ON THE DIMENSION, which is this test's own point.
    # The 15-D table above binds at 2.0. RE-MEASURED 2026-08-24 at 21 genes,
    # where uniform points in [0,1]^d sit 1.845 apart on average instead of
    # ~1.6, the same sweep reads:
    #
    #     min_dist   k picked
    #        2.00        5
    #        2.20        5
    #        2.40        3      <-- binds here
    #        2.60        2
    #
    # so the threshold is scaled with the box diagonal rather than transcribed.
    # A hard-coded 2.0 would have gone on passing at 15 genes and silently
    # stopped testing anything at 21.
    _bind = 2.4 * (grammar.N_PARAMS / 21.0) ** 0.5
    assert len(batch_infill(gp, C, float(y.min()), k=5, min_dist=_bind,
                            strict=False)) < 5

    doc = batch_infill.__doc__
    assert "EUCLIDEAN" in doc and "per axis" in doc


def test_cokriging_reads_a_real_high_fidelity_tier_or_refuses_with_a_count():
    """GAP I1, and the reason it stayed open for so long.

    The gap asks that co-kriging be fitted from REAL high-fidelity provenance
    rows "rather than the synthetic Forrester pair". `CoKriging` has existed in
    surrogate.py throughout with NO production caller: `flywheel.retrain` reads
    `training_matrix("L1", ...)` and nothing in the package ever read a tier
    above it — because nothing ever WROTE one. A solved RANS campaign left
    force histories on disk and produced no provenance row, so the tier the
    gap is about did not exist to be read.

    Both halves are fenced here:

      * `fit_cokriging` READS the high tier and refuses BY NAME with a COUNT
        when it is too thin — not silently, not by falling back to the cheap
        model, and not by fitting anyway;
      * the floor is a floor, not a sufficiency claim. MEASURED 2026-08-22 on
        the completed Gate 2U campaign, 5 of 23 scorable cases SETTLED, and
        five points in a 16-dimensional genome is an interpolation of noise at
        the tier whose entire job is to CORRECT the cheap model.
    """
    import numpy as np
    import pytest as _pytest

    from navalai import db
    from navalai.flywheel import MIN_HF_ROWS, fit_cokriging

    prov = db.Provenance(":memory:")
    rng = np.random.default_rng(0)

    def _add(tier, k):
        for _ in range(k):
            x = np.array(grammar.LOW, float) + rng.random(grammar.N_PARAMS) * (
                np.array(grammar.HIGH, float) - np.array(grammar.LOW, float))
            hid = prov.add_hull(x)
            prov.add_result(hid, tier, "s", "v", "resistance_N",
                            float(rng.uniform(100, 900)), uncertainty=1.0)

    # No high tier at all: the state this repository was actually in.
    _add("L1", 30)
    with _pytest.raises(ValueError, match="0 real L3 row"):
        fit_cokriging(prov)

    # A thin high tier still refuses, and says HOW thin.
    _add("L3", MIN_HF_ROWS - 1)
    with _pytest.raises(ValueError, match=f"{MIN_HF_ROWS - 1} real L3 row"):
        fit_cokriging(prov)

    # Enough rows and it fits — the refusal is a threshold, not a wall.
    _add("L3", 1)
    model = fit_cokriging(prov)
    assert model is not None
    assert hasattr(model, "rho")

    # And the LOW tier cannot be the sparse one: co-kriging's cheap half being
    # thinner than its expensive half is a misconfiguration, not a model.
    thin = db.Provenance(":memory:")
    prov2, prov = prov, thin
    _add("L1", 2); _add("L3", MIN_HF_ROWS + 2)
    with _pytest.raises(ValueError, match="cannot be the sparse one"):
        fit_cokriging(prov)
