"""Gate 2 (this-machine scope): Capytaine wired correctly (Hulme hemisphere
anchor), hull BEM runs with convergence sweep, CFD case generation deterministic."""

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
    # GCI triplet scaling actually changes the background mesh
    m_fine = write_resistance_case(h, 2.5, tmp_path / "c", scale=2.0)
    assert m_fine["bg_cells"] > 6 * meta1["bg_cells"]
