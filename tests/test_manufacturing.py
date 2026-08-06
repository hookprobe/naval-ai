"""Gate 6M — the manufacturing back end, against the bars it actually claims.

Every test here names the finding it exists to stop coming back (gap register
section G, BuildPlan3 R7):

  G2  there was no nesting, only stacking — the two hull panels fit on NO sheet
  G3  no BOM — three aggregate scalars, no line items, no panel->sheet map
  G4  the refold was never tested — Gate 6's clause was prose
  G5  `dev_error_rel` could not fail — it is O(h^2) for ANY smooth surface
  G6  the exported solid was not the validated hull — 12 stations vs 41
  A5  the export boundary enforced nothing (`refuse_unvalidated` had no test)
  C12 `WASTE_FACTOR = 1.30` asserted a nesting waste the layout could measure
"""

import numpy as np
import pytest

from navalai import engineer
from navalai.engineer import assess
from navalai.geometry import Hull
from navalai.unroll import (SCARPH_RATIO, SHEET_L_M, SHEET_M2, SHEET_W_M,
                            develop, export_dxf, hull_panels, min_area_rect,
                            nest, parse_dxf_polylines, refold,
                            refold_deviation_mm, split_panel)
from tests.test_phase0 import mid_params

# The bar Gate 6 owes: a panel that refolds this far off the hull is a panel
# whose seam you cannot fair. 5 mm is a fillable gap on a 10 m panel and is
# already generous; it is NOT tuned to what the hull happens to achieve, which
# is 28x and 45x worse. See test_gate6_refold_clause_is_red_on_the_hull.
REFOLD_BAR_MM = 5.0


# ---------------- fixtures: surfaces whose developability we KNOW ----------

def _true_cylinder(n=41):
    """Rulings all parallel: developable, and the textbook easy case."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))], axis=1)
    return A, A + np.array([5.0, 0.0, 0.0])


def _cone(n=41):
    """Rulings all concurrent: developable, and the case a twist metric must
    also pass, or it is only detecting non-parallel rulings."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))], axis=1)
    return A, np.repeat(np.array([[5.0, 0.0, 1.0]]), n, axis=0)


def _hypar(n=41):
    """z = 1.5 x y. Doubly ruled, Gaussian curvature strictly negative, and
    NOT developable by any definition — the negative control."""
    x = np.linspace(0, 2, n)
    A = np.stack([x, np.zeros(n), np.zeros(n)], axis=1)
    B = np.stack([x, np.ones(n), 1.5 * x], axis=1)
    return A, B


def _old_cylinder_fixture(n=41):
    """The surface tests/test_stageF.py called 'a cylindrical surface'."""
    th = np.linspace(0, np.pi / 2, n)
    A = np.stack([np.linspace(0, 5, n), np.zeros(n), np.zeros(n)], axis=1)
    B = A + np.stack([np.zeros(n), 2 * np.sin(th), 2 * (1 - np.cos(th))],
                     axis=1)
    return A, B


# ---------------- G5: a developability metric that CAN fail ---------------

@pytest.mark.parametrize("fixture", [_true_cylinder, _cone])
def test_true_developables_have_zero_ruling_twist(fixture):
    """POSITIVE CONTROL. A cylinder and a cone are developable, so
    det(A', r, r') must vanish — to machine precision, not 'small'."""
    p = develop(*fixture(), "dev")
    assert p.twist_max < 1e-12, f"twist {p.twist_max:.3e}"
    assert p.dev_error_rel < 1e-9


def test_hypar_negative_control_fails_developability():
    """NEGATIVE CONTROL, gap G5. A metric with no negative control is not a
    metric. z = 1.5xy is doubly ruled and emphatically non-developable; the
    twist criterion reads 1.000 max / 0.555 median on it.

    And the same fixture PASSES the old metric's bars, which is the whole
    finding: `dev_error_rel` is a per-quad chord residual, i.e. O(h^2)
    discretisation error for ANY smooth surface."""
    p = develop(*_hypar(41), "hypar")
    assert p.twist_max > 0.9 and p.twist_median > 0.5
    # the two bars this repository actually used, both cleared by 7.7x and 77x
    assert p.dev_error_rel < 5e-3      # tests/test_stageF cylinder bar
    assert p.dev_error_rel < 5e-2      # tests/test_stageF hull bar
    assert p.dev_error_rel == pytest.approx(6.46e-4, rel=0.05)


