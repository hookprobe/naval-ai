"""Gate FG — the fidelity governor: one test per gate, BOTH directions.

The governor (`navalai/select_fidelity.py`) turns
`docs/research/SMALL-CRAFT-REGIMES.md` §16 and `docs/BUILD-PLAN.md` §11.8
into code. A gate that only ever fires one way is not a gate, so every one of
the five is exercised on a case it routes down AND a case it does not, with
the study's own measured numbers as the fixtures.

WHAT THIS SUITE IS DEFENDING (the audit finding it was written for): before
the governor, every valid design ran the SAME L1 model and was BADGED, never
ROUTED; the environment and wave-existence gates did not exist; the friction
and Froude gates were floors with no routing; and
`limits.WH_PER_NM_SIGMA_PRODUCT` had ZERO consumers repo-wide. The last test
class pins that constant as gate 4's bar, so deleting the consumer fails here.

REYNOLDS CONVENTION. The study quotes Re at sea-water nu = 1.19e-6 m^2/s
(1 m at 1 m/s -> 8.4e5, and 9.2e5 at the warmer fresh value it uses in §3's
grid); this tree's default is `resistance.nu_water(RHO_FRESH)` = 1.14e-6, so
the same point measures 8.77e5 here. The BAND is what the gate keys on and
all three numbers are inside it — the tests assert the band and the routing,
never a viscosity-dependent digit.
"""

from __future__ import annotations

import math

import pytest

from navalai import limits
from navalai.mission import MissionSpec, PayloadSpec, WindageSpec
from navalai.resistance import FN_MICHELL_MAX
from navalai.select_fidelity import (GATE_DECISION_WORTHINESS,
                                     GATE_ENVIRONMENT, GATE_FRICTION_REGIME,
                                     GATE_FROUDE, GATE_WAVE_EXISTENCE,
                                     LAMINAR_SIGMA_MULTIPLIER, OUT_BAR,
                                     OUT_CANNOT_DECIDE, OUT_CLEAR, OUT_ROUTE,
                                     TIER_ANALYTICAL, TIER_EMPIRICAL,
                                     TIER_LOW_FIDELITY_CFD, TIER_REFUSE,
                                     TRANSITIONAL_SIGMA_FLOOR,
                                     orbital_velocity_ms, select_fidelity,
                                     wave_share_estimate, windage_force_n)

G = 9.80665


def _v_for_fn(fn: float, lwl: float) -> float:
    return fn * math.sqrt(G * lwl)


# ---------------------------------------------------------------------------
# GATE 0 — ENVIRONMENT
# ---------------------------------------------------------------------------

def test_gate0_routes_a_wave_follower_to_analytical():
    """§7: at lambda/L >~ 5 the hull rides the surface — there is nothing to
    pierce and the calm-water wave pattern is not the energy budget.

    MEASURED HERE: a 1 m drone in the study's sea state 3 (Hs 0.9 m, T 5 s,
    §7's band) sees lambda = g T^2 / 2 pi = 39.0 m, i.e. lambda/L = 39 — eight
    times the bar. The decision must be ANALYTICAL, flagged, and CFD refused.
    """
    d = select_fidelity(lwl_m=1.0, speed_ms=0.5, sea_state=3)
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_ROUTE
    assert g.measure == "lambda_over_lwl"
    assert g.value == pytest.approx(39.04, rel=1e-3)
    assert d.tier == TIER_ANALYTICAL
    assert "ENERGY_BUDGET_IS_ENVIRONMENTAL" in d.flags
    assert d.cfd_allowed is False
    assert GATE_ENVIRONMENT in d.why and "39" in d.why


