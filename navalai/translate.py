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
import math

from .energy import EnergySpec
from .mission import Topology, VesselConfig
from .evaluate import Evaluation
from .limits import FREEBOARD_FLOOR_M, gm_floor
from .mission import (DESIGN_CATEGORIES, ENERGY_RANGES, FIELD_RANGES,
                      MissionSpec, parse_mission)

# Hard ranges for every LLM-writable field: outside -> clamped or rejected.
#
# THESE ARE IMPORTED, NOT RETYPED. They lived here as `_FIELD_RANGES` /
# `_ENERGY_RANGES` and guarded the LLM path ONLY, so `parse_mission` and
# `ui/server.py`'s `MissionSpec(**body)` wrote the same fields with no bound —
# 0 knots gave 3.0e12 NM/day of solar range with ok=True and an EMPTY notes
# field. The gate now sits on the contract (`MissionSpec.clamp`) and this module
# reads the same table, so there is one set of numbers rather than two that can
# drift apart the way GM 0.35/0.45 did (CLAUDE.md, design-side invariants).
_FIELD_RANGES = FIELD_RANGES
_ENERGY_RANGES = ENERGY_RANGES

TRANSLATOR_PROMPT = """Translate the boating mission below into JSON with ONLY
these keys (omit unknowns): displacement_target_kg, cruise_speed_kn, crew,
lwl_hint_m, bwl_hint_m, berths, air_draft_max_m, design_category (one of
A/B/C/D), waters, energy {battery_kwh, payload_kg, hotel_kwh_day,
cruise_hours_day}. No other keys. No prose.
Mission: """


def sanitize(raw: dict, floor: MissionSpec) -> MissionSpec:
    """Schema-filter + clamp an untrusted dict onto the rule-based floor."""
    m = replace(floor)
    notes = [floor.notes] if floor.notes else []
    for k, (lo, hi) in _FIELD_RANGES.items():
        if k in raw:
            try:
                val = float(raw[k])
                # NaN survives min/max: every comparison against it is False,
                # so `min(max(nan, lo), hi)` returns nan and a nan
                # displacement target then made evaluate() return ok=True with
                # no violations while floating the hull at its own budget — a
                # 6 t mission silently became a 2.8 t boat. Reject non-finite
                # BEFORE clamping. `int()` moved inside the guard because
                # int(float('nan')) raises, and sanitize() is public API.
                if not math.isfinite(val):
                    notes.append(f"LLM sent a non-finite {k}; floor kept")
                    continue
                val = min(max(val, lo), hi)
                setattr(m, k, int(val) if k == "crew" else val)
            except (TypeError, ValueError, OverflowError):
                continue

    # DESIGN CATEGORY RATCHETS ONE WAY: stricter wins, never weaker.
    # Gate 5's bar is "zero pathways for the LLM to mutate geometry or OVERRIDE
    # A GATE". MEASURED: on an ocean brief the deterministic floor parses
    # category A (GM floor 0.60 m); an LLM returning {"design_category":"D"}
    # was accepted verbatim and the floor became 0.35 m — a 42% relaxation of a
    # stability bar, with no note. `parse_mission` already detects exactly this
    # conflict; sanitize() bypassed it. 'A' < 'B' < 'C' < 'D' orders severest
    # first, so min() is the ratchet.
    cat = str(raw.get("design_category", "")).upper()
    if cat in DESIGN_CATEGORIES:
        if cat > floor.design_category:
            notes.append(f"LLM proposed category {cat}, weaker than the "
                         f"rule-based floor {floor.design_category}; floor kept")
        m.design_category = min(cat, floor.design_category)

    if isinstance(raw.get("waters"), str) and raw["waters"]:
        # Whitelist: the raw string was persisted and echoed verbatim, so a
        # payload could carry control characters and markup into the record.
        m.waters = "".join(c for c in raw["waters"][:60]
                           if c.isalnum() or c in " ,.+/-")
    e_raw = raw.get("energy") or {}
    if isinstance(e_raw, dict):
        e_kw = {}
        for k, (lo, hi) in _ENERGY_RANGES.items():
            if k in e_raw:
                try:
                    v = float(e_raw[k])
                    if not math.isfinite(v):
                        continue
                    e_kw[k] = min(max(v, lo), hi)
                except (TypeError, ValueError, OverflowError):
                    pass
        if e_kw:
            base = {f: getattr(m.energy, f) for f in EnergySpec.__dataclass_fields__}
            base.update(e_kw)
            m.energy = EnergySpec(**base)
    # C-35: the NL path could not declare a VESSEL — "solar catamaran for
    # the Danube" evaluated as a monohull, silently. VesselConfig validates
    # its own JSON (string topology/manning coerced to enums, separation
    # refused when unspecified for a multihull), so the decode is a
    # whitelist plus its refusal turned into a recorded note: the LLM
    # proposing an invalid vessel degrades to the rule floor's monohull
    # WITH the reason on the record, and never crashes the floor path.
    v_raw = raw.get("vessel")
    if isinstance(v_raw, dict):
        v_kw = {k: v_raw[k] for k in
                ("topology", "manning", "separation_over_lwl") if k in v_raw}
        if v_kw:
            try:
                m.vessel = VesselConfig(**v_kw)
            except (ValueError, TypeError) as e:
                # THE DEGRADE IS PERFORMED, NOT ASSUMED. This branch used to
                # append the note "monohull floor kept" and set nothing,
                # relying on `parse_mission` never having inferred a
                # multihull from the prose. MEASURED 2026-09-01, the moment
                # that stopped being true: once the text path learned to read
                # "catamaran" (with a sourced, disclosed spacing assumption),
                # the brief "a solar catamaran" plus an LLM object of
                # `{"topology": "catamaran"}` -- NO separation, which
                # `VesselConfig` refuses by name -- produced a CATAMARAN
                # carrying the note "monohull floor kept". The note was the
                # only monohull in the result.
                #
                # A REFUSED EXPLICIT DECLARATION IS A STRONGER SIGNAL THAN A
                # PROSE INFERENCE, and it degrades to the conservative
                # topology on purpose: the model tried to state a vessel, the
                # statement was invalid, and the floor for an invalid vessel
                # is the one hull form the ladder can always evaluate.
                # Manning is carried across because it was not what failed.
                notes.append(f"LLM vessel rejected ({e}); monohull floor kept")
                if m.vessel.topology is not Topology.MONOHULL:
                    notes.append(
                        f"the text-inferred "
                        f"{m.vessel.topology.value} was DISCARDED with it — a "
                        f"refused declaration degrades to the floor, it does "
                        f"not fall back on prose")
                    m.vessel = VesselConfig(topology=Topology.MONOHULL,
                                            manning=m.vessel.manning,
                                            separation_over_lwl=0.0)
    # Every field above was written with `setattr`, which bypasses
    # `__post_init__`. This is the structural exit gate: no spec leaves this
    # function un-clamped, whatever a future branch above forgets to bound.
    # On today's code it is a no-op, and that is the point — it is a guarantee,
    # not a second clamp.
    notes.extend(m.clamp())
    m.notes = "; ".join(n for n in notes if n)
    return m


