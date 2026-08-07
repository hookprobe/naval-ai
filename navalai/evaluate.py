"""The validation ladder orchestrator: L0 -> L1 -> L2 -> L3 -> R.

Every result is tier-badged and uncertainty-carrying (BuildPlan honesty rule 1)
and can be appended to the provenance DB (rule: nothing exists unless recorded).

`evaluate()` climbs to L1. `revalidate()` is the escalation verb honesty rule 2
("any kept design re-validates up the ladder") always described and never had:
until it existed, `navalai.seakeeping` was imported outside the tests by exactly
one caller — a print-only spot-check in `scripts/demo_mission.py` — and
`navalai.cfd` only by operator CLIs, so `Evaluation.tier` read "L1" in 100% of
~2000 evaluations. There was no code path by which a design could reach L2 at
all, which makes rule 2 a sentence rather than a mechanism.

L3 IS READ, NEVER RUN (gap A1). A RANS campaign is hours of supervised compute
on a machine this process is not entitled to start — the KCS case is ~6 h on 10
ranks and this Mac's thermal sleep kills it mid-run — so `revalidate(...,
"L3")` opens no solver. It reads a RECORDED campaign: a case directory that has
already been run, or an L3 row already in the provenance DB. When neither
exists it says NO EVIDENCE AT THIS TIER and names the operator route. The one
thing it must never do is hand back the L1 number wearing an L3 badge, and the
second thing it must never do is accept somebody else's run as this hull's —
`l3_case_evidence` checks the recorded geometry against the genome before it
will quote a drag (see gate2m.py's own incident: it applied the KRISO KCS tank
data to `runs/wigley` and printed E%D -59.0 under a header naming KCS).
"""

from __future__ import annotations

import inspect
import json
import math
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from . import db, grammar
from .energy import (EnergyReport, WeightBudget, energy_report, weight_budget,
                     weight_items)
from .geometry import RHO_WATER, Hull
from .hydrostatics import (HydroState, gm, gm_long, solve,
                           solve_to_displacement)
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