def test_gate0_does_not_route_a_boat_that_is_bigger_than_its_weather():
    """The other direction, same sea state: a 12 m hull at 2.82 m/s (Fn 0.26)
    in sea state 3 has lambda/L = 3.25 (under the 5 bar), an orbital velocity
    0.565 m/s = 0.20 of its speed (under the 0.5 bar), and 10 m^2 of declared
    windage in a 10 m/s wind is 612 N against 800 N of hull resistance = 0.77
    (under the 2x bar). All three measured, none tripped, gate CLEAR."""
    d = select_fidelity(
        lwl_m=12.0, speed_ms=2.82, lb_ratio=8.0, sea_state=3,
        hull_resistance_n=800.0, wind_speed_ms=10.0,
        windage=WindageSpec(lateral_area_m2=10.0, centroid_above_wl_m=1.5))
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_CLEAR
    assert "ENERGY_BUDGET_IS_ENVIRONMENTAL" not in d.flags
    # every sub-criterion is on the receipt with its number, not just the one
    # that could have tripped
    joined = " ".join(g.detail)
    assert "lambda/L" in joined and "windage/R" in joined \
        and "u_orbital/V" in joined
    assert d.tier == TIER_EMPIRICAL


def test_gate0_trips_on_windage_alone_when_the_hull_drag_is_tiny():
    """§1's measured anchor, the windage half: a 0.5 m hull at 0.5 m/s has
    R ~ 0.06 N while a non-scaling 0.10 m^2 sensor/antenna profile in a 10 m/s
    wind pulls 6.1 N at this tree's declared bluff-body Cd — 100x, against a
    2x bar. (The study's own 30-50x uses a streamlined Cd 0.33-0.65; both are
    far over the bar, and ours errs in the tripping direction.)"""
    d = select_fidelity(lwl_m=0.5, speed_ms=0.5, hull_resistance_n=0.06,
                        wind_speed_ms=10.0,
                        windage=WindageSpec(lateral_area_m2=0.10,
                                            centroid_above_wl_m=0.3))
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_ROUTE
    assert g.measure == "windage_over_resistance"
    assert g.value == pytest.approx(6.125 / 0.06, rel=1e-3)
    assert d.tier == TIER_ANALYTICAL


def test_gate0_trips_when_the_water_moves_as_fast_as_the_boat():
    """§1/§16's third clause, isolated: sea state 3's surface orbital velocity
    is u = pi H / T = 0.565 m/s (the study quotes 0.57). A 12 m hull loitering
    at 1.0 m/s therefore sees u/V = 0.57 against the 0.5 bar, while lambda/L
    is only 3.25 — so this case can ONLY trip on the orbital clause."""
    d = select_fidelity(lwl_m=12.0, speed_ms=1.0, sea_state=3)
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_ROUTE
    assert g.measure == "u_orbital_over_speed"
    assert g.value == pytest.approx(0.565, rel=1e-2)
    assert d.tier == TIER_ANALYTICAL


def test_gate0_refuses_to_guess_an_undeclared_environment():
    """THE RULE THAT MAKES THE GATE HONEST: an undeclared environment is not
    a quiet 'the environment is fine'. Nothing declared -> CANNOT_DECIDE with
    every missing input NAMED, a warning on the decision, and the ladder
    CONTINUES to the next gate rather than passing or refusing on silence."""
    d = select_fidelity(lwl_m=12.0, speed_ms=2.82, lb_ratio=8.0)
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_CANNOT_DECIDE
    assert g.outcome != OUT_CLEAR                     # never a silent pass
    assert "sea state" in g.why or "wave period" in g.why
    assert "lateral area" in g.why
    assert any("environment gate CANNOT be decided" in w for w in d.warnings)
    assert d.tier == TIER_EMPIRICAL                   # gate 3 still decided


def test_gate0_will_not_invent_a_sea_state_it_has_no_table_for():
    """The table covers sea states 0-5, which is what §7 states. WMO code 3700
    has rows above that, this study does not, and a fabricated period would
    fabricate BOTH lambda and the orbital velocity — the two quantities the
    gate is made of. So SS7 is a named refusal, not an extrapolation."""
    d = select_fidelity(lwl_m=12.0, speed_ms=2.82, sea_state=7)
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_CANNOT_DECIDE
    assert "outside the tabulated band" in " ".join(g.detail)
    assert "NOT fabricated" in " ".join(g.detail)


