"""Slider-surface server: live L0+L1 physics behind an HTML panel.

Stdlib-only HTTP server (edge-friendly, zero deps beyond numpy stack):
  GET  /            -> the slider UI
  POST /eval        -> {params:{name:value}, mission:{...}} -> full L1 report
  POST /mission     -> {text: "..."} -> parsed MissionSpec (rule-based floor)
  POST /generate    -> {percentile: 0..1, n} -> conditioned hull suggestions

Every quantity in the response carries {value, tier, sigma} — the fidelity
badge is not optional (BuildPlan honesty rule 1).
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.generative import HullFamilyModel
from navalai.mission import MissionSpec, parse_mission

_model_lock = threading.Lock()
_model: HullFamilyModel | None = None
_mission_default = MissionSpec()
_pareto_cache: dict | None = None
_pareto_lock = threading.Lock()


def get_pareto() -> dict:
    """Small NSGA-II front, cached after first request (Pareto dashboard)."""
    global _pareto_cache
    with _pareto_lock:
        if _pareto_cache is None:
            from navalai.optimize import pareto_front
            res = pareto_front(_mission_default, pop=16, gens=6, seed=2)
            pts = []
            for x, f in zip(res.X, res.F):
                pts.append({"params": grammar.named(x),
                            "wh_per_nm": round(float(f[0]), 1),
                            "build_area_m2": round(float(f[1]), 1),
                            "gm_m": round(float(-f[2]), 3)})
            _pareto_cache = {"points": pts, "n_evals": res.n_evals,
                            "tier": "L1"}
        return _pareto_cache


def get_model() -> HullFamilyModel:
    global _model
    with _model_lock:
        if _model is None:
            X, _y = sample_valid(150, _mission_default, seed=11)
            _model = HullFamilyModel.fit(X, k=4, seed=1)
        return _model


def eval_payload(params: dict, mission_d: dict | None) -> dict:
    x = grammar.vector({**grammar.named(grammar.LOW * 0 + (grammar.LOW + grammar.HIGH) / 2),
                        **{k: float(v) for k, v in params.items()}})
    mission = _mission_default
    if mission_d:
        mission = MissionSpec(**{k: v for k, v in mission_d.items()
                                 if k in MissionSpec.__dataclass_fields__ and k != "energy"})
    ev = evaluate(x, mission)
    out: dict = {
        "ok": ev.ok,
        "tier": ev.tier,
        "violations": list(ev.violations),
        "eval_ms": round(ev.eval_ms, 2),
    }
    if ev.hydro is not None:
        out["quantities"] = {
            "displacement_kg": _q(ev.hydro.disp_kg, *ev.badges["displacement"]),
            "GM_m": _q(ev.gm_m, *ev.badges["GM"]),
            "freeboard_m": _q(ev.hydro.freeboard_min, "L1", 0.02),
            "Rt_N": _q(ev.resistance.total, *ev.badges["resistance"]),
            "wh_per_nm": _q(ev.energy.wh_per_nm, *ev.badges["wh_per_nm"]),
            "solar_kwh_day": _q(ev.energy.solar_kwh_day, "L1",
                                ev.energy.solar_kwh_day * 0.25),
            "range_solar_nm_day": _q(ev.energy.range_solar_nm_day, "L1",
                                     ev.energy.range_solar_nm_day * 0.35),
            "cb": _q(ev.hydro.cb, "L1", 0.02),
        }
        if ev.weights:
            out["weights_kg"] = {
                "structure": round(ev.weights.structure_kg),
                "battery": round(ev.weights.battery_kg),
                "panels": round(ev.weights.panel_kg),
                "outfit": round(ev.weights.outfit_kg),
                "payload": round(ev.weights.payload_kg),
                "total": round(ev.weights.total_kg),
            }
    return out


def _q(value: float, tier: str, sigma: float) -> dict:
    return {"value": round(float(value), 3), "tier": tier,
            "sigma": round(float(sigma), 3)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = (Path(__file__).parent / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
        elif self.path == "/pareto":
            self._send(200, json.dumps(get_pareto()).encode())
        elif self.path == "/bounds":
            spec = [{"name": n, "unit": u, "low": lo, "high": hi, "desc": d}
                    for (n, u, lo, hi, d) in grammar.PARAMS]
            self._send(200, json.dumps(spec).encode())
        else:
            self._send(404, b"{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/eval":
                out = eval_payload(body.get("params", {}), body.get("mission"))
            elif self.path == "/mission":
                out = json.loads(parse_mission(body.get("text", "")).to_json())
            elif self.path == "/generate":
                model = get_model()
                pct = float(body.get("percentile", 0.5))
                mission = _mission_default

                def score(X):
                    vals = []
                    for row in X:
                        ev = evaluate(row, mission)
                        vals.append(ev.energy.wh_per_nm if ev.energy else 1e9)
                    return np.array(vals)

                X = model.sample_conditioned(int(body.get("n", 3)), score, pct, seed=5)
                out = {"hulls": [grammar.named(x) for x in X]}
            else:
                self._send(404, b"{}")
                return
            self._send(200, json.dumps(out).encode())
        except Exception as e:  # honest errors to the UI
            self._send(400, json.dumps({"error": str(e)}).encode())


def serve(port: int = 8642):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"navalai slider surface: http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8642)