def constraint_vector(values: dict[str, float],
                      extra_names: tuple[str, ...] = ()) -> dict[str, float]:
    """Return `values` as a dict keyed in CONSTRAINT_NAMES order, or raise.

    Building the vector FROM the names is the fix for E16: the order is no
    longer a property of the literal a human typed, it is a property of the
    tuple the optimizer reads.

    `extra_names` is how a compiled governance policy APPENDS rows (BuildPlan 3
    §2.2 output 2). It is APPEND-ONLY and it is checked to be so: an extra name
    that collides with a CONSTRAINT_NAMES entry is refused, because the one
    thing a policy must never do is rewrite a row the ladder owns. That refusal
    is the runtime half of Gate V3.0(d) — if a policy could overwrite `gm`,
    "delete the constitution and every physics result is bit-identical" would
    be a claim about discipline instead of a property of the code.

    Order is CONSTRAINT_NAMES first, then `extra_names` in the order given, so
    `[g[k] for k in CONSTRAINT_NAMES]` keeps meaning exactly what it meant —
    every existing consumer reads the same columns whether a policy compiled or
    not.
    """
    names = tuple(CONSTRAINT_NAMES) + tuple(extra_names)
    clash = [k for k in extra_names if k in CONSTRAINT_NAMES]
    if clash:
        raise ConstraintOrderError(
            f"policy rows {clash} collide with CONSTRAINT_NAMES. Governance "
            f"APPENDS rows; it never rewrites one. A policy that could "
            f"overwrite a ladder row would change a physics margin when the "
            f"constitution is applied, which is the exact thing Gate V3.0(d) "
            f"exists to forbid.")
    if len(set(names)) != len(names):
        raise ConstraintOrderError(
            f"duplicate constraint name in {list(names)}; every name is one "
            f"column of the optimizer's G matrix and two cannot share it.")
    missing = [k for k in names if k not in values]
    extra = [k for k in values if k not in names]
    if missing or extra:
        raise ConstraintOrderError(
            f"constraint vector does not match CONSTRAINT_NAMES: "
            f"missing {missing}, unexpected {extra}. Every name in "
            f"CONSTRAINT_NAMES is a column of the optimizer's G matrix; a "
            f"vector that does not cover them exactly cannot be mapped onto it.")
    return {k: values[k] for k in names}


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
    # LWL is a GRAMMAR INPUT, not a computed result: it is sitting in `params`
    # before a single line of physics runs, so it is carried on EVERY return
    # path — including the L0 refusal, where it used to stay at the 0.0 default
    # (see `_declared_lwl_m` below). 0.0 here means ONLY "the parameter vector
    # itself was unreadable", never "the ladder stopped early".
    hull_lwl_m: float = 0.0         # so requirements can check the mission
    rules: dict = field(default_factory=dict)   # tier R, IN the ladder
    seakeeping: dict = field(default_factory=dict)   # tier L2, when it has run
    # Tier L3, when a RECORDED campaign has been read for this hull. Empty is
    # the honest default: "no evidence at this tier", never a placeholder drag.
    cfd: dict = field(default_factory=dict)
    # The genome that produced this evaluation, so a kept design can be handed
    # to revalidate() as itself rather than as a loose array the caller has to
    # keep paired with it by hand. compare=False because an ndarray field makes
    # dataclass __eq__ raise.
    params: np.ndarray | None = field(default=None, repr=False, compare=False)
    eval_ms: float = 0.0
    badges: dict = field(default_factory=dict)   # quantity -> (tier, sigma)
    g: dict = field(default_factory=dict)        # constraint -> value, <=0 feasible
    # The COLUMNS of `g`, in order. CONSTRAINT_NAMES when no constitution was
    # compiled — which is the default and is byte-identical to the tuple every
    # consumer already reads — and CONSTRAINT_NAMES + the policy's rows when
    # one was (BuildPlan 3 §2.2 output 2). Carried rather than inferred from
    # `g.keys()` so that a consumer can see the vector's shape on an evaluation
    # that never got as far as building one.
    g_names: tuple[str, ...] = CONSTRAINT_NAMES
    # What governance decided about THIS design: the compiled constitution's
    # name, the delivery route with its RCD article, and the AI Act
    # consequence. Empty when no policy was applied — an empty dict is "no
    # governance was asked", never "governance said yes".
    policy: dict = field(default_factory=dict)


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


def _declared_lwl_m(params) -> float:
    """LWL as the GRAMMAR DECLARES it, readable before any physics runs.

    A KNOWN QUANTITY MUST NOT BE REPORTED AS ABSENT (the mirror of gap E11's
    "undefined must never be reported as ideal"). MEASURED: a 4.5 m hull whose
    only defect was an L/B of 1.41 failed the L0 bound check, so `evaluate()`
    returned at tier L0 and `hull_lwl_m` kept its 0.0 default — even though
    4.5 was sitting in the parameter vector the caller had just handed in.
    `iso12217.hull_length_m()` then read 0.0, found no length anywhere, and
    `assess()` declared ISO 12217-1's SCOPE UNDECIDABLE for a boat whose
    length was never in doubt. A different constraint failing is not ignorance
    about this one.

    Returns 0.0 — genuinely "no length" — only when the vector itself cannot
    be read: wrong shape, non-numeric, or a non-finite/non-positive LWL. That
    is the one case where the scope question really is undecidable.
    """
    try:
        x = np.asarray(params, dtype=float)
    except (TypeError, ValueError):
        return 0.0
    if x.shape != (grammar.N_PARAMS,):
        return 0.0
    v = float(x[grammar.NAMES.index("LWL")])
    return v if math.isfinite(v) and v > 0.0 else 0.0