def test_the_orbital_and_windage_estimators_match_their_stated_bases():
    """The two estimators gate 0 needed and this tree did not have, checked
    against the study's own quoted values rather than against themselves.

    u = pi H / T at sea state 3 (0.9 m, 5 s) = 0.565 m/s; the study says 0.57
    in §1. Windage on the rule pressure is p*A (500 Pa is the strictest row of
    NZ Part 40A cl 1.2(8)(d)(ii)); on a declared wind speed it is the
    bluff-body form `dynamics.mooring` already uses.
    """
    assert orbital_velocity_ms(0.9, 5.0) == pytest.approx(0.57, abs=0.01)
    f_rule, basis_rule = windage_force_n(2.0)
    assert f_rule == pytest.approx(1000.0)            # 500 Pa x 2 m^2
    assert "Pa" in basis_rule
    f_wind, basis_wind = windage_force_n(2.0, wind_speed_ms=10.0)
    assert f_wind == pytest.approx(0.5 * 1.225 * 1.0 * 2.0 * 100.0)
    assert "rho_air" in basis_wind


# ---------------------------------------------------------------------------
# GATE 1 — WAVE EXISTENCE
# ---------------------------------------------------------------------------

def test_gate1_below_c_min_there_is_no_wave_system_to_model():
    """§6: the gravity-capillary phase speed has a MINIMUM c_min ~ 0.23 m/s.
    Below it no steady wave pattern of any wavelength can exist, so a wave
    resistance there is not small — it is fiction. A 1 m drone loitering at
    0.2 m/s is routed ANALYTICAL and flagged, and CFD is refused."""
    d = select_fidelity(lwl_m=1.0, speed_ms=0.2)
    g = d.gate(GATE_WAVE_EXISTENCE)
    assert g.outcome == OUT_ROUTE and g.value == pytest.approx(0.2)
    assert "WAVE_SYSTEM_ABSENT" in d.flags
    assert d.tier == TIER_ANALYTICAL
    assert d.cfd_allowed is False
    assert GATE_WAVE_EXISTENCE in d.why and "0.23" in d.why


def test_gate1_between_c_min_and_half_a_metre_per_second_it_is_contaminated():
    """The middle band, which is a BAR and not a route: at 0.4 m/s the
    transverse wavelength lambda_t = 2 pi V^2/g is 10.3 cm against the 1.7 cm
    capillary wavelength, so Michell (pure gravity) misprices the system. The
    wave term survives with a flag; CFD does not (§15: 'Never')."""
    d = select_fidelity(lwl_m=1.0, speed_ms=0.4)
    g = d.gate(GATE_WAVE_EXISTENCE)
    assert g.outcome == OUT_BAR
    assert "WAVE_CAPILLARY_CONTAMINATED" in d.flags
    assert "10.3 cm" in g.why
    assert d.cfd_allowed is False
    assert "WAVE_SYSTEM_ABSENT" not in d.flags


def test_gate1_does_not_fire_on_a_boat_that_makes_a_real_wake():
    """The other direction: the same 1 m hull at 1.0 m/s has lambda_t = 64 cm,
    38x the capillary wavelength — a clean gravity wave system (§6)."""
    d = select_fidelity(lwl_m=1.0, speed_ms=1.0)
    g = d.gate(GATE_WAVE_EXISTENCE)
    assert g.outcome == OUT_CLEAR
    assert not [f for f in d.flags if f.startswith("WAVE_")]


# ---------------------------------------------------------------------------
# GATE 2 — FRICTION REGIME  (seam: limits.RE_TRANSITION_BAND)
# ---------------------------------------------------------------------------

def test_gate2_bars_cfd_in_the_transition_band_and_widens_the_sigma():
    """THE DRONE BLOCKER, and the study's headline case: a 1 m hull at 1 m/s
    sits at Re 8.8e5 (this tree's fresh-water nu; 8.4-9.2e5 at the study's),
    inside `limits.RE_TRANSITION_BAND` = (5e5, 5e6). ITTC-57 is a FULLY
    TURBULENT correlation being read outside the flow it correlates, and a
    fully-turbulent RANS reproduces that same bias — higher cost, same
    wrongness (§20 row 6). CFD is BARRED and the empirical sigma widens to
    the study's +-30..50% band."""
    d = select_fidelity(lwl_m=1.0, speed_ms=1.0)
    g = d.gate(GATE_FRICTION_REGIME)
    lo, hi = limits.RE_TRANSITION_BAND
    assert lo < g.value < hi
    assert g.outcome == OUT_BAR and g.bars_cfd is True
    assert d.cfd_allowed is False
    assert "FRICTION_TRANSITIONAL" in d.flags
    assert d.sigma_floor_frac == TRANSITIONAL_SIGMA_FLOOR
    assert d.sigma_multiplier == 1.0
    assert d.tier == TIER_EMPIRICAL          # the wave half is still valid