def test_refining_the_polyline_hides_the_hypar_but_not_its_twist():
    """The gap register proposed a refinement-convergence test as the fix for
    G5. MEASURED, it does not work: the hypar's chord residual converges at
    O(h^2.01) — the same rate as the genuinely developable-in-the-mean hull
    bottom panel — so 'the residual plateaus' does not separate them. The
    ruling twist is what does: it is INVARIANT under refinement."""
    coarse = develop(*_hypar(41), "hypar")
    fine = develop(*_hypar(161), "hypar")
    order = np.log(coarse.dev_error_rel / fine.dev_error_rel) / np.log(4.0)
    assert 1.8 < order < 2.2, f"order {order:.2f}"
    assert fine.dev_error_rel < 1e-4          # refined away to nothing
    assert fine.twist_median == pytest.approx(coarse.twist_median, rel=1e-6)


def test_the_old_cylinder_fixture_was_a_conoid():
    """RECORDED. `test_cylinder_develops_exactly` called its fixture 'a
    cylindrical surface' and asserted dev_error_rel < 5e-3 on it. Its rulings
    are chords from a straight axis to a quarter circle — a CONOID, whose
    ruling direction rotates, so it is not developable either: twist median
    0.383. The positive control and the negative control were the same kind of
    object, and the metric could tell neither of them from a cylinder."""
    p = develop(*_old_cylinder_fixture(41), "conoid")
    assert p.twist_median == pytest.approx(0.383, abs=0.02)
    assert p.dev_error_rel < 5e-3             # it passed the old bar


def test_hull_panel_twist_is_recorded_not_blessed():
    """MEASURED on the reference hull, and NOT softened (honesty rule 6).

    The BOTTOM panel is developable except in the bow warp: median 3.8e-15,
    max 0.288 concentrated where the deadrise warps. The TOPSIDE panel is not
    developable anywhere — median 0.617 — and is indistinguishable from the
    hypar negative control above. That is a consequence of taking the rulings
    at constant station x, which makes r lie in the y-z plane; developable
    hull design solves for slanted rulings and `hull_panels` does not.

    No bar is set here that the topside would pass and the hypar would fail,
    because there is no such bar."""
    bottom, topside = hull_panels(Hull(mid_params()))
    assert bottom.twist_median < 1e-9
    assert 0.2 < bottom.twist_max < 0.4
    assert 0.4 < topside.twist_median < 0.8
    assert topside.twist_max > 0.9
    assert topside.twist_median > develop(*_hypar(41), "h").twist_median * 0.9


# ---------------- G4: the refold ------------------------------------------

@pytest.mark.parametrize("fixture", [_true_cylinder, _cone])
def test_refold_of_a_true_developable_is_exact(fixture):
    """Gap G4: no code mapped 2-D back to 3-D, so Gate 6's clause 'exported
    panels re-fold to the hull within tolerance' was untested prose.

    The mechanism has to be shown correct before its verdict on the hull means
    anything: rolling a developable's flat pattern back up must land ON the
    surface. It lands within 0.0002 mm."""
    A, B = fixture()
    p = develop(A, B, "dev")
    dev = refold_deviation_mm(p)
    assert refold(p).shape == (len(A), 3)
    assert dev.max() < 1e-3, f"{dev.max():.6f} mm"


