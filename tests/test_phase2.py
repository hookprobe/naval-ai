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
    assert (tmp_path / "a" / "system" / "controlDict").exists()
    assert "METAL-GATED" in (tmp_path / "a" / "case.info").read_text()