def test_gate2_lifts_the_bar_only_for_a_declared_transition_modelled_run():
    """The escape hatch is a DECLARATION, not a default: the same 1 m hull is
    CFD-admissible only when the caller states the run is transition-modelled
    and validated. The widened sigma stays either way."""
    d = select_fidelity(lwl_m=1.0, speed_ms=1.0, transition_modelled=True)
    assert d.cfd_allowed is True
    assert d.sigma_floor_frac == TRANSITIONAL_SIGMA_FLOOR
    assert "transition-modelled" in d.gate(GATE_FRICTION_REGIME).why


def test_gate2_refuses_cfd_outright_below_the_transition_onset():
    """Below the band there is no correlation data at all: a 0.3 m hull at
    0.6 m/s is Re 1.6e5, laminar, so the tier is ANALYTICAL only (Blasius with
    the study's x2 friction margin) and CFD is REFUSED, not merely barred.
    Note the ROUTE: gate 3 would have said EMPIRICAL at this Fn (0.35) and the
    friction gate overrides it — the routing the badges never did."""
    d = select_fidelity(lwl_m=0.3, speed_ms=0.6)
    g = d.gate(GATE_FRICTION_REGIME)
    assert g.value < limits.RE_TRANSITION_BAND[0]
    assert g.outcome == OUT_ROUTE and g.tier_cap == TIER_ANALYTICAL
    assert d.tier == TIER_ANALYTICAL
    assert d.sigma_multiplier == LAMINAR_SIGMA_MULTIPLIER
    assert "FRICTION_LAMINAR" in d.flags


def test_gate2_is_silent_on_a_hull_that_is_properly_turbulent():
    """The other direction: 12 m at 2.82 m/s is Re 2.97e7, five times over the
    band's ceiling — ITTC-57 is inside the flow it correlates and the gate
    caps nothing."""
    d = select_fidelity(lwl_m=12.0, speed_ms=2.82, lb_ratio=8.0)
    g = d.gate(GATE_FRICTION_REGIME)
    assert g.value > limits.RE_TRANSITION_BAND[1]
    assert g.outcome == OUT_CLEAR and g.tier_cap is None
    assert d.sigma_floor_frac is None and d.sigma_multiplier == 1.0


def test_gate2_reads_the_ONE_band_and_does_not_retype_it():
    """C-31's rule applied to the governor: the transition band has one home."""
    from navalai import select_fidelity as sfmod
    assert (sfmod.RE_TRANSITION_ONSET,
            sfmod.RE_FULLY_TURBULENT) == limits.RE_TRANSITION_BAND


# ---------------------------------------------------------------------------
# GATE 3 — FROUDE  (seam: resistance.FN_MICHELL_MAX)
# ---------------------------------------------------------------------------

def test_gate3_analytical_suffices_below_fn_020():
    """§5, MEASURED on repo Holtrop: below Fn 0.20 the wave share is <=5-8% at
    every size in the grid, so L0 friction+form matches anything fancier
    inside the product's own sigma. A 12 m hull at Fn 0.15 gets ANALYTICAL —
    and this is a 'suffices', not a refusal, so nothing is flagged."""
    d = select_fidelity(lwl_m=12.0, speed_ms=_v_for_fn(0.15, 12.0),
                        lb_ratio=8.0)
    g = d.gate(GATE_FROUDE)
    assert g.outcome == OUT_ROUTE and g.value == pytest.approx(0.15, abs=5e-3)
    assert d.tier == TIER_ANALYTICAL
    assert "wave share" in g.why


