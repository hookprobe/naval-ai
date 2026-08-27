"""Phase 4 generative core: hull-family model + performance-conditioned sampling.

Baseline per the research (survey S1: a GMM over feasible parameter vectors
plus a performance filter is the validated entry-level generative model on
Ship-D-style data; guided tabular diffusion is the planned upgrade and slots
in behind the same interface). The latent map is a 2-D PCA of the feasible
distribution — the PVAE 'browse a 2-D map' interaction (Danhaive & Mueller).

THE INTERFACE IS `HullGenerator`, and it is the thing PLM listed as READY while
it did not exist. `HullFamilyModel` was a concrete dataclass of GMM/PCA
internals, a tree-wide grep for Protocol/ABC/abstractmethod in `navalai/` found
ZERO, `ui/server.py` constructed it with the GMM-specific `k`, and the Gate-4
tests reached into `model.X_train`. A diffusion model could not have dropped in
without editing the server and rewriting the tests — which is the definition of
not having an upgrade slot. There are now TWO implementations behind the
Protocol (`HullFamilyModel`, GMM; `PPCAGenerator`, the probabilistic-PCA
latent already in `navalai/latent.py`) and the Gate-4 suite runs against both,
because one implementation cannot demonstrate an interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
from scipy import linalg
from scipy.special import logsumexp

from . import grammar


@dataclass
class DecodeInfo:
    """What `from_latent` actually did, per requested point.

    `from_latent` used to return only hulls, and its fallback silently
    substituted a TRAINING HULL for the point that was asked for. The product
    consequence is precise: a slider move returns the same boat, badged as the
    requested design. Honesty rule 1 says a quantity carries its provenance;
    a decoded hull is a quantity.
    """

    projected: np.ndarray        # bool: the requested point was not feasible
    displacement: np.ndarray     # |delivered - requested| / box diagonal
    is_anchor: np.ndarray        # bool: an EXACT training hull came back
    t: np.ndarray                # blend fraction toward the anchor, 0 = asked

    @property
    def unprojected_rate(self) -> float:
        return float(1.0 - self.projected.mean())

    @property
    def anchor_rate(self) -> float:
        return float(self.is_anchor.mean())


@runtime_checkable
class HullGenerator(Protocol):
    """The drop-in slot. Anything satisfying this can replace the GMM.

    Deliberately excludes `fit`: construction is implementation-specific (the
    GMM wants `k`, a diffusion model wants steps and a schedule), which is
    exactly how `k` leaked into `ui/server.py`. Use `make_generator()`.
    """

    training_data: np.ndarray

    def sample(self, n: int, seed: int = ...) -> np.ndarray: ...

    def sample_conditioned(self, n: int, score_fn, percentile: float,
                           seed: int = ...) -> np.ndarray: ...

    def to_latent(self, X: np.ndarray) -> np.ndarray: ...

    def from_latent(self, uv: np.ndarray, return_info: bool = ...): ...

    def raw_feasibility(self, n: int = ..., seed: int = ...) -> float: ...


def make_generator(X: np.ndarray, kind: str = "gmm", seed: int = 0,
                   **kw) -> HullGenerator:
    """Factory — the seam the server calls so it never names a GMM knob.

    `kind` is the only implementation-specific word a caller has to say, and
    adding "diffusion" here is the whole of the drop-in.
    """
    if kind == "gmm":
        return HullFamilyModel.fit(X, seed=seed, **kw)
    if kind == "ppca":
        return PPCAGenerator.fit(X, seed=seed, **kw)
    raise ValueError(f"unknown generator kind {kind!r}; have 'gmm', 'ppca'")


# ---------------------------------------------------------------------------
# shared machinery
# ---------------------------------------------------------------------------

_BOX_DIAG = float(np.linalg.norm(grammar.HIGH - grammar.LOW))


def _pin_post_hoc(X: np.ndarray) -> np.ndarray:
    """Hold the post-hoc genes at their defaults in any RAW model draw.

    A MODEL CANNOT LEARN A DIMENSION ITS TRAINING DATA NEVER VARIED. The feed
    (`evaluate.sample_valid`) holds `grammar.POST_HOC_DEFAULTS` fixed so that a
    seeded population reproduces across an arity change, so those columns
    arrive with EXACTLY ZERO variance. What comes back out of a fitted
    covariance is then float noise of order 1e-17 — and three of those genes
    have a LOW bound of exactly 0.0, so a value of -1e-18 fails the bound check
    and the hull is refused for a rounding artefact.

    MEASURED 2026-08-24 at arity 21: GMM raw feasibility read 44.0% against a
    60% floor; pinning the five post-hoc columns returns it to 62.3%. Fitting
    on the core genes alone and padding scores 63.5%, i.e. the same number —
    which is the check that this is a rounding fix and not a thumb on the
    scale.

    The generative model is therefore measured on the space it was actually
    trained on. When a post-hoc gene gains real variance in the feed, this stops
    being a no-op and the model will learn it.

    THAT DAY CAME: 2026-08-27, the P1 exploring stream
    (`sample_valid(..., explore_post_hoc=True)`) gives every post-hoc
    column real variance, and PINNING would now DESTROY the signal the
    feed finally carries — the audit's finding #2 verbatim ("guarantees
    /generate can never emit a full-bowed hull, even if the feed is
    fixed"). The body is now a CLAMP to the gene bounds, which subsumes
    the original rounding fix: a -1e-18 on a zero-variance column clamps
    to its 0.0 LOW exactly as the pin did, while a learned 0.2 passes
    through untouched. Zero-variance feeds are bit-identical under it.
    """
    if X.ndim != 2 or X.shape[1] != grammar.N_PARAMS:
        return X
    out = np.array(X, dtype=float, copy=True)
    for name in grammar.POST_HOC_DEFAULTS:
        if name in grammar.NAMES:
            i = grammar.NAMES.index(name)
            out[:, i] = np.clip(out[:, i], grammar.LOW[i], grammar.HIGH[i])
    return out


def _refair_targets(X: np.ndarray) -> None:
    """Re-fair (Cp, lcb) into the bands the drawn fullness genes deliver.

    A Gaussian factorises what the corrected sac solve couples: a mixture
    fitted on the P1 exploring feed happily emits pmb 0.3 beside Cp 0.55,
    and `sac.target` refuses the pair — MEASURED 2026-08-27, GMM raw
    feasibility 43.2% against the 60% collapse floor the day the feed
    started varying the fullness genes. This is the same closed-form
    re-fairing every other generator path applies (`grammar`'s exploring
    stream, the optimizer's repair, `morphology_search._clip`): the model
    keeps its drawn SHAPE, and the two targets it cannot hold
    independently are projected onto the deliverable band — construction,
    not a softened gate; `grammar.check` still judges the result.
    """
    from .geometry import GeometryError, cp_band, lcb_band
    iC, iL = grammar.NAMES.index("Cp"), grammar.NAMES.index("lcb")
    ix = {n: grammar.NAMES.index(n)
          for n in ("LWL", "x_mb", "r_transom", "r_stem", "pmb")}
    # the deadrise LAW's own ordering (`deadrise.order`: beta_bow >=
    # beta_mid; the aft warp stays near the midship value) — a mixture
    # component happily inverts it, and re-imposing an ordering the law
    # itself defines is construction, not repair
    i_bm = grammar.NAMES.index("beta_mid")
    i_bb = grammar.NAMES.index("beta_bow")
    i_bt = grammar.NAMES.index("beta_transom")
    X[:, i_bb] = np.maximum(X[:, i_bb], X[:, i_bm])
    X[:, i_bt] = np.minimum(X[:, i_bt], X[:, i_bm] + 5.0)
    for row in X:
        try:
            b_lo, b_hi = cp_band(row[ix["LWL"]], row[ix["x_mb"]],
                                 row[ix["r_transom"]], row[ix["r_stem"]],
                                 row[ix["pmb"]])
            lo_c = max(b_lo + 1e-3, float(grammar.LOW[iC]))
            hi_c = min(b_hi - 1e-3, float(grammar.HIGH[iC]))
            if hi_c > lo_c:
                row[iC] = float(np.clip(row[iC], lo_c, hi_c))
            l_lo, l_hi = lcb_band(row[ix["LWL"]], row[ix["x_mb"]],
                                  row[ix["r_transom"]], float(row[iC]),
                                  row[ix["r_stem"]], row[ix["pmb"]])
            lo_l = max(l_lo + 1e-2, float(grammar.LOW[iL]))
            hi_l = min(l_hi - 1e-2, float(grammar.HIGH[iL]))
            if hi_l > lo_l:
                row[iL] = float(np.clip(row[iL], lo_l, hi_l))
        except (GeometryError, ValueError):
            continue                      # check() refuses it by name


def _project_to_feasible(rows: np.ndarray, X_train: np.ndarray,
                         n_coarse: int = 12, n_bisect: int = 8):
    """Blend each infeasible row toward its nearest training hull, minimally.

    THE OLD LOOP WAS `for t in np.linspace(0.1, 1.0, 10)`, and its last step IS
    the anchor — so the "success" branch could succeed by returning a training
    hull, and the `else` branch returned one outright. MEASURED on a 15x15
    latent grid at +-2.5 sigma (k=4, n=150): 5 of 225 decoded points came back
    as EXACT copies of a training hull, 2.2%, indistinguishable in the response
    from a hull that was actually designed.

    Two changes. The coarse scan starts below 0.1 and the first feasible t is
    then BISECTED, so the delivered hull is the closest feasible blend the
    method can find rather than the first one on a 10-step ladder. And what
    happened is REPORTED: `t`, the normalised displacement, and whether the
    anchor itself was returned.
    """
    out, projected, disp, anchor, ts = [], [], [], [], []
    for row in rows:
        if grammar.check(row).ok:
            out.append(row)
            projected.append(False)
            disp.append(0.0)
            anchor.append(False)
            ts.append(0.0)
            continue
        a = X_train[int(np.argmin(np.linalg.norm(X_train - row, axis=1)))]
        grid = np.linspace(0.0, 1.0, n_coarse + 1)[1:]
        t_ok, t_bad = 1.0, 0.0
        for t in grid:
            if grammar.check((1 - t) * row + t * a).ok:
                t_ok = float(t)
                break
            t_bad = float(t)
        for _ in range(n_bisect):        # tighten toward the feasible boundary
            mid = 0.5 * (t_bad + t_ok)
            if grammar.check((1 - mid) * row + mid * a).ok:
                t_ok = mid
            else:
                t_bad = mid
        cand = (1 - t_ok) * row + t_ok * a
        out.append(cand)
        projected.append(True)
        disp.append(float(np.linalg.norm(cand - row) / _BOX_DIAG))
        anchor.append(bool(t_ok >= 1.0 - 1e-9))
        ts.append(t_ok)
    return (np.array(out),
            DecodeInfo(np.array(projected, bool), np.array(disp, float),
                       np.array(anchor, bool), np.array(ts, float)))


def _conditioned(sampler, n: int, score_fn, percentile: float, seed: int,
                 batch: int, max_rounds: int, time_budget_s: float | None):
    """Reference batch sets a cut; DISJOINT candidate batches are filtered.

    `percentile` IS A STRICTNESS KNOB, and its old docstring ("keep draws whose
    score is in the best `percentile` of a reference batch") reads as a KEPT
    FRACTION, which is the opposite. The code computes
    `cut = quantile(ref, 1 - percentile)` and keeps `score <= cut`, so the kept
    fraction is `1 - percentile`: 0.0 keeps nothing but the best point, 0.85
    keeps the best 15%, 1.0 keeps everything. Higher = STRICTER = better hulls,
    fewer of them. Documented rather than renamed because the Gate-4 test and
    the UI both already pass 0.85 meaning "strict", so the code was right and
    the sentence was wrong.
    """
    import time as _time
    t0 = _time.perf_counter()
    ref = sampler(batch, seed + 1)
    cut = float(np.quantile(score_fn(ref), 1.0 - percentile))
    out: list[np.ndarray] = []
    best: list[tuple[float, np.ndarray]] = []
    s = seed + 1
    partial = False
    while len(out) < n:
        s += 1
        cand = sampler(batch, s)
        sc = np.asarray(score_fn(cand), float)
        for x, v in zip(cand, sc):
            best.append((float(v), x))
            if v <= cut and len(out) < n:
                out.append(x)
        if len(out) >= n:
            break
        over_time = (time_budget_s is not None
                     and _time.perf_counter() - t0 >= time_budget_s)
        if over_time or s - seed > max_rounds:
            # BEST-SO-FAR WITH A FLAG, NOT `raise RuntimeError`. A UI widget
            # that spins until it throws is worse than one that answers with
            # the best it found and says the search was cut short.
            partial = True
            best.sort(key=lambda p: p[0])
            for _v, x in best:
                if len(out) >= n:
                    break
                if not any(np.array_equal(x, o) for o in out):
                    out.append(x)
            break
    X = np.array(out[:n]) if out else np.empty((0, grammar.N_PARAMS))
    return X, {"cut": cut, "partial": partial or len(X) < n,
               "n_requested": n, "n_returned": len(X),
               "elapsed_s": _time.perf_counter() - t0}


# ---------------------------------------------------------------------------
# implementation 1: Gaussian mixture over feasible parameter vectors
# ---------------------------------------------------------------------------

@dataclass
class HullFamilyModel:
    means: np.ndarray        # (k, d)
    covs: np.ndarray         # (k, d, d)
    weights: np.ndarray      # (k,)
    pca_mean: np.ndarray
    pca_axes: np.ndarray     # (2, d) principal directions
    pca_scale: np.ndarray    # (2,) stddev along axes
    X_train: np.ndarray
    # EM provenance — an unconverged fit that reports nothing is a fit nobody
    # can audit.
    log_likelihood: float = float("nan")
    n_iter: int = 0
    converged: bool = False
    n_reseeded: int = 0
    n_dropped: int = 0

    @property
    def training_data(self) -> np.ndarray:      # HullGenerator
        return self.X_train

    # ---------- fitting ----------

    @staticmethod
    def fit(X: np.ndarray, k: int = 4, iters: int = 400, seed: int = 0,
            tol: float = 1e-7, restarts: int = 3,
            reg: float = 1e-6) -> "HullFamilyModel":
        """EM for a GMM, with a SCALE-AWARE floor, convergence, and pruning.

        Every one of those was missing and the flat floor is the one that bites.
        The regulariser was `1e-6 * I` on parameters spanning LWL in [4, 20] m
        down to rocker in [0, 0.6] — MEASURED per-dimension training variance
        ranges from 6.4e-3 to 122.7, a factor of 19,000 — so a single additive
        constant is simultaneously negligible on the long axes and dominant on the
        short ones. MEASURED at the shipped default (n=150, k=4) the smallest
        covariance eigenvalue was 6.2e-4 with a condition number of 2.7e5.
        The floor is now `reg * diag(cov(X))`: the same *relative* jitter on
        every axis, which is the only version that means anything.

        No convergence check (a fixed 60 iterations), no restarts, and no
        component pruning either. MEASURED at n=60: a full covariance in d=15
        needs at least d+1 = 16 points, and every component falls below that
        for k >= 8 (min responsibility mass 4.0 at k=8, 2.0 at k=16) — those
        components are rank-deficient and kept alive purely by the regulariser.
        A component that starves is now reseeded on a random data point, and a
        component that starves repeatedly is DROPPED, so `len(weights)` is the
        number of components the data actually supported, not the number asked
        for.
        """
        X = np.atleast_2d(np.asarray(X, float))
        n, d = X.shape
        if k > n:
            raise ValueError(f"k={k} components for n={n} points")
        base = np.cov(X.T) if n > 1 else np.eye(d)
        floor = reg * np.diag(np.maximum(np.diag(np.atleast_2d(base)), 1e-12))
        best = None
        for r in range(max(restarts, 1)):
            cand = _em(X, k, iters, seed + r, tol, base, floor)
            if best is None or cand[3] > best[3]:
                best = cand
        mu, cov, w, ll, it, conv, reseeded, dropped = best

        pca_mean = X.mean(0)
        Xc = X - pca_mean
        _u, s, vt = linalg.svd(Xc, full_matrices=False)
        axes = vt[:2]
        scale = s[:2] / np.sqrt(len(X))
        return HullFamilyModel(mu, cov, w, pca_mean, axes, scale, X,
                               log_likelihood=ll, n_iter=it, converged=conv,
                               n_reseeded=reseeded, n_dropped=dropped)

    # ---------- sampling ----------

    def _raw_draws(self, n: int, rng, clip: bool = True) -> np.ndarray:
        chol = [np.linalg.cholesky(c) for c in self.covs]
        d = self.means.shape[1]
        j = rng.choice(len(self.weights), size=n, p=self.weights)
        Z = rng.standard_normal((n, d))
        X = np.array([self.means[jj] + chol[jj] @ z for jj, z in zip(j, Z)])
        X = _pin_post_hoc(X)
        if clip:
            X = np.clip(X, grammar.LOW, grammar.HIGH)
            _refair_targets(X)
        return X

    def sample(self, n: int, seed: int = 0, max_tries: int = 400) -> np.ndarray:
        """Draw n L0-feasible hulls (GMM proposal + grammar gate)."""
        rng = np.random.default_rng(seed)
        out = []
        for _ in range(max_tries):
            for x in self._raw_draws(max(n, 32), rng):
                if grammar.check(x).ok:
                    out.append(x)
                    if len(out) == n:
                        return np.array(out)
        raise RuntimeError(f"generative sampler starved: {len(out)}/{n}")

    def sample_conditioned(self, n: int, score_fn, percentile: float,
                           seed: int = 0, batch: int = 64,
                           max_rounds: int = 200,
                           time_budget_s: float | None = None,
                           return_info: bool = False):
        """Performance-conditioned generation — see `_conditioned`.

        THE REFERENCE AND CANDIDATE BATCHES MUST BE DISJOINT. `ref` was drawn at
        seed+1 and the loop then incremented s from `seed` to seed+1, so the
        FIRST candidate batch was bit-identical to the batch that set the
        threshold. VERIFIED: np.array_equal(ref, cand0) was True, and a control
        ("score 64 plain draws, keep the best 10") reproduced this function's
        output exactly — 316.3 vs 316.3, 313.4 vs 313.4, 317.7 vs 317.7. It was
        selection dressed as conditioning, and the Gate 4 test would have passed
        for any sampler whatsoever.
        """
        X, info = _conditioned(lambda m, s: self.sample(m, seed=s), n, score_fn,
                               percentile, seed, batch, max_rounds,
                               time_budget_s)
        return (X, info) if return_info else X

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
        X = self._raw_draws(n, rng, clip=clip)
        return float(np.mean([grammar.check(x).ok for x in X]))

    # ---------- 2-D latent map ----------

    def to_latent(self, X: np.ndarray) -> np.ndarray:
        return (np.atleast_2d(X) - self.pca_mean) @ self.pca_axes.T / self.pca_scale

    def from_latent(self, uv: np.ndarray, return_info: bool = False):
        """Decode a 2-D map point back to the nearest feasible full vector.

        With `return_info=True` also returns a `DecodeInfo` saying, per point,
        whether the requested design was DELIVERED or SUBSTITUTED. See
        `_project_to_feasible` for the incident.
        """
        uv = np.atleast_2d(uv)
        x = self.pca_mean + (uv * self.pca_scale) @ self.pca_axes
        x = np.clip(x, grammar.LOW, grammar.HIGH)
        X, info = _project_to_feasible(x, self.X_train)
        return (X, info) if return_info else X


def _em(X: np.ndarray, k: int, iters: int, seed: int, tol: float,
        base: np.ndarray, floor: np.ndarray):
    """One EM run. Returns (mu, cov, w, loglik, n_iter, converged, reseed, drop)."""
    rng = np.random.default_rng(seed)
    n, d = X.shape
    mu = X[rng.choice(n, k, replace=False)].copy()
    cov = np.tile(np.atleast_2d(base) + floor, (k, 1, 1))
    w = np.full(k, 1.0 / k)
    alive = np.ones(k, bool)
    reseed_count = np.zeros(k, int)
    min_mass = d + 1                     # a full covariance in d needs d+1 points
    ll_prev, ll, it, converged = -np.inf, -np.inf, 0, False
    reseeded = 0
    for it in range(1, iters + 1):
        idx = np.flatnonzero(alive)
        logp = np.full((n, len(idx)), -np.inf)
        for c, j in enumerate(idx):
            logp[:, c] = np.log(w[j] + 1e-300) + _mvn_logpdf(X, mu[j], cov[j])
        tot = logsumexp(logp, axis=1)
        ll = float(tot.sum())
        r = np.exp(logp - tot[:, None])
        nk = r.sum(0)
        for c, j in enumerate(idx):
            if nk[c] < min_mass and alive.sum() > 1:
                # STARVED: fewer points than a full covariance in d needs.
                # Never drop the LAST component — a mixture with zero
                # components is not a more honest model, it is no model.
                if reseed_count[j] >= 2:
                    alive[j] = False       # tried twice, the data will not feed it
                    continue
                reseed_count[j] += 1
                reseeded += 1
                mu[j] = X[rng.integers(n)]
                cov[j] = np.atleast_2d(base) + floor
                w[j] = 1.0 / max(alive.sum(), 1)
                continue
            w[j] = nk[c] / n
            mu[j] = (r[:, c:c + 1] * X).sum(0) / nk[c]
            dxy = X - mu[j]
            cov[j] = (r[:, c:c + 1] * dxy).T @ dxy / nk[c] + floor
        live = np.flatnonzero(alive)
        w[live] = np.maximum(w[live], 1e-12)
        w[live] /= w[live].sum()
        if abs(ll - ll_prev) <= tol * max(abs(ll), 1.0):
            converged = True
            break
        ll_prev = ll
    live = np.flatnonzero(alive)
    ww = w[live] / w[live].sum()
    return (mu[live].copy(), cov[live].copy(), ww, ll, it, converged,
            reseeded, int(k - len(live)))


# ---------------------------------------------------------------------------
# implementation 2: the probabilistic-PCA latent, behind the same Protocol
# ---------------------------------------------------------------------------

@dataclass
class PPCAGenerator:
    """`navalai.latent.Genome` adapted to `HullGenerator`.

    It exists to prove the Protocol is an interface and not a description of
    one class: the Gate-4 suite is parametrised over both, so a claim like
    "conditioning beats the same-batch control" is a claim about the CONTRACT.
    It is also the incumbent the diffusion upgrade has to beat — MEASURED raw
    prior feasibility 89.4% against the GMM's 77.6%.
    """

    genome: object                     # navalai.latent.Genome
    X_train: np.ndarray = field(default=None)

    @property
    def training_data(self) -> np.ndarray:
        return self.genome.X_train

    @staticmethod
    def fit(X: np.ndarray, q: int = 8, seed: int = 0) -> "PPCAGenerator":
        from .latent import Genome
        return PPCAGenerator(Genome.fit(np.asarray(X, float), q=q))

    def sample(self, n: int, seed: int = 0, max_tries: int = 400) -> np.ndarray:
        rng = np.random.default_rng(seed)
        out = []
        for _ in range(max_tries):
            Z = rng.standard_normal((max(n, 32), self.genome.W.shape[1]))
            for x in self.genome.decode(Z, project=True):
                if grammar.check(x).ok:
                    out.append(x)
                    if len(out) == n:
                        return np.array(out)
        raise RuntimeError(f"ppca sampler starved: {len(out)}/{n}")

    def sample_conditioned(self, n: int, score_fn, percentile: float,
                           seed: int = 0, batch: int = 64,
                           max_rounds: int = 200,
                           time_budget_s: float | None = None,
                           return_info: bool = False):
        X, info = _conditioned(lambda m, s: self.sample(m, seed=s), n, score_fn,
                               percentile, seed, batch, max_rounds,
                               time_budget_s)
        return (X, info) if return_info else X

    def raw_feasibility(self, n: int = 2000, seed: int = 0) -> float:
        return self.genome.raw_prior_feasibility(n=n, seed=seed)

    def to_latent(self, X: np.ndarray) -> np.ndarray:
        """The 2-D MAP is the first two pPCA axes — same contract as the GMM's
        PCA map: `to_latent` returns exactly two coordinates."""
        return np.atleast_2d(self.genome.encode(X))[:, :2]

    def from_latent(self, uv: np.ndarray, return_info: bool = False):
        uv = np.atleast_2d(np.asarray(uv, float))
        Z = np.zeros((len(uv), self.genome.W.shape[1]))
        Z[:, :2] = uv
        X = np.clip(self.genome.decode(Z, project=False),
                    grammar.LOW, grammar.HIGH)
        Xp, info = _project_to_feasible(X, self.genome.X_train)
        return (Xp, info) if return_info else Xp


def _mvn_logpdf(X: np.ndarray, mu: np.ndarray, cov: np.ndarray) -> np.ndarray:
    d = X.shape[1]
    c, low = linalg.cho_factor(cov, lower=True)
    diff = X - mu
    sol = linalg.cho_solve((c, low), diff.T).T
    logdet = 2.0 * np.log(np.diag(c)).sum()
    return -0.5 * (d * np.log(2 * np.pi) + logdet + np.einsum("ij,ij->i", diff, sol))
