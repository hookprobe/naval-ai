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


def retrain(prov: db.Provenance, mission: MissionSpec,
            quantity: str = "wh_per_nm",
            baseline_path: str | Path = "data/baselines.json",
            holdout_seed: int = 4242, tol: float = 1.25):
    """Retrain the GP from ALL provenance data for `quantity`; gate against
    the frozen holdout. Returns (gp_or_None, RetrainReport)."""
    X, y = prov.training_matrix("L1", _find_q(prov, quantity))
    if len(y) < 20:
        raise ValueError(f"only {len(y)} provenance rows for {quantity}; need >= 20")
    gp = GP.fit(X, np.log(y), seed=1)

    # frozen holdout: same seed forever -> same benchmark hulls forever
    Xt, yt = sample_valid(25, mission, seed=holdout_seed, quantity=quantity)
    med, cov = _metrics(gp, Xt, yt)

    bp = Path(baseline_path)
    baseline = json.loads(bp.read_text()) if bp.exists() else {}
    key = quantity
    prior = baseline.get(key)
    ok = True
    if prior is not None:
        ok = med <= prior["median_rel_err"] * tol and cov >= prior["coverage_2sigma"] - 0.15
    report = RetrainReport(len(y), med, cov, ok, prior or {})
    if ok:
        baseline[key] = {"median_rel_err": med, "coverage_2sigma": cov,
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