def test_gate3_routes_the_michell_envelope_to_empirical():
    """0.20 < Fn <= FN_MICHELL_MAX with a slender hull is L1's home turf: a
    12 m hull at Fn 0.26 with B/L 0.125 (L/B 8) -> EMPIRICAL, and with a
    declared correction over the 10% bar it is CFD-worthy too."""
    d = select_fidelity(lwl_m=12.0, speed_ms=_v_for_fn(0.26, 12.0),
                        lb_ratio=8.0, expected_correction_frac=0.17)
    assert d.tier == TIER_EMPIRICAL
    assert d.gate(GATE_FROUDE).value == pytest.approx(0.26, abs=5e-3)
    assert "IN ENVELOPE" in d.gate(GATE_FROUDE).why
    assert d.cfd_allowed is True and d.cfd_decision_worthy is True


def test_gate3_names_the_thin_ship_strain_on_a_full_hull():
    """Michell is linearised on hull SLOPE, so its envelope is a B/L bar
    (§5: trustworthy to B/L ~0.10-0.15, degrading fast for fuller forms). The
    same Fn on an L/B 2.5 dayboat (B/L 0.40) still routes EMPIRICAL — the
    model is not refused — but the receipt says the linearisation is strained
    and the sigma is the widened one."""
    d = select_fidelity(lwl_m=12.0, speed_ms=_v_for_fn(0.26, 12.0),
                        lb_ratio=2.5)
    assert d.tier == TIER_EMPIRICAL
    assert "STRAINED" in d.gate(GATE_FROUDE).why
    assert "0.400" in d.gate(GATE_FROUDE).why


def test_gate3_refuses_a_semi_displacement_hull_that_is_too_small_for_cfd():
    """0.45 < Fn <= 0.65 has NO empirical tier in this tree (transom, trim and
    dynamic lift are absent from L1), so CFD is the only honest answer — and
    only at L >= 3 m, where RANS is demonstrated (Delft 372, 2-5% vs tank)
    against a measured >=30% friction error at 1 m. A 2 m hull at Fn 0.5 is
    therefore REFUSE, not 'run CFD': there is no tier, not a cheap one."""
    d = select_fidelity(lwl_m=2.0, speed_ms=_v_for_fn(0.5, 2.0))
    assert d.tier == TIER_REFUSE
    assert d.tier != TIER_LOW_FIDELITY_CFD
    assert "3.0 m floor" in d.why or "3.0 m" in d.why
    assert d.cfd_allowed is False and d.cfd_decision_worthy is False


def test_gate3_sends_the_same_froude_number_to_cfd_once_the_hull_is_big():
    """The other direction of the same band: 5 m at Fn 0.5 is Re 1.5e7 (out of
    the transition band) and over the 3 m floor -> LOW_FIDELITY_CFD, which is
    a NECESSITY, not an upgrade."""
    d = select_fidelity(lwl_m=5.0, speed_ms=_v_for_fn(0.5, 5.0))
    assert d.tier == TIER_LOW_FIDELITY_CFD
    assert "only honest answer" in d.gate(GATE_FROUDE).why


def test_gate3_refuses_the_planing_regime_because_no_savitsky_exists():
    """Fn > 0.65 is dynamic lift. There is no Savitsky-class model in this
    tree, so the answer is a named REFUSE at any size — a 6 m hull included."""
    d = select_fidelity(lwl_m=6.0, speed_ms=_v_for_fn(0.80, 6.0))
    assert d.tier == TIER_REFUSE
    assert "Savitsky" in d.why


def test_gate3_reads_the_wave_envelope_from_resistance():
    """FN_MICHELL_MAX has one home. Fn just under it is EMPIRICAL; just over
    it leaves the envelope — the bar the governor uses IS resistance's."""
    lwl = 8.0
    below = select_fidelity(lwl_m=lwl, lb_ratio=8.0,
                            speed_ms=_v_for_fn(FN_MICHELL_MAX - 0.01, lwl))
    above = select_fidelity(lwl_m=lwl, lb_ratio=8.0,
                            speed_ms=_v_for_fn(FN_MICHELL_MAX + 0.01, lwl))
    assert below.tier == TIER_EMPIRICAL
    assert above.tier == TIER_LOW_FIDELITY_CFD


