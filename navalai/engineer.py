"""Engineer-agent metrics (original plan, Phase 2): material requirements,
panel counts, interior volume, build hours, manufacturing efficiency.

Coefficients marked approx (amateur plywood-epoxy practice values) — same
declared-basis discipline as the rules tier.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import Hull

SHEET_M2 = 1.22 * 2.44            # standard marine-ply sheet
WASTE_FACTOR = 1.30               # nesting waste, approx
EPOXY_KG_PER_M2 = 1.4             # sheathing + fillets + coats, approx
HOURS_PER_M2 = 15.0               # amateur build, approx
BULKHEAD_SPACING_M = 1.4


@dataclass(frozen=True)
class EngineerReport:
    panel_count: int
    bulkheads: int
    panel_area_m2: float          # developable shell + deck
    ply_sheets: int
    epoxy_kg: float
    interior_volume_m3: float     # enclosed volume above WL, below sheer
    build_hours: float
    basis: str


def assess(hull: Hull, wl: float = 0.0) -> EngineerReport:
    shell = hull.wetted_surface(float(hull.z_sheer.max()))   # full shell girth
    deck = hull.deck_area()
    area = shell + deck

    # panels: bottom pair + topside pair + transom + deck panels (deck split
    # into sheet-length segments) + bulkheads
    lwl = float(hull.x[-1])
    deck_panels = max(2, int(np.ceil(lwl / 2.44)) * 2)
    bulkheads = max(2, int(np.floor(lwl / BULKHEAD_SPACING_M)))
    panels = 2 + 2 + 1 + deck_panels + bulkheads

    # interior: enclosed volume between load WL and sheer
    b_avg = hull.y_sheer            # half-breadth at sheer
    h = np.maximum(hull.z_sheer - np.maximum(hull.z_keel, wl), 0.0)
    interior = 2.0 * float(np.trapezoid(b_avg * h, hull.x)) * 0.85  # fit-out loss

    sheets = int(np.ceil(area * WASTE_FACTOR / SHEET_M2))
    hours = HOURS_PER_M2 * area * (1.0 + 0.015 * panels)
    return EngineerReport(
        panel_count=int(panels), bulkheads=bulkheads,
        panel_area_m2=round(area, 1), ply_sheets=sheets,
        epoxy_kg=round(EPOXY_KG_PER_M2 * area, 1),
        interior_volume_m3=round(interior, 2),
        build_hours=round(hours),
        basis="approx: amateur ply-epoxy practice values, declared not certified",
    )
