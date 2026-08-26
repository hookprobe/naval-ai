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

#: THE ONE HOME of the kit reference is tests/test_manufacturing.py
#: (KIT_REFERENCE_PARAMS). This file carried a private COPY of the
#: sixteen-gene original, and on 2026-08-27 the copy went stale the exact
#: way copies do: manufacturing RE-PROVED the kit hull with a full bow
#: after the `shape` row landed (the old lens form is truthfully
#: SPEARHEAD-refused now), and this file's copy kept describing the
#: refused boat — so `status` read REFUSED where the test expected the
#: unsolved-design MARGINAL/UNMEASURED. A fixture declared twice is the
#: number-declared-twice defect wearing a test file.
from tests.test_manufacturing import KIT_REFERENCE_PARAMS as KIT_REFERENCE


def test_the_four_questions_stay_four_verdicts():
    """A REFUSED while B (the model) and C (meshability) are both OK. One flag
    could not carry that: "invalid" would send someone to the physics or the
    mesher for a HULL-side refusal. That is the whole reason the operator's
    rule is four verdicts and not one.

    THE EXAMPLE MOVED 2026-08-20 AND THE CLAIM DID NOT. This used to assert
    the reference hull was refused specifically on "the 18 mm-ply cold-bend
    radius". The operator adopted LAMINATED construction that day
    (`limits.laminate_plan`): two skins each bend at their own thickness, so
    an 18 mm bottom needs 0.72 m instead of 1.44 m, and this hull's radius is
    no longer the binding constraint. MEASURED across 30 draws of the flagship
    brief, bend-radius refusals fell 17/30 -> 3/30 and feasible designs rose
    2/30 -> 7/30.

    So the hull is still REFUSED — now on its loading conditions — and the
    four-verdict separation is what this test exists to pin. Asserting the
    particular reason was incidental and made the test a hostage to a
    construction method. What is asserted instead is that the refusal is a
    HULL-side one and that B and C are untouched by it, which is the actual
    claim.
    """
    # THE MID-BOX HULL NOW PASSES A, and this test moved twice in one day
    # because of it. It first asserted a cold-bend refusal; the laminate
    # removed that and it became a loading-state refusal; then the crowd-state
    # trim bar was found to be the DESIGN bar applied to crew movement, and
    # with trim reported rather than gated the hull comes back MARGINAL.
    #
    # Chasing the example through three states is exactly why the example was
    # never the claim. What this test is FOR is that A, B, C and D are FOUR
    # SEPARATE VERDICTS -- one flag could not carry "the hull is refused while
    # the model and the mesher are fine" -- so it asserts the separation and
    # stops pinning which verdict the fixture happens to hold.
    ev = evaluate_hull(np.array(mid_params()), MissionSpec())
    assert ev.model_verdict == OK
    assert ev.mesh_verdict == OK
    # D is UNMEASURED whatever A says: nothing has solved this hull
    assert ev.result_verdict == UNMEASURED
    # the four are independent fields, not one flag wearing four names
    assert len({id(ev.hull_verdict), id(ev.model_verdict),
                id(ev.mesh_verdict), id(ev.result_verdict)}) >= 2
    # and A's verdict must be one of the declared vocabulary, with a reason
    # whenever it is not OK
    assert ev.hull_verdict in (OK, MARGINAL, REFUSED, UNMEASURED)
    if ev.hull_verdict != OK:
        assert ev.reasons, (
            f"hull_verdict {ev.hull_verdict} with no reason is a bare bar")
    # the refusal must be a HULL question, not the model's or the mesher's —
    # that separation is the point, and a reason mentioning neither would mean
    # the verdict and its explanation had come apart
    assert not any("mesh" in r.lower() or "cells per wavelength" in r.lower()
                   for r in ev.reasons), ev.reasons


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


# ---------------------------------------------------------------------------
# QUESTION D: is the RESULT converged and physically trustworthy?
# ---------------------------------------------------------------------------


