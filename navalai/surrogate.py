"""Phase 3 surrogate spine: Kriging + AR(1) co-kriging with honest uncertainty.

Research grounding (BuildPlan section 1.2): multi-fidelity co-kriging beat
single-fidelity Kriging after CFD re-validation on DTMB 5415 (~0.05% vs -5.98%
error at the optimum); adaptive infill must be batched. Implementation:
Gaussian-process regression (anisotropic RBF, nugget) and the Kennedy-O'Hagan
autoregressive scheme  f_hi(x) = rho * f_lo(x) + delta(x).

Honesty rules implemented here:
  - every predict() returns (mean, sigma), never a bare number
  - is_ood() flags queries far outside training support -> ladder escalation,
    the "a query far from support must say so" gate
  - predict_or_escalate() is the only caller-facing entry point that is allowed
    to hand back a tier badge: out of support it either runs real physics or
    raises OODRefusal. It never returns a surrogate-badged number for a query
    the surrogate cannot support.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize


class OODRefusal(RuntimeError):
    """The surrogate was asked for a number it has no support for.

    `is_ood()` had TWO call sites in the whole repository and both were in
    tests: it flagged, and nothing anywhere escalated or refused. Gate 3's bar
    is "OOD queries reliably escalate to L2/L3", so a boolean that no caller
    consumes is not an implementation of it. Raising is the fallback when the
    caller offers no escalation route — silence is the one answer that is
    never honest.
    """

    def __init__(self, message: str, sigma: float | None = None,
                 distance: float | None = None, threshold: float | None = None):
        super().__init__(message)
        self.sigma = sigma
        self.distance = distance
        self.threshold = threshold


def _rbf(A: np.ndarray, B: np.ndarray, ls: np.ndarray) -> np.ndarray:
    d = (A[:, None, :] - B[None, :, :]) / ls[None, None, :]
    return np.exp(-0.5 * np.sum(d * d, axis=2))


def _pairwise(X: np.ndarray) -> np.ndarray:
    d = X[:, None, :] - X[None, :, :]
    return np.sqrt(np.einsum("ijk,ijk->ij", d, d))


def _nn_distance(Q: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Distance from every row of Q to its NEAREST row of X, unweighted.

    Deliberately NOT lengthscale-weighted. The ARD lengthscales are what the
    sigma test already looks through, and they saturate: MEASURED on a GP
    trained on 100 L1 hulls, two of the fifteen lengthscales sat exactly on the
    optimiser's upper bound (10.0), which means the kernel — and therefore
    sigma — is blind to those two axes entirely. A support test that divides by
    the same lengthscales inherits the same blind spot and adds nothing. This
    one asks the plain question the name promises: have we ever seen a hull
    like this?
    """
    d = Q[:, None, :] - X[None, :, :]
    return np.sqrt(np.einsum("ijk,ijk->ij", d, d)).min(axis=1)


class _Escalates:
    """The escalation seam, shared by GP and CoKriging.

    Gate 3 says "OOD queries reliably escalate to L2/L3". Before this the whole
    mechanism was `is_ood()` returning a boolean into two test files. A caller
    that wanted a number called `predict()`, which answers everywhere with the
    same confidence-shaped tuple whether or not the model has any business
    answering at all.
    """

    def predict_or_escalate(self, X, escalate_fn=None, tier: str = "S1",
                            escalate_tier: str = "L1", **ood_kw):
        """(value, tier, sigma) — and never a surrogate badge off support.

        `escalate_fn(x)` is the real-physics fallback: it takes ONE parameter
        vector and returns either a value or a (value, sigma) pair. Results it
        produces are badged `escalate_tier`, because the tier a number carries
        must name the solver that actually produced it. With no fallback
        offered, an out-of-support query raises OODRefusal.

        A 1-D X is one query and returns scalars; a 2-D X returns arrays.
        """
        Q = np.asarray(X, float)
        single = Q.ndim == 1
        Q = np.atleast_2d(Q)
        mean, sigma = self.predict(Q)
        ood = self.is_ood(Q, **ood_kw)
        d = self.support_distance(Q)
        tiers = np.array([tier] * len(Q), dtype=object)
        val = np.asarray(mean, float).copy()
        sig = np.asarray(sigma, float).copy()
        for i in np.flatnonzero(ood):
            if escalate_fn is None:
                raise OODRefusal(
                    f"query {i} is outside the surrogate's support "
                    f"(sigma {sigma[i]:.4g} of a {np.sqrt(self.prior_var):.4g} "
                    f"prior; nearest training point {d[i]:.3f} against a "
                    f"support radius of {self.d_support:.3f}) and no "
                    f"escalation route was given. Pass escalate_fn=... to run "
                    f"real physics, or evaluate() it directly — a "
                    f"{tier}-badged number here would be a guess wearing a "
                    f"tier badge.",
                    sigma=float(sigma[i]), distance=float(d[i]),
                    threshold=float(self.d_support))
            out = escalate_fn(Q[i])
            if isinstance(out, tuple):
                val[i], sig[i] = float(out[0]), float(out[1])
            else:
                val[i], sig[i] = float(out), float("nan")
            tiers[i] = escalate_tier
        if single:
            return float(val[0]), str(tiers[0]), float(sig[0])
        return val, tiers, sig


