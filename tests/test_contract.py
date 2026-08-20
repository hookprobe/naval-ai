"""The Hull Evaluation Contract: one deterministic path, one receipt.

The gap it closes: every stage of genome -> valid hull -> model -> mesh ->
solver existed and was correct in isolation, and NOTHING composed them, so
each caller re-derived Fn, Re, the regime and the model's validity for
itself. This suite pins the composition — above all that the four questions
stay FOUR VERDICTS and are never collapsed into one flag.
"""
import math

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


# ---------------------------------------------------------------------------
# the regime taxonomy and the full prescription (the operator's SS5 and SS8)
# ---------------------------------------------------------------------------


def test_regimes_are_a_tuple_because_they_are_not_exclusive():
    """A catamaran at Fn 0.46 is wave-making AND multihull, and collapsing
    that to one label is how a monohull resistance model ends up silently
    answering a multihull question. Ordered most-constraining first."""
    from navalai.contract import (REGIME_DISPLACEMENT, REGIME_HIGH_FN,
                                  REGIME_MULTIHULL, REGIME_TRANSITIONAL,
                                  REGIME_WAVEMAKING, classify_regime)

    assert classify_regime(12.0, 2.5, 0.23, 2.7e7) == (REGIME_DISPLACEMENT,)
    # a 1 m hull at 1 m/s: Re 9.2e5 is inside the transition band, so the
    # friction line is an extrapolation whatever the Froude number says
    assert classify_regime(1.0, 1.0, 0.32, 9.2e5) == (
        REGIME_TRANSITIONAL, REGIME_WAVEMAKING)
    assert classify_regime(12.0, 5.0, 0.46, 5e7, n_hulls=2) == (
        REGIME_WAVEMAKING, REGIME_MULTIHULL)
    assert classify_regime(3.0, 6.0, 1.1, 1.6e7) == (REGIME_HIGH_FN,)


def test_the_prescription_prices_the_runner_s_own_abort_bar_before_meshing():
    """`expected_tau_s` is h_min/U — the same geometric flow time scale
    run-case.sh kills a solve on below 1e-12 s. Prescribing it means the
    case is priced against that bar BEFORE the mesher runs, instead of the
    campaign discovering it 45 minutes in (h18 diverged at 4.356e-18)."""
    p = mesh_prescription(lwl_m=12.0, speed_ms=2.5, fn=0.23)
    assert p.expected_tau_s is not None and p.expected_tau_s > 1e-12
    assert p.surface_cell_m == pytest.approx(
        p.expected_tau_s * 2.5, rel=1e-9)
    # the sizes are a chain, not four independent numbers
    assert p.background_cell_m > p.free_surface_cell_m > p.surface_cell_m
    assert p.first_layer_m < p.surface_cell_m, (
        "a first layer thicker than its host cell is the stack/hull_cell "
        "defect the case writer already guards")


def test_the_prescription_carries_its_own_cost():
    """SS17: the receipt must say what the evidence COSTS, or 'is CFD worth
    it' is a question nobody can answer from it."""
    p = mesh_prescription(lwl_m=12.0, speed_ms=2.5, fn=0.23)
    assert p.cells and p.cells > 1000
    assert p.timestep_s and p.timestep_s > 0.0
    assert p.wall_s and p.wall_s > 0.0
    assert p.ram_gb and p.ram_gb > 0.0


def test_the_receipt_identifies_which_boat_it_describes():
    """SS12's identity block: a receipt that cannot say the displacement,
    Cp or hull count of the boat it grades is not the canonical truth
    anything can consume."""
    ev = evaluate_hull(np.array(KIT_REFERENCE), MissionSpec())
    assert ev.displacement_kg and ev.displacement_kg > 0.0
    assert ev.cp and 0.4 < ev.cp < 0.9
    assert ev.beam_wl_m and ev.beam_wl_m > 0.0
    assert ev.n_hulls == 1 and ev.regimes
    d = ev.to_dict()
    assert d["regimes"] == list(ev.regimes)
    assert d["mesh"]["expected_tau_s"] is not None