def translate(text: str, llm: Callable[[str], str] | None = None) -> MissionSpec:
    """NL -> MissionSpec. llm is an optional provider callable(prompt)->text.
    Any misbehaviour (bad JSON, junk keys, absurd values) degrades safely to
    the deterministic rule-based floor — never an exception, never geometry."""
    floor = parse_mission(text)
    if llm is None:
        return floor
    # THE SAME `except Exception` COLLAPSE AS `grade()` (gap E15), one layer up.
    # An LLM that returns prose, an LLM that raises ConnectionError and a
    # sanitize() with a bug in it all produced a silent, identical fallback —
    # so a translator that had been broken for a week looked exactly like a
    # user typing a mission the model declined to parse. The fallback is still
    # the right BEHAVIOUR (never an exception, never geometry: this is the
    # AI/deterministic boundary), but it now says which of the three happened,
    # in the notes field that is already persisted and served.
    def _fallback(reason: str) -> MissionSpec:
        floor.notes = "; ".join(n for n in (floor.notes, reason) if n)
        return floor

    try:
        text_out = llm(TRANSLATOR_PROMPT + text)
    except Exception as e:                          # noqa: BLE001 — reported
        return _fallback(f"checker error: LLM call raised "
                         f"{type(e).__name__}: {e}; rule-based floor kept")
    try:
        raw = json.loads(text_out)
    except Exception as e:                          # noqa: BLE001 — reported
        return _fallback(f"LLM returned unparseable JSON "
                         f"({type(e).__name__}); rule-based floor kept")
    if not isinstance(raw, dict):
        return _fallback(f"LLM returned a {type(raw).__name__}, not an "
                         f"object; rule-based floor kept")
    try:
        return sanitize(raw, floor)
    except Exception as e:                          # noqa: BLE001 — reported
        # This branch is OURS, not the model's. It means the sanitiser itself
        # is broken, which is a defect to fix and not a mission to translate.
        return _fallback(f"checker error: sanitize() raised "
                         f"{type(e).__name__}: {e}; rule-based floor kept")


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
            "gm-floor", f"category {m.design_category} floor "
                       f"{gm_floor(m.design_category):.2f} m (ISO 12217)",
            lambda ev: ev.gm_m is not None and ev.gm_m >= gm_floor(m.design_category),
            lambda ev: f"GM {ev.gm_m:.2f} m" if ev.gm_m is not None else "no GM"),
        # The floor is IMPORTED, not retyped. This file already imported
        # `gm_floor` correctly while keeping a private literal 0.25 for
        # freeboard — the same drift that limits.py exists to prevent, caught
        # one constant short.
        Requirement(
            "freeboard-floor", f"L1 floor {FREEBOARD_FLOOR_M:.2f} m at load",
            lambda ev: ev.hydro is not None
                       and ev.hydro.freeboard_min >= FREEBOARD_FLOOR_M,
            lambda ev: f"freeboard {ev.hydro.freeboard_min:.2f} m"
                       if ev.hydro else "n/a"),
        # TWO-SIDED, because the one-sided form COULD NOT FAIL. evaluate()
        # floats the hull to max(budget, target), so "disp >= 0.98*target" was
        # true by construction. MEASURED: median delivered displacement was
        # 2.12x the mission target, and a 400 kg dinghy brief was delivered at
        # 2387 kg — +497% — printing "5/5 requirements pass".
        Requirement(
            "carries-target", "mission displacement target, +/-10%",
            lambda ev: ev.hydro is not None
                       and 0.98 * m.displacement_target_kg
                       <= ev.hydro.disp_kg <= 1.10 * m.displacement_target_kg,
            lambda ev: (f"displaces {ev.hydro.disp_kg:.0f} kg "
                        f"({ev.hydro.disp_kg / m.displacement_target_kg:.2f}x "
                        f"target)") if ev.hydro else "n/a"),
        # The length the user ASKED for is a requirement, not a hint. It was
        # parsed, clamped, prompted for and read by nothing: "10 m" delivered
        # 18.58 m and still reported 5/5.
        Requirement(
            "length-hint", "stated LWL +/-10%",
            lambda ev: (m.lwl_hint_m is None or ev.hydro is None
                        or abs(ev.hull_lwl_m - m.lwl_hint_m)
                        <= 0.10 * m.lwl_hint_m),
            lambda ev: ("no length stated" if m.lwl_hint_m is None else
                        f"LWL {ev.hull_lwl_m:.2f} m vs {m.lwl_hint_m:.2f} m "
                        f"asked ({ev.hull_lwl_m / m.lwl_hint_m:.2f}x)")),
    ]
    if m.energy.battery_kwh > 0:
        reqs.append(Requirement(
            "solar-positive-day", "mission: net energy >= 0 at cruise plan",
            lambda ev: ev.energy is not None and ev.energy.net_kwh_day >= 0,
            lambda ev: f"net {ev.energy.net_kwh_day:+.1f} kWh/day"
                       if ev.energy else "n/a"))

    # ---- Tier E: the reference data gets a consumer that can say NO --------
    # `navalai/refdata/ergonomics.py` held ~40 sourced constants that NOTHING
    # read. Gate V2.0's bar is provenance, so the audit was right to keep them,
    # but a constant no code divides by has never been wrong about anything.
    # This is the first bar the boat can fail on the people it carries: the
    # crew must fit on the working deck the hull actually has.
    #
    # It is a NECESSARY condition only, and `rules.ergonomics` says so in its
    # own note — the whole deck plan is counted with no cabin or console taken
    # out. A pass is not "the crew fit"; a fail is "they do not".
    #
    # WHAT THIS ROW CANNOT DO YET, MEASURED 2026-08-07, so it is not re-derived:
    #
    #   (1) The count is `m.crew` AFTER `MissionSpec.clamp()`, and
    #       `mission.FIELD_RANGES["crew"]` is (1, 12). A brief asking for 40
    #       persons arrives here as 12 and this row grades the 12-person boat —
    #       the same substitution `length-hint` and `carries-target` exist to
    #       catch, except that the asked-for number is not recoverable: the
    #       spec keeps it only as the prose note "crew 40 outside [1, 12];
    #       clamped to 12". Deciding a verdict by regexing that sentence would
    #       make the row FAIL OPEN the day the wording changes, so the fix
    #       belongs in the contract (record what was asked, or widen the range
    #       for the 20 m+ craft `rules/estrin.py` now assesses), not here.
    #   (2) Even unclamped, 40 persons PASS on a mid grammar hull and that is
    #       the correct answer for a necessary condition: working deck 27.86 m2
    #       (LWL 10.0 m, nothing excluded — the deck's steepest panel is 6.9 deg
    #       against ISO's 25 deg scope bound), against 40 x 0.30 = 12.00 m2.
    #       This row first fails at 93 persons there, or at 40 persons on a hull
    #       of about 4.3 m. Making it fail sooner needs a deck model that takes
    #       out the console, cabin and Z1 boundary — BuildPlan 2 V2.1-V2.3,
    #       unbuilt — not a smaller number invented here.
    reqs.append(Requirement(
        "crew-fits-on-deck",
        f"ISO 15085 working deck vs {m.crew} persons "
        f"(rules.ergonomics.E-DECK; assessment aid, not certification)",
        lambda ev: _ergonomics_finding(ev, m.crew).passed,
        lambda ev: _ergonomics_finding(ev, m.crew).note))

    # ---- P2-A (2026-08-27): the parsed-and-dropped fields become rows ------
    # "a 16 m x 4 m houseboat, 8 berths, air draft 3.5 m" used to grade 5/5
    # with the beam, the berths and the bridge never consulted — the same
    # substitution defect `length-hint` was added for, three fields over.
    # Each row is graded ONLY when the brief states the field (an unstated
    # hint is not a requirement), and each is a NECESSARY condition with its
    # limitation named in the clause, per the E-DECK precedent above.
    if m.bwl_hint_m is not None:
        reqs.append(Requirement(
            "beam-hint", "stated BWL +/-10%",
            lambda ev: (abs(_declared_bwl_m(ev) - m.bwl_hint_m)
                        <= 0.10 * m.bwl_hint_m),
            lambda ev: f"BWL {_declared_bwl_m(ev):.2f} m vs "
                       f"{m.bwl_hint_m:.2f} m asked "
                       f"({_declared_bwl_m(ev) / m.bwl_hint_m:.2f}x)"))
    if m.berths:
        reqs.append(Requirement(
            "berths-fit",
            f"{m.berths} berths x minimum berth footprint vs working deck "
            f"(refdata.ergonomics; NECESSARY only — no cabin layout exists)",
            lambda ev: _berths_area_m2(m.berths) <= _working_deck_m2(ev),
            lambda ev: f"{m.berths} berths need "
                       f"{_berths_area_m2(m.berths):.1f} m2 vs "
                       f"{_working_deck_m2(ev):.1f} m2 working deck"))
    if m.air_draft_max_m is not None:
        reqs.append(Requirement(
            "air-draft",
            f"bare-hull height above WL vs {m.air_draft_max_m:.2f} m bridge "
            f"clearance (NECESSARY only — superstructure is not modelled)",
            lambda ev: _hull_air_draft_m(ev) <= m.air_draft_max_m,
            lambda ev: f"hull alone reaches {_hull_air_draft_m(ev):.2f} m "
                       f"above WL vs {m.air_draft_max_m:.2f} m limit"))
    return reqs


