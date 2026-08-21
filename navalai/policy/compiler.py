"""The compiler: ONE policy source, TWO outputs, and the ratchet law.

BuildPlan 3 §2.2, verbatim, overruling the Architect's "separate engine acting
as a pre-filter":

> So governance is a **compiler with two outputs from one source**:
> 1. a **parameter-space box** the sampler and NSGA-II are constructed inside
>    (LOA <= 12 m becomes a bound, not a rejection), and
> 2. **rows appended to the existing `evaluate.CONSTRAINT_NAMES` /
>    `Evaluation.g` vector**, so anything already consuming that vector is
>    governed for free.

Both come out of `compile_policy(Constitution)`. There is no second place a
governance number is written down, and — the point of the whole design — no
second place a PHYSICS number is written down either.

THE ADDITIVE RULE, WHICH IS WHAT MAKES GATE V3.0(d) PASS BY CONSTRUCTION
------------------------------------------------------------------------
A compiled policy may only APPEND rows to the constraint vector. It may never
rewrite one. Not `g['gm']`, not `FREEBOARD_FLOOR_M`, not a value the ladder
already computed.

That is not a stylistic preference, it is the mechanism behind

> **delete the policy file and no physics result may change.**

If a ratchet on the GM floor were implemented by substituting the tighter
number into `g['gm']`, then `g['gm']` would differ between a governed and an
ungoverned run and the structural test could only be passed by exempting the
row it is about. Implemented additively, the ladder's own row is byte-for-byte
what it always was and the tightening arrives as `policy_floors`, a row that
did not exist before. The feasible set is identical either way — max(a, b) <= 0
iff a <= 0 and b <= 0 — so nothing is lost by being honest about it.

The corollary is that `evaluate(..., policy=None)` must not merely produce the
same NUMBERS as before; it must run the same CODE. Every policy call site in
`evaluate.py` sits behind `if policy is not None`.

WHY A ROW AND A BOX BOTH, WHEN THE BOX ALREADY BOUNDS THE PARAMETER
-------------------------------------------------------------------
`max_hull_length_m` becomes an upper bound on the LWL parameter AND a
`policy_dna` constraint row, and that is deliberate duplication of an
ENFORCEMENT, not of a NUMBER — both read the same `PolicyValue`.

The precedent is `evaluate`'s `proportions` row: `grammar.check` bounds B/T on
the DESIGN draft, a hull was delivered at a floated B/T of 14.4 against a bar
of 12, and the fix was to re-check the floated state against the same shared
band. A box bounds what the search may PROPOSE; a row measures what the ladder
actually FLOATED. A design can enter the ladder from a saved genome, a latent
decode or a hand-written array, none of which passed through the box.

WHAT IS DELIBERATELY NOT A ROW
------------------------------
`allowed_propulsion`, `forbidden_propulsion` and `material_palette` compile to
`check_selection()`, a call, and NOT to a constraint row — because nothing in
the ladder declares a propulsion or a material yet, so the row would read the
same satisfied value on every design forever. This codebase has already shipped
one of those: `evaluate`'s `list` row read EXACTLY -2.000 across 800
evaluations while occupying an NSGA-II constraint dimension. A row is emitted
only where the constitution takes a position AND the ladder measures the
quantity; `CompiledPolicy.rows` is therefore computed, never a fixed tuple.

HOW HARD THE ROWS BITE — MEASURED, so that "it is a real constraint" is not an
assurance. 200 L0-feasible hulls drawn uniformly from `grammar.LOW/HIGH` (seed
0) and floated to the default 6 t mission, under `reference_policy()`:

    row              min      p50      max    violated
    policy_legal   -0.010   +0.139   +0.658     64.0%
    policy_dna     -0.514   +0.149   +0.672     66.5%
    policy_energy  -3.578   -0.119   +0.945     45.5%

Each removes a real part of the box — not 1% of it and not 99% — which is the
bar `limits.LCB_BAND_PCT_LWL` set for itself and the test
`tests/test_policy.py::test_every_policy_row_is_live_on_real_hulls` holds. Note
that these are measured on the UNBOUNDED grammar box on purpose: inside
`CompiledPolicy.box('C')` the LWL ceiling is already 11.9 m, so `policy_legal`
is mostly satisfied by construction and the row is the SECOND line of defence
for designs that did not come from the sampler. Judging the row on the sampled
box would understate it; judging the box by the row would misread what the box
is for.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np

from .. import grammar, limits
from .base import PolicyError, PolicyRefusal
from .dna import KIT_LINE_V3, DesignDNA
from .legal import (DISCLAIMER, MODULE_A_LENGTH_BREAK_M,
                    RCD_SCOPE_LENGTH_M, DeliveryRoute, LegalEnvelope,
                    art_20_row)

# --------------------------------------------------------------------------
# Every row this compiler can emit. Prefixed so a policy row can never collide
# with a ladder row, and enumerated here so `evaluate` can assert disjointness
# from CONSTRAINT_NAMES without importing the compiler.
# --------------------------------------------------------------------------
ROW_LEGAL = "policy_legal"
ROW_DNA = "policy_dna"
ROW_ENERGY = "policy_energy"
ROW_FLOORS = "policy_floors"
ROW_NAMES = (ROW_LEGAL, ROW_DNA, ROW_ENERGY, ROW_FLOORS)

# Direction of tightening. Named rather than a bool because "True means higher
# is stricter" is exactly the kind of comment that outlives its code.
FLOOR = "floor"        # a bar the design must EXCEED; raising it is tighter
CEILING = "ceiling"    # a bar the design must stay UNDER; lowering it is tighter
DIRECTIONS = (FLOOR, CEILING)


def _rel(bar: float, measured: float, direction: str) -> float:
    """Relative margin, > 0 == violated, in the sign convention of `evaluate.g`.

    Relative for the reason `LegalEnvelope.margins` gives: NSGA-II needs a
    gradient out of an infeasible region, and "0.05 m short of freeboard" means
    something different on a 4 m tender than on a 20 m barge.
    """
    scale = max(abs(float(bar)), 1e-9)
    if direction == FLOOR:
        return (float(bar) - float(measured)) / scale
    return (float(measured) - float(bar)) / scale


# ==========================================================================
# THE RATCHET REGISTRY
# ==========================================================================


@dataclass(frozen=True)
class Ratchet:
    """One `limits.py` bar a constitution is allowed to tighten.

    `live` READS `navalai.limits` at call time. It does not cache, and this
    module restates none of those numbers — so `limits.py` remains the single
    owner and a change there is picked up by the ratchet check on the next
    compile rather than at the next code review.

    `live` takes a design category because one of these bars genuinely has one
    (`gm_floor`), and a signature that fits every entry is one fewer branch.
    The rest ignore the argument.

    `measure` is optional and its absence is INFORMATION, not an oversight: a
    bar with no measured counterpart on an `Evaluation` still RATCHET-CHECKS at
    compile time (that is Gate V3.0(b)) but contributes no constraint row,
    because a row this module could only fill by recomputing physics would be
    the second engine §2.2 forbids.
    """

    key: str
    direction: str
    live: Callable[[str], float]
    what: str
    unit: str
    measure: Callable[[Any, Any], float | None] | None = None
    measured_what: str = ""

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise PolicyError(f"ratchet {self.key!r} direction "
                              f"{self.direction!r} not in {DIRECTIONS}")


def _b_wl(ev) -> float:
    return float(ev.hydro.b_wl_max)


RATCHETS: dict[str, Ratchet] = {
    r.key: r for r in (
        Ratchet(
            "freeboard_floor_m", FLOOR,
            lambda _cat: float(limits.FREEBOARD_FLOOR_M),
            "limits.FREEBOARD_FLOOR_M — the L1 freeboard floor", "m",
            lambda ev, _m: float(ev.hydro.freeboard_min),
            "minimum freeboard at the floated waterline"),
        Ratchet(
            "gm_floor_m", FLOOR,
            lambda cat: float(limits.gm_floor(cat)),
            "limits.gm_floor(category) — the ISO 12217 design-category GM floor",
            "m",
            lambda ev, _m: ev.gm_m,
            "GM after the free-surface correction"),
        Ratchet(
            "trim_limit_deg", CEILING,
            lambda _cat: float(limits.TRIM_LIMIT_DEG),
            "limits.TRIM_LIMIT_DEG — static trim from the arrangement alone",
            "deg",
            lambda ev, _m: None if ev.trim_deg is None else abs(ev.trim_deg),
            "static trim magnitude"),
        Ratchet(
            "list_limit_deg", CEILING,
            lambda _cat: float(limits.LIST_LIMIT_DEG),
            "limits.LIST_LIMIT_DEG — static list from a transverse offset",
            "deg",
            lambda ev, _m: None if ev.list_deg is None else abs(ev.list_deg),
            "static list magnitude"),
        Ratchet(
            "lcb_band_pct_lwl", CEILING,
            lambda _cat: float(limits.LCB_BAND_PCT_LWL),
            "limits.LCB_BAND_PCT_LWL — the LCB band about midships", "%LWL",
            lambda ev, _m: abs(float(ev.hydro.lcb_pct_lwl)),
            "|LCB| from midships"),
        Ratchet(
            "gm_over_beam_max", CEILING,
            lambda _cat: float(limits.GM_OVER_BEAM_MAX),
            "limits.GM_OVER_BEAM_MAX — the stiffness ceiling GM/B", "-",
            lambda ev, _m: (None if ev.gm_m is None
                            else float(ev.gm_m) / max(_b_wl(ev), 1e-9)),
            "GM / floated waterline beam"),
        Ratchet(
            "ply_thickness_m", FLOOR,
            lambda _cat: float(limits.PLY_THICKNESS_M),
            "limits.PLY_THICKNESS_M — the nominal stock sheet", "m",
            lambda ev, _m: float(ev.ply_thickness_m),
            "the bottom sheet ISO 12215-5 derived for this displacement"),
        # ---- ratchet-checked, but NOT measured on an Evaluation ----
        # The hull's own minimum bend radius lives on `geometry.Hull`, not on
        # the evaluation, and reconstructing a Hull here to read it would be
        # this module recomputing geometry. The bar still ratchets.
        Ratchet(
            "bend_radius_ratio", FLOOR,
            lambda _cat: float(limits.BEND_RADIUS_RATIO),
            "limits.BEND_RADIUS_RATIO — cold-bend radius as a multiple of the "
            "sheet thickness", "-"),
        Ratchet(
            "frame_spacing_m", CEILING,
            lambda _cat: float(limits.FRAME_SPACING_M),
            "limits.FRAME_SPACING_M — the ISO 12215-5 panel short span", "m"),
        Ratchet(
            "crew_mass_kg", FLOOR,
            lambda _cat: float(limits.CREW_MASS_KG),
            "limits.CREW_MASS_KG — the ISO default person mass", "kg"),
    )
}


# ==========================================================================
# OUTPUT 1 — THE PARAMETER BOX
# ==========================================================================


@dataclass(frozen=True)
class BoxEdit:
    """One bound the constitution moved, and the constant that moved it.

    Kept because a box with no provenance is a set of magic numbers, and
    because `tests/test_policy.py` asserts that every edit TIGHTENED — a box
    edit that widened a grammar bound would be a policy quietly enlarging the
    search space, which is the ratchet law broken on the other output.
    """

    param: str
    edge: str            # 'low' or 'high'
    was: float
    now: float
    source: str


@dataclass(frozen=True)
class ParameterBox:
    """The sampler's and NSGA-II's box, after governance.

    `low`/`high` are ordinary float arrays in `grammar.NAMES` order, so the
    consumer is `xl=box.low, xu=box.high` and nothing has to learn a new type.
    """

    names: tuple[str, ...]
    low: np.ndarray
    high: np.ndarray
    edits: tuple[BoxEdit, ...] = ()

    def as_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return self.low.copy(), self.high.copy()

    def contains(self, x) -> bool:
        v = np.asarray(x, dtype=float)
        return bool(v.shape == self.low.shape
                    and np.all(v >= self.low) and np.all(v <= self.high))

    def clip(self, x) -> np.ndarray:
        return np.clip(np.asarray(x, dtype=float), self.low, self.high)

    def sample(self, n: int, rng) -> np.ndarray:
        """n uniform draws INSIDE the box.

        This is output (1) doing its job: `LOA <= 12 m` is a bound, so a draw
        that violates it is never generated and never has to be rejected.
        """
        return rng.uniform(self.low, self.high, size=(int(n), len(self.low)))


# ==========================================================================
# THE CONSTITUTION AND ITS COMPILED FORM
# ==========================================================================


@dataclass(frozen=True)
class Constitution:
    """The ONE source: what the law allows, and what the owner prefers.

    Two fields and no third, because those are the two provenances
    `base.BASES` distinguishes and the two the owner may treat differently —
    `legal` they may not relax at any price, `dna` they may relax tomorrow.
    """

    name: str
    legal: LegalEnvelope
    dna: DesignDNA

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise PolicyError("a constitution with no name cannot be cited in "
                              "a release; name it")
        if not isinstance(self.legal, LegalEnvelope):
            raise PolicyError(f"Constitution.legal is a "
                              f"{type(self.legal).__name__}, not a LegalEnvelope")
        if not isinstance(self.dna, DesignDNA):
            raise PolicyError(f"Constitution.dna is a "
                              f"{type(self.dna).__name__}, not a DesignDNA")


@dataclass(frozen=True)
class RatchetFinding:
    """One accepted tightening: the pair, both numbers, and the direction.

    Printed on the compile report so a reader can see WHICH `limits.py` number
    each policy floor beat. The rejected case does not produce one of these; it
    raises, which is Gate V3.0(b).
    """

    key: str
    design_category: str
    policy_value: float
    limits_value: float
    direction: str
    unit: str
    what: str

    def __str__(self) -> str:
        arrow = ">" if self.direction == FLOOR else "<"
        return (f"{self.key} (category {self.design_category}): policy "
                f"{self.policy_value:g} {self.unit} {arrow} limits "
                f"{self.limits_value:g} {self.unit} — {self.what}")


@dataclass(frozen=True)
class CompiledPolicy:
    """A constitution that compiled. Both outputs hang off this object.

    Constructed ONLY by `compile_policy`, which is where the ratchet law is
    enforced — so possessing one of these IS the evidence that no floor was
    loosened.
    """

    constitution: Constitution
    rows: tuple[str, ...]
    ratchets: tuple[RatchetFinding, ...]
    disclaimer: str = DISCLAIMER

    # ------------------------------------------------------------ output 1

    def box(self, design_category: str,
            low: Sequence[float] | None = None,
            high: Sequence[float] | None = None) -> ParameterBox:
        """The parameter box for a craft of this design category.

        The category is REQUIRED and has no default, because the length bound
        genuinely depends on it: Art. 20(1)(c) gives category D the whole
        2.5-24 m band on Module A with no break at 12 m, so defaulting to C
        would silently over-route a category D design out of half its box.

        `low`/`high` default to the grammar's own bounds. A caller passing its
        own (as `optimize.HullProblem` does after applying the mission's length
        hint) gets those tightened, never widened.
        """
        cat = str(design_category).upper()
        env = self.constitution.legal
        if cat not in env.allowed_categories:
            raise PolicyRefusal(
                f"design category {cat!r} is not one of "
                f"{list(env.allowed_categories)}, which is what this "
                f"constitution's legal envelope is written for. There is no "
                f"parameter box for a craft it does not admit — that is a "
                f"categorical breach, and it is reported on the "
                f"{ROW_LEGAL!r} constraint row, not squeezed into a bound. "
                f"{DISCLAIMER}")

        lo = np.array(grammar.LOW if low is None else low, dtype=float)
        hi = np.array(grammar.HIGH if high is None else high, dtype=float)
        if lo.shape != (grammar.N_PARAMS,) or hi.shape != (grammar.N_PARAMS,):
            raise PolicyError(
                f"box bounds must be {grammar.N_PARAMS}-vectors in "
                f"grammar.NAMES order; got {lo.shape} and {hi.shape}")
        edits: list[BoxEdit] = []

        def tighten(param: str, edge: str, value: float, source: str) -> None:
            """Move a bound INWARD or leave it alone. Never outward.

            `max` on the low edge and `min` on the high edge is the ratchet law
            expressed on output (1). A policy that named a looser bound here
            would not raise — it would simply have no effect — so the EDIT is
            recorded only when the bound actually moved, and a policy whose
            box is unchanged says so in `edits`.
            """
            i = grammar.NAMES.index(param)
            arr = lo if edge == "low" else hi
            was = float(arr[i])
            now = max(was, float(value)) if edge == "low" else min(was,
                                                                  float(value))
            if now != was:
                arr[i] = now
                edits.append(BoxEdit(param, edge, was, now, source))

        dna = self.constitution.dna
        ratio = 1.0 if dna.lh_over_lwl is None else float(dna.lh_over_lwl.value)
        if ratio <= 0.0:
            raise PolicyError(
                f"lh_over_lwl {ratio!r} is not positive; hull length cannot be "
                f"derived from waterline length with it")

        # --- the RCD's own scope, which is law and not preference ---
        rcd_lo, rcd_hi = (float(v) for v in RCD_SCOPE_LENGTH_M.value)
        tighten("LWL", "low", rcd_lo / ratio, str(RCD_SCOPE_LENGTH_M.source))
        tighten("LWL", "high", rcd_hi / ratio, str(RCD_SCOPE_LENGTH_M.source))

        # --- the Art. 20 length break, but ONLY where it binds ---
        # It binds when a notified body has not been accepted AND this category
        # has a break at all. Category D has none, and encoding "12 m" for D
        # would be the §0 summary error this package already records under
        # `legal.DISCREPANCIES`.
        if not env.accept_notified_body:
            break_m = float(MODULE_A_LENGTH_BREAK_M.value)
            # The two rows the break separates, read from the Art. 20 table
            # rather than from a hard-coded list of which categories have a
            # break. That is the whole reason `legal.ART_20` is a table: the
            # bound appears for A/B/C and does NOT appear for D, and neither
            # fact is typed here.
            below = art_20_row(cat, math.nextafter(break_m, 0.0))
            above = art_20_row(cat, break_m)
            if below.module_a and not above.module_a:
                # Art. 20(1)(b)(i) reads 'to LESS THAN 12 m', so 12.00 m is
                # already the notified-body row. `nextafter` is the largest
                # float strictly below the break — the bound is exclusive in
                # the Directive and it is exclusive here.
                tighten("LWL", "high",
                        math.nextafter(break_m, 0.0) / ratio,
                        str(MODULE_A_LENGTH_BREAK_M.source))

        # --- owner preference ---
        if dna.max_hull_length_m is not None:
            tighten("LWL", "high", float(dna.max_hull_length_m.value) / ratio,
                    str(dna.max_hull_length_m.source))
        if dna.max_draft_m is not None:
            tighten("T", "high", float(dna.max_draft_m.value),
                    str(dna.max_draft_m.source))

        # --- the construction method, which is the bound this box was MISSING
        #
        # MEASURED 2026-08-21, running the flagship mission end to end: the
        # optimiser returned a hull at `roundness` 0.045 and
        # `unroll.hull_panels` refused it -- "a radiused bilge is not a
        # two-panel developable shell". Drawing 60 hulls from the same mission:
        # roundness > 0 on 60 of 60, median 0.541, unroll refused 60 of 60.
        #
        # The ladder was validating, badging and ranking a design space that is
        # ENTIRELY unbuildable in the one material this product is made of. The
        # 2026-08-21 reframe to plywood-only reached the BENCHMARK -- Gate 2M
        # demoted to solver verification -- and never reached the SEARCH SPACE.
        #
        # This is a BOUND and not a row, and that is the whole point of §9's
        # split: developability is a property of the shape the search PROPOSES,
        # decidable before a drop of physics is computed, so spending
        # evaluations outside it is pure waste. `certify` already measures
        # `non_developable_frac` on the floated hull -- but it feeds only the
        # CFD-candidacy SCORE, so it ranks hulls without ever refusing one.
        # A receipt is not a bar.
        if dna.requires_developable_shell():
            tighten("roundness", "high", 0.0, str(dna.construction.source))

        bad = [grammar.NAMES[i] for i in range(grammar.N_PARAMS)
               if lo[i] > hi[i]]
        if bad:
            raise PolicyError(
                f"this constitution compiles to an EMPTY parameter box on "
                f"{bad} for design category {cat}: the tightened lower bound is "
                f"above the tightened upper bound, so no hull satisfies it. A "
                f"box that admits nothing is a policy error, not a search that "
                f"returns no results — the optimiser would report the second "
                f"as a hard problem. Bounds: "
                + ", ".join(f"{n} [{lo[grammar.NAMES.index(n)]:.4g}, "
                            f"{hi[grammar.NAMES.index(n)]:.4g}]" for n in bad))
        return ParameterBox(tuple(grammar.NAMES), lo, hi, tuple(edits))

    # ------------------------------------------------------------ output 2

    def constraint_names(self) -> tuple[str, ...]:
        """`evaluate.CONSTRAINT_NAMES` plus this policy's rows, in g order.

        Imported lazily so that `navalai.policy` stays importable without
        pulling the whole ladder in, and so that no import cycle is created in
        the direction `evaluate -> policy` (there is none: `evaluate` takes a
        compiled policy as an argument and imports nothing from this package).
        """
        from ..evaluate import CONSTRAINT_NAMES
        return tuple(CONSTRAINT_NAMES) + self.rows

    def rows_for(self, ev, mission) -> tuple[dict[str, float], dict[str, str]]:
        """(values, explanations) for this policy's rows on one evaluation.

        Reads ONLY quantities the ladder has already computed. It floats no
        hull, solves no waterline and calls no rule — if it did, the physics
        would exist in two places and Gate V3.0(d) would be unfalsifiable.
        """
        from ..evaluate import INFEASIBLE_G

        g: dict[str, float] = {}
        why: dict[str, str] = {}
        dna = self.constitution.dna
        env = self.constitution.legal

        def worst(parts: list[tuple[float, str]]) -> tuple[float, str]:
            """The binding member of a row, or a satisfied row with no reason.

            -0.01 rather than 0.0 for a satisfied row, matching the `rules` row
            `evaluate` already emits, so 'exactly on the bar' and 'comfortably
            inside it' are not the same number.
            """
            if not parts:
                return -0.01, ""
            v, s = max(parts, key=lambda p: p[0])
            return v, (s if v > 0.0 else "")

        # ------------------------------------------------------ policy_legal
        if ROW_LEGAL in self.rows:
            # The DECLARED LWL, not the floated `lwl_eff`. MEASURED and
            # recorded in CLAUDE.md: at a declared 8.00 m the floated waterline
            # is 7.60 m, 5% short. Reading the floated length would understate
            # hull length by 5% at exactly the 12 m break the whole legal
            # envelope turns on, and LH >= LWL >= lwl_eff — so the declared
            # value is both the larger and the honest one. It is still
            # optimistic; `dna.lh_over_lwl` is where that is declared.
            lh = dna.lh_from_lwl(float(ev.hull_lwl_m))
            parts = [(m, r) for m, r in
                     env.margins(lh, mission.design_category)]
            v, s = worst(parts)
            g[ROW_LEGAL] = v
            why[ROW_LEGAL] = (
                f"legal envelope: {s} (hull length modelled as {lh:.2f} m from "
                f"a declared LWL of {ev.hull_lwl_m:.2f} m). {DISCLAIMER}"
                if s else "")

        # -------------------------------------------------------- policy_dna
        if ROW_DNA in self.rows:
            parts = []
            if dna.max_hull_length_m is not None:
                bar = float(dna.max_hull_length_m.value)
                lh = dna.lh_from_lwl(float(ev.hull_lwl_m))
                parts.append((_rel(bar, lh, CEILING),
                              f"hull length {lh:.2f} m exceeds the owner "
                              f"ceiling of {bar:.2f} m "
                              f"[{dna.max_hull_length_m.source}]"))
            if dna.max_draft_m is not None:
                bar = float(dna.max_draft_m.value)
                # The FLOATED draft, because the ceiling is about getting into
                # a canal and a marina at the mission displacement, and the
                # design draft is what the search proposes rather than what the
                # boat draws. The box bounds the design draft; this row
                # measures the floated one, and they are not the same number.
                dr = float(ev.hydro.draft)
                parts.append((_rel(bar, dr, CEILING),
                              f"floated draft {dr:.2f} m exceeds the owner "
                              f"ceiling of {bar:.2f} m "
                              f"[{dna.max_draft_m.source}]"))
            v, s = worst(parts)
            g[ROW_DNA] = v
            why[ROW_DNA] = s

        # ----------------------------------------------------- policy_energy
        if ROW_ENERGY in self.rows:
            bar = float(dna.min_solar_fraction.value)
            en = ev.energy
            # demand = solar - net, by the definition in `energy.energy_report`
            # (net = solar - hotel - propulsion). Derived rather than
            # recomputed from EnergySpec, so this module holds no copy of the
            # hotel load or the cruise-hours figure.
            demand = float(en.solar_kwh_day) - float(en.net_kwh_day)
            if not math.isfinite(demand) or demand <= 1e-9:
                g[ROW_ENERGY] = INFEASIBLE_G
                why[ROW_ENERGY] = (
                    f"solar fraction is UNDEFINED: the modelled daily demand "
                    f"is {demand:.4g} kWh/day, so there is no denominator. A "
                    f"quantity that could not be computed is a violation and "
                    f"never a pass.")
            else:
                frac = float(en.solar_kwh_day) / demand
                g[ROW_ENERGY] = _rel(bar, frac, FLOOR)
                why[ROW_ENERGY] = (
                    f"solar fraction {frac:.2f} of a {demand:.2f} kWh/day "
                    f"demand is below the owner floor of {bar:.2f} "
                    f"[{dna.min_solar_fraction.source}]"
                    if g[ROW_ENERGY] > 0.0 else "")

        # ----------------------------------------------------- policy_floors
        if ROW_FLOORS in self.rows:
            parts = []
            cat = str(mission.design_category).upper()
            for key, pv in dna.floors.items():
                r = RATCHETS[key]
                if r.measure is None:
                    continue
                bar = float(pv.value)
                m = r.measure(ev, mission)
                if m is None or not math.isfinite(float(m)):
                    parts.append((
                        float(INFEASIBLE_G),
                        f"{key}: the quantity behind it ({r.measured_what}) is "
                        f"{m!r}, so the policy floor cannot be checked — which "
                        f"is a violation and never a pass"))
                    continue
                parts.append((
                    _rel(bar, float(m), r.direction),
                    f"{key}: {r.measured_what} = {float(m):.4g} {r.unit} "
                    f"against the owner bar of {bar:g} {r.unit}, which is a "
                    f"tightening of {r.live(cat):g} {r.unit} in {r.what} "
                    f"[{pv.source}]"))
            v, s = worst(parts)
            g[ROW_FLOORS] = v
            why[ROW_FLOORS] = s

        return g, why

    # --------------------------------------------------------------- legal

    def delivery_route(self, hull_length_m: float,
                       design_category: str) -> DeliveryRoute:
        """Where this craft's conformity work goes. Gate V3.0(c)."""
        return self.constitution.legal.route(hull_length_m, design_category)

    def route_for(self, ev, mission) -> DeliveryRoute:
        """The route for an evaluated design, using the same LH model as the row."""
        lh = self.constitution.dna.lh_from_lwl(float(ev.hull_lwl_m))
        return self.delivery_route(lh, mission.design_category)

    def route_report(self, ev, mission) -> dict:
        """`route_for` as plain data, with a REFUSAL carried rather than raised.

        `route_for` raises `PolicyRefusal` for a craft the RCD does not define
        — a 26 m hull, or a design category the envelope does not admit — and
        that is right for a caller that asked a routing question directly. It
        is wrong for `evaluate`, which is running a sweep: an exception there
        would abort a population over a design the `policy_legal` row has
        ALREADY reported as a breach, with a gradient attached.

        So the refusal becomes a `mode: 'REFUSED'` record carrying the clause
        that refused it. What it must never become is a delivery mode chosen
        because a delivery mode had to be returned — that is the failure
        `legal.art_20_row` exists to prevent, and it is not undone here.
        """
        try:
            return self.route_for(ev, mission).as_dict()
        except PolicyRefusal as e:
            return {"mode": "REFUSED", "refusal": str(e),
                    "disclaimer": self.disclaimer}

    # ------------------------------------------------------- the palettes

    def check_selection(self, kind: str, value: str) -> None:
        """Raise `PolicyRefusal` if a selection is outside the owner's palette.

        A CALL and not a constraint row — see this module's docstring. When
        V3.2 gives components a place in the ladder this becomes a row, and the
        row will be live from its first evaluation rather than reading the same
        satisfied number forever.
        """
        dna = self.constitution.dna
        allowed = {"propulsion": dna.allowed_propulsion,
                   "material": dna.material_palette}
        forbidden = {"propulsion": dna.forbidden_propulsion}
        if kind not in allowed:
            raise PolicyError(
                f"no palette named {kind!r}; this constitution has "
                f"{sorted(allowed)}")
        deny = forbidden.get(kind)
        if deny is not None and value in deny.value:
            raise PolicyRefusal(
                f"{kind} {value!r} is on this constitution's forbidden list "
                f"[{deny.source}]")
        allow = allowed[kind]
        if allow is None:
            return                     # the constitution takes no position
        if value not in allow.value:
            raise PolicyRefusal(
                f"{kind} {value!r} is not in this constitution's palette "
                f"{sorted(allow.value)} [{allow.source}]")

    # -------------------------------------------------------------- report

    def report(self) -> dict:
        """What compiled, as plain data for the release and the evidence graph."""
        return {
            "constitution": self.constitution.name,
            "legal": {
                "intent": self.constitution.legal.intent,
                "allowed_categories": list(
                    self.constitution.legal.allowed_categories),
                "harmonised_standards_applied":
                    self.constitution.legal.harmonised_standards_applied,
                "accept_notified_body":
                    self.constitution.legal.accept_notified_body,
            },
            "dna": self.constitution.dna.name,
            "rows": list(self.rows),
            "ratchets": [str(r) for r in self.ratchets],
            "disclaimer": self.disclaimer,
        }


