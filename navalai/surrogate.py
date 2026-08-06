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
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize


def _rbf(A: np.ndarray, B: np.ndarray, ls: np.ndarray) -> np.ndarray:
    d = (A[:, None, :] - B[None, :, :]) / ls[None, None, :]
    return np.exp(-0.5 * np.sum(d * d, axis=2))


@dataclass
class GP:
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
        return GP(Xn, y, ls, var0, nugget, mu, c, a, x_lo, span)

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

    def is_ood(self, X: np.ndarray, sigma_frac: float = 0.6) -> np.ndarray:
        """True where predictive sigma exceeds sigma_frac of prior sigma —
        i.e. the GP admits it knows (almost) nothing there."""
        _m, s = self.predict(X)
        return s > sigma_frac * np.sqrt(self.var)


@dataclass
class CoKriging:
    """Kennedy-O'Hagan AR(1): f_hi = rho * f_lo + delta."""

    gp_lo: GP
    gp_delta: GP
    rho: float

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

    def is_ood(self, X: np.ndarray) -> np.ndarray:
        return self.gp_delta.is_ood(X)


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
