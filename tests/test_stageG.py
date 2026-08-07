"""Gate G — similitude, extrapolation, fidelity/cost, planner, evidence graph.

Every bar here is a MEASURED number with the incident that motivated it named
in the test, per the project's convention. The headline one is
`test_geometric_scale_buys_no_cpu`: it is the executable form of the finding
that killed the original "search over geometric scale to make CFD cheaper"
design, and it is a regression guard — if someone later makes the domain
absolute rather than Lwl-relative, that test goes red and the reasoning behind
the whole subsystem has to be revisited.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from navalai import evidence, extrapolate, fidelity, planner, similitude
from navalai.cfd.case import background_counts, write_resistance_case_from_stl
from navalai.evidence import EvidenceGraph, Kind
from navalai.fidelity import Budget, FidelitySpec
from navalai.planner import Belief
from navalai.similitude import Condition, Similarity

# KCS, the project's only calibrated anchor. Model 1:31.5995, Fn 0.26.
KCS_LAM = 31.5995
KCS_MODEL_L = 7.2786
KCS_SHIP_L = 230.0
KCS_MODEL_U = 2.196
KCS_EFD_CT = 3.711e-3          # KRISO, Tokyo-2015 Case 2.1
KCS_SCATTER = (3.620e-3, 3.733e-3)

_STL = ("solid s\nfacet normal 0 0 1\nouter loop\n"
        "vertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\n"
        "endloop\nendfacet\nendsolid s\n")


def _model() -> Condition:
    return Condition(KCS_MODEL_L, KCS_MODEL_U, *similitude.FRESH_WATER_15C,
                     label="KCS model")


def _ship() -> Condition:
    return Condition(KCS_SHIP_L, 0.26 * math.sqrt(9.80665 * KCS_SHIP_L),
                     *similitude.SEA_WATER_15C, label="KCS ship")


# =============================================================================
# The finding that shaped the subsystem
# =============================================================================

def test_geometric_scale_buys_no_cpu(tmp_path):
    """MEASURED: identical mesh at 2.3 m, 7.28 m and 230 m, at fixed Fn.

    This is why `scale` is NOT an optimisation variable for cost. A 100:1 span
    of hull size and a 1000:1 span of Reynolds number produce the same cell
    count to the cell, because every domain extent is a multiple of Lwl and
    lambda/L = 2 pi Fn^2. Shrinking the geometry spends the same CPU and throws
    away Reynolds number.
    """
    stl = tmp_path / "h.stl"
    stl.write_text(_STL)
    counts, res = [], []
    for lwl in (2.3, KCS_MODEL_L, KCS_SHIP_L):
        u = 0.26 * math.sqrt(9.81 * lwl)
        out = tmp_path / f"c{lwl}"
        # n_layers PINNED AT 2. MEASURED 2026-08-07: at _NX_BASE 57 the hull
        # cell on the 2.3 m member is 11.3 mm while the DERIVED stack is
        # 14.7 mm, so the generator refuses ("layer stack does not FIT").
        # 3 layers still overflows it (14.7 mm); 2 gives 8.9 mm and fits. The
        # first layer is 4.03 mm because it scales as 1/u_tau, so this bites at
        # LOW speed -- the 2.3 m hull at Fn 0.26 runs at 1.24 m/s. That refusal is correct -- a partial stack folds
        # cells -- but it is a property of the layer derivation, not of the
        # cell-count invariance this test is about, so the wall model is held
        # fixed across the hull-size span exactly as a GCI triplet holds it.
        info = write_resistance_case_from_stl(stl, lwl, u, out, end_time=10.0,
                                              scale=1.0, np_procs=10,
                                              symmetric=True, n_layers=2)
        counts.append(info["bg_cells"])
        res.append(u * lwl / 1.14e-6)
    assert len(set(counts)) == 1, f"cell count moved with hull size: {counts}"
     # RE-BASED 2026-08-07: _NX_BASE moved 54 -> 57 when the four branches
    # were consolidated. 57 is the MEASURED fix -- it is divisible by 3 at
    # every triplet member, so ny = nx/3 is exact and the symmetric family's
    # refinement-ratio spread falls 0.85% -> 0.03%. Its cost is measured too:
    # (57/54)^3 = +19% cells. These constants were taken at base 54.
    assert counts[0] == 16245, "the measured scale-1 symmetric background (base 57)"
    assert res[-1] / res[0] > 900, "Reynolds must span ~1000x for the point"


def test_background_counts_takes_no_length():
    """The cost knob is mesh density; length is not an argument at all."""
    import inspect
    assert "lwl" not in inspect.signature(background_counts).parameters
     # RE-BASED 2026-08-07: _NX_BASE moved 54 -> 57 when the four branches
    # were consolidated. 57 is the MEASURED fix -- it is divisible by 3 at
    # every triplet member, so ny = nx/3 is exact and the symmetric family's
    # refinement-ratio spread falls 0.85% -> 0.03%. Its cost is measured too:
    # (57/54)^3 = +19% cells. These constants were taken at base 54.
    assert background_counts(1.0, True) == (57, 19, 7, 2, 2, 4)


def test_triplet_cost_ratio_is_not_the_cell_ratio():
    """CLAUDE.md budgets the GCI triplet at 3x/8x. Those are CELL ratios.

    The timestep is Courant-limited, so a sqrt(2) finer grid also takes
    sqrt(2) more steps. Cost goes as cells x steps, and the triplet is ~21x the
    coarse grid rather than ~12x — a 75% under-budget if the cell ratio is used
    as a time estimate.
    """
    cond = _model()
    one = fidelity.estimate(cond, FidelitySpec(mesh_density=1.0))
    two = fidelity.estimate(cond, FidelitySpec(mesh_density=2.0))
    cell_ratio = two.cells / one.cells
    cost_ratio = two.wall_s / one.wall_s
    assert cell_ratio == pytest.approx(8.0, rel=0.02), f"{cell_ratio:.2f}"
    assert cost_ratio == pytest.approx(16.0, rel=0.05), (
        f"cost ratio {cost_ratio:.2f} must be the cell ratio {cell_ratio:.2f} "
        f"TIMES the step ratio — 16x, not 8x")


def test_z_bands_freeze_between_coarse_and_medium_MEASURED_DEFECT():
    """RECORDED FINDING, not a design choice: the sqrt(2) step does not refine z.

    Found by this suite. `background_counts` apportions nz across four bands by
    largest remainder, and between mesh_density 0.7071 and 1.0 the hull band
    lands on 2 cells BOTH times:

        density 0.7071 -> (nx 38, ny 13, nz 4/2/1/3)
        density 1.0    -> (nx 57, ny 19, nz 7/2/2/4)

    Two consequences, both real:
      1. The interface cell height is IDENTICAL on the coarse and medium grids,
         so dt is identical and the free surface is not systematically refined
         between them. A GCI built on that pair bounds x-y discretisation only.
      2. At 0.7071 the hull band (2) and wave band (1) are NOT equal, though
         CLAUDE.md records that they must be — "the two ungraded core z-bands
         are EQUAL (0.09 Lwl each)" — because unequal bands reintroduce the
         anisotropy the isotropic-background fix removed.

    This test PINS the current behaviour so the finding is not lost. It should
    be deleted, and the triplet cost test tightened, when the apportionment is
    fixed to keep the two core bands equal and refine z with the family.
    """
    coarse = background_counts(1 / math.sqrt(2), True)
    medium = background_counts(1.0, True)
    assert coarse[3] == medium[3] == 2, "z hull band frozen across the step"
    assert coarse[3] != coarse[4], "and the two core bands are unequal at 0.7071"
    cond = _model()
    dz_c = fidelity.free_surface_dz(cond, FidelitySpec(1 / math.sqrt(2)))
    dz_m = fidelity.free_surface_dz(cond, FidelitySpec(1.0))
    assert dz_c == pytest.approx(dz_m), "interface dz does not refine — the defect"


# =============================================================================
# Similitude
# =============================================================================

def test_froude_scaling_is_self_consistent():
    ship, model = _ship(), _model()
    lam = ship.lwl / model.lwl
    assert lam == pytest.approx(KCS_LAM, rel=1e-3)
    assert model.fn == pytest.approx(ship.fn, rel=1e-3)
    # a force scaled down and back up is the same force
    f = 1.0e6
    down = similitude.scale_value(f, "force", lam, "model")
    assert similitude.scale_value(down, "force", lam, "ship") == pytest.approx(f)
    # accelerations are UNCHANGED under Froude scaling — the classic trap
    assert similitude.scale_value(9.81, "acceleration", lam, "model") == 9.81


def test_reynolds_falls_as_lambda_to_the_three_halves():
    """Match Froude and Reynolds falls by lambda^1.5. In the SAME fluid."""
    ship = Condition(KCS_SHIP_L, 0.26 * math.sqrt(9.80665 * KCS_SHIP_L),
                     *similitude.FRESH_WATER_15C)
    model = ship.at_scale(KCS_LAM)
    eff = similitude.scale_effects(ship, model)
    assert eff.get("froude").preserved
    assert not eff.get("reynolds").preserved
    assert eff.get("reynolds").ratio == pytest.approx(KCS_LAM ** -1.5, rel=1e-6)
    assert eff.get("weber").ratio == pytest.approx(KCS_LAM ** -2.0, rel=1e-6)


def test_small_models_are_refused_not_silently_scaled():
    """A 1:200 model of a 10 m dayboat is below the Reynolds floor.

    Point 3 of the brief, enforced: if a scaling agent may generate small
    models, it needs a Reynolds floor or an explicit turbulence-stimulation
    assumption, or the friction is wrong in a way that reads as a solver bug.
    """
    ship = Condition(10.0, 3.0)
    tiny = ship.at_scale(200.0)
    eff = similitude.scale_effects(ship, tiny)
    assert not eff.admissible
    assert any("floor" in w or "laminar" in w for w in eff.warnings)
    assert any("Weber" in w or "We " in w for w in eff.warnings)
    # ...while the KCS model scale, which real tanks use, is admissible
    ok = similitude.scale_effects(_ship(), _model())
    assert ok.admissible, ok.report()


def test_physical_model_is_immutable_and_full_scale_is_the_default():
    pm = similitude.physical_model(_ship())
    assert pm.full_scale and pm.lam == 1.0
    with pytest.raises(Exception):
        pm.ship = _model()                      # frozen
    scaled = pm.with_(simulated=_model())
    assert scaled.lam == pytest.approx(KCS_LAM, rel=1e-3)
    assert pm.full_scale, "with_() must not mutate the original"
    assert scaled.effects is not None and "reynolds" in scaled.effects.violated


# =============================================================================
# ITTC-78 extrapolation
# =============================================================================

def test_extrapolation_is_the_identity_at_full_scale():
    """At lambda = 1 the Re-invariance assumption is never invoked."""
    ship = _ship()
    p = extrapolate.ittc78(ship, ship, 3.0e-3, 1000.0, 1000.0, form_k=0.1,
                           k_s=0.0)
    assert p.ct_ship == pytest.approx(3.0e-3 + p.dcf_roughness, rel=1e-9)
    assert p.cr == pytest.approx(3.0e-3 - 1.1 * p.cf_model, rel=1e-9)


def test_kcs_extrapolates_to_a_plausible_ship_coefficient():
    """The worked KCS case: model C_T 3.711e-3 -> ship, with (1+k) = 1.1."""
    model, ship = _model(), _ship()
    s_m = 9.4379                      # KCS model wetted area [m2], geometry
    p = extrapolate.ittc78(model, ship, KCS_EFD_CT, s_m, s_m * KCS_LAM**2,
                           form_k=0.1, sigma_ct_model=0.05 * KCS_EFD_CT)
    assert p.ct_ship < p.ct_model, "ship Re is higher, so friction is lower"
    assert 2.0e-3 < p.ct_ship < 2.8e-3, f"C_Ts = {p.ct_ship:.4e}"
    assert p.cr == pytest.approx(KCS_EFD_CT - 1.1 * p.cf_model, rel=1e-9)
    assert p.sigma_rel > 0.0, "an extrapolation without a band is not honest"
    assert any("Reynolds" in a for a in p.assumptions)


def test_residuary_is_scale_invariant_by_construction():
    """C_R is the same whichever model scale it came from — that IS the premise."""
    ship = _ship()
    crs = []
    for lam in (20.0, 31.5995, 50.0):
        m = ship.at_scale(lam, rho=similitude.FRESH_WATER_15C[0],
                          nu=similitude.FRESH_WATER_15C[1])
        # a model C_T consistent with one fixed C_R at each scale
        cf = extrapolate.ittc57_cf(m.speed, m.lwl, m.nu)
        ct = 1.1 * cf + 0.6e-3
        p = extrapolate.ittc78(m, ship, ct, 10.0, 10.0 * lam**2, form_k=0.1)
        crs.append(p.cr)
    assert max(crs) - min(crs) < 1e-9, f"C_R drifted with scale: {crs}"


def test_form_factor_1_27_is_flagged_on_kcs():
    """Point 1 of the brief, checked rather than accepted.

    (1+k) IS a scale-independent shape property and one CFD point calibrating
    it is exactly the right idea. But 1.27 applied to KCS at Fn 0.26 leaves
    C_R = 0.114e-3 — about 5x smaller than this hull's wave-making at that
    speed, and well above the ~1.1 Tokyo-2015 uses. The likeliest reading is
    that it absorbed a friction shortfall (our y+ median was 2475). The check
    does not refuse it; it refuses to let it pass unremarked.
    """
    m = _model()
    cr_127, verdict_127 = extrapolate.residuary_check(m, KCS_EFD_CT, 0.27)
    cr_110, verdict_110 = extrapolate.residuary_check(m, KCS_EFD_CT, 0.10)
    assert cr_127 < 0.15e-3 and "implausibly small" in verdict_127
    assert cr_110 > 0.4e-3 and "plausible" in verdict_110
    # and the calibration inverse is consistent with itself
    k = extrapolate.calibrate_form_factor(m, KCS_EFD_CT)
    assert extrapolate.residuary_check(m, KCS_EFD_CT, k)[0] == pytest.approx(0.0,
                                                                            abs=1e-12)


# =============================================================================
# Fidelity and cost
# =============================================================================

def test_cost_model_reproduces_the_measured_run():
    """runs/kcs_sym: 241,946 cells, 3145 steps to t=13.739 s, 2157 s wall.

    The interface cell height is the non-circular part: it is derived here from
    the block structure and must land on the 0.01024 m that case.info records.
    """
    cond = _model()
    spec = FidelitySpec(mesh_density=1.0, symmetric=True)
    assert fidelity.free_surface_dz(cond, spec) == pytest.approx(0.01024, rel=1e-3)
     # RE-BASED 2026-08-07: _NX_BASE moved 54 -> 57 when the four branches
    # were consolidated. 57 is the MEASURED fix -- it is divisible by 3 at
    # every triplet member, so ny = nx/3 is exact and the symmetric family's
    # refinement-ratio spread falls 0.85% -> 0.03%. Its cost is measured too:
    # (57/54)^3 = +19% cells. These constants were taken at base 54.
    # runs/kcs_sym measured 241,946 cells AT BASE 54; the same case on the
    # current family is 288,836. The run itself no longer exists.
    assert spec.cells() == pytest.approx(288836, rel=0.01)
    cost = fidelity.estimate(cond, spec)
    assert cost.dt_s == pytest.approx(13.739 / 3145, rel=0.05), (
        "predicted timestep must match the measured mean")
    # NORMALISE BY CELLS, do not re-fit the anchor. The 2157 s was measured on
    # the base-54 mesh (241,946 cells); the current family is 288,836, so the
    # raw seconds are not comparable and scaling the EXPECTATION to match the
    # model would be fitting the bar to the answer. What the measurement
    # actually pins is a per-cell-step throughput, and that is mesh-independent
    # -- so it survives a base change, which is the whole point of anchoring.
    measured_rate = 2157.0 / (241946 * 3145)
    predicted_rate = cost.wall_s / (spec.cells() * cost.timesteps)
    assert predicted_rate == pytest.approx(measured_rate, rel=0.15)
    assert cost.cells_per_wavelength == pytest.approx(21.5, rel=0.05)


def test_cost_does_not_depend_on_hull_size():
    """The same statement as the mesh test, now in wall-clock seconds."""
    a = fidelity.estimate(Condition(7.2786, 2.196), FidelitySpec())
    b = fidelity.estimate(Condition(230.0, 0.26 * math.sqrt(9.80665 * 230.0)),
                          FidelitySpec())
    assert a.wall_s == pytest.approx(b.wall_s, rel=1e-9)
    assert a.timesteps == b.timesteps


def test_admit_refuses_before_meshing_and_says_why():
    cond = _model()
    tight = Budget(max_wall_s=60.0, max_ram_gb=64.0, np_procs=10)
    ok, refusals, cost = fidelity.admit(cond, FidelitySpec(2.0), tight)
    assert not ok and any("exceeds" in r.reason for r in refusals)
    # and a mesh so coarse the wave field is unresolved is refused on PHYSICS,
    # not on cost — the bar that stops the search running away to free
    ok2, ref2, _ = fidelity.admit(cond, FidelitySpec(0.2),
                                  Budget(max_wall_s=1e12, max_ram_gb=1e6))
    assert not ok2 and any("wavelength" in r.reason for r in ref2)


def test_cheapest_admissible_finds_the_coarsest_valid_grid():
    spec, refusals = fidelity.cheapest_admissible(
        _model(), Budget(max_wall_s=48 * 3600, max_ram_gb=64.0, np_procs=10))
    assert spec is not None, refusals
    ok, _, cost = fidelity.admit(_model(), spec,
                                 Budget(max_wall_s=48 * 3600, max_ram_gb=64.0))
    assert ok and cost.cells_per_wavelength >= fidelity.MIN_CELLS_PER_WAVELENGTH
    # one step coarser must fail, or it was not the cheapest
    ok_c, _, _ = fidelity.admit(_model(), spec.coarser(),
                                Budget(max_wall_s=48 * 3600, max_ram_gb=64.0))
    assert not ok_c


def test_seiche_is_froude_similar_and_survives_scaling():
    """Point 2 of the brief: shrinking the model carries the resonance along.

    T_seiche/T_wave depends only on Froude number, so it is identical at every
    geometric scale — it cannot be scaled away, only designed away (longer
    domain or outlet damping).
    """
    ratios = []
    for lwl in (2.3, 7.2786, 230.0):
        c = Condition(lwl, 0.26 * math.sqrt(9.80665 * lwl))
        t_s, t_w, _ = fidelity.seiche_check(c, FidelitySpec())
        ratios.append(t_s / t_w)
    assert max(ratios) - min(ratios) < 1e-9, f"not Froude-similar: {ratios}"
    # measured on runs/kcs_sym: seiche 10.0 s against a 1.41 s wave period
    t_s, t_w, verdict = fidelity.seiche_check(_model(), FidelitySpec())
    assert t_s == pytest.approx(10.0, rel=0.05)
    assert t_w == pytest.approx(1.41, rel=0.05)
    assert "clear" in verdict, verdict
    # a short run is called out as unsettled rather than passed
    _, _, short = fidelity.seiche_check(_model(), FidelitySpec(flow_throughs=0.4))
    assert "damp" in short


# =============================================================================
# Planner
# =============================================================================

def test_stated_budget_and_the_wave_resolution_bar_are_unsatisfiable_together():
    """RECORDED CONFLICT between two of the project's own stated constraints.

    Stated budget: coarse ~15 min, medium <=2 h, fine ~4-5 h on 10 cores.
    Stated bar:    >= 20 cells per wavelength, or "the whole run is decoration".

    MEASURED, at KCS Fn 0.26 with the current 4.5 Lwl domain, they cannot both
    hold. The coarsest grid that resolves the wave field is density 1.0, and it
    costs 3.87 h — already past the 2 h MEDIUM budget, and 15x the 15 min
    allowed for a coarse grid. Every cheaper grid is refused on physics.

    This test does not pick a winner. It pins the conflict so it is decided
    deliberately rather than absorbed by whichever check happens to run first.
    Ways out, in order of honesty: run at a HIGHER Froude number (cells per
    wavelength goes as Fn^2, so Fn 0.31 resolves on the density-0.7071 grid),
    shorten the domain, or accept a coarser wave field and say so in the badge.
    """
    cond = _model()
    assert cond.fn == pytest.approx(0.26, abs=0.005)
    # nothing fits the coarse budget
    spec, refusals = fidelity.cheapest_admissible(cond, fidelity.STATED_COARSE)
    assert spec is None and refusals
    # nor the medium one
    spec_m, _ = fidelity.cheapest_admissible(cond, fidelity.STATED_MEDIUM)
    assert spec_m is None
    # the cheapest physically-valid grid, and what it actually costs
    need = fidelity.density_for_wave_resolution(cond.fn)
    assert need == pytest.approx(1.0, rel=0.05)
    cost = fidelity.estimate(cond, FidelitySpec(mesh_density=1.0))
     # RE-BASED 2026-08-07: _NX_BASE moved 54 -> 57 when the four branches
    # were consolidated. 57 is the MEASURED fix -- it is divisible by 3 at
    # every triplet member, so ny = nx/3 is exact and the symmetric family's
    # refinement-ratio spread falls 0.85% -> 0.03%. Its cost is measured too:
    # (57/54)^3 = +19% cells. These constants were taken at base 54.
    assert cost.wall_hours == pytest.approx(3.87, rel=0.05)


def test_cells_per_wavelength_goes_as_froude_squared():
    """Non-obvious: LOW Froude numbers are the expensive ones to resolve."""
    for d in (0.7071, 1.0, 1.414):
        for fn in (0.20, 0.26, 0.35):
            c = Condition(7.2786, fn * math.sqrt(9.80665 * 7.2786))
            got = fidelity.estimate(c, FidelitySpec(mesh_density=d))
            assert got.cells_per_wavelength == pytest.approx(
                fidelity.cells_per_wavelength(fn, d), rel=1e-6)
    # the closed form matches the real generated case
    assert fidelity.cells_per_wavelength(0.26, 1.0) == pytest.approx(21.5, rel=0.02)
    # halving Fn quarters the resolution
    assert (fidelity.cells_per_wavelength(0.13, 1.0)
            == pytest.approx(fidelity.cells_per_wavelength(0.26, 1.0) / 4, rel=1e-9))


def test_information_gain_has_the_right_shape():
    assert planner.information_gain(1.0, 1e9) == pytest.approx(0.0, abs=1e-15)
    assert planner.information_gain(1.0, 1.0) == pytest.approx(math.log(math.sqrt(2)))
    assert math.isinf(planner.information_gain(1.0, 0.0))
    assert planner.information_gain(0.0, 1.0) == 0.0
    # a vaguer experiment than the belief gains less than a sharper one
    assert planner.information_gain(0.1, 0.5) < planner.information_gain(0.1, 0.02)


def test_stability_question_never_selects_cfd():
    """'Do I actually need CFD?' answered by arithmetic, not by a rule list.

    No CFD tier informs GM, so CFD's information gain on it is exactly zero and
    it is never selected — at any budget.
    """
    p = planner.plan_for("initial stability",
                         {"gm": Belief("gm", 0.8, 0.4),
                          "displacement": Belief("displacement", 6000.0, 900.0)},
                         target_sigma_rel=0.10)
    assert p.steps, "something should have been chosen"
    assert all(exp.tier != "L3" for exp, *_ in p.steps), p.report()
    assert p.total_cost_s < 1.0, "hydrostatics answers this in milliseconds"


def test_tight_resistance_target_escalates_to_cfd():
    p = planner.plan_for("calm-water resistance",
                         {"resistance": Belief("resistance", 4000.0, 2000.0)},
                         target_sigma_rel=0.12,
                         budget=Budget(max_wall_s=72 * 3600, max_ram_gb=64.0,
                                       np_procs=10))
    tiers = [exp.tier for exp, *_ in p.steps]
    assert "L1" in tiers, "the cheap tier must run first — it is nearly free"
    assert "L3" in tiers, p.report()
    assert tiers.index("L1") < tiers.index("L3"), "cheapest-informative first"


def test_a_satisfied_question_runs_nothing():
    """The most valuable answer the planner can give is 'no experiment needed'."""
    p = planner.plan_for("calm-water resistance",
                         {"resistance": Belief("resistance", 4000.0, 100.0,
                                               tier="L3")},
                         target_sigma_rel=0.10)
    assert p.satisfied and not p.steps
    assert p.total_cost_s == 0.0


def test_unaffordable_cfd_is_recorded_as_a_refusal_not_dropped():
    p = planner.plan_for("calm-water resistance",
                         {"resistance": Belief("resistance", 4000.0, 2000.0)},
                         target_sigma_rel=0.01,
                         budget=Budget(max_wall_s=600.0, max_ram_gb=8.0,
                                       np_procs=10))
    assert not p.satisfied, "a 1% target is not reachable by this ladder"
    assert p.rejected, "the refused options must be visible with their reasons"
    assert any("exceeds" in why for _, why in p.rejected)


def test_zero_centred_quantity_is_not_declared_exactly_known():
    """Adversarial-review finding: relative sigma against a zero value = 0.

    A trim angle believed to be 0.0 deg would have had sigma_rel * 0 = 0 as its
    observation sigma, i.e. any experiment at all would return it as EXACTLY
    known and every target on it would be satisfied without running anything.
    `Belief.scale` gives a magnitude for relative uncertainty to bite on.
    """
    zero = Belief("trim", 0.0, 0.5, scale=2.0)
    assert zero.sigma_rel == pytest.approx(0.25)
    after = planner.update(zero, "L1", 0.30)
    assert after.sigma > 0.0, "an ordinary experiment cannot give exact knowledge"
    assert after.sigma < zero.sigma
    # and with no scale declared, a zero-valued belief is INFINITELY uncertain
    # rather than perfectly certain — it fails loudly instead of quietly
    assert Belief("trim", 0.0, 0.5).sigma_rel == math.inf


def test_one_experiment_pays_once_and_credits_every_quantity():
    """Adversarial-review finding: L1 answers resistance AND displacement.

    Scoring per (experiment, quantity) but retiring the experiment after
    crediting one quantity made the planner buy a second tier for information
    the first had already produced.
    """
    p = planner.plan("range", frozenset({"resistance", "displacement"}),
                     {"resistance": Belief("resistance", 4000.0, 2000.0),
                      "displacement": Belief("displacement", 6000.0, 1800.0)},
                     target_sigma_rel=0.20)
    l1_steps = [s for s in p.steps if s[0].tier == "L1"]
    assert len(l1_steps) == 2, "one L1 run must credit both quantities"
    charged = sum(cost for *_, cost in l1_steps)
    assert charged == pytest.approx(planner.TIER_COST_S["L1"]), (
        "and be charged exactly once")
    # displacement is settled by L1 (6% band clears the 20% target); resistance
    # is NOT (25% -> 22.4% posterior), so it legitimately escalates to L2. The
    # point of the test is that L1 was bought ONCE and credited to both.
    assert p.beliefs["displacement"].tier == "L1"
    assert p.beliefs["resistance"].tier == "L2"
    assert p.satisfied, p.report()


def test_parallel_correction_reproduces_the_measured_np_sweep():
    """MEASURED: same 0.4 s slice, np=5 -> 212.7 s, np=10 -> 127.2 s, 15 -> 153.1 s.

    Pinned because the correction is a RATIO of speedups (the calibration
    constant is itself a np=10 rate), and a reviewer read it as a double
    division. At np=10 the factor must be exactly 1.
    """
    cond = _model()
    spec = FidelitySpec()
    w = {n: fidelity.estimate(cond, spec,
                              Budget(np_procs=n, max_wall_s=1e12,
                                     max_ram_gb=1e6)).wall_s
         for n in (5, 10, 15)}
    assert w[5] / w[10] == pytest.approx(212.7 / 127.2, rel=0.02)
    assert w[15] / w[10] == pytest.approx(153.1 / 127.2, rel=0.02)
    assert w[15] > w[10], "oversubscribing all 15 cores is measurably slower"


def test_cost_is_monotone_in_density_so_ascending_search_is_correct():
    """`cheapest_admissible` scans density ascending and takes the first hit.

    That is only the CHEAPEST option if cost is non-decreasing in density.
    Cells and steps are both non-decreasing, so it is — pinned here because the
    claim is what makes the search correct rather than merely plausible.
    """
    cond = _model()
    walls = [fidelity.estimate(cond, FidelitySpec(mesh_density=d)).wall_s
             for d in (0.35, 0.5, 0.7071, 1.0, 1.414, 2.0, 2.83)]
    assert all(b >= a for a, b in zip(walls, walls[1:])), walls


def test_beliefs_tighten_but_never_loosen():
    b = Belief("resistance", 4000.0, 1000.0)
    after = planner.update(b, "L3", 0.15)
    assert after.sigma < b.sigma and after.tier == "L3"
    # a vague observation barely moves a sharp belief
    sharp = Belief("resistance", 4000.0, 40.0)
    assert planner.update(sharp, "L1", 0.25).sigma == pytest.approx(sharp.sigma,
                                                                   rel=0.05)


# =============================================================================
# Design Evidence Graph
# =============================================================================

def _graph() -> EvidenceGraph:
    g = EvidenceGraph()
    g.add("req", Kind.REQUIREMENT, "maintain 25 kn")
    g.add("dec", Kind.DECISION, "raise L/B to 9.5")
    g.add("exp", Kind.EXPERIMENT, "L3 RANS @ density 1.0")
    g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", value=4100.0, sigma=620.0,
          tier="L3", confidence=0.85)
    g.add("asm", Kind.ASSUMPTION, "appendage drag is 4% of bare hull",
          confidence=0.60)
    g.support("req", "dec")
    g.support("exp", "ev")
    g.support("ev", "dec")
    g.support("asm", "dec")
    return g


def test_confidence_is_the_weakest_link_not_the_average():
    g = _graph()
    # 0.85 evidence and 0.60 assumption -> 0.60, not 0.725
    assert g.confidence("dec") == pytest.approx(0.60)
    g.nodes["asm"].confidence = 0.95
    assert g.confidence("dec") == pytest.approx(0.85)


def test_diamond_confidence_is_the_true_minimum():
    """A shared ancestor must cap every path through it, counted once.

    The reviewer's concern was that a visited-set guard could credit a
    re-reached ancestor with 1.0. Confidence is now a minimum over the ancestor
    SET, so the question cannot arise — but the diamond is pinned anyway.
    """
    g = EvidenceGraph()
    g.add("req", Kind.REQUIREMENT, "r", confidence=1.0)
    g.add("weak", Kind.ASSUMPTION, "shared weak assumption", confidence=0.30)
    g.add("a", Kind.DECISION, "a", confidence=0.9)
    g.add("b", Kind.DECISION, "b", confidence=0.9)
    g.add("top", Kind.DECISION, "top", confidence=0.95)
    for s, t in (("req", "a"), ("req", "b"), ("weak", "a"), ("weak", "b"),
                 ("a", "top"), ("b", "top")):
        g.support(s, t)
    assert g.confidence("top") == pytest.approx(0.30)
    assert g.confidence("a") == pytest.approx(0.30)


def test_unsupported_decisions_are_the_agenda():
    g = _graph()
    assert g.unsupported() == []
    g.add("dec2", Kind.DECISION, "set transom immersion to 0.4 m")
    g.support("req", "dec2")
    names = [n.id for n in g.unsupported()]
    assert names == ["dec2"], "a decision resting on nothing must surface"


def test_circular_justification_is_rejected_at_insertion():
    g = _graph()
    g.add("d3", Kind.DECISION, "b")
    g.support("dec", "d3")
    with pytest.raises(ValueError, match="cycle"):
        g.support("d3", "dec")


def test_illegal_support_kinds_are_rejected():
    g = _graph()
    g.add("d4", Kind.DECISION, "x")
    with pytest.raises(ValueError, match="may not support"):
        g.support("d4", "req")           # a decision cannot justify a requirement


def test_graph_round_trips_through_json(tmp_path):
    g = _graph()
    p = tmp_path / "deg.json"
    g.save(p)
    back = EvidenceGraph.load(p)
    assert back.confidence("dec") == pytest.approx(g.confidence("dec"))
    assert "R_T = 4.1 kN" in back.explain("dec")
    assert set(back.nodes) == set(g.nodes)
