"""L1 mission physics: weight/CG budget and the solar-electric energy model.

BuildPlan Phase 1 makes these first-class: for a solar-electric boat, battery
mass and panel area dominate displacement/CG, and Energy/NM is the prime
objective — none of the surveyed hull literature models this, so we do.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .limits import PLY_THICKNESS_M


@dataclass(frozen=True)
class EnergySpec:
    """Mission-level energy/weight inputs (defaults: Danube summer cruising)."""
    payload_kg: float = 800.0          # crew + stores + water
    battery_kwh: float = 30.0
    hotel_kwh_day: float = 3.0
    solar_yield_kwh_m2_day: float = 4.2   # Danube ~45N summer average, horizontal
    panel_packing: float = 0.55           # usable deck fraction for PV
    panel_eff: float = 0.21
    prop_efficiency: float = 0.55         # prop x shaft
    motor_efficiency: float = 0.92
    cruise_hours_day: float = 8.0


# structural mass model constants (plywood-epoxy build, Phase 6 refines via ISO 12215)
PLY_DENSITY = 650.0        # kg/m^3
BATT_KG_PER_KWH = 7.5      # LiFePO4 pack-level
PANEL_KG_PER_M2 = 12.0
OUTFIT_KG_PER_M = 55.0     # interior, systems, rig per metre LWL


def shell_area_m2(hull) -> float:
    """The structural shell area — INTEGRATED, not a factor times the wetted area.

    THE UNDOCUMENTED x1.6 (gap C9). The weight path fed `weight_budget` a
    `hull_surface` of `hull.wetted_surface(0.0) * 1.6`: the area wetted at the
    design waterline, scaled by a bare literal standing in for "and the topsides
    above it". But a boat is planked to the SHEER, and the same integral run to
    the sheer is exactly that area — `wetted_surface` takes the waterline as an
    argument, so the quantity the 1.6 approximates was one call away, and
    `engineer.assess` was already making it. A factor sitting beside the
    quantity that computes it is this codebase's recurring defect (a number
    declared twice) with the second copy rounded.

    MEASURED on the reference 10 m hull: wetted(0.0) = 30.579 m^2, shell to the
    sheer = 51.616 m^2, so the true ratio is **1.6879** and 1.6 understated the
    shell by 5.2% — structure mass 1010.7 kg instead of 1046.1 kg (-3.38%),
    displacement 2769.6 vs 2805.0 kg (-1.26%).

    It was far worse away from the reference hull, which is the point: the ratio
    is not a constant, it is a shape. Over 200 grammar-feasible hulls (seed 3)
    it ran **1.251 to 6.702**, mean 2.062, so the single literal 1.6 was wrong
    by up to **76%** of the true area and by -15.4% on average — and the
    optimiser searches exactly that box, so it was scoring structure mass with
    an error that varied systematically with the shape it was choosing.

    Named here rather than inlined at each call site because `engineer.assess`
    and the L1 weight path must plank the same boat.
    """
    return float(hull.wetted_surface(float(hull.z_sheer.max())))


@dataclass(frozen=True)
class WeightBudget:
    structure_kg: float
    battery_kg: float
    panel_kg: float
    outfit_kg: float
    payload_kg: float
    total_kg: float
    kg_above_keel: float   # composite VCG above keel plane


def weight_budget(lwl: float, depth: float, hull_surface: float,
                  deck_area: float, spec: EnergySpec,
                  panel_thickness_m: float = PLY_THICKNESS_M) -> WeightBudget:
    structure = (hull_surface + deck_area) * panel_thickness_m * PLY_DENSITY * 1.35
    battery = spec.battery_kwh * BATT_KG_PER_KWH
    pv_area = deck_area * spec.panel_packing
    panels = pv_area * PANEL_KG_PER_M2
    outfit = OUTFIT_KG_PER_M * lwl
    total = structure + battery + panels + outfit + spec.payload_kg
    masses = {"structure": structure, "battery": battery, "panels": panels,
              "outfit": outfit, "payload": spec.payload_kg}
    # VCG stack above keel: batteries low, structure mid, panels on deck.
    # Built FROM `VCG_FRACTION` rather than from inlined literals. The two used
    # to hold the same five numbers fifteen lines apart, agreeing only because
    # a test compared them — which makes the test load-bearing instead of
    # tautological, and is the "declared twice" pattern the invariants forbid.
    kg = sum(m * VCG_FRACTION[name] * depth for name, m in masses.items()) / total
    return WeightBudget(structure, battery, panels, outfit, spec.payload_kg,
                        total, kg)


# Longitudinal placement of each bucket as a fraction of LWL from the transom.
# Declared rather than assumed: previously there was no LCG at all, so these
# were implicitly "wherever you like" and an arrangement could not trim the
# boat. They reproduce a conventional distribution — machinery and tanks aft of
# midships, accommodation amidships, payload slightly aft — and tiers E/F will
# replace them item by item with real positions.
LCG_FRACTION = {"structure": 0.50, "battery": 0.45, "panels": 0.52,
                "outfit": 0.50, "payload": 0.48}
# Vertical placement as a fraction of depth above the keel (the stack that used
# to be inlined in weight_budget's kg calculation).
VCG_FRACTION = {"structure": 0.55, "battery": 0.15, "panels": 1.02,
                "outfit": 0.60, "payload": 0.70}


def weight_items(lwl: float, depth: float, hull_surface: float,
                 deck_area: float, spec: EnergySpec, t_design: float,
                 panel_thickness_m: float = PLY_THICKNESS_M) -> list:
    """The same five buckets, as positioned MassItems.

    Same masses and the same VCG fractions as `weight_budget`, so nothing moves
    numerically — this only gives each bucket a position so tiers E and F can
    add to the SAME list instead of a parallel model. z is returned in the hull
    frame (0 at the design waterline), which is why t_design is subtracted.
    """
    from .weights import MassItem

    wb = weight_budget(lwl, depth, hull_surface, deck_area, spec,
                       panel_thickness_m)
    masses = {"structure": wb.structure_kg, "battery": wb.battery_kg,
              "panels": wb.panel_kg, "outfit": wb.outfit_kg,
              "payload": wb.payload_kg}
    items = []
    for name, m in masses.items():
        items.append(MassItem(
            id=name, mass_kg=m,
            x_m=LCG_FRACTION[name] * lwl,
            z_m=VCG_FRACTION[name] * depth - t_design,
            # 15% on a first-principles build estimate; payload is the owner's
            # to declare, so it carries none.
            sigma_kg=0.0 if name == "payload" else 0.15 * m,
            tier="L1", source="energy.weight_budget", basis="approx"))
    return items


# The fraction used ONLY when nothing is known about any input's uncertainty.
# It is not an uncertainty and `energy_report` never presents it as one: it is
# reported with `sigma_basis == SIGMA_PLACEHOLDER` so a reader, a badge and the
# provenance DB's "one-sigma" column all see that no evidence stands behind it.
# It lives here, once, so that the placeholder cannot be re-declared at a call
# site and drift away from the string that disowns it.
WH_PER_NM_PLACEHOLDER_SIGMA_FRAC = 0.30

SIGMA_PLACEHOLDER = "placeholder"     # no input sigma was supplied — DO NOT USE
SIGMA_PROPAGATED = "propagated"       # every contributing input carried a sigma
SIGMA_PROPAGATED_LOWER_BOUND = "propagated-lower-bound"   # some input did not


@dataclass(frozen=True)
class EnergyReport:
    speed: float
    prop_power_w: float        # electrical power at cruise
    wh_per_nm: float
    solar_kwh_day: float
    net_kwh_day: float         # solar - hotel - propulsion(cruise_hours)
    range_solar_nm_day: float  # miles/day sustainable on solar alone
    range_battery_nm: float
    # One-sigma on wh_per_nm, and WHERE IT CAME FROM. The basis is a field and
    # not a comment because it is the only thing that distinguishes a number
    # that can narrow with evidence from one that cannot (gap H1).
    sigma_wh_per_nm: float = 0.0
    sigma_basis: str = SIGMA_PLACEHOLDER


def energy_report(total_resistance_n: float, speed: float, deck_area: float,
                  spec: EnergySpec,
                  resistance_sigma_n: float | None = None,
                  drivetrain_sigma_frac: float | None = None) -> EnergyReport:
    """Cruise energy, with a sigma on Wh/NM that is PROPAGATED where it can be.

    THE LAST BARE SIGMA (gap H1). The badge carried `wh_per_nm * 0.30` — a
    declared fraction of its own value, which is not an uncertainty: it cannot
    narrow when the resistance model improves and it cannot widen when the
    resistance model is outside its regime. Both of those happen in this
    codebase. `resistance.total()` already returns a sigma that PROPAGATES the
    form factor's own uncertainty, and it doubles the band to the size of the
    answer above `FN_MICHELL_MAX`; under a flat 0.30 the Wh/NM badge reported
    the same confidence for a hull the resistance model has declared itself
    unfit to predict.

    Wh/NM is a pure product/quotient of its inputs:

        Wh/NM = R_t * 1852 / (3600 * eta_prop * eta_motor)

    so relative variances add:

        (sigma_wh/wh)^2 = (sigma_R/R)^2 + (sigma_drivetrain/eta)^2

    `resistance_sigma_n` is MEASURED (it comes from `ResistanceResult`).
    `drivetrain_sigma_frac` is the relative one-sigma on `eta_prop*eta_motor`;
    the mission DECLARES those efficiencies and declares no sigma with them, so
    the caller normally has none to pass. When it is absent the result is
    honestly labelled `propagated-lower-bound`: it is the resistance
    contribution alone and the true band is wider by whatever the drivetrain
    contributes. A lower bound with its name on it is a usable number; 0.30 was
    not, in either direction.

    MEASURED — state the configuration, because a sigma quoted at a condition
    the product never runs is this repository's other recurring defect. Test
    hull is `tests/test_phase0.mid_params` (10.0 x 3.2 x 0.55 m), floated by
    `hydrostatics.solve(hull, 0.0)`, default `EnergySpec`:

        U m/s    Fn      valid   Rt N    sigma_R  sigma_R/R   Wh/NM   sigma
        2.5    0.2525    yes     608.1    103.6     0.1703    618.2   105.3
        4.6    0.4645    NO     6662.2   6662.2     1.0000   6773.4  6773.4

    At 2.5 m/s the propagated band is 105.3 Wh/NM against the 185.5 the flat
    0.30 declared — the old badge was 76% too wide and said nothing about why.
    At 4.6 m/s the hull is past `FN_MICHELL_MAX` (0.45), `total_resistance`
    widens sigma to the size of the answer, and the propagated Wh/NM band
    follows it to 100%: the badge now reports that the model has left its
    regime. The flat 0.30 stayed at 0.30 through that transition, i.e. it was
    MORE confident about a prediction the resistance module had disowned than
    about one it stood behind. Passing `drivetrain_sigma_frac=0.10` at 2.5 m/s
    gives 122.1 Wh/NM and the basis becomes plain `propagated`.

    With NO resistance sigma the placeholder is returned and
    `sigma_basis == SIGMA_PLACEHOLDER`. That is the row's own escape hatch and
    it is only acceptable because the report SAYS SO in a field the badge, the
    UI and the DB can all read.
    """
    p_el = total_resistance_n * speed / (spec.prop_efficiency * spec.motor_efficiency)
    wh_nm = p_el * (1852.0 / max(speed, 1e-6)) / 3600.0
    solar = deck_area * spec.panel_packing * spec.panel_eff * spec.solar_yield_kwh_m2_day
    prop_day = p_el * spec.cruise_hours_day / 1000.0
    net = solar - spec.hotel_kwh_day - prop_day
    # A NON-POSITIVE wh_nm IS REFUSED, NOT CLAMPED. `max(wh_nm, 1e-9)` turned
    # "this design consumes nothing per mile" into a range of order 1e12 NM —
    # an unmeasurable quantity scored as a spectacular pass, which is this
    # repository's defect class 1 (LESSONS.md: "an unmeasurable metric is
    # FATAL, never a default"). It could not fire while resistance was the only
    # term, because hull resistance at a positive speed is positive.
    #
    # IT BECOMES REACHABLE THE MOMENT A TRACTION TERM EXISTS. The WindWing work
    # in docs/BUILD-PLAN.md section 10 enters at exactly this line, as a net
    # thrust (resistance minus kite pull), and a kite that fully overcomes
    # resistance drives wh_nm to zero and through it. Guarded now, while the
    # guard can be written calmly, rather than after it has printed a range.
    # NaN AND inf ARE DELIBERATELY NOT CAUGHT HERE, and that is the whole
    # distinction. A non-finite quantity ALREADY has an honest handler: the
    # badge guard downgrades it to L{n}-INVALID and `tier_rank` ranks that at
    # -1, below L0, so it can never be promoted by comparison. Two tests in
    # test_constraints_honest.py inject NaN precisely to prove that path works,
    # and an exception here breaks it — measured, both failed on the first
    # attempt at this guard. `nan <= 0.0` is False, so NaN flows on untouched.
    #
    # Zero and negative had NO handler. That is the gap.
    if wh_nm <= 0.0:
        raise ValueError(
            f"wh_per_nm is {wh_nm!r}: energy per mile must be positive. "
            f"total_resistance_n={total_resistance_n!r}, speed={speed!r}. "
            f"A non-positive value means the caller passed a net thrust that "
            f"already exceeds resistance — report that as a refusal, never as "
            f"an infinite range.")
    kwh_for_prop = max(solar - spec.hotel_kwh_day, 0.0)
    rng_solar = kwh_for_prop * 1000.0 / wh_nm
    rng_batt = spec.battery_kwh * 1000.0 * 0.8 / wh_nm              # 80% DoD

    sigma, basis = wh_per_nm_sigma(wh_nm, total_resistance_n,
                                   resistance_sigma_n, drivetrain_sigma_frac)
    return EnergyReport(speed, p_el, wh_nm, solar, net, rng_solar, rng_batt,
                        sigma, basis)


def wh_per_nm_sigma(wh_per_nm: float, total_resistance_n: float,
                    resistance_sigma_n: float | None,
                    drivetrain_sigma_frac: float | None = None
                    ) -> tuple[float, str]:
    """(sigma, basis) for Wh/NM — the propagation, split out so it is testable.

    Returns the placeholder, LABELLED as one, when there is nothing to
    propagate. It never silently substitutes: a caller that wants a real sigma
    must supply a real input sigma, and a caller that supplies none is told in
    the returned basis string that it did not.
    """
    terms: list[float] = []
    lower_bound = False

    r = abs(float(total_resistance_n))
    if (resistance_sigma_n is not None
            and math.isfinite(float(resistance_sigma_n)) and r > 0.0):
        terms.append(abs(float(resistance_sigma_n)) / r)
    else:
        lower_bound = True

    if (drivetrain_sigma_frac is not None
            and math.isfinite(float(drivetrain_sigma_frac))):
        terms.append(abs(float(drivetrain_sigma_frac)))
    else:
        lower_bound = True

    if not terms:
        return (abs(float(wh_per_nm)) * WH_PER_NM_PLACEHOLDER_SIGMA_FRAC,
                SIGMA_PLACEHOLDER)
    rel = math.sqrt(sum(t * t for t in terms))
    return (abs(float(wh_per_nm)) * rel,
            SIGMA_PROPAGATED_LOWER_BOUND if lower_bound else SIGMA_PROPAGATED)