def test_gate6_refold_clause_is_red_on_the_hull():
    """RED, RECORDED, NOT SOFTENED (honesty rule 6).

    MEASURED max |refold - hull|, reference hull, 41 stations:
        bottom-stbd   141.0 mm   (at x = 9.0 m, in the forefoot warp)
        topside-stbd  225.7 mm   (at the stem)
    At 161 stations they read 143.8 and 206.1 mm, so this is geometry and not
    discretisation — it does not refine away.

    The aft half of the BOTTOM panel refolds to 0.008 mm. That part of the hull
    really is developable, and it is why the failure is diagnosable: every
    millimetre of error is in the bow, where ruling_twist peaks at 0.288.

    The fix is slanted rulings (developable surface FITTING), not a wider
    tolerance. If someone implements that, this test fails and must be
    rewritten as a pass — that is the intended way for it to break."""
    bottom, topside = hull_panels(Hull(mid_params()))
    db = refold_deviation_mm(bottom)
    dt = refold_deviation_mm(topside)

    assert db.max() > REFOLD_BAR_MM and dt.max() > REFOLD_BAR_MM
    assert 120.0 < db.max() < 170.0, f"bottom {db.max():.1f} mm"
    assert 190.0 < dt.max() < 260.0, f"topside {dt.max():.1f} mm"
    # the aft half is the developable half, and it MEETS the bar
    assert db[:len(db) // 2].max() < REFOLD_BAR_MM
    # and the error is where the twist is
    assert int(np.argmax(db)) > len(db) // 2


def test_refold_does_not_converge_with_station_count():
    """A refold error that shrank under refinement would be a discretisation
    artefact of the development, not a statement about the panel. It does not:
    141.0 -> 143.8 mm on the bottom over a 4x refinement."""
    coarse = hull_panels(Hull(mid_params(), n_stations=41))[0]
    fine = hull_panels(Hull(mid_params(), n_stations=161))[0]
    assert (refold_deviation_mm(fine).max()
            == pytest.approx(refold_deviation_mm(coarse).max(), rel=0.15))


def test_refold_refuses_a_panel_it_cannot_locate():
    """A FlatPanel built by hand carries no 3-D datum; refolding it would have
    to invent the jig line. It refuses instead of guessing."""
    from navalai.unroll import FlatPanel
    p = FlatPanel("hand-made", np.zeros((3, 2)), np.ones((3, 2)), 0.0)
    with pytest.raises(ValueError, match="3-D edges"):
        refold(p)


# ---------------- G2: real nesting ----------------------------------------

def test_the_hull_panels_fit_no_sheet_at_all():
    """The incident, asserted so it cannot be forgotten: the developed panels
    measure 10.05 x 1.62 m and 10.54 x 1.44 m against a 1.22 x 2.44 m sheet.
    `export_dxf` used to draw them whole, offset in y."""
    for p in hull_panels(Hull(mid_params())):
        w, h, _ = min_area_rect(p.outline)
        assert max(w, h) > SHEET_L_M * 3, f"{p.name}: {w:.2f} x {h:.2f} m"


def test_split_panel_produces_pieces_that_fit_a_sheet():
    """Every piece, including its scarph flanges, fits the stock sheet."""
    t = 0.015
    allow = SCARPH_RATIO * t / 2.0
    for panel in hull_panels(Hull(mid_params())):
        parts = split_panel(panel, t)
        assert len(parts) > 1
        for q in parts:
            w, h, _ = min_area_rect(q.outline)
            assert min(w, h) + 2 * allow <= SHEET_W_M + 1e-9
            assert max(w, h) + 2 * allow <= SHEET_L_M + 1e-9


def test_scarph_allowance_is_eight_to_one_and_counted_once():
    """A plywood scarph is 8:1 on thickness, and the two tapers OVERLAP: one
    joint costs 8t of extra material in total, so each of the two pieces
    meeting there carries 4t — not 8t each, which would double the overlap."""
    t = 0.018
    parts = split_panel(hull_panels(Hull(mid_params()))[0], t)
    interior = [q for q in parts if "0 scarph" not in q.note]
    assert interior, "a split panel with no scarph joints is not a split panel"
    for q in interior:
        w, h, _ = min_area_rect(q.outline)
        n_edges = int(q.note.split(" scarph")[0].split()[-1])
        assert q.scarph_m2 <= n_edges * (SCARPH_RATIO * t / 2.0) * max(w, h) + 1e-9
        assert q.scarph_m2 > 0.0


def test_every_placed_part_is_inside_its_sheet_and_overlaps_nothing():
    """What 'nesting' has to mean before the word is used: parts on sheets,
    inside the boundary, not on top of each other. The old layout had no sheet
    boundary to be inside of."""
    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    assert layout.sheets >= 2
    for pl in layout.placements:
        assert -1e-9 <= pl.x and pl.x + pl.w <= layout.sheet_w + 1e-9
        assert -1e-9 <= pl.y and pl.y + pl.h <= layout.sheet_l + 1e-9
        assert pl.polygon[:, 0].min() >= -1e-9
        assert pl.polygon[:, 1].min() >= -1e-9
        assert pl.polygon[:, 0].max() <= layout.sheet_w + 1e-9
        assert pl.polygon[:, 1].max() <= layout.sheet_l + 1e-9
    for i in range(layout.sheets):
        rs = [(p.x, p.y, p.w, p.h) for p in layout.on_sheet(i)]
        assert rs, f"sheet {i} is empty — the packer opened a sheet for nothing"
        for a in range(len(rs)):
            for b in range(a + 1, len(rs)):
                ax, ay, aw, ah = rs[a]
                bx, by, bw, bh = rs[b]
                overlap = (min(ax + aw, bx + bw) - max(ax, bx) > 1e-9
                           and min(ay + ah, by + bh) - max(ay, by) > 1e-9)
                assert not overlap, f"sheet {i}: parts {a} and {b} overlap"


def test_rotation_is_a_rotation_and_not_a_reflection():
    """'Nesting' with no rotation is stacking with extra steps, so the packer
    must demonstrably turn parts through 90 degrees — and turning them must not
    MIRROR them. `polygon[:, ::-1]` swaps x and y, which is a reflection: it
    yields the mirror image of the strake, a piece that will not fit the boat.
    A reflection flips the signed area; a rotation preserves it."""
    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    assert any(pl.rotated for pl in layout.placements)

    def signed_area(poly):
        x, y = poly[:, 0], poly[:, 1]
        return float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2

    for pl in layout.placements:
        if not pl.rotated:
            continue
        src = next(p for p in parts if pl.part.startswith(p.name))
        assert np.sign(signed_area(pl.polygon)) == np.sign(signed_area(src.outline))
        assert abs(signed_area(pl.polygon)) == pytest.approx(
            abs(signed_area(src.outline)), rel=1e-9)


def test_sheets_are_not_mixed_across_thicknesses():
    """You cannot cut a 21 mm bottom piece out of a 15 mm topside sheet. The
    sheet count is a sum over thickness groups, which is one reason a single
    area/SHEET_M2 division could never have been right."""
    panels = hull_panels(Hull(mid_params()))
    parts = split_panel(panels[0], 0.021) + split_panel(panels[1], 0.015)
    layout = nest(parts)
    for i, t in enumerate(layout.sheet_thickness_mm):
        for pl in layout.on_sheet(i):
            src = next(p for p in parts if pl.part.startswith(p.name))
            assert src.thickness_m * 1e3 == pytest.approx(t)


# ---------------- G2/C12: ply_sheets comes off the layout ------------------

def test_waste_factor_is_gone():
    """C12. `WASTE_FACTOR = 1.30` asserted a nesting waste that the layout
    could measure. There is nothing left to declare."""
    assert not hasattr(engineer, "WASTE_FACTOR")


def test_ply_sheets_is_counted_off_the_layout():
    """MEASURED, reference hull: 68 sheets at 76.8% utilisation, against the
    old 35 from `ceil(area * 1.30 / SHEET_M2)`.

    The old number was not mostly wrong because 1.30 was a bad guess — the
    layout's own ratio of sheet area to part area comes out at 1.36. It was
    wrong because `area` was shell + deck ONLY (79.5 m^2) while the same report
    counted 7 bulkheads and a transom that consumed no material at all. The
    boat needs 148.6 m^2 of ply; 35 sheets is 104.2 m^2 of it."""
    r = assess(Hull(mid_params()))
    assert 55 <= r.ply_sheets <= 85, r.ply_sheets
    assert r.ply_sheets > 35              # strictly more than the old estimate
    assert 0.70 < r.nest_utilisation < 1.0
    assert r.sheet_area_m2 == pytest.approx(r.ply_sheets * SHEET_M2, abs=0.01)
    ply = [b for b in r.bom if b.material == "marine ply"]
    assert sum(b.area_m2 for b in ply) < r.sheet_area_m2   # cannot use more
    assert sum(b.area_m2 for b in ply) > r.panel_area_m2   # nor less than shell


def test_thicker_ply_costs_more_sheets():
    """The layout must respond to the scantling rule, or it is not a layout.
    mLDC 6000 kg drives the bottom to a 21 mm stock sheet (ISO 12215-5 wants
    18.24 mm), which cannot share sheets with the 15 mm topsides."""
    plain = assess(Hull(mid_params()))
    ruled = assess(Hull(mid_params()), mldc_kg=6000.0)
    assert ruled.bottom_thickness_mm == 21.0
    assert plain.bottom_thickness_mm == 15.0
    assert ruled.ply_sheets > plain.ply_sheets


# ---------------- G3: the BOM ---------------------------------------------

def test_bom_has_line_items_and_reconciles_with_the_layout():
    """G3: the report was three aggregate scalars. Every line now names its
    part, material, thickness, area, source panel and the SHEET it nests on,
    and those sheet numbers must be exactly the sheets the packer opened."""
    r = assess(Hull(mid_params()))
    assert len(r.bom) > 50
    ply = [b for b in r.bom if b.material == "marine ply"]
    assert {b.sheet for b in ply} == set(range(1, r.ply_sheets + 1))
    for b in ply:
        assert b.part and b.source_panel and b.note
        assert b.qty == 1 and b.area_m2 > 0.0 and b.thickness_mm > 0.0
        assert set(b.as_dict()) == {"part", "qty", "material", "thickness_mm",
                                    "area_m2", "source_panel", "sheet", "note"}
    # part names are unique, or a cut list cannot be followed
    assert len({b.part for b in r.bom}) == len(r.bom)
    # both sides of the boat are in it: the shell panels are developed to
    # starboard and built twice
    assert any(b.part.endswith("_2") for b in ply)


def test_bom_covers_every_structural_item_the_report_counts():
    """The old estimate counted 7 bulkheads and 18 frames in `panel_count` and
    then priced none of them. Every counted item must appear as line items."""
    r = assess(Hull(mid_params()))
    srcs = {b.source_panel for b in r.bom}
    assert {"bottom-stbd", "topside-stbd", "deck", "transom"} <= srcs
    assert sum(1 for s in srcs if s.startswith("bulkhead-")) == r.bulkheads
    frames = [b for b in r.bom if b.source_panel == "frames"]
    assert len(frames) == r.frames
    # frames are NOT sheet goods: counting a 2.5 x 1.0 m blank per ring frame
    # would inflate the sheet count with a fiction of the opposite sign.
    for b in frames:
        assert b.sheet is None and b.material == "laminated timber"


def test_bom_says_whether_the_bottom_thickness_is_rule_derived():
    """`limits.PLY_THICKNESS_M` is the NOMINAL sheet and failed ISO 12215-5 for
    every SKU in PLM.md. A BOM that prints 15 mm without saying which of the
    two it is invites the same contradiction back in."""
    plain = assess(Hull(mid_params()))
    ruled = assess(Hull(mid_params()), mldc_kg=6000.0)
    for r, expect in ((plain, "NOT rule-derived"), (ruled, "ISO 12215-5")):
        line = next(b for b in r.bom if b.source_panel == "bottom-stbd")
        assert expect in line.note


# ---------------- the nested DXF ------------------------------------------

def test_nested_dxf_draws_sheets_and_keeps_every_part_inside_one(tmp_path):
    """Gate R7's bar: 'a nested DXF whose declared units re-import at the right
    scale and whose panels fit real sheets'. Both halves, on the file."""
    panels = hull_panels(Hull(mid_params()))
    parts = []
    for p in panels:
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    path = export_dxf(layout, tmp_path / "nest.dxf")
    back = parse_dxf_polylines(path)

    sheets = {k: v for k, v in back.items() if k.startswith("SHEET-")}
    assert len(sheets) == layout.sheets
    for k, v in sheets.items():
        assert np.ptp(v[:, 0]) == pytest.approx(SHEET_W_M * 1000.0, abs=1.0)
        assert np.ptp(v[:, 1]) == pytest.approx(SHEET_L_M * 1000.0, abs=1.0)

    # the declared unit must be present, or "millimetres" is a habit rather
    # than a statement the importer can read
    head = path.read_text()
    assert "$INSUNITS" in head and "\n4\n" in head.split("$INSUNITS")[1][:20]

    for pl in layout.placements:
        pts = back[pl.part]
        ox = pl.sheet * (layout.sheet_w + 0.1) * 1000.0
        assert pts[:, 0].min() >= ox - 1.0
        assert pts[:, 0].max() <= ox + SHEET_W_M * 1000.0 + 1.0
        assert pts[:, 1].min() >= -1.0
        assert pts[:, 1].max() <= SHEET_L_M * 1000.0 + 1.0
        # ...and at the scale the header declares, not the metre values that
        # used to be written under no header at all
        assert np.ptp(pts[:, 0]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 0]), abs=1.0)