def _solved_case(tmp_path, drag=-900.0, n=200, t_end=120.0, yplus=None):
    """A settled, physically sane case — the fixture the D verdict grades."""
    from tests.test_settled_drag import _write_case

    t = np.linspace(t_end / n, t_end, n)
    press = drag * 0.7 * (1.0 + 0.004 * np.sin(9.0 * t))
    visc = drag * 0.3 * (1.0 + 0.004 * np.cos(7.0 * t))
    case = _write_case(tmp_path, t, press, visc, symmetric=False,
                       lwl=10.0, speed=2.5)
    if yplus is not None:
        p = case / "case.info"
        p.write_text(p.read_text() + f"\nyplus_achieved={yplus}\n")
    return case


def test_D_is_marginal_without_a_yplus_receipt_and_never_assumes_it_held():
    """The wall model's validity is a SEPARATE measurement from settledness,
    and its receipt comes from the solver node. Absent, the clause is
    UNMEASURED — so the verdict is MARGINAL, not OK. A verdict that silently
    drops the clause it cannot check is the defect this layer exists for."""
    from navalai.contract import judge_result

    verdict, reasons, detail = judge_result(_solved_case(tmp_path_factory()))
    assert verdict == MARGINAL
    assert "unverified" in reasons[0]
    assert detail["yplus_achieved"] is None
    assert "UNMEASURED, not assumed" in detail["yplus_note"]


def tmp_path_factory():
    import tempfile
    from pathlib import Path
    return Path(tempfile.mkdtemp()) / "case"


def test_D_refuses_a_sign_flipped_result_and_an_out_of_band_wall_model():
    """The two clauses that can REFUSE, each on its own evidence."""
    from navalai.contract import judge_result

    flipped = _solved_case(tmp_path_factory(), drag=+900.0, yplus=100.0)
    v, why, _ = judge_result(flipped)
    assert v == REFUSED and any("tow convention" in r for r in why)

    bad_wall = _solved_case(tmp_path_factory(), yplus=7500.0)
    v, why, _ = judge_result(bad_wall)
    assert v == REFUSED and any("log-law band" in r for r in why)

    good = _solved_case(tmp_path_factory(), yplus=100.0)
    v, why, _ = judge_result(good)
    assert v == OK, why


def test_the_contract_asks_D_only_when_given_a_case():
    """Without a case directory D is UNMEASURED — and `status` therefore
    refuses to read OK for a hull nothing has solved."""
    from navalai.contract import judge_result

    ev = evaluate_hull(np.array(KIT_REFERENCE), MissionSpec())
    assert ev.result_verdict == UNMEASURED and ev.status != OK

    v, why, _ = judge_result("/nonexistent/case")
    assert v == UNMEASURED and "does not exist" in why[0]


def test_both_halves_of_the_prescription_carry_their_evidence_status():
    """NEITHER HALF OF THIS PRESCRIPTION IS A DEFAULT, and the receipt says
    so — because both were measured and both fell short of the rule that was
    declared BEFORE the data.

    LAYERS (Mac Block 3): reducing below the writer's derived count is
    unsupported and the 5-7 m arm was worse on coverage AND skew.
    SCALE (Mac NEXT-1): the C arm separated the mechanism exactly — max
    skewness IDENTICAL between C and B to five decimals where they share a
    scale while layer counts differ by 1 and 2, so layers move skewness by
    NOTHING and scale moves it on every band. But the SIGN of the scale
    effect flips with baseline mesh health (+13%, +41%, -29%, -58%,
    monotone in the unscaled arm's skewness, crossover near 4.6-5.8), so a
    universal bump is refuted.

    This test exists so that the day either half is promoted to a default,
    the promotion has to delete a sentence that says it is not one.
    """
    p = mesh_prescription(lwl_m=11.36, speed_ms=2.639, fn=0.25)
    assert "RECEIPT ONLY" in p.basis["mesh_density_evidence"]
    assert "RECEIPT ONLY" in p.basis["n_layers_evidence"]
    assert "refuted" in p.basis["mesh_density_evidence"]
    # the numbers are still DERIVED and still reported — a receipt is not a
    # blank, it is a measured recommendation with its evidence attached
    assert p.mesh_density is not None and p.n_layers is not None


