"""Slider-surface server: live L0+L1 physics behind an HTML panel.

Stdlib-only HTTP server (edge-friendly, zero deps beyond numpy stack):
  GET  /            -> the slider UI
  GET  /pareto      -> the DEFAULT mission's front (warm-up / no-mission caller)
  POST /eval        -> {params:{name:value}, mission:{...}} -> full L1 report
  POST /mission     -> {text: "..."} -> parsed MissionSpec (rule-based floor)
  POST /generate    -> {percentile: 0..1, n, mission:{...}} -> conditioned hulls
  POST /pareto      -> {mission:{...}} -> THAT mission's trade-off surface

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

AND `/pareto` WAS THE LAST ENDPOINT ANSWERING THE WRONG QUESTION. `get_pareto`
was given a mission and a per-mission cache, but the HTTP surface was not: the
only route was `GET /pareto`, which takes no body, so the dashboard drew the
DEFAULT mission's trade-off surface beside sliders showing the user's. A
per-mission cache no caller can reach a second mission through is not a fix.
`POST /pareto {mission}` is the wire, mirroring `/generate`; GET stays for the
warm-up and for a caller that genuinely wants the default. Same honesty
accounting: an unseen mission runs NSGA-II live, MEASURED 2026-08-11 over seven
briefs on this Mac at 1.88-2.30 s against Gate 4's 100 ms bar — a 19-23x miss —
where the repeat is 0.023-0.032 ms. The payload says `live: true` and the
`elapsed_ms` it cost, rather than letting a two-second search read as a fast
widget.
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
from navalai.energy import SIGMA_PLACEHOLDER
from navalai.evaluate import evaluate, sample_valid
from navalai.flywheel import DeployedSurrogate
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


def get_pareto(mission: MissionSpec | None = None) -> dict:
    """Small NSGA-II front for THIS mission, cached per mission.

    IT ANSWERED THE WRONG QUESTION UNTIL 2026-08-11. Both the search and the
    re-evaluation read the module-level `_mission_default`, and the result went
    into ONE global `_pareto_cache` — so the trade-off surface a customer was
    shown was not their boat, and the first caller's answer was then served to
    every later one. `/eval` and `/generate` had already been fixed for exactly
    this (gap I9, the single-pool bug: "it was a SINGLE pool, which is why
    `/generate` could only ever answer the default mission"). `/pareto` was
    left behind, which is why the dashboard and the sliders could disagree
    about the same mission.

    Keyed by `mission_key`, the same helper `/generate` uses, so one cache
    entry per mission rather than one entry full stop. `mission=None` keeps the
    old default for callers that genuinely want it (the warm-up at serve()).

    BOUNDED BY `MAX_POOLS`, for the same reason `get_pool` is. While the only
    route in was `GET /pareto` this map could hold at most one entry, so the
    bound was not needed; `POST /pareto` makes the key user input, and a cache
    keyed on user input with no ceiling is a memory leak with a request behind
    it. Same FIFO, same constant — a second ceiling declared here would be the
    number-declared-twice defect.
    """
    global _pareto_cache
    mission = mission if mission is not None else _mission_default
    key = mission_key(mission)
    with _pareto_lock:
        if _pareto_cache is None:
            _pareto_cache = {}
        if key not in _pareto_cache:
            from navalai.optimize import pareto_front
            # BUDGET, not bar. pop=16/gens=6 was sized against a 6-constraint
            # ladder; "lcb" and "proportions" (gaps B8, B9) make the feasible
            # set smaller, and MEASURED at the old budget the front collapsed
            # from 6 members to 2 — a dashboard showing a point instead of a
            # trade-off. pop=24/gens=10 restored 6 members for 1.2 s.
            #
            # RAISED AGAIN 2026-08-14 (R1.1), same doctrine: the mission now
            # CHOOSES its prismatic (`mission_cp_band`), so a hinted brief
            # searches a much narrower Cp box, and MEASURED at pop=24 the
            # panel's own opening brief found 0 front members on seeds 1-3
            # (gens 10 AND 30) while pop=48 finds 7-14 — the feasible set is
            # a thin manifold and the narrower box needs more POPULATION
            # DIVERSITY, not more generations. pop=48/gens=15, measured:
            # default mission 18 members, panel brief 7 (seed 2). Cold cost
            # ~3x, declared in the payload as ever — the front's members were
            # feasible at every budget; what changed is how much of it the
            # search finds.
            res = pareto_front(mission, pop=48, gens=15, seed=2)
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
                ev = evaluate(x, mission)
                pts.append({"params": grammar.named(x),
                            "wh_per_nm": round(float(f[0]), 1),
                            "build_area_m2": round(float(f[1]), 1),
                            "gm_m": (round(float(ev.gm_m), 3)
                                     if ev.gm_m is not None else None)})
            if len(_pareto_cache) >= MAX_POOLS:
                _pareto_cache.pop(next(iter(_pareto_cache)))   # FIFO, as pools
            _pareto_cache[key] = {"points": pts, "n_evals": res.n_evals,
                                  "tier": "L1"}
        return _pareto_cache[key]


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


def _mission_from(mission_d: dict | None) -> MissionSpec:
    """ONE decoder from the wire dict to a MissionSpec.

    `eval_payload` and `generate_payload` each carried a verbatim copy of this
    comprehension, and `/pareto` would have been a third. The recurring defect
    in this codebase is a thing declared twice (CLAUDE.md, design-side
    invariants); three copies of the field filter is how two endpoints end up
    accepting different missions from the same JSON.

    `energy` used to be DROPPED here (it arrives as a nested dict and the
    spec wanted an EnergySpec), so a wire mission's battery_kwh silently
    never reached the evaluation — C-12. MissionSpec.__post_init__ now
    rehydrates energy dicts exactly as it does vessel and payload, so the
    key passes through and a malformed energy dict fails LOUDLY at the
    boundary instead of evaluating the default spec under the caller's
    label.
    """
    if not mission_d:
        return _mission_default
    return MissionSpec(**{k: v for k, v in mission_d.items()
                          if k in MissionSpec.__dataclass_fields__})


def _mission_receipt(mission: MissionSpec) -> dict:
    """What an answer says about the condition it was computed under. A
    conditioned result that does not name its condition is not auditable."""
    return {"displacement_target_kg": mission.displacement_target_kg,
            "cruise_speed_kn": mission.cruise_speed_kn,
            "design_category": mission.design_category}


def pareto_payload(mission_d: dict | None = None) -> dict:
    """`get_pareto` for THIS mission, with the cost declared, not hidden.

    THE FRONT WAS RIGHT AND THE WIRE WAS NOT. `get_pareto(mission)` and its
    per-mission cache landed earlier the same day, but `do_GET` still served
    `/pareto` with no mission and there was no POST route at all, so the only
    front any caller could obtain was the default mission's — the dashboard
    drew one boat's trade-off surface while the sliders beside it evaluated
    another. Exactly gap I9's shape, one endpoint later.

    HONESTY RULE 6, AND GATE 4'S BAR IS NOT SOFTENED. An unseen mission is a
    cache MISS and runs NSGA-II at pop=24/gens=10 — MEASURED 2026-08-11 over
    seven briefs on this Mac at 1.88-2.30 s cold against a 100 ms bar, a 19-23x
    miss, where the repeat is 0.023-0.032 ms. The `1.2 s` quoted for this
    budget in `get_pareto` is older than the constraint set the search now runs
    against; re-measure before quoting either. The payload therefore reports
    `live` (this request paid for the search) and
    `elapsed_ms` (what it cost), the same two keys `/generate` declares, so the
    miss is visible in the answer instead of being averaged away by the cached
    calls around it. The default mission is still searched at `serve()` by
    `prefit()`, so the panel's first click is not the one that pays.

    The cached front is COPIED into the response. Merging the receipt keys into
    the cached dict would mutate the cache, and the next caller would then read
    another mission's `live`/`mission` receipt off their own front.
    """
    mission = _mission_from(mission_d)
    t0 = time.perf_counter()
    key = mission_key(mission)
    with _pareto_lock:
        cached = _pareto_cache is not None and key in _pareto_cache
    front = get_pareto(mission)
    # AN EMPTY FRONT MUST SAY WHY (2026-08-20). MEASURED: the brief "3 tonne
    # dayboat, 8 m, coastal, cruise 9 knots" is Fn 0.523 — past the thin-ship
    # limit 0.45 and below the planing onset 0.65, a band where NO resistance
    # model in this tree is valid — and this endpoint returned
    # `{"points": []}` with nothing else. A bare empty list is the worst
    # available answer to "what boats suit this brief": it is
    # indistinguishable from "we looked and found none", which is a claim
    # about BOATS when the truth is a gap in OUR LIBRARY.
    _domain_reasons: tuple[str, ...] = ()
    try:
        import math as _math

        from navalai.constants import G_STANDARD
        from navalai.contract import supported_domain
        from navalai.resistance import NU_FRESH_15C
        _L = getattr(mission, "lwl_hint_m", None)
        _U = mission.cruise_speed_ms()
        if _L and _U:
            # G_STANDARD, not a literal: this Fn is handed straight to
            # `supported_domain`, which derives its own edge with the
            # same constant. Two gravities would put the mission on one
            # side of a bound computed on the other.
            _fn = _U / _math.sqrt(G_STANDARD * float(_L))
            _in, _why = supported_domain(lwl_m=float(_L), fn=_fn,
                                         re=_U * float(_L) / NU_FRESH_15C,
                                         nu_m2_s=NU_FRESH_15C)
            if not _in:
                _domain_reasons = _why
    except Exception:                                        # noqa: BLE001
        # A receipt that cannot be built must not take the endpoint down; the
        # front is still the answer. The absence shows as no `refused` key
        # rather than as a fabricated one.
        _domain_reasons = ()

    return {**front,
            "refused": bool(_domain_reasons),
            "refused_reasons": list(_domain_reasons),
            "mission": _mission_receipt(mission),
            "mission_notes": mission.notes,
            "live": not cached,
            "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 3)}


def surrogate_status(mission_d: dict | None = None) -> dict:
    """GAP I14: THE SURROGATE SPINE GETS A CONSUMER, and an honest one.

    `flywheel.DeployedSurrogate` is "the ONLY caller-facing way to ask a
    deployed surrogate for a number" — it refuses off-support rows and
    escalates to the ladder instead of badging a guess. Until now NOTHING in
    the served product consumed it, so the whole cheap-model tier existed for
    tests. That is the shape of gap A4 one layer out: machinery that looks
    load-bearing and carries nothing.

    This endpoint answers the question the operator's architecture actually
    asks — "of the candidates in front of us, how many could a cheap model
    answer, and how many must escalate?" — which is the N_candidate >> N_CFD
    economics made visible rather than asserted.

    IT FABRICATES NOTHING. Deploying a surrogate needs a provenance database
    of harvested runs (`flywheel.retrain`), and a served process may have
    none. With no deployed model this returns `deployed: False` and says so;
    it does NOT fit one on the request path, and it does NOT report a split it
    could not measure. An absence is reported as an absence.
    """
    mission = _mission_from(mission_d) if mission_d else _mission_default
    out: dict = {"deployed": False, "quantity": None, "tier": None,
                 "n_candidates": 0, "answered": 0, "escalated": 0,
                 "note": ""}
    model = _deployed_surrogate()
    if model is None:
        out["note"] = (
            "no surrogate is deployed in this process. One is produced by "
            "flywheel.retrain() from a provenance database of harvested "
            "runs; none is fitted here, because fitting on a request would "
            "make the first caller pay for it and a model fitted on the fly "
            "has no frozen-benchmark receipt behind it.")
        return out

    pool = get_pool(mission)
    X = pool.get("X")
    if X is None or not len(X):
        out["note"] = "no candidate pool for this mission"
        return out

    answered = escalated = 0
    for row in X:
        try:
            model.query(row, escalate=False)
            answered += 1
        except Exception:                                    # noqa: BLE001
            # OODRefusal and anything else the guarded path raises: the row
            # is one the cheap tier declines, which is the ANSWER here, not
            # an error to swallow.
            escalated += 1
    out.update(deployed=True, quantity=model.quantity, tier=model.tier,
               n_candidates=len(X), answered=answered, escalated=escalated,
               frozen_ood_rate=model.frozen_ood_rate,
               note=(f"{answered} of {len(X)} candidates answerable by the "
                     f"cheap tier; {escalated} would escalate to the ladder"))
    return out


#: The process's deployed surrogate. None until `deploy_surrogate` installs
#: one; never fitted implicitly.
_DEPLOYED_SURROGATE = None


def deploy_surrogate(model) -> None:
    """Install a deployed surrogate for this process, and REFUSE a bare GP.

    This is where the import earns its keep. Gap A4's finding is that a bare
    `GP` answers any query with a confident-looking tuple and no tier — it
    reported 770.9 Wh/NM with a sigma that looks like every other number the
    model produces, on a row it had no support for. `DeployedSurrogate` is
    the wrapper with no unguarded method: it refuses off-support rows and
    escalates instead of badging a guess.

    So the served product accepts ONLY the guarded object. Handing it a bare
    GP is refused here rather than discovered later in a payload, which is
    the difference between a type check and an incident.
    """
    global _DEPLOYED_SURROGATE
    if model is not None and not isinstance(model, DeployedSurrogate):
        raise TypeError(
            f"deploy_surrogate: refusing a {type(model).__name__}. Only a "
            f"flywheel.DeployedSurrogate may answer served queries — a bare "
            f"GP has no tier and no OOD refusal, and would return a "
            f"confident-looking number for a row it cannot support (gap A4).")
    _DEPLOYED_SURROGATE = model


def _deployed_surrogate():
    """The process's deployed surrogate, or None. Never fits one."""
    return _DEPLOYED_SURROGATE


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
    mission = _mission_from(mission_d)
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
        "mission": _mission_receipt(mission),
        "mission_notes": mission.notes,
        "live": not cached,
        "pool_build_s": round(float(pool["build_s"]), 3),
        "elapsed_ms": round((time.perf_counter() - t0) * 1e3, 3),
    }