def test_a_cap_plus_a_cfd_necessity_is_a_refusal_not_a_downgrade():
    """THE COMPOSITION RULE, which is where a governor usually goes wrong.

    A 5 m ASV at Fn 0.5 in sea state 3 is capped at ANALYTICAL by the
    environment gate (lambda/L = 7.8 > 5, a wave-follower) while gate 3 says
    NO cheaper tier is VALID at that Froude number. Handing back ANALYTICAL
    would be a number from a model already ruled out, so the honest answer is
    REFUSE — with the environmental flag still carried, and the why naming
    BOTH gates."""
    d = select_fidelity(lwl_m=5.0, speed_ms=_v_for_fn(0.5, 5.0), sea_state=3)
    assert d.gate(GATE_ENVIRONMENT).outcome == OUT_ROUTE
    assert d.gate(GATE_FROUDE).outcome == OUT_ROUTE
    assert d.tier == TIER_REFUSE
    assert d.tier not in (TIER_ANALYTICAL, TIER_LOW_FIDELITY_CFD)
    assert GATE_ENVIRONMENT in d.why and GATE_FROUDE in d.why
    assert "ENERGY_BUDGET_IS_ENVIRONMENTAL" in d.flags


# ---------------------------------------------------------------------------
# GATE 4 — DECISION-WORTHINESS  (seam: limits.WH_PER_NM_SIGMA_PRODUCT)
# ---------------------------------------------------------------------------

def test_gate4_is_the_first_consumer_of_the_product_sigma():
    """§13/§19: `limits.WH_PER_NM_SIGMA_PRODUCT` (0.10) was declared, measured
    and had ZERO consumers repo-wide. It is gate 4's bar, and the bar is read
    from limits — not retyped. The flip is exercised on both sides of it."""
    bar = limits.WH_PER_NM_SIGMA_PRODUCT
    kw = dict(lwl_m=12.0, speed_ms=_v_for_fn(0.26, 12.0), lb_ratio=8.0)
    over = select_fidelity(expected_correction_frac=bar + 0.01, **kw)
    under = select_fidelity(expected_correction_frac=bar - 0.01, **kw)
    assert over.cfd_decision_worthy is True
    assert under.cfd_decision_worthy is False
    assert "WH_PER_NM_SIGMA_PRODUCT" in over.gate(GATE_DECISION_WORTHINESS).why
    assert over.gate(GATE_DECISION_WORTHINESS).outcome == OUT_CLEAR
    assert under.gate(GATE_DECISION_WORTHINESS).outcome == OUT_BAR
    # the tier itself does NOT move: both are EMPIRICAL, because escalation
    # needs the second clause too (below)
    assert over.tier == under.tier == TIER_EMPIRICAL


def test_gate4_kills_the_upgrade_when_no_verdict_can_flip():
    """§16's second clause, which is the half that stops a governor becoming a
    rubber stamp: a correction is only decision-relevant if the nearest verdict
    flip is within 2.5x of it. A 20% correction with the nearest flip 90% away
    cannot reach one, so it is NOT worthy however big it is."""
    kw = dict(lwl_m=12.0, speed_ms=_v_for_fn(0.26, 12.0), lb_ratio=8.0,
              expected_correction_frac=0.20)
    reachable = select_fidelity(verdict_flip_distance_frac=0.30, **kw)
    unreachable = select_fidelity(verdict_flip_distance_frac=0.90, **kw)
    assert reachable.cfd_decision_worthy is True
    assert unreachable.cfd_decision_worthy is False
    assert "no verdict can flip" in \
        unreachable.gate(GATE_DECISION_WORTHINESS).why
    # and with BOTH clauses satisfied, §16's literal rule upgrades ONE level
    assert reachable.tier == TIER_LOW_FIDELITY_CFD


def test_gate4_prices_an_analytical_incumbent_off_the_measured_wave_share():
    """With no declared correction, what a wave-resolving tier could move is
    bounded by what the wave term is WORTH — §5's measured grid. At Fn 0.15
    that is the study's <=5% bound, which is under the 10% bar, so a 12 m hull
    cruising slowly is NOT CFD-worthy. This is §20 row 1, executable."""
    d = select_fidelity(lwl_m=12.0, speed_ms=_v_for_fn(0.15, 12.0),
                        lb_ratio=8.0)
    assert d.tier == TIER_ANALYTICAL
    assert d.expected_correction_frac == pytest.approx(0.05)
    assert "§5" in d.expected_correction_basis
    assert d.cfd_decision_worthy is False


