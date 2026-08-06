"""One weight model, one truth: mass items, and the aggregate they produce.

BuildPlan2 requires tiers E (ergonomics) and F (flotation) to "feed masses/CG
back into L1 stability — one weight model, one truth". They cannot, because the
model they would feed does not exist yet: `energy.weight_budget` returns five
scalar buckets and a single hard-coded KG built from depth fractions. There is
no LCG anywhere in the codebase, no TCG, and therefore no way for a berth on
the port side or a foam block in the bow to affect anything.

This module is the missing spine. A mass item has a mass AND a position, so:

  - moving 500 kg aft trims the boat instead of being invisible
  - a galley to port and a berth to starboard produce a real list
  - tier F's foam blocks contribute buoyant volume, not just weight
  - slack tanks raise G virtually (free-surface effect), which is the
    difference between passing and failing a category GM floor

COORDINATES follow grammar.py: x = 0 at the transom and x = LWL at the stem,
z = 0 at the design waterline (down is negative), y = 0 on centreline with
starboard positive. Callers work in that hull frame; the aggregate converts to
the above-keel frame that `hydrostatics.gm` wants, so the +t_design offset
lives in exactly one place.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Tiers that may declare mass, matching the ladder and the provenance DB.
_TIERS = ("L1", "E", "F", "R")


@dataclass(frozen=True)
class MassItem:
    """One declared mass at one declared position.

    `sigma_kg` is required by honesty rule 1 (every quantity carries value,
    tier and sigma). Use 0.0 only for a mass that is genuinely exact.
    """

    id: str
    mass_kg: float
    x_m: float                      # hull frame: 0 at transom, +forward
    z_m: float                      # hull frame: 0 at design WL, +up
    y_m: float = 0.0                # 0 on centreline, +starboard
    sigma_kg: float = 0.0
    tier: str = "L1"
    source: str = ""
    basis: str = "approx"           # 'approx' | 'standard' | 'purchased'
    # Tier F: buoyant volume and material, so a foam block or a plywood panel
    # can contribute the (SG-1)/SG term of the USCG method rather than only
    # its weight.
    volume_m3: float = 0.0
    material: str = ""
    # Tanks: a SLACK tank's free surface raises G virtually by rho*i_t/disp.
    fluid_rho: float = 0.0
    fsm_i_t_m4: float = 0.0         # transverse second moment of the free surface
    slack: bool = False

    def __post_init__(self) -> None:
        if self.tier not in _TIERS:
            raise ValueError(f"unknown tier {self.tier!r}; expected {_TIERS}")
        if self.mass_kg < 0:
            raise ValueError(f"{self.id}: negative mass {self.mass_kg}")
        if self.sigma_kg < 0:
            raise ValueError(f"{self.id}: negative sigma {self.sigma_kg}")
        if self.slack and self.fsm_i_t_m4 <= 0:
            raise ValueError(f"{self.id}: slack tank needs fsm_i_t_m4 > 0")


@dataclass(frozen=True)
class MassAggregate:
    total_kg: float
    sigma_kg: float
    lcg_m: float                    # hull frame
    tcg_m: float
    vcg_m: float                    # hull frame (z, so normally negative-ish)
    free_surface_moment: float      # sum rho * i_t over SLACK tanks [kg m^2]
    by_tier: dict = field(default_factory=dict)
    n_items: int = 0

    def vcg_above_keel(self, t_design: float) -> float:
        """KG for `hydrostatics.gm`, which measures from the keel plane."""
        return self.vcg_m + t_design

    def free_surface_correction(self) -> float:
        """Virtual rise of G from slack tanks [m]: sum(rho*i_t) / displacement."""
        return self.free_surface_moment / max(self.total_kg, 1e-9)


def aggregate(items: list[MassItem]) -> MassAggregate:
    """Total mass, its centre, and the free-surface moment.

    Sigmas combine in quadrature (independent items), which is the honest
    default; correlated uncertainty would need a covariance the callers do not
    have.
    """
    if not items:
        raise ValueError("no mass items: refusing to invent a displacement")
    total = math.fsum(i.mass_kg for i in items)
    if total <= 0:
        raise ValueError("total mass is zero")

    lcg = math.fsum(i.mass_kg * i.x_m for i in items) / total
    tcg = math.fsum(i.mass_kg * i.y_m for i in items) / total
    vcg = math.fsum(i.mass_kg * i.z_m for i in items) / total
    sigma = math.sqrt(math.fsum(i.sigma_kg ** 2 for i in items))
    fsm = math.fsum(i.fluid_rho * i.fsm_i_t_m4 for i in items if i.slack)

    by_tier: dict = {}
    for i in items:
        t = by_tier.setdefault(i.tier, {"mass_kg": 0.0, "n": 0})
        t["mass_kg"] += i.mass_kg
        t["n"] += 1

    return MassAggregate(total_kg=total, sigma_kg=sigma, lcg_m=lcg, tcg_m=tcg,
                         vcg_m=vcg, free_surface_moment=fsm, by_tier=by_tier,
                         n_items=len(items))


def trim_angle_deg(agg: MassAggregate, lcb_m: float, disp_kg: float,
                   gm_l_m: float) -> float | None:
    """Static trim from the LCG-LCB lever [deg], positive = bow down.

    theta = (LCG - LCB) / GM_L for small angles. Returns **None** when GM_L is
    not positive-finite, because at that point the equilibrium this formula
    solves does not exist and there is no trim angle to report.

    IT USED TO RETURN 0.0, AND 0.0 IS THE BEST POSSIBLE ANSWER. Gap E11.
    MEASURED with an LCG-LCB lever of 4.0 m against `limits.TRIM_LIMIT_DEG`:

        GM_L = +40 m   ->  +5.71 deg   g['trim'] = +3.710   VIOLATED
        GM_L =   0 m   ->  +0.00 deg   g['trim'] = -2.000   FEASIBLE
        GM_L = -500 m  ->  +0.00 deg   g['trim'] = -2.000   FEASIBLE

    So a hull that had just gone LONGITUDINALLY UNSTABLE — the one state where
    trim is a real engineering problem — satisfied the trim constraint more
    comfortably than a merely badly-balanced one, and NSGA-II was free to
    descend into it. Mapping "undefined" onto "ideal" is the whole defect; the
    caller must treat None as a violation, never as a pass.
    """
    if not math.isfinite(gm_l_m) or gm_l_m <= 0:
        return None
    val = math.degrees(math.atan((agg.lcg_m - lcb_m) / gm_l_m))
    return val if math.isfinite(val) else None
