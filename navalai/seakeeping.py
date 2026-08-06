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


# ---------------------------------------------------------------------------
# THE SOLVER IS CONSTRUCTED IN ONE PLACE, EXPLICITLY (gaps F2 and F3).
#
# F2. `BuildPlan §1.3` says "the default indirect BIE is inaccurate — switch to
# the direct BIE", and every solver in this file was a bare `cpt.BEMSolver()`.
# Capytaine 2.3.1's signature is `BEMSolver(*, green_function=None,
# engine=None, method='indirect')`, so the code ran the exact trap the plan
# names, in the module whose docstring quotes the accuracy study.
#
# MEASURED 2026-08-07 on this project's OWN Gate 2 anchor — Hulme's (1982)
# floating hemisphere, mu33/(2/3 pi rho a^3) -> 0.8310 as omega -> 0, at
# resolution (26, 52), omega 0.15:
#
#     method='indirect'  0.85328   +2.68%   <- what shipped
#     method='direct'    0.83671   +0.69%
#
# Same mesh, same frequency, same 0.07 s: the direct BIE is 3.9x closer to the
# analytic answer. The 6% tolerance in `tests/test_phase2.py` is why nothing
# noticed.
#
# F3. The Delhommeau tabulation defaults to 676 x 372 in this version, so the
# grid the plan asks for was correct ONLY because the library happened to
# choose it. A library default is not a decision, and a downgrade in a future
# release would re-open the trap silently with no test to notice. Pinned here,
# and asserted in `tests/test_gapfix_physics.py`.
BIE_METHOD = "direct"
TABULATION = {"tabulation_nr": 676, "tabulation_nz": 372}


def solver(method: str = BIE_METHOD):
    """The one BEM solver this module uses, with the method and the
    Green-function tabulation stated rather than inherited.

    `method` is an argument only because the FAR-FIELD post-processing
    capytaine offers (`post_pro.kochin.compute_kochin`) raises unless the
    problem was solved with `method='indirect'` and `keep_details=True` — it
    reads the source strengths, which the direct formulation does not produce.
    A caller that needs Kochin functions must therefore ask for the less
    accurate BIE and say why; nothing in the product does today.
    """
    import capytaine as cpt
    from capytaine.green_functions.delhommeau import Delhommeau

    return cpt.BEMSolver(green_function=Delhommeau(**TABULATION),
                         method=method)


@dataclass(frozen=True)
class SeakeepingResult:
    """One L2 answer, with the discretisation uncertainty it was measured with.

    GAP F4: this type — the only one in the codebase carrying
    `uncertainty_rel` — was defined and NEVER CONSTRUCTED. `convergence_sweep`
    was called only from tests, and `evaluate.revalidate` assembled its own
    dict with its own second copy of the mesh-to-mesh comparison, so no L2
    number ever left this module with a convergence-derived sigma attached to
    it. `heave_seakeeping()` below is the constructor, and revalidate() now
    consumes it instead of recomputing it.
    """

    omegas: np.ndarray          # rad/s
    added_mass_heave: np.ndarray
    damping_heave: np.ndarray
    rao_heave: np.ndarray       # |RAO| heave (unit wave) at `wave_direction`
    n_panels: int
    uncertainty_rel: float | None   # from convergence sweep; None if single mesh
    wave_direction: float = 0.0     # rad, capytaine convention (0 = along +x)
    method: str = BIE_METHOD
    meshes: tuple = ()              # the (nx, nz) levels the sigma came from

    def as_dict(self) -> dict:
        """JSON-safe view, for `Evaluation.seakeeping` and the provenance DB."""
        return {
            "omegas": np.asarray(self.omegas).tolist(),
            "added_mass_heave": np.asarray(self.added_mass_heave).tolist(),
            "damping_heave": np.asarray(self.damping_heave).tolist(),
            "rao_heave": np.asarray(self.rao_heave).tolist(),
            "n_panels": int(self.n_panels),
            "uncertainty_rel": self.uncertainty_rel,
            "wave_direction": float(self.wave_direction),
            "solver": "capytaine",
            "method": self.method,
            "tabulation": dict(TABULATION),
            "meshes": [list(m) for m in self.meshes],
        }


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
    s = solver()
    am = np.empty(len(omegas))
    dp = np.empty(len(omegas))
    for i, w in enumerate(omegas):
        pb = cpt.RadiationProblem(body=body, radiating_dof="Heave",
                                  omega=float(w), rho=rho, g=G)
        res = s.solve(pb, keep_details=False)
        am[i] = res.added_masses["Heave"]
        dp[i] = res.radiation_dampings["Heave"]
    return am, dp, body.mesh.nb_faces