def _apply_policy(ev: Evaluation, mission: MissionSpec, policy) -> None:
    """Append a compiled constitution's rows to a FINISHED evaluation.

    THE ONE CONTRACT, and the reason Gate V3.0(d) is a property of this
    function rather than a promise about it: everything above has already run
    and every physics number on `ev` is already final. This appends columns to
    `g`, appends strings to `violations`, and recomputes `ok`. It computes no
    hydrostatics, calls no rule, and writes to no field a physics quantity
    lives in. `policy.rows_for` is likewise a reader — it takes the finished
    evaluation and measures nothing itself.

    Called only from behind `if policy is not None`, so with no constitution
    the ladder does not merely produce the same numbers: it executes the same
    code, and there is no branch for a test to have to trust.

    Duck-typed on purpose. `evaluate` imports nothing from `navalai.policy`,
    so deleting the package leaves this module importable and every physics
    path intact — which is what "delete the policy file" has to mean if the
    structural test is to be worth anything.
    """
    rows, why = policy.rows_for(ev, mission)
    names = tuple(policy.rows)
    ev.g = constraint_vector({**ev.g, **rows}, extra_names=names)
    ev.g_names = tuple(CONSTRAINT_NAMES) + names

    viol = list(ev.violations)
    for k in names:
        v = ev.g[k]
        if not is_real_finite(v):
            # Same rule as the ladder's own rows (gap E10): a constraint that
            # is not a finite number is a violation, never a pass, because
            # `nan > 0.0` is False and would read as satisfied.
            viol.append(f"policy constraint {k!r} is not a finite number "
                        f"({v!r}) — the quantity behind it could not be "
                        f"computed, which is a violation and never a pass")
            ev.g[k] = INFEASIBLE_G
        elif v > 0.0:
            viol.append(why.get(k) or f"policy constraint {k!r} violated "
                                      f"(margin {v:+.4g})")
    ev.violations = tuple(viol)
    ev.ok = len(viol) == 0

    # `route_report`, not `route_for`: a craft the RCD does not define is a
    # REFUSAL, and a refusal raised here would abort a whole NSGA-II population
    # over one design that the `policy_legal` row has already reported as a
    # breach with a gradient attached. The refusal is carried, not swallowed —
    # `mode` reads 'REFUSED' and the clause that refused it comes with it.
    ev.policy = {"constitution": policy.constitution.name,
                 "rows": list(names),
                 "route": policy.route_report(ev, mission)}


