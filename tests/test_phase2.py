"""Gate 2 (this-machine scope): Capytaine wired correctly (Hulme hemisphere
anchor), hull BEM runs with convergence sweep, CFD case generation deterministic."""

import math
import re

import numpy as np
import pytest

from navalai.cfd.case import write_resistance_case
from navalai.geometry import Hull
from navalai.seakeeping import (convergence_sweep, heave_coeffs,
                                hemisphere_added_mass_lowfreq)
from tests.test_phase0 import mid_params

capytaine = pytest.importorskip("capytaine")


def test_hemisphere_hulme_anchor():
    """Hulme (1982): heave added mass of a floating hemisphere at omega->0 is
    0.8310 x displaced mass. Coarse-mesh tolerance 6%."""
    ratio = hemisphere_added_mass_lowfreq(n_theta=20, n_phi=40, omega=0.15)
    assert ratio == pytest.approx(0.8310, rel=0.06), f"got {ratio:.4f}"


def test_hull_heave_coeffs_physical():
    h = Hull(mid_params())
    omegas = np.array([0.8, 1.5, 2.5])
    am, dp, nb = heave_coeffs(h, omegas, nx=24, nz=6)
    assert nb > 200
    assert (am > 0).all()            # heave added mass positive
    assert (dp >= -1e-6).all()       # radiation damping non-negative


def test_convergence_sweep_reports_uncertainty():
    h = Hull(mid_params())
    vals, panels, rel = convergence_sweep(h, omega=1.2,
                                          levels=((16, 4), (24, 6), (32, 8)))
    assert panels[2] > panels[0]
    assert rel < 0.25, f"mesh far from convergence: {vals}"


def test_cfd_case_generation_deterministic(tmp_path):
    h = Hull(mid_params())
    meta1 = write_resistance_case(h, 2.5, tmp_path / "a")
    meta2 = write_resistance_case(h, 2.5, tmp_path / "b")
    assert meta1["stl_sha256"] == meta2["stl_sha256"]
    # a COMPLETE runnable case: mesh, schemes, fields, physics, decomposition
    for rel in ("system/controlDict", "system/blockMeshDict",
                "system/snappyHexMeshDict", "system/fvSchemes",
                "system/fvSolution", "system/decomposeParDict",
                "system/setFieldsDict", "system/surfaceFeatureExtractDict",
                "constant/transportProperties", "constant/turbulenceProperties",
                "constant/g", "0/U", "0/p_rgh", "0/alpha.water", "0/k",
                "0/omega", "0/nut"):
        assert (tmp_path / "a" / rel).exists(), rel
    assert "Gate 2M" in (tmp_path / "a" / "case.info").read_text()
    # CFD hull must be a closed manifold (Mac smoke run found 198 open edges
    # on the wetted-only shell) with outward windings and plausible volume
    from navalai.cfd.case import stl_watertight_report
    rep = stl_watertight_report(tmp_path / "a" / "constant" / "triSurface" / "hull.stl")
    assert rep["watertight"], rep
    assert 10.0 < rep["signed_volume"] < 60.0
    # v2606 mandatory addLayers entries present
    snappy = (tmp_path / "a" / "system" / "snappyHexMeshDict").read_text()
    for key in ("maxFaceThicknessRatio", "maxThicknessToMedialRatio",
                "minMedialAxisAngle", "nBufferCellsNoExtrude", "nLayerIter"):
        assert key in snappy, key
    # inlet alpha must be height-stratified (air-injection drain bug, smoke #2)
    alpha = (tmp_path / "a" / "0" / "alpha.water").read_text()
    assert "exprFixedValue" in alpha and "pos().z()" in alpha
    # GCI triplet scaling actually changes the background mesh
    m_fine = write_resistance_case(h, 2.5, tmp_path / "c", scale=2.0)
    assert m_fine["bg_cells"] > 6 * meta1["bg_cells"]


def test_free_surface_is_resolved_and_refinement_is_systematic(tmp_path):
    """Mac GCI incident (2026-08-04): the own-hull triplet reported p=nan and
    GCI 58.5% (oscillatory) even after the waterline-alignment fix. Two causes,
    both measured: refinementRegions was EMPTY, so the wave field ran at
    5.1/7.1/10.2 cells per wavelength against the >=20 standard with a
    background cell 0.63-1.25 m tall against ~0.1 m waves; and snapping nz to a
    multiple of 3 gave z-refinement ratios of 1.333 and 1.5, so the three grids
    were never a refinement family (effective r = 1.297 then 1.368).
    """
    h = Hull(mid_params())
    metas = {n: write_resistance_case(h, 2.57, tmp_path / n, scale=s)
             for n, s in (("coarse", 1.0), ("medium", 2 ** 0.5), ("fine", 2.0))}

    for name, m in metas.items():
        # the bar the wave field failed by 4x before the fix
        assert m["cells_per_wavelength"] >= 20.0, (name, m)
        snappy = (tmp_path / name / "system" / "snappyHexMeshDict").read_text()
        assert "freeSurface" in snappy, f"{name}: no free-surface refinement"
        assert "refinementRegions {}" not in snappy, f"{name}: empty regions"

    # systematic refinement: a CONSISTENT r, close to the sqrt(2) claimed
    r12 = (metas["medium"]["bg_cells"] / metas["coarse"]["bg_cells"]) ** (1 / 3)
    r23 = (metas["fine"]["bg_cells"] / metas["medium"]["bg_cells"]) ** (1 / 3)
    assert abs(r12 - 2 ** 0.5) < 0.03, r12
    assert abs(r23 - 2 ** 0.5) < 0.03, r23
    assert abs(r12 - r23) / max(r12, r23) < 0.02, (r12, r23)


