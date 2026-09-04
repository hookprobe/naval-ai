"""Gate test for the 16 m x 4 m inland liveaboard probe.

MOTIVATING INCIDENT (2026-08-23, docs/research/HOUSEBOAT-16M.md). A prose brief
-- 16 x 4 x 3 m, 3 t, 100 kWh, 15 kW, 7-12 kn, full liveaboard -- was put
through the whole product for the first time at a size and a hull form no SKU
had exercised. Four numbers in it are refused by the physics and three product
defects were found on the way. This file pins the ones that are cheap to check
so they cannot regress silently.

It does NOT re-derive the design; `scripts/houseboat_16m.py` owns that. It pins
the REFUSALS, because a refusal that quietly becomes an acceptance is the
failure mode this repository keeps finding in its own history.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from navalai import grammar
from navalai.evaluate import evaluate
from navalai.geometry import Hull
from navalai.mission import Manning, parse_mission
from navalai.translate import parse_mission as _pm  # same symbol; import parity

import houseboat_16m as HB


def test_the_briefs_three_tonnes_is_refused_loudly():
    """3 t on a 16 x 4 m hull is refused — and the refusal NAMES the family.

    HISTORY OF THIS PIN, because the refusal has changed shape twice and
    each change was a measurement: (1) an early probe called it
    geometrically unreachable, which was true of a hull with l_pmb 0.30 and
    not of the brief; (2) the held test then pinned "BUILDS at 0.217 m,
    refused by the B/T band"; (3) RE-MEASURED 2026-08-26 when this landed:
    the barge genome the probe now draws (Cp 0.92, r_transom 0.92 — the
    widened envelope this file waited for) displaces MORE at every draft,
    so 3000 kg falls BELOW the lightest buildable member and
    `design_draft_for` refuses with `Unreachable`, naming the family and
    the floor. A stronger refusal than a violated band, and still loud.
    """
    with pytest.raises(HB.Unreachable, match="16.0 x 4.0 m family"):
        HB.design_draft_for(HB.AS_ASKED_KG)


def test_the_corrected_design_passes_the_whole_ladder():
    """14 t on the same envelope: L0, L1 and every constraint row."""
    T, disp = HB.design_draft_for(HB.CORRECTED_KG)
    assert abs(disp - HB.CORRECTED_KG) < 50.0
    assert HB.BWL_M / T <= grammar.B_OVER_T_BAND[1]

    x = grammar.vector(HB.base_genome(T))
    assert grammar.check(x).ok
    ev = evaluate(x, HB.make_mission(HB.CORRECTED_KG, "16 m liveaboard"),
                  rho=HB.RHO_FRESH)
    assert ev.ok, ev.violations
    assert ev.tier == "L1"
    for name, val in ev.g.items():
        assert val is not None and val <= 0.0, f"{name} = {val}"


def test_twelve_knots_is_outside_the_resistance_model():
    """The brief's upper speed is past FN_MICHELL_MAX, and is REPORTED as such.

    The bar is not that 12 kn is slow to reach -- it is that the L1 model does
    not stand behind the number, and a consumer must see `valid=False` rather
    than a confident figure.
    """
    T, _ = HB.design_draft_for(HB.CORRECTED_KG)
    x = grammar.vector(HB.base_genome(T))
    hull = Hull(x)
    mission = HB.make_mission(HB.CORRECTED_KG, "speed probe")
    ev = evaluate(x, mission, rho=HB.RHO_FRESH)

    slow = HB.power_at(hull, ev, mission.energy, HB.CRUISE_KN)
    fast = HB.power_at(hull, ev, mission.energy, HB.DASH_KN)
    assert slow["model_valid"], "7 kn should be inside the model"
    assert not fast["model_valid"], "12 kn should be refused by the model"
    assert slow["within_15kw"], (
        f"7 kn needs {slow['electrical_kw']:.1f} kW against the 15 kW installed")
    assert not fast["within_15kw"]


def test_the_installed_fifteen_kilowatts_reaches_the_cruise_speed():
    """MEASURED 7.78 kn on 15 kW. The bar is the brief's 7 kn, with margin."""
    T, _ = HB.design_draft_for(HB.CORRECTED_KG)
    x = grammar.vector(HB.base_genome(T))
    mission = HB.make_mission(HB.CORRECTED_KG, "power probe")
    ev = evaluate(x, mission, rho=HB.RHO_FRESH)
    v = HB.max_speed_on(Hull(x), ev, mission.energy, HB.MOTOR_KW)
    assert v >= HB.CRUISE_KN, f"only {v:.2f} kn on {HB.MOTOR_KW} kW"


def test_the_accommodation_passes_the_l0a_arrangement_gate():
    """Living room, kitchen, bathroom, cabin and terrace, checked by L0-A."""
    from navalai.arrangement import Function, check_l0a

    T, _ = HB.design_draft_for(HB.CORRECTED_KG)
    x = grammar.vector(HB.base_genome(T))
    ev = evaluate(x, HB.make_mission(HB.CORRECTED_KG, "layout probe"),
                  rho=HB.RHO_FRESH)
    arr, _trunk = HB.houseboat_layout(Hull(x), ev)
    rep = check_l0a(arr)
    assert rep.ok, [str(m) for m in rep.messages]

    got = {s.function for s in arr.spaces}
    for need in (Function.SALOON, Function.GALLEY, Function.HEAD,
                 Function.BERTH):
        assert need in got, f"the brief asked for {need.value}"