def test_the_supported_domains_lower_edge_is_derivable_from_two_constants():
    """WHY THE 2.5-3.0 m COVERAGE BAND CAME BACK EMPTY, and it is not a
    sampling accident.

    A hull can only be handed to the full-fidelity chain if it is BOTH
    fully turbulent (Re >= RE_TRANSITION_BAND[1]) and inside the thin-ship
    envelope (Fn <= FN_MICHELL_MAX). Those two conditions fight each other
    as length falls, because Re = Fn * sqrt(g) * L^1.5 / nu: shrinking the
    hull costs Reynolds number as L^1.5 while the Froude ceiling is fixed.
    Setting them equal gives the shortest hull for which the window is not
    empty, in closed form:

        L = (Re * nu / (Fn * sqrt(g)))^(2/3) = 2.61 m

    MEASURED CONSEQUENCE across the band, at nu = 1.19e-6:
        2.50 m needs Fn 0.48 for Re 5e6 — PAST the Michell limit
        2.75 m needs Fn 0.42 — just inside
        3.00 m needs Fn 0.37 — comfortably inside
    so the band is not uniformly out of scope; its BOTTOM is and its TOP is
    not, and the crossover sits at 2.61 m.

    THIS IS THE THIRD INDEPENDENT ROUTE TO THE SAME NUMBER.
    docs/research/SMALL-CRAFT-REGIMES.md derived ~2.6 m from three physical
    walls (Reynolds, environment, cube-law payload); the RCD scope that
    `supported_domain` enforces starts at 2.5 m for a legal reason that has
    nothing to do with either. Getting 2.61 m out of two constants the code
    already owns is a check on the research, not a restatement of it.
    """
    from navalai.limits import RE_TRANSITION_BAND, min_lwl_for_full_fidelity_m
    from navalai.resistance import FN_MICHELL_MAX, NU_FRESH_15C
    from navalai.constants import NU_SEA_HOLTROP, G_STANDARD

    # 2026-08-20: this test used to type `nu, g = 1.19e-6, 9.81` INLINE and
    # import neither, while the commit it fences advertised "2.61 m from two
    # constants the code already owns". It was two owned constants plus a
    # literal -- and that literal is a SEAWATER viscosity, while the prose
    # making the same argument at limits.py:284 cites the FRESH one. Same
    # formula, two fluids, 2.8% apart in L. Both are now IMPORTED and the
    # edge is computed by the one function that owns the closed form.
    lwl_fresh = min_lwl_for_full_fidelity_m(
        NU_FRESH_15C, FN_MICHELL_MAX, G_STANDARD)
    lwl_sea = min_lwl_for_full_fidelity_m(
        NU_SEA_HOLTROP, FN_MICHELL_MAX, G_STANDARD)
    assert 2.53 < lwl_fresh < 2.55, lwl_fresh   # MEASURED 2.5386
    assert 2.60 < lwl_sea < 2.62, lwl_sea       # MEASURED 2.6098

    # THE FLUID IS THE DOMINANT UNCERTAINTY, so the third digit of "2.61" is
    # not supportable and this test refuses to assert it. Sensitivity is
    # +3.31% in L per +5% in nu; the fresh/sea span is 4.2% in nu.
    assert lwl_sea > lwl_fresh
    assert 0.02 < (lwl_sea - lwl_fresh) < 0.09, (lwl_sea, lwl_fresh)
    lwl = lwl_sea

    # and the band's own ends behave as the closed form says -- checked for
    # BOTH fluids, because the edge moves with nu and a claim about "the
    # band" that only holds for one of them is a claim about that fluid.
    def fn_for_turbulent(L, nu):
        return RE_TRANSITION_BAND[1] * nu / (L * math.sqrt(G_STANDARD * L))

    for nu in (NU_FRESH_15C, NU_SEA_HOLTROP):
        assert fn_for_turbulent(2.50, nu) > FN_MICHELL_MAX   # window empty
        assert fn_for_turbulent(3.00, nu) < FN_MICHELL_MAX   # window open


