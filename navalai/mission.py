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

from .energy import EnergySpec

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
    "lwl_hint_m": (4.0, 20.0),
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
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(s: str) -> "MissionSpec":
        d = json.loads(s)
        e = d.pop("energy", {})
        m = MissionSpec(**{k: v for k, v in d.items() if k in MissionSpec.__dataclass_fields__})
        m.energy = EnergySpec(**e)
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
