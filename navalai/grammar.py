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
    # C33 slenderness / stability proportions
    lb = lwl / bwl
    _rel("L/B", 2.2 <= lb <= 8.5, f"L/B {lb:.2f} outside [2.2, 8.5]", v)
    bt = bwl / t
    _rel("B/T", 1.8 <= bt <= 12.0, f"B/T {bt:.2f} outside [1.8, 12]", v)
    # C35 deadrise ordering (bow at least as steep as midship)
    _rel("deadrise.order", bbow >= bmid, f"beta_bow {bbow:.1f} < beta_mid {bmid:.1f}", v)
    # C36 chine must stay submerged-ish at midship: z_chine = -T + (B/2) tan(beta)
    z_chine = -t + 0.5 * bwl * math.tan(math.radians(bmid))
    _rel("chine.height", z_chine <= 0.25 * t, f"mid chine {z_chine:.2f} m above 0.25T", v)
    # C37 chine below sheer
    _rel("chine.below.sheer", z_chine <= fb - 0.05, "chine reaches sheer", v)
    # C38 keel profile sanity: rocker+forefoot cannot lift keel through WL amidships
    _rel("keel.rocker", rock * t <= 0.75 * t, "rocker lifts transom keel above 0.75T", v)
    _rel("keel.forefoot", ff <= 1.0, "forefoot beyond stem", v)
    # C40 transom immersion: transom chine z with rocker must not fly high
    z_ch_tr = -t * (1.0 - rock) + rtr * 0.5 * bwl * math.tan(math.radians(bmid))
    _rel("transom.chine", z_ch_tr <= 0.35 * t, f"transom chine {z_ch_tr:.2f} m too high", v)
    # C41 max-beam station keeps a finite run to both ends
    _rel("x_mb.margin", 0.05 * lwl <= xmb * lwl <= 0.95 * lwl, "max-beam at hull end", v)
    # C42 flare cannot fold the topside inboard past the chine at the sheer
    y_sheer_delta = (fb - z_chine) * math.tan(math.radians(flare))
    _rel("flare.fold", 0.5 * bwl + y_sheer_delta >= 0.15 * bwl, "sheer folds inboard", v)
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
