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

from dataclasses import replace

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
    two props at the governed 5 kn -> both rows satisfied.

    THE TITLE SAID "TWIN TUNNEL" AND THE NUMBER SAYS TWIN PROPS. MEASURED
    2026-09-01 when the recess stopped being a free declaration
    (`propulsion.credited_recess_m`): this hull draws NO tunnel, so the
    0.16 m in the spec is credited as 0.000 m and `prop_space` reads
    -0.2920 either way. The two props are the whole fix here, and the test
    now says which lever it is testing — a claim about a tunnel has to be
    made on a hull that has one, which is
    `test_a_drawn_tunnel_is_what_buys_the_single_prop_its_disc`.
    """
    ms = MissionSpec(name="prop-gate", lwl_hint_m=11.9,
                     displacement_target_kg=6500.0, cruise_speed_kn=5.0,
                     design_category="C", crew=4, waters="river+coastal",
                     energy=EnergySpec(battery_kwh=100.0, n_props=2,
                                       prop_tunnel_recess_m=0.16,
                                       prop_max_below_keel_m=0.0))
    ev = evaluate(_hb19_vector(), ms)
    assert ev.g["motor_power"] < 0.0 and ev.g["prop_space"] < 0.0
    assert ev.ok, f"violations: {ev.violations}"
    # and the declared recess is NOT what did it: the same mission with no
    # recess at all returns the identical row, because the hull draws none
    ms0 = replace(ms, energy=replace(ms.energy, prop_tunnel_recess_m=0.0))
    assert evaluate(_hb19_vector(), ms0).g["prop_space"] == pytest.approx(
        ev.g["prop_space"], abs=0.0, rel=0.0), (
        "the declared recess moved a row on a hull that draws no tunnel — "
        "a lever the hull does not have must contribute nothing")


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


# --------------------------------------------------------------------------
# CFD audit P2-15: the wake-deficit layer becomes a FIELD, not a note.
#
# THE MEASUREMENT. hookprobe v1, v2 and v3 at 8 kn — three hulls, one
# campaign — all read the same thing at the prop plane: 0.70-0.84 of boat
# speed at 0.2 m below the static waterline, 99-107% at 0.4 m. It
# REPEATED across all three and survived the v2 fin-TE taper, which makes
# it the strongest measured feature-to-flow link in this tree.
#
# THE DEFECT IT FIXES. Until 2026-08-28 the rule lived inside a DriveLaw
# `note` string, where the ladder could not read it, no report carried
# it, and no test could fail on it. A design rule that only a human can
# apply is not encoded — it is documented, which is a different thing.
# --------------------------------------------------------------------------

def test_the_wake_depth_rule_is_a_number_a_reader_gets_not_a_note():
    from navalai import propulsion as pr

    assert pr.WAKE_CLEAN_DEPTH_M > pr.WAKE_DEFICIT_DEPTH_M
    # The nondimensional form must be the quotient, never a second copy.
    assert pr.WAKE_CLEAN_DEPTH_FRAC_LWL == pytest.approx(
        pr.WAKE_CLEAN_DEPTH_M / pr.WAKE_REFERENCE_LWL_M)
    # ... and it must reproduce the measurement at the measured length.
    assert pr.wake_clean_depth_m(pr.WAKE_REFERENCE_LWL_M) == pytest.approx(
        pr.WAKE_CLEAN_DEPTH_M)


def test_only_the_tunnel_stern_carries_a_wake_verdict():
    """An unmeasured stern gets None — not False, and not a guess."""
    from navalai import propulsion as pr

    anchored = [a for a, law in pr.DRIVE_LAWS.items() if law.wake_anchored]
    assert anchored == [pr.DriveArchitecture.TUNNEL], (
        "the wake deficit was measured on the hookprobe TUNNEL stern and "
        "nowhere else. A transom-hung leg and a pod sit in different "
        "flow; claiming the tunnel's anchor over them is a defect "
        f"measured at a configuration the product never runs: {anchored}")


def test_an_unanchored_stern_returns_none_rather_than_a_verdict():
    from navalai import propulsion as pr
    from navalai.evaluate import sample_valid

    X, _ = sample_valid(1, MissionSpec(), seed=11)
    h = Hull(np.asarray(X, float)[0])
    # Float it properly rather than guessing a waterline: the verdict is
    # a depth comparison, so a fabricated wl would be a fabricated answer.
    wl = float(evaluate(np.asarray(X, float)[0], MissionSpec()).wl)
    out = pr.axis_clears_wake_deficit(
        h, wl, pr.DRIVE_LAWS[pr.DriveArchitecture.OUTBOARD])
    assert out is None, (
        "an outboard leg got a wake verdict from a tunnel measurement. "
        "'I could not measure this' must not read as 'this is fine' — "
        "nor as 'this is broken'")
    tun = pr.axis_clears_wake_deficit(
        h, wl, pr.DRIVE_LAWS[pr.DriveArchitecture.TUNNEL])
    assert isinstance(tun, bool), "the anchored stern must give a verdict"


def test_the_axis_convention_is_the_centred_disc_and_is_single_sourced():
    """The shallowest-admissible reading would fire on every boat afloat."""
    from navalai import propulsion as pr

    # Centred in the column it may use: half of (column + recess).
    assert pr.prop_axis_depth_m(0.8, 0.0) == pytest.approx(0.40)
    assert pr.prop_axis_depth_m(0.8, 0.2) == pytest.approx(0.50)
    # A recess DEEPENS the axis — that is the whole point of the recess,
    # and a sign error here would report the tunnel as making things
    # worse.
    assert pr.prop_axis_depth_m(0.8, 0.2) > pr.prop_axis_depth_m(0.8, 0.0)
    assert pr.prop_axis_depth_m(-1.0, -1.0) == 0.0


# ---------------------------------------------------------------------------
# GATE PROP, the geometry-coupling cases (2026-09-01): the levers the
# propulsion rows are scored with must be levers the HULL carries, not
# numbers the spec declares. These live under Gate PROP rather than under a
# new gate name — `docs/audit/ALIGNMENT-2026-08-21.md` records what a gate
# name declared twice costs, and this file already has an owner.
# ---------------------------------------------------------------------------

def _plain(**over):
    """A 16 x 4 m inland cruiser, with the tunnel genes under the caller's
    control. Deliberately not a sampled hull: the point is the difference
    between two hulls that differ ONLY in whether the tunnel is drawn."""
    g = dict(grammar.POST_HOC_DEFAULTS)
    g.update({"LWL": 16.0, "BWL": 4.0, "T": 0.75, "D": 1.60, "Cp": 0.72,
              "lcb": -1.0, "x_mb": 0.52, "r_transom": 0.55, "beta_mid": 6.0,
              "beta_bow": 22.0, "beta_len": 0.30, "roundness": 0.35,
              "rocker": 0.06, "forefoot": 0.10, "flare": 6.0,
              "sheer_rise": 0.10})
    g.update(over)
    from navalai.geometry import Hull as _H
    return _H(grammar.vector(g))


def test_a_declared_tunnel_recess_is_not_credited_to_a_hull_without_one():
    """THE MEASURED DEFECT (2026-09-01, the end-to-end integration audit).

    `prop_tunnel_recess_m` is a free declaration on `EnergySpec` and nothing
    looked at the hull, so on a 16 x 4 m hull at 6 kN of thrust:

        max drawn crown:  flat 0.000 m | tunnelled 0.2467 m
        flat  declared 0.00 -> prop_space +0.1315   VIOLATED
        flat  declared 0.50 -> prop_space -0.1948   satisfied
        tunnelled, both declarations -> IDENTICAL to the flat hull

    A flat-bottomed hull bought itself a bigger disc by saying so, and a hull
    that actually drew a tunnel got nothing for it. Same shape as the P6
    defect above, one level down: a lever the HULL does not have contributes
    nothing.
    """
    flat = _plain()
    assert propulsion.drawn_tunnel_recess_m(flat) == 0.0
    spec_r = EnergySpec(drive="shaft", n_props=1, motor_kw=40.0,
                        prop_tunnel_recess_m=0.5)
    spec_0 = EnergySpec(drive="shaft", n_props=1, motor_kw=40.0,
                        prop_tunnel_recess_m=0.0)
    g_r, why = propulsion.rows_for(flat, 0.0, 6000.0, 20000.0, spec_r)
    g_0, _ = propulsion.rows_for(flat, 0.0, 6000.0, 20000.0, spec_0)
    assert g_r["prop_space"] == pytest.approx(g_0["prop_space"], rel=0.0,
                                              abs=0.0)
    assert g_r["prop_space"] > 0.0, (
        "the row must still FIRE on this hull — a guard that stops firing is "
        "not a fix")
    # and the refusal is NAMED, never silent
    assert "does not have contributes nothing" in why["prop_space"]


def test_a_drawn_tunnel_IS_credited_and_moves_the_row():
    """The other half, and the half that makes the first one a fix rather
    than a blanket refusal: a hull that draws the tunnel gets the metres it
    draws. MEASURED at the prop station (0.12 L forward of the transom),
    where the Phase-4 crown has tapered to 0.1587 m of its 0.3797 m maximum.
    """
    tun = _plain(tun_w=0.35, tun_crown=0.50, tun_len=0.35)
    drawn = propulsion.drawn_tunnel_recess_m(tun)
    assert drawn == pytest.approx(0.1587, rel=0.02), drawn
    spec = EnergySpec(drive="shaft", n_props=1, motor_kw=40.0,
                      prop_tunnel_recess_m=0.5)
    law = propulsion.drive_law(spec)[1]
    credited, note = propulsion.credited_recess_m(tun, spec, law)
    assert credited == pytest.approx(drawn)
    assert "credited 0.159 m" in note
    g_t, _ = propulsion.rows_for(tun, 0.0, 6000.0, 20000.0, spec)
    g_f, _ = propulsion.rows_for(_plain(), 0.0, 6000.0, 20000.0, spec)
    assert g_t["prop_space"] < g_f["prop_space"], (
        "drawing the tunnel must buy disc room; if it does not, the geometry "
        "is still invisible to the propulsion rows")


def test_a_modest_declaration_under_the_drawn_tunnel_is_honoured_in_full():
    """`min(declared, drawn)`, not `drawn`: declaring LESS tunnel than the
    hull carries is a conservative installation, and refusing it would be a
    bar with no content."""
    tun = _plain(tun_w=0.35, tun_crown=0.50, tun_len=0.35)
    spec = EnergySpec(drive="shaft", n_props=1, motor_kw=40.0,
                      prop_tunnel_recess_m=0.05)
    law = propulsion.drive_law(spec)[1]
    credited, note = propulsion.credited_recess_m(tun, spec, law)
    assert credited == 0.05 and note == ""


def test_the_drive_law_still_wins_over_the_geometry():
    """An outboard on a tunnelled hull is still an outboard. The two guards
    compose; neither may cancel the other."""
    tun = _plain(tun_w=0.35, tun_crown=0.50, tun_len=0.35)
    spec = EnergySpec(drive="outboard", n_props=1, motor_kw=40.0,
                      prop_tunnel_recess_m=0.5)
    law = propulsion.drive_law(spec)[1]
    assert propulsion.credited_recess_m(tun, spec, law)[0] == 0.0


def test_a_drawn_tunnel_is_what_buys_the_single_prop_its_disc():
    """The claim `test_the_assessments_twin_tunnel_fix_passes` used to make,
    now made on a hull that has the tunnel.

    houseboat19 with ONE prop and no tunnel VIOLATES `prop_space`. Drawing
    the Phase-4 tunnel turns it into a pass, and the threshold is measurable:

        drawn at the prop station   prop_space   ladder
            0.0432 m                 +0.0224     REFUSED
            0.0718 m                 -0.0447     ok
            0.1005 m                 -0.0433     ok
            0.1720 m                    --       the hull no longer floats to
                                                 its target displacement

    The last row is the kernel's own contract holding: a notch deep enough to
    change the floated state is refused by flotation, not mis-integrated.
    """
    import json as _json
    base = _json.loads(_HB19.read_text()) if _HB19.exists() else None
    if base is None:
        pytest.skip("houseboat19 genome not on disk")
    ms = MissionSpec(name="prop-gate", lwl_hint_m=11.9,
                     displacement_target_kg=6500.0, cruise_speed_kn=5.0,
                     design_category="C", crew=4, waters="river+coastal",
                     energy=EnergySpec(battery_kwh=100.0, n_props=1,
                                       prop_tunnel_recess_m=0.16,
                                       prop_max_below_keel_m=0.0))
    flat = evaluate(grammar.vector(base), ms)
    assert flat.g["prop_space"] > 0.0, (
        "one un-tunnelled prop on this hull must still violate prop_space — "
        "that is the measured incident the row exists for")
    tunnelled = evaluate(
        grammar.vector({**base, "tun_w": 0.40, "tun_crown": 0.35,
                        "tun_len": 0.30}), ms)
    assert tunnelled.g["prop_space"] < 0.0 and tunnelled.ok, (
        f"the drawn tunnel did not buy the disc: "
        f"{tunnelled.g.get('prop_space')} {tunnelled.violations}")
