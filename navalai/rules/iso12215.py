"""ISO 12215-5 — simplified plywood bottom-panel scantling check.

Displacement-mode motor craft path:
  design pressure   P_BM = max(10, 2.4 * mLDC^0.33 + 20)   [kN/m^2]
  required thickness t = b * kC * sqrt(P * k2 / (1000 * sigma_d))   [mm]
    b        panel short span [mm] (frame spacing)
    k2       aspect-ratio coefficient (0.308..0.5; 0.5 for long panels)
    sigma_d  design bending stress of the ply [N/mm^2]
    kC       curvature correction (1.0 for flat developable panels)

basis='approx': formula structure follows the 12215-5 displacement-mode path;
coefficients await licensed-text parity review (Gate 6). Mechanics exact.
"""

from __future__ import annotations

import math

from . import RuleFinding

SIGMA_D_OKOUME = 15.0     # N/mm^2 design bending stress, marine okoume ply


def design_pressure_bottom(mldc_kg: float) -> float:
    return max(10.0, 2.4 * mldc_kg ** 0.33 + 20.0)


def required_thickness_mm(mldc_kg: float, span_mm: float = 400.0,
                          k2: float = 0.5, sigma_d: float = SIGMA_D_OKOUME,
                          k_curve: float = 1.0) -> float:
    p = design_pressure_bottom(mldc_kg)
    return span_mm * k_curve * math.sqrt(p * k2 / (1000.0 * sigma_d))


def assess(mldc_kg: float, provided_mm: float, span_mm: float = 400.0,
           sigma_d: float = SIGMA_D_OKOUME) -> list[RuleFinding]:
    p = design_pressure_bottom(mldc_kg)
    t_req = required_thickness_mm(mldc_kg, span_mm, sigma_d=sigma_d)
    return [
        RuleFinding("R-PBM", "ISO 12215-5 (bottom design pressure, displ. mode)",
                    "approx", True, p, p, "kN/m^2",
                    f"mLDC {mldc_kg:.0f} kg"),
        RuleFinding("R-TBM", "ISO 12215-5 (plywood bottom panel thickness)",
                    "approx", provided_mm >= t_req, provided_mm, t_req, "mm",
                    f"span {span_mm:.0f} mm, sigma_d {sigma_d} N/mm^2, flat panel"),
    ]
