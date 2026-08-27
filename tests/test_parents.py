"""Gate PARENTS: retrieval + distortion seeding — the industry's method,
not a network's.

P5 of the hull-design gap plan (docs/audit/HULL-DESIGN-AUDIT.md, research
matrix rows "variation of a parent" / "learned generation"): with a corpus
of TENS of hulls, the honest seeding mechanism is a PROVEN parent plus a
low-dimensional distortion (Lackenby's Cp/LCB shift; homothetic
principal-dimension scaling). This suite is the proof burden that comes
with that claim:

  - every parent in the library still builds, still passes L0, and still
    passes the shape critic FOR ITS FAMILY — a decayed parent would seed
    every search with the very shape the critic refuses;
  - the operators deliver what they promise (proportions preserved,
    unreachable targets clipped into the deliverable band, never raised);
  - the barge family bar exists and is MEASURED, because without it P2-A's
    family routing made every houseboat mission's shape row unsatisfiable
    by construction;
  - the genomes have ONE home (`navalai.parents`), and their prover
    (`scripts/hull_kb_reconstruct.py`) imports them back.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from navalai import grammar, morphology, parents
from navalai.geometry import Hull
from navalai.mission import MissionSpec, parse_mission


def _margin(x: np.ndarray, family: str | None) -> float:
    d = morphology.describe(morphology.from_hull(Hull(x)))
    return float(morphology.shape_margin(d, family=family))


def test_every_parent_is_still_a_proven_boat():
    """The library's core bar: L0-valid AND critique-clean for its family.

    `family` here maps through the same rule evaluate() uses: only families
    the bar table knows get special bands; the regime words
    (displacement/planing) are retrieval vocabulary, not bar vocabulary,
    so those parents must clear the GENERAL bars.
    """
    assert len(parents.PARENTS) >= 3
    for p in parents.PARENTS:
        x = grammar.vector(p.genes)
        rep = grammar.check(x)
        assert rep.ok, (p.name, [str(v) for v in rep.violations])
        fam = p.family if p.family in morphology._FAMILY_BAR else None
        assert _margin(x, fam) <= 0.0, (
            f"parent {p.name} fails the shape critic for family {fam!r} — "
            f"a decayed parent seeds every search with a refused shape")
        assert p.provenance, f"parent {p.name} carries no provenance"


def test_the_barge_bar_is_measured_and_the_general_bar_still_refuses_it():
    """MEASURED 2026-08-27: the PROVEN 16x4 barge (88% beam carried,
    59.4 m2 deck — tests/test_barge_bow.py) fails the GENERAL critic on
    plan_waist 0.105 (bar 0.020) and waterline_convexity 0.732 (bar
    0.800), because all 58 corpus hulls are pointed-bow monohulls and a
    pram bow is not in their vocabulary. P2-A routes mission family
    "barge" into the bar table, so WITHOUT the barge row every houseboat
    mission's shape row was unsatisfiable by construction — the demihull
    L/B false positive over again. Both facts are pinned: the barge bar
    accepts the proven barge, and the general bar still refuses it (if the
    general bar ever accepts it, the family row is dead weight and should
    be removed rather than kept as superstition)."""
    barge = next(p for p in parents.PARENTS if p.family == "barge")
    x = grammar.vector(barge.genes)
    assert _margin(x, "barge") <= 0.0, "the barge bar refuses the proven barge"
    assert _margin(x, None) > 0.0, (
        "the GENERAL bar now accepts the pram-bow barge — the barge family "
        "row in morphology._FAMILY_BAR is no longer doing anything; "
        "re-measure and remove it rather than keeping a dead band")


def test_rescale_is_homothetic_unless_told_otherwise():
    cruiser = next(p for p in parents.PARENTS
                   if p.name == "solar-slender-cruiser")
    g = parents.rescale(cruiser.genes, lwl=16.0)
    s = 16.0 / cruiser.genes["LWL"]
    assert g["LWL"] == pytest.approx(16.0)
    assert g["BWL"] == pytest.approx(cruiser.genes["BWL"] * s)
    assert g["T"] == pytest.approx(cruiser.genes["T"] * s)
    assert g["D"] == pytest.approx(cruiser.genes["D"] * s)
    assert grammar.check(grammar.vector(g)).ok

    # an explicit dimension OVERRIDES its scaled value — that is how a
    # 16 m brief gets its 4 m beam from a 15.2 x 4.0 parent
    g2 = parents.rescale(cruiser.genes, lwl=16.0, bwl=3.0)
    assert g2["BWL"] == pytest.approx(3.0)


def test_lackenby_clips_into_the_deliverable_band_instead_of_raising():
    cruiser = next(p for p in parents.PARENTS
                   if p.name == "solar-slender-cruiser")
    # 0.95 Cp with +3 %LWL LCB is not deliverable by these fullness genes;
    # the corrected sac solve would REFUSE it (audit D.4). The operator's
    # contract is to get close and let the ladder judge:
    g = parents.lackenby(cruiser.genes, cp=0.95, lcb=+3.0)
    x = grammar.vector(g)          # must not raise
    Hull(x)                        # must build
    # the walk moves BOTH genes toward band middle until the solver
    # accepts the pair (band membership is necessary, not sufficient — see
    # parents.refair on the high-Cp band edge), so the delivered pair is
    # CLOSE to the request, not component-wise below it
    assert g["Cp"] < 0.95
    assert abs(g["lcb"] - 3.0) < 1.0
    # a reachable target is delivered verbatim
    g2 = parents.lackenby(cruiser.genes, cp=0.66)
    assert g2["Cp"] == pytest.approx(0.66)


def test_seeds_land_on_the_brief_and_mostly_pass_the_family_critic():
    m = parse_mission("a 16 m x 4 m houseboat for canals")
    X = parents.seed_for_mission(m, 8, np.random.default_rng(7))
    assert len(X) >= 4, "seeding collapsed — fewer than half survived L0"
    j_l, j_b = grammar.NAMES.index("LWL"), grammar.NAMES.index("BWL")
    # principal dimensions are the MISSION's: not jittered, exactly the ask
    assert np.allclose(X[:, j_l], 16.0) and np.allclose(X[:, j_b], 4.0)
    ok = sum(_margin(x, "barge") <= 0.0 for x in X)
    assert ok >= len(X) // 2, (
        f"only {ok}/{len(X)} seeds pass the barge critic — the operator is "
        f"un-fairing the parent")
    # deterministic: same rng seed, same seeds
    Y = parents.seed_for_mission(m, 8, np.random.default_rng(7))
    assert np.array_equal(X, Y)


def test_retrieval_prefers_the_declared_family_then_the_regime():
    m = parse_mission("a 16 m x 4 m houseboat for canals")
    assert [p.family for p in parents.select_parents(m)] == ["barge"]
    # no family declared: the Froude number at the stated length decides
    fast = parse_mission("8 m sportboat at 22 knots")     # Fn ~ 1.28
    assert [p.family for p in parents.select_parents(fast)] == ["planing"]
    slow = parse_mission("12 m solar cruiser at 5 knots")  # Fn ~ 0.24
    assert ([p.family for p in parents.select_parents(slow)]
            == ["displacement"])
    # never empty — retrieval is a seeding heuristic, not a gate
    assert parents.select_parents(MissionSpec())


def test_the_genomes_have_one_home_and_the_prover_imports_them():
    """The cruiser/deepv genomes lived in scripts/hull_kb_reconstruct.py
    (which proved them against the KB records) and now live in
    navalai.parents. The recurring defect in this codebase is A NUMBER
    DECLARED TWICE; this is the fence against these two dicts growing a
    second copy that drifts."""
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "scripts"))
    try:
        import hull_kb_reconstruct as rk
    finally:
        sys.path.pop(0)
    by_name = {p.name: p for p in parents.PARENTS}
    assert rk.TARGETS["cruiser"]["genes"] == by_name[
        "solar-slender-cruiser"].genes
    assert rk.TARGETS["deepv"]["genes"] == by_name["warped-deepv"].genes
    src = (repo / "scripts" / "hull_kb_reconstruct.py").read_text()
    assert "from navalai.parents import" in src


def test_a_declared_family_seeds_the_optimizer_and_an_undeclared_one_cannot():
    """The stream-safety clause of the P5 wiring, asserted from both sides:
    a family mission's initial population contains parent-derived members
    (their LWL is EXACTLY the hint — raw draws essentially never are), and
    a family-less mission never even calls the seeder, so every recorded
    front reproduces bit-identically."""
    from navalai.optimize import HullProblem, _DrawBoxSampling

    m = parse_mission("a 16 m x 4 m houseboat for canals")
    prob = HullProblem(m)
    X = _DrawBoxSampling()._do(prob, 8,
                               random_state=np.random.default_rng(5))
    j = grammar.NAMES.index("LWL")
    assert (np.abs(X[:, j] - 16.0) < 1e-9).any(), (
        "no parent-derived member in a declared-family population")

    calls = []
    import navalai.parents as parents_mod
    orig = parents_mod.seed_for_mission
    parents_mod.seed_for_mission = (
        lambda *a, **k: calls.append(1) or orig(*a, **k))
    try:
        plain = HullProblem(MissionSpec(displacement_target_kg=6000,
                                        cruise_speed_kn=5))
        _DrawBoxSampling()._do(plain, 8,
                               random_state=np.random.default_rng(5))
    finally:
        parents_mod.seed_for_mission = orig
    assert calls == [], (
        "the seeder ran for a family-less mission — the RNG stream every "
        "recorded front depends on has been re-dealt")
