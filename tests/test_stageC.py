"""Stage C gate: agent network produces engineered designs with a clean audit
trail; builder emits parameters only; engineer numbers sane; STEP exports."""

import numpy as np
import pytest

from navalai import engineer, export, grammar
from navalai import hydrostatics as H
from navalai.agents import run_plm
from navalai.engineer import assess
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec
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
# Gate F: the exported solid IS the boat the ladder validated
# ---------------------------------------------------------------------------

def test_the_export_reads_the_section_by_meaning_and_not_by_index():
    """THE MOTIVATING INCIDENT, MEASURED 2026-08-13, and it shipped a sliver.

    `Hull.section()` returned exactly three points — keel, chine, sheer — for
    every hull the pre-plate-P2 kernel could draw, so `pts[0]`, `pts[1]`,
    `pts[2]` WERE the three moulded corners and `export._station_wires` and
    `export.moulded_volume_m3` both read them that way. Plate P2 made the
    section a shape function: at `roundness > 0` it returns 257 points and the
    first three sit a few millimetres apart at the keel. VERIFIED on
    `sample_valid(3, MissionSpec(), seed=0)[0]` (roundness 0.981):

        section() shape                (257, 2)
        first three points span         0.00862 m
        full section span               1.90618 m
        ladder validated volume        11.172241 m^3
        export.moulded_volume_m3        0.000650 m^3     -99.994%

    Read by MEANING — the whole polyline, with `Hull.chine_row` giving the
    bilge row for any sampling — the same hull's exported displacement is
    within 0.032% of the ladder's.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=0)
    h = Hull(np.asarray(X[0], dtype=float))
    assert h.roundness > 0.5, "this test needs a hull with a radiused bilge"
    assert h.section(20).shape[0] > 3, "the section is not a shape function"

    rec = export.export_receipt(h, export._LOFT_STATIONS)
    assert abs(rec["displacement_error_pct"]) < 0.1, rec

    ref = export.export_receipt(Hull(mid_params()), export._LOFT_STATIONS)
    assert abs(ref["displacement_error_pct"]) < 0.1, ref
    assert ref["section_rows"] == 2          # hard chine: keel, chine, sheer
    assert ref["n_stations_exported"] == 161
    assert ref["n_stations_validated"] == 41


def test_the_receipt_can_see_the_between_station_term_it_used_to_sample_past():
    """A RECEIPT THAT SAMPLES ONLY AT THE STATIONS IS BLIND TO THE LOFT.

    `_displaced_volume_of` evaluated at the loft's own stations trapezoids the
    EXACT section areas there — arithmetically the ladder's own integral — so
    at `n_stations == hull.n_stations` it read **0.0000%** and could not see
    the surface between them at all. That is the same shape of defect as the
    `volume_error_pct` it replaced: a cross-check that shares its answer with
    the thing being checked.

    The term it was missing is real and its SIGN is forced. A ruled loft is
    linear in the control points between stations, area is CONVEX in those
    control points, so `A(lerp p) <= lerp(A p)` and the loft can only ever
    enclose LESS than the trapezoid the ladder integrates. MEASURED at a
    41-station loft once the receipt sub-samples: -0.0129% on the reference
    hull and -0.0419% on the worst of `sample_valid(6, seed=0)` — negative on
    every hull, as convexity requires.

    `measure_lofted_displacement` sub-samples between the stations, and
    `_LOFT_STATIONS` (161) is what closes the term rather than merely
    reporting it.
    """
    h = Hull(mid_params())
    coarse = export.export_receipt(h, 41)["displacement_error_pct"]
    shipped = export.export_receipt(h, export._LOFT_STATIONS)[
        "displacement_error_pct"]
    # the term exists, is negative, and is no longer invisible
    assert coarse < 0.0, (
        f"a 41-station loft reads {coarse:+.4f}% — convexity says the loft "
        f"under-encloses, so a non-negative reading means the receipt is "
        f"sampling at the stations again and is blind")
    assert coarse == pytest.approx(-0.0129, abs=0.005)
    # and the shipped loft has converged past it
    assert abs(shipped) < abs(coarse) + 0.05
    assert abs(shipped) < 0.05

    # THE SIGN IS NOT AN ACCIDENT OF ONE HULL. Every hull must under-enclose at
    # a coarse loft, or the mechanism named above is not the mechanism.
    X, _ = sample_valid(6, MissionSpec(), seed=0)
    for i, x in enumerate(X):
        e = export.export_receipt(Hull(np.asarray(x, float)),
                                  41)["displacement_error_pct"]
        assert e <= 0.0, f"hull {i} lofts LARGER than the ladder at 41: {e:+.4f}%"


def test_the_export_receipt_can_fail_and_refuses_the_verbatim_defect():
    """THE RECEIPT COULD NOT FAIL, WHICH IS WHY IT DID NOT.

    `volume_error_pct` divided the lofted solid by `moulded_volume_m3`, and
    both read the section through the SAME index — so when the index read
    collapsed to a sliver, both sides collapsed together and the receipt
    reported a fraction of a percent on a 99.994% error. A cross-check between
    two readings that share a code path is the same number printed twice.

    The receipt's reference is now `hydrostatics.solve`, which derives the
    displacement from `Hull.immersed_section`'s closed-form control points and
    shares nothing with the loft but the hull. THE GUARD IS FED THE VERBATIM
    INPUT IT MUST REJECT: the pre-plate-P2 three-index section, reconstructed
    here rather than described.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=0)
    h = Hull(np.asarray(X[0], dtype=float))
    xs = np.linspace(float(h.x[0]), float(h.x[-1]), h.n_stations)

    # the defect, verbatim: the first three points of the section, read as
    # keel / chine / sheer
    sliver = [np.asarray(h._section_at(float(xv)), dtype=float)[:3] for xv in xs]
    bad = export._displaced_volume_of(xs, sliver, 0.0)
    good = float(H.solve(h, 0.0).volume)
    err = 100.0 * (bad - good) / good
    assert err < -99.0, f"the defect no longer reproduces ({err:.4f}%)"
    assert abs(err) > export.EXPORT_DISPLACEMENT_BAR_PCT

    with pytest.raises(ValueError, match="not the boat that passed the gates"):
        export.refuse_wrong_solid(
            {"displacement_error_pct": err,
             "displaced_volume_m3": bad,
             "ladder_displaced_volume_m3": good}, "STEP")

    # ...and it ACCEPTS the honest one, or it is a refusal and not a bar. The
    # bar sits between measurements: 0.758% is the worst legitimate value over
    # seven hulls (a deliberately coarse 12-station loft) and 99.994% is the
    # defect.
    ok = export.export_receipt(h, h.n_stations)
    export.refuse_wrong_solid(ok, "STEP")
    coarse = export.export_receipt(h, 12)
    assert abs(coarse["displacement_error_pct"]) > \
        abs(ok["displacement_error_pct"]), \
        "a coarser loft must cost something, or the receipt is not measuring it"
    export.refuse_wrong_solid(coarse, "STEP")


