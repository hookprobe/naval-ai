"""Mission spec: the typed contract between the NL front end and the physics.

The LLM (Phase 5) translates prose into THIS structure and nothing else; the
evaluator consumes only this structure. That is the 'AI proposes, deterministic
gates enforce' boundary.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from enum import Enum

from . import grammar
from .energy import EnergySpec
from .formlib import Topology            # AXIS 1's enum has ONE home; see below

DESIGN_CATEGORIES = ("A", "B", "C", "D")   # ISO 12217 / CE categories
WATERS = {"river": "D", "lake": "D", "coastal": "C", "offshore": "B", "ocean": "A"}

# ---------------------------------------------------------------------------
# THE ONE RANGE TABLE. It used to live in `translate._FIELD_RANGES` and guard
# the LLM path ONLY, so the SAME numbers arriving as prose or over HTTP were
# unbounded. MEASURED before this moved:
#
#   parse_mission("6 tonne boat at 0 knots")  -> cruise_speed_kn 0.0, notes ""
#     and evaluate() then returned range_solar_nm_day = 3.0e12 NM/day
#     (Earth's circumference is ~21,600 NM) with ok/L1 and no warning at all
#   parse_mission("5000 crew river barge")    -> crew 5000
#   MissionSpec(displacement_target_kg=-1.0)  -> accepted verbatim
#   ui/server.py `MissionSpec(**body)`        -> no clamp anywhere on the path
#
# The dataclass is the typed contract every front end must pass through, so the
# gate belongs on the contract and not on one of its three callers. `translate`
# imports THIS table rather than keeping a second copy — the recurring defect
# in this codebase is a number declared twice (CLAUDE.md, design-side
# invariants).
#
# CREW CEILING 12 -> 250, 2026-08-07. The old 12 was not arbitrary and it is
# worth saying why before replacing it: Directive (EU) 2016/1629 Art. 3 and
# ES-TRIN 1.01 define a PASSENGER VESSEL as one carrying MORE THAN 12
# passengers, so 12 was exactly the boundary below which a craft is not one.
# That was the right ceiling while this grammar emitted small craft only.
#
# It is no longer. `navalai/rules/estrin.py` now assesses inland craft in
# ES-TRIN scope — L >= 20 m, or L.B.T >= 100 m3 — and the grammar's LWL
# ceiling is 20.0 m, the same number this very table already carries for
# `lwl_hint_m`. A 20 m inland vessel that is IN ES-TRIN scope is by
# construction one whose crew the old ceiling declared impossible, and the
# clamp did not merely warn: MEASURED, `replace(m, crew=40).crew == 12`, so
# `translate.requirements_from_mission` built the `crew-fits-on-deck` row
# against a 12-person boat while the brief asked for 40. The asked-for number
# survived only as the prose note "crew 40 outside [1, 12]; clamped to 12".
#
# 250 is bounded by geometry, MEASURED 2026-08-07 with
# `ergonomics.working_deck_area_m2` at `seat_area_m2()` = 0.30 m2/person:
#
#   LWL 20.0, BWL 6.0 (L/B 3.33, the beamiest inside L_OVER_B_BAND),
#   otherwise mid shape parameters -> 95.53 m2 of working deck = 318 persons
#   corner search over all 15 grammar params, LWL/BWL pinned at max
#                                          -> 165.99 m2           = 553 persons
#
# Both of those are the E-DECK NECESSARY condition — the whole deck plan, with
# no console, cabin, side deck or Z1 boundary taken out — so real capacity is
# strictly less than either. 250 therefore sits below what the largest hull
# this grammar can emit could nominally seat, and above any inland day-trip
# vessel it could plausibly represent.
#
# This is a CONTRACT bound, not a capacity verdict. It exists to stop absurd
# input ("5000 crew river barge") reaching the physics; whether a given crew
# fits on a given hull is `rules.ergonomics.E-DECK`'s answer, and that bar is
# what must fail a crowded boat. Widening the contract does not widen the bar.
FIELD_RANGES: dict[str, tuple[float, float]] = {
    "displacement_target_kg": (300.0, 200_000.0),
    "cruise_speed_kn": (1.0, 30.0),
    "crew": (1, 250),
    # DERIVED, not retyped (audit D1, fixed R1.2): this row froze at
    # (4.0, 20.0) while the grammar's LWL box moved to (2.5, 24.0), so the
    # mission contract silently refused hints for hulls the grammar builds.
    # One length contract: whatever box the grammar declares IS the hint's
    # legal range.
    "lwl_hint_m": (float(grammar.LOW[grammar.NAMES.index("LWL")]),
                   float(grammar.HIGH[grammar.NAMES.index("LWL")])),
}

# EnergySpec's writable ranges, for the same reason and with the same history:
# `translate._ENERGY_RANGES` guarded the LLM only, while `parse_mission` set
# `battery_kwh` straight from prose. MEASURED: "canal boat with 999999 kWh"
# parsed to 999999 kWh, i.e. 7,499,993 kg of battery in a 6 t mission.
#
# These are NOT applied in `MissionSpec.__post_init__`. `battery_kwh == 0` is a
# live sentinel — `translate.requirements_from_mission` adds the
# solar-positive-day requirement only when it is positive, so clamping 0 up to
# the 1.0 floor would silently add a requirement the caller switched off. They
# are applied where an untrusted VALUE arrives (prose parse, LLM sanitise), not
# where a caller constructs a spec deliberately.
ENERGY_RANGES: dict[str, tuple[float, float]] = {
    "payload_kg": (50.0, 20_000.0),
    "battery_kwh": (1.0, 500.0),
    "hotel_kwh_day": (0.2, 50.0),
    "solar_yield_kwh_m2_day": (1.0, 7.0),
    "panel_packing": (0.1, 0.85),
    "panel_eff": (0.10, 0.30),
    "prop_efficiency": (0.3, 0.75),
    "motor_efficiency": (0.7, 0.98),
    "cruise_hours_day": (1.0, 24.0),
}

_DEFAULTS = {"displacement_target_kg": 6000.0, "cruise_speed_kn": 5.0,
             "crew": 2, "lwl_hint_m": None, "design_category": "C"}


# ---------------------------------------------------------------------------
# THE VESSEL — THREE ORTHOGONAL AXES, and every one of them SELECTS BEHAVIOUR
# ---------------------------------------------------------------------------
#
# NOT one "vessel type" enum, and not a list of named boats. Three axes, because
# the combinations are real and each one is a different piece of work:
#
#   AXIS 1  TOPOLOGY  monohull | catamaran | trimaran
#           selects the I_T sum (`hydrostatics.vessel_terms`), whether wave
#           interference applies at all (`resistance.total_resistance`), and —
#           the safety-critical half — WHICH STABILITY CRITERION GOVERNS.
#
#   AXIS 2  MANNING   crewed | liveaboard | uncrewed
#           selects WHICH RULE SET APPLIES. Uncrewed is not "crewed with zero
#           people": the RCD does not govern uncrewed craft at all, so ISO
#           12217-1's assessment — crew mass, accommodation, escape — does not
#           apply to it, and `limits.CREW_MASS_KG` and the offset-load crowding
#           fraction are crewed-only concepts.
#
#   AXIS 3  REGIME    DERIVED from size and speed (Fn, Re) — NEVER declared,
#           so it is not a field here. It lives in `resistance.flow_regime`
#           beside the models it admits or refuses, and it selects WHICH
#           PHYSICS MODELS MAY ANSWER. Declaring it would let a caller assert a
#           regime the geometry contradicts.
#
# A drone catamaran is topology=CATAMARAN, manning=UNCREWED, and a regime our
# solvers may not cover. Collapsing that into one enum would hide that those
# are three separate gaps.
#
# HOW MANY HULLS, AND HOW FAR APART
#
# WHY IT LIVES HERE AND NOT IN THE GENOME. `grammar.PARAMS` describes ONE
# moulded surface: LWL, BWL, deadrise, sheer, the chine plan-form. Every one of
# those is a property of a single hull and every consumer of the genome —
# `Hull`, `unroll`, `export`, `formlib` — reads it as one. Hull COUNT is not a
# property of that surface at all: two demihulls of the same genome are the same
# moulded surface built twice. Putting `n_hulls` in the parameter vector would
# put a topological switch inside a continuous box that NSGA-II samples
# uniformly and that `hull_ast.project` pins by typology, and every existing
# consumer would have to learn to ignore one column.
#
# It is a vessel-level object above the hull, referenced from `MissionSpec`,
# because that is the level at which the question is actually asked: a solar
# liveaboard wanting deck area and stability is a CONFIGURATION decision made
# with the mission, alongside the design category and the displacement target,
# and it is the same layer that `EnergySpec` already sits at.
#
# WHY SEPARATION IS A RATIO OF LWL AND NOT METRES. The physics is a function of
# s/Lwl at a given Froude number, in both halves of it:
#   * `resistance.n_theta_for_separation` is written in s/Lwl, and
#     `navalai/experiments.py` measured the interference optimum as an s/Lwl
#     that MOVES with Fn (0.390 at Fn 0.20, 0.300 at Fn 0.25, 0.430 at 0.30);
#   * the stability term A_wp d^2 scales with the same ratio once the demihull
#     is scaled with the hull.
# LWL is a free grammar parameter, so a spacing declared in metres would be a
# DIFFERENT physical configuration at every length the optimiser tries — the
# ratio is the thing that is held constant when the mission says "catamaran".
# `separation_m(lwl)` is the ONE place the conversion happens; nothing else in
# the tree multiplies the ratio by a length.
#
# THE BAND IS A CONTRACT BOUND, NOT A VERDICT, exactly like `FIELD_RANGES`
# above: it refuses absurd input. Whether a given spacing actually clears the
# demihulls of each other is a GEOMETRY question and is answered against the
# hull by `hydrostatics.vessel_terms`, which refuses an intersection.
SEPARATION_OVER_LWL_BAND = (0.05, 2.0)


# AXIS 1's enum IS `formlib.Topology`, IMPORTED AND NOT REDECLARED.
# `navalai/formlib.py` already owns it — monohull, catamaran, trimaran,
# quadrimaran, small-waterplane, supported — with a docstring explaining why a
# topology is not a peer of a section law, and `formlib.MISSION` already
# declares this product line's topology as CATAMARAN. Writing a second
# three-member `Topology` here would be the recurring defect in this codebase
# (a thing declared twice) applied to the one contract three agents have to
# agree on. `formlib` imports nothing from this package, so there is no cycle.
#
# WHAT ANOTHER MODULE SHOULD IMPORT: `from navalai.mission import Topology` or
# `from navalai.formlib import Topology` — they are the SAME object, and
# `mission.vessel.topology` is the stable accessor for a design's value.


class Manning(str, Enum):
    """AXIS 2. Who is aboard, and therefore WHICH RULE SET APPLIES.

    UNCREWED is not CREWED with zero people. The RCD (Directive 2013/53/EU)
    governs recreational craft; an uncrewed vehicle is outside it, so ISO
    12217-1 — a harmonised standard under that directive, and one whose whole
    assessment is built from crew mass, accommodation and escape — does not
    apply, and nothing in this repository applies in its place.
    """

    CREWED = "crewed"
    LIVEABOARD = "liveaboard"
    UNCREWED = "uncrewed"


# Hull count PER TOPOLOGY, in one place. `n_hulls` is a derived property of the
# topology and not a second field, so it is impossible to declare a catamaran
# with three hulls.
#
# TWO of `formlib.Topology`'s six members have NO hull count at all, and they
# are absent from this table on purpose rather than defaulted to 1:
# SMALL_WATERPLANE is a section law and SUPPORTED is a lift mechanism ("lift
# comes from something that is not buoyancy" — formlib's own words). Asking
# how many hulls a SUPPORTED craft has is a category error, and `n_hulls`
# raises for it instead of answering 1 — which is the `${VAR:-0}` pattern that
# has already cost this project a run.
#
# TRIMARAN AND QUADRIMARAN ARE DECLARABLE AND NOT EVALUABLE, which is a
# different thing from absent. A trimaran's centre hull is NOT a copy of its
# amas — different displacement, different waterline, different free-wave
# spectrum — while `grammar.PARAMS` carries exactly one moulded surface and
# `resistance.catamaran_interference` derives `I_cat = 2 I_demi cos(k_y s/2)`
# from two IDENTICAL translated Kochin amplitudes. Summing three copies of one
# genome would report a vessel nobody would build. So `evaluate` REFUSES the
# topology BY NAME, which keeps the gap visible instead of absent.
HULL_COUNT: dict[Topology, int] = {
    Topology.MONOHULL: 1,
    Topology.CATAMARAN: 2,
    Topology.TRIMARAN: 3,
    Topology.QUADRIMARAN: 4,
}
EVALUABLE_TOPOLOGIES = (Topology.MONOHULL, Topology.CATAMARAN)


@dataclass(frozen=True)
class VesselConfig:
    """The two DECLARED axes: topology and manning. Regime is derived, not here.

    Frozen because it is part of the design description, not a call argument:
    `hydrostatics.solve` and `resistance.total_resistance` must be asked about
    ONE vessel, and a mutable spacing that a caller could change between the
    two would produce a hydrostatic answer and a resistance answer for
    different boats.

    REFUSES rather than clamps. A multihull with no declared spacing is not a
    magnitude error that a clamp could sensibly resolve — it is an unspecified
    vessel, and `resistance._separation_or_raise` already refuses the same
    thing for the same reason ("a demihull spacing of zero, negative or NaN is
    not a degenerate boat, it is an unspecified one").

    `n_hulls` IS THE STABLE ACCESSOR other modules read. `hydrostatics.
    vessel_terms` duck-types on `.n_hulls` and `.separation_m(lwl)`;
    `grammar`/`limits` should key their topology-conditional bands off
    `mission.vessel.topology` (`navalai.mission.Topology`), which is the enum
    and never a string literal.
    """

    topology: Topology = Topology.MONOHULL
    manning: Manning = Manning.CREWED
    separation_over_lwl: float = 0.0     # centreplane to centreplane, / Lwl

    def __post_init__(self) -> None:
        # Coerce first: a spec arriving from JSON carries plain strings, and a
        # `topology` that is the string "catamaran" while every comparison in
        # the tree is against the enum would silently evaluate as a monohull.
        try:
            object.__setattr__(self, "topology", Topology(self.topology))
            object.__setattr__(self, "manning", Manning(self.manning))
        except ValueError as e:
            raise ValueError(
                f"VesselConfig: {e}. topology is one of "
                f"{[t.value for t in Topology]}, manning one of "
                f"{[m.value for m in Manning]}.") from e
        s = self.separation_over_lwl
        if not (isinstance(s, (int, float)) and math.isfinite(s)):
            raise ValueError(
                f"VesselConfig: separation_over_lwl = {s!r} is not a finite "
                f"number")
        if self.n_hulls == 1:
            if float(s) != 0.0:
                raise ValueError(
                    f"VesselConfig: topology {self.topology.value} with "
                    f"separation_over_lwl = {s!r}. A monohull has nothing to "
                    f"be separated from; a spacing here would be silently "
                    f"ignored by every consumer, which is how a two-hull "
                    f"intention becomes a one-hull answer.")
            return
        lo, hi = SEPARATION_OVER_LWL_BAND
        if not (lo <= float(s) <= hi):
            raise ValueError(
                f"VesselConfig: separation_over_lwl = {float(s):g} is outside "
                f"{list(SEPARATION_OVER_LWL_BAND)}. This is a contract bound, "
                f"not a stability or resistance verdict — whether the "
                f"demihulls clear each other is checked against the actual "
                f"hull by hydrostatics.vessel_terms.")

    @property
    def n_hulls(self) -> int:
        """Hull count, DERIVED from the topology. Never a second field."""
        try:
            return HULL_COUNT[self.topology]
        except KeyError:
            raise ValueError(
                f"VesselConfig: topology {self.topology.value!r} has no hull "
                f"count — it is a section law or a lift mechanism, not a "
                f"number of hulls. Asking how many hulls it has is a category "
                f"error and is refused rather than answered with 1.") from None

    def separation_m(self, lwl: float) -> float:
        """Centreplane-to-centreplane spacing [m] on a waterline length `lwl`.

        THE ONE HOME OF THE RATIO -> METRES CONVERSION. `hydrostatics` needs it
        for the parallel-axis term and `resistance` needs it for the
        interference phase, and if the two ever derived it from different
        lengths they would be describing different vessels while sharing an
        `Evaluation`.
        """
        if not (isinstance(lwl, (int, float)) and math.isfinite(lwl)
                and lwl > 0.0):
            raise ValueError(
                f"VesselConfig.separation_m: lwl = {lwl!r} is not a positive "
                f"finite length, so the spacing has no value here")
        return float(self.separation_over_lwl) * float(lwl)

    @property
    def is_multihull(self) -> bool:
        return self.n_hulls > 1

    @property
    def is_evaluable(self) -> bool:
        """False for a topology this project can DECLARE but not evaluate.

        The refusal itself belongs to `evaluate`, which says which topology and
        why; this is only the predicate, so nobody has to spell the tuple out
        twice.
        """
        return self.topology in EVALUABLE_TOPOLOGIES


@dataclass
class MissionSpec:
    name: str = "unnamed mission"
    lwl_hint_m: float | None = None
    displacement_target_kg: float = 6000.0
    cruise_speed_kn: float = 5.0
    design_category: str = "C"           # worst waters intended
    crew: int = 2
    waters: str = "river+coastal"
    energy: EnergySpec = field(default_factory=EnergySpec)
    # Default is a MONOHULL, so every existing mission — and every one built
    # by `MissionSpec(**body)` over HTTP, which cannot know about this field —
    # describes exactly the vessel it described before multihull support
    # existed, and the ladder runs the identical arithmetic on it.
    vessel: VesselConfig = field(default_factory=VesselConfig)
    notes: str = ""

    def __post_init__(self) -> None:
        self.notes = "; ".join(n for n in [self.notes, *self.clamp()] if n)

    def clamp(self) -> list[str]:
        """Force every field into `FIELD_RANGES`; return one note per change.

        Idempotent, and callable AFTER construction — `parse_mission` and
        `translate.sanitize` both build a spec and then `setattr` onto it, which
        bypasses `__post_init__` entirely. A gate that only fires in the
        constructor would have been no gate at all for the two paths that
        actually carry untrusted numbers.

        A clamp is always RECORDED. The original finding was not that 0 knots
        was accepted; it was that 0 knots was accepted with `notes` EMPTY, so
        the caller had no way to know the mission it got back was not the
        mission it asked for.
        """
        notes: list[str] = []
        for k, (lo, hi) in FIELD_RANGES.items():
            raw = getattr(self, k)
            if raw is None:
                continue                      # lwl_hint_m is legitimately unset
            try:
                val = float(raw)
            except (TypeError, ValueError):
                notes.append(f"{k}={raw!r} is not a number; default "
                             f"{_DEFAULTS[k]} used")
                setattr(self, k, _DEFAULTS[k])
                continue
            # NaN survives min/max — every comparison against it is False — so
            # `min(max(nan, lo), hi)` returns nan. translate.sanitize learned
            # this the hard way (a nan displacement target floated the hull at
            # its own budget and reported ok=True); the contract must not have
            # to learn it again.
            if not math.isfinite(val):
                notes.append(f"{k} was non-finite ({raw!r}); default "
                             f"{_DEFAULTS[k]} used")
                setattr(self, k, _DEFAULTS[k])
                continue
            new = min(max(val, lo), hi)
            if new != val:
                notes.append(f"{k} {val:g} outside [{lo:g}, {hi:g}]; "
                             f"clamped to {new:g}")
            setattr(self, k, int(new) if k == "crew" else float(new))

        cat = str(self.design_category).upper()
        if cat not in DESIGN_CATEGORIES:
            notes.append(f"design_category {self.design_category!r} is not one "
                         f"of {'/'.join(DESIGN_CATEGORIES)}; "
                         f"{_DEFAULTS['design_category']} used")
            cat = _DEFAULTS["design_category"]
        self.design_category = cat
        return notes

    def cruise_speed_ms(self) -> float:
        return self.cruise_speed_kn * 0.514444

    def to_json(self) -> str:
        # `default=` because `formlib.Topology` is a plain `enum.Enum`, not a
        # str mixin, and `asdict` does not unwrap it — `json.dumps` would raise
        # `TypeError: Object of type Topology is not JSON serializable`. The
        # value written is the plain word ("catamaran"), which is what
        # `VesselConfig.__post_init__` coerces back, so the round trip is
        # closed. Importing formlib's enum rather than declaring a str-mixin
        # copy is worth this one line.
        return json.dumps(asdict(self), indent=2,
                          default=lambda o: getattr(o, "value", str(o)))

    @staticmethod
    def from_json(s: str) -> "MissionSpec":
        d = json.loads(s)
        e = d.pop("energy", {})
        # `asdict` flattens VesselConfig to a dict on the way out, so it has to
        # be rebuilt as the frozen type on the way back in. Assigning the raw
        # dict would give a MissionSpec whose `.vessel.n_hulls` raises
        # AttributeError deep inside `evaluate` — a round-trip that looks like
        # it worked. `.pop` before the field filter for the same reason `energy`
        # is popped: the filter would otherwise pass the dict straight through.
        v = d.pop("vessel", None)
        m = MissionSpec(**{k: v2 for k, v2 in d.items()
                           if k in MissionSpec.__dataclass_fields__})
        m.energy = EnergySpec(**e)
        if v is not None:
            m.vessel = VesselConfig(**v)
        return m


# --- deterministic keyword translator (rule-based floor; LLM hook sits above) --

_NUM = r"(\d+(?:[.,]\d+)?)"
# Unit separator: a space, a hyphen, or nothing. "9-metre" and "3-tonne" are
# ordinary English and were silently unparsed while `\s*` only spanned spaces.
_SEP = r"[\s-]*"


def parse_mission(text: str) -> MissionSpec:
    """Rule-based NL -> MissionSpec. Deliberately conservative: anything it
    cannot parse stays at a safe default and is listed in .notes. The LoRA
    translator (Phase 5, BuildPlan) plugs in above this floor; research finding
    S1.5: base LLMs are unreliable at structured params without fine-tuning."""
    # Thousands separators are stripped BEFORE the decimal-comma substitution.
    # MEASURED: "a 6,000 kg river cruiser" parsed to 6.000 kg and "1,500 kg"
    # to 1.500 kg, because `.replace(",", ".")` ran over the whole string and
    # `_NUM` then matched "6.000" as a decimal. `notes` came back EMPTY, so it
    # read as a clean parse, and evaluate()'s max(budget, target) quietly
    # substituted the weight model for the displacement the user asked for.
    t = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text.lower()).replace(",", ".")
    m = MissionSpec(name=text.strip()[:70])
    unparsed = []

    if g := re.search(_NUM + _SEP + r"(?:tonnes?|tons?|t)\b", t):
        m.displacement_target_kg = float(g.group(1)) * 1000.0
    elif g := re.search(_NUM + _SEP + r"kg\b", t):
        m.displacement_target_kg = float(g.group(1))
    else:
        unparsed.append("displacement (default 6 t)")

    if g := re.search(_NUM + _SEP + r"(?:metres?|meters?|m)\b", t):
        m.lwl_hint_m = float(g.group(1))

    if g := re.search(_NUM + _SEP + r"(?:knots?|kn)\b", t):
        m.cruise_speed_kn = float(g.group(1))
    elif g := re.search(_NUM + _SEP + r"km/?h", t):
        m.cruise_speed_kn = float(g.group(1)) / 1.852
    else:
        unparsed.append("cruise speed (default 5 kn)")

    cats = [c for w, c in WATERS.items() if w in t]
    if "black sea" in t or "coastal" in t:
        cats.append("C")
    if "danube" in t or "river" in t or "canal" in t:
        cats.append("D")
    if "offshore" in t or "ocean" in t:
        cats.append("B")
    # An EXPLICIT design category beats anything inferred from waters. Without
    # this, "category A" parsed to the default C — the request was read, the
    # word 'category' matched nothing, and the mission silently came back one
    # or more categories weaker than asked for. Note "." because the caller has
    # already turned commas into full stops.
    explicit = None
    if g := re.search(r"categor(?:y|ies)" + _SEP + r"[.:]?" + _SEP + r"([a-d])\b", t):
        explicit = g.group(1).upper()

    if explicit:
        m.design_category = explicit
        if cats and min(cats) < explicit:
            # Asking for C while naming ocean waters is a real conflict, not a
            # typo to silently resolve: honour the stated category and say so.
            unparsed.append(f"waters imply category {min(cats)}, "
                            f"stated category {explicit} used")
        m.waters = ",".join(sorted(set(cats))) if cats else explicit
    elif cats:
        m.design_category = min(cats)   # 'A' < 'B' < 'C' < 'D': keep the worst waters
        m.waters = ",".join(sorted(set(cats)))
    else:
        unparsed.append("waters (default category C)")

    if g := re.search(r"(\d+)" + _SEP + r"(?:crew|people|persons|berths)", t):
        m.crew = int(g.group(1))

    solar = "solar" in t
    if g := re.search(_NUM + _SEP + r"kwh", t):
        # Clamped through the SHARED table: prose was the one writer of
        # battery_kwh that had no bound at all. "999999 kWh" parsed verbatim,
        # which is 7,499,993 kg of LiFePO4 in a 6 t mission.
        lo, hi = ENERGY_RANGES["battery_kwh"]
        raw = float(g.group(1))
        kwh = min(max(raw, lo), hi)
        if kwh != raw:
            unparsed.append(f"battery {raw:g} kWh outside [{lo:g}, {hi:g}]; "
                            f"clamped to {kwh:g}")
        m.energy = EnergySpec(battery_kwh=kwh)
    if solar and m.energy.battery_kwh == 30.0:
        pass  # defaults already solar-electric

    # The clamp runs LAST, after every `setattr` above: `__post_init__` saw only
    # the defaults, so a parsed 0 knots or 5000 crew would have walked straight
    # past it. Its notes join the unparsed list, which is the only channel this
    # function has for saying "what you got back is not what you asked for".
    unparsed.extend(m.clamp())
    m.notes = "; ".join(unparsed)
    return m
