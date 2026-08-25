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

import math
import warnings
from dataclasses import dataclass, field

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize, minimize_scalar


# ARD lengthscale search box, on the NORMALISED input cube [0, 1]^d, declared
# once because two places used to need it and only one of them had it: the
# optimiser bound inside `GP.fit` and the saturation test that reads the
# fitted result back. When those two disagree the test either never fires or
# always does, which is this codebase's number-declared-twice defect aimed at
# the guard rather than at the physics.
#
# The BOX ITSELF IS NOT THE DEFECT and it is not being widened here. An upper
# bound of 10 on a unit cube already means "this axis is effectively flat", and
# raising it only moves where the optimiser stops. The defect (gap A6c) is that
# stopping there was SILENT.
ARD_LENGTHSCALE_BOUNDS = (1e-2, 10.0)

# How close to a bound counts as ON it. L-BFGS-B returns the bound exactly when
# it clips, so this is a float-equality guard with slack, not a tolerance band.
_LS_BOUND_REL_TOL = 1e-6


class ARDSaturation(UserWarning):
    """One or more ARD lengthscales stopped on the edge of the search box.

    NOT an error: an upper-bound lengthscale is how ARD says "this input does
    not matter", which is a legitimate and often correct answer. It is a
    WARNING because the same state also says the kernel — and therefore the
    predictive sigma — is blind along that axis, and until 2026-08-12 nothing
    in this module said so out loud. `_nn_distance` is unweighted precisely
    because of this (see its docstring), so the support half of the OOD test
    already survives it; the sigma half does not, and a caller that does not
    know cannot compensate.
    """


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
    sigma test already looks through, and they saturate. RE-MEASURED 2026-08-13
    on the 16-parameter genome, and the count depends on the TRAINING SET, so
    the configuration is stated rather than a single number quoted:

        sample_valid(250, seed=7), full box   3 of 16: D, beta_len, sheer_rise
        the beta_mid >= 12 subset, 109 rows   6 of 16: lcb, r_transom,
                                              beta_bow, beta_len, flare,
                                              sheer_rise

    (The superseded reading was "two of the fifteen ... trained on 100 L1
    hulls" — a 15-parameter genome that no longer exists.) The kernel — and
    therefore sigma — is blind to those axes entirely. A support test that
    divides by
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
    # Which ARD lengthscales stopped ON the search box, and which end (gap A6c).
    # ((dim_index, "upper" | "lower"), ...) — empty when the fit is interior.
    # A field and not a recomputation, because the bounds that produced it are
    # the ones that must judge it.
    ls_at_bound: tuple[tuple[int, str], ...] = field(default=())
    #: Boolean mask over the FULL input width: which columns actually varied in
    #: training. Constant columns are dropped before fitting (see `fit`), and
    #: `_norm` re-applies the mask so callers keep passing full-width vectors.
    active: np.ndarray | None = field(default=None)
    #: The value each DROPPED (constant) column held in training, full width.
    #: Kept so `denormalise` can hand a caller back a vector in the coordinate
    #: system it passed in, rather than in the reduced one the kernel uses.
    const_values: np.ndarray | None = field(default=None)

    @property
    def prior_var(self) -> float:
        return self.var

    @staticmethod
    def fit(X: np.ndarray, y: np.ndarray, nugget: float = 1e-8,
            restarts: int = 3, seed: int = 0) -> "GP":
        X = np.atleast_2d(np.asarray(X, float))
        y = np.asarray(y, float)
        n, _d_full = X.shape
        # A CONSTANT COLUMN IS NOT A DIMENSION. It carries no information, and
        # an ARD length-scale fitted to it is a free parameter the optimiser
        # must still search — L-BFGS-B over d+1 hyperparameters in a harder
        # space, for nothing.
        #
        # MEASURED 2026-08-24. `evaluate.sample_valid` holds the post-hoc genes
        # at their defaults so a seeded population survives an arity change, so
        # five of the twenty-one columns arrive with EXACTLY zero variance. The
        # GP's median relative error went to 0.835 for wh_per_nm and 2.018 for
        # gm — and `scripts/make_baseline.py` then refused to write ANY
        # quantity, leaving `data/baselines.json` holding nothing but its own
        # README. Restricting the fit to the columns that actually vary is the
        # fix; the normaliser already zeroed them, but the optimiser was still
        # paying for them.
        _span_full = X.max(0) - X.min(0)
        active = _span_full > 1e-12
        if not active.any():                     # degenerate: keep one column
            active = np.zeros(_d_full, bool)
            active[0] = True
        const_full = X.min(0)          # for a constant column this IS its value
        X = X[:, active]
        d = int(active.sum())
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
        ls_lo, ls_hi = ARD_LENGTHSCALE_BOUNDS
        bounds = ([(np.log(ls_lo), np.log(ls_hi))] * d
                  + [(np.log(1e-8), np.log(0.5))])
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

        # THE HYPERPARAMETER THAT STOPPED ON ITS BOUND IS NOW REPORTED (gap
        # A6c). RE-MEASURED 2026-08-13 on the Gate 3 production GP —
        # `sample_valid(250, MissionSpec(), seed=7)`, log(Wh/NM), seed=1 —
        # THREE of the SIXTEEN lengthscales come back at exactly 10.0000, the
        # optimiser's ceiling: `D`, `beta_len` and `sheer_rise`.
        #
        # The superseded reading was "ONE of the fifteen, `x_mb`". Both halves
        # of that changed: the genome went 15 -> 16 parameters, and `x_mb`
        # STOPPED saturating while three other axes started. So the specific
        # axis named here is not durable and the COUNT is not either — what is
        # durable is that saturation happens and must be reported. That is the
        # kernel declaring itself blind to those axes, and the module printed,
        # returned and recorded
        # nothing about it: the surrogate's own predictive sigma cannot see a
        # query that moves only along x_mb, and every caller was told the fit
        # succeeded. An unmeasured value must never be scored as a passing one;
        # here the value WAS measured, by the optimiser, and then dropped.
        at_bound = tuple(
            (int(i), "upper" if ls[i] >= ls_hi * (1.0 - _LS_BOUND_REL_TOL)
             else "lower")
            for i in range(d)
            if ls[i] >= ls_hi * (1.0 - _LS_BOUND_REL_TOL)
            or ls[i] <= ls_lo * (1.0 + _LS_BOUND_REL_TOL))
        gp = GP(Xn, y, ls, var0, nugget, mu, c, a, x_lo, span, d_support,
                at_bound, active, const_full)
        if at_bound:
            warnings.warn(gp.saturation_report(), ARDSaturation, stacklevel=2)
        return gp

    def saturation_report(self) -> str:
        """What saturated, which end, and what it costs the caller.

        Returns "" when the fit is interior, so `if gp.saturation_report():`
        is the whole test. It reports the CONSEQUENCE and not just the fact,
        because "lengthscale 7 is at 10.0" is not actionable and "sigma is
        blind along input 7" is.
        """
        if not self.ls_at_bound:
            return ""
        lo, hi = ARD_LENGTHSCALE_BOUNDS
        parts = []
        for i, end in self.ls_at_bound:
            if end == "upper":
                parts.append(
                    f"input {i} lengthscale {self.ls[i]:.4g} == upper bound "
                    f"{hi:g}: the kernel treats this axis as flat, so the "
                    f"predictive sigma is blind to it")
            else:
                parts.append(
                    f"input {i} lengthscale {self.ls[i]:.4g} == lower bound "
                    f"{lo:g}: the kernel has degenerated to noise on this "
                    f"axis, so predictions along it are the prior mean")
        return (f"{len(self.ls_at_bound)} of {len(self.ls)} ARD lengthscales "
                f"stopped on the search box: " + "; ".join(parts)
                + ". The support half of is_ood() is unaffected "
                  "(_nn_distance is unweighted, deliberately); the sigma half "
                  "is not.")

    def _norm(self, X: np.ndarray) -> np.ndarray:
        Xa = np.atleast_2d(np.asarray(X, float))
        act = getattr(self, "active", None)
        if act is not None and Xa.shape[1] == act.size:
            Xa = Xa[:, act]
        return (Xa - self.x_lo) / self.x_hi

    def denormalise(self, Xn: np.ndarray) -> np.ndarray:
        """Normalised ACTIVE rows -> full-width inputs in the caller's units.

        `self.X` holds the reduced, normalised training matrix because that is
        what the kernel needs. A caller reconstructing training points must not
        have to know that: MEASURED 2026-08-24, `gp.X * gp.x_hi + gp.x_lo` gave
        16 columns against a 21-column probe and the vstack raised. Constant
        columns are restored from the value they held in training, which is
        exact — that is what made them constant.
        """
        Xn = np.atleast_2d(np.asarray(Xn, float))
        real = Xn * self.x_hi + self.x_lo
        if self.active is None or self.const_values is None:
            return real
        out = np.repeat(np.asarray(self.const_values, float)[None, :],
                        len(Xn), axis=0)
        out[:, self.active] = real
        return out

    def predict(self, X: np.ndarray):
        Xn = self._norm(X)
        k = self.var * _rbf(Xn, self.X, self.ls)
        mean = self.mu + k @ self._alpha
        # The learned noise belongs in the PREDICTIVE variance too, or the
        # band still collapses at the data even after learning it.
        v = (self.var * (1.0 + self.nugget)
             - np.einsum("ij,ji->i", k, cho_solve(self._chol, k.T)))
        return mean, np.sqrt(np.maximum(v, 1e-14))

    def posterior_cov(self, X: np.ndarray) -> np.ndarray:
        """FULL joint posterior covariance at X, not just its diagonal.

        The co-kriging likelihood needs this one. A GP's extrapolation error is
        a smooth function reverting to the prior mean, so it is strongly
        CORRELATED between neighbouring query points; treating it as
        independent per-point noise overstates how much independent information
        those points carry and over-penalises the term it multiplies. MEASURED:
        the diagonal form drove rho to exactly 0.0000 on three of the
        narrow-LF cases in `CoKriging.fit`'s table — the register's own failure
        mode, reproduced by the fix meant to remove it.
        """
        Xn = self._norm(X)
        k = self.var * _rbf(Xn, self.X, self.ls)
        C = self.var * _rbf(Xn, Xn, self.ls) - k @ cho_solve(self._chol, k.T)
        return 0.5 * (C + C.T)

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


class RhoDegenerate(RuntimeWarning):
    """rho was selected at a value that makes the co-kriging model a lie.

    Two shapes, both MEASURED (see `CoKriging.fit`):
      - |rho| below `rho_floor`: `predict` is then `0 * m_lo + m_delta`, i.e.
        single-fidelity kriging on the high-fidelity points, while the object
        still calls itself CoKriging and still carries a low-fidelity GP that
        contributes nothing. Silently discarding the cheap model is the one
        outcome a multi-fidelity method must never do quietly.
      - the optimum sits ON a scan endpoint: the scan did not bracket it, so
        the reported rho is a boundary artefact, not an estimate.
    """


@dataclass
class CoKriging(_Escalates):
    """Kennedy-O'Hagan AR(1): f_hi = rho * f_lo + delta."""

    gp_lo: GP
    gp_delta: GP
    rho: float
    # Selection diagnostics — recorded on the object because a scalar rho with
    # no provenance is exactly what let rho = -0.64 pass unnoticed.
    nll: float = float("nan")            # joint KOH negative log-likelihood
    lf_hf_corr: float = float("nan")     # Pearson corr(m_lo(X_hi), y_hi)
    loo_rmse: float = float("nan")       # of the selected delta-GP
    rho_evidence: float = float("nan")   # nats of nll(rho=0) - nll(rho_hat)
    rho_scan: tuple = ()                 # (lo, hi) of the final scan bracket
    rho_warning: str = ""                # "" when the fit is clean

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
            X_hi: np.ndarray, y_hi: np.ndarray, seed: int = 0,
            n_scan: int = 25, refine: int = 12, rho_floor: float = 0.05,
            rho_max: float = 50.0, min_evidence: float = 2.0,
            strict: bool = False) -> "CoKriging":
        """Fit the AR(1) pair, selecting rho by the JOINT KOH LOG-LIKELIHOOD.

        IT USED TO MINIMISE THE DELTA-GP'S *ABSOLUTE* LEAVE-ONE-OUT RMSE, and
        the comment beside it claimed that was "the KOH MLE spirit". It is not:
        LOO-RMSE carries the units of delta, so the criterion is minimised by
        whatever rho makes the residual SMALL, not by whatever rho makes the
        residual most LIKELY under its own fitted covariance. A magnitude
        minimiser is not an estimator, and it behaved like one.

        MEASURED, LF = `forrester_lo` (an EXACT AR(1) partner with
        rho_true = 2.0, so the right answer is known to the last digit):

            n_hi   old (LOO-RMSE)   new (KOH NLL)
              6        1.9337           1.9955
              8        2.0401           1.9996
             10        2.0018           2.0001
             12        1.9773           1.9997
             15        1.9509           1.9999
             20        1.9210           2.0001
             25        1.9009           2.0013

        The old column is NON-MONOTONE and then walks steadily AWAY from 2.0 as
        data is added — the one thing an estimator may never do. More data made
        it worse because more high-fidelity points give delta more room to be
        small somewhere other than the truth. Worst error 0.0991 against 0.0045.

        Worse, MEASURED on a broad-HF / narrow-LF case (LF on [0, 0.3], HF on
        [0, 1], the situation every real campaign is in, since the cheap model
        is run where the expensive one has not been):

            LF span   n_hi   old rho
            [0, 0.3]    12   -0.6422
            [0, 0.4]    12   -0.7209
            [0, 0.35]   16   -0.4281
            [0, 0.3]    20   +0.3045

        A NEGATIVE rho on a low-fidelity model that is a positively-correlated
        half of the truth means the fit is subtracting the cheap model, and at
        +0.30 it is discarding three-quarters of it. Either way the object
        still reports itself as co-kriging and emits no diagnostic at all.

        The criterion here is the marginal likelihood of the high-fidelity data
        under the KOH model (`_koh_nll`), and it carries the term that fixes
        the case above: the low-fidelity mean at X_hi is itself a PREDICTION,
        so `rho^2 * Sigma_lo(X_hi)` joins the covariance. Where the LF GP is
        extrapolating that is large and the likelihood declines to lean on it
        rather than inverting its sign. `Sigma_lo` is the FULL posterior
        covariance, not its diagonal — the diagonal form drove rho to exactly
        0.0000 on three narrow-LF cases, reproducing the very failure it was
        added to remove (see `GP.posterior_cov`).

        The bracket is re-centred and doubled while the optimum sits on an end
        (up to 3 times), then golden-section-refined. What is left over is
        RECORDED, not swallowed: `rho_warning` is non-empty and a
        `RhoDegenerate` warning is raised when

          - |rho| < `rho_floor`, i.e. the low-fidelity model is being discarded;
          - the optimum still sits on a scan endpoint after four expansions;
          - `rho_evidence` — nll(rho=0) minus nll(rho_hat), in nats — is below
            `min_evidence`, i.e. the fit cannot beat single-fidelity kriging
            and the value of rho is whatever the noise preferred. MEASURED with
            an LF model replaced by white noise: rho lands anywhere from -2.36
            to +4.02 across five seeds and buys 0.06 to 0.96 nats.

        Pass `strict=True` to make those a refusal instead of a warning.
        """
        X_hi = np.atleast_2d(np.asarray(X_hi, float))
        y_hi = np.asarray(y_hi, float)
        gp_lo = GP.fit(X_lo, y_lo, seed=seed)
        m_lo_at_hi, _s = gp_lo.predict(X_hi)
        cov_lo_at_hi = gp_lo.posterior_cov(X_hi)
        mc = m_lo_at_hi - m_lo_at_hi.mean()
        rho0 = float(np.dot(mc, y_hi - y_hi.mean()) / max(np.dot(mc, mc), 1e-12))
        yc = y_hi - y_hi.mean()
        corr = float(np.dot(mc, yc)
                     / max(np.sqrt(np.dot(mc, mc) * np.dot(yc, yc)), 1e-300))

        # A CONSTANT low-fidelity mean makes rho structurally unidentifiable:
        # `rho * const` is absorbed by the delta-GP's own mean, so the
        # likelihood is FLAT in rho and rho0 divides by ~0. MEASURED on an LF
        # model that is a constant plus 1e-6 noise: the scan ran out to
        # rho = 2,378,233.8, which then multiplies s_lo into the predictive
        # sigma and makes every query out of support. Named and handled.
        if float(np.std(mc)) <= 1e-6 * max(float(np.std(y_hi)), 1e-300):
            msg = (f"the low-fidelity mean is CONSTANT over the high-fidelity "
                   f"points (std {np.std(mc):.3g}); rho is not identifiable "
                   f"and is set to 0 — this model is single-fidelity kriging")
            if strict:
                raise ValueError("co-kriging refused: " + msg)
            warnings.warn(msg, RhoDegenerate, stacklevel=2)
            gp_d = GP.fit(X_hi, y_hi, seed=seed + 1, restarts=1)
            return CoKriging(gp_lo, gp_d, 0.0,
                             nll=_koh_nll(gp_d, cov_lo_at_hi, 0.0),
                             lf_hf_corr=corr, loo_rmse=float(_loo_error(gp_d)),
                             rho_evidence=0.0, rho_scan=(0.0, 0.0),
                             rho_warning=msg)

        cache: dict[float, tuple[float, GP]] = {}

        def score(rho: float) -> tuple[float, GP]:
            r = round(float(rho), 12)
            if r not in cache:
                gp_d = GP.fit(X_hi, y_hi - r * m_lo_at_hi,
                              seed=seed + 1, restarts=1)
                cache[r] = (_koh_nll(gp_d, cov_lo_at_hi, r), gp_d)
            return cache[r]

        span = max(abs(rho0), 0.5) * 1.5
        lo, hi = max(rho0 - span, -rho_max), min(rho0 + span, rho_max)
        on_edge = False
        for _expand in range(4):
            grid = np.linspace(lo, hi, n_scan)
            vals = [score(r)[0] for r in grid]
            j = int(np.argmin(vals))
            on_edge = j in (0, n_scan - 1)
            if not on_edge:
                break
            # the optimum is outside the bracket: re-centre on it and double
            centre, span = float(grid[j]), (hi - lo)
            lo = max(centre - span, -rho_max)
            hi = min(centre + span, rho_max)

        # golden-section refinement inside the bracketing triple
        a = float(grid[max(j - 1, 0)])
        b = float(grid[min(j + 1, n_scan - 1)])
        gr = 0.5 * (np.sqrt(5.0) - 1.0)
        c, d = b - gr * (b - a), a + gr * (b - a)
        for _ in range(max(refine, 0)):
            if score(c)[0] < score(d)[0]:
                b, d = d, c
                c = b - gr * (b - a)
            else:
                a, c = c, d
                d = a + gr * (b - a)
        best_rho = min(list(cache), key=lambda r: cache[r][0])
        best_nll, best_gp = cache[best_rho]
        # How much the low-fidelity model is WORTH, in nats: the likelihood
        # ratio of the fitted rho against rho = 0, which IS single-fidelity
        # kriging on the HF points. A co-kriging model that cannot beat that is
        # a co-kriging model with nothing to co-krige.
        evidence = float(score(0.0)[0] - best_nll)

        notes = []
        if on_edge:
            notes.append(
                f"rho={best_rho:.4f} sits on a scan endpoint after 4 bracket "
                f"expansions ([{lo:.3f}, {hi:.3f}]) — this is a boundary "
                f"artefact, not an estimate")
        if abs(best_rho) < rho_floor:
            notes.append(
                f"rho={best_rho:.4f} is below the floor {rho_floor}: the "
                f"low-fidelity model contributes nothing and this object is "
                f"single-fidelity kriging wearing a co-kriging name "
                f"(LF/HF correlation {corr:+.3f})")
        if evidence < min_evidence:
            notes.append(
                f"rho is NOT IDENTIFIED: the fitted rho={best_rho:.4f} beats "
                f"rho=0 by only {evidence:.2f} nats against a bar of "
                f"{min_evidence} (LF/HF correlation {corr:+.3f}). The "
                f"low-fidelity data carries no usable information about the "
                f"high-fidelity function here, and the value of rho is "
                f"whatever the noise preferred")
        msg = "; ".join(notes)
        if msg:
            if strict:
                raise ValueError("co-kriging refused: " + msg)
            warnings.warn(msg, RhoDegenerate, stacklevel=2)
        return CoKriging(gp_lo, best_gp, float(best_rho),
                         nll=float(best_nll), lf_hf_corr=corr,
                         loo_rmse=float(_loo_error(best_gp)),
                         rho_evidence=evidence,
                         rho_scan=(float(lo), float(hi)), rho_warning=msg)

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