def test_the_derived_full_fidelity_edge_is_ENFORCED_and_is_not_the_legal_bound():
    """M1/M2, MEASURED 2026-08-20: the derived edge had NO CODE PATH.

    `a62bf48` published the 2.61 m lower edge, tested it and documented it,
    and `supported_domain` went on enforcing `RCD_HULL_LENGTH_SCOPE_M[0]`
    = 2.5 m, which is a LEGAL scope and not a physical one. MEASURED before
    the fix: `supported_domain(lwl_m=2.55)` returned `in_domain=True`, so a
    hull between the legal bound and the physics edge passed the gate with
    no honest friction line beneath it.

    The two bounds answer DIFFERENT QUESTIONS and this test pins that they
    stay separate reasons -- a legal scope and a regime boundary collapsed
    into one number is how "we do not model this" becomes "this is
    impossible".
    """
    from navalai.contract import supported_domain
    from navalai.limits import min_lwl_for_full_fidelity_m
    from navalai.resistance import FN_MICHELL_MAX, NU_FRESH_15C
    from navalai.constants import NU_SEA_HOLTROP, G_STANDARD

    for nu in (NU_FRESH_15C, NU_SEA_HOLTROP):
        edge = min_lwl_for_full_fidelity_m(nu, FN_MICHELL_MAX, G_STANDARD)
        just_under = edge - 0.01
        just_over = edge + 0.01
        assert just_under > 2.5, "fixture must sit ABOVE the legal bound"

        ok_under, why_under = supported_domain(lwl_m=just_under, nu_m2_s=nu)
        assert not ok_under, (
            f"a hull at {just_under:.3f} m is inside the RCD scope but below "
            f"the derived edge {edge:.3f} m and was NOT refused")
        joined = " ".join(why_under)
        assert "REGIME boundary" in joined, (
            "the refusal must say it is a regime boundary, not an "
            "impossibility: " + joined)
        assert f"{nu:.4g}" in joined, "the refusal must NAME the fluid"

        ok_over, _ = supported_domain(lwl_m=just_over, nu_m2_s=nu)
        assert ok_over, f"{just_over:.3f} m is above the edge and must pass"

    # AND IT MUST NOT INVENT A FLUID. With no `nu` there is no edge, and
    # guessing one is the defect that produced the 2.61-vs-2.54 split.
    ok_nofluid, _ = supported_domain(lwl_m=2.55)
    assert ok_nofluid, ("with no fluid given the physics edge must not be "
                        "applied at all -- refusing to guess is the point")


