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

import json
import math
import tempfile
from pathlib import Path

import pytest

from navalai import evidence, extrapolate, fidelity, planner, similitude
from navalai.cfd.case import background_counts, write_resistance_case_from_stl
from navalai.evidence import EvidenceGraph, EvidenceTier, Kind, Origin
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

def _tetra_stl() -> str:
    """A CLOSED tetrahedron, not a single triangle.

    This fixture was one triangle until 2026-08-12 — an open shell fed to
    `write_resistance_case_from_stl`, whose docstring has always said "The STL
    must be watertight". It worked because nothing enforced that, and it stopped
    working the moment the import boundary got its guard (Gate 2H). The test
    itself is unaffected: it measures BACKGROUND cell counts, which derive from
    `lwl` and the domain multiples, never from the surface. So the fix is to
    make the fixture honest rather than to exempt the test — a test that only
    passes because a guard is missing is a test that was measuring the gap.
    """
    v = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    out = ["solid s"]
    for a, b, c in faces:
        out += ["facet normal 0 0 0", "outer loop"]
        out += [f"vertex {v[i][0]} {v[i][1]} {v[i][2]}" for i in (a, b, c)]
        out += ["endloop", "endfacet"]
    out.append("endsolid s")
    return "\n".join(out) + "\n"


_STL = _tetra_stl()


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


def test_tank_resonance_is_froude_similar_and_survives_scaling():
    """Point 2 of the brief: shrinking the model carries the resonance along.

    REWRITTEN 2026-08-14 (audit G8-P0): the still-water seiche this test
    pinned at 10.0 s was REFUTED by scripts/tank_resonance.py — the tank
    oscillates on the DOPPLER-SHIFTED tank mode (measured 5.53 s where the
    Doppler model predicts 5.64 with the case's exact depth and this
    module's derived depth gives 5.80; the seiche formula said 7.75 s at
    both test speeds and matched neither). The physical claim SURVIVES the
    model swap and that is the point of this test: with h = 0.6 L binding,
    k_n h is dimensionless, so T_n/T_wave depends only on Froude number —
    the resonance cannot be scaled away, only designed away (longer domain
    or outlet damping).
    """
    ratios = []
    for lwl in (2.3, 7.2786, 230.0):
        c = Condition(lwl, 0.26 * math.sqrt(9.80665 * lwl))
        t_s, t_w, _ = fidelity.tank_resonance_check(c, FidelitySpec())
        ratios.append(t_s / t_w)
    assert max(ratios) - min(ratios) < 1e-9, f"not Froude-similar: {ratios}"
    # the MEASURED mechanism: prediction within 10% of the 5.53 s the tank
    # actually rang at (val_coarse5), and nowhere near the refuted 7.75/10.0
    t_s, t_w, verdict = fidelity.tank_resonance_check(_model(), FidelitySpec())
    assert t_s == pytest.approx(5.53, rel=0.10)
    assert t_w == pytest.approx(1.41, rel=0.05)
    assert "clear" in verdict, verdict
    # a short run is called out as unsettled rather than passed
    _, _, short = fidelity.tank_resonance_check(_model(),
                                                FidelitySpec(flow_throughs=0.4))
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
    # the cheapest physically-valid grid, and what it actually costs.
    # RE-BASED 2026-08-14: this pinned ~0.98, a number computed with the
    # DRIFTED fourth copy of _NX_BASE (54); with the inverse now importing
    # the live 57 the floor is 57/54 lower, 0.9294 — verified round-trip:
    # cells_per_wavelength(0.26, 0.9294) = 20.01 against the 20 bar.
    need = fidelity.density_for_wave_resolution(cond.fn)
    assert need == pytest.approx(0.9294, rel=0.02)
    assert fidelity.cells_per_wavelength(cond.fn, need) >=         fidelity.MIN_CELLS_PER_WAVELENGTH - 0.05
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
    g.add("req", Kind.REQUIREMENT, "maintain 25 kn", tier=EvidenceTier.NA)
    g.add("dec", Kind.DECISION, "raise L/B to 9.5", tier=EvidenceTier.NA)
    g.add("exp", Kind.EXPERIMENT, "L3 RANS @ density 1.0", tier=EvidenceTier.L3)
    g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", value=4100.0, sigma=620.0,
          tier="L3", confidence=0.85)
    g.add("asm", Kind.ASSUMPTION, "appendage drag is 4% of bare hull",
          tier=EvidenceTier.NA, confidence=0.60)
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
    g.add("req", Kind.REQUIREMENT, "r", tier=EvidenceTier.NA, confidence=1.0)
    g.add("weak", Kind.ASSUMPTION, "shared weak assumption",
          tier=EvidenceTier.NA, confidence=0.30)
    g.add("a", Kind.DECISION, "a", tier=EvidenceTier.NA, confidence=0.9)
    g.add("b", Kind.DECISION, "b", tier=EvidenceTier.NA, confidence=0.9)
    g.add("top", Kind.DECISION, "top", tier=EvidenceTier.NA, confidence=0.95)
    for s, t in (("req", "a"), ("req", "b"), ("weak", "a"), ("weak", "b"),
                 ("a", "top"), ("b", "top")):
        g.support(s, t)
    assert g.confidence("top") == pytest.approx(0.30)
    assert g.confidence("a") == pytest.approx(0.30)


