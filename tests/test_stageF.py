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
    the flat width must equal the arc length."""
    n = 40
    theta = np.linspace(0, np.pi / 2, n)
    r = 2.0
    A = np.stack([np.linspace(0, 5, n), np.zeros(n), np.zeros(n)], axis=1)
    B = A + np.stack([np.zeros(n), r * np.sin(theta), r * (1 - np.cos(theta))],
                     axis=1)
    panel = develop(A, B, "cyl")
    assert panel.dev_error_rel < 5e-3
    widths3 = np.linalg.norm(B - A, axis=1)
    widths2 = np.linalg.norm(panel.edge_b - panel.edge_a, axis=1)
    assert np.allclose(widths2, widths3, rtol=1e-9)   # ruling lengths preserved


def test_hull_panels_develop_within_tolerance():
    panels = hull_panels(Hull(mid_params()))
    assert {p.name for p in panels} == {"bottom-stbd", "topside-stbd"}
    for p in panels:
        # developability honesty: chine hulls with warped bottoms are NEAR-
        # developable; the residual must be small but is NOT claimed zero
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
    panels = hull_panels(Hull(mid_params()))
    path = export_dxf(panels, tmp_path / "panels.dxf")
    back = parse_dxf_polylines(path)
    assert set(back) == {"bottom-stbd", "topside-stbd"}
    for p in panels:
        pts = back[p.name]
        assert len(pts) == len(p.outline)
        # extents survive the write/read (nesting offset shifts y only)
        assert np.ptp(pts[:, 0]) == pytest.approx(np.ptp(p.outline[:, 0]), abs=1e-3)
        assert np.ptp(pts[:, 1]) == pytest.approx(np.ptp(p.outline[:, 1]), abs=1e-3)


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