# ==========================================================================
# THE COMPILER
# ==========================================================================


def compile_policy(constitution: Constitution) -> CompiledPolicy:
    """Compile a constitution, or raise `PolicyError` naming what is wrong.

    THE RATCHET LAW, which is Gate V3.0(b):

      Policy may only ratchet a gate TIGHTER. A policy floor that would loosen
      a `limits.py` bar is rejected HERE, at compile time, with the offending
      pair named — not a runtime override, not a warning, not a note.

    Two details that are easy to get wrong and are tested:

    * The check runs for EVERY design category the legal envelope admits, not
      for one. `gm_floor` is category-dependent (C 0.45 m, D 0.35 m), so a
      policy floor of 0.40 m is a tightening of D and a LOOSENING of C. A
      constitution that admits both must beat both, and the error names the
      category it failed on.

    * EQUAL is rejected too. A policy value identical to the `limits.py` value
      is not a ratchet, it is A SECOND COPY OF THE NUMBER — this codebase's
      most expensive recurring defect (the GM floor at 0.35 in three modules
      against 0.45 in the rules gate; a 15 mm ply that failed its own scantling
      rule). A restatement drifts the moment `limits.py` moves, and it buys
      nothing, so it is refused with that said out loud.
    """
    if not isinstance(constitution, Constitution):
        raise PolicyError(f"compile_policy takes a Constitution, not a "
                          f"{type(constitution).__name__}")

    dna = constitution.dna
    env = constitution.legal
    findings: list[RatchetFinding] = []

    for key, pv in dict(dna.floors).items():
        if key not in RATCHETS:
            raise PolicyError(
                f"DesignDNA.floors[{key!r}] names no bar this platform owns. "
                f"The ratchetable bars are {sorted(RATCHETS)} — every one of "
                f"them reads `navalai/limits.py` live. A floor on a name that "
                f"is not there would be a governance number with nothing to "
                f"tighten, which is a fourth place for a limit to live.")
        r = RATCHETS[key]
        try:
            policy_value = float(pv.value)
        except (TypeError, ValueError) as e:
            raise PolicyError(
                f"DesignDNA.floors[{key!r}] value {pv.value!r} is not a number "
                f"({e}); a ratchet is a comparison and needs one") from None
        if not math.isfinite(policy_value):
            raise PolicyError(
                f"DesignDNA.floors[{key!r}] is {policy_value!r}. A non-finite "
                f"bar cannot be compared against {r.what}, and 'we could not "
                f"compare it' is never a pass.")

        for cat in env.allowed_categories:
            live = float(r.live(cat))
            tighter = (policy_value > live if r.direction == FLOOR
                       else policy_value < live)
            if tighter:
                findings.append(RatchetFinding(
                    key, cat, policy_value, live, r.direction, r.unit, r.what))
                continue
            if policy_value == live:
                raise PolicyError(
                    f"POLICY IS NOT A RATCHET, IT IS A SECOND COPY: "
                    f"DesignDNA.floors[{key!r}] = {policy_value:g} {r.unit} is "
                    f"EXACTLY {r.what} = {live:g} {r.unit} for design category "
                    f"{cat}. A restatement tightens nothing and drifts the "
                    f"moment limits.py moves — that is this codebase's most "
                    f"expensive recurring defect (GM 0.35 in three modules "
                    f"against 0.45 in the rules gate). State a strictly "
                    f"tighter value, or delete the row and let limits.py own "
                    f"the number. {DISCLAIMER}")
            direction_word = ("must be ABOVE" if r.direction == FLOOR
                              else "must be BELOW")
            raise PolicyError(
                f"POLICY WOULD LOOSEN A LIMIT, AND POLICY MAY ONLY RATCHET "
                f"TIGHTER: DesignDNA.floors[{key!r}] = {policy_value:g} "
                f"{r.unit} against {r.what} = {live:g} {r.unit} for design "
                f"category {cat}. This bar is a {r.direction}, so a policy "
                f"value {direction_word} it. Rejected at COMPILE TIME: a "
                f"runtime override would let a design be optimised against the "
                f"looser number and judged against the tighter one, which is "
                f"exactly how NSGA-II came to return a GM 0.40 m hull the "
                f"rules gate then refused. {DISCLAIMER}")

    # ------------------------------------------------------- which rows exist
    rows: list[str] = [ROW_LEGAL]      # a constitution always has a legal box
    if dna.max_hull_length_m is not None or dna.max_draft_m is not None:
        rows.append(ROW_DNA)
    if dna.min_solar_fraction is not None:
        rows.append(ROW_ENERGY)
    if any(RATCHETS[k].measure is not None for k in dna.floors):
        rows.append(ROW_FLOORS)
    ordered = tuple(n for n in ROW_NAMES if n in rows)

    compiled = CompiledPolicy(constitution, ordered, tuple(findings))

    # Compile the box for every category the envelope admits, so an empty box
    # is a COMPILE-time error rather than a surprise the first time somebody
    # asks the sampler for a hull. Nothing is kept: the box depends on the
    # caller's bounds, and caching one would be a third place a bound lives.
    for cat in env.allowed_categories:
        compiled.box(cat)
    return compiled