# ---------------------------------------------------------------------------
# The two product defects the probe found in the mission front end. These are
# EXPECTED-FAILURE pins: they assert the CURRENT broken behaviour so that the
# fix trips them and they get deleted, rather than sitting undetected.
# See docs/research/HOUSEBOAT-16M.md sections 5 and 6.
# ---------------------------------------------------------------------------

def test_prose_saying_river_still_fails_to_trigger_the_estrin_wire():
    """DEFECT (HOUSEBOAT-16M section 5). Delete this test when it is fixed.

    `evaluate` consults ES-TRIN on the tokens river|canal|lake|inland in
    `mission.waters`, but `parse_mission` writes the design CATEGORY LETTER
    there. So a brief that says "river" produces waters="D" and the inland
    rules do NOT run, while the DEFAULT "river+coastal" does run them.
    """
    m = parse_mission("16 m liveaboard houseboat, inland river and canal "
                      "cruising, 4 crew")
    fires = any(t in str(m.waters).lower()
                for t in ("river", "canal", "lake", "inland"))
    assert not fires, (
        "parse_mission now preserves the waters tokens -- the ES-TRIN wire is "
        "reachable from prose. FIX CONFIRMED: delete this test and "
        "HOUSEBOAT-16M section 5.")


def test_manning_is_still_not_parsed_from_prose():
    """DEFECT (HOUSEBOAT-16M section 6). Delete this test when it is fixed."""
    assert parse_mission("16 m liveaboard houseboat").vessel.manning \
        is Manning.CREWED, (
        "manning is now parsed. FIX CONFIRMED: delete this test and "
        "HOUSEBOAT-16M section 6.")
    assert parse_mission("uncrewed survey boat 8 m").vessel.manning \
        is Manning.CREWED


def test_the_motor_power_defect_is_fixed_the_way_the_sentinel_demanded():
    """The sentinel that stood here ("EnergySpec still has no motor power
    field — delete this test when fixed") FIRED on landing day: commit
    b01ce4e gave `EnergySpec.motor_kw` a default and made `motor_power` a
    permanent constraint row. Per the sentinel's own instruction it is
    deleted; this replaces it with the positive assertion, so the fix
    cannot silently un-land."""
    from navalai.energy import EnergySpec
    from navalai.evaluate import CONSTRAINT_NAMES

    assert "motor_kw" in EnergySpec.__dataclass_fields__
    assert "motor_power" in CONSTRAINT_NAMES


def test_a_houseboat_mission_search_delivers_a_BARGE_not_a_cruiser():
    """The flagship-class finding of the 2026-09-03 overnight audit, closed.

    MEASURED before the fix: the entire 48-member pareto front for
    "16 m x 4.5 m liveaboard houseboat" carried beam_carried <= 0.341
    (energy-best member 0.220) — handsome displacement CRUISERS wearing a
    houseboat's label, because the barge family bands were one-sided
    PERMISSIONS (they stopped the general bars refusing a true barge) and
    all three objectives punish barge-form, so the proven liveaboard-barge
    parent was seeded and then dominated out. "Mathematically valid but
    nautically nonsensical", the exact failure mode the product exists to
    prevent, in its flagship class.

    The fix is ONE requiring band: barge missions demand
    beam_carried >= 0.50, sourced between the cruiser front's measured
    ceiling (0.341) and the proven parent's measured 0.585 on the current
    kernel. MEASURED after: the front returns 5 members, every one at
    beam_carried >= 0.51, plan-form with beam carried across the midbody.

    This test runs a REDUCED search and asserts the property, not the
    numbers: a non-empty front whose every member clears the barge floor.
    The budget is itself measured: pop 24x12 and 48x12 STARVE (the
    barge-feasible region is thin and the parent neighbourhood needs
    generations to propagate); 36x20 is the smallest measured budget that
    finds it (front of 2 in ~14 s).
    """
    import numpy as np
    from navalai import geometry, morphology, optimize
    from navalai.mission import parse_mission

    m = parse_mission("16 m x 4.5 m recreational liveaboard houseboat, "
                      "5 knots, 6 tonne, category C")
    assert m.hull_family == "barge"
    r = optimize.pareto_front(m, pop=36, gens=20, seed=0)
    X = np.atleast_2d(r.X) if r.X is not None else np.empty((0, 0))
    assert len(X), f"the barge floor emptied the search: {r.why_empty()}"
    for x in X:
        d = morphology.describe(morphology.from_hull(geometry.Hull(x)))
        assert d.beam_carried >= 0.50 - 1e-9, (
            f"a cruiser (beam_carried {d.beam_carried:.3f}) survived a "
            f"barge mission's shape row")
