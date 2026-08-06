"""Hull grammar: parameter vector + closed-form feasibility constraints (L0 gate).

Pattern from Ship-D (Bagazinski & Ahmed 2023): validity is decided by cheap
algebraic constraints on the parameter vector (their 49 checks run in ~0.2 ms,
~10,000x faster than mesh checks), which is what makes slider-rate gating
possible. This grammar targets small craft (4-20 m) with hard-chine,
developable sections — buildable from sheet plywood/aluminium by construction,
a constraint absent from Ship-D and named in BuildPlan Phase 0.

Coordinate system: x=0 at transom, x=LWL at stem; z=0 at design waterline,
z negative down; y is half-breadth (starboard).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# (name, unit, low, high, description)
PARAMS = [
    ("LWL",        "m",   4.0, 20.0, "waterline length"),
    ("BWL",        "m",   1.2,  6.0, "chine beam at max-beam station"),
    ("T",          "m",   0.2,  1.5, "design draft (keel at midship)"),
    ("D",          "m",   0.6,  3.0, "depth, keel to sheer at midship"),
    ("beta_mid",   "deg", 0.0, 25.0, "deadrise at midship"),
    ("beta_bow",   "deg", 2.0, 50.0, "deadrise at forward stations"),
    ("p_bow",      "-",   1.2,  4.0, "waterline fullness exponent, forward"),
    ("p_stern",    "-",   1.2,  6.0, "fullness exponent, aft"),
    ("x_mb",       "-",   0.40, 0.68, "max-beam station / LWL"),
    ("r_transom",  "-",   0.0,  0.95, "transom half-beam / max half-beam"),
    ("rocker",     "-",   0.0,  0.6, "keel rise at transom / T"),
    ("forefoot",   "-",   0.0,  1.0, "keel rise at stem / T"),
    ("flare",      "deg", -5.0, 25.0, "topside flare angle"),
    ("sheer_rise", "-",   0.0,  0.5, "bow sheer rise / D"),
    ("beta_len",   "-",   0.15, 0.6, "fraction of LWL over which deadrise warps"),
]

N_PARAMS = len(PARAMS)
NAMES = [p[0] for p in PARAMS]
LOW = np.array([p[2] for p in PARAMS])
HIGH = np.array([p[3] for p in PARAMS])

# Slenderness / stability proportion bands, as ONE definition each.
#
# They used to be four literals inside `check()`, which is how gap B9 became
# possible: L0 bounded BWL/T at 12 on the PARAMETER vector and nothing ever
# re-checked the proportions of the hull that was actually delivered. MEASURED
# on 200 L0-feasible hulls floated to their mission displacement: 28.0% sit
# outside the B/T band and 4.5% outside the L/B band ON THE FLOATED STATE, and
# one delivered hull reached B/T 14.4 against the project's own <= 12 bar. The
# parameter T is the DESIGN draft at midship; the floated draft is whatever the
# weight model produces, so the two are simply different numbers and the gate
# was checking the one nobody sails.
#
# `proportion_margins` is the shared kernel: `check()` applies it to the
# parameters and `evaluate()` applies it to `HydroState`, so the band cannot
# drift between the two.
L_OVER_B_BAND = (2.2, 8.5)
B_OVER_T_BAND = (1.8, 12.0)


def proportion_margins(lwl: float, b_wl: float, t: float) -> dict[str, float]:
    """Relative band margins for L/B and B/T: > 0 means OUTSIDE the band.

    Normalised by the band edge rather than left absolute, so the number is
    scale-free and continuous — NSGA-II needs a gradient out of an infeasible
    region, and "L/B is 1.2 too big" means something different on a 4 m tender
    than on a 20 m barge.
    """
    out: dict[str, float] = {}
    for key, val, (lo, hi) in (("L/B", lwl / max(b_wl, 1e-9), L_OVER_B_BAND),
                               ("B/T", b_wl / max(t, 1e-9), B_OVER_T_BAND)):
        out[key] = max((lo - val) / lo, (val - hi) / hi)
    return out


@dataclass(frozen=True)
class GateReport:
    ok: bool
    violations: tuple[str, ...]


def _rel(name: str, cond: bool, msg: str, out: list[str]) -> None:
    if not cond:
        out.append(f"{name}: {msg}")


def check(x: np.ndarray) -> GateReport:
    """L0 algebraic gate. Pure closed-form; no geometry construction.

    Returns every violated constraint (not just the first) so the UI can
    grey sliders with a reason, mirroring the manifest-style gating rule.
    """
    x = np.asarray(x, dtype=float)
    v: list[str] = []
    if x.shape != (N_PARAMS,):
        return GateReport(False, (f"shape: expected {N_PARAMS} params",))
    if not np.all(np.isfinite(x)):
        return GateReport(False, ("finite: NaN/inf in parameter vector",))

    # C1..C30 bound constraints
    for i, (name, _u, lo, hi, _d) in enumerate(PARAMS):
        _rel(f"bound[{name}]", lo <= x[i] <= hi, f"{x[i]:.4g} outside [{lo}, {hi}]", v)

    lwl, bwl, t, d, bmid, bbow, _pb, _ps, xmb, rtr, rock, ff, flare, _sr, _bl = x

    # C31 draft below depth with real freeboard
    fb = d - t
    _rel("freeboard.abs", fb >= 0.30, f"freeboard {fb:.2f} m < 0.30 m", v)
    _rel("freeboard.rel", fb >= 0.045 * lwl, f"freeboard {fb:.2f} m < 4.5% LWL", v)
    # C33 slenderness / stability proportions. Same kernel evaluate() re-applies
    # to the FLOATED hull (gap B9) — one band, two states.
    marg = proportion_margins(lwl, bwl, t)
    _rel("L/B", marg["L/B"] <= 0.0,
         f"L/B {lwl / bwl:.2f} outside {list(L_OVER_B_BAND)}", v)
    _rel("B/T", marg["B/T"] <= 0.0,
         f"B/T {bwl / t:.2f} outside {list(B_OVER_T_BAND)}", v)
    # C35 deadrise ordering (bow at least as steep as midship)
    _rel("deadrise.order", bbow >= bmid, f"beta_bow {bbow:.1f} < beta_mid {bmid:.1f}", v)
    # C36 chine must stay submerged-ish at midship: z_chine = -T + (B/2) tan(beta)
    z_chine = -t + 0.5 * bwl * math.tan(math.radians(bmid))
    _rel("chine.height", z_chine <= 0.25 * t, f"mid chine {z_chine:.2f} m above 0.25T", v)
    # C37 chine below sheer
    _rel("chine.below.sheer", z_chine <= fb - 0.05, "chine reaches sheer", v)
    # C40 transom immersion: transom chine z with rocker must not fly high
    z_ch_tr = -t * (1.0 - rock) + rtr * 0.5 * bwl * math.tan(math.radians(bmid))
    _rel("transom.chine", z_ch_tr <= 0.35 * t, f"transom chine {z_ch_tr:.2f} m too high", v)
    #
    # FOUR CHECKS WERE DELETED HERE, AND DELETING THEM CHANGES NO VERDICT.
    # Gap E4: `keel.rocker`, `keel.forefoot`, `x_mb.margin` and `flare.fold`
    # cannot fire anywhere inside the declared parameter bounds, so they padded
    # the constraint count and nothing else. MEASURED over 400,000 uniform
    # in-bounds vectors — 0 hits each, while the nine that survive fire between
    # 3.06% and 33.04% of the time:
    #
    #     freeboard.rel      33.039%      chine.height        12.557%
    #     L/B                32.419%      panel.twist          6.819%
    #     freeboard.abs      23.097%      transom.chine        5.497%
    #     deadrise.order     22.204%      chine.below.sheer    3.059%
    #     B/T                18.618%
    #
    # Each is dead for a reason that is arithmetic, not empirical:
    #   keel.rocker    `rocker * T <= 0.75 * T` with rocker bounded at 0.6.
    #   keel.forefoot  `forefoot <= 1.0` IS the forefoot upper bound, restated.
    #   x_mb.margin    0.05..0.95 against an x_mb bound of [0.40, 0.68].
    #   flare.fold     needs BWL < 0.70 m (flare >= -5 deg, freeboard <= 2.8 m)
    #                  against a BWL minimum of 1.20 m.
    # Ship-D's "49 closed-form constraints" is a count this grammar was written
    # to echo; echoing it with tautologies makes the count true and the claim
    # false. The honest figure is 15 bound checks plus 9 live relations, and
    # `tests/test_phase0.py` now pins it by measurement so it cannot rot back.
    #
    # C43 developability proxy: deadrise warp per metre (plywood twist limit)
    warp_len = max(x[14] * lwl, 1e-6)
    twist_rate = (bbow - bmid) / warp_len
    _rel("panel.twist", twist_rate <= 14.0, f"bottom twist {twist_rate:.1f} deg/m > 14", v)

    return GateReport(len(v) == 0, tuple(v))


def sample(n: int, rng: np.random.Generator | None = None,
           max_tries: int = 200) -> np.ndarray:
    """Rejection-sample n feasible parameter vectors (uniform in bounds)."""
    rng = rng or np.random.default_rng(0)
    out = np.empty((n, N_PARAMS))
    got = 0
    for _ in range(max_tries * n):
        cand = rng.uniform(LOW, HIGH)
        if check(cand).ok:
            out[got] = cand
            got += 1
            if got == n:
                return out
    raise RuntimeError(f"only {got}/{n} feasible samples after {max_tries * n} tries")


def named(x: np.ndarray) -> dict[str, float]:
    return {n: float(val) for n, val in zip(NAMES, np.asarray(x, dtype=float))}


def vector(d: dict[str, float]) -> np.ndarray:
    return np.array([d[n] for n in NAMES], dtype=float)
