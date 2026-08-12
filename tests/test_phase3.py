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


def test_the_l1_error_bar_is_measured_across_seeds_and_it_misses_the_bar(l1_gp):
    """Gap D10: Gate 3's error bar sat on ONE query seed, and that seed was the
    only one of five that cleared it.

    MEASURED 2026-08-12 — same training draw (seed 7, n=250), same fit
    (GP.fit(seed=1)), five held-out draws of 35:

        query seed   kept    median rel err   within 2-sigma
              991    27/35        0.1056           0.963
              992    33/35        0.1830           0.879
              993    31/35        0.2222           0.968
              994    34/35        0.1798           0.824
              995    33/35        0.2340           0.818

        across-seed median   0.1830     spread 2.22x (0.1056 - 0.2340)

    991 is the seed the test pinned and it is the MINIMUM. Every other honest
    draw lands 0.18-0.23 against a <=0.15 bar, so the gate was reading a
    favourable draw as a property of the model.

    THE BAR IS NOT MOVED. 0.15 is what Gate 3 claims and it stands; what
    changes is that the shortfall is now MEASURED, asserted honestly here, and
    carried as `Gate 3E` — a typed RED row with a watermark, an owner and a
    review_by in data/gate-ledger.json. That is the Gate 4F treatment applied
    to the same shape: a suite that passes everything it asserts while the
    clause it is named for is missed. The watermark is NOT restated in this
    file; the ledger is its one home.
    """
    gp, m = l1_gp
    meds = [_l1_draw(gp, m, s)[0] for s in L1_QUERY_SEEDS]
    across = float(statistics.median(meds))

    # The honest assertion of a MISSED bar, in the shape test_phase4.py uses
    # for raw feasibility: it asserts the shortfall EXISTS, so the day the
    # model improves this test fails and the ledger row must be retired.
    assert across > 0.15, (
        f"the across-seed median error bar is {across:.4f}, i.e. Gate 3's "
        f"0.15 bar is now MET across seeds. Delete the Gate 3E row and its "
        f"ledger entry — a GREEN gate still listed in the ledger is a failure.")
    # ...and it must not have got worse than the recorded watermark, which the
    # ledger owns. This is the local sanity band, not the watermark.
    assert 0.15 < across < 0.25, f"across-seed median {across:.4f}"

    # THE POINT OF THE ROW: the pinned seed disagrees with the model.
    assert min(meds) < 0.15 < across, (
        "the single-seed reading no longer differs from the across-seed one, "
        "so D10's finding has changed shape — re-measure the table above")
    assert max(meds) / min(meds) > 2.0, (
        f"seed spread collapsed to {max(meds) / min(meds):.2f}x; the table "
        f"above is the thing that is now wrong")


