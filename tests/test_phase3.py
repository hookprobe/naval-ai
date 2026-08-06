"""Gate 3: co-kriging beats single-fidelity on Forrester; GP honest on our L1
physics; OOD queries escalate; batched EI infill works."""

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
from navalai.surrogate import (GP, CoKriging, OODRefusal, batch_infill,
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


def test_surrogate_on_l1_physics():
    """GP on log(Wh/NM) over 250 L1-valid hulls: median rel error < 15% on
    held-out in-support hulls, and the sigma band must be calibrated.

    (Measured baseline: n=250 -> median 10.3%, 2-sigma coverage 91%, and ARD
    lengthscales rank LWL/BWL/T as dominant — matching physics. The published
    <=1-2% bars are for LOCAL low-D deformation spaces near an optimum, not a
    global 15-D grammar; this gate states the honest global number.)"""
    from navalai.evaluate import sample_valid
    m = MissionSpec()
    X, y = sample_valid(250, m, seed=7)
    gp = GP.fit(X, np.log(y), seed=1)
    Xt, yt = sample_valid(35, m, seed=991)
    keep = ~gp.is_ood(Xt, 0.5)
    assert keep.sum() >= 15, "OOD filter rejected almost everything"
    pred, sigma = gp.predict(Xt[keep])
    rel = np.abs(np.exp(pred) - yt[keep]) / yt[keep]
    assert np.median(rel) < 0.15, f"median rel err {np.median(rel):.3f}"
    within = (np.abs(pred - np.log(yt[keep])) <= 2 * sigma).mean()
    assert within >= 0.75, f"only {within:.0%} within 2 sigma"


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
    """
    X_lo = np.linspace(0.0, 0.5, 11)[:, None]
    X_hi = np.linspace(0.0, 1.0, 11)[:, None]
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
