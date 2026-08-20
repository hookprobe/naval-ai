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
import math
from dataclasses import dataclass, field

import numpy as np

from . import grammar
from .certify import certify
from .geometry import GeometryError, Hull
from .limits import RE_TRANSITION_BAND
from .mission import MissionSpec
from .select_fidelity import FN_PLANING_ONSET as FN_PLANING_ONSET_LOCAL
from .select_fidelity import (TIER_ANALYTICAL, TIER_EMPIRICAL, TIER_FULL_CFD,
                              TIER_LOW_FIDELITY_CFD, TIER_REFUSE,
                              select_fidelity)

# --------------------------------------------------------------------------
# The regime taxonomy (the operator's SS8). The NAMES do not matter; what
# matters is that one function owns the boundaries, so no downstream module
# re-derives "is this a small boat" from a length it happened to have.
# Every boundary here is IMPORTED or cited, never re-declared.
# --------------------------------------------------------------------------

REGIME_ENVIRONMENT = "ENVIRONMENT_DOMINATED"   # A: calm-water refinement moot
REGIME_TRANSITIONAL = "LOW_RE_TRANSITIONAL"    # B: ITTC-57 out of its regime
REGIME_DISPLACEMENT = "DISPLACEMENT"           # C: the product's home turf
REGIME_WAVEMAKING = "WAVE_MAKING"              # D: form matters most
REGIME_HIGH_FN = "HIGH_FN_NON_DISPLACEMENT"    # E: no valid cheap tier
REGIME_MULTIHULL = "MULTIHULL_INTERFERENCE"    # M: modifies C/D, not replaces

#: Fn at which wave-making stops being a rounding error. MEASURED across the
#: size range in docs/research/SMALL-CRAFT-REGIMES.md SS5: the wave share of
#: total resistance is <= 5-8% at Fn 0.20 for every hull from 0.5 to 12 m,
#: and reaches 28-46% by Fn 0.35. Below it, hull FORM is not the lever.
FN_WAVEMAKING = 0.30


def classify_regime(lwl_m, speed_ms, fn, re, n_hulls: int = 1,
                    environment_dominated: bool = False) -> tuple[str, ...]:
    """Which physical regimes this design is in. A TUPLE, because they are
    not exclusive: a catamaran at Fn 0.4 is wave-making AND multihull, and
    collapsing that to one label is how a monohull resistance model ends up
    silently answering a multihull question (the operator's SS8 example).

    Ordered most-constraining first, so `regime[0]` is the one that decides
    which models may speak.
    """
    out: list[str] = []
    if environment_dominated:
        out.append(REGIME_ENVIRONMENT)
    if re is not None and re < RE_TRANSITION_BAND[1]:
        # Below the fully-turbulent floor the friction line this tree is
        # built on is an extrapolation, whatever the length happens to be.
        out.append(REGIME_TRANSITIONAL)
    if fn is not None:
        if fn > FN_PLANING_ONSET_LOCAL:
            out.append(REGIME_HIGH_FN)
        elif fn >= FN_WAVEMAKING:
            out.append(REGIME_WAVEMAKING)
        else:
            out.append(REGIME_DISPLACEMENT)
    if n_hulls and n_hulls > 1:
        out.append(REGIME_MULTIHULL)
    return tuple(out) or (UNMEASURED,)


# --------------------------------------------------------------------------
# THE SUPPORTED DOMAIN (the operator's §14), enforced in ONE place
#
# "Do not claim Naval-AI solves every boat. Define the SUPPORTED DOMAIN, then
# make the code refuse designs outside it. This is much better than
# pretending universal coverage."
#
# It was declared in docs/audit/INTEGRATION-GAP-MATRIX.md §II.2 and enforced
# PIECEMEAL — the grammar box clipped length, `select_fidelity` gated Fn and
# Re, `mission.EVALUABLE_TOPOLOGIES` refused a trimaran by name — with no
# single place that could answer "is this design even in scope?". That is the
# same shape as every other defect this campaign found: a bar that exists and
# nothing consults as a whole.
#
# IN-DOMAIN IS NOT A VERDICT ON THE BOAT. It is the question that PRECEDES
# the four: a design outside the domain is not bad, it is unaddressed, and
# the honest answer is to say so by name rather than to run it through
# machinery calibrated for something else and report the number.
# --------------------------------------------------------------------------


