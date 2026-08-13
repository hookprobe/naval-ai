"""Stage B gate: AST type checker dispatches typologies; bend-radius check
catches unbuildable curvature; 8-D genome encodes/decodes/samples honestly."""

import numpy as np
import pytest

from navalai import grammar
from navalai.evaluate import evaluate, sample_valid
from navalai.geometry import Hull
from navalai.hull_ast import (HullDesign, Typology, infer_typology,
                              type_check)
from navalai.latent import LATENT_DIM, Genome
from navalai.mission import MissionSpec
from tests.test_phase0 import mid_params


# ---------------- AST / typology ----------------

def test_reference_hull_type_checks_as_sharp_chine():
    d = HullDesign.from_vector(mid_params(), Typology.SHARP_CHINE)
    rep = type_check(d)
    assert rep.ok, rep.violations
    assert infer_typology(mid_params()) == Typology.SHARP_CHINE


def test_ast_vector_roundtrip():
    d = HullDesign.from_vector(mid_params(), Typology.SHARP_CHINE)
    assert np.allclose(d.to_vector(), mid_params())


def test_typology_rules_dispatch():
    """The same vector must NOT type-check as a pram (fine entry, raked stem)."""
    d = HullDesign.from_vector(mid_params(), Typology.PRAM)
    rep = type_check(d)
    assert not rep.ok
    assert any("typology[pram]" in v for v in rep.violations)


def test_pram_subspace_type_checks():
    x = mid_params()
    p = grammar.named(x)
    # `"p_bow": 1.5` STOOD HERE AND HAD BEEN DOING NOTHING SINCE THE GENOME
    # LOST THAT GENE — `grammar.vector` builds from `NAMES` and silently drops
    # an unknown key, so the line that was meant to make this vector a pram was
    # a no-op that a green test hid. The pram bands are now `Cp` (0.600-0.710)
    # and `roundness` (0.0-0.25), and they are set explicitly.
    p.update({"Cp": 0.65, "roundness": 0.0, "forefoot": 0.1, "rocker": 0.2,
              "sheer_rise": 0.1, "beta_bow": 12.0, "beta_mid": 6.0})
    xv = grammar.vector(p)
    d = HullDesign.from_vector(xv, Typology.PRAM)
    rep = type_check(d)
    assert rep.ok, rep.violations
    assert infer_typology(xv) in (Typology.SHARP_CHINE, Typology.PRAM)