def test_gate4_will_not_treat_an_unmeasured_correction_as_a_large_one():
    """The missing-input direction: a CFD tier reached by NECESSITY still has
    to declare what it would correct. Nothing declared -> CANNOT_DECIDE, and
    an unmeasured correction is not a passing one."""
    d = select_fidelity(lwl_m=5.0, speed_ms=_v_for_fn(0.5, 5.0))
    g = d.gate(GATE_DECISION_WORTHINESS)
    assert g.outcome == OUT_CANNOT_DECIDE
    assert d.cfd_decision_worthy is False
    assert "not a large one" in g.why


def test_the_measured_wave_share_table_is_read_not_extrapolated():
    """§5's grid: wave share rises with size at fixed Fn (the small hull is
    MORE friction-dominated) and with Fn at fixed size, and it is CLAMPED at
    the last measured column rather than extrapolated into the hump."""
    s_small, _ = wave_share_estimate(0.25, 1.0)
    s_big, _ = wave_share_estimate(0.25, 12.0)
    assert s_small == pytest.approx(0.105, abs=1e-3)
    assert s_big == pytest.approx(0.177, abs=1e-3)
    assert wave_share_estimate(0.35, 12.0)[0] == pytest.approx(0.46, abs=1e-3)
    clamped, basis = wave_share_estimate(0.60, 12.0)
    assert clamped == pytest.approx(0.46, abs=1e-3) and "CLAMPED" in basis


# ---------------------------------------------------------------------------
# MISSING INPUTS — named receipts, never a crash and never a silent pass
# ---------------------------------------------------------------------------

def test_an_empty_call_refuses_to_select_and_names_every_missing_input():
    """The governor is TOTAL: given nothing, it neither raises nor defaults to
    the cheapest tier (an unknown hull is not a slow one). Every gate returns
    CANNOT_DECIDE with its missing input named, and the tier is REFUSE with a
    warning saying REFUSE here means UNDECIDABLE."""
    d = select_fidelity()
    assert d.tier == TIER_REFUSE
    assert [g.outcome for g in d.gates] == [OUT_CANNOT_DECIDE] * 5
    assert not any(g.outcome == OUT_CLEAR for g in d.gates)
    assert d.cfd_allowed is False and d.cfd_decision_worthy is False
    assert any("too little to route" in w for w in d.warnings)
    for g in d.gates:
        assert g.why and len(g.why) > 20, g.name


@pytest.mark.parametrize("bad", [0.0, -3.0, float("nan"), float("inf"),
                                 "banana", None, object()])
def test_junk_geometry_is_unknown_not_zero(bad):
    """Defect class 1 in this repository is an unmeasurable quantity scored as
    a passing one. A non-positive, non-finite or non-numeric length or speed
    is treated as UNKNOWN — never coerced to zero, never crashing."""
    d = select_fidelity(lwl_m=bad, speed_ms=bad)
    assert d.tier == TIER_REFUSE
    assert d.fn is None and d.re is None
    assert d.gate(GATE_FROUDE).outcome == OUT_CANNOT_DECIDE


def test_a_partially_declared_environment_names_only_what_is_missing():
    """Half a declaration is not a refusal of the whole gate: with a sea state
    but no windage area, lambda/L and u/V ARE measured and appear on the
    receipt, and the gate says exactly which input it still lacks."""
    d = select_fidelity(lwl_m=12.0, speed_ms=2.82, lb_ratio=8.0, sea_state=2)
    g = d.gate(GATE_ENVIRONMENT)
    assert g.outcome == OUT_CANNOT_DECIDE
    assert "lambda/L" in " ".join(g.detail)
    assert "lateral area" in g.why
    assert "wave period" not in g.why          # that one WAS declared