def test_the_prescription_and_the_shipped_writer_disagree_about_the_stack():
    """MEASURED across the whole seed-0 25-hull campaign population: the
    prescription's derived layer count differs from the shipped writer's on
    24 of 25 hulls (prescription 6, writer 7, on 18 of them).

    WHY THAT IS NOT A VICTORY CLAIM. The Mac measured on 2026-08-20 that
    n=6 meshes CLEAN for h011 and h012 where n=7 produces 13 and 12
    wrong-oriented faces — so the prescription's count is inside the safe
    region for exactly the two hulls the campaign lost. But it prescribes 6
    for 22 hulls that meshed perfectly well at 7, so it does NOT
    discriminate failures from passers and must not be sold as a predictor.
    What it is: a DIFFERENT default, derived from a physics-set cell size
    rather than from a cap (_MAX_LAYERS = 7) that was calibrated on the old
    anisotropic background.

    The disagreement is the reason the prescription A/B has to be measured
    before it becomes the default, and this test exists so that the day
    someone flips that switch, the size of what they are changing is
    already written down.
    """
    import json
    import math
    from pathlib import Path

    from navalai.cfd.case import (_DOMAIN_LENGTH_L, _HULL_REFINE,
                                  _LAYER_EXPANSION, _MAX_LAYERS, _NX_BASE,
                                  _TARGET_YPLUS, first_layer_thickness,
                                  n_layers_to_bridge)

    data = json.loads((Path(__file__).resolve().parents[1] / "data"
                       / "gate2u-16gene-mesh.json").read_text())
    rows = data.get("rows") or data.get("hulls")
    u, scale = data["speed"], data["scale"]

    disagree = 0
    for r in rows:
        lwl = r.get("lwl")
        if lwl is None:
            continue
        nx_w = max(1, int(round(_NX_BASE * scale)))
        cell_w = _DOMAIN_LENGTH_L * lwl / nx_w / (2.0 ** _HULL_REFINE[1])
        t1 = first_layer_thickness(u, lwl, _TARGET_YPLUS)
        n_writer = min(n_layers_to_bridge(t1, cell_w, _LAYER_EXPANSION),
                       _MAX_LAYERS)
        p = mesh_prescription(lwl, u, u / math.sqrt(9.81 * lwl))
        assert p.n_layers is not None
        if p.n_layers != n_writer:
            disagree += 1
    assert disagree >= 20, (
        f"only {disagree} of {len(rows)} disagree — if this has fallen, the "
        f"two derivations have converged and the A/B may be moot; re-measure "
        f"before assuming so")


def test_the_prescribed_density_clears_the_bar_AFTER_the_writer_rounds_it():
    """MEASURED BY THE MAC, Block 4, 2026-08-20: all four Fn-matched size
    bands wrote at 19.90 cells per wavelength against a bar of 20 — the same
    0.5% miss in every band, because they are Fn-matched by construction and
    therefore share the rounding.

    The mechanism is this module's, not the writer's:
    `density_for_wave_resolution` inverts the floor EXACTLY, so the ideal
    density buys precisely MIN_CELLS_PER_WAVELENGTH — and then the writer
    discretises it into an integer background cell count. Rounding to
    NEAREST steps under the bar whenever the fraction is below a half, which
    is most of the time. A floor that the prescription's own discretisation
    steps under is not a floor.
    """
    from navalai.fidelity import MIN_CELLS_PER_WAVELENGTH

    for lwl, fn in ((3.44, 0.25), (5.87, 0.25), (7.29, 0.25), (11.36, 0.25),
                    (12.0, 0.23), (8.0, 0.31), (20.0, 0.18)):
        p = mesh_prescription(lwl, fn * math.sqrt(9.81 * lwl), fn)
        assert p.cells_per_wavelength >= MIN_CELLS_PER_WAVELENGTH, (
            f"L={lwl} Fn={fn}: {p.cells_per_wavelength:.3f} < bar")
        # ...and it does not overshoot into paying for cells nobody asked
        # for: at most one background cell in x above the ideal.
        assert p.cells_per_wavelength < MIN_CELLS_PER_WAVELENGTH * 1.10