def test_unsupported_decisions_are_the_agenda():
    g = _graph()
    assert g.unsupported() == []
    g.add("dec2", Kind.DECISION, "set transom immersion to 0.4 m",
          tier=EvidenceTier.NA)
    g.support("req", "dec2")
    names = [n.id for n in g.unsupported()]
    assert names == ["dec2"], "a decision resting on nothing must surface"


def test_circular_justification_is_rejected_at_insertion():
    g = _graph()
    g.add("d3", Kind.DECISION, "b", tier=EvidenceTier.NA)
    g.support("dec", "d3")
    with pytest.raises(ValueError, match="cycle"):
        g.support("d3", "dec")


def test_illegal_support_kinds_are_rejected():
    g = _graph()
    g.add("d4", Kind.DECISION, "x", tier=EvidenceTier.NA)
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


# =============================================================================
# The evidence tier vocabulary is CLOSED
#
# MEASURED 2026-08-11 (adversarial re-audit, 91c0086; docs/BUILD-PLAN.md
# §17.1.1): `evidence.Node.tier` was a free-form `str` defaulting to `""`. The
# ladder's honesty trick is that `evaluate.tier_rank` ranks a badge it does not
# recognise at -1, BELOW L0, so a claim can never be promoted by comparison — and
# a node that spells its tier anything else never reaches that check at all. A
# real-boat observation was therefore admissible under any spelling, including a
# typo, and the default spelled nothing.
#
# Every test below feeds a guard the VERBATIM input it must reject
# (docs/LESSONS.md defect class 3: a guard never made to fire is not a guard).
# =============================================================================

def test_evidence_tiers_are_the_project_vocabulary_not_a_second_one():
    """Defect class 2 (a number declared twice), applied to a vocabulary.

    `EvidenceTier` cannot IMPORT the ladder: `evaluate` will import `evidence`
    when the graph is populated from `evaluate()` (BUILD-PLAN §4.3), and the
    ladder tuple must stay four members long because `tier_rank` derives
    "unknown, therefore -1" from NOT being in it. So the agreement is policed
    here instead, the way `tests/test_limits_single_source.py` polices limits.
    """
    from navalai import flywheel, weights
    from navalai.evaluate import TIER_ORDER, tier_rank

    ladder = (EvidenceTier.L0, EvidenceTier.L1, EvidenceTier.L2, EvidenceTier.L3)
    assert [t.value for t in ladder] == list(TIER_ORDER), (
        "the ladder members must be TIER_ORDER, in TIER_ORDER's order")
    assert EvidenceTier.S1.value == flywheel.SURROGATE_TIER
    for t in (EvidenceTier.L1, EvidenceTier.E, EvidenceTier.F, EvidenceTier.R):
        assert t.value in weights._TIERS, f"{t.value} must match weights._TIERS"

    # The whole mechanism: anything off the ladder ranks -1, below L0, so it can
    # never satisfy a ladder requirement by comparison. That includes M1 — a
    # real measurement is not weaker than L0, it is INCOMMENSURABLE with a
    # simulated ladder, and -1 is how this codebase already says that (S1).
    for t in EvidenceTier:
        expected = TIER_ORDER.index(t.value) if t.value in TIER_ORDER else -1
        assert tier_rank(t.value) == expected, t.value
    assert tier_rank(EvidenceTier.M1.value) == -1 < tier_rank("L0")
    assert tier_rank(EvidenceTier.L3_INVALID.value) == -1

    # Exactly ONE value means "measured on a real boat" (BUILD-PLAN §17.1.1's
    # bar). Two would be two vocabularies again.
    observed = [t for t in EvidenceTier
                if evidence.ORIGIN[t] is Origin.OBSERVED]
    assert observed == [EvidenceTier.M1]
    # and every member is classified: an unclassified tier must be a KeyError,
    # never a default (LESSONS defect class 1).
    assert set(evidence.ORIGIN) == set(EvidenceTier)