def _declared_bwl_m(ev: Evaluation) -> float:
    """BWL as the grammar declares it, from the genome the ladder floated.

    Raises on a missing genome — `grade()` types that as a BROKEN checker,
    never a passing one (gap E15), matching `_ergonomics_finding`.
    """
    from . import grammar
    if ev is None or ev.params is None:
        raise ValueError("no genome on the evaluation — the beam requirement "
                         "cannot be measured")
    import numpy as _np
    return float(_np.asarray(ev.params, float)[grammar.NAMES.index("BWL")])


def _berths_area_m2(berths: int) -> float:
    """Minimum plan area of N single berths, from the sourced refdata.

    The absolute-floor berth (1980 mm) at its tapered mean width
    ((560 + 380)/2 mm) — the smallest rectangle-equivalent a berth can
    occupy, so the row it feeds is a necessary condition by construction.
    """
    from .refdata.ergonomics import (BERTH_LENGTH_MIN_MM, BERTH_WIDTH_FOOT_MM,
                                     BERTH_WIDTH_HEAD_MM)
    per = (BERTH_LENGTH_MIN_MM.value / 1e3) * (
        (BERTH_WIDTH_HEAD_MM.value + BERTH_WIDTH_FOOT_MM.value) / 2e3)
    return berths * per


