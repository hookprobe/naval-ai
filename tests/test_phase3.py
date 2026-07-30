"""Gate 3: co-kriging beats single-fidelity on Forrester; GP honest on our L1
physics; OOD queries escalate; batched EI infill works."""

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
from navalai.surrogate import (GP, CoKriging, batch_infill,
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