@pytest.mark.parametrize("spelling", ["CFD", "l3", "sea trial", "L4", "L1H",
                                      "T1", "measured", "0"])
def test_an_unknown_tier_is_refused_at_construction(spelling):
    """The verbatim spellings the free-form `str` used to accept.

    `L1H` is real: `holtrop.py` emits it, and `tier_rank("L1H")` is already -1.
    It is refused rather than blessed — a tier that ranks below L0 everywhere
    else must not become a first-class member here.
    """
    g = EvidenceGraph()
    with pytest.raises(ValueError, match="not an evidence tier"):
        g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", value=4100.0, sigma=620.0,
              tier=spelling)


def test_the_empty_tier_that_was_the_default_is_refused():
    g = EvidenceGraph()
    with pytest.raises(ValueError, match="not an evidence tier"):
        g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", tier="")


def test_a_missing_tier_fails_construction_rather_than_defaulting():
    """Absence of a classification is an error, not a permissive value."""
    g = EvidenceGraph()
    with pytest.raises(TypeError, match="tier"):
        g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", value=4100.0, sigma=620.0)
    with pytest.raises(TypeError, match="tier"):
        evidence.Node(id="ev", kind=Kind.EVIDENCE, text="R_T = 4.1 kN")


def test_every_declared_tier_is_accepted_by_some_kind():
    """The refusals above prove nothing if the vocabulary refuses everything."""
    for t in EvidenceTier:
        kinds = [k for k, allowed in evidence.ALLOWED_TIERS.items() if t in allowed]
        assert kinds, f"{t.value} is declared but no kind may carry it"
        g = EvidenceGraph()
        assert g.add("n", kinds[0], "x", tier=t).tier is t


def test_a_node_kind_may_not_wear_a_tier_that_is_not_its_own():
    """Semantic laundering at the node, the same shape as ALLOWED_SUPPORT.

    A decision is a choice; giving it `L3` lends it the authority of a solve
    nobody ran. Evidence is a claim about a quantity; `NA` would be evidence
    that declines to say what it is worth, which is the `""` default again.
    """
    g = EvidenceGraph()
    with pytest.raises(ValueError, match="may not carry tier"):
        g.add("dec", Kind.DECISION, "raise L/B to 9.5", tier=EvidenceTier.L3)
    with pytest.raises(ValueError, match="may not carry tier"):
        g.add("req", Kind.REQUIREMENT, "maintain 25 kn", tier=EvidenceTier.M1)
    with pytest.raises(ValueError, match="may not carry tier"):
        g.add("asm", Kind.ASSUMPTION, "appendage drag is 4%", tier=EvidenceTier.L1)
    with pytest.raises(ValueError, match="may not carry tier"):
        g.add("ev", Kind.EVIDENCE, "R_T = 4.1 kN", tier=EvidenceTier.NA)
    # An `-INVALID` badge is a property of a RESULT: no solve runs "at
    # L3-INVALID", so an EXPERIMENT may not claim one.
    with pytest.raises(ValueError, match="may not carry tier"):
        g.add("exp", Kind.EXPERIMENT, "L3 RANS", tier=EvidenceTier.L3_INVALID)
    # ...but the EVIDENCE it produced may, or a downgraded result could not be
    # recorded at all, and the only way to file it would be to relabel it valid.
    g.add("exp", Kind.EXPERIMENT, "L3 RANS", tier=EvidenceTier.L3)
    g.add("ev", Kind.EVIDENCE, "R_T = nan", tier=EvidenceTier.L3_INVALID)
    g.support("exp", "ev")