def test_a_sheet_built_typology_pins_roundness_and_the_generator_projects_it():
    """THE PIPELINE DELIVERED ZERO DESIGNS, AND THIS IS THE NUMBER THAT DID IT.

    `TYPOLOGY_RULES` banded `roundness` at (0.0, 0.15) for SHARP_CHINE and
    (0.0, 0.25) for PRAM, with the in-source comment "a chine, not a bilge
    radius". `unroll.hull_panels` refuses ANY `roundness > 0`, because a
    radiused bilge is a fillet, the filleted strip is doubly curved, and a
    doubly curved strip is not developable from flat sheet — a fact about sheet
    material, not a limitation of the unroller. So the bands and the admissible
    set were disjoint except at the SINGLE POINT `roundness == 0.0`, and
    `type_check` is a pure rejection test, which a continuous sampler passes at
    that point with probability zero.

    MEASURED 2026-08-13 on the Builder's own distribution — `sample_valid(80,
    MissionSpec(), seed=17)` -> `Genome.fit` -> `sample(4096, seed=1,
    temperature=1.0)`:

        pass a typology AS DRAWN                    4 of 4096
        ... of which roundness == 0                 0
        pass after projecting the pin            1594 of 4096
        SHARP_CHINE clause histogram   roundness 4086, forefoot 2180,
                                       Cp 881, beta_bow 315

    Every one of those 4 was refused downstream by `unroll.hull_panels`, by
    `engineer.assess` and by `admissibility`, so `run_plm` delivered ZERO
    records and three tests failed on one cause
    (`test_stageC.py::test_network_delivers_validated_designs`,
    `::test_audit_trail_flows`, and
    `test_end_to_end_flow.py::test_the_manufacturing_stage_builds_the_ply...`).

    THE FIX IS A PROJECTION, NOT A WIDER BAR. Four arms, because no one of them
    catches the mechanism alone: the pin must be a pin and not a band, the
    generator must project onto it, verification must stay EXACT, and the
    refusal must say "pinned" and why. Nothing about the unroller is relaxed —
    `tests/test_geometry_kernel.py::...unroll...` still requires it to refuse
    `roundness = 0.4`.
    """
    from navalai.hull_ast import Pin, TYPOLOGY_RULES, fit_typology, project

    # ARM 1: it is a PIN, in the source, for every sheet-built typology — not a
    # band of some small width that a future edit could widen back.
    for t in Typology:
        rule = TYPOLOGY_RULES[t]["roundness"]
        assert isinstance(rule, Pin), (
            f"typology {t.name} bands `roundness` as {rule!r}. Both declared "
            f"typologies are sheet-built (formlib: hard_chine_displacement is "
            f"'buildable from flat sheet'; pram_dory is the flat-bottom "
            f"skiff), and a band admits fillets the cutter cannot make.")
        assert rule.value == 0.0 and "developable" in rule.why

    # ARM 2: the projection recovers the population. The bar is 1/4 of the 1594
    # measured above — far enough below not to flap on a genome refit, far
    # enough above the 4 that motivated this to name the regression.
    X, _y = sample_valid(80, MissionSpec(), seed=17)
    g = Genome.fit(X)
    Y = g.sample(4096, seed=1, temperature=1.0)
    raw = sum(1 for x in Y if infer_typology(x) is not None)
    fitted = [fit_typology(x) for x in Y]
    projected = sum(1 for f in fitted if f is not None)
    assert projected >= 400, (
        f"{projected} of {len(Y)} genome draws project onto a typology; 1594 "
        f"were measured 2026-08-13 and {raw} passed AS DRAWN. The design path "
        f"is back to rejecting draws for a parameter the typology sets.")
    # and the projected vectors really are sheet-built, and really do
    # type-check on their own — the Validator is not asked to take it on trust.
    ir = grammar.NAMES.index("roundness")
    for f in fitted:
        if f is None:
            continue
        t, y = f
        assert y[ir] == 0.0
        assert infer_typology(y) is not None

    # ARM 3: verification stays EXACT. A hand-written vector at roundness 0.07
    # is inside the OLD sharp-chine band and must still be refused.
    p = grammar.named(mid_params())
    p["roundness"] = 0.07
    rep = type_check(HullDesign.from_vector(grammar.vector(p),
                                            Typology.SHARP_CHINE))
    assert not rep.ok, (
        "roundness 0.07 type-checked as a sharp chine. Projection is for the "
        "generator; the verifier does not project.")

    # ARM 4: the refusal is legible — it says PINNED and it says why, rather
    # than naming a bound a reader would go looking for a tolerance in.
    hits = [v for v in rep.violations if "roundness" in v]
    assert len(hits) == 1, rep.violations
    assert "PINNED" in hits[0] and "developable from flat sheet" in hits[0], hits[0]
    assert "outside [" not in hits[0], (
        f"the pin refusal is printing a band: {hits[0]}")

    # ... and the projection of that same vector is accepted.
    assert type_check(HullDesign.from_vector(
        project(grammar.vector(p), Typology.SHARP_CHINE),
        Typology.SHARP_CHINE)).ok


def test_projection_sets_the_pin_and_touches_nothing_else():
    """`project` is not a repair pass. It sets pinned parameters and leaves
    every band violation exactly where it was — otherwise the generator would
    be quietly editing designs into compliance, which is the defect this
    project calls softening a bar."""
    from navalai.hull_ast import project

    p = grammar.named(mid_params())
    p.update({"roundness": 0.42, "forefoot": 0.05})   # forefoot is a BAND
    x = grammar.vector(p)
    y = project(x, Typology.SHARP_CHINE)
    ir = grammar.NAMES.index("roundness")
    assert y[ir] == 0.0
    assert np.array_equal(np.delete(x, ir), np.delete(y, ir)), (
        "project() moved a parameter that is not pinned")
    rep = type_check(HullDesign.from_vector(y, Typology.SHARP_CHINE))
    assert any("forefoot" in v for v in rep.violations), (
        "the band violation was repaired by the projection")
    assert not any("roundness" in v for v in rep.violations)