def test_the_engineer_refuses_a_round_bilge_as_a_round_bilge():
    """A refusal reported as the WRONG refusal is defect class 1's cousin.

    `unroll.hull_panels` refuses `roundness > 0` because a filleted bilge is
    doubly curved and not developable from flat sheet — a fact about the
    material, not a limitation of the unroller. `engineer.assess` swallowed
    every `ValueError` in its strake search, so on
    `sample_valid(3, MissionSpec(), seed=0)[0]` (roundness 0.981) the unroller's
    own sentence — "take this hull to a mould, not a cutter" — came out as
    "no feasible nesting layout for this hull", which sends the reader to look
    at sheet sizes for a problem that has nothing to do with packing.
    """
    X, _ = sample_valid(3, MissionSpec(), seed=0)
    h = Hull(np.asarray(X[0], dtype=float))
    assert h.roundness > 0.5
    with pytest.raises(ValueError, match="radiused bilge"):
        engineer.assess(h)
    # the negative control: a hard chine still nests, so the refusal is about
    # the bilge and not about this module having stopped working
    assert engineer.assess(Hull(mid_params())).panel_count >= 8


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

    IT CAME BACK, MEASURED 2026-08-20, and passing `mldc_kg` is exactly why.
    On the module's own 6 t Danube mission this test read

        delivered BOM is built to 18.0 mm while the ladder that
        validated it derived 15.0 mm

    with `mldc_kg=mission.displacement_target_kg` being passed the whole time.
    The formula never differed — both sides call `select_stock_thickness_m`.
    ONE ARGUMENT differed: `evaluate()` passes `mission.design_category`, and
    `translate()` reads the Danube mission as category **D**, while
    `engineer.assess` hard-coded "category C default". kDC is 0.4 for D and
    0.6 for C (ISO 12215-5:2008(E) §7.2), so the same hull selects

        select_stock_thickness_m(6000, lwl 15.905, span 400, cat 'D')  15.0 mm
        select_stock_thickness_m(6000, lwl 15.905, span 400, cat 'C')  18.0 mm

    18 > 15 is the conservative direction and not unsafe, but the cut list and
    the ladder that validated the boat still described two different boats.
    Handing the delivery path the RULE'S ARGUMENTS is a second source of the
    number no matter how many of them are forwarded; it now consumes the
    ANSWER, `Evaluation.ply_thickness_m`. See
    `test_the_engineer_consumes_the_ladder_thickness_and_never_re_derives_it`
    for the cheap arm that holds the mechanism directly.
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


