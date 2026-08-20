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
from .energy import (EnergyReport, WeightBudget, energy_report, shell_area_m2,
                     weight_budget, weight_items)
from .geometry import RHO_WATER, Hull
from .holtrop import envelope_violations as holtrop_envelope_violations
from .holtrop import particulars_from_floated
from .hydrostatics import (HydroState, gm, gm_long,
                           multihull_crowding_heel,
                           multihull_gz_assessment,
                           multihull_stability_refusal, solve,
                           solve_equilibrium, solve_to_displacement,
                           vessel_terms)
from .limits import (FREEBOARD_FLOOR_M, LCB_BAND_PCT_LWL, LIST_LIMIT_DEG,
                     PRISMATIC_TOLERANCE, TRIM_LIMIT_DEG, gm_floor,
                     laminate_plan, min_bend_radius_m)
from .mission import (EVALUABLE_TOPOLOGIES, Manning, MissionSpec,
                      mission_cp_band, mission_cp_target, mission_lcb_band)
from .resistance import (FN_MICHELL_MAX, ResistanceResult, bow_wave_rise,
                         total_resistance)
from .rules import report as rules_report
from .rules.iso12215 import assess as scantling_rules
from .rules.iso12215 import select_stock_thickness_m
from .rules.iso12217 import assess as stability_rules
from .weights import MassAggregate, MassItem, aggregate


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
    # WHAT VESSEL this evaluation is of, and the derived quantities that only
    # exist for a multihull: hull count, demihull spacing, overall waterline
    # beam, and the wet-deck clearance the ship's OWN bow wave demands. A
    # REPORT, not a constraint vector — the genome declares no wet-deck height,
    # and `resistance.wet_deck_clearance_g` refuses an unmeasured clearance
    # rather than scoring it as satisfied. Empty for nothing: a monohull fills
    # it in too, saying n_hulls 1, so a reader never has to infer the
    # configuration from a missing key.
    vessel: dict = field(default_factory=dict)
    # WHAT THE MISSION ASKED FOR vs WHAT THE FLOATED HULL DELIVERS
    # (consolidation directive §5/§6). Target, sampled and delivered Cp are
    # THREE different numbers; a candidate is never mission-conformant
    # merely because its gene started inside the sampling band, so the
    # receipt measures conformance on the EQUILIBRIUM state. A REPORT with
    # bases, not a constraint vector — no new bars (§24).
    targets: dict = field(default_factory=dict)
    # AXIS 3's receipts: every L1 model that is outside its SUPPORT at this
    # size and speed. Distinct from `violations` on purpose — a model inside
    # its validity flag but outside the band it was correlated on (ITTC-57 in
    # the laminar-turbulent transition) is information a reader needs and is
    # not, today, a bar. Same shape and the same reason as
    # `holtrop_envelope_violations` below.
    resistance_envelope: tuple[str, ...] = ()
    # WHICH resistance model answered, and why the other one did not (gap E1b).
    # A METHOD RECEIPT, not a quantity: it gets its own field rather than a
    # `badges` entry, because a badge is `(tier, sigma, basis)` about a NUMBER
    # and this has no number of its own — putting prose in a `basis` slot is how
    # a receipt starts being read as an uncertainty. Empty tuple means
    # Holtrop-Mennen is INSIDE its envelope on this hull and was still not used;
    # a non-empty tuple is the method's own words for why it does not apply.
    resistance_method: str = ""
    holtrop_envelope_violations: tuple[str, ...] = ()
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
    # The pre-filter must judge by the SAME role the ladder will: a demihull
    # candidate rejected here by monohull bands would starve the sampler for
    # a catamaran mission (R0.1 — the 2026-08-14 finding).
    vessel_cfg = getattr(mission, "vessel", None)
    # THE MISSION CHOOSES THE PRISMATIC (R1.1): when the mission states a
    # length, the Cp gene is drawn from `prismatic_target` across the hint's
    # ±10% Froude window instead of the whole gene box — form follows
    # function in the data feed, not only in the search. A hint-less mission
    # draws the full box exactly as before (band is None), which remains the
    # explicit exploration mode.
    lo, hi = grammar.LOW.copy(), grammar.HIGH.copy()
    hint = getattr(mission, "lwl_hint_m", None)
    if hint:
        band = mission_cp_band(mission, max(hint * 0.9, float(lo[grammar.NAMES.index("LWL")])),
                               min(hint * 1.1, float(hi[grammar.NAMES.index("LWL")])))
        if band is not None:
            j = grammar.NAMES.index("Cp")
            b_lo, b_hi = max(lo[j], band[0]), min(hi[j], band[1])
            if b_lo <= b_hi:
                lo[j], hi[j] = b_lo, b_hi
    X, y = [], []
    while len(X) < n:
        x = rng.uniform(lo, hi)
        if not grammar.check(x, vessel=vessel_cfg).ok:
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

    # `getattr` rather than `mission.vessel`: `translate.sanitize` and
    # `ui/server.py`'s `MissionSpec(**body)` build spec-like objects, and a
    # caller holding an older one must get the monohull it has always got
    # rather than an AttributeError from inside the ladder. Resolved BEFORE
    # the L0 gate: `grammar.check` judges proportions by HULL ROLE, and a
    # demihull judged by monohull bands refuses the project's own catamaran
    # (the 2026-08-14 finding quoted at the top of `grammar.py`).
    vessel_cfg = getattr(mission, "vessel", None)

    rep = grammar.check(params, vessel=vessel_cfg)
    if not rep.ok:
        return Evaluation(False, "L0", rep.violations, params=np.asarray(params),
                          hull_lwl_m=_declared_lwl_m(params),
                          eval_ms=(time.perf_counter() - t0) * 1e3)

    hull = Hull(params)
    p = grammar.named(params)

    # HOW MANY HULLS, AND HOW FAR APART — resolved ONCE, above, and handed to
    # both halves of the physics. `hydrostatics.vessel_terms` is the single
    # home of the derivation (`mission.VesselConfig.separation_m` is the single
    # home of the ratio -> metres conversion inside it); the stability term and
    # the wave-interference term must be given the same spacing or they
    # describe different vessels while sharing one Evaluation.
    try:
        # AXIS 1 has values this project can DECLARE and cannot EVALUATE. A
        # trimaran's amas are not copies of its centre hull and this genome
        # carries one moulded surface; refusing by name keeps the gap visible,
        # where silently summing three copies would report a vessel nobody
        # would build.
        if vessel_cfg is not None and not vessel_cfg.is_evaluable:
            raise ValueError(
                f"topology {vessel_cfg.topology.value!r} is NOT IMPLEMENTED. "
                f"`grammar.PARAMS` carries exactly one moulded surface and "
                f"`resistance.catamaran_interference` derives its factor from "
                f"two IDENTICAL translated hulls, so a centre hull that "
                f"differs from its amas cannot be built from this genome. "
                f"Evaluable topologies: "
                f"{[t.value for t in EVALUABLE_TOPOLOGIES]}.")
        n_hulls, separation_m, _d = vessel_terms(hull, vessel_cfg)
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        # An unbuildable VESSEL is an L0 refusal, not a floatation failure: it
        # is decided by the configuration and the moulded surface, before a
        # drop of water is involved. It is CAUGHT rather than allowed to
        # propagate for the same reason `_apply_policy` uses `route_report` —
        # one bad design must not abort a whole NSGA-II population.
        #
        # C-15 (forensics C6): an AttributeError/KeyError here is OUR bug
        # (a typo in vessel_terms, a missing field), not a bad design — the
        # old message dressed a code defect as a per-design refusal and a
        # broken checker read as a 100%-refused population. Same precedent
        # as translate.py's 'checker error:' labels: still refuse (the
        # population must not abort), but NAME the class so a reader can
        # tell 'your config is bad' from 'our code is broken'.
        msg = (f"vessel: {e}" if isinstance(e, (ValueError, TypeError))
               else f"checker error (a code defect, not a design refusal): "
                    f"{type(e).__name__}: {e}")
        return Evaluation(False, "L0", (msg,),
                          params=np.asarray(params),
                          hull_lwl_m=_declared_lwl_m(params),
                          eval_ms=(time.perf_counter() - t0) * 1e3)

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
    t_ply = None   # selected below at the FIXED POINT (C-04) — see there
    # THE SHELL IS INTEGRATED TO THE SHEER, NOT A FACTOR TIMES THE WATERLINE
    # AREA (gap C9). This line read `hull.wetted_surface(0.0) * 1.6`, where the
    # bare literal stood in for "and the topsides above the design waterline" —
    # but a boat is planked to the sheer and `wetted_surface` takes the
    # waterline as an argument, so the quantity the factor approximated was one
    # call away and `engineer.assess` was already making it. Two modules,
    # two shell areas, one hull: the module that counts plywood and the module
    # that weighs it were planking different boats.
    #
    # MEASURED on the reference hull: wetted(0.0) = 30.579 m^2 -> 48.927 m^2 at
    # x1.6 against a true 51.616 m^2, so the true ratio is 1.6879 and the
    # factor understated the shell by 5.2%. That is the small part. Over 200
    # grammar-feasible hulls (seed 3) the ratio runs 1.251 to 6.702, mean
    # 2.062 — the one literal was wrong by up to 76% of the true area and by
    # -15.4% on average, and it was wrong in a way that varied systematically
    # with exactly the parameters NSGA-II is free to move. The optimiser was
    # scoring structure mass over that error.
    # TWO DEMIHULLS ARE TWO SHELLS. This is counting, not modelling: the same
    # moulded surface is built n_hulls times, so the plywood in it is n_hulls
    # times as much. `1 * shell` is exact, so the monohull is untouched.
    #
    # WHAT IS NOT COUNTED, AND IT FLATTERS THE CATAMARAN — said out loud rather
    # than left to be found. `deck` stays ONE demihull's deck, so the BRIDGE
    # DECK spanning the tunnel contributes neither structure mass (which would
    # hurt the design) nor solar area (which would help it), and `weight_items`
    # places every item at a single-hull height, so a bridge deck and its
    # superstructure — which sit ABOVE the demihull sheer — do not raise KG.
    # KG is the lever GM is measured from, so a catamaran's GM here is an
    # UPPER estimate. Closing this needs a bridge-deck geometry the grammar
    # does not carry and an arrangement model (tier E); inventing a height
    # would be the `${VAR:-0}` pattern with a boat on top of it.
    shell = n_hulls * shell_area_m2(hull)       # computed once, not twice
    deck = hull.deck_area()
    # §11: the payload's CONTINUOUS DRAW joins the hotel load before either
    # consumer reads the spec, so the battery-range and Wh/NM numbers
    # describe the boat with its instruments on. One adjusted spec, used by
    # BOTH the weight budget and the energy report — two readings of
    # different specs would be the two-boats defect.
    energy_spec = mission.energy
    payload_spec = getattr(mission, "payload", None)
    if payload_spec is not None and payload_spec.power_w > 0.0:
        from dataclasses import replace as _dc_replace
        energy_spec = _dc_replace(
            energy_spec,
            hotel_kwh_day=energy_spec.hotel_kwh_day
            + payload_spec.power_w * 24.0 / 1000.0)
    # C-04 (forensics B1): ONE mLDC. The stock sheet used to be selected
    # from the MISSION TARGET while the same rule was assessed at the
    # FLOATED displacement — whenever the weight budget exceeded the
    # target, selection and assessment read different boats and R-TBM
    # failed by construction (measured: a 0.02 mm sliver refusal on the
    # 5 m case). The circularity the old comment feared (thickness → mass
    # → displacement → thickness) is closed by a fixed point on the EXACT
    # final displacement: hs.disp = max(budget(t) + payload, target), a
    # discrete stock map that settles in <= 3 steps or is refused.
    _payload_kg = (payload_spec.mass_kg
                   if payload_spec is not None else 0.0)
    # 6R re-shape (2026-08-19): the selection is category- and
    # length-dependent per ISO 12215-5:2008(E) Eq 7/8; the design LWL is
    # the genome's (the floated lwl_eff does not exist yet at selection).
    from .rules.iso12215 import bottom_panel_dims_mm
    _b_mm, _l_mm = bottom_panel_dims_mm(hull)
    t_ply = select_stock_thickness_m(mission.displacement_target_kg,
                                     float(p["LWL"]),
                                     design_category=mission.design_category,
                                     span_mm=_b_mm, l_mm=_l_mm)
    for _ in range(3):
        _wb_probe = weight_budget(p["LWL"], p["D"], shell, deck,
                                  energy_spec, t_ply)
        _disp_probe = max(_wb_probe.total_kg + _payload_kg,
                          mission.displacement_target_kg)
        _t_next = select_stock_thickness_m(
            _disp_probe, float(p["LWL"]),
            design_category=mission.design_category,
            span_mm=_b_mm, l_mm=_l_mm)
        if _t_next == t_ply:
            break
        t_ply = _t_next
    else:
        return Evaluation(
            False, "L1",
            (f"scantling: stock-sheet selection did not settle in 3 "
             f"iterations (last {t_ply * 1e3:.0f} mm at "
             f"{_disp_probe:.0f} kg) — the thickness-mass fixed point is "
             f"oscillating and neither sheet can honestly be certified",),
            params=np.asarray(params), hull_lwl_m=float(p["LWL"]),
            eval_ms=(time.perf_counter() - t0) * 1e3)
    wb = weight_budget(p["LWL"], p["D"], shell, deck, energy_spec, t_ply)
    items = weight_items(p["LWL"], p["D"], shell, deck, energy_spec,
                         t_design, t_ply)
    # §10/§11: the mission's equipment payload enters the POSITIONED model —
    # at its declared station, or at the budget's payload station with the
    # defaulting SAID in the source string (nothing enters displacement
    # without a declared position).
    if payload_spec is not None and payload_spec.mass_kg > 0.0:
        from .energy import LCG_FRACTION, VCG_FRACTION
        xf = (payload_spec.x_frac_lwl if payload_spec.x_frac_lwl is not None
              else LCG_FRACTION["payload"])
        zf = (payload_spec.z_frac_depth
              if payload_spec.z_frac_depth is not None
              else VCG_FRACTION["payload"])
        defaulted = (payload_spec.x_frac_lwl is None
                     or payload_spec.z_frac_depth is None)
        items.append(MassItem(
            id="mission_payload", mass_kg=payload_spec.mass_kg,
            x_m=xf * p["LWL"], z_m=zf * p["D"] - t_design, y_m=0.0,
            sigma_kg=0.0, tier="L1",
            source=("mission.PayloadSpec"
                    + (" (position DEFAULTED to the budget's payload "
                       "station — declare x_frac_lwl/z_frac_depth)"
                       if defaulted else " (declared position)")),
            basis="declared"))
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
        # The VESSEL floats to `target`, so a two-hull vessel puts half the
        # mass in each demihull and floats higher than the same genome would as
        # a monohull. Draft is what KB, the waterplane beam and every
        # proportion downstream are measured at, so this is not bookkeeping.
        hs, wl = solve_to_displacement(hull, target, rho, vessel=vessel_cfg)
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
    # UNDEFINED IS NOT IDEAL (gap E11). trim/list used to fall back to 0.0
    # — the best possible value of each — exactly where the physics behind
    # them stopped existing. None here, INFEASIBLE_G below, and a violation
    # naming the state.
    #
    # THE ATTITUDE IS SOLVED, NOT LINEARISED (R2.1 — audit P0 "no trim
    # equilibrium; all hydrostatics upright-zero-trim"). The small-angle
    # lever (LCG-LCB)/GM_L is demoted from answer to warm start:
    # `solve_equilibrium` floats the hull on the TRIMMED plane until the
    # buoyant mass matches the weight and lcb stands under lcg, and every
    # quantity downstream — GM, freeboard, proportions, the resistance
    # inputs — is reported at that attitude. The E11 guard keeps its
    # meaning: GM_L <= 0 still has no equilibrium to solve about, and a hull
    # whose lcg cannot be stood under within the solver's ±6 deg range is a
    # refusal carried into the trim violation, not an endpoint answer.
    gm_l_level = gm_long(hs, kg)
    trim: float | None = None
    trim_refusal: str | None = None
    if is_real_finite(gm_l_level) and gm_l_level > 0.0:
        try:
            hs, wl, trim = solve_equilibrium(
                hull, target, agg.lcg_m, rho, vessel=vessel_cfg,
                warm=(hs, wl))
        except ValueError as e:
            trim_refusal = str(e)
    gm_m = gm(hs, kg) - fsc
    gm_l_m = gm_long(hs, kg)
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
    # BUILDABILITY IS NOW A CONSTRUCTION CHOICE, NOT A FIXED SHEET
    # (operator decision, 2026-08-20). MEASURED before this: sizing every
    # panel as ONE stock sheet made an 18 mm bottom demand a 1.44 m cold-bend
    # radius, and over 30 draws of the flagship brief the achieved radii ran
    # min 0.30 / median 0.89 / max 1.40 m — ZERO of 17 hulls reaching the
    # check cleared it, and only 2 of 30 designs were feasible. That is a
    # MATERIALS mismatch, not a population of bad hulls.
    #
    # `laminate_plan` bends each skin at its own thickness, so the governing
    # radius follows the THICKER SKIN rather than the total. It laminates ONLY
    # when a single sheet cannot take the radius this hull actually has and a
    # laminate can, so a gentle boat is still built the cheap way. Across
    # 12-21 mm the laminate reaches the same total from stock, so this is
    # weight-neutral for every SKU in PLM.md — `t_ply` (the WEIGHT) is
    # deliberately not re-read from the plan here.
    _ply_plan = laminate_plan(t_ply, r_min)
    r_req = _ply_plan["min_radius_m"]

    u = mission.cruise_speed_ms()
    # ONE STATE, NOT TWO (gap E7). `cb` and `wetted` have always come from the
    # floated `HydroState`; the beam and draft the form factor divides by came
    # from the DESIGN parameters, and on the reference hull those are 3.200 m
    # and 0.550 m against a floated 3.252 m and 0.374 m — a 47% error on the
    # draft, entering as sqrt(B/T). Passing them from `hs` makes the four
    # arguments describe the same boat at the same waterline.
    # AND THE SEPARATION REACHES THE WAVE TERM. `hs.wetted` is already the
    # VESSEL's (both demihulls) while `hs.cb`, `hs.b_wl_max` and `hs.draft`
    # stay ONE demihull's, which is exactly the split `total_resistance`
    # documents and Watanabe's regression needs.
    res = total_resistance(hull, u, hs.wetted, hs.cb, rho, wl,
                           beam_wl=hs.b_wl_max, draft=hs.draft,
                           separation=(separation_m if n_hulls > 1 else None),
                           lwl_eff=hs.lwl_eff)
    early: list[str] = []
    if not res.valid:
        # Reported as a violation, not buried in a badge: outside its envelope
        # the L1 model is answering a different question than the mission.
        # THE REASON COMES FROM AXIS 3 rather than being spelled out here,
        # because validity now has TWO causes — Fn above `FN_MICHELL_MAX` and
        # Re below the transition — and a message that names only the Froude
        # one would misreport a slow 1 m hull as a planing boat.
        for why_env in (res.flow.envelope if res.flow is not None else
                        (f"Fn {res.fn:.2f} > {FN_MICHELL_MAX}",)):
            early.append(f"speed/size outside the L1 model: {why_env}")
    # THE RESISTANCE SIGMA IS HANDED ON (gap H1). `energy_report` has propagated
    # since the H1 fix landed in energy.py, but this — its ONLY production call
    # site — passed no input sigma, so it took the placeholder branch every
    # time and evaluate() then threw even that away for its own inline
    # `wh_per_nm * 0.30` in the badge dict below. Two copies of 0.30, and the
    # one that reached the badge was the one nothing could narrow.
    # WHY HOLTROP-MENNEN IS NOT THE MODEL HERE, IN THE METHOD'S OWN WORDS
    # (gap E1b). The row offers two arms — wire H-M into evaluate(), or route
    # small craft away from it with an explicit guard — and the MEASUREMENT
    # picks the second. Over 300 grammar samples (seed 3) floated to the 6 t
    # default mission, 299 float and only **15 of 299 = 5.0%** satisfy all
    # three of the method's stated applicability clauses:
    #
    #     L/B   min 1.97   med 4.32   max  9.66    band 3.9 - 9.5
    #     B/T   min 0.84   med 6.96   max 43.73    band 2.1 - 4.0
    #     Cp    min 0.39   med 0.66   max  0.88    band 0.55 - 0.85
    #
    # B/T is the killer: shallow-draft river craft sit at 2-10x the
    # beam-to-draught of the 1982 merchant/trawler population the regression
    # was fitted to. Calling it on every dayboat would spend the compute to
    # produce an `L1H-INVALID` badge on 95% of the search box, and it would put
    # a ship method within one edit of answering for a boat — the failure this
    # row is named after. So the envelope is EVALUATED and REPORTED, and the
    # resistance stays Michell + ITTC-57.
    #
    # A BADGE AND NOT A CONSTRAINT ROW, deliberately: an always-satisfied row
    # occupying an NSGA-II dimension is a defect this repository has already
    # shipped once (gap E4 deleted four of them). `envelope_violations` does
    # not raise — `domain_errors`/`total()` do, and neither is called here.
    _hm_p = particulars_from_floated(
        lwl=hs.lwl_eff, b=hs.b_wl_max, draught=hs.draft, volume=hs.volume,
        cb=hs.cb, cp=hs.cp, awp=hs.awp, lcb_pct=hs.lcb_pct_lwl)
    holtrop_env = holtrop_envelope_violations(_hm_p, res.fn, hs.cp)

    en = energy_report(res.total, u, hull.deck_area(), energy_spec,
                       resistance_sigma_n=res.uncertainty)

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
        hull_lwl_m=float(p["LWL"]),
        # THE VESSEL RIDES ALONG (2026-08-19): this hand-assembled
        # Evaluation was exactly the case _vessel_of's docstring warns
        # about — no vessel dict, so every CATAMARAN was monohull-
        # classified inside the rules tier: R-GM emitted on the quantity
        # that does not govern, and the multihull branches (the stricter
        # NZ offset-load cap, R-MHS) dead. Found while wiring cl 6.6.
        vessel={"n_hulls": hs.n_hulls,
                "manning": getattr(vessel_cfg, "manning",
                                   Manning.CREWED).value,
                "topology": (vessel_cfg.topology.value
                             if vessel_cfg is not None else "monohull")})
    # THE OFFSET-LOAD LEVER IS THE VESSEL'S BEAM, NOT ONE DEMIHULL'S.
    # `iso12217.assess` uses `beam_m` for exactly one thing: R-OLH's crew
    # offset, `b = 0.40 * beam`. The crew of a catamaran crowd to the outboard
    # edge of the BRIDGE DECK, which is s further out than a demihull's own
    # side, so passing the demihull beam would understate the heeling moment by
    # the whole separation — the flattering direction, and the same error class
    # as judging a demihull by a monohull GM floor. Overall beam is the
    # separation plus one demihull's moulded beam; for a monohull
    # `separation_m` is 0.0 and this is the identical expression it always was.
    beam_for_offset_load = separation_m + 2.0 * float(hull.y_chine.max())

    # AXIS 2 — MANNING SELECTS THE RULE SET, and this is where it selects it.
    #
    # UNCREWED IS NOT CREWED WITH ZERO PEOPLE. The RCD (Directive 2013/53/EU)
    # governs recreational craft; an uncrewed vehicle is outside its scope, so
    # ISO 12217-1 — harmonised UNDER that directive, and whose whole assessment
    # is built out of crew mass, accommodation and escape — does not apply.
    # `limits.CREW_MASS_KG` and `iso12217.OFFSET_FRACTION` are crewed-only
    # concepts, and running them on a drone would produce a heel angle from a
    # crew that is not aboard, under a header naming a standard that does not
    # cover the craft. That is the `gate2m.py` printing KCS's EFD figure over a
    # Wigley hull defect, in the rules tier.
    #
    # So the assessment is NOT RUN, and its absence is a REFUSAL rather than a
    # silence: nothing in this repository implements a stability rule set for
    # uncrewed craft, and an uncrewed hull must not come back blessed by the
    # scantling half alone.
    manning = getattr(vessel_cfg, "manning", Manning.CREWED)
    # Two lists on purpose: `rules_not_implemented` is the REPORT of every rule
    # set that did not run, and `manning_refusals` is the subset that is also a
    # VIOLATION. A whole missing rule set (uncrewed) is a refusal; a missing
    # half of a rule set that did run (liveaboard) is a recorded gap, because a
    # habitable monohull is not thereby unsafe and inventing a bar for it would
    # be the mirror of the defect this file exists to prevent.
    rules_not_implemented: list[str] = []
    manning_refusals: list[str] = []
    if manning is Manning.UNCREWED:
        findings = list(scantling_rules(
            hs.disp_kg, t_ply * 1e3,
            design_category=mission.design_category, lwl_m=hs.lwl_eff,
            span_mm=_b_mm, l_mm=_l_mm))
        manning_refusals.append(
            f"manning=uncrewed: ISO 12217-1 was NOT ASSESSED and NOTHING was "
            f"assessed in its place. The RCD does not govern uncrewed craft, "
            f"so a harmonised standard under it cannot answer for this "
            f"vehicle, and this repository implements no stability rule set "
            f"that can. `mission.crew` = {mission.crew} was IGNORED: crew "
            f"mass and the offset-load crowding fraction are crewed-only "
            f"concepts. This hull therefore has NO stability assessment of any "
            f"kind — which is a refusal, not a pass.")
        rules_not_implemented.extend(manning_refusals)
    else:
        findings = list(stability_rules(ev_for_rules, mission.design_category,
                                        mission.crew, beam_for_offset_load,
                                        windage=mission.windage)
                        + scantling_rules(
                            hs.disp_kg, t_ply * 1e3,
                            design_category=mission.design_category,
                            lwl_m=hs.lwl_eff,
                            span_mm=_b_mm, l_mm=_l_mm))
    if manning is Manning.LIVEABOARD:
        # A recorded gap and NOT a violation for a monohull: ISO 12217-1 does
        # cover habitable craft and is assessed above, so the missing piece is
        # the habitability/escape half rather than the whole rule set. For a
        # habitable MULTIHULL the missing piece is inversion and escape, and
        # that is exactly what the multihull refusal below already fails on —
        # so it is not counted twice.
        rules_not_implemented.append(
            "manning=liveaboard: ISO 12217-1's habitability, downflooding-"
            "opening and ESCAPE provisions are not implemented; only the "
            "numeric bars in `rules/iso12217.py` were assessed.")
    # C-23, THE WIRE (2026-08-19): ES-TRIN is consulted when the mission
    # DECLARES inland waters — the same token vocabulary parse_mission
    # maps ("river"/"canal"/"lake", plus an explicit "inland"). The
    # standard then applies its OWN scope test (Directive (EU) 2016/1629:
    # L >= 20 m or L.B.T >= 100 m3, on ES-TRIN Art. 1.01 hull dimensions)
    # and returns an explicit IN/OUT-OF-SCOPE receipt either way — a
    # 10 m dayboat on the Danube gets "OUT OF SCOPE ... RCD instead",
    # never silence, and a 20 m river barge gets the real bars. The
    # checkers read only the floated state, passed as such; scope is not
    # manning-dependent (an unmanned barge is still an inland vessel).
    _waters = str(mission.waters or "").lower()
    if any(t in _waters for t in ("river", "canal", "lake", "inland")):
        import types as _types

        from .rules.estrin import assess as estrin_rules
        findings = list(findings) + list(estrin_rules(
            _types.SimpleNamespace(hydro=hs), hull))
    rules_rep = rules_report(findings)
    # One continuous margin so NSGA-II can descend it: 0 when every rule
    # passes, else the worst RELATIVE shortfall. A boolean would give the
    # optimiser no gradient to follow out of an infeasible region.
    fails = [f for f in findings if not f.passed]

    # Proportions re-checked on the FLOATED hull, against the same bands L0
    # applied to the parameter vector (gap B9). `grammar.proportion_margins` is
    # the shared kernel, so the two states cannot be judged by different
    # numbers — and it receives the SAME vessel L0 received, so a demihull is
    # not re-judged as a monohull once it floats.
    props = grammar.proportion_margins(hs.lwl_eff, hs.b_wl_max, hs.draft,
                                       vessel=vessel_cfg)
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
        # AN UNDECIDABLE FINDING IS NOT A SHORTFALL, AND FOLDING IT IN HERE
        # POISONED THE WHOLE CONSTRAINT. `ES-REC` reports `measured = nan`
        # ON PURPOSE — ES-TRIN Art. 26.01 decides whether Chapter 4's bars
        # govern at all, craft TYPE is not modelled, and the rule says so at
        # length rather than inventing an answer. But `max()` over a NaN is
        # NaN, so the aggregate became non-finite and EVERY design that
        # reached the inland-waters tier was refused with "the quantity
        # behind it could not be computed" — a sentence that reads like a
        # broken computation and sends the next reader to look for one.
        # MEASURED 2026-08-20 on 40 uniform grammar samples: 5 refused this
        # way, 12.5% of the draw, none of them for a reason about the boat.
        #
        # The margin is now taken over findings whose numbers EXIST. The
        # design still fails — ES-REC is `passed=False` and stays in the
        # report with its full explanation, and ES-COV fails unconditionally
        # for an in-scope craft — but it fails with a gradient the optimiser
        # can descend and a reason a reader can act on. If every failing
        # finding is undecidable, the constraint is INFEASIBLE_G: unmeasured
        # is never a pass.
        "rules": _rules_margin(fails),
    })
    why = {
        "freeboard": f"freeboard at load {hs.freeboard_min:.2f} m "
                     f"< {FREEBOARD_FLOOR_M:.2f} m",
        "gm": f"GM {gm_m:.2f} m < {gm_min:.2f} m "
              f"(category {mission.design_category} floor, ISO 12217)",
        "bend_radius": f"panel bend radius {r_min:.2f} m < {r_req:.2f} m "
                       f"[{_ply_plan['method']}: "
                       f"{'+'.join(f'{s * 1e3:.0f}' for s in _ply_plan['skins'])} mm] "
                       f"({t_ply * 1e3:.0f} mm ply cold-bend limit)",
        "trim": ((f"static trim is UNDEFINED: {trim_refusal}"
                  if trim_refusal is not None else
                  f"static trim is UNDEFINED: GM_L {gm_l_level:+.2f} m is not "
                  f"positive, so the hull has no longitudinal equilibrium to "
                  f"trim about (LCG {agg.lcg_m:.2f} m vs LCB {hs.lcb:.2f} m)")
                 if trim is None else
                 f"static trim {trim:+.2f} deg (SOLVED equilibrium, R2.1) "
                 f"exceeds {TRIM_LIMIT_DEG:.1f} deg "
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
                       f"{list(grammar.bands_for(vessel_cfg)['L/B'][0])}, B/T "
                       f"{hs.b_wl_max / max(hs.draft, 1e-9):.2f} "
                       f"{list(grammar.bands_for(vessel_cfg)['B/T'][0])} — "
                       f"role {grammar.hull_role(vessel_cfg).value}; L0 "
                       f"checked the design draft, this is the hull that "
                       f"floated",
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

    # AXIS 1's SAFETY HALF, and it is the reason this whole feature is not a
    # regression. The parallel-axis term above just made every catamaran's GM
    # enormous; without this, that lands as "catamarans now sail through the
    # stability gate" on a criterion that does not apply to them. See
    # `hydrostatics.multihull_stability_refusal` for the mechanism (a
    # catamaran is stable INVERTED and cannot self-right), for the criterion
    # that governs, and for exactly which of its clauses cannot be computed
    # here. Empty tuple for a monohull, so the monohull path is untouched.
    #
    # A VIOLATION AND NOT A CONSTRAINT ROW, deliberately. `CONSTRAINT_NAMES`
    # feeds NSGA-II's G matrix, and a row that is a large constant for every
    # multihull and satisfied for every monohull carries no gradient while
    # occupying a dimension — the E4 defect. It also would have changed the
    # vector's SHAPE for monohulls. This is the same mechanism the ladder
    # already uses for `early`, the "speed outside the L1 model" refusal.
    # R2.2, THE CLASS THAT CAN NOW VERDICT (2026-08-19): NZ Part 40A App.1
    # cl 1.3 governs a multihull under 15 m LOA carrying <= 50 persons and
    # is establishable BY CALCULATION (its own footnote 31) — both halves
    # (heel AND trim under uncontrolled crowding, bar 8 deg) are computed
    # by `hydrostatics.multihull_crowding_heel`, so THIS class gets a
    # MEASURED verdict instead of the blanket refusal. A passing test also
    # supersedes the R-OLH monohull-bar caveat: the crowding test IS the
    # multihull offset-load criterion, applied with the rule's own crowd
    # model. The >= 15 m / > 50 passenger class keeps the cl 1.4 refusal
    # until the windage declarables land (clauses (c)/(d) — (d) is READ
    # as of 2026-08-19; (c) still needs a declared lateral area).
    _cht = None
    _cl14 = None
    if hs.n_hulls > 1:
        _persons = 0 if manning is Manning.UNCREWED else int(mission.crew)
        _loa = float(hull.x[-1] - hull.x[0])
        if _loa < 15.0 and _persons <= 50:
            _cht = multihull_crowding_heel(
                hull, hs, kg, _persons, rho, vessel=mission.vessel,
                trim_deg=float(trim if trim is not None else 0.0),
                gm_m=gm_m)
            if not _cht.passes:
                _heel_txt = ("no static equilibrium (capsize)"
                             if _cht.heel_deg is None
                             else f"heel {_cht.heel_deg:.2f} deg")
                viol.append(
                    f"multihull stability: NZ Part 40A App.1 cl 1.3 FAILED "
                    f"— {_heel_txt}, trim {_cht.trim_deg_crowd:.2f} deg "
                    f"under uncontrolled crowding ({_cht.persons} x 75 kg "
                    f"at the outboard deck edge), bar 8 deg on both. "
                    f"CONSERVATIVE placement: a fail here is marginal "
                    f"evidence — see CrowdingHeelTest.basis.")
        elif not mission.windage.declared:
            # THE SILENT PASS, MEASURED 2026-08-20. The two branches here
            # cover < 15 m (cl 1.3) and >= 15 m WITH a declared windage
            # (cl 1.4), and a multihull that is neither fell through BOTH
            # and out of the function with no assessment and no violation.
            # Measured on an 18 m catamaran with windage undeclared:
            # cl13 None, cl14 None, stability_criterion None, and not one
            # stability violation.
            #
            # It is silent because the surrounding design is otherwise
            # right: R-GM is deliberately NOT emitted for a multihull (GM
            # is the monohull criterion and a catamaran passes it trivially
            # while remaining capsizable), and R-MHS is emitted as a
            # RECEIPT pointing at "the evaluation's cl13/cl14 receipt for
            # the measured verdict". With no cl13 and no cl14 that receipt
            # does not exist, so the pointer resolved to nothing and the
            # vessel came back clean.
            #
            # Same defect class as the rest of this campaign: a bar that
            # exists and is not consulted. An UNASSESSED multihull must
            # read as unassessed, never as passed.
            viol.append(
                f"multihull stability: UNASSESSED — this vessel is "
                f"{_loa:.1f} m with {_persons} persons, so NZ Part 40A "
                f"App.1 cl 1.3 (< 15 m and <= 50 persons) does not apply, "
                f"and cl 1.4 needs a DECLARED windage (mission.windage) "
                f"that was not given. No stability criterion in this tree "
                f"has judged it. This is a REFUSAL to answer, not a "
                f"finding against the design: declare the windage and cl "
                f"1.4 will assess it.")
        elif mission.windage.declared:
            # The >= 15 m / > 50 passenger class WITH a declared windage:
            # the full four-clause cl 1.4 verdict (2026-08-19 — (c)/(d)
            # computable once A and its centroid are declared). Costly
            # (a full GZ curve), honest, and only on declaration.
            _kg13 = kg
            _mha = multihull_gz_assessment(
                hull, float(hs.disp_kg), _kg13, rho,
                vessel=mission.vessel,
                trim_deg=float(trim if trim is not None else 0.0),
                windage=mission.windage, persons=_persons)
            _cl14 = _mha
            if _mha.passes is False:
                fails = [n for n, ok in (
                    ("(a) GZ area", _mha.clause_a_satisfied),
                    ("(b) GZmax heel >= 10 deg", _mha.clause_b_satisfied),
                    ("(c) wind heel <= 16 deg", _mha.clause_c_satisfied),
                    ("(d) residual area >= 0.028", _mha.clause_d_satisfied),
                ) if not ok]
                viol.append(
                    "multihull stability: NZ Part 40A App.1 cl 1.4 FAILED "
                    "on " + "; ".join(fails) + " (declared windage "
                    f"{mission.windage.lateral_area_m2} m2 at "
                    f"{mission.windage.centroid_above_wl_m} m)")
        else:
            viol.extend(multihull_stability_refusal(
                hs, gm_m,
                offset_load_assessed=manning is not Manning.UNCREWED))
    viol.extend(manning_refusals)
    # AXIS 3's receipts. A model out of its SUPPORT but still inside its
    # validity flag (the transition band) is reported and not counted as a
    # violation; a model outside its VALIDITY has already produced `early`
    # above via `res.valid`.
    flow_envelope = tuple(res.flow.envelope) if res.flow is not None else ()

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
        # THE LAST BARE SIGMA, and it was a second copy of a constant that
        # already lives in energy.py (gap H1). This line read
        # `en.wh_per_nm * 0.30` — a declared fraction of its own value, which
        # cannot narrow when the resistance model improves and cannot widen
        # when the resistance model disowns the answer. MEASURED on the
        # reference hull at 2.5 m/s: the propagated band is 105.3 Wh/NM against
        # the 185.5 the flat 0.30 declared (76% too wide), and at 4.6 m/s —
        # past FN_MICHELL_MAX, where `total_resistance` doubles its own sigma
        # to the size of the answer — the propagated band follows to 100% while
        # the flat 0.30 stayed at 0.30. It was MORE confident about a
        # prediction the resistance module had disowned than about one it stood
        # behind. The basis string comes from `energy` too, so a placeholder
        # can never again be served under a badge that does not say so.
        "wh_per_nm": ("L1", en.sigma_wh_per_nm, en.sigma_basis),
    }
    # WHICH resistance method answered, and why the other one did not (gap
    # E1b). Not in `values` below: it is a method receipt, not a quantity, and
    # it carries the resistance sigma so a reader cannot mistake it for a
    # second, differently-badged resistance.

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

    # THE DERIVED VESSEL QUANTITIES. `bridge_deck_clearance_required_m` is the
    # ship's own steady bow wave, U^2/(2g) — an exact stagnation rise and an
    # upper bound for a finite entrance angle. It is REQUIRED clearance, not
    # achieved clearance: the genome declares no wet-deck height, so there is
    # nothing to subtract it from and no constraint row is added. Reporting the
    # bar without a measurement is honest; scoring an unmeasured clearance as
    # satisfied is the defect class `wet_deck_clearance_g` refuses outright.
    # It says nothing about slamming in a seaway, which is relative motion
    # against the incident wave and belongs to `seakeeping`.
    vessel_report = {
        "topology": (vessel_cfg.topology.value if vessel_cfg is not None
                     else "monohull"),
        "manning": manning.value,
        "n_hulls": n_hulls,
        "separation_m": separation_m,
        "separation_over_lwl": (separation_m / max(float(p["LWL"]), 1e-9)
                                if n_hulls > 1 else 0.0),
        "beam_demihull_wl_m": hs.b_wl_max,
        "beam_overall_wl_m": hs.beam_overall_m,
        "i_t_m4": hs.i_t,
        "bridge_deck_clearance_required_m": (bow_wave_rise(u) if n_hulls > 1
                                             else 0.0),
        # AXIS 3, derived and reported beside the axes that were declared.
        "fn": res.flow.fn if res.flow is not None else res.fn,
        "re": res.flow.re if res.flow is not None else float("nan"),
        "models_admitted": ("michell" if res.flow is None or res.flow.michell_ok
                            else "") + ("+ittc57" if res.flow is None
                                        or res.flow.ittc57_ok else ""),
        # Every rule set that was NOT run, and every criterion that has no
        # implementation. A reader must never have to infer an absence.
        "rules_not_implemented": tuple(rules_not_implemented),
        "stability_criterion": (
            "ISO 12217-1 metacentric floor (a MONOHULL proxy)" if n_hulls == 1
            else ("NZ Part 40A App.1 cl 1.3 — uncontrolled-crowding heel and "
                  "trim, bar 8 deg, COMPUTED (see cl13)" if _cht is not None
                  else "cl 1.4 class (>= 15 m LOA or > 50 passengers): NOT "
                       "assessable — see violations; GM does not establish "
                       "multihull safety")),
        # R2.2's receipt: the criterion that DECIDED, with its numbers — a
        # PASSING verdict must be as auditable as a refusal.
        "cl14": (None if _cl14 is None else {
            "wind_heel_deg": _cl14.wind_heel_deg,
            "theta_h_deg": _cl14.theta_h_deg,
            "residual_area_m_rad": _cl14.residual_area_m_rad,
            "clauses": {"a": _cl14.clause_a_satisfied,
                        "b": _cl14.clause_b_satisfied,
                        "c": _cl14.clause_c_satisfied,
                        "d": _cl14.clause_d_satisfied},
            "passes": _cl14.passes}),
        "cl13": (None if _cht is None else {
            "persons": _cht.persons,
            "heel_deg": _cht.heel_deg,
            "trim_deg_crowd": _cht.trim_deg_crowd,
            "heel_ok": _cht.heel_ok, "trim_ok": _cht.trim_ok,
            "passes": _cht.passes, "basis": _cht.basis,
            "note": _cht.heel_lever_note}),
        "caveats": (() if n_hulls == 1 else (
            "KG is a single-hull KG: the bridge deck and anything on it are "
            "not in the weight model, so GM here is an UPPER estimate",
            "deck area, and therefore solar area, is ONE demihull's — the "
            "bridge deck contributes none, so range is an UNDER estimate",
            "viscous form interference between the demihulls is not modelled",
        )),
    }
    # §5/§6 targets receipt: delivered = the FLOATED equilibrium state.
    cp_target = mission_cp_target(mission)
    lcb_lo, lcb_hi, lcb_basis = mission_lcb_band(mission)
    targets_report = {
        "cp_target": cp_target,
        "cp_gene": float(p["Cp"]),
        "cp_delivered": float(hs.cp),
        "cp_error": (float(hs.cp) - cp_target if cp_target is not None
                     else None),
        "cp_tolerance": PRISMATIC_TOLERANCE,
        "cp_conformant": (abs(float(hs.cp) - cp_target)
                          <= PRISMATIC_TOLERANCE
                          if cp_target is not None else None),
        "cp_basis": ("target = limits.prismatic_target(mission.design_fn), "
                     "practice curve, basis approx; delivered = demihull "
                     "prismatic of the SOLVED equilibrium (HydroState.cp); "
                     "no target without a stated length"),
        "lcb_target_pct": None,
        "lcb_band_pct": (lcb_lo, lcb_hi),
        "lcb_delivered_pct": float(hs.lcb_pct_lwl),
        "lcb_basis": lcb_basis,
    }
    ev = Evaluation(
        ok=len(viol) == 0, tier="L1", violations=tuple(viol), hydro=hs, wl=wl,
        weights=wb, masses=agg, gm_m=gm_m, gm_l_m=gm_l_m,
        trim_deg=trim, list_deg=heel, resistance=res, energy=en, g=g,
        ply_thickness_m=t_ply, unaccounted_frac=unaccounted_frac,
        hull_lwl_m=float(p["LWL"]), rules=rules_rep, params=np.asarray(params),
        eval_ms=(time.perf_counter() - t0) * 1e3, badges=badges,
        vessel=vessel_report, targets=targets_report,
        resistance_envelope=flow_envelope,
        resistance_method=("michell+ittc57" if n_hulls == 1 else
                           "michell+ittc57 (catamaran: wave interference "
                           "exact in thin-ship theory, viscous form "
                           "interference NOT modelled, no experimental "
                           "anchor)"),
        holtrop_envelope_violations=holtrop_env,
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

    # THE INGEST PATH IS THE ONE PLACE CFD REACHES A SCORE, AND IT USED TO BE
    # THE WEAKEST LINK IN THE CHAIN. Until 2026-08-20 this block took a RAW
    # tail mean (`post.mean_resistance`) with no finiteness check, computed
    # its own drift with an `else 0.0` fallback on an empty window — a
    # too-short record therefore scored drift ZERO, the most settled answer
    # there is — and carried no LTS pseudo-time seam, so a diverged LTS case
    # whose "time" is pseudo-iterations could read as more than one
    # flow-through. It then took `abs()` of the result, which rectified a
    # SIGN FLIP into a resistance and made `pipeline.check_cfd`'s `ct <= 0`
    # refusal unreachable.
    #
    # It now delegates to `post.settled_drag`, which is the module that owns
    # every one of those seams (three-outcome vocabulary, per-component
    # drift AND batch error, symmetric doubling, the pseudo-time and
    # mixed-history NaN rules). An L3 badge means a SETTLED record here;
    # "ran to budget" is not convergence, and the Mac's 2026-08-20 export
    # measured how far apart those two are (15 runners, 3 settled).
    try:
        sd = post.settled_drag(case)
    except post.ForceHistoryError as e:
        # THE LADDER'S CONTRACT IS `TierRefusal`. `settled_drag` raises its
        # own error class for a history it cannot read or that cannot
        # support a window; letting that escape here would make an
        # unreadable case look like a CRASH to every caller that knows how
        # to handle a refusal. It is a refusal — a named one.
        raise TierRefusal(
            f"{case} has no history a settled verdict can be read from "
            f"({e}). An unmeasurable record is a refusal, not a badge."
        ) from e
    # ORDER MATTERS, AND THE RUN'S LENGTH IS CHECKED FIRST. A record covering
    # less than one flow-through is ALSO unsettled — necessarily, since the
    # free stream has not crossed the domain — but "0.57 of a flow-through"
    # sends the next session to the run length, while "the batch error
    # exceeds 5%" sends it to the statistics. The more specific cause is the
    # one worth naming, and `settled_drag` returns its verdict (rather than
    # raising) for a merely-unsettled record, so both are in hand here.
    flow_throughs = float(sd["flow_throughs"])
    if not math.isfinite(flow_throughs):
        raise TierRefusal(
            f"{case} carries pseudo-time (LTS) or a mixed history without a "
            f"`transient_tail_from` receipt, so it has NO flow-through count. "
            f"Pseudo-iterations divided by a domain length in metres is "
            f"fiction wearing a unit; an L3 badge needs real time.")
    if flow_throughs < _L3_MIN_FLOW_THROUGHS:
        raise TierRefusal(
            f"{case} covers {flow_throughs:.2f} of one flow-through. The free "
            f"stream has not crossed the domain, so the average still "
            f"contains the initial condition: this describes startup, not "
            f"resistance. No L3 badge is issued for it.")
    if not sd["settled"]:
        raise TierRefusal(
            f"{case} is {sd['outcome']}: " + "; ".join(sd["reasons"]) +
            ". An unsettled record is a picture of a transient, not a "
            "resistance, and it gets no L3 badge.")
    drag_tail = float(sd["drag_n"])          # already symmetric-corrected
    sigma = max(abs(float(sd["std_n"])), abs(float(sd["drift"])))
    symmetric = bool(sd["symmetric"])

    # PHYSICS SANITY, before any abs(). The L1 prior is this repository's own
    # cheap model at the same speed — not an accuracy reference (that is the
    # calibration lane's job) but the magnitude check that catches unit,
    # reference-area and column errors, which is exactly the shape of the two
    # force defects this project has actually shipped.
    prior_n = None
    try:
        _hs = solve(hull, rho, 0.0)
        _r = total_resistance(hull, u_case, hull.wetted_surface(0.0),
                              _hs.cb, rho=rho, lwl_eff=_hs.lwl_eff)
        prior_n = float(_r.total) if math.isfinite(_r.total) else None
    except Exception:                        # noqa: BLE001 - prior is optional
        # A missing prior must not become a passing magnitude check: the sign
        # and finiteness clauses still run, and the ratio is simply absent
        # from the receipt rather than defaulted to something agreeable.
        prior_n = None
    sanity = post.physics_sanity(drag_tail, prior_n=prior_n)
    if not sanity["ok"]:
        raise TierRefusal(
            f"{case} fails physics sanity: " + "; ".join(sanity["reasons"]))

    drag = abs(drag_tail)

    if not (dom_len > 0.0):
        raise TierRefusal(f"{case} declares domain_length_m={dom_len!r}")

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


def _rules_margin(fails) -> float:
    """The worst RELATIVE shortfall over failing findings THAT HAVE NUMBERS.

    Separated from the constraint table so the undecidable-vs-failing
    distinction has one home. See the comment at its call site for the
    incident.
    """
    finite = [f for f in fails
              if is_real_finite(f.measured) and is_real_finite(f.required)]
    if finite:
        return max(abs(f.measured - f.required) / max(abs(f.required), 1e-9)
                   for f in finite)
    return INFEASIBLE_G if fails else -0.01


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