def _koh_nll(gp_delta: GP, cov_lo_at_hi: np.ndarray, rho: float) -> float:
    """Negative log marginal likelihood of y_hi under the KOH AR(1) at `rho`.

        y_hi ~ N(rho*m_lo(X_hi) + mu_delta,  rho^2 * Sigma_lo(X_hi) + K_delta)

    The low-fidelity mean fed into `delta = y_hi - rho * m_lo` is a PREDICTION,
    not data. A criterion that treats it as data leans on the LF model exactly
    where the LF model is guessing, which is how the old rule ended up choosing
    a NEGATIVE rho against a positively-correlated LF partner. `Sigma_lo` is
    the FULL posterior covariance for the reason recorded on
    `GP.posterior_cov`.

    delta is a deterministic shift of y_hi given the LF GP, so the Jacobian is
    1 and this is exactly log p(y_hi | rho) up to the rho-free LF factor of the
    joint — i.e. maximising it maximises the joint KOH likelihood in rho.

    THE PROCESS VARIANCE IS PROFILED, and that is not a detail. `GP.fit` pins
    `var` to the EMPIRICAL variance of its labels, so at a fixed var the whole
    scale dependence of the likelihood collapses into `(n/2) log var(delta)` —
    which is a monotone function of |delta| and reinstates the exact
    residual-magnitude criterion this rewrite exists to remove. MEASURED on the
    4-point Forrester case (rho_true = 2.0): at fixed var the profile bottomed
    at rho = 0.98 (delta small and wiggly) instead of 2.0 (delta LARGE and
    perfectly linear, hence very likely under a smooth GP). Profiling var over
    the correlation matrix lets smoothness pay for magnitude, which is what a
    likelihood is for.
    """
    n = len(gp_delta.X)
    R = (_rbf(gp_delta.X, gp_delta.X, gp_delta.ls)
         + (gp_delta.nugget + 1e-10) * np.eye(n))
    S = (rho * rho) * np.asarray(cov_lo_at_hi, float)
    yc = gp_delta.y - gp_delta.mu
    const = 0.5 * n * np.log(2.0 * np.pi)

    def nll(log_v: float) -> float:
        K = np.exp(log_v) * R + S
        try:
            c = cho_factor(K, lower=True)
        except np.linalg.LinAlgError:
            return 1e12
        return float(0.5 * yc @ cho_solve(c, yc)
                     + np.log(np.diag(c[0])).sum() + const)

    v0 = np.log(max(float(gp_delta.var), 1e-300))
    res = minimize_scalar(nll, bounds=(v0 - 25.0, v0 + 10.0), method="bounded")
    return float(min(res.fun, nll(v0)))


