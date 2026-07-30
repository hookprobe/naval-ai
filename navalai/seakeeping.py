"""L2 seakeeping: Capytaine BEM wrapper (BuildPlan Phase 2).

Research-flagged traps handled here (NREL/OMAE 2024 accuracy study):
  - mesh sensitivity is mandatory -> convergence_sweep() is part of the API
  - forward speed is approximate  -> this tier reports zero-speed seakeeping
    quantities only; resistance stays with L1/L3
Results carry tier='L2' and a convergence-derived uncertainty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from .geometry import G, Hull

logging.getLogger("capytaine").setLevel(logging.ERROR)


@dataclass(frozen=True)
class SeakeepingResult:
    omegas: np.ndarray          # rad/s
    added_mass_heave: np.ndarray
    damping_heave: np.ndarray
    rao_heave: np.ndarray       # |RAO| heave in beam seas approx (unit wave)
    n_panels: int
    uncertainty_rel: float | None   # from convergence sweep; None if single mesh


def _body_from_hull(hull: Hull, nx: int, nz: int):
    import capytaine as cpt

    verts, faces = hull.panel_mesh(nx=nx, nz=nz)
    mesh = cpt.Mesh(vertices=verts, faces=faces)
    mesh.heal_mesh()
    body = cpt.FloatingBody(mesh=mesh, name="hull")
    body.add_translation_dof(name="Heave")
    return body


def heave_coeffs(hull: Hull, omegas: np.ndarray, nx: int = 40,
                 nz: int = 10, rho: float = 1000.0):
    """Heave added mass + radiation damping over a frequency set."""
    import capytaine as cpt

    body = _body_from_hull(hull, nx, nz)
    solver = cpt.BEMSolver()
    am = np.empty(len(omegas))
    dp = np.empty(len(omegas))
    for i, w in enumerate(omegas):
        pb = cpt.RadiationProblem(body=body, radiating_dof="Heave",
                                  omega=float(w), rho=rho, g=G)
        res = solver.solve(pb, keep_details=False)
        am[i] = res.added_masses["Heave"]
        dp[i] = res.radiation_dampings["Heave"]
    return am, dp, body.mesh.nb_faces


def convergence_sweep(hull: Hull, omega: float, levels=((24, 6), (36, 9), (48, 12)),
                      rho: float = 1000.0):
    """Added-mass at one frequency across mesh refinements.

    Returns (values, n_panels, rel_change_last) — the honest uncertainty basis.
    """
    vals, panels = [], []
    for nx, nz in levels:
        am, _dp, nb = heave_coeffs(hull, np.array([omega]), nx, nz, rho)
        vals.append(float(am[0]))
        panels.append(nb)
    rel = abs(vals[-1] - vals[-2]) / max(abs(vals[-1]), 1e-12)
    return np.array(vals), np.array(panels), rel


def hemisphere_added_mass_lowfreq(radius: float = 1.0, n_theta: int = 26,
                                  n_phi: int = 52, omega: float = 0.15,
                                  rho: float = 1000.0) -> float:
    """Benchmark case: floating hemisphere heave added mass, near zero frequency.

    Analytic (Hulme 1982): mu33 / (2/3 pi rho a^3) -> 0.8310 as omega -> 0.
    This is the Gate 2 anchor that proves our Capytaine integration is wired
    correctly (solver, units, dof, mesh orientation).
    """
    import capytaine as cpt

    mesh = cpt.mesh_sphere(radius=radius, resolution=(n_theta, n_phi)).immersed_part()
    body = cpt.FloatingBody(mesh=mesh)
    body.add_translation_dof(name="Heave")
    solver = cpt.BEMSolver()
    pb = cpt.RadiationProblem(body=body, radiating_dof="Heave",
                              omega=omega, rho=rho, g=G)
    res = solver.solve(pb, keep_details=False)
    disp = (2.0 / 3.0) * np.pi * rho * radius**3
    return float(res.added_masses["Heave"]) / disp