def test_the_rung_the_screen_names_is_one_the_writer_can_stand_on():
    """A FIX THAT WAS CORRECT AND UNREACHED, caught by the Mac.

    The first attempt rounded the density up inside
    `contract.mesh_prescription` — right arithmetic, wrong module:
    `navalai/cfd/case.py` has ZERO references to `contract`, so the number
    a reader actually acts on (`wave_resolution_screen`'s `scale_needed`)
    was still the continuous inverse, which lands BACK under the bar once
    the writer discretises it. The four coverage bands were being told to
    use a scale that would have reproduced the 19.90 they were flagged for.

    The rounding now lives in `fidelity.density_that_clears_wave_resolution`,
    the home both callers already share, and this test asserts the property
    that matters end to end: THE RUNG THE SCREEN NAMES, FED BACK IN, CLEARS.
    """
    from navalai.cfd.case import wave_resolution_screen
    from navalai.fidelity import (MIN_CELLS_PER_WAVELENGTH,
                                  cells_per_wavelength)

    for lwl, fn in ((3.44, 0.25), (11.36, 0.25), (10.0, 0.202), (7.0, 0.18)):
        u = fn * math.sqrt(9.81 * lwl)
        rep = wave_resolution_screen(lwl, u, 1.0)
        if rep["verdict"] == "CLEAR":
            continue
        assert cells_per_wavelength(fn, rep["scale_needed"]) >= \
            MIN_CELLS_PER_WAVELENGTH, (
                f"L={lwl} Fn={fn}: the screen names a rung that still misses")


# ---------------------------------------------------------------------------
# §14: the supported domain, enforced in ONE place
# ---------------------------------------------------------------------------


def test_the_supported_domain_refuses_by_axis_and_by_name():
    """The operator's §14: "do not claim Naval-AI solves every boat; define
    the supported domain, then make the code refuse designs outside it."

    It was DECLARED in the gap matrix and enforced PIECEMEAL — the grammar
    box clipped length, select_fidelity gated Fn and Re, EVALUABLE_TOPOLOGIES
    refused a trimaran — with nowhere that could answer "is this even in
    scope?". Every bound here is IMPORTED from its owner, so the domain
    cannot drift from the modules that enforce its parts.
    """
    from navalai.contract import supported_domain
    from navalai.mission import Topology

    ok, why = supported_domain(lwl_m=12.0, fn=0.25, re=2.7e7,
                               topology=Topology.MONOHULL)
    assert ok and why == ()

    for kwargs, expect in (
            (dict(lwl_m=1.0, fn=0.32, re=9.2e5), "below the supported 2.5"),
            (dict(lwl_m=30.0, fn=0.20, re=5e7), "above the supported 24.0"),
            (dict(lwl_m=3.0, fn=1.10, re=1.6e7), "past the planing onset"),
            (dict(lwl_m=10.0, fn=0.25, re=3.0e5), "below 5e+05"),
            (dict(lwl_m=10.0, fn=0.25, re=3.0e7,
                  topology=Topology.TRIMARAN), "not evaluable"),
    ):
        ok, why = supported_domain(**kwargs)
        assert not ok, kwargs
        assert any(expect in r for r in why), (expect, why)


def test_out_of_domain_is_not_a_verdict_on_the_boat():
    """A design outside the domain is UNADDRESSED, not bad. The receipt says
    so on its own axis, so nobody reads "we do not model this" as "this hull
    is wrong" — and, just as important, nobody runs it through machinery
    calibrated for something else and reports the number."""
    ev = evaluate_hull(np.array(KIT_REFERENCE), MissionSpec())
    assert ev.in_domain and ev.domain_reasons == ()
    d = ev.to_dict()
    assert d["in_domain"] is True and d["domain_reasons"] == []
