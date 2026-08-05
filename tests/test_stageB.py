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
    p.update({"p_bow": 1.5, "forefoot": 0.1, "rocker": 0.2, "sheer_rise": 0.1,
              "beta_bow": 12.0, "beta_mid": 6.0})
    xv = grammar.vector(p)
    d = HullDesign.from_vector(xv, Typology.PRAM)
    rep = type_check(d)
    assert rep.ok, rep.violations
    assert infer_typology(xv) in (Typology.SHARP_CHINE, Typology.PRAM)


def test_type_check_runs_before_geometry():
    """A type-check failure must not require geometry construction: feed a
    vector that violates flat bounds; type_check reports without Hull()."""
    x = mid_params()
    x[0] = 50.0
    rep = type_check(HullDesign.from_vector(x, Typology.SHARP_CHINE))
    assert not rep.ok and any("bound[LWL]" in v for v in rep.violations)


# ---------------- bend radius ----------------

def test_reference_hull_is_buildable():
    # Imported, not retyped: `80.0 * 0.015` here was a third copy of the
    # bend limit, and it would have gone on passing after the sheet became
    # a DERIVED quantity — silently checking a boat we no longer build.
    from navalai.limits import min_bend_radius_m

    h = Hull(mid_params())
    assert h.min_bend_radius() > min_bend_radius_m()


def test_extreme_rocker_flags_bend_limit():
    p = grammar.named(mid_params())
    p.update({"rocker": 0.6, "forefoot": 1.0, "LWL": 4.2, "T": 1.2,
              "D": 1.7, "BWL": 1.9})
    x = grammar.vector(p)
    h = Hull(x)
    # a 4 m hull with 0.72 m of keel sweep bends far tighter than a 17 m one
    assert h.min_bend_radius() < Hull(mid_params()).min_bend_radius()
    ev = evaluate(x, MissionSpec(displacement_target_kg=800))
    if ev.hydro is not None and h.min_bend_radius() < 1.2:
        assert any("bend radius" in v for v in ev.violations)


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