def test_export_dxf_nests_a_bare_panel_list_rather_than_stacking_it(tmp_path):
    """No caller can go back to stacking by accident: handing `export_dxf` the
    raw panels nests them here."""
    path = export_dxf(hull_panels(Hull(mid_params())), tmp_path / "auto.dxf")
    back = parse_dxf_polylines(path)
    assert any(k.startswith("SHEET-") for k in back)
    assert "bottom-stbd" not in back          # the whole panel is never drawn
    for k, v in back.items():
        if not k.startswith("SHEET-"):
            assert np.ptp(v[:, 0]) <= SHEET_W_M * 1000.0 + 1.0
            assert np.ptp(v[:, 1]) <= SHEET_L_M * 1000.0 + 1.0


# ---------------- A5: the export boundary ---------------------------------

def test_export_refuses_a_design_that_failed_the_ladder(tmp_path):
    """A5 had a fix and no test. An L0-failing hull exported to an 8,487-byte
    DXF and a 174,406-byte STEP without a murmur; `refuse_unvalidated` closed
    that and nothing pinned it shut."""
    from types import SimpleNamespace
    ev = SimpleNamespace(ok=False, tier="L0", violations=["deadrise.order"])
    with pytest.raises(ValueError, match="did not pass the ladder"):
        export_dxf(hull_panels(Hull(mid_params())), tmp_path / "no.dxf", ev=ev)
    assert not (tmp_path / "no.dxf").exists()
    # ev=None is the declared escape hatch for a deliberately unvalidated
    # artefact, and it must keep working
    export_dxf(hull_panels(Hull(mid_params())), tmp_path / "yes.dxf", ev=None)


