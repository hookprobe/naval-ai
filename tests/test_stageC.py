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


# ---------------------------------------------------------------------------
# The delivered BOM must be the boat the ladder validated
# ---------------------------------------------------------------------------

def test_the_delivered_bom_is_built_to_the_rule_derived_thickness(plm_run):
    """`_engineer` called `assess(Hull(x), ev.wl)` and never passed `mldc_kg`,
    although `mission` was already a parameter of that coroutine.

    MEASURED on the reference hull at the default 6 t mission, before the fix:

        assess(hull, ev.wl)                 bottom 15.0 mm,  40 sheets
        assess(hull, ev.wl, mldc_kg=6000)   bottom 21.0 mm,  42 sheets
        the agent-delivered record          bottom 15.0 mm, 140 sheets
        ev.ply_thickness_m                         21.0 mm

    So the SAME ladder run derived 21 mm from ISO 12215-5, charged the boat
    that structural weight, and then shipped a bill of materials for a 15 mm
    boat. The BOM even said so — "thickness nominal stock sheet (no mLDC given
    — NOT rule-derived)" — which makes it honest and still a cut list that
    fails the platform's own scantling rule. Delivered sheets went 140 -> 153.
    """
    results, _audit, _m = plm_run
    for rec in results:
        want_mm = rec.evaluation.ply_thickness_m * 1e3
        assert rec.engineering.bottom_thickness_mm == pytest.approx(want_mm), (
            f"delivered BOM is built to {rec.engineering.bottom_thickness_mm} mm "
            f"while the ladder that validated it derived {want_mm} mm")
        bottom = [b for b in rec.engineering.bom
                  if b.source_panel.startswith("bottom")]
        assert bottom, "no bottom panel in the BOM"
        for line in bottom:
            assert line.thickness_mm == pytest.approx(want_mm)
            assert "NOT rule-derived" not in line.note


# ---------------------------------------------------------------------------
# The Validator's L0 type-check has to be able to reject
# ---------------------------------------------------------------------------

def test_the_l0_type_check_can_actually_reject(plm_run):
    """It could not. The gatekeeper read

        rep = type_check(HullDesign.from_vector(x, Typology.SHARP_CHINE))
        ev = evaluate(x, mission) if rep.ok or grammar.check(x).ok else None

    and `type_check` ends by appending `grammar.check(...).violations` to its
    own list, so `rep.ok` IMPLIES `grammar.check(x).ok` and the whole
    disjunction is identically `grammar.check(x).ok`. The typology arm was
    inert while the Validator's docstring advertised an "L0 type-check".

    MEASURED over 200,000 uniform in-box vectors: 48,243 pass `grammar.check`,
    of which 27,440 (56.9%) FAIL the sharp-chine type check — example
    violation `typology[sharp-chine]: forefoot 0.32 outside [0.4, 1.0]` — and
    every one of them was delivered.

    Three arms, because no one of them catches the mechanism alone: the class
    of rejectable vectors must be non-empty, the Validator must be seen
    rejecting at L0, and every DELIVERED design must name the typology it
    type-checked as.
    """
    from navalai import grammar
    from navalai.hull_ast import (HullDesign, Typology, infer_typology,
                                  type_check)

    # ARM 1: the class of vectors the old disjunction could not exclude is not
    # empty. If it ever becomes empty the measurement above has gone stale and
    # this test is worthless without saying so.
    rng = np.random.default_rng(0)
    in_box = rejectable = 0
    for _ in range(4000):
        x = rng.uniform(grammar.LOW, grammar.HIGH)
        if not grammar.check(x).ok:
            continue
        in_box += 1
        if infer_typology(x) is None:
            rejectable += 1
    assert in_box > 100 and rejectable > 0, (
        f"{rejectable} of {in_box} in-box vectors are rejectable at L0; the "
        f"measurement this test rests on no longer holds")

    # ARM 2: the Validator is SEEN doing it, on the Builder's own distribution.
    results, audit, _m = plm_run
    stages = [m.payload.get("stage") for m in audit.trail if m.kind == "rejected"]
    assert "L0 type-check" in stages, (
        "the agent network rejected nothing at L0 — the arm that was inert")

    # ARM 3: nothing is delivered that does not type-check as a real typology.
    for rec in results:
        assert rec.typology in {t.value for t in Typology}, (
            f"delivered design carries typology {rec.typology!r}")
        assert type_check(HullDesign.from_vector(
            rec.params, Typology(rec.typology))).ok