# --------------------------------------------------------------------------
# THE REFERENCE SKU. BuildPlan 3 §5: Kit-Line v3 is "the self-certifiable
# envelope (LH < 12 m, category C/D) delivered as a CNC kit. It is a
# CONFIGURATION, not a fork: same grammar, same ladder, one policy profile, one
# delivery mode."
#
# `floors` is EMPTY, and that is a measured statement rather than a placeholder:
# there is no bar in `limits.py` this product line wants tighter than the
# platform already holds. The consequence is that `policy_floors` is not among
# its rows at all — see `compile_policy` — which is the None doctrine of
# `DesignDNA` applied to the constraint vector.
# --------------------------------------------------------------------------
KIT_LINE_V3_CONSTITUTION = Constitution(
    name="Kit-Line v3 — self-certifiable envelope, own-build CNC plywood kit",
    legal=LegalEnvelope(
        intent="placed_on_market",
        harmonised_standards_applied=True,
        accept_notified_body=False,
        allowed_categories=("C", "D")),
    dna=KIT_LINE_V3)


def reference_policy() -> CompiledPolicy:
    """The compiled reference SKU. Compiled on demand, never at import time.

    Import-time compilation would make a `limits.py` edit that breaks the
    ratchet surface as an ImportError from an unrelated module, which is the
    wrong place to learn it. `tests/test_policy.py` compiles it explicitly.
    """
    return compile_policy(KIT_LINE_V3_CONSTITUTION)


__all__ = [
    "CEILING", "FLOOR", "DIRECTIONS", "ROW_NAMES", "ROW_LEGAL", "ROW_DNA",
    "ROW_ENERGY", "ROW_FLOORS", "Ratchet", "RATCHETS", "BoxEdit",
    "ParameterBox", "Constitution", "RatchetFinding", "CompiledPolicy",
    "compile_policy", "KIT_LINE_V3_CONSTITUTION", "reference_policy",
]