def test_waterline_sits_on_a_block_face_for_any_cell_count(tmp_path):
    """The z=0 split is a blockMesh BLOCK BOUNDARY, so a mesh face lies on the
    waterline by construction. This replaces the 'nz must be a multiple of 3'
    rule, which held only for the specific 1.5L/0.75L domain and put the
    medium grid's interface mid-cell (nz=25) -- doubling its drag.
    """
    h = Hull(mid_params())
    # deliberately awkward scales: none of these would give a "nice" nz
    for i, s in enumerate((1.0, 2 ** 0.5, 2.0, 1.234, 0.777)):
        meta = write_resistance_case(h, 2.57, tmp_path / f"s{i}", scale=s)
        text = (tmp_path / f"s{i}" / "system" / "blockMeshDict").read_text()
        assert text.count("hex (") == 2, "waterline split block missing"
        # the middle vertex ring is exactly z=0, whatever the cell counts
        assert re.search(r"\(-?[\d.]+ -?[\d.]+ 0\)", text), text[:400]
        assert meta["tank_depth"] > 0


def test_near_wall_spacing_targets_the_wall_function_band(tmp_path):
    """Measured on the Mac (2026-08-04) once a yPlus function object existed:
    3 RELATIVE-sized layers gave hull y+ min 42 / avg 7491 / max 60017, one to
    three orders above the build plan's y+ ~ 30. Wall functions were being
    applied far outside their valid band, and skin friction is most of this
    hull's drag at Fn 0.26 -- so the triplet would have converged on a wrong
    number. First-layer thickness is now absolute, from the ITTC-57 line.
    """
    from navalai.cfd.case import first_layer_thickness

    # ITTC-57 at the reference condition: y+ 30 wants a ~0.7 mm first cell
    t1 = first_layer_thickness(2.57, 10.0, 30.0)
    assert 5e-4 < t1 < 1e-3, t1
    # y+ target and thickness are proportional
    assert first_layer_thickness(2.57, 10.0, 60.0) == pytest.approx(2 * t1,
                                                                    rel=1e-9)
    # faster ship -> thinner first cell (higher u_tau)
    assert first_layer_thickness(5.0, 10.0, 30.0) < t1

    h = Hull(mid_params())
    write_resistance_case(h, 2.57, tmp_path / "y", scale=1.0)
    snappy = (tmp_path / "y" / "system" / "snappyHexMeshDict").read_text()
    assert "relativeSizes false" in snappy, "relative sizing caused y+ ~ 7500"
    assert "firstLayerThickness" in snappy
    m = re.search(r"firstLayerThickness ([\d.e+-]+)", snappy)
    assert float(m.group(1)) == pytest.approx(t1, rel=1e-3)

    # the y+ instrumentation itself must be wired, or this regresses unseen
    ctrl = (tmp_path / "y" / "system" / "controlDict").read_text()
    assert "yPlus" in ctrl and "fieldFunctionObjects" in ctrl

    # the wall model is held FIXED across the triplet, so GCI bounds the outer
    # flow: first-layer thickness must NOT vary with grid scale
    coarse = write_resistance_case(h, 2.57, tmp_path / "yc", scale=1.0)
    fine = write_resistance_case(h, 2.57, tmp_path / "yf", scale=2.0)
    def first_layer(p):
        t = (p / "system" / "snappyHexMeshDict").read_text()
        return float(re.search(r"firstLayerThickness ([\d.e+-]+)", t).group(1))
    assert first_layer(tmp_path / "yc") == pytest.approx(
        first_layer(tmp_path / "yf"), rel=1e-9)
    assert coarse["bg_cells"] < fine["bg_cells"]


def test_tank_deepens_with_speed_instead_of_faking_deep_water(tmp_path):
    """Deep water is a property of the wave (lambda/2 = pi*U^2/g), not of LWL.
    A fixed 0.6L tank would be shallow above ~4.3 m/s for this hull and would
    return shallow-water resistance under a deep-water label.
    """
    h = Hull(mid_params())
    for speed in (2.57, 5.0, 7.0):
        m = write_resistance_case(h, speed, tmp_path / f"u{speed}")
        half_lambda = math.pi * speed ** 2 / 9.81
        assert m["tank_depth"] >= half_lambda, (speed, m["tank_depth"])