def test_type_check_runs_before_geometry():
    """A type-check failure must not require geometry construction: feed a
    vector that violates flat bounds; type_check reports without Hull()."""
    x = mid_params()
    x[0] = 50.0
    rep = type_check(HullDesign.from_vector(x, Typology.SHARP_CHINE))
    assert not rep.ok and any("bound[LWL]" in v for v in rep.violations)


# ---------------- bend radius ----------------

def test_the_bend_radius_metric_is_a_function_of_its_sampling_and_says_so():
    """WAS `test_reference_hull_is_buildable`, AND THE ANSWER IS NOW NO —
    RECORDED, NOT SOFTENED (honesty rule 6), AND THE BAR IS NOT THE PART THAT
    IS WRONG.

    It asserted `Hull(mid_params()).min_bend_radius() > min_bend_radius_m()`
    and passed. On the plate-P1/P2 kernel the reference hull reads 0.954 m
    against the 1.2 m limit for a 15 mm sheet (1.68 m for the rule-derived
    21 mm bottom the ladder actually plans), so it FAILS.

    THE REASON IS NOT THAT THE NEW HULL IS WORSE. `min_bend_radius` takes a
    central-difference curvature along the keel and the chine, and the chine
    has a TANGENT BREAK at the max-area station: the sectional area curve's
    forward and aft branches meet there with different slopes, and so does the
    flare envelope. A central difference straddling a corner measures the
    corner divided by the step, so the reported radius DIVERGES to zero as the
    station count rises. MEASURED on the reference hull at 21 / 41 / 81 / 161 /
    321 / 641 stations:

        plate-P1/P2 kernel   1.777  0.954  0.515  0.277  0.148  0.078
        pre-rebuild kernel   4.184  2.239  1.147  0.578  0.289  0.145

    Both halve with every doubling, and **the pre-rebuild hull also fails the
    1.2 m limit from 81 stations up.** The old number passed at the shipped 41
    only because the sampling was coarse enough to blur the corner. So the
    quantity has never been a property of the boat — it is docs/LESSONS.md
    defect class 1, a value that cannot be measured being scored as if it
    could, and the rebuild's sharper knuckle merely pushed it across the line
    at the configuration the product runs.

    NOTHING IS SOFTENED HERE. `limits.min_bend_radius_m` and
    `Hull.min_bend_radius` are untouched, the ladder still refuses the
    reference hull (see tests/test_ladder.py, where it is the single
    violation), and this test now pins the DIVERGENCE so the ill-posedness
    cannot be quietly re-blessed by someone changing `n_stations`. Closing it
    properly means either making the area curve C1 at the max-area station or
    measuring the corner as a corner, and both are design decisions outside a
    green-the-tree change.
    """
    from navalai.limits import min_bend_radius_m

    h = Hull(mid_params())
    # the refusal, recorded
    assert h.min_bend_radius() == pytest.approx(0.954, abs=0.01)
    assert h.min_bend_radius() < min_bend_radius_m()

    # the divergence, which is why the number above is not a length
    r = {n: Hull(mid_params(), n_stations=n).min_bend_radius()
         for n in (41, 81, 161, 321)}
    for a, b in ((41, 81), (81, 161), (161, 321)):
        assert 1.75 < r[a] / r[b] < 2.05, (
            f"min_bend_radius stopped halving with the station count "
            f"({a}->{b}: {r[a] / r[b]:.3f}) — if it has become a convergent "
            f"quantity, this test is the one to re-derive, and the bar in "
            f"limits.py is then meaningful for the first time")