def expected_improvement(gp, X: np.ndarray, y_best: float) -> np.ndarray:
    """EI for minimisation — the batched-infill acquisition (BuildPlan 1.2)."""
    from scipy.stats import norm
    m, s = gp.predict(X)
    s = np.maximum(s, 1e-12)
    z = (y_best - m) / s
    return (y_best - m) * norm.cdf(z) + s * norm.pdf(z)


class InfillStarved(RuntimeError):
    """`batch_infill` could not honour k under the diversity constraint.

    It used to return a short array and say nothing. A batch method whose whole
    reason to exist is "run k expensive simulations at once instead of one per
    cycle" cannot silently deliver fewer than k: the caller sizes a compute
    budget on k, and MEASURED it asked for 60 and got 51 with no signal.
    """

    def __init__(self, message: str, chosen: np.ndarray, k: int):
        super().__init__(message)
        self.chosen = chosen
        self.k = k


def batch_infill(gp, candidates: np.ndarray, y_best: float, k: int,
                 min_dist: float = 0.05, bounds: tuple | None = None,
                 strict: bool = True) -> np.ndarray:
    """Pick k EI-ranked candidates with mutual distance (batched, not 1/cycle).

    `min_dist` is a EUCLIDEAN distance in the CANDIDATE BOX normalised to the
    unit cube — each axis is rescaled onto [0, 1] by the box, and the bar is
    applied to the NORM of the difference, not per axis. The box is the right
    reference (it is the only one the caller can reason about); it used to be
    the GP's TRAINING span — `gp._norm` — and that is the span of the few
    high-fidelity points already run, not of the region being searched.

    READ THE UNITS BEFORE SETTING IT: THE BAR DOES NOT MEAN WHAT IT MEANS IN 1-D.
    This docstring said "a fraction of the candidate box PER AXIS", and in one
    dimension those are the same sentence — which is why the 1-D table below is
    honest and the design-space case was not covered at all. In d dimensions the
    norm accumulates d independent gaps, so a request that reads like "5% apart
    on every axis" is satisfied by points that are 5%/sqrt(d) apart on one axis
    and nearly coincident on the rest. MEASURED in the 15-D grammar box, k=5
    from 400 uniform candidates:

        min_dist requested   picks change?   min PER-AXIS gap   min EUCLIDEAN gap
              0.05               —               0.00121             1.1945
              0.10           identical           0.00121             1.1945
              0.20           identical           0.00121             1.1945
              0.50           identical           0.00121             1.1945
              1.00           identical           0.00121             1.1945
              1.50             changed           0.00172             1.5202
              2.00           k drops to 3        0.00984             2.0133

    The same five points are returned for every request from 0.05 to 1.00: the
    bar is INERT over a twentyfold range, because random points in a 15-cube are
    already ~1.2 apart in norm. Two picks 0.0012 of an axis apart — a tenth of a
    millimetre of beam — are billed as two experiments and the filter says
    nothing. The bar first binds between 1.0 and 1.5, and by 2.0 it starves the
    batch.

    So `min_dist=0.05` is a real constraint in 1-D and a no-op in 15-D. Scale it
    with the dimension (sqrt(d) x the per-axis separation you actually want:
    ~0.19 for 5% per axis in 15-D, and note that is still a NORM, so it does not
    forbid two picks agreeing closely on one axis). This is documented rather
    than changed: switching to a per-axis (Chebyshev) test would silently alter
    every caller's batch, and no measurement has been made of what that does to
    infill quality. The behaviour is Euclidean; the sentence now says so.

    The two spans are different by construction (you infill where you have NOT
    been), and the error is in the dangerous direction: a small training span
    INFLATES every normalised distance, so the diversity filter passes
    everything and the batch collapses onto the EI peak. MEASURED, HF points
    drawn on [0.40, 0.55], candidates on [0, 1], min_dist 0.05, k=5:

        n_candidates   picks                              min gap
                 21    0.25 0.30 0.35 0.65 0.70            0.0500
                 51    0.34 0.36 0.38 0.64 0.66            0.0200
                101    0.36 0.37 0.63 0.64 0.65            0.0100
                201    0.36 0.37 0.63 0.64 0.65            0.0100

    The requested separation is 0.05 and the delivered separation falls to the
    candidate grid spacing — the filter is not filtering, it is rounding. Five
    CFD runs at 0.36, 0.37, 0.63, 0.64, 0.65 is two experiments billed as five.
    Note the failure HIDES at coarse candidate grids: at 21 candidates the grid
    itself enforces 0.05, so a test written on a coarse grid passes.

    `bounds=(lo, hi)` overrides the inferred box for the case where the
    candidate set is a sample rather than a grid and does not span the design
    space. Short batches raise `InfillStarved` unless `strict=False`.
    """
    C = np.atleast_2d(np.asarray(candidates, float))
    if bounds is None:
        lo, hi = C.min(0), C.max(0)
    else:
        lo, hi = np.asarray(bounds[0], float), np.asarray(bounds[1], float)
    span = np.where(hi - lo < 1e-12, 1.0, hi - lo)
    Xn = (C - lo) / span

    ei = expected_improvement(gp, C, y_best)
    order = np.argsort(-ei)
    chosen: list[int] = []
    for idx in order:
        if len(chosen) == k:
            break
        if all(np.linalg.norm(Xn[idx] - Xn[j]) > min_dist for j in chosen):
            chosen.append(int(idx))
    out = np.array(chosen, dtype=int)
    if len(out) < k and strict:
        raise InfillStarved(
            f"asked for {k} infill points at min_dist {min_dist} (normalised "
            f"EUCLIDEAN, in {C.shape[1]}-D) but only {len(out)} survive the "
            f"diversity filter. "
            f"Widen the candidate set, lower min_dist, or pass strict=False "
            f"and size the compute budget on len(result) — a short batch "
            f"returned silently is a compute plan that quietly shrinks.",
            out, k)
    return out