def test_every_prescribed_number_carries_its_PROVENANCE_and_its_KIND():
    """M4 (operator brief SS10), MEASURED 2026-08-20.

    `MeshPrescription`'s docstring claimed "every field is either inverted
    from a floor this repository measured or marked as not derivable". Of
    the 15 fields a real hull populates, ELEVEN carried no `basis` entry:
    cells_per_wavelength, target_yplus, all three cell sizes,
    hull_refine_levels, n_layers_cap, timestep_s, cells, wall_s, ram_gb.

    The derivations were not missing -- they sat in COMMENTS beside the
    arithmetic. What was missing is that the OBJECT A CALLER READS carried
    them. A docstring asserting provenance the object does not carry is
    worse than no claim, because it stops the next reader from looking.

    Both halves are fenced: no populated field without a basis, and no basis
    that does not declare its KIND. The kind is the load-bearing part -- the
    brief's SS10 asks that an empirical value be labelled empirical and a
    receipt kept receipt-only, so that a reader never has to infer how much a
    number is worth.
    """
    import math as _math

    from navalai.contract import BASIS_KINDS, mesh_prescription

    for lwl, speed in ((7.3, 2.11), (12.0, 3.0), (3.0, 1.2)):
        fn = speed / _math.sqrt(9.81 * lwl)
        pres = mesh_prescription(lwl, speed, fn)
        fields = {k: v for k, v in pres.to_dict().items()
                  if k not in ("basis", "refusals")}

        unbacked = [k for k, v in fields.items()
                    if v is not None and k not in pres.basis]
        assert not unbacked, (
            f"prescribed with NO provenance at Lwl {lwl} m: {unbacked}")

        unlabelled = [k for k, v in pres.basis.items()
                      if not str(v).startswith(tuple(BASIS_KINDS))]
        assert not unlabelled, (
            f"basis entries that do not declare a kind {BASIS_KINDS}: "
            f"{unlabelled}")

        # and the labels must not all collapse to one word, which would make
        # the vocabulary decorative rather than informative
        kinds = {str(v).split(":")[0] for v in pres.basis.values()}
        assert len(kinds) >= 3, (
            f"only {kinds} used — a provenance vocabulary that never "
            f"distinguishes is not distinguishing anything")


def test_a_RECEIPT_ONLY_number_says_so_and_is_not_dressed_as_a_derivation():
    """The three that must never silently become rules.

    `hull_refine_levels` and `n_layers_cap` are envelopes measured on this
    tree's own hulls, and `n_layers` rests on a single experiment. Each is
    DERIVED arithmetic in the sense that an equation produces it — and the
    stronger claim is what a reader acts on, so the receipt label wins.
    """
    import math as _math

    from navalai.contract import BASIS_RECEIPT, mesh_prescription

    pres = mesh_prescription(7.3, 2.11, 2.11 / _math.sqrt(9.81 * 7.3))
    for field in ("hull_refine_levels", "n_layers_cap", "n_layers"):
        if pres.to_dict().get(field) is None:
            continue
        assert pres.basis[field].startswith(BASIS_RECEIPT), (
            f"{field} is a measured envelope and must be labelled "
            f"{BASIS_RECEIPT!r}, not dressed as a derivation: "
            f"{pres.basis[field][:80]}")


def _mid_genome(**over):
    import numpy as _np
    from navalai import grammar as _g
    d = {n: 0.5 * (lo + hi)
         for n, lo, hi in zip(_g.NAMES, _g.LOW, _g.HIGH)}
    d.update(over)
    return _g.vector(d)


def test_the_contract_states_its_COST_and_whether_it_must_ESCALATE():
    """M5 (operator brief SS9), MEASURED 2026-08-20.

    The contract is required to determine "expected cost" and "escalation
    requirement" and did neither as a FIELD. The cost sat on
    `mesh.wall_s` -- 39474 s, ELEVEN HOURS, on a mid-box genome -- where a
    caller had to know to read through to the mesh prescription, and
    escalation was implied by the tier and never stated.

    NEITHER FIELD MAY DECIDE ANYTHING NEW. SS9 says one authoritative
    calculation, so `escalation_required` reads the tier `select_fidelity`
    already chose and `expected_cost_s` reads the estimate `mesh` already
    carries. This test pins the CONSISTENCY, which is what would break if
    someone later grew a second rule here.
    """
    from navalai.contract import evaluate_hull
    from navalai.select_fidelity import TIER_FULL_CFD, TIER_LOW_FIDELITY_CFD

    ev = evaluate_hull(_mid_genome())
    assert isinstance(ev.escalation_required, bool)
    assert ev.escalation_why, "an escalation decision with no reason is a guess"

    needs_cfd = ev.fidelity_tier in (TIER_FULL_CFD, TIER_LOW_FIDELITY_CFD)
    if ev.in_domain:
        assert ev.escalation_required == needs_cfd, (
            f"escalation {ev.escalation_required} disagrees with the tier "
            f"{ev.fidelity_tier} that select_fidelity chose — a SECOND rule "
            f"has grown here")

    # a cheap answer must not carry a CFD price tag, and vice versa
    if ev.escalation_required:
        assert ev.expected_cost_s and ev.expected_cost_s > 0.0
    else:
        assert not ev.expected_cost_s

    assert "expected_cost_s" in ev.to_dict()
    assert "escalation_required" in ev.to_dict()


