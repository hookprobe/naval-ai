"""Stage C gate: agent network produces engineered designs with a clean audit
trail; builder emits parameters only; engineer numbers sane; STEP exports."""

import numpy as np
import pytest

from navalai import grammar
from navalai.agents import run_plm
from navalai.engineer import assess
from navalai.geometry import Hull
from tests.test_phase0 import mid_params

MISSION = ("6 tonne solar-electric liveaboard, 10 m, Danube river, "
           "cruise 5 knots, 2 crew")


@pytest.fixture(scope="module")
def plm_run():
    return run_plm(MISSION, n_designs=3, batch=10, timeout_s=180.0)


def test_network_delivers_validated_designs(plm_run):
    results, audit, mission = plm_run
    assert len(results) == 3
    for rec in results:
        assert rec.evaluation.ok and rec.evaluation.tier == "L1"
        assert rec.requirements["pass"] or rec.requirements["passed"] >= 4
        assert np.isfinite(rec.fitness)


def test_audit_trail_flows(plm_run):
    _results, audit, _m = plm_run
    flows = audit.flows()
    kinds = {k for _s, _r, k in flows}
    assert {"mission", "candidate", "validated", "engineered"} <= kinds
    # pipeline order respected: builder->validator->engineer->orchestrator
    assert ("builder", "validator", "candidate") in flows
    assert ("validator", "engineer", "validated") in flows
    assert ("engineer", "orchestrator", "engineered") in flows


def test_builder_emits_parameters_never_vertices(plm_run):
    _r, audit, _m = plm_run
    for msg in audit.trail:
        if msg.sender == "builder":
            assert isinstance(msg.payload, np.ndarray)
            assert msg.payload.shape == (grammar.N_PARAMS,)   # a genome, not a mesh


def test_gatekeeper_assigns_infinite_fitness(plm_run):
    _r, audit, _m = plm_run
    rejects = [m for m in audit.trail if m.kind == "rejected"]
    for m in rejects:
        assert m.payload["fitness"] == float("inf") and m.payload["why"]


def test_engineer_metrics_sane():
    rep = assess(Hull(mid_params()))
    assert rep.panel_count >= 8
    assert rep.bulkheads >= 2
    assert 20 < rep.panel_area_m2 < 200
    assert rep.ply_sheets > 10
    assert 5 < rep.interior_volume_m3 < 60
    assert 500 < rep.build_hours < 5000
    assert "approx" in rep.basis          # declared basis, same as rules tier


def test_step_export():
    cq = pytest.importorskip("cadquery")
    from navalai.export import export_step
    p = export_step(Hull(mid_params()), "data/exports/hull.step")
    text = p.read_text(errors="ignore")
    assert text.startswith("ISO-10303-21")
    assert p.stat().st_size > 10_000


def test_iges_export():
    pytest.importorskip("cadquery")
    from navalai.export import export_iges
    p = export_iges(Hull(mid_params()), "data/exports/hull.iges")
    assert p.stat().st_size > 50_000
    assert "S0000001" in p.read_text(errors="ignore")[:100]