def supported_domain(lwl_m=None, fn=None, re=None, n_hulls: int = 1,
                     topology=None) -> tuple[bool, tuple[str, ...]]:
    """(in_domain, reasons). Every bound is IMPORTED from its owner.

    Length is the RCD scope (`limits.RCD_HULL_LENGTH_SCOPE_M`), which is
    also where the rules tier stops having anything to say — below it there
    is additionally no honest friction line (the small-craft study's three
    walls). Froude stops at the planing onset, where this tree holds no
    model at all. Reynolds refuses below the laminar floor. Topology is
    `mission.EVALUABLE_TOPOLOGIES`: a trimaran is declarable and not
    evaluable, and saying that plainly is the point.
    """
    from .limits import RCD_HULL_LENGTH_SCOPE_M
    from .mission import EVALUABLE_TOPOLOGIES

    out: list[str] = []
    lo, hi = RCD_HULL_LENGTH_SCOPE_M
    if lwl_m is not None:
        if lwl_m < lo:
            out.append(
                f"LWL {lwl_m:.2f} m is below the supported {lo:.1f} m: the "
                f"rules tier has no clauses there AND no honest friction "
                f"line exists (the turbulent-Re + displacement-Fn window is "
                f"empty below ~2.6 m). This is the drone line, and it is "
                f"descoped, not broken.")
        elif lwl_m > hi:
            out.append(f"LWL {lwl_m:.2f} m is above the supported {hi:.1f} m "
                       f"(RCD scope)")
    if fn is not None and fn > FN_PLANING_ONSET_LOCAL:
        out.append(
            f"Fn {fn:.3f} is past the planing onset "
            f"{FN_PLANING_ONSET_LOCAL:.2f}: no Savitsky-class model exists "
            f"in this tree, so there is nothing here that may answer")
    if re is not None and re < RE_TRANSITION_BAND[0]:
        out.append(
            f"Re {re:.3g} is below {RE_TRANSITION_BAND[0]:.0e}: the flow is "
            f"laminar and every friction model here is a turbulent "
            f"correlation")
    if topology is not None and topology not in EVALUABLE_TOPOLOGIES:
        out.append(f"topology {getattr(topology, 'value', topology)!r} is "
                   f"declarable but not evaluable: only "
                   f"{[t.value for t in EVALUABLE_TOPOLOGIES]} are built")
    return (not out), tuple(out)


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
    background_cell_m: float | None = None    # the volume cell
    surface_cell_m: float | None = None       # after hull refinement
    free_surface_cell_m: float | None = None  # after free-surface refinement
    hull_refine_levels: tuple[int, int] | None = None
    n_layers: int | None = None               # the prism stack, DERIVED
    n_layers_cap: int | None = None           # what the writer would request
    expected_tau_s: float | None = None       # geometric flow time scale
    timestep_s: float | None = None
    cells: int | None = None
    wall_s: float | None = None
    ram_gb: float | None = None
    basis: dict = field(default_factory=dict)
    refusals: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"mesh_density": self.mesh_density,
                "cells_per_wavelength": self.cells_per_wavelength,
                "first_layer_m": self.first_layer_m,
                "target_yplus": self.target_yplus,
                "background_cell_m": self.background_cell_m,
                "surface_cell_m": self.surface_cell_m,
                "free_surface_cell_m": self.free_surface_cell_m,
                "hull_refine_levels": (list(self.hull_refine_levels)
                                       if self.hull_refine_levels else None),
                "n_layers": self.n_layers, "n_layers_cap": self.n_layers_cap,
                "expected_tau_s": self.expected_tau_s,
                "timestep_s": self.timestep_s,
                "cells": self.cells, "wall_s": self.wall_s,
                "ram_gb": self.ram_gb,
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
    # SS12's identity block: the numbers a reader needs to know WHICH boat
    # this receipt describes, not merely that it passed.
    beam_wl_m: float | None = None
    draft_m: float | None = None
    displacement_kg: float | None = None
    cp: float | None = None
    lcb_pct: float | None = None
    n_hulls: int = 1
    regimes: tuple[str, ...] = ()
    #: §14: is this design even in scope? Asked BEFORE the four verdicts,
    #: because out-of-domain is not a judgement on the boat.
    in_domain: bool = True
    domain_reasons: tuple[str, ...] = ()

    hull_verdict: str = UNMEASURED        # A
    model_verdict: str = UNMEASURED       # B
    mesh_verdict: str = UNMEASURED        # C
    result_verdict: str = UNMEASURED      # D

    fidelity_tier: str = TIER_REFUSE
    fidelity_why: str = ""
    resistance_n: float | None = None
    sigma_n: float | None = None
    tier_of_resistance: str | None = None

    mesh: MeshPrescription = field(
        default_factory=lambda: MeshPrescription(None, None, None, None))
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
            "beam_wl_m": self.beam_wl_m, "draft_m": self.draft_m,
            "displacement_kg": self.displacement_kg,
            "cp": self.cp, "lcb_pct": self.lcb_pct,
            "n_hulls": self.n_hulls, "regimes": list(self.regimes),
            "in_domain": self.in_domain,
            "domain_reasons": list(self.domain_reasons),
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
            mesh_density=None, cells_per_wavelength=None, first_layer_m=None,
            target_yplus=None, basis=basis,
            refusals=("cannot prescribe a mesh without lwl, speed and Fn — "
                      "an unmeasurable case gets no numbers, not default "
                      "ones",))

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

    # ---- the cell SIZES, in metres, and the solver numbers they imply ----
    #
    # These are not new physics either: the domain is Lwl-similar and the
    # refinement levels are the case writer's own, so a cell size is the
    # domain length divided by the cells the density buys, halved once per
    # refinement level. Stating them HERE is what turns "will this generic
    # mesh work" into "this hull needs a 52 mm surface cell".
    bg = surf = fs = tau = dt = None
    cells = wall = ram = None
    levels = None
    n_layers = n_cap = None
    try:
        from .cfd.case import (_DOMAIN_LENGTH_L, _FS_BOX, _HULL_REFINE,
                               _NX_BASE)
        levels = tuple(_HULL_REFINE)
        # ROUND UP, NOT TO NEAREST, AND THE MEASUREMENT IS THE MAC'S.
        # `density_for_wave_resolution` inverts the floor EXACTLY, so the
        # ideal density buys precisely MIN_CELLS_PER_WAVELENGTH — and then
        # the writer discretises it into an integer cell count. Rounding to
        # NEAREST lands below the bar whenever the fraction is under a half,
        # which is most of the time: MEASURED on the Fn-matched coverage set
        # (Block 4, 2026-08-20), ALL FOUR size bands wrote at 19.90 cells per
        # wavelength against a bar of 20 — the same 0.5% miss in every band,
        # because they are Fn-matched by construction and therefore share the
        # rounding. A floor that the prescription's own discretisation steps
        # under is not a floor. ceil() costs at most one background cell in x
        # and makes the delivered mesh clear the bar it was derived from.
        nx = max(1, int(math.ceil(_NX_BASE * (density or 1.0) - 1e-9)))
        density = nx / float(_NX_BASE)      # the density actually delivered
        cpw = float(cells_per_wavelength(fn, density))
        bg = float(_DOMAIN_LENGTH_L * lwl_m / nx)
        surf = bg / (2.0 ** levels[1])
        # The free surface is refined to its own level; `_FS_BOX`'s z extent
        # is the slab it applies in. Level 2 is the writer's shipped choice.
        fs = bg / (2.0 ** 2)
        basis["cells_m"] = (
            f"domain {_DOMAIN_LENGTH_L:g}*Lwl / nx {nx} "
            f"(_NX_BASE {_NX_BASE} x density {density:.3f}); "
            f"surface halved {levels[1]}x, free surface 2x "
            f"(cfd.case._HULL_REFINE, _FS_BOX z={_FS_BOX['z']:g})")
        # THE GEOMETRIC FLOW TIME SCALE, which is where this connects to the
        # runner's own live abort. tau = V/(A.U) is h/U for a cube, so the
        # SMALLEST cell sets it — and run-case.sh kills a solve when the
        # printed tau falls below 1e-12 s. Prescribing tau means the case is
        # priced against that bar BEFORE the mesher runs, instead of
        # discovering it 45 minutes in.
        tau = surf / speed_ms
        basis["expected_tau_s"] = (
            "h_min / U for a cubic cell; run-case.sh aborts below 1e-12 s")

        # THE PRISM STACK, AND IT IS NOT A DETAIL — it is the quantity the
        # Mac measured on 2026-08-20 to be the whole mechanism behind Gate
        # 2U's two failures. h011 and h012 mesh at n=6 and FAIL at n=7:
        #   h011  n=7: 13 wrong-oriented, skew 247.2  ->  n=6: 0, skew 3.5
        #   h012  n=7: 12 wrong-oriented, skew   9.9  ->  n=6: 0, skew 4.5
        # while layer COVERAGE barely moved (73.5 -> 73.6% on h011) and
        # skewness fell by a factor of 71. Coverage was never the signal.
        # `n_layers_to_bridge` is what the writer derives; the cap is what it
        # will actually request. Prescribing BOTH means a reader can see the
        # rung the ladder would have to walk before a mesher ever runs.
        if first_layer is not None:
            from .cfd.case import (_LAYER_EXPANSION, _MAX_LAYERS,
                                   n_layers_to_bridge)
            n_bridge = int(n_layers_to_bridge(first_layer, surf,
                                              _LAYER_EXPANSION))
            n_layers = int(min(n_bridge, _MAX_LAYERS))
            n_cap = int(_MAX_LAYERS)
            basis["n_layers"] = (
                f"n_layers_to_bridge(first_layer {first_layer * 1000:.2f} mm, "
                f"surface cell {surf * 1000:.1f} mm, expansion "
                f"{_LAYER_EXPANSION:g}) = {n_bridge}, capped at {n_cap}. "
                f"MEASURED (Mac, 2026-08-20): h011/h012 mesh at n=6 and fail "
                f"at n=7 with 13/12 wrong-oriented faces — the derived count "
                f"IS the mesh-success mechanism on those hulls, and the "
                f"ladder's first backoff rung is what recovers them.")
    except Exception as e:                                  # noqa: BLE001
        refusals.append(f"cell sizes unavailable: {e}")

    try:
        from .fidelity import Budget, Condition, FidelitySpec, estimate
        est = estimate(Condition(lwl=lwl_m, speed=speed_ms),
                       FidelitySpec(mesh_density=density or 1.0))
        cells = int(est.cells)
        dt = float(est.dt_s)
        wall = float(est.wall_s)
        ram = float(est.ram_gb)
        basis["cost"] = est.basis if isinstance(est.basis, str) else "fidelity.estimate"
    except Exception as e:                                  # noqa: BLE001
        refusals.append(f"cost estimate unavailable: {e}")

    return MeshPrescription(
        mesh_density=density, cells_per_wavelength=cpw,
        first_layer_m=first_layer, target_yplus=target_yplus,
        background_cell_m=bg, surface_cell_m=surf, free_surface_cell_m=fs,
        hull_refine_levels=levels, n_layers=n_layers, n_layers_cap=n_cap,
        expected_tau_s=tau, timestep_s=dt,
        cells=cells, wall_s=wall, ram_gb=ram,
        basis=basis, refusals=tuple(refusals))