def test_a_REFUSED_genome_does_not_report_itself_IN_the_supported_domain():
    """FAIL CLOSED. MEASURED 2026-08-20: `in_domain` defaulted to True and
    neither early REFUSED return set it, so a genome the grammar rejected
    came back `in_domain=True` with `lwl_m=None` — "yes, inside the
    supported domain" about a hull with no length.

    That is this repository's oldest defect class, an absence rendered as a
    result, and the same move as `${VAR:-0}` turning "could not measure"
    into "perfect". The default is now False and the reason distinguishes
    NOT REACHED from OUT OF SCOPE, because collapsing those two is how "we
    never asked" becomes "we checked and it failed".
    """
    from navalai.contract import REFUSED, evaluate_hull

    ev = evaluate_hull(_mid_genome(LWL=2.5))
    if ev.hull_verdict != REFUSED:
        import pytest
        pytest.skip("this genome now solves; pick another refusal fixture")

    assert ev.lwl_m is None
    assert ev.in_domain is False, (
        "a refused genome reported itself inside the supported domain")
    assert ev.domain_reasons, "a False in_domain with no reason is a bare bar"
    joined = " ".join(ev.domain_reasons)
    assert "never REACHED" in joined, (
        "the reason must say the question was not reached, NOT that the "
        "design is out of scope: " + joined[:120])


def test_the_derived_edge_is_reached_on_the_MAIN_path_not_only_in_the_helper():
    """The fix that was enforced by nobody.

    `d37b212` taught `supported_domain` the derived full-fidelity edge and
    `evaluate_hull` went on calling it with NO `nu`, so the edge never
    applied on the path everything actually uses. The fluid is now inverted
    from the Re that was already computed (nu = U*L/Re), which is what keeps
    it the SAME water rather than a second constant to drift.
    """
    from navalai.contract import evaluate_hull
    from navalai.resistance import NU_FRESH_15C

    ev = evaluate_hull(_mid_genome())
    assert ev.re and ev.lwl_m and ev.speed_ms
    nu_implied = ev.speed_ms * ev.lwl_m / ev.re
    assert nu_implied == pytest.approx(NU_FRESH_15C, rel=1e-6), (
        f"the domain edge would be judged in {nu_implied:.4g} m2/s while the "
        f"resistance tier used {NU_FRESH_15C:.4g} — two fluids again")


