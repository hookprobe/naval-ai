"""Stage F gate: panels unroll isometrically with an honest development-error
metric; DXF round-trips; Pareto endpoint serves clickable designs; agent
handoff overhead measured (the anti-Zig receipt)."""

import json
import time

import numpy as np
import pytest

from navalai.geometry import Hull
from navalai.unroll import develop, export_dxf, hull_panels, parse_dxf_polylines
from tests.test_phase0 import mid_params


# ---------------- unrolling ----------------

def test_cylinder_develops_exactly():
    """A cylindrical surface is perfectly developable: error must be ~0 and
    the flat width must equal the arc length.

    THE FIXTURE USED TO BE A CONOID, NOT A CYLINDER (gap G5). It ran chords
    from a straight axis to a quarter circle, so the ruling DIRECTION rotated
    along the strip — twist median 0.383, i.e. not developable — and the bar
    was 5e-3, which the hyperbolic paraboloid also clears (6.5e-4 at n=41).
    A cylinder has PARALLEL rulings, and then the development is exact to
    machine precision, which is a bar a conoid cannot pass. See
    tests/test_manufacturing.py for the negative control the pair needs."""
    n = 40
    theta = np.linspace(0, np.pi / 2, n)
    r = 2.0
    A = np.stack([np.zeros(n), r * np.sin(theta), r * (1 - np.cos(theta))],
                 axis=1)
    B = A + np.array([5.0, 0.0, 0.0])
    panel = develop(A, B, "cyl")
    assert panel.dev_error_rel < 1e-12
    assert panel.twist_max < 1e-12
    widths3 = np.linalg.norm(B - A, axis=1)
    widths2 = np.linalg.norm(panel.edge_b - panel.edge_a, axis=1)
    assert np.allclose(widths2, widths3, rtol=1e-9)   # ruling lengths preserved


def test_hull_panels_develop_within_tolerance():
    panels = hull_panels(Hull(mid_params()))
    assert {p.name for p in panels} == {"bottom-stbd", "topside-stbd"}
    for p in panels:
        # ISOMETRY residual only. This is NOT a developability verdict: it is
        # O(h^2) for any smooth surface, so refining the polyline drives it to
        # zero for a hypar as readily as for a cylinder. The verdict lives in
        # `twist_max`/`twist_median`, and on the topside panel it is bad —
        # tests/test_manufacturing.py::test_hull_panel_twist_is_recorded_not_blessed
        assert p.dev_error_rel < 0.05, f"{p.name}: {p.dev_error_rel:.3f}"


def test_edge_lengths_preserved_3d_to_2d():
    h = Hull(mid_params())
    keel = np.stack([h.x, np.zeros_like(h.x), h.z_keel], axis=1)
    chine = np.stack([h.x, h.y_chine, h.z_chine], axis=1)
    p = develop(keel, chine, "bottom")
    for E3, E2 in ((keel, p.edge_a), (chine, p.edge_b)):
        l3 = np.linalg.norm(np.diff(E3, axis=0), axis=1).sum()
        l2 = np.linalg.norm(np.diff(E2, axis=0), axis=1).sum()
        assert l2 == pytest.approx(l3, rel=1e-6)      # isometric edges


def test_dxf_roundtrip(tmp_path):
    """Every placed part survives the write/read, vertex for vertex.

    THE FILE IS NOW A NEST, NOT A STACK (gap G2). It used to draw the two whole
    panels offset in y — 10.05 x 1.62 m and 10.54 x 1.44 m against a
    1.22 x 2.44 m sheet, so `set(back) == {"bottom-stbd", "topside-stbd"}` was
    asserting that the file contained two parts no shop could cut. The
    round-trip is now over the split, rotated, placed pieces."""
    from navalai.unroll import nest, split_panel

    parts = []
    for p in hull_panels(Hull(mid_params())):
        parts += split_panel(p, 0.015)
    layout = nest(parts)
    path = export_dxf(layout, tmp_path / "panels.dxf")
    back = parse_dxf_polylines(path)

    assert {"bottom-stbd", "topside-stbd"} & set(back) == set()   # never whole
    for pl in layout.placements:
        pts = back[pl.part]
        assert len(pts) == len(pl.polygon)
        # Extents survive the write/read, IN THE UNITS THE FILE DECLARES.
        # The writer now emits millimetres and says so via $INSUNITS 4. It
        # previously wrote metres with NO header at all, so a shop importing
        # the file cut a 10 mm part instead of a 10 m one. Comparing the
        # round-trip against the metre-valued outline is what let that pass.
        assert np.ptp(pts[:, 0]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 0]), abs=1.0)
        assert np.ptp(pts[:, 1]) == pytest.approx(
            1000.0 * np.ptp(pl.polygon[:, 1]), abs=1.0)
    # ...and the declared unit must be present, or "millimetres" is a habit
    # rather than a statement the importer can read.
    head = path.read_text()
    assert "$INSUNITS" in head and "\n4\n" in head.split("$INSUNITS")[1][:20]


# ---------------- Pareto dashboard ----------------

def test_pareto_endpoint_serves_designs():
    from ui.server import get_pareto
    d = get_pareto()
    assert len(d["points"]) >= 3 and d["tier"] == "L1"
    for p in d["points"]:
        assert set(p) == {"params", "wh_per_nm", "build_area_m2", "gm_m"}
        assert len(p["params"]) == 15
    # cached: second call is instant
    t0 = time.perf_counter()
    get_pareto()
    assert time.perf_counter() - t0 < 0.01


def test_dashboard_html_has_pareto_ui():
    html = open("ui/index.html").read()
    assert 'id="pareto"' in html and "/pareto" in html


# ---------------- handoff-latency receipt ----------------

def test_agent_handoff_overhead_is_noise():
    """Original plan Phase 5 wanted Zig to cut agent-handoff latency. Measure
    it instead: queue round-trip must be <1% of one L1 physics evaluation."""
    import asyncio

    from navalai.evaluate import evaluate
    from navalai.mission import MissionSpec

    async def roundtrip(n=200):
        q = asyncio.Queue()
        t0 = time.perf_counter()
        for _ in range(n):
            await q.put(1)
            await q.get()
        return (time.perf_counter() - t0) / n

    handoff = asyncio.run(roundtrip())
    evaluate(mid_params(), MissionSpec())   # warm
    t0 = time.perf_counter()
    evaluate(mid_params(), MissionSpec())
    physics = time.perf_counter() - t0
    ratio = handoff / physics
    assert ratio < 0.01, f"handoff {handoff*1e6:.1f} us vs physics {physics*1e3:.1f} ms"