def test_the_mission_is_read_defensively_and_optionally():
    """`MissionSpec` is the natural source of the declared environment, and it
    is read through `getattr` so any object — or none — works. A mission that
    declares a sea state routes on it; the same mission with nothing declared
    reaches the CANNOT_DECIDE receipt instead of an exception."""
    m = MissionSpec(lwl_hint_m=1.0, cruise_speed_kn=1.0,
                    payload=PayloadSpec(sea_state=3))
    d = select_fidelity(lwl_m=1.0, speed_ms=m.cruise_speed_ms(), mission=m)
    assert d.gate(GATE_ENVIRONMENT).outcome == OUT_ROUTE
    assert d.tier == TIER_ANALYTICAL
    bare = select_fidelity(lwl_m=1.0, speed_ms=0.5,
                           mission=object())          # not a MissionSpec
    assert bare.gate(GATE_ENVIRONMENT).outcome == OUT_CANNOT_DECIDE


def test_every_receipt_carries_its_measured_value_and_never_a_bare_verdict():
    """§25's rule applied to the governor: `why` always contains the number
    the gate decided on, and the decision's own `why` names the GATE."""
    d = select_fidelity(lwl_m=1.0, speed_ms=1.0, lb_ratio=6.0,
                        expected_correction_frac=0.4)
    for g in d.gates[:4]:
        if g.value is not None:
            token = f"{g.value:.3g}".split("e")[0][:4]
            assert token in g.why, f"{g.name}: {g.why}"
    # gate 4 renders its fraction as a percentage, which is the form the
    # product sigma is quoted in everywhere else
    assert "40.0%" in d.gate(GATE_DECISION_WORTHINESS).why
    assert d.why.split(":")[0] in {GATE_ENVIRONMENT, GATE_WAVE_EXISTENCE,
                                   GATE_FRICTION_REGIME, GATE_FROUDE,
                                   GATE_DECISION_WORTHINESS}


def test_the_decision_serialises_whole():
    """The certification carries this block as a dict; nothing in it may be a
    live object, and the worthiness bar travels with it."""
    d = select_fidelity(lwl_m=12.0, speed_ms=2.82, lb_ratio=8.0,
                        expected_correction_frac=0.17)
    out = d.to_dict()
    import json
    json.dumps(out)                       # raises if anything is not plain
    assert out["tier"] == TIER_EMPIRICAL
    assert len(out["gates"]) == 5
    assert out["worthiness_bar"] == limits.WH_PER_NM_SIGMA_PRODUCT


# ---------------------------------------------------------------------------
# THE CERTIFY SEAM — "CFD-eligible" now means the governor said so
# ---------------------------------------------------------------------------

def test_certify_carries_the_governor_and_uses_it_for_eligibility():
    """The audit's finding, closed: `cfd_candidate["eligible"]` used to mean
    'the ladder could evaluate this hull', which made every valid design
    CFD-worthy. It now means select_fidelity says CFD is admissible AND
    decision-worthy — and the certification carries the five gate receipts.

    MEASURED on the canonical 15 m cruiser (formcheck case b, 7 kn): Fn 0.297,
    Re 4.7e7, L1 relative sigma 17% — EMPIRICAL, CFD admissible, and worthy
    because 17% clears the 10% product sigma. The verdict does not move.
    """
    from navalai import formcheck
    from navalai.certify import certify

    case = {c.key: c for c in formcheck.CASES}["b"]
    cert = certify(case.params, case.mission, with_gz=False)
    assert cert.fidelity["tier"] == TIER_EMPIRICAL
    assert len(cert.fidelity["gates"]) == 5
    assert cert.cfd_candidate["fidelity_tier"] == TIER_EMPIRICAL
    assert cert.cfd_candidate["decision_worthy"] is True
    assert cert.cfd_candidate["eligible"] is True
    assert cert.cfd_candidate["worthiness_bar"] == \
        limits.WH_PER_NM_SIGMA_PRODUCT
    # the environment gate is UNDECIDED on this mission (no declared sea state
    # or windage) and says so — it does not read as a clean pass
    env = [g for g in cert.fidelity["gates"] if g["gate"] == GATE_ENVIRONMENT]
    assert env and env[0]["outcome"] == OUT_CANNOT_DECIDE


def test_the_planing_onset_has_one_home():
    """`certify._FN_PLANING_ONSET` is gate 3's top band, imported rather than
    declared twice (C-31's rule)."""
    from navalai import certify as C
    from navalai.select_fidelity import FN_PLANING_ONSET
    assert C._FN_PLANING_ONSET is FN_PLANING_ONSET
