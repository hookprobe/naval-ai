"""The validation ladder orchestrator: L0 -> L1 -> L2 (-> L3, operator-run).

Every result is tier-badged and uncertainty-carrying (BuildPlan honesty rule 1)
and can be appended to the provenance DB (rule: nothing exists unless recorded).

`evaluate()` climbs to L1. `revalidate()` is the escalation verb honesty rule 2
("any kept design re-validates up the ladder") always described and never had:
until it existed, `navalai.seakeeping` was imported outside the tests by exactly
one caller — a print-only spot-check in `scripts/demo_mission.py` — and
`navalai.cfd` only by operator CLIs, so `Evaluation.tier` read "L1" in 100% of
~2000 evaluations. There was no code path by which a design could reach L2 at
all, which makes rule 2 a sentence rather than a mechanism.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, replace

import numpy as np

from . import db, grammar
from .energy import (EnergyReport, WeightBudget, energy_report, weight_budget,
                     weight_items)
from .geometry import RHO_WATER, Hull
from .hydrostatics import HydroState, gm, gm_long, solve_to_displacement
from .limits import (FREEBOARD_FLOOR_M, LCB_BAND_PCT_LWL, LIST_LIMIT_DEG,
                     TRIM_LIMIT_DEG, gm_floor, min_bend_radius_m)
from .mission import MissionSpec
from .resistance import (FN_MICHELL_MAX, ResistanceResult,
                         total_resistance)
from .rules import report as rules_report
from .rules.iso12215 import assess as scantling_rules
from .rules.iso12215 import select_stock_thickness_m
from .rules.iso12217 import assess as stability_rules
from .weights import MassAggregate, MassItem, aggregate, trim_angle_deg


# The ladder's inequality constraints, in one place, as g <= 0 == feasible.
# The optimizer used to re-derive these by hand from Evaluation fields, with
# its own copies of the numbers (0.25 freeboard, 80*0.015 bend radius). That
# guarantees drift: a check added to evaluate() stayed invisible to NSGA-II,
# so the optimizer would return designs the ladder then called violations.
# Both now read the SAME dict.
# "rules" joined the vector because TIER R WAS NOT IN THE PIPELINE AT ALL.
# Import scan of the whole package: NOTHING imported navalai.rules except the
# tests and a demo script. It was not in evaluate(), not in CONSTRAINT_NAMES,
# not in the NSGA-II constraint vector and not in the agent shell, so a hull
# that failed ISO 12215-5 or the offset-load heel came back ok=True and
# exported. PLM.md section 1 lists the rules tier as a platform truth mechanism
# that "fails closed"; it was a print statement in a demo.
# "list" IS A RESERVED TIER-E/F HOOK, AND SAYING SO IS THE POINT (gap E13).
# It read EXACTLY -2.000 across 800 evaluations, because `agg.tcg_m` is
# identically 0 while no mass item declares a transverse offset — and nothing
# in the product declares one yet, so on today's inputs it is a green light
# occupying an NSGA-II constraint dimension. It is KEPT rather than deleted for
# two reasons, both of which are now gate tests rather than assurances:
#   1. it is LIVE, not dead. Give any item a y_m and it moves; the trade it
#      constrains is the one tier E (arrangement) and tier F (tanks, foam) will
#      produce, and a galley to port is the ordinary case, not an exotic one.
#      `tests/test_stageB.py` moves 300 kg 0.8 m off centreline and asserts the
#      constraint moves with it.
#   2. after E11 it is no longer unconditionally satisfiable: a hull with
#      GM <= 0 has no upright equilibrium to heel about, so `list` goes
#      INFEASIBLE_G rather than -2.000.
# What would NOT be honest is to leave it reading -2.000 forever and describe
# the ladder as having six live constraints. It has five plus this one.
#
# "lcb" joined because LCB WAS UNCONSTRAINED ANYWHERE (gap B8) — measured at
# -6.47 and -7.86 %LWL on delivered hulls, and see `limits.LCB_BAND_PCT_LWL`.
# "proportions" joined because L0 CHECKED THE PARAMETER VECTOR AND NOTHING EVER
# RE-CHECKED THE HULL (gap B9): `grammar.check` bounds BWL/T at 12 on the
# design draft, and a delivered hull floated at B/T 14.4 — the project's own
# bar broken by the project's own output, with every gate green.
CONSTRAINT_NAMES = ("freeboard", "gm", "bend_radius", "trim", "list",
                    "lcb", "proportions", "rules")

# The value a constraint takes when the physics behind it is UNDEFINED rather
# than merely violated: large, positive, finite. Large so NSGA-II ranks such a
# design below every genuinely-infeasible one; positive so it is a violation;
# FINITE so it never re-enters the ladder as the nan this exists to stop.
# optimize.py imports it rather than keeping its own 1e3, because a number
# declared twice is this codebase's recurring defect.
INFEASIBLE_G = 1e3


class ConstraintOrderError(RuntimeError):
    """The constraint dict does not match CONSTRAINT_NAMES exactly.

    A REAL exception, because the invariant it guards used to be an `assert`
    (gap E16) and `python -O` strips asserts — verified, `__debug__` is False
    under -O. `optimize.py` builds its G matrix as `[ev.g[k] for k in
    CONSTRAINT_NAMES]`, so a g dict that gained, lost or reordered a key would,
    under -O, silently map the freeboard margin onto the GM column and the
    optimiser would descend a constraint it was not shown. `constraint_vector`
    below both ORDERS and CHECKS, so order is now established by construction
    and the check that remains cannot be optimised away.
    """


def constraint_vector(values: dict[str, float]) -> dict[str, float]:
    """Return `values` as a dict keyed in CONSTRAINT_NAMES order, or raise.

    Building the vector FROM the names is the fix for E16: the order is no
    longer a property of the literal a human typed, it is a property of the
    tuple the optimizer reads.
    """
    missing = [k for k in CONSTRAINT_NAMES if k not in values]
    extra = [k for k in values if k not in CONSTRAINT_NAMES]
    if missing or extra:
        raise ConstraintOrderError(
            f"constraint vector does not match CONSTRAINT_NAMES: "
            f"missing {missing}, unexpected {extra}. Every name in "
            f"CONSTRAINT_NAMES is a column of the optimizer's G matrix; a "
            f"vector that does not cover them exactly cannot be mapped onto it.")
    return {k: values[k] for k in CONSTRAINT_NAMES}


def is_real_finite(v) -> bool:
    """True only for a value that is a real, finite float.

    Not `math.isfinite` directly: `isfinite` RAISES on a complex, and a complex
    is one of the shapes this guard exists to catch. `navalai.holtrop` measured
    a resistance of 8504.47-1749.72j landing in a float-typed dataclass field
    from a negative fractional power — so "not a number" here means nan, inf,
    complex, or anything that will not become a float at all.
    """
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


# The ladder, in order. A tier badge is only ever allowed to move RIGHT along
# this tuple, and only when the solver named by that tier has actually run.
TIER_ORDER = ("L0", "L1", "L2", "L3")


def tier_rank(tier: str) -> int:
    """Position on the ladder. Unknown badges rank below L0 rather than throw,
    so a comparison can never silently promote something it does not know."""
    base = tier.split("-")[0]          # 'L1-INVALID' is not an L1 result
    return TIER_ORDER.index(base) if (base in TIER_ORDER
                                      and base == tier) else -1


class TierRefusal(RuntimeError):
    """The ladder was asked for a tier it cannot honestly deliver here.

    The point of a distinct exception is that the ONE thing escalation must
    never do is return a lower-tier number wearing a higher-tier badge. Every
    branch of revalidate() that cannot compute the tier it was asked for
    raises; none of them degrades quietly.
    """


class TierUnavailable(TierRefusal):
    """The solver for that tier is not installed on this machine."""


class TierRequiresOperator(TierRefusal):
    """That tier is a supervised campaign, not an in-process call."""


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
    # None, NOT 0.0, when the equilibrium the angle describes does not exist.
    # 0.0 is the BEST POSSIBLE value of both, so returning it for a hull that
    # had just gone longitudinally or transversely unstable reported the
    # pathological state as the ideal one (gap E11).
    trim_deg: float | None = None         # + = bow down
    list_deg: float | None = None         # + = heel to starboard
    resistance: ResistanceResult | None = None
    energy: EnergyReport | None = None
    ply_thickness_m: float = 0.0    # DERIVED from ISO 12215-5, not declared
    unaccounted_frac: float = 0.0   # displacement with no declared position
    hull_lwl_m: float = 0.0         # so requirements can check the mission
    rules: dict = field(default_factory=dict)   # tier R, IN the ladder
    seakeeping: dict = field(default_factory=dict)   # tier L2, when it has run
    # The genome that produced this evaluation, so a kept design can be handed
    # to revalidate() as itself rather than as a loose array the caller has to
    # keep paired with it by hand. compare=False because an ndarray field makes
    # dataclass __eq__ raise.
    params: np.ndarray | None = field(default=None, repr=False, compare=False)
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
        return Evaluation(False, "L0", rep.violations, params=np.asarray(params),
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
                          ply_thickness_m=t_ply, params=np.asarray(params),
                          eval_ms=(time.perf_counter() - t0) * 1e3)

    # Free-surface correction is a VIRTUAL RISE of G, so it is subtracted from
    # GM. With no slack tanks declared it is exactly zero; the moment a tier-F
    # tank is added it stops being zero, which is the whole point of carrying it.
    kg = agg.vcg_above_keel(t_design)
    fsc = agg.free_surface_correction()
    gm_m = gm(hs, kg) - fsc
    gm_l_m = gm_long(hs, kg)
    # UNDEFINED IS NOT IDEAL (gap E11). Both of these used to fall back to 0.0
    # — the best possible value of each — exactly where the physics behind them
    # stopped existing, so the two constraints they feed were "satisfied" on
    # precisely the hulls that had lost longitudinal or transverse stability.
    # None here, INFEASIBLE_G below, and a violation naming the state.
    trim = trim_angle_deg(agg, hs.lcb, hs.disp_kg, gm_l_m)
    # List from a transverse offset: tan(phi) = TCG / GM. Zero while every item
    # sits on centreline, non-zero as soon as an arrangement is asymmetric.
    heel = (math.degrees(math.atan(agg.tcg_m / gm_m))
            if (is_real_finite(gm_m) and gm_m > 1e-6) else None)

    gm_min = gm_floor(mission.design_category)
    r_min = hull.min_bend_radius()
    # Call the helper rather than re-deriving it: `min_bend_radius_m` existed
    # and had no callers while this line recomputed the same product inline.
    # It now follows the DERIVED sheet, so a boat that needs thicker ply also
    # gets a larger required bend radius — the coupling limits.py claimed.
    r_req = min_bend_radius_m(t_ply)

    u = mission.cruise_speed_ms()
    res = total_resistance(hull, u, hs.wetted, hs.cb, rho, wl)
    early: list[str] = []
    if not res.valid:
        # Reported as a violation, not buried in a badge: at Fn > 0.45 the
        # thin-ship model is answering a different question than the mission.
        early.append(
            f"speed outside the L1 model: Fn {res.fn:.2f} > {FN_MICHELL_MAX} "
            f"(planing regime — Michell thin-ship has no dynamic lift, trim or "
            f"spray; needs a Savitsky-class method)")
    en = energy_report(res.total, u, hull.deck_area(), mission.energy)

    ev_for_rules = Evaluation(
        ok=True, tier="L1", hydro=hs, wl=wl, weights=wb, masses=agg,
        gm_m=gm_m, gm_l_m=gm_l_m, ply_thickness_m=t_ply)
    findings = (stability_rules(ev_for_rules, mission.design_category,
                                mission.crew, 2.0 * float(hull.y_chine.max()))
                + scantling_rules(hs.disp_kg, t_ply * 1e3))
    rules_rep = rules_report(findings)
    # One continuous margin so NSGA-II can descend it: 0 when every rule
    # passes, else the worst RELATIVE shortfall. A boolean would give the
    # optimiser no gradient to follow out of an infeasible region.
    fails = [f for f in findings if not f.passed]

    # Proportions re-checked on the FLOATED hull, against the same bands L0
    # applied to the parameter vector (gap B9). `grammar.proportion_margins` is
    # the shared kernel, so the two states cannot be judged by different numbers.
    props = grammar.proportion_margins(hs.lwl_eff, hs.b_wl_max, hs.draft)
    worst_prop = max(props, key=lambda k: props[k])

    # Built FROM CONSTRAINT_NAMES, not typed in an order that happened to match
    # (gap E16 — the `assert` that used to bind them is stripped by `python -O`).
    g = constraint_vector({
        "freeboard": FREEBOARD_FLOOR_M - hs.freeboard_min,
        "gm": gm_min - gm_m,
        "bend_radius": r_req - r_min,
        "trim": INFEASIBLE_G if trim is None else abs(trim) - TRIM_LIMIT_DEG,
        "list": INFEASIBLE_G if heel is None else abs(heel) - LIST_LIMIT_DEG,
        "lcb": abs(hs.lcb_pct_lwl) - LCB_BAND_PCT_LWL,
        "proportions": props[worst_prop],
        "rules": (max(abs(f.measured - f.required) / max(abs(f.required), 1e-9)
                      for f in fails) if fails else -0.01),
    })
    why = {
        "freeboard": f"freeboard at load {hs.freeboard_min:.2f} m "
                     f"< {FREEBOARD_FLOOR_M:.2f} m",
        "gm": f"GM {gm_m:.2f} m < {gm_min:.2f} m "
              f"(category {mission.design_category} floor, ISO 12217)",
        "bend_radius": f"panel bend radius {r_min:.2f} m < {r_req:.2f} m "
                       f"({t_ply * 1e3:.0f} mm ply cold-bend limit)",
        "trim": (f"static trim is UNDEFINED: GM_L {gm_l_m:+.2f} m is not "
                 f"positive, so the hull has no longitudinal equilibrium to "
                 f"trim about (LCG {agg.lcg_m:.2f} m vs LCB {hs.lcb:.2f} m)"
                 if trim is None else
                 f"static trim {trim:+.2f} deg exceeds {TRIM_LIMIT_DEG:.1f} deg "
                 f"(LCG {agg.lcg_m:.2f} m vs LCB {hs.lcb:.2f} m)"),
        "list": (f"static list is UNDEFINED: GM {gm_m:+.3f} m is not positive, "
                 f"so the hull has no upright equilibrium to heel about "
                 f"(TCG {agg.tcg_m:+.3f} m off centreline)"
                 if heel is None else
                 f"static list {heel:+.2f} deg exceeds {LIST_LIMIT_DEG:.1f} deg "
                 f"(TCG {agg.tcg_m:+.3f} m off centreline)"),
        "lcb": f"LCB {hs.lcb_pct_lwl:+.2f} %LWL from midships is outside "
               f"+-{LCB_BAND_PCT_LWL:.1f}% (LCB {hs.lcb:.2f} m on a floated "
               f"waterline of {hs.lwl_eff:.2f} m)",
        "proportions": f"floated {worst_prop} outside its band: L/B "
                       f"{hs.lwl_eff / max(hs.b_wl_max, 1e-9):.2f} "
                       f"{list(grammar.L_OVER_B_BAND)}, B/T "
                       f"{hs.b_wl_max / max(hs.draft, 1e-9):.2f} "
                       f"{list(grammar.B_OVER_T_BAND)} — L0 checked the design "
                       f"draft, this is the hull that floated",
        "rules": ("rules tier: " + "; ".join(
            f"{f.rule_id} {f.measured:.2f} vs {f.required:.2f} {f.unit}"
            for f in fails)) if fails else "",
    }

    # A NON-FINITE CONSTRAINT USED TO MAKE A DESIGN FEASIBLE (gap E10).
    # `[why[k] for k, v in g.items() if v > 0.0]` reads as a violation filter,
    # but `nan > 0.0` is False, so ANY nan constraint produced violations=[]
    # and ok=True. VERIFIED end to end: a nan cruise speed gave Rt=nan, Fn=nan
    # and Wh/NM=nan, was written to the provenance DB as a badge sigma, and was
    # emitted over HTTP as a bare `NaN` — which is not valid JSON (RFC 8259),
    # so the response could not even be parsed by a conforming client. Honesty
    # rule 1 says every quantity carries value, tier and sigma; nan is not a
    # value, and "we could not compute it" is never a pass.
    viol: list[str] = []
    for k in CONSTRAINT_NAMES:
        v = g[k]
        if not is_real_finite(v):
            viol.append(f"constraint {k!r} is not a finite number ({v!r}) — the "
                        f"quantity behind it could not be computed, which is a "
                        f"violation and never a pass")
            g[k] = INFEASIBLE_G
        elif v > 0.0:
            viol.append(why[k])
    viol.extend(early)

    # Sigmas that are DERIVED carry it; sigmas that are still a declared
    # fraction say so. The mass model computes a real sigma (`agg.sigma_kg`,
    # 178 kg / 6.4% on the reference hull, and much larger once the unaccounted
    # mass declares its 50%) and evaluate() used to throw it away in favour of a
    # flat 0.02*disp — a decoration in a column documented as one-sigma. KG
    # uncertainty now reaches GM through the mass lever, so a boat whose weights
    # are poorly known reports a correspondingly vague GM instead of a confident
    # one.
    badges = {
        "displacement": ("L1", agg.sigma_kg, "measured"),
        "GM": ("L1", agg.sigma_kg / max(agg.total_kg, 1e-9)
               * abs(kg) + 0.05, "measured"),
        # A number outside its model's validity is not an L1 quantity.
        "resistance": ("L1" if res.valid else "L1-INVALID",
                       res.uncertainty, "measured"),
        "wh_per_nm": ("L1", en.wh_per_nm * 0.30, "assumed"),
    }
    # THE SAME DEFECT ON THE OTHER SIDE OF THE BADGE (gap E10). A constraint
    # cannot go nan on its own — it goes nan because the quantity it was
    # computed from did, and that quantity is what gets recorded and served.
    # Every badged quantity is checked HERE, with its sigma, so an unusable
    # number cannot leave evaluate() wearing a plain "L1".
    values = {"displacement": hs.disp_kg, "GM": gm_m,
              "resistance": res.total, "wh_per_nm": en.wh_per_nm}
    for name, val in values.items():
        tier_b, sigma, basis = badges[name]
        bad = []
        if not is_real_finite(val):
            bad.append(f"value {val!r}")
        if not is_real_finite(sigma) or float(sigma) < 0.0:
            bad.append(f"sigma {sigma!r}")
        if bad:
            viol.append(
                f"{name} is not a reportable L1 quantity ({', '.join(bad)}) — "
                f"honesty rule 1 wants value, tier and sigma, and this has no "
                f"value to badge")
            badges[name] = (f"{tier_b.split('-')[0]}-INVALID", sigma, basis)

    ev = Evaluation(
        ok=len(viol) == 0, tier="L1", violations=tuple(viol), hydro=hs, wl=wl,
        weights=wb, masses=agg, gm_m=gm_m, gm_l_m=gm_l_m,
        trim_deg=trim, list_deg=heel, resistance=res, energy=en, g=g,
        ply_thickness_m=t_ply, unaccounted_frac=unaccounted_frac,
        hull_lwl_m=float(p["LWL"]), rules=rules_rep, params=np.asarray(params),
        eval_ms=(time.perf_counter() - t0) * 1e3, badges=badges,
    )

    if provenance is not None:
        hid = provenance.add_hull(params)
        # A non-finite number is NOT written. The provenance DB is the record of
        # what the ladder computed, and nan is a record that it did not compute
        # anything — it reached the `uncertainty` column and then the HTTP
        # response as literal `NaN`, which no conforming JSON parser accepts.
        # The refusal is not silent: it is already in ev.violations above, so
        # the missing row and the reason for it are both visible.
        rows = (("michell+ittc57", f"Rt_N@{u:.2f}", res.total, res.uncertainty,
                 {"fn": res.fn, "wl": wl}),
                ("hydrostatics", "GM_m", gm_m, ev.badges["GM"][1],
                 {"kg": wb.kg_above_keel}),
                ("energy", "wh_per_nm", en.wh_per_nm, ev.badges["wh_per_nm"][1],
                 {}))
        for method, q, val, sig, meta in rows:
            if is_real_finite(val) and is_real_finite(sig):
                provenance.add_result(hid, "L1", method, "0.1", q,
                                      float(val), float(sig), meta)
    return ev


# Small on purpose. L2 escalation is meant to be affordable enough that a kept
# design is re-validated as a matter of course rather than as an event: the
# reference hull costs ~0.7 s for both meshes and the RAO together. Three
# frequencies straddle the heave resonance of a small craft.
_L2_OMEGAS = np.array([0.6, 1.0, 1.6])
# Two mesh levels, so the sigma the L2 badge carries is a MEASURED
# discretisation uncertainty and not a declared fraction. seakeeping.py's own
# docstring names mesh sensitivity as mandatory (NREL/OMAE 2024); a single-mesh
# BEM result has no basis for an error bar at all.
_L2_MESHES = ((20, 5), (28, 7))


def revalidate(design, mission: MissionSpec, target_tier: str = "L2",
               provenance: db.Provenance | None = None,
               rho: float = RHO_WATER, omegas: np.ndarray | None = None
               ) -> Evaluation:
    """Re-validate a kept design UP the ladder and return the promoted result.

    `design` is either an `Evaluation` (as returned by `evaluate()`, carrying
    its own genome) or a raw parameter vector, which is evaluated to L1 first.

    The returned Evaluation's `tier` is the HIGHEST tier that actually ran, so
    an L2 result supersedes the L1 badge and the badges dict gains the L2
    quantities alongside the L1 ones it did not recompute. Promotion is
    monotone: `tier_rank(out.tier) >= tier_rank(in.tier)` always, and asking
    for a tier at or below the one already reached is a no-op rather than a
    demotion.

    Raises `TierRefusal` (or a subclass) rather than returning anything for a
    tier it could not compute — see the class docstring for why that asymmetry
    is the whole point.

    Provenance: the L1 rows are written by `evaluate()`, so passing a genome
    (rather than an already-evaluated `Evaluation`) is what makes a hull's
    history show the L2 row superseding its own L1 row in one call. Passing an
    Evaluation that was produced without a provenance writes L2 rows against a
    hull that has no L1 rows — true, and visible, rather than back-filled.
    """
    if isinstance(design, Evaluation):
        ev = design
        if ev.params is None:
            raise TierRefusal(
                "this Evaluation carries no genome, so there is nothing to "
                "re-validate — pass the parameter vector instead")
        params = np.asarray(ev.params, float)
    else:
        params = np.asarray(design, float)
        ev = evaluate(params, mission, rho, provenance)

    if target_tier not in TIER_ORDER:
        raise ValueError(f"{target_tier!r} is not a tier: {TIER_ORDER}")
    if tier_rank(target_tier) <= tier_rank(ev.tier):
        return ev                       # already there; never step backwards

    if ev.hydro is None:
        raise TierRefusal(
            f"cannot escalate to {target_tier}: this design has no L1 state "
            f"(tier {ev.tier}, {'; '.join(ev.violations) or 'no reason given'})"
            f". L2 needs the floated waterline and L3 needs a hull that passed "
            f"L0 — the ladder is climbed, not skipped.")

    if target_tier == "L3":
        # THE SEAM EXISTS AND IT IS HONEST. L3 is a multi-hour supervised
        # OpenFOAM campaign (the KCS case on this machine is ~6 h on 10 ranks,
        # resumable because thermal sleep kills it), so there is no truthful
        # way to answer an in-process call with an L3 number. What would be
        # dishonest is to fall back to the L1 result and badge it L3.
        raise TierRequiresOperator(
            "L3 (RANS) is not an in-process tier. Generate the case with "
            "`python scripts/make_case.py --out runs/<name> --speed U --np 10`, "
            "run it with `openfoam navalai/cfd/run-case.sh runs/<name> 10`, and "
            "post it with `python scripts/post_gci.py runs/<name>`; the result "
            "then enters the ladder through the provenance DB as an L3 row. "
            "No L3 badge is issued for a number L3 did not produce.")

    # ---- L2: zero-speed radiation/diffraction (Capytaine BEM) --------------
    try:
        from . import seakeeping
        import capytaine as _cpt          # noqa: F401  (presence check only)
    except Exception as e:                # pragma: no cover - env dependent
        raise TierUnavailable(
            f"L2 needs Capytaine and it is not importable here ({e}). Install "
            f"requirements-optional.txt, or run the ladder to L1 and say L1 — "
            f"an L2 badge without Capytaine would name a solver that never "
            f"ran.") from e

    w = _L2_OMEGAS if omegas is None else np.asarray(omegas, float)
    hull = Hull(params)
    try:
        (nx0, nz0), (nx1, nz1) = _L2_MESHES
        am0, _dp0, _n0 = seakeeping.heave_coeffs(hull, w, nx0, nz0, rho)
        am1, dp1, npan = seakeeping.heave_coeffs(hull, w, nx1, nz1, rho)
        rao = seakeeping.heave_rao(hull, w, ev.hydro.disp_kg, ev.hydro.awp,
                                   nx1, nz1, rho)
    except Exception as e:
        raise TierUnavailable(
            f"the L2 solve failed on this hull ({type(e).__name__}: {e}); no "
            f"L2 badge is issued") from e

    # Worst relative mesh-to-mesh change across the frequency set. This is the
    # honest one-sigma basis: it is what the convergence sweep measures.
    unc_rel = float(np.max(np.abs(am1 - am0) / np.maximum(np.abs(am1), 1e-12)))
    sk = {
        "omegas": w.tolist(),
        "added_mass_heave": am1.tolist(),
        "damping_heave": dp1.tolist(),
        "rao_heave": rao.tolist(),
        "n_panels": int(npan),
        "uncertainty_rel": unc_rel,
        "solver": "capytaine",
    }

    if provenance is not None:
        hid = provenance.add_hull(params)
        ver = getattr(_cpt, "__version__", "unknown")
        for wi, a, b, r in zip(w, am1, dp1, rao):
            meta = {"omega": float(wi), "n_panels": int(npan),
                    "meshes": list(_L2_MESHES), "basis": "mesh convergence"}
            provenance.add_result(hid, "L2", "capytaine", ver,
                                  f"A33_kg@{wi:.2f}", float(a),
                                  unc_rel * abs(float(a)), meta)
            provenance.add_result(hid, "L2", "capytaine", ver,
                                  f"B33_Ns_per_m@{wi:.2f}", float(b),
                                  unc_rel * abs(float(b)), meta)
            provenance.add_result(hid, "L2", "capytaine", ver,
                                  f"RAO_heave@{wi:.2f}", float(r),
                                  unc_rel * abs(float(r)), meta)

    badges = dict(ev.badges)
    badges["heave_added_mass"] = ("L2", unc_rel * float(np.max(np.abs(am1))),
                                  "measured")
    badges["heave_rao"] = ("L2", unc_rel * float(np.max(np.abs(rao))),
                           "measured")
    return replace(ev, tier="L2", seakeeping=sk, badges=badges)
