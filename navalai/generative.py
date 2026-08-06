"""Phase 4 generative core: hull-family model + performance-conditioned sampling.

Baseline per the research (survey S1: a GMM over feasible parameter vectors
plus a performance filter is the validated entry-level generative model on
Ship-D-style data; guided tabular diffusion is the planned upgrade and slots
in behind the same interface). The latent map is a 2-D PCA of the feasible
distribution — the PVAE 'browse a 2-D map' interaction (Danhaive & Mueller).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import linalg

from . import grammar


@dataclass
class HullFamilyModel:
    means: np.ndarray        # (k, d)
    covs: np.ndarray         # (k, d, d)
    weights: np.ndarray      # (k,)
    pca_mean: np.ndarray
    pca_axes: np.ndarray     # (2, d) principal directions
    pca_scale: np.ndarray    # (2,) stddev along axes
    X_train: np.ndarray

    # ---------- fitting ----------

    @staticmethod
    def fit(X: np.ndarray, k: int = 4, iters: int = 60, seed: int = 0) -> "HullFamilyModel":
        """Plain EM for a GMM (diagonal-regularised full covariances)."""
        rng = np.random.default_rng(seed)
        n, d = X.shape
        mu = X[rng.choice(n, k, replace=False)].copy()
        cov = np.tile(np.cov(X.T) + 1e-6 * np.eye(d), (k, 1, 1))
        w = np.full(k, 1.0 / k)
        for _ in range(iters):
            # E step
            logp = np.empty((n, k))
            for j in range(k):
                logp[:, j] = np.log(w[j] + 1e-12) + _mvn_logpdf(X, mu[j], cov[j])
            logp -= logp.max(1, keepdims=True)
            r = np.exp(logp)
            r /= r.sum(1, keepdims=True)
            # M step
            nk = r.sum(0) + 1e-9
            w = nk / n
            for j in range(k):
                mu[j] = (r[:, j:j + 1] * X).sum(0) / nk[j]
                dxy = X - mu[j]
                cov[j] = (r[:, j:j + 1] * dxy).T @ dxy / nk[j] + 1e-6 * np.eye(d)
        pca_mean = X.mean(0)
        Xc = X - pca_mean
        _u, s, vt = linalg.svd(Xc, full_matrices=False)
        axes = vt[:2]
        scale = s[:2] / np.sqrt(len(X))
        return HullFamilyModel(mu, cov, w, pca_mean, axes, scale, X)

    # ---------- sampling ----------

    def sample(self, n: int, seed: int = 0, max_tries: int = 400) -> np.ndarray:
        """Draw n L0-feasible hulls (GMM proposal + grammar gate)."""
        rng = np.random.default_rng(seed)
        out = []
        chol = [np.linalg.cholesky(c) for c in self.covs]
        for _ in range(max_tries * n):
            j = rng.choice(len(self.weights), p=self.weights)
            x = self.means[j] + chol[j] @ rng.standard_normal(self.means.shape[1])
            x = np.clip(x, grammar.LOW, grammar.HIGH)
            if grammar.check(x).ok:
                out.append(x)
                if len(out) == n:
                    return np.array(out)
        raise RuntimeError(f"generative sampler starved: {len(out)}/{n}")

    def sample_conditioned(self, n: int, score_fn, percentile: float,
                           seed: int = 0, batch: int = 64) -> np.ndarray:
        """Performance-conditioned generation: keep draws whose score_fn is in
        the best `percentile` of a reference batch (the literal performance
        knob from the PVAE precedent — percentile in [0, 1], 1 = best)."""
        # THE REFERENCE AND CANDIDATE BATCHES MUST BE DISJOINT.
        # `ref` was drawn at seed+1 and the loop then incremented s from `seed`
        # to seed+1, so the FIRST candidate batch was bit-identical to the
        # batch that set the threshold. VERIFIED: np.array_equal(ref, cand0)
        # was True, and a control ("score 64 plain draws, keep the best 10")
        # reproduced this function's output exactly — 316.3 vs 316.3, 313.4 vs
        # 313.4, 317.7 vs 317.7. It was selection dressed as conditioning, and
        # the Gate 4 test would have passed for any sampler whatsoever.
        ref = self.sample(batch, seed=seed + 1)
        ref_scores = score_fn(ref)
        cut = np.quantile(ref_scores, 1.0 - percentile)  # lower score = better
        out = []
        s = seed + 1
        while len(out) < n:
            s += 1
            cand = self.sample(batch, seed=s)
            sc = score_fn(cand)
            for x, v in zip(cand, sc):
                if v <= cut and len(out) < n:
                    out.append(x)
            if s - seed > 200:
                raise RuntimeError("conditioned sampler starved")
        return np.array(out)

    def raw_feasibility(self, n: int = 2000, seed: int = 0,
                        clip: bool = True) -> float:
        """Fraction of RAW model draws that pass L0 — the ShipGen-comparable
        number, and the one Gate 4's >=99% bar is actually about.

        `sample()` has `grammar.check` INSIDE its rejection loop, so measuring
        feasibility there returns 100% by construction and says nothing about
        the model. MEASURED with this method: raw GMM 31.98%, clipped to the
        box 77.60%, against a 99% bar — and the pPCA latent already in the repo
        scores 89.4%, i.e. the generative model is WORSE than something we
        already have. That is the gap the diffusion upgrade has to close.
        """
        rng = np.random.default_rng(seed)
        chol = [np.linalg.cholesky(c) for c in self.covs]
        ok = 0
        for _ in range(n):
            j = rng.choice(len(self.weights), p=self.weights)
            x = self.means[j] + chol[j] @ rng.standard_normal(self.means.shape[1])
            if clip:
                x = np.clip(x, grammar.LOW, grammar.HIGH)
            ok += bool(grammar.check(x).ok)
        return ok / n

    # ---------- 2-D latent map ----------

    def to_latent(self, X: np.ndarray) -> np.ndarray:
        return (np.atleast_2d(X) - self.pca_mean) @ self.pca_axes.T / self.pca_scale

    def from_latent(self, uv: np.ndarray) -> np.ndarray:
        """Decode a 2-D map point back to the nearest feasible full vector."""
        uv = np.atleast_2d(uv)
        x = self.pca_mean + (uv * self.pca_scale) @ self.pca_axes
        x = np.clip(x, grammar.LOW, grammar.HIGH)
        out = []
        for row in x:
            if grammar.check(row).ok:
                out.append(row)
                continue
            # project toward the nearest training hull until feasible
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


def _mvn_logpdf(X: np.ndarray, mu: np.ndarray, cov: np.ndarray) -> np.ndarray:
    d = X.shape[1]
    c, low = linalg.cho_factor(cov, lower=True)
    diff = X - mu
    sol = linalg.cho_solve((c, low), diff.T).T
    logdet = 2.0 * np.log(np.diag(c)).sum()
    return -0.5 * (d * np.log(2 * np.pi) + logdet + np.einsum("ij,ij->i", diff, sol))