def test_the_tier_cannot_be_reassigned_out_of_the_vocabulary_after_construction():
    """A construction-only check is not a guard on a mutable object.

    `Node` is deliberately mutable — the confidence tests revise a value in
    place — so `n.tier = "sea trial"` is the third door, next to `add()` and
    `from_json`. All three land in `__setattr__`.
    """
    g = _graph()
    n = g.nodes["ev"]
    with pytest.raises(ValueError, match="not an evidence tier"):
        n.tier = "sea trial"
    with pytest.raises(ValueError, match="may not carry tier"):
        n.tier = EvidenceTier.NA           # evidence that declines to say
    with pytest.raises(ValueError, match="may not carry tier"):
        g.nodes["dec"].tier = EvidenceTier.L3
    assert n.tier is EvidenceTier.L3, "a refused assignment must not stick"
    n.tier = "L3-INVALID"                  # a legal revision still works
    assert n.tier is EvidenceTier.L3_INVALID


def test_a_simulation_may_not_produce_a_real_observation_or_the_reverse():
    """The laundering the graph exists to prevent, in both directions.

    `EXPERIMENT -> EVIDENCE` is the only edge on which a number acquires its
    provenance (ALLOWED_SUPPORT), so it is the only place this can happen
    without anyone writing a false sentence. Written BEFORE any observation row
    exists — once telemetry lands, the vocabulary is being fixed under a
    deadline by whoever is ingesting it (BUILD-PLAN §17.1.1).
    """
    g = EvidenceGraph()
    g.add("rans", Kind.EXPERIMENT, "L3 RANS @ density 1.0", tier=EvidenceTier.L3)
    g.add("trial", Kind.EXPERIMENT, "sea trial, hull 004", tier=EvidenceTier.M1)
    g.add("ev_obs", Kind.EVIDENCE, "R_T = 4.10 kN measured", value=4100.0,
          sigma=310.0, tier=EvidenceTier.M1)
    g.add("ev_sim", Kind.EVIDENCE, "R_T = 4.10 kN computed", value=4100.0,
          sigma=620.0, tier=EvidenceTier.L3)
    with pytest.raises(ValueError, match="may not produce"):
        g.support("rans", "ev_obs")        # a solve wearing a measurement
    with pytest.raises(ValueError, match="may not produce"):
        g.support("trial", "ev_sim")       # a measurement wearing a solve
    g.support("rans", "ev_sim")            # and the honest pairings still work
    g.support("trial", "ev_obs")
    assert g.nodes["ev_obs"].origin is Origin.OBSERVED
    assert g.nodes["ev_sim"].origin is Origin.COMPUTED


def test_the_tier_survives_serialization_and_an_unknown_one_is_refused_on_the_way_in(
        tmp_path):
    """A file is an untrusted boundary.

    A constructor-side fix alone would have been bypassed here: `from_json`
    rebuilds nodes with `Node(**d)` straight from whatever is on disk, so the
    guard has to sit where BOTH doors pass through it.
    """
    g = _graph()
    p = tmp_path / "deg.json"
    g.save(p)

    # written as the badge the rest of the project greps for, not "EvidenceTier.L3"
    raw = json.loads(p.read_text())
    assert raw["ev"]["tier"] == "L3" and raw["req"]["tier"] == "NA"
    assert "EvidenceTier" not in p.read_text()

    back = EvidenceGraph.load(p)
    assert back.nodes["ev"].tier is EvidenceTier.L3
    assert back.nodes["req"].tier is EvidenceTier.NA
    assert ", L3]" in back.explain("dec")

    for tampered, exc, match in (
        ("sea trial", ValueError, "not an evidence tier"),
        ("", ValueError, "not an evidence tier"),
        ("L3 ", ValueError, "not an evidence tier"),
    ):
        raw["ev"]["tier"] = tampered
        with pytest.raises(exc, match=match):
            EvidenceGraph.from_json(json.dumps(raw))

    # a node written by an older build, with no tier field at all
    raw["ev"].pop("tier")
    with pytest.raises(TypeError, match="tier"):
        EvidenceGraph.from_json(json.dumps(raw))


