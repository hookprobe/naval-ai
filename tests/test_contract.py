"""The Hull Evaluation Contract: one deterministic path, one receipt.

The gap it closes: every stage of genome -> valid hull -> model -> mesh ->
solver existed and was correct in isolation, and NOTHING composed them, so
each caller re-derived Fn, Re, the regime and the model's validity for
itself. This suite pins the composition — above all that the four questions
stay FOUR VERDICTS and are never collapsed into one flag.
"""
import numpy as np
import pytest

from navalai.contract import (MARGINAL, OK, REFUSED, UNMEASURED,
                              evaluate_hull, genome_sha256,
                              mesh_prescription)
from navalai.mission import MissionSpec
from tests.test_phase0 import mid_params

KIT_REFERENCE = [12.24464859, 3.105685017, 0.55, 1.55, 0.6392941018, -1.0,
                 0.4760097448, 0.3, 9.039289126, 9.039289126, 0.35, 0.0,
                 0.15, 0.0, 0.0, 0.18]


def test_the_four_questions_stay_four_verdicts():
    """MEASURED on the reference hull: A REFUSED (the 18 mm-ply cold-bend
    radius), while B (the model) and C (meshability) are both OK. One flag
    could not carry that: "invalid" would send someone to the physics or the
    mesher for a MANUFACTURING refusal. That is the whole reason the
    operator's rule is four verdicts and not one."""
    ev = evaluate_hull(np.array(mid_params()), MissionSpec())
    assert ev.hull_verdict == REFUSED
    assert ev.model_verdict == OK
    assert ev.mesh_verdict == OK
    assert ev.result_verdict == UNMEASURED
    assert any("bend radius" in r for r in ev.reasons), ev.reasons
    assert ev.status == REFUSED


def test_a_design_that_has_never_been_solved_can_never_read_OK():
    """D is UNMEASURED until a solve exists, and `status` refuses to be
    optimistic about it. A receipt that read OK for a hull nothing has ever
    solved is precisely the 'looks checkable and is not' failure."""
    ev = evaluate_hull(np.array(KIT_REFERENCE), MissionSpec())
    assert ev.result_verdict == UNMEASURED
    assert ev.status in (MARGINAL, UNMEASURED)
    assert ev.status != OK


def test_the_receipt_names_its_own_hull_and_the_gate_that_decided():
    ev = evaluate_hull(np.array(KIT_REFERENCE), MissionSpec())
    assert ev.genome_sha256 == genome_sha256(np.array(KIT_REFERENCE))
    assert len(ev.genome_sha256) == 64
    # `why` names the GATE and carries its measured value — never a bare
    # verdict, so a receipt can be argued with.
    assert ":" in ev.fidelity_why and any(
        c.isdigit() for c in ev.fidelity_why), ev.fidelity_why
    d = ev.to_dict()
    assert d["status"] == ev.status and d["mesh"]["mesh_density"] is not None


def test_a_refused_genome_stops_the_path_without_inventing_verdicts():
    """grammar refuses before any physics; the stages that depend on it are
    UNMEASURED rather than assumed — the opposite of scoring an
    unmeasurable value as a passing one."""
    bad = np.array(mid_params())
    bad[0] = float("nan")
    ev = evaluate_hull(bad, MissionSpec())
    assert ev.hull_verdict == REFUSED
    assert ev.model_verdict == ev.mesh_verdict == UNMEASURED
    assert ev.status == REFUSED
    assert ev.mesh.mesh_density is None and ev.mesh.refusals


def test_the_mesh_prescription_is_derived_not_defaulted():
    """The prescription INVERTS floors the repo already owns: the density
    is whatever buys MIN_CELLS_PER_WAVELENGTH (20) AT THIS Fn, and the
    first layer comes from the y+ target through ITTC-57's friction
    velocity. Before this, a case could be — and was — written at 12.7
    cells per wavelength with nothing in the lane to say so."""
    from navalai.fidelity import MIN_CELLS_PER_WAVELENGTH

    p = mesh_prescription(lwl_m=12.0, speed_ms=2.5, fn=0.23)
    assert p.cells_per_wavelength == pytest.approx(MIN_CELLS_PER_WAVELENGTH,
                                                   rel=0.01)
    assert 0.0 < p.first_layer_m < 0.05
    assert "MIN_CELLS_PER_WAVELENGTH" in p.basis["mesh_density"]
    assert "ITTC-57" in p.basis["first_layer_m"]

    # A LOWER Froude number needs a FINER mesh for the same wave resolution:
    # the transverse wavelength scales with Fn^2, so a slow hull's waves are
    # short relative to the hull and cost more cells, which is the opposite
    # of the intuition that slow is cheap.
    slow = mesh_prescription(lwl_m=12.0, speed_ms=1.5, fn=0.14)
    assert slow.mesh_density > p.mesh_density


def test_a_prescription_without_inputs_refuses_by_name():
    p = mesh_prescription(None, None, None)
    assert p.mesh_density is None and p.first_layer_m is None
    assert p.refusals and "unmeasurable" in p.refusals[0]
