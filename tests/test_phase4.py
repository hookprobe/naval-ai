"""Gate 4: generative feasibility rate, conditioning actually improves the
objective, latent map round-trip, and slider latency p95 < 100 ms."""

import json
import threading
import time
import urllib.request

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.generative import HullFamilyModel
from navalai.mission import MissionSpec


@pytest.fixture(scope="module")
def model():
    X, _y = sample_valid(120, MissionSpec(), seed=11)
    return HullFamilyModel.fit(X, k=3, seed=1)


def test_generative_samples_are_feasible(model):
    X = model.sample(40, seed=2)
    ok = sum(grammar.check(x).ok for x in X)
    assert ok == 40      # the gate is IN the sampler; 100% by construction


def test_conditioning_improves_objective(model):
    """Performance knob: percentile=0.85 samples must beat the unconditioned
    mean on Wh/NM (the C-ShipGen 'guidance steers generation' property,
    demonstrated at GMM-baseline scale)."""
    m = MissionSpec()

    def score(X):
        return np.array([evaluate(x, m).energy.wh_per_nm
                         if evaluate(x, m).energy else 1e9 for x in X])

    base = score(model.sample(30, seed=8))
    cond = score(model.sample_conditioned(10, score, percentile=0.85, seed=9))
    assert cond.mean() < np.median(base), (
        f"conditioned {cond.mean():.0f} not better than base median {np.median(base):.0f}")


def test_latent_map_roundtrip_feasible(model):
    uv = model.to_latent(model.X_train[:10])
    X2 = model.from_latent(uv)
    for x in X2:
        assert grammar.check(x).ok
    # decoded hulls stay near their sources (same family)
    rel = np.linalg.norm(X2 - model.X_train[:10], axis=1) / np.linalg.norm(
        grammar.HIGH - grammar.LOW)
    assert np.median(rel) < 0.25


def test_latent_grid_decodes_feasible(model):
    grid = np.array([[u, v] for u in (-1.5, 0.0, 1.5) for v in (-1.5, 0.0, 1.5)])
    X = model.from_latent(grid)
    assert all(grammar.check(x).ok for x in X)


# ---------------- slider latency + HTTP smoke ----------------

def test_slider_eval_p95_under_100ms():
    from ui.server import eval_payload
    p = {n: v for n, v in zip(grammar.NAMES,
                              (10.0, 3.2, 0.55, 1.55, 8, 30, 2.2, 3.0, 0.55,
                               0.75, 0.15, 0.85, 10, 0.18, 0.35))}
    eval_payload(p, None)  # warm
    times = []
    for _ in range(30):
        t0 = time.perf_counter()
        out = eval_payload(p, None)
        times.append((time.perf_counter() - t0) * 1e3)
        assert out["tier"] == "L1"
    p95 = float(np.percentile(times, 95))
    assert p95 < 100.0, f"slider p95 {p95:.1f} ms"
    # fidelity badges are mandatory on every quantity
    for q in out["quantities"].values():
        assert set(q) == {"value", "tier", "sigma"}


def test_http_server_smoke():
    from http.server import ThreadingHTTPServer

    from ui.server import Handler
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/bounds", timeout=10) as r:
            spec = json.loads(r.read())
        assert len(spec) == grammar.N_PARAMS
        body = json.dumps({"params": {"LWL": 10, "BWL": 3.2, "T": 0.55, "D": 1.55,
                                      "beta_mid": 8, "beta_bow": 30, "p_bow": 2.2,
                                      "p_stern": 3.0, "x_mb": 0.55, "r_transom": 0.75,
                                      "rocker": 0.15, "forefoot": 0.85, "flare": 10,
                                      "sheer_rise": 0.18, "beta_len": 0.35}}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/eval", data=body)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        assert d["tier"] == "L1" and "quantities" in d
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as r:
            html = r.read().decode()
        assert "slider surface" in html
    finally:
        srv.shutdown()
