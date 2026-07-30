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
