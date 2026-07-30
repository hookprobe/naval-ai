"""The validation ladder orchestrator: L0 -> L1 (-> L2/L3 escalation hooks).

Every result is tier-badged and uncertainty-carrying (BuildPlan honesty rule 1)
and can be appended to the provenance DB (rule: nothing exists unless recorded).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from . import db, grammar
from .energy import EnergyReport, WeightBudget, energy_report, weight_budget
from .geometry import RHO_WATER, Hull
from .hydrostatics import HydroState, gm, solve_to_displacement
from .mission import MissionSpec
from .resistance import ResistanceResult, total_resistance


@dataclass
class Evaluation:
    ok: bool
    tier: str                       # highest tier reached
    violations: tuple[str, ...] = ()
    hydro: HydroState | None = None
    wl: float = 0.0                 # floated waterline vs design WL
    weights: WeightBudget | None = None
    gm_m: float | None = None
    resistance: ResistanceResult | None = None
    energy: EnergyReport | None = None
    eval_ms: float = 0.0
    badges: dict = field(default_factory=dict)   # quantity -> (tier, sigma)


def evaluate(params: np.ndarray, mission: MissionSpec,
             rho: float = RHO_WATER,
             provenance: db.Provenance | None = None) -> Evaluation:
    """Run the ladder as far as L1. Fails fast and cheap (Fitness=inf pattern)."""
    t0 = time.perf_counter()

    rep = grammar.check(params)
    if not rep.ok:
        return Evaluation(False, "L0", rep.violations,
                          eval_ms=(time.perf_counter() - t0) * 1e3)

    hull = Hull(params)
    p = grammar.named(params)

    # weight budget first: the boat must float AT its real weight, not a wish
    wb = weight_budget(p["LWL"], p["D"], hull.wetted_surface(0.0) * 1.6,
                       hull.deck_area(), mission.energy)
    target = max(wb.total_kg, mission.displacement_target_kg)
    try:
        hs, wl = solve_to_displacement(hull, target, rho)
    except ValueError as e:
        return Evaluation(False, "L1", (f"floatation: {e}",), weights=wb,
                          eval_ms=(time.perf_counter() - t0) * 1e3)

    gm_m = gm(hs, wb.kg_above_keel)
    viol = []
    if hs.freeboard_min < 0.25:
        viol.append(f"freeboard at load {hs.freeboard_min:.2f} m < 0.25 m")
    if gm_m < 0.35:
        viol.append(f"GM {gm_m:.2f} m < 0.35 m (L1 floor; ISO 12217 check is tier R)")

    u = mission.cruise_speed_ms()
    res = total_resistance(hull, u, hs.wetted, hs.cb, rho, wl)
    en = energy_report(res.total, u, hull.deck_area(), mission.energy)

    ev = Evaluation(
        ok=len(viol) == 0, tier="L1", violations=tuple(viol), hydro=hs, wl=wl,
        weights=wb, gm_m=gm_m, resistance=res, energy=en,
        eval_ms=(time.perf_counter() - t0) * 1e3,
        badges={
            "displacement": ("L1", 0.02 * hs.disp_kg),
            "GM": ("L1", 0.15 * abs(gm_m) + 0.05),
            "resistance": ("L1", res.uncertainty),
            "wh_per_nm": ("L1", en.wh_per_nm * 0.30),
        },
    )

    if provenance is not None:
        hid = provenance.add_hull(params)
        q = f"Rt_N@{u:.2f}"
        provenance.add_result(hid, "L1", "michell+ittc57", "0.1", q,
                              res.total, res.uncertainty,
                              {"fn": res.fn, "wl": wl})
        provenance.add_result(hid, "L1", "hydrostatics", "0.1", "GM_m", gm_m,
                              ev.badges["GM"][1], {"kg": wb.kg_above_keel})
        provenance.add_result(hid, "L1", "energy", "0.1", "wh_per_nm",
                              en.wh_per_nm, ev.badges["wh_per_nm"][1], {})
    return ev