def test_an_imported_stl_with_flipped_winding_is_REALLY_repaired(tmp_path):
    """AUDIT G7.1 (2026-08-14): the import path called `diagnose` — which
    only counts — and then wrote `import_winding_repaired={rep.applied}`, a
    field only `repair()` fills. The receipt was structurally always "no"
    while the block comment promised repair, and a conflicted STL sailed
    into the mesher unrepaired under a receipt that read as checked.

    The fixture is the honest tetrahedron above with ONE face flipped; the
    case must (a) write a hull.stl whose winding is consistent again,
    (b) say so in the receipt, and (c) list what was applied."""
    from navalai.mesh_repair import IMPORTED, diagnose

    v = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (2, 1, 3)]   # last one FLIPPED
    out = ["solid s"]
    for a, b, c in faces:
        out += ["facet normal 0 0 0", "outer loop"]
        out += [f"vertex {v[i][0]} {v[i][1]} {v[i][2]}" for i in (a, b, c)]
        out += ["endloop", "endfacet"]
    out.append("endsolid s")
    stl = tmp_path / "flipped.stl"
    stl.write_text("\n".join(out) + "\n")
    assert diagnose(str(stl), origin=IMPORTED).found["winding_conflicts"] > 0

    case = tmp_path / "case"
    write_resistance_case_from_stl(stl, KCS_MODEL_L, KCS_MODEL_U, case,
                                   end_time=1.0, scale=1.0, np_procs=2,
                                   symmetric=True, n_layers=2)
    info = (case / "case.info").read_text()
    assert "import_winding_repaired=yes" in info, info
    assert "reoriented to a consistent outward winding" in info, info
    written = case / "constant" / "triSurface" / "hull.stl"
    rep2 = diagnose(str(written), origin=IMPORTED)
    assert rep2.found["winding_conflicts"] == 0, (
        "the receipt says repaired but the WRITTEN surface still carries "
        f"{rep2.found['winding_conflicts']} winding conflict(s)")
    assert rep2.found["boundary_edges"] == 0


def test_a_clean_import_is_not_repaired_and_says_so(tmp_path):
    """The mirror guard: when nothing was needed, no repair is applied and
    the receipt says none. Byte identity of hull.stl is NOT the claim — the
    bow-patch instrument (`split_bow_region`) legitimately renames the
    facets into main/bow regions downstream of the import — so what is
    asserted is the REPAIR half: receipt says none, and the written surface
    carries exactly the source's facets (same count, still clean)."""
    from navalai.mesh_repair import IMPORTED, diagnose

    stl = tmp_path / "clean.stl"
    stl.write_text(_STL)
    case = tmp_path / "case"
    write_resistance_case_from_stl(stl, KCS_MODEL_L, KCS_MODEL_U, case,
                                   end_time=1.0, scale=1.0, np_procs=2,
                                   symmetric=True, n_layers=2)
    info = (case / "case.info").read_text()
    assert "import_winding_repaired=no" in info
    assert "import_repairs_applied=none" in info
    written = case / "constant" / "triSurface" / "hull.stl"
    assert written.read_text().count("facet normal") == _STL.count(
        "facet normal")
    rep = diagnose(str(written), origin=IMPORTED)
    assert rep.found["winding_conflicts"] == 0
    assert rep.found["boundary_edges"] == 0