# ---------------- G6: the exported solid IS the validated hull -------------

def test_step_export_defaults_to_the_validated_discretisation(tmp_path):
    """G6. `export_step`/`export_iges` lofted a hard-coded 12 stations while
    the Hull the ladder floated and ruled on has 41. MEASURED: 37.247988 m^3
    against a kernel moulded volume of 37.433959 m^3 — **-0.497%** between what
    passed the gates and what shipped, from a default argument.

    At the validated 41 stations the same loft reads -0.0004%, a factor of
    1240 better, and the receipt records which it was either way."""
    import json
    pytest.importorskip("cadquery")
    from navalai.export import export_step, moulded_volume_m3

    hull = Hull(mid_params())
    p = export_step(hull, tmp_path / "hull.step")
    rec = json.loads((tmp_path / "hull.step.receipt.json").read_text())
    assert rec["n_stations_exported"] == hull.n_stations == 41
    assert rec["n_stations_validated"] == 41
    assert rec["kernel_moulded_volume_m3"] == pytest.approx(
        moulded_volume_m3(hull), abs=1e-5)
    assert abs(rec["volume_error_pct"]) < 0.01
    assert p.stat().st_size > 10_000


def test_the_old_twelve_station_loft_really_did_lose_half_a_percent(tmp_path):
    """The measurement behind G6, kept executable so the default can never
    drift back without someone seeing the number it costs."""
    import json
    pytest.importorskip("cadquery")
    from navalai.export import export_step

    export_step(Hull(mid_params()), tmp_path / "coarse.step", n_stations=12)
    rec = json.loads((tmp_path / "coarse.step.receipt.json").read_text())
    assert rec["n_stations_exported"] == 12
    assert rec["solid_volume_m3"] == pytest.approx(37.248, abs=0.01)
    assert rec["volume_error_pct"] == pytest.approx(-0.497, abs=0.01)