def heave_rao(hull: Hull, omegas: np.ndarray, disp_kg: float, awp: float,
              nx: int = 30, nz: int = 8, rho: float = 1000.0,
              wave_direction: float = 0.0) -> np.ndarray:
    """|RAO| of heave in long-crested waves from `wave_direction` (zero speed).

    RAO(w) = |F_exc| / |-w^2 (m + A33) + i w B33 + C33|,  C33 = rho g Awp.
    Physics check built into Gate D: RAO -> 1 as w -> 0 (a small boat follows
    long waves).

    `wave_direction` is in RADIANS, in capytaine's convention: 0 is a wave
    travelling along +x, i.e. from the transom toward the stem in this
    project's hull frame (`weights.py` fixes x = 0 at the transom), and pi/2 is
    beam-on. It used to be hard-coded 0.0 while this docstring said
    "head/beam", so the one heading the caller could not choose was the one
    the docstring named two of. Heading matters for heave less than for surge,
    but "less" is not "not at all" and an argument that does not exist cannot
    be swept — see gap F5 and `waves.heave_response`.
    """
    import capytaine as cpt
    from capytaine.bem.airy_waves import froude_krylov_force

    body = _body_from_hull(hull, nx, nz)
    s = solver()
    c33 = rho * G * awp
    out = np.empty(len(omegas))
    for i, w in enumerate(omegas):
        rad = s.solve(cpt.RadiationProblem(
            body=body, radiating_dof="Heave", omega=float(w), rho=rho, g=G),
            keep_details=False)
        dif_pb = cpt.DiffractionProblem(
            body=body, wave_direction=float(wave_direction), omega=float(w),
            rho=rho, g=G)
        dif = s.solve(dif_pb, keep_details=False)
        a33 = rad.added_masses["Heave"]
        b33 = rad.radiation_dampings["Heave"]
        # excitation = Froude-Krylov + diffraction (scattering alone -> 0 at
        # long waves; the physics-limit gate below catches that mistake)
        f = froude_krylov_force(dif_pb)["Heave"] + dif.forces["Heave"]
        den = -w**2 * (disp_kg + a33) + 1j * w * b33 + c33
        out[i] = abs(f) / max(abs(den), 1e-12)
    return out


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


# Two mesh levels, so the sigma an L2 badge carries is a MEASURED
# discretisation uncertainty and not a declared fraction. This module's own
# docstring names mesh sensitivity as mandatory (NREL/OMAE 2024); a
# single-mesh BEM result has no basis for an error bar at all. The levels
# lived in `evaluate.py` as `_L2_MESHES` while the type that reports the
# uncertainty lived here and was never built — see `SeakeepingResult`.
L2_MESHES = ((20, 5), (28, 7))


def heave_seakeeping(hull: Hull, omegas: np.ndarray, disp_kg: float,
                     awp: float, rho: float = 1000.0,
                     meshes: tuple = L2_MESHES,
                     wave_direction: float = 0.0) -> SeakeepingResult:
    """The L2 heave answer for one hull, as a `SeakeepingResult`.

    Solves the coarse and fine meshes, takes the worst relative added-mass
    change between them across the frequency set as `uncertainty_rel`, and
    returns the fine-mesh coefficients and RAO carrying it.

    GAP F4: this function is the missing constructor. Before it, the only L2
    type that carried an uncertainty was never instantiated, and the escalation
    path in `evaluate.revalidate` held a hand-rolled copy of this arithmetic —
    the "one number, two homes" defect, in the module whose whole purpose is to
    attach an honest band to a number.

    REFUSES rather than degrades: fewer than two mesh levels means there is no
    convergence evidence, and a single-mesh L2 result with `uncertainty_rel`
    left at None would be badged with a sigma of nothing at all.
    """
    if len(meshes) < 2:
        raise ValueError(
            f"heave_seakeeping needs at least two mesh levels to measure a "
            f"discretisation uncertainty; got {meshes!r}. A single-mesh BEM "
            f"result has no basis for an error bar, and this module's premise "
            f"(NREL/OMAE 2024) is that the mesh is the dominant one.")
    w = np.asarray(omegas, float)
    (nx0, nz0), (nx1, nz1) = meshes[0], meshes[-1]
    am0, _dp0, _n0 = heave_coeffs(hull, w, nx0, nz0, rho)
    am1, dp1, npan = heave_coeffs(hull, w, nx1, nz1, rho)
    rao = heave_rao(hull, w, disp_kg, awp, nx1, nz1, rho,
                    wave_direction=wave_direction)
    unc = float(np.max(np.abs(am1 - am0) / np.maximum(np.abs(am1), 1e-12)))
    return SeakeepingResult(
        omegas=w, added_mass_heave=am1, damping_heave=dp1, rao_heave=rao,
        n_panels=int(npan), uncertainty_rel=unc,
        wave_direction=float(wave_direction), method=BIE_METHOD,
        meshes=tuple(tuple(m) for m in meshes))


def hemisphere_added_mass_lowfreq(radius: float = 1.0, n_theta: int = 26,
                                  n_phi: int = 52, omega: float = 0.15,
                                  rho: float = 1000.0,
                                  method: str = BIE_METHOD) -> float:
    """Benchmark case: floating hemisphere heave added mass, near zero frequency.

    Analytic (Hulme 1982): mu33 / (2/3 pi rho a^3) -> 0.8310 as omega -> 0.
    This is the Gate 2 anchor that proves our Capytaine integration is wired
    correctly (solver, units, dof, mesh orientation).

    `method` is exposed so the anchor can be measured with BOTH boundary
    integral equations — that comparison is the evidence for gap F2 and it is
    asserted in `tests/test_gapfix_physics.py` rather than left as a claim.
    """
    import capytaine as cpt

    mesh = cpt.mesh_sphere(radius=radius, resolution=(n_theta, n_phi)).immersed_part()
    body = cpt.FloatingBody(mesh=mesh)
    body.add_translation_dof(name="Heave")
    pb = cpt.RadiationProblem(body=body, radiating_dof="Heave",
                              omega=omega, rho=rho, g=G)
    res = solver(method=method).solve(pb, keep_details=False)
    disp = (2.0 / 3.0) * np.pi * rho * radius**3
    return float(res.added_masses["Heave"]) / disp