def _working_deck_m2(ev: Evaluation) -> float:
    """ISO-countable working deck area for the evaluated genome (E-DECK)."""
    from .geometry import Hull                # local: geometry <-> translate
    from .rules.ergonomics import working_deck_area_m2
    if ev is None or ev.params is None:
        raise ValueError("no genome on the evaluation — the berths "
                         "requirement cannot be measured")
    counting, _ = working_deck_area_m2(Hull(ev.params))
    return counting


def _hull_air_draft_m(ev: Evaluation) -> float:
    """Height of the bare hull's highest point above the floated waterline.

    The sheer peaks at the bow at D*(1 + sheer_rise) above the keel
    (grammar: sheer_rise is "bow sheer rise / D"); subtracting the solved
    draft gives the hull-only air draft. No superstructure is modelled, so
    the row consuming this can only ever REFUSE a hull that is too tall by
    itself — it cannot clear one.
    """
    from . import grammar
    import numpy as _np
    if ev is None or ev.params is None or ev.hydro is None:
        raise ValueError("no genome/hydrostatics on the evaluation — the "
                         "air-draft requirement cannot be measured")
    x = _np.asarray(ev.params, float)
    d = float(x[grammar.NAMES.index("D")])
    sheer = float(x[grammar.NAMES.index("sheer_rise")])
    return d * (1.0 + sheer) - float(ev.hydro.draft)


