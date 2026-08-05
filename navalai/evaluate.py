"""The validation ladder orchestrator: L0 -> L1 (-> L2/L3 escalation hooks).

Every result is tier-badged and uncertainty-carrying (BuildPlan honesty rule 1)
and can be appended to the provenance DB (rule: nothing exists unless recorded).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np

from . import db, grammar
from .energy import (EnergyReport, WeightBudget, energy_report, weight_budget,
                     weight_items)
from .geometry import RHO_WATER, Hull
from .hydrostatics import HydroState, gm, gm_long, solve_to_displacement
from .limits import (FREEBOARD_FLOOR_M, LIST_LIMIT_DEG, TRIM_LIMIT_DEG,
                     gm_floor, min_bend_radius_m)
from .mission import MissionSpec
from .resistance import ResistanceResult, total_resistance
from .rules.iso12215 import select_stock_thickness_m
from .weights import MassAggregate, MassItem, aggregate, trim_angle_deg


# The ladder's inequality constraints, in one place, as g <= 0 == feasible.
# The optimizer used to re-derive these by hand from Evaluation fields, with
# its own copies of the numbers (0.25 freeboard, 80*0.015 bend radius). That
# guarantees drift: a check added to evaluate() stayed invisible to NSGA-II,
# so the optimizer would return designs the ladder then called violations.
# Both now read the SAME dict.
CONSTRAINT_NAMES = ("freeboard", "gm", "bend_radius", "trim", "list")


@dataclass
class Evaluation:
    ok: bool
    tier: str                       # highest tier reached
    violations: tuple[str, ...] = ()
    hydro: HydroState | None = None
    wl: float = 0.0                 # floated waterline vs design WL
    weights: WeightBudget | None = None
    masses: MassAggregate | None = None   # the positioned model (LCG/TCG/VCG)
    gm_m: float | None = None             # AFTER free-surface correction
    gm_l_m: float | None = None
    trim_deg: float = 0.0                 # + = bow down
    list_deg: float = 0.0                 # + = heel to starboard
    resistance: ResistanceResult | None = None
    energy: EnergyReport | None = None
    ply_thickness_m: float = 0.0    # DERIVED from ISO 12215-5, not declared
    unaccounted_frac: float = 0.0   # displacement with no declared position
    eval_ms: float = 0.0
    badges: dict = field(default_factory=dict)   # quantity -> (tier, sigma)
    g: dict = field(default_factory=dict)        # constraint -> value, <=0 feasible


def sample_valid(n: int, mission: MissionSpec, seed: int = 0,
                 quantity: str = "wh_per_nm"):
    """Sample n hulls that clear L0 AND produce a finite L1 evaluation.

    Returns (X, y) for surrogate training — the flywheel's data feed.
    """
    rng = np.random.default_rng(seed)
    X, y = [], []
    while len(X) < n:
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        ev = evaluate(x, mission)
        if ev.energy is None:
            continue
        val = {"wh_per_nm": ev.energy.wh_per_nm,
               "gm": ev.gm_m,
               "rt": ev.resistance.total}[quantity]
        X.append(x)
        y.append(val)
    return np.array(X), np.array(y)


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

    # Weight model first: the boat must float AT its real weight, not a wish.
    # The POSITIONED model is the one truth (weights.MassAggregate) — it used to
    # exist only in tests while the ladder read a separate scalar budget, so an
    # arrangement could move mass without moving the boat. weight_items()
    # reproduces weight_budget's masses and VCG exactly, so wiring it in changes
    # no number; it adds LCG, TCG and the free-surface moment, which the checks
    # below then have something to check.
    t_design = -float(hull.z_keel.min())
    # The bottom panel is DERIVED from ISO 12215-5 at the mission's loaded
    # displacement and rounded up to a stock sheet — it is not a declared
    # constant. Before this, `limits.PLY_THICKNESS_M` (15 mm) fed the structural
    # mass and the bend-radius limit while the same rule independently demanded
    # 18.24 mm for the same 6 t boat, and nothing in the ladder could see the
    # contradiction because the only caller that compared them hand-passed a
    # third value. mLDC is the mission target rather than the weight budget:
    # ISO's mLDC is the loaded displacement, and using the budget would make the
    # thickness depend on the mass it is about to change.
    t_ply = select_stock_thickness_m(mission.displacement_target_kg)
    shell = hull.wetted_surface(0.0) * 1.6      # computed once, not twice
    deck = hull.deck_area()
    wb = weight_budget(p["LWL"], p["D"], shell, deck, mission.energy, t_ply)
    items = weight_items(p["LWL"], p["D"], shell, deck, mission.energy,
                         t_design, t_ply)
    # THE UNACCOUNTED MASS IS DECLARED, NOT HIDDEN IN A max().
    # `target = max(budget, mission_target)` floated the hull at the mission's
    # displacement while KG, LCG and trim were computed from the budget alone.
    # MEASURED at the 6 t mission: 3230 kg — 54% of displacement — had no
    # declared position (77% at 12 t), and KG stayed pinned at 0.9330 m while
    # GM swung 3.80 -> 1.78 -> 0.78 m across those targets. Every stability
    # verdict, including the ISO R-GM pass, rested on a mass model that did not
    # sum to the displacement.
    #
    # It is placed at the aggregate's OWN centre, so it moves no centre it has
    # no right to move — putting it low would flatter GM, putting it high would
    # punish it, and we do not know which is true. What it carries instead is a
    # 50% sigma, so the ignorance is visible in the badge rather than absent
    # from the model. Tier E/F arrangements will replace it item by item.
    provisional = aggregate(items)
    gap_kg = mission.displacement_target_kg - provisional.total_kg
    if gap_kg > 0.0:
        items.append(MassItem(
            id="unaccounted", mass_kg=gap_kg,
            x_m=provisional.lcg_m, z_m=provisional.vcg_m, y_m=0.0,
            sigma_kg=0.5 * gap_kg, tier="L1",
            source="mission displacement target minus the modelled budget",
            basis="approx"))
    agg = aggregate(items)
    target = max(agg.total_kg, mission.displacement_target_kg)
    unaccounted_frac = gap_kg / max(target, 1e-9) if gap_kg > 0.0 else 0.0
    try:
        hs, wl = solve_to_displacement(hull, target, rho)
    except ValueError as e:
        return Evaluation(False, "L1", (f"floatation: {e}",), weights=wb,
                          ply_thickness_m=t_ply,
                          eval_ms=(time.perf_counter() - t0) * 1e3)

    # Free-surface correction is a VIRTUAL RISE of G, so it is subtracted from
    # GM. With no slack tanks declared it is exactly zero; the moment a tier-F
    # tank is added it stops being zero, which is the whole point of carrying it.
    kg = agg.vcg_above_keel(t_design)
    fsc = agg.free_surface_correction()
    gm_m = gm(hs, kg) - fsc
    gm_l_m = gm_long(hs, kg)
    trim = trim_angle_deg(agg, hs.lcb, hs.disp_kg, gm_l_m)
    # List from a transverse offset: tan(phi) = TCG / GM. Zero while every item
    # sits on centreline, non-zero as soon as an arrangement is asymmetric.
    heel = math.degrees(math.atan(agg.tcg_m / gm_m)) if gm_m > 1e-6 else 0.0

    gm_min = gm_floor(mission.design_category)
    r_min = hull.min_bend_radius()
    # Call the helper rather than re-deriving it: `min_bend_radius_m` existed
    # and had no callers while this line recomputed the same product inline.
    # It now follows the DERIVED sheet, so a boat that needs thicker ply also
    # gets a larger required bend radius — the coupling limits.py claimed.
    r_req = min_bend_radius_m(t_ply)
    g = {
        "freeboard": FREEBOARD_FLOOR_M - hs.freeboard_min,
        "gm": gm_min - gm_m,
        "bend_radius": r_req - r_min,
        "trim": abs(trim) - TRIM_LIMIT_DEG,
        "list": abs(heel) - LIST_LIMIT_DEG,
    }
    assert tuple(g) == CONSTRAINT_NAMES, "constraint order must match the names"
    why = {
        "freeboard": f"freeboard at load {hs.freeboard_min:.2f} m "
                     f"< {FREEBOARD_FLOOR_M:.2f} m",
        "gm": f"GM {gm_m:.2f} m < {gm_min:.2f} m "
              f"(category {mission.design_category} floor, ISO 12217)",
        "bend_radius": f"panel bend radius {r_min:.2f} m < {r_req:.2f} m "
                       f"({t_ply * 1e3:.0f} mm ply cold-bend limit)",
        "trim": f"static trim {trim:+.2f} deg exceeds {TRIM_LIMIT_DEG:.1f} deg "
                f"(LCG {agg.lcg_m:.2f} m vs LCB {hs.lcb:.2f} m)",
        "list": f"static list {heel:+.2f} deg exceeds {LIST_LIMIT_DEG:.1f} deg "
                f"(TCG {agg.tcg_m:+.3f} m off centreline)",
    }
    viol = [why[k] for k, v in g.items() if v > 0.0]

    u = mission.cruise_speed_ms()
    res = total_resistance(hull, u, hs.wetted, hs.cb, rho, wl)
    en = energy_report(res.total, u, hull.deck_area(), mission.energy)

    ev = Evaluation(
        ok=len(viol) == 0, tier="L1", violations=tuple(viol), hydro=hs, wl=wl,
        weights=wb, masses=agg, gm_m=gm_m, gm_l_m=gm_l_m,
        trim_deg=trim, list_deg=heel, resistance=res, energy=en, g=g,
        ply_thickness_m=t_ply, unaccounted_frac=unaccounted_frac,
        eval_ms=(time.perf_counter() - t0) * 1e3,
        # Sigmas that are DERIVED carry it; sigmas that are still a declared
        # fraction say so. The mass model computes a real sigma
        # (`agg.sigma_kg`, 178 kg / 6.4% on the reference hull, and much larger
        # once the unaccounted mass declares its 50%) and evaluate() used to
        # throw it away in favour of a flat 0.02*disp — a decoration in a
        # column documented as one-sigma. KG uncertainty now reaches GM through
        # the mass lever, so a boat whose weights are poorly known reports a
        # correspondingly vague GM instead of a confident one.
        badges={
            "displacement": ("L1", agg.sigma_kg, "measured"),
            "GM": ("L1", agg.sigma_kg / max(agg.total_kg, 1e-9)
                   * abs(kg) + 0.05, "measured"),
            "resistance": ("L1", res.uncertainty, "measured"),
            "wh_per_nm": ("L1", en.wh_per_nm * 0.30, "assumed"),
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
