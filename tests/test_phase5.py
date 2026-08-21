"""Gate 5: >=90% mission-brief translation on the held-out set; the LLM seam
cannot corrupt the spec or reach geometry; requirement grading works."""

import json

import numpy as np
import pytest

from navalai.evaluate import evaluate
from navalai.mission import MissionSpec, parse_mission
from navalai.translate import (grade, requirements_from_mission, sanitize,
                               translate)
from tests.test_phase0 import mid_params

# (brief, expected-field checks)
BRIEFS = [
    ("6 tonne solar liveaboard, 10 m, Danube river cruising at 5 knots",
     {"displacement_target_kg": 6000, "cruise_speed_kn": 5, "design_category": "D"}),
    ("2 t dayboat, 6.5 m, lake use, 8 knots",
     {"displacement_target_kg": 2000, "cruise_speed_kn": 8, "design_category": "D"}),
    ("12 tonne coastal trawler 15 m at 7 knots",
     {"displacement_target_kg": 12000, "design_category": "C"}),
    ("black sea coastal cruiser, 9 m, 6 knots, 4 crew",
     {"design_category": "C", "crew": 4}),
    ("offshore passagemaker 14 m, 20 tonne, 8 knots",
     {"displacement_target_kg": 20000, "design_category": "B"}),
    ("solar electric canal boat 3 tonnes at 4 knots with 60 kWh battery",
     {"displacement_target_kg": 3000, "design_category": "D"}),
    ("river houseboat 8 tonnes, 11 m, 5 knots",
     {"displacement_target_kg": 8000, "design_category": "D"}),
    ("4t coastal fisher, 8 m, 9 knots, 3 crew",
     {"displacement_target_kg": 4000, "crew": 3, "design_category": "C"}),
    ("ocean crossing 18 m yacht 30 tonne 9 knots",
     {"displacement_target_kg": 30000, "design_category": "A"}),
    ("5 tonne electric river cruiser 12 km/h",
     {"displacement_target_kg": 5000, "design_category": "D"}),
]


