"""Engineer-agent metrics (original plan, Phase 2): material requirements,
panel counts, interior volume, build hours, manufacturing efficiency — plus a
LINE-ITEM BILL OF MATERIALS derived from the real nesting layout.

Coefficients marked approx (amateur plywood-epoxy practice values) — same
declared-basis discipline as the rules tier.

WHAT CHANGED AND WHY (gaps G2/G3/C12)
-------------------------------------
`ply_sheets` used to be `ceil(area * 1.30 / SHEET_M2)` — an area divided by a
sheet, times a DECLARED nesting waste factor. Three things were wrong with it:

  1. The 1.30 was an assertion about a layout that existed and could have been
     measured. `unroll.export_dxf` was stacking panels 10.05 x 1.62 m and
     10.54 x 1.44 m that fit on NO 1.22 x 2.44 m sheet, so the layout the 1.30
     described was not buildable in the first place.
  2. `area` was shell + deck ONLY, while the same report counted 7 bulkheads
     and 18 frames. MEASURED on the reference hull: 35 sheets covered 40
     "panels" of which 25 consumed no material in the estimate at all.
  3. Nothing forced the thickness split. Bottom and topside can be different
     stock sheets (the bottom is DERIVED from ISO 12215-5), and you cannot cut
     a 21 mm part out of a 15 mm sheet — so the sheet count is a sum over
     thickness groups, not one division.

`ply_sheets` is now a COUNT of the sheets the packer actually opened, and the
BOM says which sheet each part lands on. There is no waste factor left to
declare: the waste is `1 - nest_utilisation`, and it is measured.

MEASURED on the reference hull, old vs new: **35 sheets -> 68**, 104.2 m^2 of
stock -> 202.4 m^2. And note WHERE the old number went wrong, because it is not
only where it looks: the layout's own sheet-to-part ratio comes out at 1.36
against the declared 1.30, so the waste factor was not far off. The bigger error
was the AREA it multiplied — 79.5 m^2 of shell and deck against the 148.6 m^2 of
plywood the boat actually consumes once its transom, its seven bulkheads and the
scarph flanges on every joint are cut.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .energy import shell_area_m2
from .geometry import Hull
from .limits import FRAME_SPACING_M, PLY_THICKNESS_M
from .unroll import SHEET_L_M, SHEET_M2, SHEET_W_M, Part  # noqa: F401
from .unroll import (hull_panels, min_strakes, nest, rect_parts,
                     split_panel)

EPOXY_KG_PER_M2 = 1.4             # sheathing + fillets + coats, approx
HOURS_PER_M2 = 15.0               # amateur build, approx
BULKHEAD_SPACING_M = 1.4
FRAME_WEB_M = 0.10                # laminated ring-frame web depth, approx


@dataclass(frozen=True)
class BomLine:
    """One purchasable/cuttable line item."""

    part: str
    qty: int
    material: str
    thickness_mm: float
    area_m2: float
    source_panel: str
    sheet: int | None          # 1-based sheet it nests on; None = not sheet goods
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "part": self.part, "qty": self.qty, "material": self.material,
            "thickness_mm": round(self.thickness_mm, 1),
            "area_m2": round(self.area_m2, 4),
            "source_panel": self.source_panel, "sheet": self.sheet,
            "note": self.note,
        }


@dataclass(frozen=True)
class EngineerReport:
    panel_count: int
    bulkheads: int
    frames: int                   # intermediate transverse frames, at FRAME_SPACING_M
    panel_area_m2: float          # developable shell + deck
    ply_sheets: int               # COUNTED off the nesting layout
    epoxy_kg: float
    interior_volume_m3: float     # enclosed volume above WL, below sheer
    build_hours: float
    basis: str
    bom: tuple[BomLine, ...] = ()
    nest_utilisation: float = 0.0  # placed part footprint / sheet area
    sheet_area_m2: float = 0.0
    bottom_thickness_mm: float = PLY_THICKNESS_M * 1e3


# Extra strake counts tried beyond the minimum. MEASURED on the reference
# hull, sheets at utilisation:
#     1 trial (the fewest-seams layout)  81 at 57.1%   0.03 s
#     2                                  72 at 66.9%   0.06 s
#     4                                  68 at 76.8%   0.15 s
#     8                                  68 at 76.8%   0.45 s
# It saturates at 4 and 5 costs 0.21 s. Fewest seams is what a builder wants
# and fewest sheets is what a budget wants, and this is the only place the two
# are traded, so the trade is written down here rather than assumed.
STRAKE_TRIALS = 5


def _shell_parts(hull: Hull, t_bottom: float, t_other: float,
                 extra_strakes: int = 0) -> list[Part]:
    """Split the two developed shell panels; each is built PORT AND STARBOARD."""
    out: list[Part] = []
    for panel in hull_panels(hull):
        t = t_bottom if panel.name.startswith("bottom") else t_other
        k = min_strakes(panel, t) + extra_strakes
        for p in split_panel(panel, t, strakes=k):
            # `replace`, not a hand-built Part: rebuilding it by hand dropped
            # `foot_w`/`foot_h` and the packer silently fell back to the
            # unflanged box, which is the same splitter/packer disagreement
            # that Part.foot_* exists to prevent.
            out.append(replace(p, qty=2, note=p.note + "; port + stbd"))
    return out


def assess(hull: Hull, wl: float = 0.0,
           mldc_kg: float | None = None) -> EngineerReport:
    """Materials, layout and BOM.

    `mldc_kg` lets the bottom-panel thickness come from ISO 12215-5 rather than
    the nominal stock sheet — the same DERIVED-not-declared discipline
    `limits.PLY_THICKNESS_M` documents. Omitting it uses the nominal sheet and
    the BOM says so.
    """
    # Gap C9: the shell area is INTEGRATED to the sheer, once, in
    # `energy.shell_area_m2` — the weight path used to reach the same quantity
    # through a bare `wetted_surface(0.0) * 1.6`, so the boat this module planked
    # and the boat the L1 weight budget massed were two different boats (5.2%
    # apart on the reference hull, up to 76% over the grammar box).
    shell = shell_area_m2(hull)                              # full shell girth
    deck = hull.deck_area()
    area = shell + deck

    lwl = float(hull.x[-1])
    bulkheads = max(2, int(np.floor(lwl / BULKHEAD_SPACING_M)))
    # The scantling rule sizes the bottom panel for a span of FRAME_SPACING_M.
    # Nothing used to BUILD that span: bulkheads sat 1.4 m apart with no
    # intermediate structure, so the rule and the build described different
    # boats — at 1.4 m the same rule wants 63.8 mm of plywood instead of 21.
    # The frames the panel thickness presumes are now counted and built.
    stations = max(1, int(np.floor(lwl / FRAME_SPACING_M)))
    frames = max(0, stations - bulkheads)

    t_other = PLY_THICKNESS_M
    if mldc_kg is not None:
        from .rules.iso12215 import select_stock_thickness_m
        t_bottom = select_stock_thickness_m(mldc_kg)
        t_note = f"ISO 12215-5 derived at mLDC {mldc_kg:.0f} kg"
    else:
        t_bottom = PLY_THICKNESS_M
        t_note = "nominal stock sheet (no mLDC given — NOT rule-derived)"

    # transom: the section at station 0, as a blank
    y_t = float(hull.y_sheer[0])
    h_t = float(hull.z_sheer[0] - hull.z_keel[0])
    fixed = rect_parts("transom", max(2.0 * y_t, 1e-3), max(h_t, 1e-3),
                       t_other, note="blank; corner offcut is waste")

    # deck: a strip of the true deck area, laid over the full length
    fixed += rect_parts("deck", lwl, max(deck / max(lwl, 1e-9), 1e-3), t_other,
                        note="deck area spread over LWL")

    # bulkheads: solid ply, cut from a blank the size of the section they close
    xs = np.linspace(0.0, lwl, bulkheads + 2)[1:-1]
    for k, xv in enumerate(xs, start=1):
        sec = np.asarray(hull._section_at(float(xv)), dtype=float)
        # BY MEANING, NOT BY INDEX. This read `sec[1]` and `sec[2]` as the
        # chine and the sheer, which they were for as long as every section had
        # exactly three points. Plate P2 made the section a shape function —
        # 257 points on a radiused bilge — so `sec[1]` and `sec[2]` became two
        # samples a few millimetres up from the keel and a bulkhead blank came
        # out ~1 mm wide, which `nest()` then refuses as "no feasible layout".
        # The widest half-breadth and the keel-to-sheer depth are what the
        # blank is, and for a hard chine these are arithmetically the old
        # expressions. Same defect, same day, as `export._station_wires`.
        b = max(2.0 * float(sec[:, 0].max()), 1e-3)
        d = max(float(sec[:, 1].max() - sec[:, 1].min()), 1e-3)
        fixed += rect_parts(f"bulkhead-{k}", b, d, t_other,
                            note=f"station x={xv:.2f} m; blank, corners waste")

    # The strake count is a real layout choice, not a constant: fewest seams
    # and fewest sheets pull in opposite directions. Search it and keep the
    # best layout, so the reported sheet count cannot be inflated by an
    # arbitrary first guess any more than it could be deflated by a factor.
    # A ROUND BILGE IS NOT A NESTING FAILURE, AND SAYING SO WAS A LIE OF
    # CATEGORY (2026-08-13). `unroll.hull_panels` REFUSES `roundness > 0` —
    # a filleted bilge is doubly curved and not developable from flat sheet,
    # which is a fact about the material and not a limitation of the unroller.
    # That refusal is a `ValueError`, this loop swallowed every `ValueError`,
    # and the hull came out the other end as "no feasible nesting layout for
    # this hull", i.e. as a PACKING problem. MEASURED on
    # `sample_valid(3, MissionSpec(), seed=0)[0]` (roundness 0.981): the
    # unroller's own sentence — "take this hull to a mould, not a cutter" —
    # was replaced by one that sends the reader to look at sheet sizes.
    # The refusal is raised where it is made.
    from .unroll import hull_panels as _hp                     # noqa: F401
    if hull.roundness > 0.0:
        _hp(hull)                                              # raises, with the reason
    parts, layout = None, None
    for extra in range(STRAKE_TRIALS):
        try:
            cand = _shell_parts(hull, t_bottom, t_other, extra) + fixed
            lay = nest(cand)
        except ValueError:
            continue
        if layout is None or (lay.sheets, -lay.utilisation()) < (
                layout.sheets, -layout.utilisation()):
            parts, layout = cand, lay
    if layout is None:
        raise ValueError("no feasible nesting layout for this hull")

    # interior: enclosed volume between load WL and sheer
    b_avg = hull.y_sheer            # half-breadth at sheer
    h = np.maximum(hull.z_sheer - np.maximum(hull.z_keel, wl), 0.0)
    interior = 2.0 * float(np.trapezoid(b_avg * h, hull.x)) * 0.85  # fit-out loss

    sheet_of = {pl.part: pl.sheet + 1 for pl in layout.placements}
    bom: list[BomLine] = []
    for p in parts:
        for k in range(p.qty):
            label = p.name if k == 0 else f"{p.name}_{k + 1}"
            note = p.note
            if p.source_panel.startswith("bottom"):
                note = f"{note}; thickness {t_note}"
            bom.append(BomLine(
                part=label, qty=1, material=p.material,
                thickness_mm=p.thickness_m * 1e3,
                area_m2=p.area_m2() + p.scarph_m2,
                source_panel=p.source_panel, sheet=sheet_of.get(label),
                note=note))

    # Frames are NOT sheet goods. Counting a 2.5 x 1.0 m blank per ring frame
    # would inflate the sheet count with a fiction; they are laminated timber
    # ring frames and are quantified in linear metres of their own girth.
    girth = shell / lwl        # same integrated shell area, not a third copy
    for k in range(frames):
        bom.append(BomLine(
            part=f"frame-{k + 1}", qty=1, material="laminated timber",
            thickness_mm=FRAME_WEB_M * 1e3, area_m2=girth * FRAME_WEB_M,
            source_panel="frames", sheet=None,
            note=f"ring frame, ~{girth:.2f} m girth x {FRAME_WEB_M * 1e3:.0f} mm "
                 f"web; not cut from sheet stock"))

    # STRUCTURAL ITEMS, not cut pieces. The layout now knows the real piece
    # count (143 on the reference hull) and feeding THAT into the complexity
    # term would take build_hours from 1908 to 3750 — but the 0.015 coefficient
    # was declared per PANEL, and silently repurposing a coefficient for a
    # different driver is the same defect as declaring a number twice. The
    # count is derived from the layout (deck tiles are counted, not assumed at
    # 2.44 m) and the driver is unchanged.
    deck_tiles = sum(1 for p in fixed if p.source_panel == "deck")
    panels = 2 * 2 + 1 + deck_tiles + bulkheads + frames
    hours = HOURS_PER_M2 * area * (1.0 + 0.015 * panels)
    return EngineerReport(
        panel_count=int(panels), bulkheads=bulkheads, frames=frames,
        panel_area_m2=round(area, 1), ply_sheets=layout.sheets,
        epoxy_kg=round(EPOXY_KG_PER_M2 * area, 1),
        interior_volume_m3=round(interior, 2),
        build_hours=round(hours),
        basis="approx: amateur ply-epoxy practice values, declared not "
              "certified; ply_sheets COUNTED off the nesting layout, not a "
              "waste factor",
        bom=tuple(bom),
        nest_utilisation=round(layout.utilisation(), 4),
        sheet_area_m2=round(layout.sheets * SHEET_M2, 2),
        bottom_thickness_mm=round(t_bottom * 1e3, 1),
    )
