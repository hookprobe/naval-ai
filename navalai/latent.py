"""The 8-D latent genome (original plan, Phase 1/4).

Probabilistic PCA (Tipping & Bishop 1999) — the closed-form linear-Gaussian
VAE: encoder/decoder in one SVD, a proper N(0, I) prior to sample from, and
no training instability. Research honesty (BuildPlan 1.1) is preserved: NO
latent model guarantees validity, so decode() always passes through the L0
gate and the feasibility projection — 'guaranteed-valid' is delivered by the
gate, not assumed of the model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import grammar

LATENT_DIM = 8


@dataclass
class Genome:
    mean: np.ndarray          # (d,)
    W: np.ndarray             # (d, q) factor loadings
    sigma2: float             # residual variance
    M_inv: np.ndarray         # (q, q) posterior precision inverse
    explained: float          # fraction of variance captured by q dims
    X_train: np.ndarray

    @staticmethod
    def fit(X: np.ndarray, q: int = LATENT_DIM) -> "Genome":
        X = np.asarray(X, float)
        mu = X.mean(0)
        Xc = X - mu
        _u, s, vt = np.linalg.svd(Xc, full_matrices=False)
        lam = s**2 / len(X)                      # eigenvalues of covariance
        sigma2 = float(lam[q:].mean()) if len(lam) > q else 1e-9
        W = vt[:q].T * np.sqrt(np.maximum(lam[:q] - sigma2, 1e-12))
        M = W.T @ W + sigma2 * np.eye(q)
        explained = float(lam[:q].sum() / lam.sum())
        return Genome(mu, W, sigma2, np.linalg.inv(M), explained, X)

    # ---- encoder / decoder ----

    def encode(self, X: np.ndarray) -> np.ndarray:
        Xc = np.atleast_2d(X) - self.mean
        return Xc @ self.W @ self.M_inv.T        # posterior mean E[z|x]

    def decode(self, Z: np.ndarray, project: bool = True) -> np.ndarray:
        X = np.atleast_2d(Z) @ self.W.T + self.mean
        X = np.clip(X, grammar.LOW, grammar.HIGH)
        if not project:
            return X
        out = []
        for row in X:
            if grammar.check(row).ok:
                out.append(row)
                continue
            d = np.linalg.norm(self.X_train - row, axis=1)
            anchor = self.X_train[int(np.argmin(d))]
            for t in np.linspace(0.1, 1.0, 10):
                cand = (1 - t) * row + t * anchor
                if grammar.check(cand).ok:
                    out.append(cand)
                    break
            else:
                out.append(anchor)
        return np.array(out)

    # ---- generative sampling from the 8-D prior ----

    def sample(self, n: int, seed: int = 0, temperature: float = 1.0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        Z = rng.standard_normal((n, self.W.shape[1])) * temperature
        return self.decode(Z)

    def raw_prior_feasibility(self, n: int = 200, seed: int = 3) -> float:
        """Fraction of UNPROJECTED prior draws that already pass L0 — the
        honest measure of how 'valid' the latent space itself is."""
        rng = np.random.default_rng(seed)
        Z = rng.standard_normal((n, self.W.shape[1]))
        X = self.decode(Z, project=False)
        return float(np.mean([grammar.check(x).ok for x in X]))
