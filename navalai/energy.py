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


@dataclass(frozen=True)
class EnergyReport:
    speed: float
    prop_power_w: float        # electrical power at cruise
    wh_per_nm: float
    solar_kwh_day: float
    net_kwh_day: float         # solar - hotel - propulsion(cruise_hours)
    range_solar_nm_day: float  # miles/day sustainable on solar alone
    range_battery_nm: float


def energy_report(total_resistance_n: float, speed: float, deck_area: float,
                  spec: EnergySpec) -> EnergyReport:
    p_el = total_resistance_n * speed / (spec.prop_efficiency * spec.motor_efficiency)
    wh_nm = p_el * (1852.0 / max(speed, 1e-6)) / 3600.0
    solar = deck_area * spec.panel_packing * spec.panel_eff * spec.solar_yield_kwh_m2_day
    prop_day = p_el * spec.cruise_hours_day / 1000.0
    net = solar - spec.hotel_kwh_day - prop_day
    kwh_for_prop = max(solar - spec.hotel_kwh_day, 0.0)
    rng_solar = kwh_for_prop * 1000.0 / max(wh_nm, 1e-9)
    rng_batt = spec.battery_kwh * 1000.0 * 0.8 / max(wh_nm, 1e-9)   # 80% DoD
    return EnergyReport(speed, p_el, wh_nm, solar, net, rng_solar, rng_batt)
