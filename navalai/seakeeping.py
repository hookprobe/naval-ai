"""Seakeeping: the ship's response to a seaway.

Two tiers live here, and they are separate by construction:

  - **L2, Capytaine BEM** (BuildPlan Phase 2). Research-flagged traps handled:
    mesh sensitivity is mandatory -> convergence_sweep() is part of the API;
    forward speed is approximate -> this tier reports zero-speed seakeeping
    quantities only, resistance stays with L1/L3. Results carry tier='L2' and
    a convergence-derived uncertainty.
  - **L0, closed-form slamming** (`wagner_impact_cp` and below). Wagner
    wedge-entry impact pressure. No solver, no mesh, microseconds. It takes an
    ANGLE and a VELOCITY and knows nothing about which part of a boat they
    belong to — the bow patch is its first call site, not its subject. The
    target vessel is a catamaran, whose governing slam is usually the WET DECK
    rather than the bow, and that case is meant to be a second call site here
    rather than a second implementation anywhere.

WHY SLAMMING LIVES HERE and not in `waves.py`, `cfd/case.py` or `limits.py`.
`waves.py` owns the SEAWAY (JONSWAP spectra, encounter frequency, sea-state
presets) — the environment, not the ship. `cfd/case.py` writes OpenFOAM case
DICTIONARIES; it is a code generator and has no analytic physics in it, which
is the property that keeps it reviewable. `limits.py` owns BARS the design must
clear, and an impact pressure is a computed quantity, not a bar. What is left
is this module, which is the one that already owns "what the hull DOES in a
wave" — and slamming is the same question as heave, one derivative harder. The
CFD instrument that measures the same quantity at L3 (the `hull_bow` patch and
the `bowSlammingPressure` function object in `navalai/cfd/case.py`) is
deliberately its own artefact: one computes, one measures, and they are
compared rather than sharing an implementation.

The L0 half imports nothing from capytaine, so it is usable in an environment
where the BEM stack is not installed (every capytaine import in this file is
function-local, and stays that way).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

from .geometry import G, RHO_WATER, Hull

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
                 nz: int = 10, rho: float = RHO_WATER):
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
              nx: int = 30, nz: int = 8, rho: float = RHO_WATER,
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
                      rho: float = RHO_WATER):
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
                     awp: float, rho: float = RHO_WATER,
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
                                  rho: float = RHO_WATER,
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


# ---------------------------------------------------------------------------
# L0 SLAMMING: Wagner wedge entry (plate P6)
#
# The companion to the `bowSlammingPressure` function object in
# `navalai/cfd/case.py`. Before P6, `P_slam` could not be obtained at ANY tier:
# there was no analytic model here and no instrument there —
#     grep -c "surfaceFieldValue\|hull_bow\|bowSlam" navalai/cfd/case.py  ->  0
# — so the quantity was not merely unmeasured, it was unmeasurABLE.
#
# THESE FUNCTIONS ARE NOT ABOUT THE BOW, AND THAT IS DELIBERATE.
# Wagner wedge entry is a general result: a wedge of half-angle beta meeting a
# water surface at velocity V. Nothing in it knows what part of a boat the
# wedge belongs to. So the API is `wagner_impact_cp(beta)` and
# `slam_pressure(beta, V, rho)` — an angle, a velocity and a density — rather
# than a bow routine, and a second impact site is a second CALL SITE.
#
# There is a specific second site already known, and it matters more than the
# first. THE TARGET VESSEL IS A CATAMARAN, and for a catamaran the governing
# slam is usually CROSS-STRUCTURE (WET-DECK) SLAMMING — the bridge deck
# between the demihulls impacting the wave surface in head seas — not bow
# slamming. A wave-piercing bow is specifically designed to reduce bow slam and
# does nothing at all for the wet deck. `bowSlammingPressure` therefore answers
# a NARROWER question than "is this hull safe in a seaway", and a green bow
# number is not evidence about the wet deck. That caveat is repeated at every
# artefact a future session might read alone: here, in `cfd/case.py` beside the
# function object, and in each generated `case.info`.
#
# A second IMPLEMENTATION of this physics for the wet deck would be this
# repository's signature defect — `gate2m.py` shipped a second GCI that
# returned -27.027% on a diverging family and printed PASS. What the wet-deck
# case needs is wiring, not arithmetic: a wet-deck patch (a horizontal cut of
# the cross-structure underside rather than a longitudinal cut at the stem),
# the RELATIVE vertical velocity between the wet deck and the wave surface as
# V_entry rather than the bow's entry velocity, and the local wet-deck
# deadrise, which for a flat bridge deck is near zero — i.e. exactly where
# `wagner_impact_cp` blows up, which is the physics saying what it always says
# about flat panels meeting water.
# ---------------------------------------------------------------------------

# The valid deadrise domain, in DEGREES, and both ends are refused rather than
# extrapolated.
#
# beta -> 0 is a FLAT bottom, where wedge-entry theory has no finite answer:
# the wetted-line velocity is unbounded, the impact becomes an air-cushioned
# compressible problem and the model is simply not about that flow any more.
# Returning `inf` would be a number a caller can carry into an arithmetic
# expression; raising is not.
#
# beta > 90 deg is a RE-ENTRANT section, not a wedge, and the expression below
# does not merely become inaccurate there — it changes SIGN. At beta = 100 deg
# it evaluates to -0.505, i.e. a NEGATIVE impact pressure coefficient, and
# `0.5 rho V^2 C_p` would then report a slam that SUCKS. That is this repo's
# defect class 1 in its purest form (an unmeasurable value scored as a good
# one), so the domain is a guard and `tests/test_slamming.py` feeds it the
# verbatim inputs it must reject.
DEADRISE_MIN_DEG = 0.0      # exclusive
DEADRISE_MAX_DEG = 90.0     # inclusive: 90 deg is a vertical wall, C_p = 0


def wagner_impact_cp(deadrise_deg: float) -> float:
    """Wagner wedge-entry impact pressure coefficient, dimensionless.

        C_p(beta) = pi * cot(beta) + (pi^2 / 2) * (pi / (2 beta) - 1)^2

    with beta in RADIANS inside; the ARGUMENT is in DEGREES because that is
    the unit the rest of this project carries deadrise in (`grammar.PARAMS`
    declares `beta_mid` and `beta_bow` in deg, and `geometry.hull_curves`
    converts them). A function that silently took radians while every caller
    holds degrees is a factor-57 error waiting to be committed.

    Structure, which is what the gate tests assert (they are the properties
    that make it a slamming model at all, and they hold exactly):

      - STRICTLY DECREASING in beta. Both terms are: cot is decreasing on
        (0, pi/2], and pi/(2 beta) - 1 is decreasing and NON-NEGATIVE there,
        so squaring preserves the direction. A sharp wave-piercing entry is
        always gentler than a blunt one; nothing in between can invert.
      - C_p(90 deg) = 0 in exact arithmetic — cot(pi/2) = 0 and
        pi/(2 * pi/2) - 1 = 0, so both terms vanish. A vertical wall does not
        slam, it shears. MEASURED in float it returns 1.92e-16, because
        `math.radians(90)` is the nearest double to pi/2 and `tan` of it is
        1.633e16 rather than infinite. That residue is stated rather than
        special-cased to a hard zero: a hand-placed 0.0 at one endpoint would
        hide whether the expression really goes there, and the gate asserts
        < 1e-15 with the value named.
      - C_p -> +inf as beta -> 0, at rate 1/beta^2 (the second term dominates:
        at 0.1 deg it is 3.99e6 against 1.80e3 for the first).

    WHAT THIS IS NOT, said out loud because the magnitude invites the mistake.
    This is not the classical Wagner PEAK, C_p = 1 + (pi / (2 tan beta))^2.
    Evaluated at beta = 10 deg the classical peak is 80.4 and this expression
    is 333.6 — 4.1x larger — because it is an integrated/asymptotic form
    including the flat-plate-limit correction rather than the pressure at the
    single instant and point of the spray-root maximum. So treat it as a
    CONSERVATIVE design value, and note that the P6 gate tests deliberately
    assert STRUCTURE (monotonicity, both limits, sign) and not calibration:
    calibration is what `bowSlammingPressure` is being built to supply, and
    this project does not score a number it has not measured.
    """
    beta = float(deadrise_deg)
    if not math.isfinite(beta):
        raise ValueError(
            f"deadrise must be finite, got {deadrise_deg!r}. A non-finite "
            f"deadrise propagates as a non-finite pressure, which is honesty "
            f"rule 1's 'no bare numbers' failing in the worst direction.")
    if not (DEADRISE_MIN_DEG < beta <= DEADRISE_MAX_DEG):
        raise ValueError(
            f"deadrise {beta} deg is outside ({DEADRISE_MIN_DEG}, "
            f"{DEADRISE_MAX_DEG}] deg, where Wagner wedge entry is defined. "
            f"At beta <= 0 the wetted-line velocity is unbounded and the "
            f"impact is an air-cushioned compressible problem this model does "
            f"not describe; at beta > 90 deg the section is re-entrant and "
            f"the expression returns a NEGATIVE coefficient (-0.505 at 100 "
            f"deg), i.e. a slam that sucks. Refused rather than extrapolated.")
    b = math.radians(beta)
    return (math.pi / math.tan(b)
            + 0.5 * math.pi ** 2 * (math.pi / (2.0 * b) - 1.0) ** 2)


def slam_pressure(deadrise_deg: float, v_entry: float,
                  rho: float = RHO_WATER) -> float:
    """Wagner slamming pressure [Pa]: 0.5 * rho * V_entry^2 * C_p(beta).

    `rho` defaults to `geometry.RHO_WATER` — the ONE water density this project
    owns — rather than to a literal. `docs/LESSONS.md` records a NINTH copy of
    water density that was dividing every C_T the gate printed; this function
    does not add a tenth.

    `v_entry` is the RELATIVE vertical velocity of the section at the moment it
    meets the surface, so it is signed by convention only and enters squared. A
    negative value is therefore accepted and gives the same pressure; a
    non-finite one is not.

    Tier L0. It costs microseconds and it consumes no geometry beyond one
    angle, which is exactly why it is a COMPANION to the CFD instrument and not
    a replacement for it: it knows nothing about the three-dimensionality of a
    real impacting surface, about air entrapment, or about how much of the
    section is already wet when the impact starts.

    IT IS ALSO NOT BOW-SPECIFIC. `beta` is a local deadrise and `v_entry` a
    local relative velocity, so a wet-deck (cross-structure) slam on the
    catamaran this project targets is this same function at a different angle
    and a different velocity — a second call site, never a second
    implementation. See the section header above for what that wiring needs.
    """
    v = float(v_entry)
    r = float(rho)
    if not math.isfinite(v) or not math.isfinite(r):
        raise ValueError(
            f"v_entry and rho must be finite, got {v_entry!r} and {rho!r}")
    if r <= 0.0:
        raise ValueError(f"rho must be positive, got {rho!r}")
    return 0.5 * r * v * v * wagner_impact_cp(deadrise_deg)


def slam_pressure_band(deadrise_a_deg: float, deadrise_b_deg: float,
                       v_entry: float,
                       rho: float = RHO_WATER) -> tuple[float, float]:
    """(low, high) Pa bracketing the Wagner pressure over a REGION.

    THE POINT OF THIS FUNCTION, AND WHY IT IS NOT `slam_pressure` CALLED ONCE.
    A CFD impact instrument reports ONE number — the maximum of p_rgh over a
    patch — and it does not report WHERE on the patch that maximum occurred.
    The deadrise is not constant over a patch of any size, so a single analytic
    value would be a comparison against a section the impact may not have
    happened on.

    What IS true is that the local deadrise lies between the region's two
    extreme values and that `wagner_impact_cp` is strictly decreasing, so the
    analytic pressure over the region lies between the two endpoint
    evaluations. That is a BAND, and a band is the honest companion to a patch
    maximum. Reporting a point value here would be this repo's "single sample
    quoted as a measurement" (docs/LESSONS.md, Physics and compute) with extra
    steps.

    THE ENDPOINTS ARE JUST ANGLES. For the `hull_bow` patch they are the
    grammar's `beta_mid` and `beta_bow`, because `geometry`'s section law warps
    deadrise QUADRATICALLY between them over the forward part of the hull. For
    the wet-deck (cross-structure) case this project still owes, they are the
    two extreme deadrise values across the cross-structure underside. Same
    function, second call site — see the section header above.

    Endpoint ORDER is not assumed: `grammar.check` enforces
    `beta_bow >= beta_mid` (the `deadrise.order` constraint) but this function
    is reachable from a hand-written array, and returning a reversed interval
    for an L0-infeasible hull would be a silent wrong answer, so the band is
    sorted rather than trusted.
    """
    a = slam_pressure(deadrise_a_deg, v_entry, rho)
    b = slam_pressure(deadrise_b_deg, v_entry, rho)
    return (min(a, b), max(a, b))


# ---------------------------------------------------------------------------
# ADDED RESISTANCE IN WAVES (gap F1)
#
# A product validated only in calm water is not validated for a mission. Every
# resistance number this tree produces is a CALM-WATER number, so a boat sized
# on it has no margin for the sea it was specified to work in.
#
# WHAT IS IMPLEMENTED, AND WHAT IS NOT. This is STAwave-1, the ITTC/ISO 15016
# short-wave correlation for the added resistance of a ship in HEAD SEAS:
#
#     R_AWL = (1/16) * rho * g * H_S^2 * B * sqrt(B / L_BWL)
#
# with L_BWL the waterline length of the bow region. It is a CORRELATION, not
# a radiated-energy or far-field drift calculation: it carries no RAO, no
# spectrum and no heading dependence, and it is derived for the regime where
# the ship's own motions are SMALL — short waves relative to the hull, where
# added resistance is dominated by reflection at the bow rather than by
# radiated energy from heave and pitch.
#
# ITS BASIS IS 'approx' IN `rules/review.py`'s SENSE. This project holds no
# citable copy of ISO 15016 or the ITTC procedure, so the coefficient 1/16 and
# the sqrt(B/L_BWL) form are reproduced from the standard's widely-published
# shape and cannot be checked here against the text. That is stated rather
# than implied, and it is why `basis` travels with the number.
#
# THE HONEST LIMIT, AND WHY THERE IS NO HEADING SWEEP DRESSED AS PHYSICS.
# STAwave-1 is a head-sea formula. There is no defensible way to bend it to
# bow, beam or following seas without a method this tree does not hold, so
# `added_resistance_sweep` REFUSES every heading but head seas BY NAME instead
# of returning a number with an invented cosine in it. A refusal that says
# which method is missing is worth more than a curve nobody can defend.
# ---------------------------------------------------------------------------

#: Head seas, in `waves.encounter_omega`'s convention (180 deg = waves on the
#: bow). The one heading STAwave-1 is derived for.
HEAD_SEAS_DEG = 180.0

#: Above this wavelength-to-length ratio the ship's own heave and pitch stop
#: being small and reflection stops dominating, which is the assumption
#: STAwave-1 rests on. Widely quoted for the short-wave regime; 'approx' here
#: for the same reason the coefficient is.
STAWAVE1_MAX_LAMBDA_OVER_LPP = 0.5


def added_resistance_stawave1(hs_m: float, beam_m: float, l_bwl_m: float,
                              rho: float | None = None,
                              g: float | None = None) -> dict:
    """Mean added resistance in HEAD SEAS [N], with its basis and domain.

    Returns a dict rather than a float so the number cannot travel without
    the tier and the assumption it rests on — honesty rule 1.
    """
    # THE FLUID AND GRAVITY COME FROM constants.py, never from a default
    # typed here. The AST single-source fence caught exactly that on the
    # first draft of this function: 1025.0 and 9.80665 as parameter defaults,
    # which is four densities and three viscosities all over again.
    from .constants import G_STANDARD, RHO_SEA_HOLTROP
    rho = RHO_SEA_HOLTROP if rho is None else rho
    g = G_STANDARD if g is None else g
    for name, v in (("hs_m", hs_m), ("beam_m", beam_m), ("l_bwl_m", l_bwl_m),
                    ("rho", rho), ("g", g)):
        if not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0.0):
            raise ValueError(
                f"added_resistance_stawave1: {name} = {v!r} is not a positive "
                f"finite number; an unmeasurable input is refused, never "
                f"defaulted")
    r = (1.0 / 16.0) * rho * g * (hs_m ** 2) * beam_m * math.sqrt(
        beam_m / l_bwl_m)
    return {
        "r_added_n": float(r),
        "heading_deg": HEAD_SEAS_DEG,
        "tier": "EMPIRICAL",
        "basis": (
            "STAwave-1 (ITTC / ISO 15016) short-wave head-sea correlation, "
            "R_AWL = rho*g*H_S^2*B*sqrt(B/L_BWL)/16. A CORRELATION, not a "
            "drift-force calculation: no RAO, no spectrum, no heading term. "
            "Coefficient reproduced from the standard's published form; this "
            "tree holds no citable copy, so the basis is 'approx'."),
        "domain": (
            f"head seas only ({HEAD_SEAS_DEG:g} deg) and the SHORT-WAVE "
            f"regime where the ship's own motions are small "
            f"(lambda/Lpp <~ {STAWAVE1_MAX_LAMBDA_OVER_LPP}). Outside it the "
            f"radiated-energy contribution this formula omits is not small."),
        "inputs": {"hs_m": float(hs_m), "beam_m": float(beam_m),
                   "l_bwl_m": float(l_bwl_m), "rho": float(rho),
                   "g": float(g)},
    }


def added_resistance_sweep(hs_m: float, beam_m: float, l_bwl_m: float,
                           headings_deg=(180.0, 135.0, 90.0, 45.0, 0.0),
                           rho: float | None = None,
                           g: float | None = None) -> dict:
    """Added resistance across a HEADING SWEEP — answered where a method
    exists, REFUSED BY NAME where none does.

    The sweep is the shape a mission needs (a boat does not only meet head
    seas), and the refusals are the honest content of it: this tree holds one
    head-sea correlation and nothing for oblique or following seas. Returning
    a smooth curve here would mean inventing a heading dependence, which is
    the failure this repository has spent its history recording.
    """
    out: dict = {"headings": {}, "answered": 0, "refused": 0}
    for mu in headings_deg:
        key = f"{float(mu):g}"
        if abs(float(mu) - HEAD_SEAS_DEG) < 1e-9:
            out["headings"][key] = added_resistance_stawave1(
                hs_m, beam_m, l_bwl_m, rho, g)
            out["answered"] += 1
        else:
            out["headings"][key] = {
                "r_added_n": None,
                "heading_deg": float(mu),
                "tier": "UNMEASURED",
                "refused": (
                    f"no method in this tree covers {float(mu):g} deg. "
                    f"STAwave-1 is a HEAD-SEA correlation and carries no "
                    f"heading term; bending it with a cosine would be an "
                    f"invented dependence, not a model. What is owed is a "
                    f"drift-force method (Maruo/Salvesen far-field, or "
                    f"Gerritsma-Beukelman radiated energy off the strip "
                    f"damping) — and Tokyo-2015 KCS Case 2.10 data to judge "
                    f"it against, which this tree does not hold either."),
            }
            out["refused"] += 1
    return out