def test_the_engineer_consumes_the_ladder_thickness_and_never_re_derives_it():
    """THE MECHANISM OF THE 18.0/15.0 DEFECT, held without running the network.

    The test above needs a ~45 s `run_plm` to see the disagreement at all,
    which is part of why forwarding `mldc_kg` looked like the whole fix. The
    disagreement is cheap to hold directly: on the reference hull at 6 t the
    ISO 12215-5:2008(E) design category alone moves the selected stock sheet

        A 21.0 mm   B 18.0 mm   C 18.0 mm   D 15.0 mm

    so an engineer that assumes a category is choosing a boat's plating from
    an input the mission already declares. Three arms, because no one of them
    catches it alone.
    """
    from navalai import engineer as E
    from navalai.rules.iso12215 import (bottom_panel_dims_mm,
                                        select_stock_thickness_m)

    h = Hull(mid_params())
    lwl = float(h.x[-1])
    b_mm, l_mm = bottom_panel_dims_mm(h)

    # ARM 1: the mechanism is LIVE. If the category ever stops moving the
    # sheet, arms 2 and 3 are testing nothing and this says so out loud.
    t_c = select_stock_thickness_m(6000.0, lwl, design_category="C",
                                   span_mm=b_mm, l_mm=l_mm)
    t_d = select_stock_thickness_m(6000.0, lwl, design_category="D",
                                   span_mm=b_mm, l_mm=l_mm)
    assert t_c == pytest.approx(0.018) and t_d == pytest.approx(0.015), (
        f"category C/D select {t_c * 1e3:.1f}/{t_d * 1e3:.1f} mm — the "
        f"measurement this regression rests on has moved; RE-MEASURE and "
        f"record before editing the numbers")

    # ARM 2: given the ladder's answer, the engineer BUILDS to it — including
    # the category-D sheet its own default would never have picked — and the
    # BOM lines carry the same number, not a note about a nominal sheet.
    rep = E.assess(h, 0.0, bottom_thickness_m=t_d)
    assert rep.bottom_thickness_mm == pytest.approx(15.0), (
        f"the engineer re-derived {rep.bottom_thickness_mm} mm over the "
        f"15.0 mm the ladder handed it — this is the 18.0/15.0 defect")
    bottom = [ln for ln in rep.bom if ln.source_panel.startswith("bottom")]
    assert bottom, "no bottom panel in the BOM"
    for ln in bottom:
        assert ln.thickness_mm == pytest.approx(15.0), ln
        assert "NOT rule-derived" not in ln.note, ln

    # ARM 3: there is exactly ONE source. Accepting the answer AND the rule's
    # arguments is how the two drifted apart, so it is refused; and a
    # thickness that is not a sold sheet is refused rather than nested.
    with pytest.raises(ValueError, match="never both"):
        E.assess(h, 0.0, mldc_kg=6000.0, bottom_thickness_m=t_d)
    with pytest.raises(ValueError, match="not a stock sheet"):
        E.assess(h, 0.0, bottom_thickness_m=0.0163)


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
    # Drawn over the FROZEN DRAW box with post-hoc genes at defaults
    # (2026-08-26): the legal envelope widened past what a blind uniform
    # draw can satisfy, and the measurement this arm rests on was made on
    # the sampler's own distribution — which is the DRAW box.
    rng = np.random.default_rng(0)
    in_box = rejectable = 0
    for _ in range(4000):
        x = rng.uniform(grammar.DRAW_LOW, grammar.DRAW_HIGH)
        for _nm, _v in grammar.POST_HOC_DEFAULTS.items():
            x[grammar.NAMES.index(_nm)] = float(_v)
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