def test_the_MINIMUM_STATE_VECTOR_for_a_numerical_prescription():
    """M7 (operator brief SS5): the smallest set of inputs sufficient to
    determine the numerical treatment.

    The brief lists ~20 candidate variables (LWL, B, T, displacement, Cp,
    LCB, Fn, Re, curvature, minimum feature size, wave length, hull family,
    multihull separation, mesh scale, prism layers, background density,
    free-surface refinement, y+, geometric tau) and asks which are
    INDEPENDENT. MEASURED 2026-08-20 against the code:

        X_mesh = { Lwl, U, y+_target }

    Everything else is either DERIVED from these (Fn = U/sqrt(g*Lwl),
    Re = U*Lwl/nu, wavelength = 2*pi*U^2/g) or is an OUTPUT of the
    prescription rather than an input to it (mesh scale, background density,
    free-surface refinement, prism layers, tau, timestep).

    SUFFICIENT: the prescription is a pure function of these three —
    identical inputs give an identical object.
    MINIMAL: each of the three moves it, so none can be dropped.

    SCOPE, STATED SO IT IS NOT OVER-CLAIMED. This is the state vector for
    the PRESCRIPTION — what numbers to use. It is NOT sufficient for
    NUMERICAL ADMISSIBILITY, which is the separate question of whether a
    given geometry can be meshed at all: `admissibility.screen` takes the
    whole `Hull`, because tightest-feature and curvature genuinely enter
    there. Brief SS6's C and D are different questions and stay different.
    """
    import math as _math

    from navalai.contract import mesh_prescription

    g = 9.80665
    ref_l, ref_u, ref_yp = 7.3, 2.11, 100.0

    def pres(lwl=ref_l, u=ref_u, yp=ref_yp):
        return mesh_prescription(lwl, u, u / _math.sqrt(g * lwl), yp).to_dict()

    base = pres()

    # SUFFICIENT — a pure function of the three
    assert pres() == base, "the prescription is not deterministic"

    # MINIMAL — drop-one: each input must move the result
    for label, kw in (("Lwl", {"lwl": 8.0}),
                      ("U", {"u": 2.5}),
                      ("y+", {"yp": 30.0})):
        moved = [k for k, v in pres(**kw).items()
                 if k != "basis" and base[k] != v]
        assert moved, (
            f"{label} is in the claimed state vector but changing it moved "
            f"NOTHING — it is redundant and the vector is not minimal")

    # y+ must be the NARROW one: it touches the wall model, not the volume
    # mesh. If it ever starts moving the background cell, the derivation has
    # been rewired and this vector needs re-deriving.
    yp_moved = {k for k, v in pres(yp=30.0).items()
                if k != "basis" and base[k] != v}
    assert "background_cell_m" not in yp_moved, (
        "y+ moved the BACKGROUND cell; the wall model and the volume mesh "
        "have become entangled")
    assert "first_layer_m" in yp_moved


def test_Fn_is_DERIVED_and_a_supplied_one_that_contradicts_is_refused():
    """Fn is not a fourth state variable — it is U/sqrt(g*Lwl).

    Taking it as an independent argument is this codebase's cardinal defect
    (a number declared twice) wearing an argument list, and MEASURED
    2026-08-20 it could CONTRADICT its own inputs in silence: passing double
    the true Fn was accepted and swung `mesh_density` from 1.0175 to 0.2632,
    a 4x change in the delivered mesh, with no refusal recorded.
    """
    import math as _math

    from navalai.contract import (FN_CONSISTENCY_REL_TOL, mesh_prescription)

    lwl, u = 7.3, 2.11
    fn_true = u / _math.sqrt(9.80665 * lwl)

    derived = mesh_prescription(lwl, u)                 # omitted -> derived
    supplied = mesh_prescription(lwl, u, fn_true)       # consistent
    assert derived.mesh_density == supplied.mesh_density
    assert not [r for r in derived.refusals if "CONTRADICTS" in r]

    liar = mesh_prescription(lwl, u, fn_true * 2.0)
    contradiction = [r for r in liar.refusals if "CONTRADICTS" in r]
    assert contradiction, (
        "a doubled Fn was accepted in silence — the prescription trusted an "
        "input that disagrees with the two inputs it is computed from")
    assert "DERIVED" in contradiction[0]
    # and it must fall back to the derivation, not to the lie
    assert liar.mesh_density == derived.mesh_density

    # a rounded fixture is NOT a contradiction: two-sig-fig Fn and the
    # 9.80665/9.81 gravity ambiguity both sit inside the documented bar
    rounded = mesh_prescription(12.0, 1.5, 0.14)
    assert not [r for r in rounded.refusals if "CONTRADICTS" in r], (
        "a legitimately rounded Fn was treated as a contradiction; the bar "
        f"({100 * FN_CONSISTENCY_REL_TOL:.0f}%) is too tight")

    # a missing pair still refuses rather than defaulting
    assert mesh_prescription(None, None).refusals