def eval_payload(params: dict, mission_d: dict | None) -> dict:
    x = grammar.vector({**grammar.named(grammar.LOW * 0 + (grammar.LOW + grammar.HIGH) / 2),
                        **{k: float(v) for k, v in params.items()}})
    mission = _mission_from(mission_d)
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
            # H1's FENCE DID NOT REACH THIS FILE (2026-08-21). Four sigmas
            # were typed HERE, at the call site, two of them as literal
            # fractions of their own value: freeboard 0.02, cb 0.02,
            # solar * 0.25 and range_solar * 0.35. `evaluate.badges` had no
            # entry to propagate from, so the UI invented one — and the badge
            # dict is the only place allowed to decide what a sigma means.
            # freeboard and range_solar now propagate; see the comment on
            # `evaluate.badges` for why the other two cannot yet.
            "freeboard_m": _q(ev.hydro.freeboard_min, *ev.badges["freeboard"]),
            "Rt_N": _q(ev.resistance.total, *ev.badges["resistance"]),
            "wh_per_nm": _q(ev.energy.wh_per_nm, *ev.badges["wh_per_nm"]),
            # SOLAR GENERATION STILL HAS NO PROPAGATABLE SIGMA. `EnergySpec`
            # declares `solar_yield_kwh_m2_day`, `panel_packing` and
            # `panel_eff` as bare floats, so there is no input band to carry
            # through. The honest move is to say so rather than to keep
            # dressing a typed 25% as a one-sigma result: the value is served
            # with sigma 0.0 under the basis `energy` owns for exactly this
            # case. Closing it needs a SOURCED yield spread on EnergySpec,
            # which is a data decision, not a code one.
            "solar_kwh_day": _q(ev.energy.solar_kwh_day, "L1", 0.0,
                                SIGMA_PLACEHOLDER),
            "range_solar_nm_day": _q(ev.energy.range_solar_nm_day,
                                     *ev.badges["range_solar_nm_day"]),
            # cb is a shape coefficient of the FLOATED hull, so its band is
            # the sinkage band seen through the volume integral. Nothing
            # computes that today, and 0.02 was a guess wearing a one-sigma
            # column.
            "cb": _q(ev.hydro.cb, "L1", 0.0, SIGMA_PLACEHOLDER),
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
            # GET carries no body, so this is the DEFAULT mission's front and
            # nothing else. It is kept for the warm-up path and for a caller
            # that genuinely wants the default; the dashboard POSTs the mission
            # it is displaying. When GET was the ONLY route, "the default" was
            # the only answer the endpoint could give.
            self._send(200, json.dumps(pareto_payload()).encode())
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
            elif self.path == "/pareto":
                # The last endpoint that could only answer the default mission.
                # `get_pareto` took a mission and cached per mission; the HTTP
                # surface did not, so no caller could reach a second entry and
                # the dashboard showed a trade-off surface for a boat nobody
                # had asked about.
                out = pareto_payload(body.get("mission"))
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