def _ergonomics_finding(ev: Evaluation, crew: int):
    """The single E-DECK finding for an evaluation, or a refusal.

    The hull is rebuilt from `ev.params`, the genome the evaluation was
    produced from, so this reads the SAME shape the ladder floated rather than
    a second hull assembled from rounded principal dimensions.

    A missing genome RAISES rather than returning a pass. `grade()` turns that
    into `state: "broken"` and refuses the whole report (gap E15), which is the
    correct outcome: a requirement that cannot be measured is not a
    requirement that is met.
    """
    from .geometry import Hull                # local: geometry <-> translate
    from .rules.ergonomics import assess as ergonomics_rules
    if ev is None or ev.params is None:
        raise ValueError("no genome on the evaluation — the working-deck "
                         "requirement cannot be measured, and an unmeasurable "
                         "requirement is not a passing one")
    return ergonomics_rules(Hull(ev.params), crew)[0]


def grade(ev: Evaluation, reqs: list[Requirement]) -> dict:
    """Typed pass/fail report — the contract the agentic loop is graded on.

    A BROKEN CHECKER AND A FAILED DESIGN USED TO BE THE SAME ROW (gap E15).
    `except Exception: ok = False` cannot tell "this hull's GM is below the
    category floor" from "the GM checker raised AttributeError because
    `Evaluation` lost a field" — both printed `"pass": false` with a plausible
    detail string beside them, and the second one is a broken TOOL reported as
    a broken BOAT. On a rename it would report every design as failing and
    the loop would optimise against a lie.

    Now the two are separate facts. A raising checker is `state: "broken"`
    with the exception typed into `error`, it still counts as NOT passing (an
    unmeasurable requirement is fatal, never a passing default — PLM §3), and
    the report carries `checkers_ok: False` plus a `broken` list so a caller
    can refuse the whole grade rather than read a score off it.

    `detail()` is inside the guard too. It was OUTSIDE, so a detail lambda that
    raised took down `grade()` entirely with a traceback from a formatting
    call — the one part of this function nobody would think to suspect.
    """
    rows = []
    broken: list[str] = []
    for r in reqs:
        row: dict = {"name": r.name, "clause": r.clause, "pass": False,
                     "state": "checked"}
        try:
            row["pass"] = bool(r.check(ev))
        except Exception as e:                      # noqa: BLE001 — reported
            row["state"] = "broken"
            row["error"] = f"checker error: {type(e).__name__}: {e}"
            broken.append(r.name)
        try:
            row["detail"] = r.detail(ev) if ev else "n/a"
        except Exception as e:                      # noqa: BLE001 — reported
            row["detail"] = f"checker error in detail(): {type(e).__name__}: {e}"
            if r.name not in broken:
                row["state"] = "broken"
                row["pass"] = False
                broken.append(r.name)
        rows.append(row)
    return {"pass": all(r["pass"] for r in rows) and not broken,
            "passed": sum(r["pass"] for r in rows), "total": len(rows),
            # A grade with a broken checker in it is not a grade. Callers that
            # read `pass` alone still get False; callers that want to know WHY
            # get the names without parsing prose.
            "checkers_ok": not broken, "broken": broken,
            "requirements": rows}