def evaluate(params: np.ndarray, mission: MissionSpec,
             rho: float = RHO_WATER,
             provenance: db.Provenance | None = None,
             policy=None) -> Evaluation:
    """Run the ladder as far as L1. Fails fast and cheap (Fitness=inf pattern).

    `policy` is an optional COMPILED constitution
    (`navalai.policy.compile_policy`). It is keyword-usable, defaults to None,
    and every line that touches it sits behind `if policy is not None` — so an
    ungoverned call runs the identical code path it ran before governance
    existed. See `_apply_policy` and Gate V3.0(d).
    """
    t0 = time.perf_counter()

    rep = grammar.check(params)
    if not rep.ok:
        return Evaluation(False, "L0", rep.violations, params=np.asarray(params),
                          hull_lwl_m=_declared_lwl_m(params),
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
                          hull_lwl_m=float(p["LWL"]),
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
    # ONE STATE, NOT TWO (gap E7). `cb` and `wetted` have always come from the
    # floated `HydroState`; the beam and draft the form factor divides by came
    # from the DESIGN parameters, and on the reference hull those are 3.200 m
    # and 0.550 m against a floated 3.252 m and 0.374 m — a 47% error on the
    # draft, entering as sqrt(B/T). Passing them from `hs` makes the four
    # arguments describe the same boat at the same waterline.
    res = total_resistance(hull, u, hs.wetted, hs.cb, rho, wl,
                           beam_wl=hs.b_wl_max, draft=hs.draft)
    early: list[str] = []
    if not res.valid:
        # Reported as a violation, not buried in a badge: at Fn > 0.45 the
        # thin-ship model is answering a different question than the mission.
        early.append(
            f"speed outside the L1 model: Fn {res.fn:.2f} > {FN_MICHELL_MAX} "
            f"(planing regime — Michell thin-ship has no dynamic lift, trim or "
            f"spray; needs a Savitsky-class method)")
    en = energy_report(res.total, u, hull.deck_area(), mission.energy)

    # hull_lwl_m is carried here too, not just on the returned Evaluation.
    # `iso12217.hull_length_m` prefers the DECLARED LWL and falls back to the
    # floated `lwl_eff`, and the two are not the same number — MEASURED at a
    # declared 8.00 m the floated length is 7.60 m, 5% short. Omitting it made
    # the ladder's OWN scope call read lwl_eff while a caller doing
    # `stability(ev, ...)` on the returned object read the declared value, so
    # a hull declared just over 6 m could be assessed by ISO 12217-1 in
    # `ev.rules` and refused as out of scope by the identical function one line
    # later. One scope question, one length.
    ev_for_rules = Evaluation(
        ok=True, tier="L1", hydro=hs, wl=wl, weights=wb, masses=agg,
        gm_m=gm_m, gm_l_m=gm_l_m, ply_thickness_m=t_ply,
        hull_lwl_m=float(p["LWL"]))
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

    # GOVERNANCE, LAST AND ADDITIVE. Every physics number above is final before
    # this line, and this line does not exist when no constitution was handed
    # in (BuildPlan 3 §2.2: "delete the policy file and no physics result may
    # change").
    #
    # Policy rows are appended to the L1 vector and NOT to the two early
    # returns above, which carry no `g` at all. That is not an oversight: two
    # of the three rows measure the FLOATED hull (draft, solar fraction), and a
    # design that never floated has no floated state to govern. Pruning before
    # physics is the job of the OTHER output — `CompiledPolicy.box()` bounds
    # the sampler so an over-length hull is never proposed, rather than being
    # proposed and rejected.
    if policy is not None:
        _apply_policy(ev, mission, policy)

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
# The mesh levels moved to `seakeeping.L2_MESHES`, next to the
# `SeakeepingResult` that reports the uncertainty they measure. They were here,
# and so was a second copy of the mesh-to-mesh arithmetic, while the type that
# exists to carry that uncertainty was never constructed at all (gap F4).


# ---------------------------------------------------------------- tier L3 ---
# A RANS result enters the ladder as EVIDENCE that already exists. Nothing
# below starts a solver, and there is deliberately no code path here that
# could: `navalai.cfd.post` is a parser, `navalai.cfd.case` is a writer, and
# the runner is a shell script an operator invokes.

# ONE flow-through is a physical floor, not a tuned bar: a domain the free
# stream has not yet crossed still contains its initial condition, so no
# average taken over it is stationary. CLAUDE.md's target for a settled KCS run
# is 5.0 flow-throughs, and the 2026-08-06 re-audit found EVERY run in this
# repository sitting between 0.13 and 0.70 with conclusions drawn from all of
# them. `scripts/gate2m.py` applies the same floor inline (`fts >= 1.0`); it is
# the one number this module and that script both hold, and consolidating them
# into a single owner is owed.
_L3_MIN_FLOW_THROUGHS = 1.0

# Identity tolerances. The submerged volume of the case's own STL is compared
# against the hull the genome describes, which is a far stronger test than the
# length alone: MEASURED on the reference hull, `hull_to_stl` at nx=80 lands
# within 0.91% of the analytic displacement and at nx=400 within 0.07%, while a
# DIFFERENT hull misses by tens of percent. 3% is triangulation slack, not a
# window for another boat to fit through.
_L3_VOLUME_TOL = 0.03
_L3_LENGTH_TOL = 0.01
_L3_SPEED_TOL = 0.02


def read_case_info(case_dir) -> dict[str, str]:
    """`case.info` as a dict of strings, or raise `TierRefusal`.

    Values are returned raw. Nothing here supplies a default for a key the
    generator did not write: the caller checks for the keys it MEASURES from
    and refuses when one is absent (`.get` is used only for labels — the
    benchmark name, the STL hash — which are provenance, not quantities).
    """
    p = Path(case_dir) / "case.info"
    if not p.exists():
        raise TierRefusal(
            f"{p} does not exist, so this directory does not describe a case "
            f"at all — no L3 evidence can be read from it")
    out: dict[str, str] = {}
    for line in p.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith(("#", "NOTE", "run:",
                                                         "Gate")):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def l3_case_evidence(case_dir, hull: Hull, mission: MissionSpec,
                     rho: float = RHO_WATER) -> dict:
    """Read a RECORDED RANS campaign as L3 evidence for THIS hull, or refuse.

    Runs no solver. Reads `case.info`, the merged force history and the case's
    own STL, and returns a dict carrying the drag, its measured scatter, the
    resistance coefficient and the receipts (flow-throughs, symmetry, geometry
    residuals) that justify quoting it.

    Every failure is a `TierRefusal`, never a degraded answer:

    * the case is a different hull, or was towed at a different speed;
    * the case cannot say how long its domain is, so the number of
      flow-throughs is UNKNOWABLE. `scripts/gate2m.py` substitutes 4.5*Lwl
      here and records `domain_assumed`; this refuses instead, because a
      stationarity claim resting on an assumed domain is the `${VAR:-0}`
      pattern that has already cost this project a run. Every case generated
      before 2026-08-06 — `runs/wigley`, `runs/kcs_gci2/*` — is refused by
      this clause, which is the correct verdict for them and not a bug;
    * the flow has not crossed the domain once.

    The sigma is MEASURED, not declared: the scatter over the settled tail, or
    the drift between that tail and the window immediately before it,
    whichever is larger. A run that is still shedding its transient therefore
    reports a wide L3 band instead of a confident wrong one.
    """
    from .cfd import post          # a parser; importing it starts nothing

    case = Path(case_dir)
    info = read_case_info(case)

    # ---- identity: is this run about the hull we are holding? --------------
    for key in ("lwl", "speed_ms", "symmetric", "domain_length_m"):
        if key not in info:
            raise TierRefusal(
                f"{case}/case.info has no {key!r}. It is not enough for the "
                f"campaign to have happened; the record has to say what it was "
                f"of. A missing key is refused rather than defaulted — "
                f"'domain_length_m' in particular decides how many "
                f"flow-throughs the run covers, and a stationarity claim "
                f"resting on an assumed domain is not evidence.")
    try:
        lwl_case = float(info["lwl"])
        u_case = float(info["speed_ms"])
        dom_len = float(info["domain_length_m"])
    except ValueError as e:
        raise TierRefusal(
            f"{case}/case.info holds a value that is not a number ({e}); a "
            f"receipt that cannot be read is not a receipt") from e
    lwl_hull = float(hull.x[-1] - hull.x[0])
    if abs(lwl_case - lwl_hull) > _L3_LENGTH_TOL * max(lwl_hull, 1e-9):
        raise TierRefusal(
            f"{case} is a {lwl_case:.3f} m hull and this design is "
            f"{lwl_hull:.3f} m — that campaign is not evidence about this "
            f"boat. (gate2m.py once printed KCS tank errors for runs/wigley "
            f"for exactly this reason.)")

    u_want = mission.cruise_speed_ms()
    if abs(u_case - u_want) > _L3_SPEED_TOL * max(abs(u_want), 1e-9):
        raise TierRefusal(
            f"{case} was towed at {u_case:.3f} m/s and the mission cruises at "
            f"{u_want:.3f} m/s. Resistance is a function of speed, so this is "
            f"a different design point, not a better answer at this one.")

    stl = case / "constant" / "triSurface" / "hull.stl"
    if not stl.exists():
        raise TierRefusal(
            f"{stl} is missing, so the geometry the solver actually saw cannot "
            f"be checked against the genome and the wetted area C_T needs "
            f"cannot be measured")
    sub = post.stl_submerged_properties(str(stl), waterline=0.0)
    # The case STL is written with the DESIGN waterline at z=0 (that is the
    # frame `hull_to_stl` emits and the frame the tank is built around), so the
    # comparison is against the hull's displacement at wl=0, not at the floated
    # waterline the mission target produced.
    vol_hull = solve(hull, rho, 0.0).disp_kg / rho
    vol_res = abs(sub["volume_m3"] - vol_hull) / max(vol_hull, 1e-9)
    if vol_res > _L3_VOLUME_TOL:
        raise TierRefusal(
            f"{stl} encloses {sub['volume_m3']:.3f} m^3 below the waterline "
            f"and this genome's hull encloses {vol_hull:.3f} m^3 "
            f"({100 * vol_res:.1f}% apart, bar {100 * _L3_VOLUME_TOL:.0f}%). "
            f"Same length is not the same hull.")

    # ---- the recorded numbers ---------------------------------------------
    try:
        forces = post.forces_path(case)
    except FileNotFoundError as e:
        raise TierRefusal(
            f"{case} has no force history ({e}), so the campaign either has "
            f"not run or did not survive. There is no L3 number to read.") from e
    t, fx = post.parse_forces(forces)
    if len(t) < 10:
        raise TierRefusal(
            f"{forces} holds {len(t)} samples — too short to average. A drag "
            f"read off a handful of startup timesteps is not a resistance.")

    drag_tail, scatter = post.mean_resistance(forces)
    # The drift estimate reuses post.mean_resistance's OWN window rather than
    # declaring a second one — the fraction is read off its signature, so the
    # two windows are the same length by construction and there is no number
    # here to drift out of step with it. The previous window sits immediately
    # before the tail; the gap between the two means is what a run that has not
    # settled still has, and it is folded into sigma rather than turned into a
    # pass/fail bar. Stationarity is `scripts/gate2m.py`'s verdict to give;
    # this module's job is to make sure the band it reports is not narrower
    # than the evidence supports.
    frac = float(inspect.signature(post.mean_resistance)
                 .parameters["tail_frac"].default)
    span = float(t[-1] - t[0])
    lo = t[0] + max(1.0 - 2.0 * frac, 0.0) * span
    hi = t[0] + (1.0 - frac) * span
    prev = fx[(t >= lo) & (t < hi)]
    drift = abs(drag_tail - float(np.mean(prev))) if len(prev) else 0.0
    sigma = max(abs(scatter), drift)

    symmetric = info["symmetric"].strip().lower() == "true"
    if symmetric:
        # Half the hull is meshed, so the patch integral is half the force.
        # CLAUDE.md records `forceCoeffs wrong by exactly 2x on every symmetric
        # run` as a shipped defect; this is the same trap on the other side.
        drag_tail, sigma = 2.0 * drag_tail, 2.0 * sigma
    drag = abs(drag_tail)

    if not (dom_len > 0.0):
        raise TierRefusal(f"{case} declares domain_length_m={dom_len!r}")
    flow_throughs = float(t[-1]) * u_case / dom_len
    if flow_throughs < _L3_MIN_FLOW_THROUGHS:
        raise TierRefusal(
            f"{case} covers {flow_throughs:.2f} of one flow-through "
            f"({t[-1]:.1f} s of {dom_len / u_case:.2f} s). The free stream has "
            f"not crossed the domain, so the average still contains the "
            f"initial condition: this describes startup, not resistance. No "
            f"L3 badge is issued for it.")

    s_wetted = post.stl_wetted_area(str(stl), waterline=0.0)
    ct = post.resistance_coefficient(drag, s_wetted, u_case, rho)
    return {
        "case": str(case),
        "solver": "openfoam-interfoam",
        # NOT a hard-coded "v2606". `case.info` does not record the solver
        # build today, and a version string invented at read time is exactly
        # the kind of provenance that looks checkable and is not. When the
        # generator starts writing it, this picks it up with no change here.
        "solver_version": info.get("openfoam_version", "unrecorded"),
        "benchmark": info.get("benchmark", "unknown"),
        "stl_sha256": info.get("stl_sha256", "unknown"),
        "speed_ms": u_case,
        "drag_n": drag,
        "sigma_n": sigma,
        "ct": ct,
        "wetted_area_m2": s_wetted,
        "symmetric": symmetric,
        "t_end_s": float(t[-1]),
        "flow_throughs": flow_throughs,
        "n_samples": int(len(t)),
        "volume_residual": vol_res,
        # Not a verdict — a comparison. The ladder's whole point is that the
        # higher tier can disagree with the lower one, and a caller that never
        # sees BY HOW MUCH has learned nothing from the escalation.
        "identity": "lwl + submerged volume + speed matched against the genome",
    }


def revalidate(design, mission: MissionSpec, target_tier: str = "L2",
               provenance: db.Provenance | None = None,
               rho: float = RHO_WATER, omegas: np.ndarray | None = None,
               case_dir=None) -> Evaluation:
    """Re-validate a kept design UP the ladder and return the promoted result.

    `design` is either an `Evaluation` (as returned by `evaluate()`, carrying
    its own genome) or a raw parameter vector, which is evaluated to L1 first.

    The returned Evaluation's `tier` is the HIGHEST tier that actually ran, so
    an L2 result supersedes the L1 badge and the badges dict gains the L2
    quantities alongside the L1 ones it did not recompute. Promotion is
    monotone: `tier_rank(out.tier) >= tier_rank(in.tier)` always, and asking
    for a tier at or below the one already reached is a no-op rather than a
    demotion.

    `case_dir` is L3's evidence: a campaign directory that has ALREADY been
    run. L3 never starts a solver — see `l3_case_evidence`. Without it (and
    without an L3 row already in `provenance` for this hull at this speed) the
    L3 request is refused with "NO EVIDENCE AT THIS TIER".

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
        return _promote_to_l3(ev, params, mission, rho, case_dir, provenance)

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
        sea = seakeeping.heave_seakeeping(hull, w, ev.hydro.disp_kg,
                                          ev.hydro.awp, rho)
    except Exception as e:
        raise TierUnavailable(
            f"the L2 solve failed on this hull ({type(e).__name__}: {e}); no "
            f"L2 badge is issued") from e

    # The uncertainty is the worst relative mesh-to-mesh change across the
    # frequency set, and it is now MEASURED BY THE TYPE THAT REPORTS IT
    # (`SeakeepingResult`, gap F4) rather than recomputed here from a second
    # copy of the mesh levels.
    am1, dp1, rao = (sea.added_mass_heave, sea.damping_heave, sea.rao_heave)
    npan, unc_rel = sea.n_panels, sea.uncertainty_rel
    sk = sea.as_dict()

    if provenance is not None:
        hid = provenance.add_hull(params)
        ver = getattr(_cpt, "__version__", "unknown")
        for wi, a, b, r in zip(w, am1, dp1, rao):
            meta = {"omega": float(wi), "n_panels": int(npan),
                    "meshes": [list(m) for m in sea.meshes],
                    "method": sea.method, "basis": "mesh convergence"}
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


# The route an operator takes to CREATE the evidence this tier reads. Stated
# once, quoted by every refusal, so a "no" always comes with a "here is how".
_L3_OPERATOR_ROUTE = (
    "L3 (RANS) is not an in-process tier and this process will not start one: "
    "the KCS case is ~6 h on 10 ranks here and does not survive a thermal "
    "sleep. Generate the case with `python scripts/make_case.py --out "
    "runs/<name> --speed U --np 10`, run it with `openfoam "
    "scripts/run_campaign.sh runs/<name> 10`, check it with `python "
    "scripts/gate2m.py runs/<name>`, then hand the directory back as "
    "`revalidate(ev, mission, 'L3', case_dir='runs/<name>')`. No L3 badge is "
    "issued for a number L3 did not produce.")


def _l3_quantity(speed: float) -> str:
    """The provenance quantity name for an L3 drag, in ONE place.

    Written by `_promote_to_l3` and read back by it; if the two ever spelled it
    differently the read-back would silently find nothing and every escalation
    would report "no evidence" forever, which looks exactly like the gap this
    code closes.
    """
    return f"Rt_N@{speed:.3f}"


def _promote_to_l3(ev: Evaluation, params: np.ndarray, mission: MissionSpec,
                   rho: float, case_dir, provenance) -> Evaluation:
    """Badge an Evaluation L3 from RECORDED evidence, or refuse.

    Two sources, in order of preference:

    1. `case_dir` — a campaign directory that has already been run. Read,
       identity-checked against the genome, and RECORDED to provenance so the
       next caller does not need the directory.
    2. the provenance DB — an L3 row this hull already has, at this speed.

    Neither: `TierRequiresOperator`, naming the route. That refusal is the
    honest answer to "escalate this design to L3" on a machine holding no RANS
    result for it, and it is the only answer that cannot become the L1 number
    wearing an L3 badge.
    """
    u = mission.cruise_speed_ms()
    if case_dir is not None:
        hull = Hull(params)
        cfd = l3_case_evidence(case_dir, hull, mission, rho)
        if provenance is not None:
            hid = provenance.add_hull(params)
            provenance.add_result(hid, "L3", cfd["solver"],
                                  cfd["solver_version"],
                                  _l3_quantity(cfd["speed_ms"]),
                                  float(cfd["drag_n"]), float(cfd["sigma_n"]),
                                  cfd)
    else:
        cfd = None
        if provenance is not None:
            for _tier, _solver, q, value, unc, meta in provenance.results(
                    db.hull_id(params), "L3"):
                if not q.startswith("Rt_N@") or value is None:
                    continue
                rec = json.loads(meta or "{}")
                # Matched on the RECORDED speed, not on the quantity string.
                # The row is named for the speed the tank ran at and the query
                # is the speed the mission asks for, and those agree only to
                # within _L3_SPEED_TOL — keying on the formatted name would
                # miss its own row and report "no evidence" forever, which is
                # indistinguishable from the gap this code closes.
                if abs(float(rec.get("speed_ms", float("nan"))) - u) > \
                        _L3_SPEED_TOL * max(abs(u), 1e-9):
                    continue
                rec["drag_n"] = float(value)
                rec["sigma_n"] = float(unc if unc is not None else 0.0)
                cfd = rec
                break
        if cfd is None:
            raise TierRequiresOperator(
                f"NO EVIDENCE AT THIS TIER: no recorded L3 result for this "
                f"hull at {u:.3f} m/s"
                + ("" if provenance is not None else
                   " (and no provenance DB was passed to look in)")
                + ". " + _L3_OPERATOR_ROUTE)

    badges = dict(ev.badges)
    badges["resistance_cfd"] = ("L3", float(cfd["sigma_n"]), "measured")
    # The L1 number is NOT overwritten and NOT deleted. `ev.resistance` stays
    # the Michell/ITTC-57 result it always was, badged L1, and the L3 drag sits
    # beside it with the ratio between them stated. An escalation whose only
    # visible effect is a different number in the same field teaches the reader
    # nothing about which tier they are reading.
    if ev.resistance is not None and is_real_finite(ev.resistance.total):
        cfd = dict(cfd)
        cfd["l1_rt_n"] = float(ev.resistance.total)
        cfd["l3_over_l1"] = (float(cfd["drag_n"])
                             / max(abs(float(ev.resistance.total)), 1e-9))
    return replace(ev, tier="L3", cfd=cfd, badges=badges)
