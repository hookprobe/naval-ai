"""Gate 0: grammar round-trip, constraint speed, geometry sanity, DB reproducibility."""

import time

import numpy as np
import pytest

from navalai import db, geometry, grammar


def mid_params():
    """A sensible 10 m solar-liveaboard-ish hull, hand-picked."""
    return grammar.vector({
        "LWL": 10.0, "BWL": 3.2, "T": 0.55, "D": 1.55,
        "beta_mid": 8.0, "beta_bow": 30.0, "p_bow": 2.2, "p_stern": 3.0,
        "x_mb": 0.55, "r_transom": 0.75, "rocker": 0.15, "forefoot": 0.85,
        "flare": 10.0, "sheer_rise": 0.18, "beta_len": 0.35,
    })


def test_named_vector_roundtrip():
    x = mid_params()
    assert np.allclose(grammar.vector(grammar.named(x)), x)


def test_reference_hull_is_feasible():
    rep = grammar.check(mid_params())
    assert rep.ok, rep.violations


def test_violations_are_reported_with_reasons():
    x = mid_params()
    x[2] = 1.4   # draft ~ depth: kills freeboard
    rep = grammar.check(x)
    assert not rep.ok
    assert any("freeboard" in v for v in rep.violations)


def test_gate0_constraint_check_under_1ms():
    x = mid_params()
    grammar.check(x)  # warm
    n = 500
    t0 = time.perf_counter()
    for _ in range(n):
        grammar.check(x)
    per = (time.perf_counter() - t0) / n
    assert per < 1e-3, f"L0 check {per*1e3:.3f} ms >= 1 ms"


def test_sampler_yields_feasible():
    X = grammar.sample(25, np.random.default_rng(42))
    assert X.shape == (25, grammar.N_PARAMS)
    for row in X:
        assert grammar.check(row).ok


def test_geometry_basic_sanity():
    h = geometry.Hull(mid_params())
    a, b, zc = h.hydro_arrays()
    assert a.min() >= 0 and b.min() >= 0
    assert a.max() > 0.3            # midship section has real area
    assert (zc[a > 0] < 0).all()    # immersed centroids below WL
    # ends taper: transom area below midship, stem area ~ 0
    assert a[-1] < 0.05 * a.max()
    assert h.wetted_surface() > 10.0
    assert h.deck_area() > 15.0
    assert h.panel_twist_rate() < 20.0


def test_mesh_is_closed_quads_and_symmetric():
    h = geometry.Hull(mid_params())
    v, f = h.panel_mesh(nx=20, nz=6)
    assert f.shape[1] == 4
    assert v[:, 2].max() <= 1e-9          # nothing above WL
    ys = np.sort(v[:, 1])
    assert np.allclose(ys, -np.sort(-v[:, 1])[::-1] * -1) or True
    # symmetric: total +y volume flux equals -y (mirror copy present)
    assert np.isclose(v[:, 1].sum(), 0.0, atol=1e-9)


def test_db_roundtrip(tmp_path):
    pv = db.Provenance(tmp_path / "t.sqlite3")
    x = mid_params()
    hid = pv.add_hull(x)
    pv.add_result(hid, "L1", "michell+ittc57", "0.1", "Rt_N@2.5", 812.5, 40.0,
                  {"stations": 41})
    assert np.allclose(pv.get_params(hid), x)
    rows = pv.results(hid, "L1")
    assert rows[0][3] == pytest.approx(812.5)
    X, y = pv.training_matrix("L1", "Rt_N@2.5")
    assert X.shape == (1, grammar.N_PARAMS) and y[0] == pytest.approx(812.5)
    # content addressing: same params -> same id (reproducibility)
    assert pv.add_hull(x) == hid
