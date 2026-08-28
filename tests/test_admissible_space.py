"""The admissible design space, attacked (meshability-math directive §16/§17).

Every deliberately pathological hull below must be refused BEFORE OpenFOAM,
by the NAMED gate — L0 (`grammar.check`) for geometry the section law cannot
deliver, the admissibility screen (`Report.refused_no_rescue`) for geometry
the MESH cannot represent, and the case writer for both. The full derivation
of each inequality is docs/MESHABILITY_MATH.md; the layering is:

    L0 (case-independent, ~4-6 ms):  bounds, proportions, freeboard,
        sac.target, section.solve (1921-station probe), chine.submerged,
        panel.twist — refuses what the SECTION LAW cannot build.
    screen (case-dependent, ~10-230 ms): feature-size vs the cell the case
        derives — refuses what the MESHER cannot represent; the un-rescuable
        subset guards `write_resistance_case`.
    run-case.sh (owns the mesh): checkMesh bars + the layer-backoff ladder +
        the flow-time-scale early abort (1e-12 s) — enforces on the meshes
        the screens cannot see.

Vectors are CONSTRUCTED as named mutations of the reference genome (or drawn
from a pinned seed), so each test feeds the gate the verbatim input it must
reject (docs/LESSONS.md defect class 3).
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from navalai import grammar
from navalai.admissibility import Verdict, screen
from navalai.evaluate import sample_valid
from navalai.geometry import Hull
from navalai.mission import MissionSpec
from navalai.reference import reference_params


def _mut(**kw) -> np.ndarray:
    d = grammar.named(reference_params())
    d.update(kw)
    return grammar.vector(d)


def _clauses(x) -> dict[str, list[str]]:
    rep = grammar.check(x)
    out: dict[str, list[str]] = {}
    for v in rep.violations:
        out.setdefault(v.split(":")[0], []).append(v)
    return out


# ---------------------------------------------------------------------------
# §16 — L0 refuses what the section law cannot deliver (case-independent)
# ---------------------------------------------------------------------------

def test_L0_refuses_an_unreachable_prismatic_target():
    """Cp at the gene floor with the max-area station fully aft and a fat
    transom: the SAC family (exponents in [-6, 8]) cannot remove that much
    area. Named clause: sac.target — refused, never approximated (plate P1).
    """
    c = _clauses(_mut(Cp=0.525, x_mb=0.68, r_transom=0.50))
    assert "sac.target" in c, c


def test_L0_refuses_an_unreachable_lcb_target():
    """LCB at the +3 %LWL band edge with a FORWARD-starved area curve
    (x_mb at the aft end of ITS bound, low Cp): the closed-form bracket in
    `sac_exponents` cannot reach it. Named clause: sac.target."""
    c = _clauses(_mut(lcb=3.0, Cp=0.525, x_mb=0.40))
    assert "sac.target" in c, c


def test_L0_refuses_a_section_asked_for_more_area_than_it_can_hold():
    """Steep deadrise + full rocker (shallow aft draft) + a full aft SAC:
    A > d^2/tan(beta) at the transom — the chine would pierce the waterline.
    The discriminant of the section quadratic goes negative and the 1921-
    station probe catches it wherever it happens. Named: section.solve."""
    c = _clauses(_mut(beta_mid=25.0, beta_bow=50.0, rocker=0.6,
                      r_transom=0.5, Cp=0.71, x_mb=0.68))
    assert "section.solve" in c, c
    assert any("unreachable" in v for v in c["section.solve"])


def test_L0_refuses_a_flare_that_consumes_the_half_beam():
    """tan(25 deg) * 1.4 m of draft exceeds the 0.65 m half-beam: the topside
    alone is wider than the boat. `_stations` raises (GeometryError) and
    check() reports it as section.solve — alongside the B/T bound, which the
    same geometry also violates; both must fire, neither may mask the other.
    """
    c = _clauses(_mut(flare=25.0, BWL=1.3, T=1.4, D=1.9))
    assert "section.solve" in c, c
    assert any("consumes the whole" in v for v in c["section.solve"])
    assert "B/T" in c


def test_L0_refuses_tumblehome_that_closes_the_sheer():
    """Max tumblehome (-5 deg) on a fine, high-sided aft body drives the
    delivered sheer past the centreline. THE LOAD-BEARING HALF: this is the
    refusal that made `admissibility.sheer_collapse_cells` a stale copy —
    the kernel refuses at L0 what the old kernel silently clamped."""
    c = _clauses(_mut(flare=-5.0, r_transom=0.05, Cp=0.525, x_mb=0.68,
                      rocker=0.6, sheer_rise=0.5, D=2.5, T=0.6))
    assert "section.solve" in c, c
    assert any("tumblehome closes the sheer" in v for v in c["section.solve"])


def test_L0_refuses_an_unbuildable_panel_twist():
    """Flat midship to 45 deg of bow deadrise over 0.15 L: 45 deg/m of local
    twist against the 14 deg/m cold-bend limit. Named: panel.twist, and
    ONLY panel.twist — the vector is otherwise inside every band, so the
    clause cannot hide behind a bound violation."""
    c = _clauses(_mut(beta_mid=0.0, beta_bow=45.0, beta_len=0.15, Cp=0.55))
    assert set(c) == {"panel.twist"}, c


def test_L0_refuses_a_chine_above_the_design_waterline():
    """Drawn from the 10k property sweep (seed 42, index 2083 — regenerated,
    not transcribed): a wide shallow hull whose chine solves ABOVE z=0.
    With the DWL a first-class curve, the closed-form area the kernel
    solves against does not hold there. Named: chine.submerged, and only it.

    Index 569 -> 484 on 2026-08-26: the sweep draws uniforms over the LEGAL
    envelope (grammar.LOW/HIGH), which widened when the Cp gene box was
    decoupled from the Froude target table — so the same uniforms scale to
    different gene values and 569 no longer names a chine.submerged-only
    hull. 484 is the first index in the same sweep whose ONLY clause is
    chine.submerged under the widened envelope.
    """
    # THE SWEEP DRAWS THE CORE GENES ONLY, so index 569 keeps naming the same
    # hull when the genome gains a post-hoc gene. Drawing
    # `size=(10000, N_PARAMS)` re-shapes the whole array the moment the arity
    # moves, and "index 569" then names a different boat while still resolving
    # — the failure mode is a silently different fixture, not an error. The
    # appended genes take their POST_HOC_DEFAULTS, which are proven no-ops, so
    # this is the same hull the clause was measured on.
    core = [i for i, n in enumerate(grammar.NAMES)
            if n not in grammar.POST_HOC_DEFAULTS]
    rng = np.random.default_rng(42)
    Xc = rng.uniform(grammar.LOW[core], grammar.HIGH[core],
                     size=(10000, len(core)))
    x = np.empty(grammar.N_PARAMS)
    x[core] = Xc[484]
    for n, v in grammar.POST_HOC_DEFAULTS.items():
        x[grammar.NAMES.index(n)] = float(v)
    c = _clauses(x)
    assert set(c) == {"chine.submerged"}, c


def test_L0_refuses_nan_and_out_of_box_vectors():
    x = reference_params().copy()
    x[0] = float("nan")
    rep = grammar.check(x)
    assert not rep.ok and rep.violations[0].startswith("finite")
    y = reference_params().copy()
    y[grammar.NAMES.index("BWL")] = grammar.HIGH[grammar.NAMES.index("BWL")] * 2
    assert any(v.startswith("bound[BWL]") for v in grammar.check(y).violations)


# ---------------------------------------------------------------------------
# §16 — the screen refuses what the MESH cannot represent (case-dependent)
# ---------------------------------------------------------------------------

def test_a_sub_cell_sliver_hull_is_refused_before_any_openfoam(tmp_path):
    """RE-BASED 2026-08-19 by the 16-gene confusion table: seed-0 hull 18 —
    this test's original exemplar at 0.26/0.35 cells — meshed CLEAN at
    rung 0 on the metal, refuting the 1.0-cell danger edge in [0.26, 1.0).
    The edge moved to 0.1 cells (labelled-fatal anchors at literal 0.0);
    the SAME hull at MODEL SCALE 0.25 puts its bottom panel at 0.065
    cells — genuinely below anything measured to mesh — and the §16
    acceptance shape holds there: the screen refuses with no rescue and
    the case writer never reaches snappyHexMesh."""
    from navalai.cfd.case import write_resistance_case

    X, _ = sample_valid(19, MissionSpec(), seed=0)
    # full scale: the measured-clean class is ADMITTED now (warn band)
    rep1 = screen(X[18], 2.57, 1.0)
    assert rep1.verdict is not Verdict.DANGEROUS
    assert not rep1.refused_no_rescue
    # model scale: the same feature is sub-0.1-cell and refused, no rescue
    rep = screen(X[18], 2.57, 0.25)
    assert rep.verdict is Verdict.DANGEROUS
    assert "min_bottom_panel_width_cells" in rep.refused_no_rescue
    with pytest.raises(ValueError, match="admissibility screen"):
        write_resistance_case(Hull(X[18]), 2.57, tmp_path / "refused",
                              end_time=1.0, symmetric=True, n_layers=2,
                              scale=0.25)


def test_the_same_hull_is_admissible_when_the_cell_shrinks_with_scale():
    """The screen is a statement about a (hull, speed, scale) CASE, not about
    a hull: at scale 2 the cell halves and seed-0 hull 18's 0.26-cell panel
    reads 0.52 cells — still sub-cell, still refused — while at scale 4 it
    clears 1.0. Feature bars must move with the pipeline's own cell
    derivation, or they are opinions."""
    X, _ = sample_valid(19, MissionSpec(), seed=0)
    v1 = screen(X[18], 2.57, 1.0).get("min_bottom_panel_width_cells").value
    v2 = screen(X[18], 2.57, 2.0).get("min_bottom_panel_width_cells").value
    assert v2 == pytest.approx(2.0 * v1, rel=1e-6), (
        "the feature bar no longer tracks the derived cell size")


# ---------------------------------------------------------------------------
# §17 — the property test: the funnel, its attribution, and its cost
# ---------------------------------------------------------------------------

def test_property_random_genomes_are_gated_cheaply_with_attribution():
    """N=600 uniform-in-box genomes through L0, screen on the passers.

    The committed N is 600 to keep the suite fast; the SAME harness at
    N=10,000 (seed 42, this box, 2026-08-18) measured:
      L0 pass 675/10000 = 6.75% at 4.2-5.6 ms/genome; top refusals
      freeboard.rel 4756, L/B 4489, B/T 3995, section.solve 3983,
      freeboard.abs 3692, deadrise.order 2191, chine.below.sheer 882,
      panel.twist 877, sac.target 606, chine.submerged 79;
      screen on the 675: SAFE 234 / MARGINAL 286 / DANGEROUS 155,
      writer-admissible 626/675 (92.7%), 19.5 ms/genome for the whole
      funnel (docs/MESHABILITY_MATH.md §G records the derivation).
    This pins the funnel's SHAPE, not those exact counts: every refusal
    carries a named clause, no genome escapes both gates unclassified, and
    the amortised cost stays in single-digit milliseconds per genome at L0.
    """
    rng = np.random.default_rng(7)
    N = 600
    X = rng.uniform(grammar.LOW, grammar.HIGH, size=(N, grammar.N_PARAMS))
    t0 = time.perf_counter()
    l0 = [grammar.check(x) for x in X]
    t_l0 = (time.perf_counter() - t0) / N
    # THE PASS-RATE CLAIM IS MEASURED ON THE **DRAW** BOX, NOT THE LEGAL
    # ONE, AND 2026-08-28 IS WHY. The uniform legal draw above went to
    # **0/600** — through no change to any gate. The genome reached 34
    # genes (dwl/cwp_x/rb_* , tunnel, split, rho_bow/rho_len), every one
    # appended under POST_HOC_DEFAULTS at a proven no-op and pinned at
    # (0.0, 0.0) in `_LEGACY_DRAW_ROWS` so recorded populations do not
    # move. `LOW`/`HIGH` are the LEGAL envelope, where those 11 genes are
    # ACTIVE, so a uniform legal draw now asks for a tunnel AND a split
    # AND a fuller waterline AND a warped section at once, on the same
    # hull, at independently random magnitudes. Almost none of those
    # boats exist, and refusing them is the gate working.
    #
    # This is the SAME defect that took the surrogate to a 0.79 median
    # error the same week: the held-out arm drew post-hoc genes active
    # from the uniform legal box while `sample_valid` pins them at their
    # no-ops, so it scored retrains on a hull class the training set
    # structurally cannot contain (0.79 -> 0.146 once matched). Draw from
    # the box you claim a rate over.
    #
    # The legal-box sample above is KEPT and still carries the funnel's
    # SHAPE claims (attribution, cost) — it is the honest stress case, and
    # a gate that cannot attribute a refusal on a wild genome is broken
    # whatever its pass rate.
    Xd = rng.uniform(grammar.DRAW_LOW, grammar.DRAW_HIGH,
                     size=(N, grammar.N_PARAMS))
    l0d = [grammar.check(x) for x in Xd]
    n_ok = sum(r.ok for r in l0d)                 # MEASURED 5/600 = 0.83%
    # Floor 0.01 -> 0.002 on 2026-08-26. `sac_exponents` now inverts the
    # ACTUAL a(x) with pmb/r_stem (audit finding D.4), so a UNIFORM draw
    # over the full 23-gene box mostly asks for contradictions — pmb 0.45
    # alone floors deliverable Cp near 0.60 while the Cp gene draws down to
    # 0.525 — and sac.target now refuses those honestly instead of
    # delivering a silently different Cp. The funnel's SHAPE claims
    # (attribution, cost) are unchanged; consistent draws come from
    # `grammar.sample` (600/600 measured ok same day) or from drawing Cp
    # inside `geometry.cp_band`.
    assert 0.002 < n_ok / N < 0.25, f"{n_ok}/{N} L0 pass"
    for r in l0:
        if not r.ok:
            assert r.violations, "a refusal must carry named clauses"
            for v in r.violations:
                assert ":" in v, f"unattributed violation {v!r}"
    # L0 is milliseconds-per-genome (generous bar: this box runs 4-6 ms
    # under load; the phase-0 single-call bar of ~1 ms lives elsewhere)
    assert t_l0 < 0.05, f"L0 at {1e3 * t_l0:.1f} ms/genome"
    # The writer screen is exercised on the DRAW-box passers for the same
    # reason the rate is: the legal box has none, and a hull with a tunnel
    # and a split and a warped section at once is not the population any
    # writer downstream of this gate will ever be handed.
    reps = [screen(x, 2.57, 1.0) for x, r in zip(Xd, l0d) if r.ok]
    assert reps, "no L0 passer in 600 draws — the box collapsed"
    for rep in reps:
        assert rep.verdict in (Verdict.SAFE, Verdict.MARGINAL,
                               Verdict.DANGEROUS)
        # attribution: every DANGEROUS names its metric, and the writer set
        # is a subset of the refusals
        if rep.verdict is Verdict.DANGEROUS:
            assert rep.refused_by
        assert set(rep.refused_no_rescue) <= set(rep.refused_by) | {
            m.name for m in rep.metrics if m.verdict is Verdict.UNMEASURED}
    # most of what L0 admits must remain writer-admissible: the screen is a
    # guard, not a second grammar (10k measured 92.7%).
    #
    # RE-SCOPED 2026-08-27 (the dwl arity event). A uniform draw over the
    # legal box now has dwl > 0 almost surely, with RANDOM waterline
    # targets nobody designed — and MEASURED on 6000 draws (30 L0-ok, all
    # dwl-active), only 27% of those are writer-admissible: the faired
    # solve builds them and the mesh screen truthfully refuses the thin
    # ridges the un-designed curves produce. That is the screen doing its
    # job on a hull class the PRODUCT never draws (the DRAW box pins the
    # quartet at 0; grammar.sample and every seeded stream are dwl = 0).
    # So the guard-not-second-grammar bar applies to the PRODUCT's own
    # draw, asserted here on grammar.sample; the uniform-box fraction is
    # recorded above as a measurement, not a bar, until the exploring-
    # stream calibration chooses dwl spans that pair targets with the
    # genes that can carry them.
    admissible = sum(1 for rep in reps if not rep.refused_no_rescue)
    assert admissible >= 1, (
        "the uniform box has NO writer-admissible L0-passer at all — "
        "either L0 or the screen moved; re-measure both")
    Xs = grammar.sample(40, np.random.default_rng(5))
    reps_s = [screen(x, 2.57, 1.0) for x in Xs if grammar.check(x).ok]
    assert reps_s, "grammar.sample yielded no L0-ok hulls"
    adm_s = sum(1 for rep in reps_s if not rep.refused_no_rescue)
    assert adm_s / len(reps_s) > 0.75, (
        f"writer admits only {adm_s}/{len(reps_s)} of the PRODUCT's own "
        f"draw — the screen has become a second grammar")
