"""Gate PROP — the drive system is a design-stage quantity.

THE INCIDENT, measured 2026-08-25. houseboat19 (11.9 m governed warped hull,
`data/exports/houseboat19/genome.json`) passed all eight physics rows, all
seven design rules, morphology and the compiled policy — and the owner
rejected it on sight: "this looks ok for a paddle boat not for a motor boat".
The eye was right and the pipeline had no row that could agree: stern
immersion 0.33-0.37 m, the 7 kn thrust wanting a 0.42 m disc, transom Froude
1.42-1.99 against ~2.5 for clean ventilation — none of it measured anywhere.
The held houseboat16 study had already recorded the root: "15 kW IS NOT
EXPRESSIBLE — there is no motor-power field anywhere in this codebase."

The owner then made it a product definition, twice: "all boats will have
motors, electric motors and solar panels ... naval-ai only designs boats
with motors." So `motor_power` and `prop_space` are PERMANENT members of
`CONSTRAINT_NAMES` (grown 8 -> 10), not opt-in appendages.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from navalai import grammar, propulsion
from navalai.evaluate import CONSTRAINT_NAMES, evaluate
from navalai.geometry import Hull
from navalai.mission import EnergySpec, MissionSpec

_HB19 = Path(__file__).resolve().parents[1] / "data/exports/houseboat19/genome.json"


def _hb19_vector():
    if not _HB19.exists():
        pytest.skip("houseboat19 genome not on disk (data/exports is a build "
                    "artifact on some clones)")
    return grammar.vector(json.loads(_HB19.read_text()))


def _mission(**energy):
    return MissionSpec(name="prop-gate", lwl_hint_m=11.9,
                       displacement_target_kg=6500.0, cruise_speed_kn=7.0,
                       design_category="C", crew=4, waters="river+coastal",
                       energy=EnergySpec(battery_kwh=100.0, **energy))


def test_the_propulsion_rows_are_permanent_members_of_the_vector():
    """Product definition, not a flag: 10 names, the two new ones LAST so
    every pre-existing row keeps its index (the order fence's contract)."""
    # 10 -> 11 on 2026-08-26: the `shape` row joined the same way these
    # two did (a deliberate product decision recorded in its module —
    # evaluate.CONSTRAINT_NAMES' comment carries the incident).
    assert len(CONSTRAINT_NAMES) == 11
    assert CONSTRAINT_NAMES[:8] == ("freeboard", "gm", "bend_radius", "trim",
                                    "list", "lcb", "proportions", "rules")
    assert CONSTRAINT_NAMES[8:] == ("motor_power", "prop_space", "shape")
    assert propulsion.ROWS == ("motor_power", "prop_space")


def test_every_boat_has_a_motor_by_default():
    """`EnergySpec.motor_kw` defaults to the ORIGINAL BRIEF's 15 kW — never
    None. A None here would resurrect the 'silently dropped' defect the held
    study measured. The default drive is CONVENTIONAL (prop may hang 0.35 m
    below the keel behind a skeg); a shallow mission opts INTO 0.0 and pays
    for its disc with tunnels or props."""
    spec = EnergySpec()
    assert spec.motor_kw == 15.0
    assert spec.n_props == 1
    assert spec.prop_tunnel_recess_m == 0.0
    assert spec.prop_max_below_keel_m == 0.35


def test_houseboat19_shallow_single_prop_is_refused_for_the_reason_the_owner_saw():
    """THE PADDLE BOAT, refused by measurement. houseboat19's product point
    is its 0.55 m draft — hanging a prop 0.35 m below the keel would forfeit
    it, so the SHALLOW mission (prop_max_below_keel_m = 0) is this hull's
    honest configuration. There, one un-tunnelled prop at 7 kn needs a
    0.42 m disc against ~0.26 m of room -> prop_space VIOLATED, and the
    message names every design lever."""
    ev = evaluate(_hb19_vector(), _mission(prop_max_below_keel_m=0.0))
    assert ev.g["prop_space"] > 0.0, (
        "houseboat19 shallow with a single un-tunnelled prop must violate "
        "prop_space — this is the measured incident the row exists for")
    assert not ev.ok
    msg = " ".join(ev.violations)
    assert "disc" in msg and "tunnel" in msg
    # the motor itself is fine — 7.2 kW demand inside 80% of 15 kW — so the
    # row that fires is the SPACE row, not the power row: the diagnosis is
    # geometric, exactly as the owner's eye said.
    assert ev.g["motor_power"] < 0.0


def test_a_conventional_shaft_drive_passes_where_shallow_is_refused():
    """The below-keel hang is the lever that separates the two verdicts on
    the SAME hull: allow the ordinary 0.35 m and houseboat19's single prop
    fits. The row distinguishes configurations, not hulls — which is what
    makes it a design constraint rather than a shape opinion."""
    ev = evaluate(_hb19_vector(), _mission())      # default: hang allowed
    assert ev.g["prop_space"] < 0.0, (
        f"a conventional shaft drive must fit: g={ev.g['prop_space']:+.3f}")


def test_the_assessments_twin_tunnel_fix_passes():
    """The arrangement drawn in motor_integration.png, machine-verified:
    two props + 0.16 m tunnels at the governed 5 kn -> both rows satisfied."""
    ms = MissionSpec(name="prop-gate", lwl_hint_m=11.9,
                     displacement_target_kg=6500.0, cruise_speed_kn=5.0,
                     design_category="C", crew=4, waters="river+coastal",
                     energy=EnergySpec(battery_kwh=100.0, n_props=2,
                                       prop_tunnel_recess_m=0.16,
                                       prop_max_below_keel_m=0.0))
    ev = evaluate(_hb19_vector(), ms)
    assert ev.g["motor_power"] < 0.0 and ev.g["prop_space"] < 0.0
    assert ev.ok, f"violations: {ev.violations}"


def test_a_toy_motor_is_refused_by_the_power_row():
    """The row must be able to fail on its own axis: 1 kW cannot push 6.5 t
    at 7 kn (demand ~7 kW), whatever the prop geometry says."""
    ev = evaluate(_hb19_vector(), _mission(motor_kw=1.0))
    assert ev.g["motor_power"] > 0.0
    assert any("continuous rating" in v for v in ev.violations)


def test_transom_froude_matches_the_hand_measurement():
    """The report reproduces the numbers the assessment derived by hand
    (1.99 at 7 kn on 0.33 m immersion) from the hull's own geometry —
    within the tolerance of reading the keel at slightly different
    stations. Fn_T of a DRY transom is +inf: clean by definition."""
    v = _hb19_vector()
    hull = Hull(v)
    ev = evaluate(v, _mission())
    imm = propulsion.transom_immersion_m(hull, ev.wl)
    fn = propulsion.transom_froude(7.0 * 0.5144, imm)
    assert 0.25 <= imm <= 0.45, f"immersion {imm:.3f}"
    assert 1.6 <= fn <= 2.4, f"Fn_T {fn:.2f} (hand measurement: 1.99)"
    assert propulsion.transom_froude(3.6, 0.0) == float("inf")
    assert fn < propulsion.TRANSOM_FN_CLEAN  # the paddle-boat stern, in numbers


def test_the_roll_and_pitch_reports_read_the_floated_geometry():
    """Anti-roll and anti-pitch are REPORT quantities (assessment aid, not
    rows): the bilge-keel span is the submerged chine — measured 1.00 on
    houseboat19, chine wet stem to stern — and the pitch report carries the
    entry angle and the axe forefoot drop."""
    v = _hb19_vector()
    hull = Hull(v)
    ev = evaluate(v, _mission())
    span = propulsion.wetted_chine_span_frac(hull, ev.wl)
    assert 0.9 <= span <= 1.0, f"hb19's chine is wet full-length; got {span}"
    assert span >= propulsion.BILGE_KEEL_MIN_SPAN_FRAC
    ae, drop = propulsion.pitch_entry_report(hull, ev.wl)
    assert 5.0 <= ae <= 45.0
    assert drop > 0.0, ("houseboat19 carries stem_depth 0.21 — the forefoot "
                        "is deeper than midships (the axe mechanism)")


def test_disc_sizing_is_monotone_in_its_levers():
    """More props -> smaller disc each; a tunnel -> more room; both monotone,
    so NSGA-II gets a slope, not a cliff."""
    d1 = propulsion.min_prop_diameter_m(1100.0, 1)
    d2 = propulsion.min_prop_diameter_m(1100.0, 2)
    assert d2 < d1
    assert propulsion.max_prop_diameter_m(0.33, 0.16) > \
        propulsion.max_prop_diameter_m(0.33, 0.0)


# ===========================================================================
# P6 (2026-08-27) — THE DRIVE ARCHITECTURE. Before it, the rows judged every
# hull as a conventional shaft drive: an outboard was CREDITED with a tunnel
# recess it cannot have, and a protected tunnel drive was credited with a
# below-keel hang it exists to avoid — the naval-ai-concept's central
# protected prop puts NOTHING below the keel line, and the row measured a
# stern that does not exist (audit H chain).
# ===========================================================================

from tests.test_phase0 import mid_params  # noqa: E402


def test_the_shaft_default_reproduces_the_pre_p6_rows_bit_identically():
    """The compatibility clause: DRIVE_LAWS['shaft'] is station 0.12 with
    both levers live, so every recorded evaluation stands."""
    law = propulsion.DRIVE_LAWS[propulsion.DriveArchitecture.SHAFT]
    assert law.station_frac == propulsion.PROP_STATION_FRAC
    assert law.allows_recess and law.allows_below_keel
    assert EnergySpec().drive == "shaft"
    x = np.array(mid_params())
    from navalai.geometry import Hull
    hull = Hull(x)
    g_new, _ = propulsion.rows_for(hull, 0.0, 3000.0, 9000.0, EnergySpec())
    # hand-build the pre-P6 computation from the same primitives
    imm = propulsion.prop_immersion_m(hull, 0.0)
    d_min = propulsion.min_prop_diameter_m(3000.0, 1)
    d_max = propulsion.max_prop_diameter_m(imm, 0.0, 0.35)
    assert g_new["prop_space"] == pytest.approx(d_min / d_max - 1.0, rel=1e-12)


def test_an_outboard_gets_no_credit_for_a_tunnel_it_cannot_have():
    x = np.array(mid_params())
    from navalai.geometry import Hull
    hull = Hull(x)
    with_recess = EnergySpec(drive="outboard", prop_tunnel_recess_m=0.5)
    without = EnergySpec(drive="outboard", prop_tunnel_recess_m=0.0)
    g1, _ = propulsion.rows_for(hull, 0.0, 3000.0, 9000.0, with_recess)
    g0, _ = propulsion.rows_for(hull, 0.0, 3000.0, 9000.0, without)
    assert g1["prop_space"] == pytest.approx(g0["prop_space"]), (
        "a declared tunnel recess bought an outboard disc diameter — the "
        "drive law is not being applied")


def test_a_protected_tunnel_drive_puts_nothing_below_the_keel():
    """The naval-ai-concept configuration: the recess is the ONLY lever."""
    x = np.array(mid_params())
    from navalai.geometry import Hull
    hull = Hull(x)
    spec = EnergySpec(drive="tunnel", prop_max_below_keel_m=0.35,
                      prop_tunnel_recess_m=0.0)
    g, why = propulsion.rows_for(hull, 0.0, 3000.0, 9000.0, spec)
    imm = propulsion.prop_immersion_m(hull, 0.0)
    d_max_no_hang = propulsion.max_prop_diameter_m(imm, 0.0, 0.0)
    d_min = propulsion.min_prop_diameter_m(3000.0, 1)
    assert g["prop_space"] == pytest.approx(
        (d_min / d_max_no_hang - 1.0) if d_max_no_hang > 1e-9
        else float("inf"))
    # and when the row fires, the message names the drive and ONLY the
    # levers this drive actually has
    if g["prop_space"] > 0:
        assert "tunnel stern" in why["prop_space"]
        assert "hang below the keel" not in why["prop_space"]


def test_an_unknown_drive_is_refused_by_name_never_defaulted():
    with pytest.raises(ValueError, match="waterjet"):
        propulsion.drive_law(EnergySpec(drive="waterjet"))


def test_the_usable_column_fraction_is_derived_from_the_named_margins():
    """The 0.70 was a single opaque number with the 15% tip clearance
    folded in silently; now both margins are named and the fraction is
    DERIVED — a change to either moves it, retyping it is impossible."""
    assert propulsion.PROP_IMMERSION_FRACTION == pytest.approx(
        1.0 - propulsion.TIP_CLEARANCE_FRACTION
        - propulsion.GROUNDING_MARGIN_FRACTION)
    assert propulsion.PROP_IMMERSION_FRACTION == pytest.approx(0.70)


def test_the_brief_names_the_drive_and_the_spec_receives_it():
    from navalai.mission import parse_mission
    cases = {
        "6 m dinghy with an outboard, 8 knots": "outboard",
        "12 m saildrive cruiser at 6 knots": "pod",
        "16 m houseboat with a protected prop, 5 knots": "tunnel",
        "10 m solar boat at 5 knots": "shaft",
    }
    for brief, drive in cases.items():
        assert parse_mission(brief).energy.drive == drive, brief


def test_the_report_carries_the_drive_and_the_as_applied_levers():
    """`assess` must report the recess AS APPLIED (zeroed for a drive with
    no tunnel), not as declared — a report that echoes the request is the
    layer-table lie all over again."""
    m = _mission(n_props=1, drive="outboard", prop_tunnel_recess_m=0.5)
    x = np.array(mid_params())
    ev = evaluate(x, m)
    from navalai.geometry import Hull
    rep = propulsion.assess(Hull(x), ev, m.energy)
    assert rep.drive == "outboard"
    assert rep.tunnel_recess_m == 0.0