@dataclass
class GP(_Escalates):
    X: np.ndarray
    y: np.ndarray
    ls: np.ndarray
    var: float
    nugget: float
    mu: float
    _chol: tuple
    _alpha: np.ndarray
    x_lo: np.ndarray
    x_hi: np.ndarray
    # Radius of the largest hole the training set leaves between neighbouring
    # points, in the normalised input box. Set by fit(); see is_ood().
    d_support: float = field(default=np.inf)

    @property
    def prior_var(self) -> float:
        return self.var

    @staticmethod
    def fit(X: np.ndarray, y: np.ndarray, nugget: float = 1e-8,
            restarts: int = 3, seed: int = 0) -> "GP":
        X = np.atleast_2d(np.asarray(X, float))
        y = np.asarray(y, float)
        n, d = X.shape
        x_lo, x_hi = X.min(0), X.max(0)
        span = np.where(x_hi - x_lo < 1e-12, 1.0, x_hi - x_lo)
        Xn = (X - x_lo) / span
        mu = float(y.mean())
        yc = y - mu
        var0 = max(float(yc.var()), 1e-12)
        rng = np.random.default_rng(seed)

        # THE NUGGET IS LEARNED, not fixed at 1e-8 jitter. With a fixed tiny
        # nugget the GP INTERPOLATES: sigma -> 0 at every training point and
        # the predictive variance is structurally too small everywhere else.
        # MEASURED: 2-sigma coverage 0.85-0.91 against a nominal 0.95 on the
        # Gate 3 GP, and injecting sigma=0.05 label noise dropped it to 0.782
        # with std(z)=1.93. A surrogate whose band is too narrow is worse than
        # one with no band, because the OOD test is built on that same sigma.
        def nll(theta):
            ls, nug = np.exp(theta[:-1]), np.exp(theta[-1])
            K = var0 * _rbf(Xn, Xn, ls) + (nug + 1e-10) * var0 * np.eye(n)
            try:
                c = cho_factor(K, lower=True)
            except np.linalg.LinAlgError:
                return 1e10
            a = cho_solve(c, yc)
            return float(0.5 * yc @ a + np.log(np.diag(c[0])).sum())

        best, best_v = np.zeros(d + 1), np.inf
        bounds = [(np.log(1e-2), np.log(10.0))] * d + [(np.log(1e-8), np.log(0.5))]
        for r in range(restarts):
            x0 = (np.append(rng.uniform(np.log(0.05), np.log(2.0), d),
                            np.log(max(nugget, 1e-6))) if r
                  else np.append(np.full(d, np.log(0.3)), np.log(max(nugget, 1e-6))))
            res = minimize(nll, x0, method="L-BFGS-B", bounds=bounds)
            if res.fun < best_v:
                best, best_v = res.x, res.fun
        ls, nugget = np.exp(best[:-1]), float(np.exp(best[-1]))
        K = var0 * _rbf(Xn, Xn, ls) + (nugget + 1e-10) * var0 * np.eye(n)
        c = cho_factor(K, lower=True)
        a = cho_solve(c, yc)
        # The support radius is MEASURED from the training set, not declared:
        # the 95th percentile of each training point's distance to its own
        # nearest neighbour. A query farther from the data than the data is
        # from itself is in a hole the model was never shown. Calibrating it
        # this way is what makes the test dimension- and density-aware; a fixed
        # distance in 15-D means nothing (uniform points in [0,1]^15 sit ~1.6
        # apart on average, so any absolute bar is either never or always hit).
        if n >= 2:
            dd = _pairwise(Xn)
            np.fill_diagonal(dd, np.inf)
            d_support = float(np.quantile(dd.min(axis=1), 0.95))
        else:
            d_support = float("inf")
        return GP(Xn, y, ls, var0, nugget, mu, c, a, x_lo, span, d_support)

    def _norm(self, X: np.ndarray) -> np.ndarray:
        return (np.atleast_2d(np.asarray(X, float)) - self.x_lo) / self.x_hi

    def predict(self, X: np.ndarray):
        Xn = self._norm(X)
        k = self.var * _rbf(Xn, self.X, self.ls)
        mean = self.mu + k @ self._alpha
        # The learned noise belongs in the PREDICTIVE variance too, or the
        # band still collapses at the data even after learning it.
        v = (self.var * (1.0 + self.nugget)
             - np.einsum("ij,ji->i", k, cho_solve(self._chol, k.T)))
        return mean, np.sqrt(np.maximum(v, 1e-14))

    def support_distance(self, X: np.ndarray) -> np.ndarray:
        """Distance from each query to the nearest TRAINING point, normalised."""
        return _nn_distance(self._norm(X), self.X)

    def is_ood(self, X: np.ndarray, sigma_frac: float = 0.6,
               support_frac: float = 1.0) -> np.ndarray:
        """Out of support: the GP's band is wide, OR the query sits in a hole.

        IT USED TO BE THE FIRST TEST ALONE, AND THAT IS A SIGMA THRESHOLD, NOT
        A SUPPORT TEST. MEASURED on the Gate 3 GP (250 L1 hulls, 240 held-out
        queries): it fired on 11 of 240 and the queries it rejected had a
        median relative error of 0.200 against 0.161 for the ones it kept — no
        separation at all, and on one seed the rejected set was the MORE
        accurate one. It fired at 100% only on hulls scaled 3x outside the
        grammar box, which `grammar.check` rejects before a surrogate is ever
        consulted, and at 0.0% on in-box queries whose error reached 146%.

        Two things were wrong and only one of them was the criterion. The other
        was the probe: train and test were both drawn uniformly from the same
        grammar box, so there was NO out-of-distribution query in the
        experiment. Nothing can separate an OOD set that is empty. Re-measured
        against a training set restricted to part of the box — which is what a
        real surrogate sees, since it is trained on wherever the optimiser has
        been — the two tests do different work:

            training support   criterion       rejected kept  rej  ratio recall
            full box (no OOD)  sigma only         1/240 0.172 0.186  1.08   --
            full box (no OOD)  sigma + distance  12/240 0.172 0.181  1.05   --
            LWL <= 12 m        sigma only       132/240 0.274 0.867  3.16  0.89
            LWL <= 12 m        sigma + distance 132/240 0.274 0.867  3.16  0.89
            beta_mid >= 12 deg sigma only        68/240 0.200 0.416  2.08  0.46
            beta_mid >= 12 deg sigma + distance  99/240 0.184 0.378  2.06  0.66
            T <= 0.85 m        sigma only        52/240 0.189 0.335  1.77  0.49
            T <= 0.85 m        sigma + distance  65/240 0.202 0.299  1.48  0.60

        "recall" is the fraction of queries that are out of the training
        support BY CONSTRUCTION which the criterion catches. The distance term
        is what catches an axis the kernel has decided to ignore: it lifts
        recall from 0.46 to 0.66 on the beta_mid split and 0.49 to 0.60 on the
        draft split, and costs a 5% false-alarm rate on a training set that
        really does span the box. Recorded rather than sold: on the draft split
        the extra rejections are milder cases, so the kept/rejected error RATIO
        drops from 1.77 to 1.48 even though both medians move the right way for
        the ones it now catches. Recall is the quantity this test exists to
        maximise — a missed OOD query returns a confident wrong number, a false
        alarm only costs an escalation.
        """
        _m, s = self.predict(X)
        far = self.support_distance(X) > support_frac * self.d_support
        return (s > sigma_frac * np.sqrt(self.var)) | far