# ---------------------------------------------------------------------------
# CALIBRATION (gap I5)
#
# Until 2026-08-12 the entire calibration evidence for this module was ONE
# assertion, `within >= 0.75`, on a 2-sigma band whose nominal coverage is
# 0.9545. A single point on the coverage curve cannot tell "the band is too
# wide in the middle" from "the tails are wrong", and it is trivially GAMEABLE:
# any model reaches any coverage target by inflating sigma. That is why
# `sharpness` is here and why `calibration` returns it beside the error --
# this codebase has already shipped one bar a degenerate answer passed
# (`gci <= 5.0` being true of -27%), and a coverage figure with no sharpness
# beside it is the same offer.
#
# These are DIAGNOSTICS, deliberately not gates. No bar is asserted here, and
# no bar derived from them is added to `flywheel`'s ratchet in this change: a
# threshold interpolated from the 0.75 that is already known to be the wrong
# statistic would be a guess wearing a number (LESSONS defect class 3). They
# measure; the bars come after someone has looked at what they measure.
# ---------------------------------------------------------------------------

# Nominal central-interval levels the coverage curve is reported at. Declared
# once because the curve, its summary error and every test read the same list;
# 0.9545 is included because it is the 2-sigma level the old single assertion
# was really asking about, and having it in the curve is what makes the old
# number comparable to the new one.
COVERAGE_LEVELS = (0.50, 0.80, 0.90, 0.9545, 0.99)

