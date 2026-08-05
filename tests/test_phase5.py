"""Gate 5: >=90% mission-brief translation on the held-out set; the LLM seam
cannot corrupt the spec or reach geometry; requirement grading works."""

import json

import numpy as np
import pytest

from navalai.evaluate import evaluate
from navalai.mission import MissionSpec
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
