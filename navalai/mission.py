"""Mission spec: the typed contract between the NL front end and the physics.

The LLM (Phase 5) translates prose into THIS structure and nothing else; the
evaluator consumes only this structure. That is the 'AI proposes, deterministic
gates enforce' boundary.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from .energy import EnergySpec

DESIGN_CATEGORIES = ("A", "B", "C", "D")   # ISO 12217 / CE categories
WATERS = {"river": "D", "lake": "D", "coastal": "C", "offshore": "B", "ocean": "A"}


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
    t = text.lower().replace(",", ".")
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
        m.energy = EnergySpec(battery_kwh=float(g.group(1)))
    if solar and m.energy.battery_kwh == 30.0:
        pass  # defaults already solar-electric

    m.notes = "; ".join(unparsed)
    return m