def test_the_bend_limit_limb_fires_and_names_the_derived_sheet():
    """WAS `test_extreme_rocker_flags_bend_limit`, AND IT WAS NOT TESTING THAT.

    Two things were wrong with it and both are worth writing down.

    1. ITS SECOND HALF NEVER RAN. The assertion was guarded by
       `if ev.hydro is not None and h.min_bend_radius() < 1.2`, and its fixture
       (`mid_params` with LWL 4.2, T 1.2, BWL 1.9) has B/T 1.58 against the
       [1.8, 12.0] band, so `evaluate` refused it at L0 and `hydro` was None.
       The limb this test is named for was never reached — a guard that cannot
       fire (docs/LESSONS.md defect class 3), hidden behind an `if`.
       On the plate-P1/P2 kernel that same fixture does not even build:
       `section: area 0.1424 m^2 unreachable at x = 4.095 m (draft 0.192 m,
       deadrise 27.0 deg)`, because a 1.0 forefoot on a 1.2 m draft lifts the
       keel to within 0.19 m of the waterline while the area curve still asks
       for 0.14 m^2 there.

    2. ITS STATED MECHANISM WAS WRONG. "A 4 m hull with 0.72 m of keel sweep
       bends far tighter" attributes the tight bend to the KEEL. MEASURED on
       the replacement fixture below, curvature along each edge separately:
       the keel's tightest radius is 3.976 m and the CHINE's is 0.301 m, at
       x = 2.668 m against a max-area station at 2.763 m. It is the max-area
       knuckle, on this hull as on the reference one — see
       `test_the_bend_radius_metric_is_a_function_of_its_sampling_and_says_so`
       for what that means about the metric.

    So what this test can honestly establish is the WIRING, which is a real
    gap-fix and is not ill-posed: `evaluate` publishes a `bend_radius` row, the
    violation names the DERIVED sheet thickness rather than a hard-coded 15 mm,
    and a small heavily-rockered hull is refused where the reference hull's own
    refusal is milder. The fixture is L0-clean and FLOATS, so the limb is
    actually reached.
    """
    x = grammar.vector({
        "LWL": 4.1043, "BWL": 1.4613, "T": 0.2663, "D": 0.7254,
        "Cp": 0.6585, "lcb": -2.6991, "x_mb": 0.6731, "r_transom": 0.1193,
        "beta_mid": 14.0707, "beta_bow": 21.5764, "beta_len": 0.3570,
        "roundness": 0.0117, "rocker": 0.4787, "forefoot": 0.7188,
        "flare": 7.8302, "sheer_rise": 0.2008,
    })
    assert grammar.check(x).ok, grammar.check(x).violations
    h = Hull(x)
    assert h.min_bend_radius() == pytest.approx(0.301, abs=0.01)
    assert h.min_bend_radius() < Hull(mid_params()).min_bend_radius()

    ev = evaluate(x, MissionSpec(displacement_target_kg=800))
    assert ev.hydro is not None, "the fixture must FLOAT, or the limb is unreached"
    assert ev.g["bend_radius"] > 0.0
    hits = [v for v in ev.violations if "bend radius" in v]
    assert len(hits) == 1, ev.violations
    # the message carries the sheet the ladder actually planned, not a literal
    assert f"{ev.ply_thickness_m * 1000:.0f} mm ply" in hits[0], hits[0]


# ---------------- 8-D genome ----------------

@pytest.fixture(scope="module")
def genome():
    X, _y = sample_valid(150, MissionSpec(), seed=31)
    return Genome.fit(X, q=LATENT_DIM)


def test_genome_captures_most_variance(genome):
    assert genome.explained > 0.85, f"8-D captures only {genome.explained:.0%}"


def test_genome_roundtrip_accuracy(genome):
    X = genome.X_train[:20]
    X2 = genome.decode(genome.encode(X), project=False)
    rel = np.linalg.norm(X2 - X, axis=1) / np.linalg.norm(grammar.HIGH - grammar.LOW)
    assert np.median(rel) < 0.10


def test_genome_prior_sampling_valid(genome):
    X = genome.sample(40, seed=5)
    assert all(grammar.check(x).ok for x in X)     # gate-guaranteed
    raw = genome.raw_prior_feasibility(150)
    assert raw > 0.30, f"raw prior feasibility {raw:.0%} — latent space junk"


def test_genome_honesty_no_validity_claim(genome):
    """The UNPROJECTED prior must NOT be assumed valid (research finding):
    verify the gate actually does work sometimes."""
    raw = genome.raw_prior_feasibility(300)
    assert raw < 1.0    # if this ever fails, celebrate and update BuildPlan 1.1