# Standard-normal quantiles for COVERAGE_LEVELS, i.e. z such that
# P(|Z| <= z) = level. Derived, not typed: a table of z-values beside a table
# of levels is a number declared twice and they drift.
_SQRT2 = math.sqrt(2.0)


def _z_for(level: float) -> float:
    """z with P(|Z| <= level) — the inverse of erf, by bisection.

    scipy.stats is not imported anywhere else in this module and this is two
    lines; `math.erf` is in the standard library and monotone, so bisection is
    exact to float precision in ~60 steps.
    """
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if math.erf(mid / _SQRT2) < level:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _mean_sigma(model, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean, sig = model.predict(np.atleast_2d(np.asarray(X, float)))
    return np.asarray(mean, float).ravel(), np.asarray(sig, float).ravel()


def pit_values(model, X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Probability-integral transform of the observations under the posterior.

    `PIT_i = Phi((y_i - mean_i) / sigma_i)`. If the predictive distribution is
    right, these are Uniform(0, 1); a U-shape means the bands are too NARROW, a
    peak in the middle means too WIDE, and a shifted mass means BIAS. It is the
    only one of these diagnostics that sees dispersion and bias at once, which
    is why it is first.

    `y` is in the model's OWN target space. The L1 surrogate is fitted on
    log(Wh/NM), so a caller holding raw Wh/NM must pass `np.log(y)` -- the same
    space `_metrics` and the coverage assertions use. Mixing the two produces a
    PIT that is uniformly wrong and looks like a calibration failure.
    """
    mean, sig = _mean_sigma(model, X)
    yv = np.asarray(y, float).ravel()
    if yv.shape != mean.shape:
        raise ValueError(
            f"pit_values: {yv.size} targets against {mean.size} predictions")
    bad = ~np.isfinite(sig) | (sig <= 0.0)
    if bad.any():
        # An unmeasurable calibration point is REFUSED, not scored as 0.5.
        raise ValueError(
            f"pit_values: {int(bad.sum())} of {sig.size} predictive sigmas are "
            f"non-positive or non-finite, so the PIT is undefined there. A "
            f"model that cannot state its own band cannot be calibrated.")
    z = (yv - mean) / sig
    return 0.5 * (1.0 + np.array([math.erf(v / _SQRT2) for v in z]))


def coverage_curve(model, X: np.ndarray, y: np.ndarray,
                   levels=COVERAGE_LEVELS) -> dict[float, float]:
    """Empirical coverage of the central interval at each NOMINAL level.

    `{0.50: 0.44, 0.80: 0.72, ...}`. A perfectly calibrated model returns the
    identity. Computed from the PIT so the curve and `pit_values` cannot
    disagree about what the model said.
    """
    p = pit_values(model, X, y)
    out: dict[float, float] = {}
    for lv in levels:
        lo, hi = 0.5 * (1.0 - lv), 0.5 * (1.0 + lv)
        out[float(lv)] = float(np.mean((p >= lo) & (p <= hi)))
    return out


def sharpness(model, X: np.ndarray) -> float:
    """Mean predictive sigma over X, in the model's target space.

    Reported WITH coverage, never instead of it and never after it. Coverage
    alone is satisfiable by any model that widens its band far enough, so a
    coverage number quoted on its own says nothing about whether the model is
    useful -- only that it is not overconfident.
    """
    _mean, sig = _mean_sigma(model, X)
    return float(np.mean(sig))


def calibration(model, X: np.ndarray, y: np.ndarray,
                levels=COVERAGE_LEVELS) -> dict:
    """The whole calibration receipt: curve, scalar error, sharpness, PIT.

    `calibration_error` is the mean |empirical - nominal| over `levels` -- one
    number a report can carry, with the curve beside it so nobody has to trust
    the summary. `pit_ks` is the Kolmogorov-Smirnov distance of the PIT from
    Uniform(0, 1), which catches a mis-shaped predictive distribution that
    happens to have the right coverage at the levels sampled.
    """
    p = pit_values(model, X, y)
    curve = {}
    for lv in levels:
        lo, hi = 0.5 * (1.0 - lv), 0.5 * (1.0 + lv)
        curve[float(lv)] = float(np.mean((p >= lo) & (p <= hi)))
    n = p.size
    srt = np.sort(p)
    ecdf_hi = np.arange(1, n + 1) / n
    ecdf_lo = np.arange(0, n) / n
    ks = float(max(np.max(np.abs(ecdf_hi - srt)), np.max(np.abs(srt - ecdf_lo))))
    return {
        "n": int(n),
        "levels": tuple(float(lv) for lv in levels),
        "coverage_curve": curve,
        "calibration_error": float(
            np.mean([abs(curve[float(lv)] - float(lv)) for lv in levels])),
        "sharpness": sharpness(model, X),
        "pit_mean": float(np.mean(p)),
        "pit_ks": ks,
    }


# ---- the standard multi-fidelity test problem (Forrester et al. 2007) -------

def forrester_hi(x: np.ndarray) -> np.ndarray:
    return (6 * x - 2) ** 2 * np.sin(12 * x - 4)


def forrester_lo(x: np.ndarray, A=0.5, B=10.0, C=-5.0) -> np.ndarray:
    return A * forrester_hi(x) + B * (x - 0.5) + C