def test_translation_set_at_least_90pct():
    field_checks = 0
    field_pass = 0
    for text, expect in BRIEFS:
        m = translate(text)
        for k, v in expect.items():
            field_checks += 1
            got = getattr(m, k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                field_pass += abs(got - v) < 1e-6 or (
                    isinstance(got, float) and got == pytest.approx(v, rel=0.02))
            else:
                field_pass += got == v
    rate = field_pass / field_checks
    assert rate >= 0.90, f"translation rate {rate:.0%} ({field_pass}/{field_checks})"


def test_llm_seam_bad_json_falls_back():
    m = translate("6 tonne boat at 5 knots", llm=lambda p: "I think you want {")
    assert m.displacement_target_kg == pytest.approx(6000)   # rule floor won


def test_llm_seam_junk_keys_and_absurd_values_neutralised():
    evil = json.dumps({
        "displacement_target_kg": 1e12,          # clamped to range max
        "cruise_speed_kn": -50,                  # clamped to range min
        "hull_params": [999] * 15,               # no such field: dropped
        "LWL": 999, "__class__": "pwned",        # dropped
        "design_category": "Z",                  # invalid: ignored
        "energy": {"battery_kwh": 1e9, "panel_eff": 5.0},
    })
    m = translate("6 tonne boat at 5 knots", llm=lambda p: evil)
    assert m.displacement_target_kg <= 200_000.0
    assert m.cruise_speed_kn >= 1.0
    assert m.design_category in "ABCD"
    assert m.energy.battery_kwh <= 500.0
    assert m.energy.panel_eff <= 0.30
    assert not hasattr(m, "hull_params") and not hasattr(m, "LWL")


def test_no_geometry_pathway():
    """Structural guarantee: MissionSpec has no field that reaches the grammar."""
    from navalai import grammar
    spec_fields = set(MissionSpec.__dataclass_fields__)
    assert spec_fields.isdisjoint(set(grammar.NAMES))


def test_llm_seam_good_output_is_used():
    good = json.dumps({"displacement_target_kg": 7500, "crew": 6})
    m = translate("a boat", llm=lambda p: good)
    assert m.displacement_target_kg == pytest.approx(7500)
    assert m.crew == 6


def test_requirement_grading_end_to_end():
    m = MissionSpec(displacement_target_kg=4000)
    ev = evaluate(mid_params(), m)
    report = grade(ev, requirements_from_mission(m))
    assert report["total"] >= 4
    names = {r["name"]: r for r in report["requirements"]}
    assert names["floats-at-budget"]["pass"]
    assert names["gm-floor"]["pass"] == (ev.gm_m >= 0.35)
    # every requirement carries clause provenance
    assert all(r["clause"] for r in report["requirements"])


def test_mission_parser_handles_ordinary_english_units():
    """Gate 5 regression, found by running the end-to-end demo (2026-08-05).

    Two silent parse failures, both of which fell back to a DEFAULT rather than
    erroring — the worst failure mode for a mission translator, because the
    pipeline then optimises confidently for the wrong boat:

      "3 tonnes"  -> 6000 kg (the default).  The alternation was
                     (?:t|tonne|tons?)\\b: `t` fails the word boundary,
                     `tonne` fails on the trailing s, `tons?` fails on the
                     second n. The plural of "tonne" simply never matched.
      "9-metre"   -> lwl_hint_m None.  The separator was \\s*, which cannot
                     span a hyphen, though hyphenated units are ordinary
                     English.
    """
    from navalai.mission import parse_mission

    cases = [
        # (text, displacement_kg, lwl_hint_m, cruise_kn)
        ("6 tonne solar-electric liveaboard, 10 m, cruise 5 knots", 6000, 10.0, 5.0),
        ("12 m dayboat, 3 tonnes, 6 knots", 3000, 12.0, 6.0),      # was 6000
        ("a 9-metre cruiser, 4 t", 4000, 9.0, None),               # was None
        ("7-tonne 11-metre trawler at 8 knots", 7000, 11.0, 8.0),  # both hyphenated
        ("5000 kg launch, 6 m, 7 kn", 5000, 6.0, 7.0),
        ("2 ton tender, 5 meters", 2000, 5.0, None),
    ]
    for text, disp, lwl, kn in cases:
        s = parse_mission(text)
        assert s.displacement_target_kg == disp, (text, s.displacement_target_kg)
        assert s.lwl_hint_m == lwl, (text, s.lwl_hint_m)
        if kn is not None:
            assert s.cruise_speed_kn == kn, (text, s.cruise_speed_kn)


def test_explicit_design_category_is_honoured():
    """Audit 2026-08-05: "category A" parsed to the default C.

    The category was only ever INFERRED from waters keywords, so a mission that
    stated it outright came back one or more categories weaker than asked for —
    and since the GM floor is category-driven (limits.gm_floor), that silently
    relaxed the stability bar the design was held to.
    """
    from navalai.limits import gm_floor
    from navalai.mission import parse_mission

    for cat in ("A", "B", "C", "D"):
        for phrasing in (f"category {cat}", f"design category {cat}",
                         f"a category-{cat} vessel", f"Category {cat}"):
            m = parse_mission(f"a 10 metre boat, 3 tonnes, {phrasing}")
            assert m.design_category == cat, (phrasing, m.design_category)

    # a stated category beats inferred waters, and the conflict is REPORTED
    m = parse_mission("a 10 metre ocean boat, 3 tonnes, category D")
    assert m.design_category == "D"
    assert "waters imply category A" in m.notes
    assert gm_floor("D") != gm_floor("A")


# ---------------------------------------------------------------------------
# E12 — the range table guarded the LLM path only
# ---------------------------------------------------------------------------

def test_prose_and_direct_construction_pass_the_same_range_gate():
    """`_FIELD_RANGES` lived in `translate.py` and clamped the LLM's JSON.
    The SAME fields arriving as prose, or over HTTP as `MissionSpec(**body)`,
    were unbounded.

    MEASURED before the fix:

        parse_mission("6 tonne boat at 0 knots") -> cruise_speed_kn 0.0
          with notes EMPTY, and evaluate() then returned
          range_solar_nm_day = 3.0e12 NM/day at tier L1 with no warning.
          Earth's circumference is ~21,600 NM.
        parse_mission("5000 crew river barge")   -> crew 5000
        MissionSpec(displacement_target_kg=-1.0) -> accepted verbatim

    MEASURED after: speed clamps to 1.0 kn, the range falls to 130.4 NM/day,
    and every clamp is written into `.notes`. The note is the point — 0 knots
    being rejected is worth little if the caller cannot tell that the mission
    it got back is not the mission it asked for.
    """
    from navalai.mission import FIELD_RANGES

    m = parse_mission("6 tonne boat at 0 knots")
    assert m.cruise_speed_kn == FIELD_RANGES["cruise_speed_kn"][0]
    assert "cruise_speed_kn" in m.notes and "clamped" in m.notes
    ev = evaluate(mid_params(), m)
    assert ev.energy.range_solar_nm_day < 21_600, (
        f"solar range {ev.energy.range_solar_nm_day:.3g} NM/day exceeds the "
        f"circumference of the Earth")

    m2 = parse_mission("5000 crew river barge")
    assert m2.crew == FIELD_RANGES["crew"][1] and "crew" in m2.notes

    # the HTTP path: a bare constructor is the same gate
    m3 = MissionSpec(displacement_target_kg=-1.0, cruise_speed_kn=0.0,
                     crew=5000)
    lo_d, _ = FIELD_RANGES["displacement_target_kg"]
    assert m3.displacement_target_kg == lo_d
    assert m3.cruise_speed_kn == FIELD_RANGES["cruise_speed_kn"][0]
    assert m3.crew == FIELD_RANGES["crew"][1]
    assert m3.notes.count("clamped") == 3

    # NaN survives min/max — sanitize() learned that the hard way and the
    # contract must not have to learn it again.
    m4 = MissionSpec(displacement_target_kg=float("nan"))
    assert m4.displacement_target_kg == 6000.0 and "non-finite" in m4.notes
    m5 = MissionSpec(design_category="Z")
    assert m5.design_category == "C" and "design_category" in m5.notes


def test_there_is_one_range_table_not_two():
    """The recurring defect in this codebase is a number declared twice (GM
    0.35 vs 0.45). `translate` now READS `mission.FIELD_RANGES` instead of
    keeping its own copy, so the LLM seam and the prose parser cannot drift.
    """
    import navalai.mission as M
    import navalai.translate as T

    assert T._FIELD_RANGES is M.FIELD_RANGES
    assert T._ENERGY_RANGES is M.ENERGY_RANGES


def test_prose_battery_capacity_is_bounded_too():
    """Found while closing E12. `parse_mission` set `battery_kwh` straight from
    prose with no bound at all — the one writer of that field that the LLM
    range table never covered. MEASURED: "999999 kWh" parsed verbatim, which is
    7,499,993 kg of LiFePO4 in a 6 t mission.

    It is clamped where the untrusted VALUE arrives, not in
    `MissionSpec.__post_init__`: `battery_kwh == 0` is a live sentinel that
    switches off the solar-positive requirement, and clamping it up to the
    1.0 kWh floor would silently add a requirement the caller turned off.
    """
    from navalai.energy import EnergySpec
    from navalai.mission import ENERGY_RANGES

    m = parse_mission("canal boat with 999999 kwh battery")
    assert m.energy.battery_kwh == ENERGY_RANGES["battery_kwh"][1]
    assert "battery" in m.notes and "clamped" in m.notes

    # the sentinel is untouched by the contract's own gate
    zero = MissionSpec(energy=EnergySpec(battery_kwh=0.0))
    assert zero.energy.battery_kwh == 0.0
    assert not any("battery" in n for n in zero.notes.split("; ") if n)
    names = {r.name for r in requirements_from_mission(zero)}
    assert "solar-positive-day" not in names


def test_llm_seam_can_declare_a_vessel_and_a_bad_one_degrades_with_a_note():
    """C-35: the NL path had no vessel decode, so "solar catamaran" from the
    LLM evaluated as a MONOHULL, silently. A valid vessel dict now reaches
    MissionSpec.vessel; an invalid one (multihull with no declared
    separation — VesselConfig's own refusal) degrades to the rule floor's
    monohull WITH the reason recorded in notes, never a crash.
    """
    from navalai.mission import Topology

    good = json.dumps({"vessel": {"topology": "catamaran",
                                  "separation_over_lwl": 0.22}})
    m = translate("a solar catamaran", llm=lambda p: good)
    assert m.vessel.topology is Topology.CATAMARAN
    assert m.vessel.separation_over_lwl == pytest.approx(0.22)

    bad = json.dumps({"vessel": {"topology": "catamaran"}})  # no separation
    m = translate("a solar catamaran", llm=lambda p: bad)
    assert m.vessel.topology is Topology.MONOHULL, (
        "an unspecified multihull must degrade to the floor, not sneak in")
    assert "vessel rejected" in m.notes, (
        f"the degradation left no note: {m.notes!r}")


def test_a_unit_match_that_measures_the_wrong_quantity_is_refused_and_said():
    """MEASURED 2026-08-21 on a brief the product's own UX doc used as its
    worked example:

        "Monohull wave-piercer, 4-6 people, 1-tonne battery payload,
         3 m total height, stitch-and-glue plywood"

    `re.search` takes the FIRST match and the unit regexes carry no notion of
    which dimension the unit measures, so this parsed to a 3-metre boat
    weighing one tonne — `lwl_hint_m = 3.0` from "3 m total height" and
    `displacement_target_kg = 1000.0` from "1-tonne battery payload". Both land
    INSIDE `FIELD_RANGES`, so `clamp()` said nothing and `notes` came back
    EMPTY. It read as a clean parse of a brief that stated neither number.

    Same shape as the thousands-separator defect already recorded in
    `parse_mission`, and worse: that one at least returned digits the user had
    typed. The discriminator is the FOLLOWING NOUN, because the units are
    genuinely right — and it must be, since the cases below lock a mass at
    end-of-string and a battery in kWh that must both keep working.
    """
    m = parse_mission("Monohull wave-piercer, 4-6 people, 1-tonne battery "
                      "payload, 3 m total height, stitch-and-glue plywood")
    assert m.lwl_hint_m is None, "a stated height became the waterline length"
    assert m.displacement_target_kg == 6000.0, (
        "a stated payload became the whole boat's displacement")
    # AND IT IS NOT SILENT. The empty-notes part is the defect, not a detail.
    assert "1-tonne" in m.notes and "3 m" in m.notes, m.notes
    assert "air-draft" in m.notes, (
        "a declared vertical clearance that nothing checks must say so")

    # THE SCAN DOES NOT STOP AT THE FIRST MATCH: a disqualified number before
    # a real one must not cost us the real one.
    m2 = parse_mission("1-tonne battery payload, 6 tonne boat, 9 m")
    assert m2.displacement_target_kg == 6000.0 and m2.lwl_hint_m == 9.0

    # THE LOCKED CASES STILL PARSE — these are why the rule cannot simply ban
    # "a number followed by 'battery'" or "a number near the end".
    assert parse_mission("a 9-metre cruiser, 4 t").displacement_target_kg == 4000
    assert parse_mission("2 ton tender, 5 meters").lwl_hint_m == 5.0
    assert parse_mission(
        "6 tonne solar-electric liveaboard, 10 m, Danube and Black Sea "
        "coastal, cruise 5 knots, 2 crew, 40 kWh battery"
    ).energy.battery_kwh == pytest.approx(40)
