"""THE HULL EVALUATION CONTRACT — one deterministic path, one receipt.

    GENOME -> VALID HULL -> APPROPRIATE MODEL -> MESH PRESCRIPTION
           -> SOLVER PRESCRIPTION -> the evidence a result must carry

WHY THIS MODULE EXISTS, and why it is thin on purpose. Every stage of that
path was already built and correct in isolation — grammar admits a genome,
the kernel refuses an unbuildable section, `certify` gives a verdict,
`flow_regime` bands the model, `select_fidelity` routes the tier,
`admissibility.screen` predicts meshability, `fidelity.estimate` prices a
case, `post.settled_drag`/`physics_sanity` judge a result. What did not
exist was anything that COMPOSED them, so every caller re-derived Fn, Re,
water properties, the regime and the model's validity for itself, and
"what does the computer do next" had no single answer.

**This module adds no physics.** It calls what exists, in one order, and
returns one receipt. The single new derivation is `mesh_prescription`,
which INVERTS floors this repository already owns (the wave-resolution
density, the y+-derived first-layer height) into the numbers a case writer
consumes — the difference between "will this generic mesh happen to work?"
and "what mesh does this hull require?".

FOUR QUESTIONS, FOUR VERDICTS, NEVER ONE FLAG. The operator's rule, and it
is load-bearing rather than stylistic — the four fail for different reasons,
are fixed by different people, and collapsing them is how "invalid" stops
telling anyone what to do:

    A  hull_verdict      is the HULL physically valid?     (geometry, rules)
    B  model_verdict     is the MODEL valid here?          (Fn/Re envelope)
    C  mesh_verdict      is the GEOMETRY meshable?         (screen + scale)
    D  result_verdict    is the RESULT trustworthy?        (settled + sanity)

D is UNMEASURED until a solve exists; it is never assumed, and `status`
says so rather than reporting a hull as finished.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np

from . import grammar
from .certify import certify
from .geometry import GeometryError, Hull
from .limits import RE_TRANSITION_BAND
from .mission import MissionSpec
from .select_fidelity import (TIER_ANALYTICAL, TIER_EMPIRICAL, TIER_FULL_CFD,
                              TIER_LOW_FIDELITY_CFD, TIER_REFUSE,
                              select_fidelity)

#: Verdict vocabulary. UNMEASURED is not a hedge — it is the honest answer
#: for a question nothing has asked yet (there is no solve, so D has no
#: evidence), and it must never read as a pass.
OK = "OK"
MARGINAL = "MARGINAL"
REFUSED = "REFUSED"
UNMEASURED = "UNMEASURED"


@dataclass(frozen=True)
class MeshPrescription:
    """What mesh THIS hull requires — derived, with every number's source.

    Every field is either inverted from a floor this repository measured or
    marked as not derivable; nothing here is a default that happens to have
    worked on the reference hull.
    """

    mesh_density: float | None            # cells per Lwl (the scale knob)
    cells_per_wavelength: float | None    # what that density buys at this Fn
    first_layer_m: float | None           # from the y+ target and ITTC-57 u_tau
    target_yplus: float | None
    basis: dict = field(default_factory=dict)
    refusals: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"mesh_density": self.mesh_density,
                "cells_per_wavelength": self.cells_per_wavelength,
                "first_layer_m": self.first_layer_m,
                "target_yplus": self.target_yplus,
                "basis": dict(self.basis),
                "refusals": list(self.refusals)}


@dataclass(frozen=True)
class HullEvaluation:
    """The receipt (§12). ONE machine-readable answer per design.

    Consumed by the optimiser, the surrogate, the gates, the CFD lane and
    any audit — so that none of them re-derives a regime or a validity band
    for itself.
    """

    genome_sha256: str
    lwl_m: float | None
    speed_ms: float | None
    fn: float | None
    re: float | None

    hull_verdict: str                     # A
    model_verdict: str                    # B
    mesh_verdict: str                     # C
    result_verdict: str                   # D

    fidelity_tier: str
    fidelity_why: str
    resistance_n: float | None
    sigma_n: float | None
    tier_of_resistance: str | None

    mesh: MeshPrescription
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    detail: dict = field(default_factory=dict)

    @property
    def status(self) -> str:
        """The one-line answer — and it REFUSES to be optimistic.

        REFUSED if any measured verdict refused; UNMEASURED while D has no
        evidence (the normal state of a design that has never been solved);
        MARGINAL if anything is marginal; OK only when every question that
        has an answer answers well.
        """
        vs = (self.hull_verdict, self.model_verdict, self.mesh_verdict,
              self.result_verdict)
        if REFUSED in vs:
            return REFUSED
        if MARGINAL in vs:
            return MARGINAL
        if UNMEASURED in vs:
            return UNMEASURED
        return OK

    def to_dict(self) -> dict:
        return {
            "genome_sha256": self.genome_sha256,
            "lwl_m": self.lwl_m, "speed_ms": self.speed_ms,
            "fn": self.fn, "re": self.re,
            "hull_verdict": self.hull_verdict,
            "model_verdict": self.model_verdict,
            "mesh_verdict": self.mesh_verdict,
            "result_verdict": self.result_verdict,
            "fidelity_tier": self.fidelity_tier,
            "fidelity_why": self.fidelity_why,
            "resistance_n": self.resistance_n, "sigma_n": self.sigma_n,
            "tier_of_resistance": self.tier_of_resistance,
            "mesh": self.mesh.to_dict(),
            "reasons": list(self.reasons), "warnings": list(self.warnings),
            "status": self.status,
            "detail": self.detail,
        }


def genome_sha256(params) -> str:
    """A stable identity for the genome, so a receipt names its own hull.

    Float64 bytes in declared gene order — the same discipline the campaign
    rows use with `stl_sha256`: an artefact without identity is unverifiable
    the moment the geometry moves.
    """
    x = np.asarray(params, dtype=float).ravel()
    return hashlib.sha256(x.tobytes()).hexdigest()


def mesh_prescription(lwl_m: float | None, speed_ms: float | None,
                      fn: float | None, target_yplus: float = 100.0,
                      ) -> MeshPrescription:
    """What mesh this hull requires, INVERTED from floors already measured.

    Two derivations, both from constants this repository owns:

    * `fidelity.density_for_wave_resolution(fn)` inverts the
      MIN_CELLS_PER_WAVELENGTH floor (20) into the cells-per-Lwl the free
      surface needs AT THIS FROUDE NUMBER. The floor existed and was
      consulted by the planner alone — a case could be, and was, written at
      12.7 cells per wavelength with nothing to say so.
    * `cfd.case.first_layer_thickness` inverts the y+ target through
      ITTC-57's friction velocity. That one was already physics; what it
      lacked was a caller that asks for it per design instead of per
      configuration.

    A missing input yields a NAMED refusal, never a default: a prescription
    that quietly falls back to the reference hull's numbers is the failure
    this function exists to end.
    """
    refusals: list[str] = []
    basis: dict = {}
    if lwl_m is None or speed_ms is None or fn is None:
        return MeshPrescription(
            None, None, None, None, basis,
            ("cannot prescribe a mesh without lwl, speed and Fn — an "
             "unmeasurable case gets no numbers, not default ones",))

    density = cpw = first_layer = None
    try:
        from .fidelity import (MIN_CELLS_PER_WAVELENGTH, cells_per_wavelength,
                               density_for_wave_resolution)
        density = float(density_for_wave_resolution(fn))
        cpw = float(cells_per_wavelength(fn, density))
        basis["mesh_density"] = (
            f"inverted from MIN_CELLS_PER_WAVELENGTH="
            f"{MIN_CELLS_PER_WAVELENGTH:g} at Fn {fn:.3f} "
            f"(fidelity.density_for_wave_resolution)")
    except Exception as e:                                  # noqa: BLE001
        refusals.append(f"wave-resolution density unavailable: {e}")

    try:
        from .cfd.case import first_layer_thickness
        first_layer = float(first_layer_thickness(speed_ms, lwl_m,
                                                  target_yplus))
        basis["first_layer_m"] = (
            f"y+ {target_yplus:g} through ITTC-57 friction velocity at "
            f"Re {speed_ms * lwl_m / 1.09e-6:.3g} "
            f"(cfd.case.first_layer_thickness)")
    except Exception as e:                                  # noqa: BLE001
        refusals.append(f"first-layer height unavailable: {e}")

    return MeshPrescription(density, cpw, first_layer, target_yplus, basis,
                            tuple(refusals))


def evaluate_hull(genome, mission: MissionSpec | None = None,
                  environment: dict | None = None) -> HullEvaluation:
    """The contract. One genome in, one receipt out, no hidden assumptions.

    Order is the path itself, and each stage's refusal STOPS the ones that
    depend on it while leaving the independent ones measured — a hull that
    fails the rules tier still gets its regime named, because that is what
    tells the operator whether the design is wrong or merely out of scope.
    """
    x = np.asarray(genome, dtype=float)
    sha = genome_sha256(x)
    mission = mission or MissionSpec()
    env = dict(environment or {})
    reasons: list[str] = []
    warnings: list[str] = []
    detail: dict = {}

    # ---- A: is the hull physically valid? --------------------------------
    g = grammar.check(x)
    detail["grammar_ok"] = bool(g.ok)
    if not g.ok:
        detail["grammar_violations"] = list(getattr(g, "violations", ()))
        reasons.extend(str(v) for v in getattr(g, "violations", ()))
        return HullEvaluation(
            sha, None, None, None, None,
            REFUSED, UNMEASURED, UNMEASURED, UNMEASURED,
            TIER_REFUSE, "grammar refused the genome before any physics",
            None, None, None, mesh_prescription(None, None, None),
            tuple(reasons), tuple(warnings), detail)

    try:
        cert = certify(x, mission, with_gz=False)
    except GeometryError as e:
        # The kernel refuses rather than clamps, and that refusal is a HULL
        # verdict — not a crash for a caller to interpret.
        reasons.append(f"geometry: {e}")
        return HullEvaluation(
            sha, None, None, None, None,
            REFUSED, UNMEASURED, UNMEASURED, UNMEASURED,
            TIER_REFUSE, "the section solve refused this genome",
            None, None, None, mesh_prescription(None, None, None),
            tuple(reasons), tuple(warnings), detail)

    hull_verdict = {"ACCEPT": OK, "MARGINAL": MARGINAL,
                    "REFUSE": REFUSED}.get(cert.verdict, REFUSED)
    reasons.extend(cert.reasons)
    detail["certification"] = cert.verdict

    # ---- B: is the MODEL valid here? -------------------------------------
    fid = cert.fidelity if getattr(cert, "fidelity", None) else {}
    lwl = fid.get("lwl_m")
    speed = fid.get("speed_ms")
    fn = fid.get("fn")
    re = fid.get("re")
    tier = fid.get("tier", TIER_REFUSE)
    why = fid.get("why", "no fidelity decision was recorded")
    if not fid:
        # certify predates the governor, or refused before reaching it: ask
        # the governor directly rather than inventing a tier.
        d = select_fidelity(lwl_m=lwl, speed_ms=speed, mission=mission, **env)
        tier, why, fn, re = d.tier, d.why, d.fn, d.re
        detail["fidelity"] = d.to_dict()
    else:
        detail["fidelity"] = fid
    warnings.extend(fid.get("warnings", ()) or ())

    if tier == TIER_REFUSE:
        model_verdict = REFUSED
    elif tier in (TIER_LOW_FIDELITY_CFD, TIER_FULL_CFD):
        # The cheap tiers cannot answer here — valid, but only CFD may speak.
        model_verdict = MARGINAL
    elif tier in (TIER_ANALYTICAL, TIER_EMPIRICAL):
        model_verdict = OK
    else:
        model_verdict = UNMEASURED

    q = (cert.quantities or {}).get("resistance_total")
    resistance_n = getattr(q, "value", None)
    sigma_n = getattr(q, "sigma", None)
    tier_of_resistance = getattr(q, "tier", None)

    # ---- C: is the geometry meshable, and what mesh does it need? --------
    mesh_verdict = UNMEASURED
    try:
        from .admissibility import Verdict, screen
        rep = screen(Hull(x), speed or 2.57, 1.0)
        detail["screen"] = {"verdict": str(rep.verdict),
                            "no_rescue": list(rep.refused_no_rescue)}
        if rep.refused_no_rescue:
            mesh_verdict = REFUSED
            reasons.extend(f"mesh: {r}" for r in rep.refused_no_rescue)
        elif rep.verdict is Verdict.DANGEROUS:
            mesh_verdict = MARGINAL
        else:
            mesh_verdict = OK
    except Exception as e:                                  # noqa: BLE001
        # An unscreenable hull is UNMEASURED, never OK — this repository's
        # defect class 1 is exactly the opposite reading.
        warnings.append(f"meshability could not be screened: {e}")

    presc = mesh_prescription(lwl, speed, fn)

    # ---- D: is the RESULT trustworthy? -----------------------------------
    # Nothing has solved this hull, so there is no result to judge. That is
    # UNMEASURED and it is why `status` cannot read OK for a design that has
    # never been through CFD.
    result_verdict = UNMEASURED

    return HullEvaluation(
        sha, lwl, speed, fn, re,
        hull_verdict, model_verdict, mesh_verdict, result_verdict,
        tier, why, resistance_n, sigma_n, tier_of_resistance,
        presc, tuple(reasons), tuple(warnings), detail)
