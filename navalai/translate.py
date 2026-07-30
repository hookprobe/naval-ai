"""Phase 5: NL mission translation with a hard AI/deterministic boundary.

Research grounding: base LLMs are unreliable at structured params without
fine-tuning (LLM-as-UI, Ocean Eng. 2026), and one-shot LLM geometry authoring
scores ~0 strict passes (FEA-agent benchmark 2026). Therefore:
  - the LLM (any provider, injected as a callable) may ONLY emit MissionSpec
    JSON; it is schema-filtered, range-clamped, and falls back to the
    rule-based floor on any fault
  - geometry parameters are NOT in MissionSpec: there is no code path from
    the model's output to the hull grammar
  - requirements are typed executable checkers graded against the ladder
    (the Hephaestus 'requirements as executable contract' pattern)
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import json

from .energy import EnergySpec
from .evaluate import Evaluation
from .mission import DESIGN_CATEGORIES, MissionSpec, parse_mission

# hard ranges for every LLM-writable field: outside -> clamped or rejected
_FIELD_RANGES = {
    "displacement_target_kg": (300.0, 200_000.0),
    "cruise_speed_kn": (1.0, 30.0),
    "crew": (1, 12),
    "lwl_hint_m": (4.0, 20.0),
}
_ENERGY_RANGES = {
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

TRANSLATOR_PROMPT = """Translate the boating mission below into JSON with ONLY
these keys (omit unknowns): displacement_target_kg, cruise_speed_kn, crew,
lwl_hint_m, design_category (one of A/B/C/D), waters, energy {battery_kwh,
payload_kg, hotel_kwh_day, cruise_hours_day}. No other keys. No prose.
Mission: """


def sanitize(raw: dict, floor: MissionSpec) -> MissionSpec:
    """Schema-filter + clamp an untrusted dict onto the rule-based floor."""
    m = replace(floor)
    for k, (lo, hi) in _FIELD_RANGES.items():
        if k in raw:
            try:
                val = float(raw[k])
            except (TypeError, ValueError):
                continue
            val = min(max(val, lo), hi)
            setattr(m, k, int(val) if k == "crew" else val)
    if str(raw.get("design_category", "")).upper() in DESIGN_CATEGORIES:
        m.design_category = str(raw["design_category"]).upper()
    if isinstance(raw.get("waters"), str) and raw["waters"]:
        m.waters = raw["waters"][:60]
    e_raw = raw.get("energy") or {}
    if isinstance(e_raw, dict):
        e_kw = {}
        for k, (lo, hi) in _ENERGY_RANGES.items():
            if k in e_raw:
                try:
                    e_kw[k] = min(max(float(e_raw[k]), lo), hi)
                except (TypeError, ValueError):
                    pass
        if e_kw:
            base = {f: getattr(m.energy, f) for f in EnergySpec.__dataclass_fields__}
            base.update(e_kw)
            m.energy = EnergySpec(**base)
    return m


def translate(text: str, llm: Callable[[str], str] | None = None) -> MissionSpec:
    """NL -> MissionSpec. llm is an optional provider callable(prompt)->text.
    Any misbehaviour (bad JSON, junk keys, absurd values) degrades safely to
    the deterministic rule-based floor — never an exception, never geometry."""
    floor = parse_mission(text)
    if llm is None:
        return floor
    try:
        raw = json.loads(llm(TRANSLATOR_PROMPT + text))
        if not isinstance(raw, dict):
            return floor
        return sanitize(raw, floor)
    except Exception:
        return floor


# ---------------- executable requirement checkers ----------------

@dataclass(frozen=True)
class Requirement:
    name: str
    clause: str                       # provenance: where this bar comes from
    check: Callable[[Evaluation], bool]
    detail: Callable[[Evaluation], str]


def requirements_from_mission(m: MissionSpec) -> list[Requirement]:
    reqs = [
        Requirement(
            "floats-at-budget", "Archimedes; BuildPlan L1",
            lambda ev: ev.hydro is not None,
            lambda ev: "hull cannot carry its own weight budget"
                       if ev.hydro is None else "floats"),
        Requirement(
            "gm-floor", "L1 floor 0.35 m (ISO 12217 assessment is tier R)",
            lambda ev: ev.gm_m is not None and ev.gm_m >= 0.35,
            lambda ev: f"GM {ev.gm_m:.2f} m" if ev.gm_m is not None else "no GM"),
        Requirement(
            "freeboard-floor", "L1 floor 0.25 m at load",
            lambda ev: ev.hydro is not None and ev.hydro.freeboard_min >= 0.25,
            lambda ev: f"freeboard {ev.hydro.freeboard_min:.2f} m"
                       if ev.hydro else "n/a"),
        Requirement(
            "carries-target", "mission displacement target",
            lambda ev: ev.hydro is not None
                       and ev.hydro.disp_kg >= 0.98 * m.displacement_target_kg,
            lambda ev: f"displaces {ev.hydro.disp_kg:.0f} kg"
                       if ev.hydro else "n/a"),
    ]
    if m.energy.battery_kwh > 0:
        reqs.append(Requirement(
            "solar-positive-day", "mission: net energy >= 0 at cruise plan",
            lambda ev: ev.energy is not None and ev.energy.net_kwh_day >= 0,
            lambda ev: f"net {ev.energy.net_kwh_day:+.1f} kWh/day"
                       if ev.energy else "n/a"))
    return reqs


def grade(ev: Evaluation, reqs: list[Requirement]) -> dict:
    """Typed pass/fail report — the contract the agentic loop is graded on."""
    rows = []
    for r in reqs:
        try:
            ok = bool(r.check(ev))
        except Exception:
            ok = False
        rows.append({"name": r.name, "clause": r.clause, "pass": ok,
                     "detail": r.detail(ev) if ev else "n/a"})
    return {"pass": all(r["pass"] for r in rows),
            "passed": sum(r["pass"] for r in rows), "total": len(rows),
            "requirements": rows}
