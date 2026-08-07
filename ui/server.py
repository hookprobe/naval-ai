"""Slider-surface server: live L0+L1 physics behind an HTML panel.

Stdlib-only HTTP server (edge-friendly, zero deps beyond numpy stack):
  GET  /            -> the slider UI
  POST /eval        -> {params:{name:value}, mission:{...}} -> full L1 report
  POST /mission     -> {text: "..."} -> parsed MissionSpec (rule-based floor)
  POST /generate    -> {percentile: 0..1, n, mission:{...}} -> conditioned hulls

Every quantity in the response carries {value, tier, sigma} — the fidelity
badge is not optional (BuildPlan honesty rule 1).

GATE 4'S BAR IS "EVERY WIDGET ANSWERS IN <100 ms", AND ONLY `/eval` WAS EVER
TESTED. MEASURED before this rewrite, on this Mac:

    /eval        6.75 ms     the one endpoint with a test          PASS
    /generate     861 ms     at n=3; 11.5 s at n=20; UNTESTED      FAIL
    first request 1018 ms    extra — a blocking model fit          FAIL
    /pareto       440 ms     cold, 0.00 ms after                   FAIL

Two of those are startup work charged to whichever click happened to arrive
first, and the fix is to do it at `serve()` instead — `prefit()`. The third is
real physics: `/generate` scores candidate hulls through L1 at ~13 ms each, and
100 ms buys seven of them, which is not enough to condition on. So the
candidate pool is SCORED AT STARTUP and a request re-cuts it, which is the same
statistic without the wait.

The disjoint reference/candidate split is preserved in the pool exactly as
`sample_conditioned` draws it. Collapsing them into one pool would quietly turn
conditioning back into the same-batch top-k control — the control that R6.3
names as the baseline conditioning has to BEAT, and the one the Gate-4 test
used to be unable to distinguish itself from.

AND THE POOL IS A FUNCTION OF THE MISSION (gap I9, second half). The rewrite
above scored ONE pool under `_mission_default` and `do_POST` had no `mission`
parameter at all, so a mission-specific `/generate` was not slow, it was
impossible — the widget answered the server's mission while the panel displayed
the user's. `/generate` now takes a mission, pools are keyed on it, and the
first request for an unseen mission MISSES Gate 4's 100 ms bar at ~1.5 s. That
is recorded, declared in the payload (`live`, `elapsed_ms`), and not softened:
scoring 176 hulls through L1 costs what it costs, and the default mission is
still prefit at `serve()` so the panel's first click is not the one that pays.
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.generative import HullGenerator, make_generator
from navalai.mission import MissionSpec, parse_mission

_model_lock = threading.Lock()
_model: HullGenerator | None = None
_mission_default = MissionSpec()
_pareto_cache: dict | None = None
_pareto_lock = threading.Lock()
_pool_lock = threading.Lock()
# mission_key -> scored pool. It was a SINGLE pool, which is why `/generate`
# could only ever answer the default mission (gap I9).
_pool: dict[str, dict] | None = None

# Sizes of the pre-scored pools. `N_REF` sets the percentile cut, `N_CAND` is
# what a request selects from; they are DISJOINT batches, not one pool split.
N_REF, N_CAND = 48, 128


def get_pareto() -> dict:
    """Small NSGA-II front, cached after first request (Pareto dashboard)."""
    global _pareto_cache
    with _pareto_lock:
        if _pareto_cache is None:
            from navalai.optimize import pareto_front
            # BUDGET, not bar. pop=16/gens=6 was sized against a 6-constraint
            # ladder; "lcb" and "proportions" (gaps B8, B9) make the feasible
            # set smaller, and MEASURED at the old budget the front collapsed
            # from 6 members to 2 — a dashboard showing a point instead of a
            # trade-off. pop=24/gens=10 restores 6 members for 1.2 s against
            # 0.4 s on the first (cached) request. The front's members were
            # feasible at BOTH budgets; what changed is how much of it the
            # search had found.
            res = pareto_front(_mission_default, pop=24, gens=10, seed=2)
            pts = []
            for x, f in zip(res.X, res.F):
                # GM IS RE-READ FROM THE LADDER, NOT DECODED FROM f[2].
                # This line was `-f[2]` from when the third objective was
                # `-gm`; optimize.py now minimises |GM - GM_mid| (GM is a band,
                # not a maximisation target), so `-f[2]` had become minus a
                # distance. MEASURED on the served front: it reported
                # gm_m = -0.047 for a hull whose GM is +0.514 m — a number that
                # reads as "this boat capsizes at the dock" and is not GM at
                # all. An objective that changes meaning must not be decoded by
                # a caller guessing at its sign.
                ev = evaluate(x, _mission_default)
                pts.append({"params": grammar.named(x),
                            "wh_per_nm": round(float(f[0]), 1),
                            "build_area_m2": round(float(f[1]), 1),
                            "gm_m": (round(float(ev.gm_m), 3)
                                     if ev.gm_m is not None else None)})
            _pareto_cache = {"points": pts, "n_evals": res.n_evals,
                            "tier": "L1"}
        return _pareto_cache


def get_model() -> HullGenerator:
    """The generator, from the FACTORY — no implementation knob in this file.

    It used to read `HullFamilyModel.fit(X, k=4, seed=1)`, and `k` is a GMM
    word. A diffusion model has no `k`, so the "drop-in upgrade slot" PLM lists
    as READY would have required editing this line — which means there was no
    slot. `NAVALAI_GENERATOR` selects the implementation; the server names
    none.
    """
    global _model
    with _model_lock:
        if _model is None:
            X, _y = sample_valid(150, _mission_default, seed=11)
            _model = make_generator(
                X, kind=os.environ.get("NAVALAI_GENERATOR", "gmm"), seed=1)
        return _model


def _score(X: np.ndarray, mission: MissionSpec) -> np.ndarray:
    vals = []
    for row in X:
        ev = evaluate(row, mission)
        vals.append(ev.energy.wh_per_nm if ev.energy else 1e9)
    return np.array(vals, float)


def mission_key(mission: MissionSpec) -> str:
    """Identity of a mission for pool caching — everything the score depends on.

    `name` and `notes` are excluded deliberately: two briefs whose prose differs
    but whose parsed numbers agree score identically, and keying on the text
    would make the cache miss on a retyped sentence.
    """
    e = mission.energy
    return json.dumps([mission.displacement_target_kg, mission.cruise_speed_kn,
                       mission.design_category, mission.crew,
                       mission.lwl_hint_m,
                       [getattr(e, f) for f in sorted(
                           type(e).__dataclass_fields__)]], sort_keys=True)


# How many distinct missions keep a scored pool. Small and explicit: each pool
# is 176 L1 evaluations and ~30 kB, and an unbounded cache keyed on user input
# is a memory leak with a request behind it.
MAX_POOLS = 8


def get_pool(mission: MissionSpec | None = None) -> dict:
    """Reference + candidate batches, SCORED ONCE, per mission.

    Both are drawn from the generator at disjoint seeds, exactly as
    `sample_conditioned` draws them, so a request that re-cuts this pool
    computes the statistic a live conditioned search would — it just does not
    make the user pay 861 ms for it.

    THE MISSION IS PART OF THE KEY BECAUSE THE SCORE IS A FUNCTION OF IT.
    `_score` is Wh/NM at the mission's own cruise speed and energy spec, so a
    pool scored under the default mission answers questions about the default
    mission and nothing else. See `generate_payload` for the history.
    """
    global _pool
    mission = _mission_default if mission is None else mission
    key = mission_key(mission)
    with _pool_lock:
        if _pool is None:
            _pool = {}
        hit = _pool.get(key)
        if hit is None:
            model = get_model()
            t0 = time.perf_counter()
            ref = model.sample(N_REF, seed=6)
            cand = model.sample(N_CAND, seed=7)
            ref_s, cand_s = _score(ref, mission), _score(cand, mission)
            order = np.argsort(cand_s)
            hit = {"ref_scores": ref_s, "cand": cand[order],
                   "cand_scores": cand_s[order],
                   "build_s": time.perf_counter() - t0, "key": key}
            if len(_pool) >= MAX_POOLS:
                _pool.pop(next(iter(_pool)))     # oldest insertion, FIFO
            _pool[key] = hit
        return hit


def prefit() -> dict:
    """Do every blocking startup cost BEFORE the first click, not on it.

    MEASURED: the first `/generate` paid a 1018 ms model fit and the first
    `/pareto` 440 ms (1.2 s at the widened NSGA-II budget) — constant work
    with nothing to do with the request that happened to arrive first.

    It prefits the DEFAULT mission only. A pool is a function of the mission
    (`get_pool`), and there is no honest way to pre-pay for a mission the user
    has not typed yet — so the first `/generate` on a NEW mission does pay, and
    `generate_payload` returns `live: true` and `elapsed_ms` saying so rather
    than pretending otherwise.
    """
    t0 = time.perf_counter()
    get_model()
    pool = get_pool()
    get_pareto()
    return {"prefit_s": time.perf_counter() - t0, "pool_s": pool["build_s"],
            "n_ref": N_REF, "n_cand": N_CAND}


def generate_payload(n: int = 3, percentile: float = 0.5,
                     mission_d: dict | None = None) -> dict:
    """Conditioned hulls off the pre-scored pool, with the cut declared.

    `percentile` IS A STRICTNESS KNOB, not a kept fraction. The cut is the
    `1 - percentile` quantile of the REFERENCE scores and candidates at or
    below it are kept, so 0.85 means "the best 15% of what the model produces"
    and 1.0 means "the single best". The old docstring read "keep draws whose
    score is in the best `percentile`", which says the opposite; the code was
    right and the sentence was wrong, and both the UI and the Gate-4 test
    already passed 0.85 meaning strict.

    `partial` replaces `raise RuntimeError("conditioned sampler starved")`. A
    widget that spins and then throws is worse than one that returns the best
    it has and says the search was cut short.

    THE MISSION USED TO BE UNREACHABLE FROM HERE (gap I9). `do_POST` passed only
    `n` and `percentile`, and `_score` read the module-level `_mission_default`,
    so the panel's own mission box — which `/eval` honours — did nothing to
    `/generate`. That is not a slow feature; it is a wrong answer: the user sets
    "3 t dayboat at 9 knots", the widget ranks candidates by Wh/NM at 5 knots
    under a 6 t budget, and nothing in the response says which mission it
    answered. MEASURED after wiring it through, the ranking really does move:
    the default mission and a 9 kn / 3 t mission return DIFFERENT hulls from the
    same 128 candidates.

    THE COST IS DECLARED RATHER THAN HIDDEN, and honesty rule 6 applies to it.
    A mission the server has not seen must score 176 hulls through L1, and
    MEASURED on this Mac that is ~1.5 s — 15x over Gate 4's 100 ms bar. It is
    therefore paid ONCE per mission and cached (`get_pool`), so the first
    request for a mission MISSES the bar and every later one is ~0.03 ms. The
    response says which it was: `live` is True when this request paid for the
    pool, and `elapsed_ms` is what it actually cost. The default mission is
    scored at `serve()` by `prefit()`, so the panel's first click is fast; a
    retyped mission is not, and the payload now admits that instead of quietly
    answering a different question.
    """
    if not 0.0 <= percentile <= 1.0:
        raise ValueError(f"percentile must be in [0, 1], got {percentile}")
    n = max(int(n), 0)
    mission = _mission_default
    if mission_d:
        mission = MissionSpec(**{k: v for k, v in mission_d.items()
                                 if k in MissionSpec.__dataclass_fields__
                                 and k != "energy"})
    t0 = time.perf_counter()
    key = mission_key(mission)
    with _pool_lock:
        cached = _pool is not None and key in _pool
    pool = get_pool(mission)
    cut = float(np.quantile(pool["ref_scores"], 1.0 - percentile))
    sel = pool["cand_scores"] <= cut
    X = pool["cand"][sel][:n]
    scores = pool["cand_scores"][sel][:n]
    return {
        "hulls": [grammar.named(x) for x in X],
        "wh_per_nm": [round(float(v), 1) for v in scores],
        "percentile": percentile, "cut_wh_per_nm": round(cut, 1),
        "n_requested": n, "n_returned": int(len(X)),
        "partial": bool(len(X) < n),
        "n_pool": int(len(pool["cand"])), "n_reference": int(N_REF),
        "tier": "L1", "source": "prefit_pool" if cached else "live_pool",
        # Which mission this answer is about, and whether the caller paid for
        # it. A conditioned result that does not name its condition is not an
        # auditable answer.
        "mission": {"displacement_target_kg": mission.displacement_target_kg,
                    "cruise_speed_kn": mission.cruise_speed_kn,
                    "design_category": mission.design_category},
        "mission_notes": mission.notes,
        "live": not cached,
        "pool_build_s": round(float(pool["build_s"]), 3),
        "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 3),
    }


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
        if ev.masses is not None:
            # HONESTY RULE 1 WAS VIOLATED IN THE ONE PLACE A USER READS.
            # This block served six BARE rounded floats — no tier, no sigma —
            # while `weights.aggregate()` had already computed both, item by
            # item and in quadrature. MEASURED on the reference hull: total
            # 6000 kg +/- 1620 kg, i.e. a 27% band the panel simply did not
            # show.
            #
            # And it served the wrong TOTAL. `ev.weights` is the five-bucket
            # budget; the hull is floated at `ev.masses.total_kg`, which
            # includes the DECLARED `unaccounted` item — MEASURED at 3230 kg,
            # 54% of displacement on the 6 t mission. Serving the budget's
            # total next to `displacement_kg` showed two numbers that are
            # supposed to be the same mass and are not, with nothing saying
            # why. The positioned model is the one truth (CLAUDE.md), so the
            # panel now reports THAT model's own items, `unaccounted`
            # included, and the lines sum to the displacement above them.
            #
            # Sigma and tier come from the MassItems themselves, never retyped
            # here: `0.15 * mass` lives in `energy.weight_items` and 0.5 on the
            # unaccounted gap in `evaluate`, and a copy in this file is exactly
            # the drift the design-side invariants forbid. `basis` is "assumed"
            # because every one of those sigmas is a declared fraction of its
            # own value; the TOTAL is "measured" because it is propagated.
            out["weights_kg"] = {
                it.id: _q(it.mass_kg, it.tier, it.sigma_kg, "assumed")
                for it in ev.masses.items
            }
            out["weights_kg"]["total"] = _q(
                ev.masses.total_kg, "L1", ev.masses.sigma_kg, "measured")
    return out


def _q(value: float, tier: str, sigma: float, basis: str = "assumed") -> dict:
    """One quantity, badged. `basis` distinguishes a PROPAGATED sigma from a
    declared fraction of the value — the audit found every band in the UI was
    the latter (freeboard a constant 0.02, wh_per_nm literally 0.30 x value),
    which is a decoration, not an uncertainty. Saying which is which costs one
    string and stops the band being read as a measurement it is not."""
    if not math.isfinite(value) or not math.isfinite(sigma):
        # honesty rule 1: a non-finite quantity is a refusal, not a number.
        # NaN is also not valid JSON (RFC 8259) and was being emitted raw.
        return {"value": None, "tier": tier, "sigma": None,
                "basis": basis, "state": "non-finite — refused"}
    return {"value": round(float(value), 3), "tier": tier,
            "sigma": round(float(sigma), 3), "basis": basis}


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
                # `mission` joined the wire. It was absent, so a
                # mission-specific generate was not slow — it was IMPOSSIBLE,
                # while the panel showed a mission box next to the button.
                out = generate_payload(int(body.get("n", 3)),
                                       float(body.get("percentile", 0.5)),
                                       body.get("mission"))
            else:
                self._send(404, b"{}")
                return
            self._send(200, json.dumps(out).encode())
        except Exception as e:  # honest errors to the UI
            self._send(400, json.dumps({"error": str(e)}).encode())


def serve(port: int = 8642):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    info = prefit()          # pay the startup cost here, not on a user's click
    print(f"navalai slider surface: http://127.0.0.1:{port} "
          f"(prefit {info['prefit_s']:.2f} s: model + {info['n_ref']}/"
          f"{info['n_cand']} scored pool + Pareto front)")
    httpd.serve_forever()


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8642)