def judge_result(case_dir) -> tuple[str, tuple[str, ...], dict]:
    """QUESTION D: is the RESULT converged and physically trustworthy?

    (verdict, reasons, detail). Composition again — every judgement here
    already exists and is simply never asked in one place:

      settled_drag    stationarity, per component, with the LTS pseudo-time
                      and mixed-history seams
      physics_sanity  sign, finiteness, and magnitude against a prior
      yPlus receipt   whether the wall model the case ASSUMED was achieved

    The y+ half is the one that cannot be answered from fortress: the
    receipt is written by the solver node, and until it is there this
    returns UNMEASURED for that clause rather than assuming the wall model
    held. A verdict that silently drops the clause it cannot check is the
    defect this whole layer exists to refuse.
    """
    from pathlib import Path

    from .cfd.post import ForceHistoryError, physics_sanity, settled_drag

    case = Path(case_dir)
    detail: dict = {"case": str(case)}
    reasons: list[str] = []
    if not case.exists():
        return UNMEASURED, (f"{case} does not exist",), detail

    try:
        sd = settled_drag(case)
    except ForceHistoryError as e:
        return REFUSED, (f"no readable force history: {e}",), detail
    except Exception as e:                                  # noqa: BLE001
        return UNMEASURED, (f"settledness could not be judged: {e}",), detail

    detail["settled"] = {"outcome": sd["outcome"], "drift": sd["drift"],
                         "flow_throughs": sd["flow_throughs"]}
    if not sd["settled"]:
        reasons.append(f"{sd['outcome']}: " + "; ".join(sd["reasons"]))

    sane = physics_sanity(float(sd["drag_n"]))
    detail["physics_sanity"] = sane
    reasons.extend(sane["reasons"])

    # THE WALL MODEL'S OWN VALIDITY. The case DESIGNED for a y+ target;
    # whether it achieved one is a separate measurement, and the receipt
    # comes from the solver node. Absent, the clause is UNMEASURED — never
    # assumed to have held.
    info = case / "case.info"
    yplus = None
    if info.exists():
        for line in info.read_text().splitlines():
            if line.startswith("yplus_achieved="):
                try:
                    yplus = float(line.split("=", 1)[1])
                except ValueError:
                    yplus = None
    detail["yplus_achieved"] = yplus
    if yplus is None:
        detail["yplus_note"] = ("no achieved-y+ receipt: the wall model's "
                                "validity is UNMEASURED, not assumed")
    elif not (30.0 <= yplus <= 300.0):
        reasons.append(
            f"achieved y+ {yplus:.1f} is outside the log-law band [30, 300] "
            f"the case's wall functions require, so the near-wall model the "
            f"drag was read through does not apply")

    if reasons:
        return REFUSED, tuple(reasons), detail
    if yplus is None:
        return MARGINAL, ("settled and physically sane, but the wall model's "
                          "validity is unverified (no achieved-y+ receipt)",), \
            detail
    return OK, (), detail