# --------------------------------------------------------------------------
# CFD audit P1-8: THEORY FIRST, THEN THE BOOK, THEN A SOLVE.
#
# THE INCIDENT THIS EXISTS FOR. The audit found ~30 findings that were
# correct and PROSE-ONLY, and the most expensive class was the one where
# a closed form already answered the question a solve was about to be
# bought for. `preflight.theory_answers` and `preflight.already_measured`
# were written and then had NO CALLER for a day — a bar that exists and
# is not consulted, which §16 names as this repository's defect class
# (nine incidents on 2026-08-20 alone). The planner is the ONE place in
# the tree where an L3 grid is chosen, so the bar belongs here or nowhere.
#
# The measured prices that make it worth a gate: an L3 grid is hours to
# ~69 h for a triplet, while `lambda = 2*pi*U^2/g` and the ITTC-57 line
# are microseconds. A refusal is RECORDED on `Plan.rejected`, never
# silently dropped, because the audit's other recurring defect was
# unmeasured things being reported as fine.
# --------------------------------------------------------------------------

def _loose_priors():
    """A resistance belief far too vague for the 10% target, so an L3 grid
    is genuinely WANTED — otherwise the test proves nothing when it does
    not appear."""
    from navalai.planner import Belief
    return {"resistance": Belief("resistance", 900.0, 400.0, tier="prior")}


def test_theory_first_refuses_an_l3_grid_for_a_question_theory_answers():
    """A wavelength question must not buy a RANS grid."""
    from navalai import planner as pl

    q = frozenset({"resistance"})
    theory_q = pl.plan("what is the transverse wavelength at this speed?",
                       q, _loose_priors())
    open_q = pl.plan("how does this stern's wave system interact with the "
                     "tunnel?", q, _loose_priors())

    assert not any(e.tier == "L3" for e, *_ in theory_q.steps), (
        "the planner bought an L3 grid for a question closed-form theory "
        "answers (lambda = 2*pi*U^2/g) — the audit's P1-8 trigger is not "
        f"firing: {[e.name for e, *_ in theory_q.steps]}")
    assert any(e.tier == "L3" for e, _ in theory_q.rejected), (
        "the L3 candidates were dropped SILENTLY. A run that was not "
        "bought must be visible with its reason on Plan.rejected, or the "
        "policy is indistinguishable from an omission")
    assert any("theory already answers" in why
               for _, why in theory_q.rejected)
    # ... and the trigger must not be a blanket ban: an open question is
    # exactly what a solve is for, so L3 must still be reachable.
    assert any(e.tier == "L3" for e, *_ in open_q.steps) or \
        any(e.tier == "L3" and "theory already answers" not in why
            for e, why in open_q.rejected), (
        "P1-8 removed L3 from a question with NO closed form — that is a "
        "ban on CFD, not a theory-first policy")


def test_theory_first_refuses_a_resolve_of_a_surface_already_in_the_book():
    """The same STL at the same speed buys a second sample, not a number."""
    from navalai import cfd_kb
    from navalai import planner as pl

    book = cfd_kb.anchors(settled_only=True)
    if not book:
        import pytest
        pytest.skip("no settled anchors in data/cfd_anchors.json")
    name, a = sorted(book.items())[0]
    sha, speed = a.get("stl_sha256"), a.get("speed_ms")
    if not sha or not speed:
        import pytest
        pytest.skip(f"anchor {name} carries no sha/speed to re-query")

    q = frozenset({"resistance"})
    cond = pl.Condition(lwl=float(a.get("lwl_m") or 7.2786),
                        speed=float(speed))
    again = pl.plan("what is this hull's total resistance?", q,
                    _loose_priors(), cond=cond, stl_sha=sha)
    fresh = pl.plan("what is this hull's total resistance?", q,
                    _loose_priors(), cond=cond, stl_sha="0" * 64)

    assert not any(e.tier == "L3" for e, *_ in again.steps), (
        f"the planner re-bought a grid for surface {sha[:12]} at "
        f"{speed} m/s, which {name} already measured")
    assert any("already solved at this speed" in why
               for _, why in again.rejected)
    assert any(e.tier == "L3" for e, *_ in fresh.steps), (
        "an UNMEASURED surface must still be able to buy a grid — "
        "otherwise the book's identity check is not what refused")
