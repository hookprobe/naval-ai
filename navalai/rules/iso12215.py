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

from ..limits import FRAME_SPACING_M, STOCK_PLY_THICKNESS_M
from . import RuleFinding
from .review import basis_for

SIGMA_D_OKOUME = 15.0     # N/mm^2 design bending stress, marine okoume ply

# The panel short span is the frame spacing, and it is declared ONCE, in
# limits.py. It used to be a bare 400.0 default here while engineer.py built to
# 1.4 m — see the FRAME_SPACING_M comment there for what that cost.
DEFAULT_SPAN_MM = FRAME_SPACING_M * 1e3


def design_pressure_bottom(mldc_kg: float) -> float:
    return max(10.0, 2.4 * mldc_kg ** 0.33 + 20.0)


def required_thickness_mm(mldc_kg: float, span_mm: float = DEFAULT_SPAN_MM,
                          k2: float = 0.5, sigma_d: float = SIGMA_D_OKOUME,
                          k_curve: float = 1.0) -> float:
    p = design_pressure_bottom(mldc_kg)
    return span_mm * k_curve * math.sqrt(p * k2 / (1000.0 * sigma_d))


def select_stock_thickness_m(mldc_kg: float, span_mm: float = DEFAULT_SPAN_MM,
                             sigma_d: float = SIGMA_D_OKOUME,
                             k_curve: float = 1.0) -> float:
    """Thinnest STOCK sheet [m] that satisfies the bottom-panel requirement.

    This is the fix for the defect the 2026-08-05 audit called the flagship
    case of "a number declared twice": the platform DECLARED a 15 mm sheet and
    the rule DERIVED 18.24 mm for the same 6 t boat, and the two never met
    because the only place they could have met — the demo — hand-passed a third
    number (20 mm) that made the check pass.

    Making the build thickness a FUNCTION of the rule removes the contradiction
    by construction: the weight model, the bend-radius limit and the scantling
    verdict now all read the same sheet, and a boat that needs thicker ply
    simply gets heavier, which is the truth.

    Raises when no stock sheet is thick enough, rather than silently returning
    the thickest one — an unbuildable panel is a finding, not a rounding.
    """
    t_req_mm = required_thickness_mm(mldc_kg, span_mm, sigma_d=sigma_d,
                                     k_curve=k_curve)
    for t in STOCK_PLY_THICKNESS_M:
        if t * 1e3 >= t_req_mm:
            return t
    raise ValueError(
        f"ISO 12215-5 wants {t_req_mm:.1f} mm at mLDC {mldc_kg:.0f} kg and "
        f"{span_mm:.0f} mm span; thickest stock sheet is "
        f"{max(STOCK_PLY_THICKNESS_M) * 1e3:.0f} mm. Reduce the frame spacing "
        f"or change material — do not round the requirement down.")


def assess(mldc_kg: float, provided_mm: float, span_mm: float = DEFAULT_SPAN_MM,
           sigma_d: float = SIGMA_D_OKOUME) -> list[RuleFinding]:
    p = design_pressure_bottom(mldc_kg)
    t_req = required_thickness_mm(mldc_kg, span_mm, sigma_d=sigma_d)
    return [
        RuleFinding("R-PBM", "ISO 12215-5 (bottom design pressure, displ. mode)",
                    basis_for("R-PBM"), True, p, p, "kN/m^2",
                    f"mLDC {mldc_kg:.0f} kg"),
        RuleFinding("R-TBM", "ISO 12215-5 (plywood bottom panel thickness)",
                    basis_for("R-TBM"), provided_mm >= t_req, provided_mm, t_req, "mm",
                    f"span {span_mm:.0f} mm, sigma_d {sigma_d} N/mm^2, flat panel"),
    ]