def evaluate_hull(genome, mission: MissionSpec | None = None,
                  environment: dict | None = None,
                  case_dir=None) -> HullEvaluation:
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
            genome_sha256=sha, lwl_m=None, speed_ms=None, fn=None, re=None,
            hull_verdict=REFUSED,
            fidelity_why="grammar refused the genome before any physics",
            mesh=mesh_prescription(None, None, None),
            reasons=tuple(reasons), warnings=tuple(warnings), detail=detail)

    try:
        cert = certify(x, mission, with_gz=False)
    except GeometryError as e:
        # The kernel refuses rather than clamps, and that refusal is a HULL
        # verdict — not a crash for a caller to interpret.
        reasons.append(f"geometry: {e}")
        return HullEvaluation(
            genome_sha256=sha, lwl_m=None, speed_ms=None, fn=None, re=None,
            hull_verdict=REFUSED,
            fidelity_why="the section solve refused this genome",
            mesh=mesh_prescription(None, None, None),
            reasons=tuple(reasons), warnings=tuple(warnings), detail=detail)

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
    # With no case directory nothing has solved this hull, so there is no
    # result to judge: UNMEASURED, which is why `status` cannot read OK for
    # a design that has never been through CFD. Given one, the same three
    # judgements the CFD lane already owns are asked here, in one place.
    if case_dir is None:
        result_verdict = UNMEASURED
    else:
        result_verdict, d_reasons, d_detail = judge_result(case_dir)
        detail["result"] = d_detail
        reasons.extend(f"result: {r}" for r in d_reasons)

    # ---- the identity block and the regime -------------------------------
    sc = (cert.descriptors or {}).get("scalars", {}) or {}
    n_hulls = int(getattr(getattr(mission, "vessel", None), "n_hulls", 1) or 1)
    env_dominated = any(
        g.name == "ENVIRONMENT" and g.outcome == "ROUTE"
        for g in getattr(detail.get("_decision"), "gates", ())) if \
        detail.get("_decision") else False
    regimes = classify_regime(lwl, speed, fn, re, n_hulls=n_hulls,
                              environment_dominated=env_dominated)
    topo = getattr(getattr(mission, "vessel", None), "topology", None)
    in_domain, domain_reasons = supported_domain(
        lwl_m=lwl, fn=fn, re=re, n_hulls=n_hulls, topology=topo)
    if not in_domain:
        warnings.extend(f"out of supported domain: {r}" for r in domain_reasons)
    detail.pop("_decision", None)

    return HullEvaluation(
        genome_sha256=sha, lwl_m=lwl, speed_ms=speed, fn=fn, re=re,
        beam_wl_m=sc.get("bwl_m"), draft_m=sc.get("draft_m"),
        displacement_kg=sc.get("displacement_design_kg"),
        cp=sc.get("Cp"), lcb_pct=sc.get("lcb_pct_lwl"),
        n_hulls=n_hulls, regimes=regimes,
        in_domain=in_domain, domain_reasons=domain_reasons,
        hull_verdict=hull_verdict, model_verdict=model_verdict,
        mesh_verdict=mesh_verdict, result_verdict=result_verdict,
        fidelity_tier=tier, fidelity_why=why,
        resistance_n=resistance_n, sigma_n=sigma_n,
        tier_of_resistance=tier_of_resistance,
        mesh=presc, reasons=tuple(reasons), warnings=tuple(warnings),
        detail=detail)
