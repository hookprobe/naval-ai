"""CFDManifest — ONE description of the vessel a CFD case is about (§14).

The audit's G7 finding, verbatim class: the case generator carried a
PARALLEL mass model — mass = rho * V_STL, LCG = LCB, KG warned-and-defaulted
— while the L1 ladder held a positioned weight model whose KG was measured
19% away on KCS. Two mass models is two boats. This object is generated
FROM the canonical chain (geometry -> floated equilibrium -> mission) and
everything a case needs — mass, centres, attitude, fluid, condition, wave
resolution — reads from it. `case.info` is a RENDERING of this object,
never an independent source.

What it does NOT do: run anything. It is CFD-READY bookkeeping; the
CFD-VALIDATED claim still belongs to a converged campaign on the CFD node
(Gate 2M, watermark NONE).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field

import numpy as np

from ..constants import G_OPENFOAM, NU_FRESH_20C, RHO_FRESH_20C
from .case import (_DOMAIN_LENGTH_L, _NX_BASE, background_counts,
                   sixdof_properties)


@dataclass(frozen=True)
class CFDManifest:
    """Everything the case dictionaries derive from, in one signed place."""

    # --- identity ----------------------------------------------------------
    genome_sha256: str            # sha of the 16 parameter floats
    # --- geometry + floated state (the §13 single truth) -------------------
    lwl_m: float
    waterline_m: float            # wl0 at midships, ev.wl
    trim_deg: float               # the SOLVED equilibrium attitude
    displacement_kg: float        # ev.hydro.disp_kg — what the water carries
    mass_kg: float                # ev.masses.total_kg — what the boat weighs
    lcg_m: float
    tcg_m: float
    kg_above_keel_m: float        # the ballast lever the L1 GM used
    design_draft_m: float         # T from the genome: keel at z = -T in the
                                  # case frame (design WL at z = 0)
    wetted_m2: float
    # --- vessel ------------------------------------------------------------
    topology: str
    n_hulls: int
    separation_m: float
    # --- fluid (the CFD case convention, from the constants home) ----------
    rho_kg_m3: float = RHO_FRESH_20C
    nu_m2_s: float = NU_FRESH_20C
    g_m_s2: float = G_OPENFOAM
    # --- condition ---------------------------------------------------------
    speed_ms: float = 0.0
    fn: float = 0.0
    re: float = 0.0
    # --- domain / mesh request --------------------------------------------
    mesh_scale: float = 1.0
    nx_background: int = _NX_BASE
    domain_length_over_lwl: float = _DOMAIN_LENGTH_L
    symmetric: bool = True
    n_layers: int | None = None
    # --- numerics / waves --------------------------------------------------
    solver: str = "interFoam"
    turbulence: str = "kOmegaSST"
    timestep_policy: str = "adaptive (maxCo-controlled)"
    wavelength_m: float = 0.0
    cells_per_wavelength: float = 0.0
    notes: tuple[str, ...] = field(default=())

    def render_case_info(self) -> str:
        """The `[manifest]` block for case.info — a RENDERING, no new facts."""
        lines = ["[manifest]"]
        for k, v in asdict(self).items():
            if k == "notes":
                continue
            lines.append(f"manifest_{k}={v}")
        for n in self.notes:
            lines.append(f"manifest_note={n}")
        return "\n".join(lines) + "\n"

    def free_motion(self, beam_m: float, awp_m2: float,
                    i_l_m4: float | None = None) -> dict:
        """The sixDoF dict, from THIS mass model — the G7 fix made usable.

        `motion_from_geometry` stays the honest fallback for an IMPORTED
        surface (a bare STL has no weight model to consult); a genome hull
        has one, and this hands the solver the same mass, centres and KG
        the ladder floated."""
        return sixdof_properties(
            mass_kg=self.mass_kg,
            cog=(self.lcg_m, self.tcg_m,
                 self.kg_above_keel_m - self.design_draft_m),
            k_roll=0.40 * beam_m, k_pitch=0.25 * self.lwl_m,
            k_yaw=0.25 * self.lwl_m, lwl=self.lwl_m, awp_m2=awp_m2,
            i_l_m4=i_l_m4, symmetric=self.symmetric, rho=self.rho_kg_m3)


def manifest_from_evaluation(ev, mission, *, mesh_scale: float = 1.0,
                             symmetric: bool = True,
                             n_layers: int | None = None) -> CFDManifest:
    """Build the manifest from the canonical chain — an OK L1 evaluation.

    Refuses an evaluation that never floated: a case about a hull whose
    equilibrium was refused would be a case about nothing.
    """
    if ev.hydro is None or ev.masses is None:
        raise ValueError(
            "manifest_from_evaluation needs a floated evaluation "
            "(hydro + masses); this one stopped at "
            f"tier {ev.tier}: {ev.violations[:1]}")
    u = mission.cruise_speed_ms()
    lwl = float(ev.hull_lwl_m)
    fn = u / math.sqrt(G_OPENFOAM * lwl)
    re = u * lwl / NU_FRESH_20C
    lam = 2.0 * math.pi * fn * fn * lwl
    from ..fidelity import cells_per_wavelength as _cpw
    genome = np.asarray(ev.params, float)
    from .. import grammar
    t_design = float(grammar.named(genome)["T"])
    return CFDManifest(
        genome_sha256=hashlib.sha256(genome.tobytes()).hexdigest(),
        lwl_m=lwl,
        waterline_m=float(ev.wl),
        trim_deg=float(ev.trim_deg or 0.0),
        displacement_kg=float(ev.hydro.disp_kg),
        mass_kg=float(ev.masses.total_kg),
        lcg_m=float(ev.masses.lcg_m),
        tcg_m=float(ev.masses.tcg_m),
        # the SAME lever the ladder's GM consumed: vcg_above_keel(T_design)
        kg_above_keel_m=float(ev.masses.vcg_above_keel(t_design)),
        design_draft_m=t_design,
        wetted_m2=float(ev.hydro.wetted),
        topology=str(ev.vessel.get("topology", "monohull")),
        n_hulls=int(ev.vessel.get("n_hulls", 1)),
        separation_m=float(ev.vessel.get("separation_m", 0.0)),
        speed_ms=u, fn=fn, re=re,
        mesh_scale=mesh_scale,
        nx_background=background_counts(mesh_scale, symmetric)[0],
        symmetric=symmetric, n_layers=n_layers,
        wavelength_m=lam,
        cells_per_wavelength=float(_cpw(fn, mesh_scale)),
        notes=(
            "mass/centres/attitude from the L1 positioned weight model at "
            "the SOLVED equilibrium — never rho*V_STL (audit G7)",
            "fluid is the 20C case convention (constants.py); the L1 design "
            "condition is rho=1000 — a declared difference, not drift",
        ))