@dataclass
class CoKriging(_Escalates):
    """Kennedy-O'Hagan AR(1): f_hi = rho * f_lo + delta."""

    gp_lo: GP
    gp_delta: GP
    rho: float

    @property
    def prior_var(self) -> float:
        return (self.rho * self.rho) * self.gp_lo.var + self.gp_delta.var

    @property
    def d_support(self) -> float:
        """The BINDING support radius — the one that refuses first."""
        return min(self.gp_lo.d_support, self.gp_delta.d_support)

    def support_distance(self, X: np.ndarray) -> np.ndarray:
        """Worst of the two, each measured against its own radius.

        Reported as a multiple of each GP's own radius and then scaled back, so
        a query that is fine for the delta-GP but far outside the low-fidelity
        data reports the distance that actually matters.
        """
        a = self.gp_lo.support_distance(X) / max(self.gp_lo.d_support, 1e-12)
        b = self.gp_delta.support_distance(X) / max(self.gp_delta.d_support, 1e-12)
        return np.maximum(a, b) * self.d_support

    @staticmethod
    def fit(X_lo: np.ndarray, y_lo: np.ndarray,
            X_hi: np.ndarray, y_hi: np.ndarray, seed: int = 0) -> "CoKriging":
        gp_lo = GP.fit(X_lo, y_lo, seed=seed)
        m_lo_at_hi, _ = gp_lo.predict(X_hi)
        # rho: centered-covariance start, then pick the candidate whose residual
        # the delta-GP explains best (leave-one-out error) — the KOH MLE spirit
        mc = m_lo_at_hi - m_lo_at_hi.mean()
        rho0 = float(np.dot(mc, y_hi - y_hi.mean()) / max(np.dot(mc, mc), 1e-12))
        span = max(abs(rho0), 0.5)
        best_rho, best_gp, best_err = rho0, None, np.inf
        for rho in np.linspace(rho0 - 1.5 * span, rho0 + 1.5 * span, 25):
            delta = y_hi - rho * m_lo_at_hi
            gp_d = GP.fit(X_hi, delta, seed=seed + 1, restarts=1)
            err = _loo_error(gp_d)
            if err < best_err:
                best_rho, best_gp, best_err = float(rho), gp_d, err
        return CoKriging(gp_lo, best_gp, best_rho)

    def predict(self, X: np.ndarray):
        m_lo, s_lo = self.gp_lo.predict(X)
        m_d, s_d = self.gp_delta.predict(X)
        mean = self.rho * m_lo + m_d
        sigma = np.sqrt((self.rho * s_lo) ** 2 + s_d**2)
        return mean, sigma

    def is_ood(self, X: np.ndarray, sigma_frac: float = 0.6,
               support_frac: float = 1.0) -> np.ndarray:
        """BOTH GPs get a vote, because both are in the prediction.

        It consulted `gp_delta` alone. But `predict()` returns
        `rho * m_lo + m_d`, so the low-fidelity GP's mean is multiplied into
        every answer this model gives. DEMONSTRATED: with the low-fidelity data
        confined to x in [0, 0.5] and the high-fidelity points spanning [0, 1],
        probes at x = 0.8 and 0.95 have `gp_lo.is_ood == [True, True]` — the
        term carrying rho is extrapolating — and the old `CoKriging.is_ood`
        returned [False, False], because the delta-GP had seen points nearby
        and it was the only one asked.
        """
        return (self.gp_lo.is_ood(X, sigma_frac, support_frac)
                | self.gp_delta.is_ood(X, sigma_frac, support_frac))