def test_calibration_is_measured_as_a_curve_with_sharpness_beside_it(l1_gp):
    """Gap I5: the whole calibration evidence for this module was ONE
    assertion, `within >= 0.75`, on a 2-sigma band whose nominal level is
    0.9545.

    One point on the coverage curve cannot separate "the band is too wide in
    the middle" from "the tails are wrong", and coverage alone is GAMEABLE:
    any model hits any coverage target by inflating sigma. This repository has
    already shipped one bar a degenerate answer passed (`gci <= 5.0` is true of
    -27%), so sharpness is measured beside coverage, always.

    MEASURED 2026-08-12 on the Gate 3 GP, held-out draw seed 991, 27 in-support
    hulls, in log(Wh/NM) space:

        nominal   0.500   0.800   0.900   0.9545   0.990
        empirical 0.667   0.815   0.926   0.963    1.000

        calibration_error 0.0452   sharpness 0.2462   PIT KS 0.2268
        PIT mean 0.4048

    The model is UNDER-confident at the middle of the curve (0.667 against a
    nominal 0.50) — which the single 2-sigma assertion could not have shown,
    because at 2 sigma it reads 0.963 and passes anything above 0.75.

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
    assert keep.sum() == 27, "the measured table above is for 27 in-support hulls"

    rep = calibration(gp, Xk, yk)
    assert rep["n"] == 27 and rep["levels"] == COVERAGE_LEVELS
    curve = rep["coverage_curve"]
    for lv, want in ((0.50, 0.667), (0.80, 0.815), (0.90, 0.926),
                     (0.9545, 0.963), (0.99, 1.000)):
        assert curve[lv] == pytest.approx(want, abs=0.02), (
            f"coverage at nominal {lv} moved to {curve[lv]:.3f}; re-measure "
            f"the table above rather than widening this")
    assert rep["calibration_error"] == pytest.approx(0.0452, abs=0.005)
    assert rep["sharpness"] == pytest.approx(0.2462, rel=0.02)
    assert rep["pit_ks"] == pytest.approx(0.2268, abs=0.02)

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
    assert tight["calibration_error"] > 8 * rep["calibration_error"]
    assert tight["coverage_curve"][0.9545] == pytest.approx(0.481, abs=0.02)
    assert tight["sharpness"] < 0.3 * rep["sharpness"]

    vague = calibration(_Scaled(gp, 4.0), Xk, yk)
    assert vague["calibration_error"] > 3 * rep["calibration_error"]
    assert vague["coverage_curve"][0.9545] == pytest.approx(1.0)
    assert vague["sharpness"] > 3 * rep["sharpness"], (
        "sharpness is what stops a coverage target being bought by widening "
        "the band, and it did not move")

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

    MEASURED 2026-08-12, all three on `sample_valid(250, MissionSpec(),
    seed=7)` with `GP.fit(..., seed=1)` on log(Wh/NM):

        training set        lengthscales at the 10.0 ceiling
        full box            1 of 15   x_mb
        LWL <= 12 m         4 of 15   D, beta_bow, p_bow, sheer_rise
        beta_mid >= 12 deg  3 of 15   p_stern, x_mb, beta_len

    Every one of those is the kernel declaring itself blind along an axis, and
    every one of them was invisible: `fit` returned, nothing was recorded, and
    the predictive sigma the OOD test is built on could not see a query that
    moved only along a saturated input. Defect class 1 with the roles swapped —
    the value was measured, by the optimiser, and then discarded.

    The bar is that the report is DERIVED from the fitted lengthscales and the
    same bounds `fit` searched in, so it cannot drift; the negative control is
    a fit that does NOT saturate, which must report nothing.
    """
    from navalai.evaluate import sample_valid
    from navalai.surrogate import ARD_LENGTHSCALE_BOUNDS, ARDSaturation

    lo, hi = ARD_LENGTHSCALE_BOUNDS
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)

    # THE GUARD IS MADE TO FIRE, on the production Gate 3 GP itself.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gp = GP.fit(X, np.log(y), seed=1)
    assert gp.ls_at_bound == ((8, "upper"),), (
        f"x_mb no longer saturates: {gp.ls_at_bound} — re-measure the table in "
        f"this docstring rather than loosening the assertion")
    assert grammar.NAMES[8] == "x_mb"
    assert gp.ls[8] == pytest.approx(hi, rel=1e-9)
    assert any(issubclass(w.category, ARDSaturation) for w in caught), (
        "the fit saturated and nobody was told")
    rep = gp.saturation_report()
    assert "x_mb" not in rep and "input 8" in rep   # index, not a name it lacks
    assert "blind" in rep

    # The restricted fit saturates HARDER, and the report tracks it rather than
    # carrying a number written down once.
    inside = X[:, 0] <= 12.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ARDSaturation)
        gp_r = GP.fit(X[inside], np.log(y[inside]), seed=1)
    assert [i for i, _e in gp_r.ls_at_bound] == [3, 5, 6, 13]
    assert all(e == "upper" for _i, e in gp_r.ls_at_bound)
    assert "4 of 15" in gp_r.saturation_report()

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
    ignore. ARD lengthscales saturate — MEASURED on the LWL-restricted GP
    above, two of the fifteen sat exactly on the optimiser's upper bound (10.0)
    — and sigma is computed through those same lengthscales, so it is blind
    there. A support test that also divided by them would inherit the blindness,
    which is why `_nn_distance` is unweighted.

    MEASURED, training restricted to beta_mid >= 12 deg, 200 queries:
        sigma only        58/200 rejected, kept 0.200, rejected 0.354, recall 0.47
        sigma + distance  82/200 rejected, kept 0.180, rejected 0.354, recall 0.63
    """
    from navalai.evaluate import sample_valid
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)
    Xq, yq = sample_valid(200, m, seed=901)

    inside = X[:, 4] >= 12.0                       # index 4 is beta_mid
    gp = GP.fit(X[inside], np.log(y[inside]), seed=1)
    pred, sig = gp.predict(Xq)
    rel = np.abs(np.exp(pred) - yq) / yq
    out = Xq[:, 4] < 12.0

    sigma_only = sig > 0.6 * np.sqrt(gp.var)
    both = gp.is_ood(Xq)
    r_old = (sigma_only & out).sum() / out.sum()
    r_new = (both & out).sum() / out.sum()
    assert r_new >= r_old + 0.10, (
        f"the distance term adds nothing: recall {r_old:.2f} -> {r_new:.2f}")
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
    assert len(batch_infill(gp, C, float(y.min()), k=5, min_dist=2.0,
                            strict=False)) < 5

    doc = batch_infill.__doc__
    assert "EUCLIDEAN" in doc and "per axis" in doc
