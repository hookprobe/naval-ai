"""Phase 7 flywheel: harvest -> retrain -> regression-gate -> (only then) deploy.

BuildPlan Gate 7: "a retrained model that degrades on the frozen benchmark
suite never deploys." The benchmark here is a frozen holdout of hulls + L1
truths stored beside the model metrics; the gate compares candidate metrics
against the recorded baseline with a tolerance.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import db, grammar
from .evaluate import evaluate, sample_valid
from .mission import MissionSpec
from .surrogate import GP


def harvest(n: int, mission: MissionSpec, prov: db.Provenance,
            seed: int = 0) -> int:
    """Evaluate n random valid hulls through L1 and record to provenance."""
    X, _y = sample_valid(n, mission, seed=seed)
    for x in X:
        evaluate(x, mission, provenance=prov)
    return len(X)


@dataclass
class RetrainReport:
    n_train: int
    median_rel_err: float
    coverage_2sigma: float
    passed_gate: bool
    baseline: dict


def _metrics(gp: GP, Xt: np.ndarray, yt: np.ndarray) -> tuple[float, float]:
    pred, sig = gp.predict(Xt)
    rel = np.abs(np.exp(pred) - yt) / yt
    cov = float((np.abs(pred - np.log(yt)) <= 2 * sig).mean())
    return float(np.median(rel)), cov


# ABSOLUTE FLOORS. No ratchet, no baseline and no tolerance may move these:
# a model worse than this does not deploy regardless of history.
HARD_MAX_MEDIAN_REL_ERR = 0.35
HARD_MIN_COVERAGE_2SIGMA = 0.80


def retrain(prov: db.Provenance, mission: MissionSpec,
            quantity: str = "wh_per_nm",
            baseline_path: str | Path = "data/baselines.json",
            holdout_seed: int = 4242, tol: float = 1.25,
            bootstrap: bool = False):
    """Retrain the GP from ALL provenance data for `quantity`; gate against
    the frozen holdout. Returns (gp_or_None, RetrainReport).

    THE GATE COMPARES AGAINST A HIGH-WATER MARK, NOT THE LAST VALUE.
    Gate 7's bar is "surrogate error DECREASES release-over-release". The old
    code accepted `med <= prior * 1.25` and then wrote the accepted (worse)
    metric back as the new prior. MEASURED with a stubbed metric: ten
    consecutive retrains ALL passed while median_rel_err went 0.100 -> 0.859
    (8.6x) and coverage went 0.950 -> -0.450. A negative probability passed,
    because it was only ever compared to `prior - 0.15`. That is a ratchet
    down the hill with a green light on it.

    The baseline now carries `best_median_rel_err` / `best_coverage_2sigma`,
    which only ever improve. `tol` remains as a hard ceiling above the BEST
    ever seen, so run-to-run noise does not block a genuine tie, but drift
    cannot accumulate.
    """
    X, y = prov.training_matrix("L1", _find_q(prov, quantity))
    if len(y) < 20:
        raise ValueError(f"only {len(y)} provenance rows for {quantity}; need >= 20")
    gp = GP.fit(X, np.log(y), seed=1)

    # frozen holdout: same seed forever -> same benchmark hulls forever
    Xt, yt = sample_valid(25, mission, seed=holdout_seed, quantity=quantity)
    med, cov = _metrics(gp, Xt, yt)

    bp = Path(baseline_path)
    if not bp.exists() and not bootstrap:
        # A MISSING BASELINE IS A REFUSAL, NOT A PASS. data/baselines.json was
        # untracked, so on any fresh clone `prior is None` made `ok = True`
        # unconditionally: the first retrain always deployed and wrote its own
        # numbers as the eternal reference. Proven with a label-shuffled model
        # (median_rel_err 0.407 against an honest 0.165) which DEPLOYED.
        raise FileNotFoundError(
            f"no frozen benchmark at {bp}. The regression gate cannot compare "
            f"against a baseline that does not exist, and defaulting to 'pass' "
            f"is how a poisoned model becomes the reference. Pass "
            f"bootstrap=True only when you are deliberately creating the "
            f"first baseline, and commit the result.")
    baseline = json.loads(bp.read_text()) if bp.exists() else {}
    key = quantity
    prior = baseline.get(key)

    # Absolute floors first: these bind even on a bootstrap.
    ok = (med <= HARD_MAX_MEDIAN_REL_ERR
          and HARD_MIN_COVERAGE_2SIGMA <= cov <= 1.0)
    if ok and prior is not None:
        best_med = prior.get("best_median_rel_err", prior["median_rel_err"])
        best_cov = prior.get("best_coverage_2sigma", prior["coverage_2sigma"])
        ok = med <= best_med * tol and cov >= best_cov - 0.15

    report = RetrainReport(len(y), med, cov, ok, prior or {})
    if ok:
        prev_best_med = (prior or {}).get("best_median_rel_err", med)
        prev_best_cov = (prior or {}).get("best_coverage_2sigma", cov)
        baseline[key] = {
            "median_rel_err": med, "coverage_2sigma": cov,
            # monotone: the mark only ever improves, so ten mediocre releases
            # cannot walk the bar downhill one tolerance at a time.
            "best_median_rel_err": min(med, prev_best_med),
            "best_coverage_2sigma": max(cov, prev_best_cov),
            "n_train": len(y), "utc": time.time()}
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_text(json.dumps(baseline, indent=2))
        return gp, report
    return None, report          # degraded model never deploys


def _find_q(prov: db.Provenance, quantity: str) -> str:
    """Resolve short quantity name to the recorded key (e.g. Rt_N@2.57)."""
    if quantity == "wh_per_nm":
        return "wh_per_nm"
    if quantity == "gm":
        return "GM_m"
    rows = prov.con.execute(
        "SELECT DISTINCT quantity FROM result WHERE quantity LIKE ?",
        (quantity + "%",)).fetchall()
    if not rows:
        raise KeyError(quantity)
    return rows[0][0]