def _loo_error(gp: GP) -> float:
    """Leave-one-out RMSE via the Dubrule/Rasmussen closed form."""
    K = gp.var * _rbf(gp.X, gp.X, gp.ls) + (gp.nugget + 1e-10) * gp.var * np.eye(len(gp.X))
    Ki = np.linalg.inv(K)
    resid = (Ki @ (gp.y - gp.mu)) / np.diag(Ki)
    return float(np.sqrt(np.mean(resid**2)))


def expected_improvement(gp, X: np.ndarray, y_best: float) -> np.ndarray:
    """EI for minimisation — the batched-infill acquisition (BuildPlan 1.2)."""
    from scipy.stats import norm
    m, s = gp.predict(X)
    s = np.maximum(s, 1e-12)
    z = (y_best - m) / s
    return (y_best - m) * norm.cdf(z) + s * norm.pdf(z)


def batch_infill(gp, candidates: np.ndarray, y_best: float, k: int,
                 min_dist: float = 0.05) -> np.ndarray:
    """Pick k EI-ranked candidates with mutual distance (batched, not 1/cycle)."""
    ei = expected_improvement(gp, candidates, y_best)
    order = np.argsort(-ei)
    chosen: list[int] = []
    Xn = gp._norm(candidates) if isinstance(gp, GP) else gp.gp_delta._norm(candidates)
    for idx in order:
        if len(chosen) == k:
            break
        if all(np.linalg.norm(Xn[idx] - Xn[j]) > min_dist for j in chosen):
            chosen.append(int(idx))
    return np.array(chosen, dtype=int)


# ---- the standard multi-fidelity test problem (Forrester et al. 2007) -------

def forrester_hi(x: np.ndarray) -> np.ndarray:
    return (6 * x - 2) ** 2 * np.sin(12 * x - 4)


def forrester_lo(x: np.ndarray, A=0.5, B=10.0, C=-5.0) -> np.ndarray:
    return A * forrester_hi(x) + B * (x - 0.5) + C
