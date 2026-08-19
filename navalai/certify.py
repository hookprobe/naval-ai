"""The pre-CFD design certification layer (screening directive §1/§4).

ONE question, answered cheaply and with receipts: is this a plausible boat
for this mission, and is it worth spending CFD on? The verdict is a
classification — ACCEPT / MARGINAL / REFUSE — plus a separate CFD-worthiness
score, never a claim of CFD-grade accuracy.

COMPOSITION, NOT A PARALLEL LADDER (§4). `evaluate.Evaluation` remains the
one evaluation object; this module composes it with the descriptor engine
(`formcheck`), the righting-arm solve (`hydrostatics.gz_curve`), the
buildability metrics (`buildability.shell_complexity`), a validity-banded
speed curve, and a loading matrix — every derived figure carried as a
`Quantity` with value/unit/tier/sigma/basis (§25). Where the tree cannot
answer, the certification says UNKNOWN or REFUSED by name; it never
fabricates (a criterion that is not sourced returns REFUSE, not a pass).

NO CFD. Nothing in this module launches or needs a solver; the
`cfd_candidate` block *selects* what would deserve one.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np

from . import formcheck, grammar
from . import __version__ as _NAVALAI_VERSION
from .buildability import BuildabilityError, shell_complexity
from .energy import energy_report
from .evaluate import evaluate
from .geometry import Hull
from .hydrostatics import GZCurve, gz_curve, multihull_gz_assessment
from .mission import Manning, MissionSpec
from .resistance import FN_MICHELL_MAX, total_resistance


@dataclass(frozen=True)
class Quantity:
    """§25: a number is useful only if we know exactly what it means."""

    value: float
    unit: str
    tier: str                    # L0/L1/… or "geometry"
    sigma: float | None          # one-sigma where meaningful, None otherwise
    basis: str                   # formula/model source + validity note


@dataclass(frozen=True)
class SpeedPoint:
    """One point of the resistance/energy curve, with its validity band.

    §15: unsupported values are never connected into a smooth curve and
    called physics — each point carries VALID / TRANSITION / EXTRAPOLATED /
    UNSUPPORTED, and consumers must break the curve at the band edges.
      VALID        both models inside their support
      TRANSITION   a model inside its validity flag but outside the band it
                   was correlated on (e.g. ITTC-57 in the laminar band)
      EXTRAPOLATED the Watanabe form factor came off its clamp — the number
                   is the estimator's ceiling, not its estimate
      UNSUPPORTED  outside model validity (Fn > FN_MICHELL_MAX or Re floor)
    """

    v_ms: float
    fn: float
    re: float
    rf_n: float
    rw_n: float
    rt_n: float
    sigma_rt_n: float
    pe_w: float                  # effective towing power R_t * V
    wh_per_nm: float | None      # None when the energy model refuses
    validity: str
    notes: tuple[str, ...] = ()


# §16: regimes are declared, and a regime is ENABLED only when its
# reduced-order physics exists and is tested in this tree. Everything else
# refuses BY NAME rather than pretending (the directive's rule verbatim).
REGIME_SLENDER_DISPLACEMENT = "SLENDER_DISPLACEMENT"
REGIME_MODERATE_DISPLACEMENT = "MODERATE_DISPLACEMENT"
REGIME_AUTONOMOUS_SLOW_CRUISE = "AUTONOMOUS_SLOW_CRUISE"
REGIME_SEMI_DISPLACEMENT = "SEMI_DISPLACEMENT"
REGIME_PLANING = "PLANING"

_SUPPORTED_REGIMES = {
    REGIME_SLENDER_DISPLACEMENT: "Michell + ITTC-57 (verified in-tree)",
    REGIME_MODERATE_DISPLACEMENT: "Michell + ITTC-57 (verified in-tree)",
    REGIME_AUTONOMOUS_SLOW_CRUISE: "Michell + ITTC-57 (verified in-tree)",
}
# Fn bands: displacement practice below FN_MICHELL_MAX; the 0.65 planing
# onset is the conventional practice figure and is used ONLY to name which
# unsupported regime a mission asked for — it gates nothing else.
_FN_PLANING_ONSET = 0.65


def mission_regime(mission: MissionSpec,
                   lb_ratio: float | None = None) -> tuple[str, bool, str]:
    """(regime, supported, why) for the mission's design Froude number.

    A mission with no length hint has no design Fn; it is routed to the
    displacement regime its cruise speed will be judged against per-hull by
    the resistance validity flags (which remain the enforcement — this
    router only names the regime and refuses the unsupported ones early).
    """
    fn = mission.design_fn()
    uncrewed = mission.vessel.manning is Manning.UNCREWED
    if fn is None:
        reg = (REGIME_AUTONOMOUS_SLOW_CRUISE if uncrewed
               else REGIME_MODERATE_DISPLACEMENT)
        return reg, True, ("no length hint -> no design Fn; per-hull "
                           "validity flags govern")
    if fn > _FN_PLANING_ONSET:
        return REGIME_PLANING, False, (
            f"design Fn {fn:.2f} > {_FN_PLANING_ONSET} — NO planing model "
            f"exists in this tree; not yet supported")
    if fn > FN_MICHELL_MAX:
        return REGIME_SEMI_DISPLACEMENT, False, (
            f"design Fn {fn:.2f} > {FN_MICHELL_MAX} (Michell validity) — "
            f"NO semi-displacement model exists in this tree; not yet "
            f"supported")
    if uncrewed:
        return REGIME_AUTONOMOUS_SLOW_CRUISE, True, (
            f"uncrewed, design Fn {fn:.2f} inside displacement validity")
    slender = (lb_ratio is not None and lb_ratio >= 6.0)
    reg = (REGIME_SLENDER_DISPLACEMENT if slender
           else REGIME_MODERATE_DISPLACEMENT)
    return reg, True, f"design Fn {fn:.2f} inside displacement validity"


def speed_curve(params, mission: MissionSpec, ev, n: int = 12,
                v_max_over_cruise: float = 1.5) -> tuple[SpeedPoint, ...]:
    """Resistance/energy vs speed at the mission's floated state.

    DECLARED ASSUMPTION: the flotation is HELD at the mission equilibrium
    (wetted, cb, beam, draft from `ev.hydro`); no squat/sinkage with speed.
    That is the standard displacement-regime approximation and it is said
    here rather than hidden. Each point re-runs `total_resistance`, whose
    own validity flags band the point.
    """
    hull = Hull(np.asarray(params))
    hs = ev.hydro
    u_cruise = mission.cruise_speed_ms()
    sep = (ev.vessel.get("separation_m") if ev.vessel.get("n_hulls", 1) > 1
           else None)
    out = []
    for u in np.linspace(max(0.3 * u_cruise, 0.2), v_max_over_cruise
                         * u_cruise, n):
        res = total_resistance(hull, float(u), hs.wetted, hs.cb, wl=ev.wl,
                               beam_wl=hs.b_wl_max, draft=hs.draft,
                               separation=sep, lwl_eff=hs.lwl_eff)
        notes = tuple(res.flow.envelope) if res.flow is not None else ()
        if not res.valid:
            band = "UNSUPPORTED"
        elif res.form is not None and res.form.k != res.form.k_raw:
            band = "EXTRAPOLATED"
        elif notes:
            band = "TRANSITION"
        else:
            band = "VALID"
        # §14: the clamp stays VISIBLE AS UNCERTAINTY, not as a hidden
        # number — an EXTRAPOLATED point still carries its Wh/NM, because
        # the resistance sigma already widened when the estimator hit its
        # ceiling and the energy report propagates it. Only UNSUPPORTED
        # points refuse the energy figure outright.
        wh = None
        if band != "UNSUPPORTED":
            en = energy_report(res.total, float(u), hull.deck_area(),
                               mission.energy,
                               resistance_sigma_n=res.uncertainty)
            wh = float(en.wh_per_nm)
        out.append(SpeedPoint(
            v_ms=float(u), fn=float(res.fn),
            re=float(res.flow.re) if res.flow is not None else float("nan"),
            rf_n=float(res.rf), rw_n=float(res.rw), rt_n=float(res.total),
            sigma_rt_n=float(res.uncertainty),
            pe_w=float(res.total * u), wh_per_nm=wh,
            validity=band, notes=notes))
    return tuple(out)


def loading_matrix(params, mission: MissionSpec) -> dict[str, dict]:
    """§11: the same hull under its declared load states, each fully floated.

    States are built from quantities the mission DECLARES — nothing is
    invented. LIGHTSHIP zeroes the crew/stores provision and the mission
    payload; DESIGN is the mission as given; PEOPLE_FORWARD/PEOPLE_AFT
    (crewed only) move the provision to the 0.75/0.25 LWL stations;
    EMPTY_PAYLOAD (declared payload only) removes it. A MAXIMUM state needs
    a declared maximum the spec does not carry — reported UNKNOWN rather
    than fabricated.
    """
    from dataclasses import replace

    out: dict[str, dict] = {}

    def _state(name: str, m: MissionSpec) -> None:
        ev = evaluate(np.asarray(params), m)
        if ev.hydro is None:
            out[name] = {"refused": "; ".join(ev.violations[:2])}
            return
        out[name] = {
            "displacement_kg": float(ev.hydro.disp_kg),
            "draft_m": float(ev.hydro.draft),
            "trim_deg": None if ev.trim_deg is None else float(ev.trim_deg),
            "lcg_m": float(ev.masses.lcg_m),
            "tcg_m": float(ev.masses.tcg_m),
            "gm_m": None if ev.gm_m is None else float(ev.gm_m),
            "freeboard_m": float(ev.hydro.freeboard_min),
            "ok": bool(ev.ok),
        }

    _state("DESIGN", mission)
    light = replace(
        mission,
        energy=replace(mission.energy, payload_kg=0.0),
        payload=replace(mission.payload, mass_kg=0.0),
        notes="")
    _state("LIGHTSHIP", light)
    if mission.vessel.manning is not Manning.UNCREWED \
            and mission.energy.payload_kg > 0.0:
        # the provision moved bodily to the forward/aft quarter stations —
        # representable through PayloadSpec's declared-position mechanism
        for name, xf in (("PEOPLE_FORWARD", 0.75), ("PEOPLE_AFT", 0.25)):
            shifted = replace(
                mission,
                energy=replace(mission.energy, payload_kg=0.0),
                payload=replace(mission.payload,
                                mass_kg=mission.payload.mass_kg
                                + mission.energy.payload_kg,
                                x_frac_lwl=xf, z_frac_depth=0.55),
                notes="")
            _state(name, shifted)
    if mission.payload.mass_kg > 0.0:
        empty = replace(mission,
                        payload=replace(mission.payload, mass_kg=0.0),
                        notes="")
        _state("EMPTY_PAYLOAD", empty)
    out["MAXIMUM"] = {"unknown": "no declared maximum load in the mission "
                                 "spec — not fabricated"}
    return out


@dataclass(frozen=True)
class DesignCertification:
    """§4: the single machine-readable pre-CFD result."""

    verdict: str                             # ACCEPT | MARGINAL | REFUSE
    # C-22: the certification names the exact hull and code that produced
    # it (the gate2u lesson: an artifact without identity is unverifiable
    # the moment the geometry moves).
    genome_sha256: str
    code_version: str
    reasons: tuple[str, ...]
    regime: str
    regime_supported: bool
    quantities: dict[str, Quantity]
    descriptors: dict                        # formcheck.form_descriptors
    targets: dict                            # Evaluation.targets receipt
    speed_curve: tuple[SpeedPoint, ...]
    loading: dict[str, dict]
    stability: dict
    buildability: dict
    cfd_candidate: dict
    violations: tuple[str, ...]
    assumptions: tuple[str, ...]
    evaluation_ok: bool


# MARGINAL band: a satisfied constraint within this relative margin of its
# bar is a design one loading change or one model-sigma from refusal.
_MARGINAL_G = -0.05


def certify(params, mission: MissionSpec,
            with_gz: bool = True) -> DesignCertification:
    """The screening engine: one design, one mission, one classified answer.

    Cost: a few seconds — evaluate + descriptors + speed sweep + loading
    states + (optionally) the righting-arm solve. No CFD, no BEM.
    """
    x = np.asarray(params, float)
    ev = evaluate(x, mission)
    reasons: list[str] = []
    assumptions: list[str] = []

    lb = None
    if ev.hydro is not None:
        lb = ev.hydro.lwl_eff / max(ev.hydro.b_wl_max, 1e-9)
    regime, supported, why = mission_regime(mission, lb)
    if not supported:
        reasons.append(f"regime {regime}: {why}")

    if ev.hydro is None:
        return DesignCertification(
            verdict="REFUSE",
            genome_sha256=hashlib.sha256(x.tobytes()).hexdigest(),
            code_version=_NAVALAI_VERSION,
            reasons=tuple(reasons) + tuple(ev.violations),
            regime=regime, regime_supported=supported, quantities={},
            descriptors={}, targets=dict(ev.targets), speed_curve=(),
            loading={}, stability={}, buildability={}, cfd_candidate={
                "score": 0.0, "eligible": False,
                "why": "never floated — nothing to simulate"},
            violations=tuple(ev.violations), assumptions=(),
            evaluation_ok=False)

    hull = Hull(x)
    hs = ev.hydro

    # --- §5 geometry intelligence: the descriptor engine + fairness -------
    desc = formcheck.form_descriptors(x, mission)
    fair = float(hull.fairness())
    quantities = {
        "displacement": Quantity(float(hs.disp_kg), "kg", "L1",
                                 None, "hydrostatics.solve_equilibrium"),
        "wetted_area": Quantity(float(hs.wetted), "m^2", "L1", None,
                                "HydroState at the solved attitude"),
        "gm": Quantity(float(ev.gm_m), "m", "L1", None,
                       "upright metacentre minus KG, free-surface corrected"),
        # E11 discipline (forensics C-02): a REFUSED equilibrium is not an
        # even keel. The quantity exists only when the solve produced it.
        **({"trim": Quantity(float(ev.trim_deg), "deg", "L1", None,
                             "solved (wl0, theta) equilibrium")}
           if ev.trim_deg is not None else {}),
        "fairness": Quantity(fair, "1", "geometry",
                             None, "Hull.fairness strain-energy functional "
                             "(§26: wired into certification)"),
        "wh_per_nm": Quantity(float(ev.energy.wh_per_nm), "Wh/NM", "L1",
                              float(ev.energy.sigma_wh_per_nm),
                              f"energy_report ({ev.energy.sigma_basis})"),
        "rt_cruise": Quantity(float(ev.resistance.total), "N", "L1",
                              float(ev.resistance.uncertainty),
                              "Michell + ITTC-57 at the floated state"),
    }

    # --- §15 speed curve + §11 loading matrix -----------------------------
    curve = speed_curve(x, mission, ev)
    assumptions.append("speed curve holds the mission-equilibrium flotation "
                       "(no squat/sinkage with speed)")
    loading = loading_matrix(x, mission)

    # --- stability: GZ where affordable, refusal where the criterion is ---
    stability: dict = {"gm_m": float(ev.gm_m)}
    n_hulls = int(ev.vessel.get("n_hulls", 1))
    if with_gz and ev.trim_deg is None:
        # C-02: the trim equilibrium was REFUSED — computing a righting-arm
        # curve at a fabricated even keel would be stability numbers for an
        # attitude the solver said does not exist.
        stability["refused"] = (
            "no longitudinal equilibrium (see violations) — GZ not computed "
            "at a fabricated attitude")
        with_gz = False
    if with_gz:
        kg = ev.masses.vcg_above_keel(float(grammar.named(x)["T"]))
        if n_hulls > 1:
            _crew = (0 if mission.vessel.manning.value == "uncrewed"
                     else int(mission.crew))
            a = multihull_gz_assessment(hull, float(hs.disp_kg), kg,
                                        vessel=mission.vessel,
                                        trim_deg=float(ev.trim_deg),
                                        windage=mission.windage,
                                        persons=_crew)
            # R2.2 (2026-08-19): the governing clause SPLITS by class. Under
            # 15 m LOA with <= 50 persons, cl 1.3 governs and the ladder
            # COMPUTED it (ev.vessel["cl13"]); the cl 1.4 curve clauses are
            # measured here as supplementary evidence. At or over 15 m (or
            # > 50 passengers) cl 1.4 governs and stays refusal-first until
            # the windage declarables land ((d) is READ as of 2026-08-19;
            # (c) still needs a declared lateral area).
            _cl13 = ev.vessel.get("cl13")
            if _cl13 is not None:
                stability["cl13"] = _cl13
            _v = ("ASSESSED" if _cl13 and _cl13.get("passes")
                  else ("SEE VIOLATIONS" if _cl13 else "REFUSED"))
            stability.update({
                "criterion": (
                    "NZ Part 40A App.1 cl 1.3 (COMPUTED — the governing "
                    "clause for < 15 m, <= 50 persons) + cl 1.4 (a)/(b) "
                    "measured as supplementary evidence" if _cl13 is not None
                    else "NZ Part 40A App.1 cl.1.4 — PARTIAL (a/b measured; "
                         "c needs a declared lateral area; d READ, "
                         "implementable once (c) is declarable)"),
                "verdict": _v,
                "clause_a": {"area_m_rad": a.area_to_theta_m_rad,
                             "required": a.area_required_m_rad,
                             "satisfied": a.clause_a_satisfied},
                "clause_b": {"heel_at_gz_max_deg": a.heel_at_gz_max_deg,
                             "satisfied": a.clause_b_satisfied},
                "clause_c": (None if a.clause_c_satisfied is None else
                             {"wind_lever_m": a.wind_lever_m,
                              "wind_heel_deg": a.wind_heel_deg,
                              "satisfied": a.clause_c_satisfied}),
                "clause_d": (None if a.clause_d_satisfied is None else
                             {"theta_h_deg": a.theta_h_deg,
                              "residual_area_m_rad": a.residual_area_m_rad,
                              "satisfied": a.clause_d_satisfied}),
                "cl14_passes": a.passes,
                "unassessable": a.unassessable,
                "gz_max_m": a.curve.gz_max_m,
                "deck_edge_deg": a.curve.deck_edge_deg,
            })
            assumptions.extend(a.curve.assumptions)
        else:
            crv: GZCurve = gz_curve(hull, float(hs.disp_kg), kg,
                                    trim_deg=float(ev.trim_deg))
            stability.update({
                "criterion": "ISO 12217-1 GM floor (practice bar; R-GM is "
                             "not in the standard) + reported GZ curve",
                "verdict": "ASSESSED" if ev.ok else "SEE VIOLATIONS",
                "gz_max_m": crv.gz_max_m,
                "heel_at_gz_max_deg": crv.heel_at_gz_max_deg,
                "avs_deg": crv.avs_deg,
                "area_to_30_m_rad": crv.area_to_30_m_rad,
                "deck_edge_deg": crv.deck_edge_deg,
            })
            assumptions.extend(crv.assumptions)

    # --- §17 buildability: report, not just a score -----------------------
    try:
        # C-05 (forensics B2): shell_complexity used to run at the DEFAULT
        # 15 mm sheet with its own weight budget — a 29% structure-mass
        # divergence inside one certification on the case-b chine variant.
        # It now consumes the ladder's own derived sheet, so the build
        # report and the ladder plank the same boat.
        sc = shell_complexity(hull, wl=float(ev.wl), spec=mission.energy,
                              panel_thickness_m=float(ev.ply_thickness_m))
        buildability = {
            "shell_area_m2": sc.shell_area_m2,
            "deck_area_m2": sc.deck_area_m2,
            "build_area_m2": sc.build_area_m2,
            "structure_kg": sc.structure_kg,
            "non_developable_frac": sc.non_developable_frac,
            "twist_max_deg": sc.twist_max,
            "gauss_abs_integral": sc.gauss_abs_integral,
            "fairness": fair,
            "note": "PRELIMINARY buildability — not certification-level "
                    "scantlings (§17)",
        }
    except BuildabilityError as e:
        # C-19: the strip analyser is a SHEET-DEVELOPMENT tool; a round
        # bilge (roundness > 0) is outside its scope by construction, which
        # is a MISSING metric, not a defect of the hull — the project's own
        # target class is round-bilge. The refusal is recorded verbatim and
        # must not zero CFD eligibility (see the cfd_candidate block).
        buildability = {"refused": str(e),
                        "note": "developability analysis inapplicable "
                                "(sheet-built tool); NOT a physics verdict"}

    # --- verdict ----------------------------------------------------------
    marginal: list[str] = []
    if not ev.ok:
        reasons.extend(ev.violations)
        verdict = "REFUSE"
    elif not supported:
        verdict = "REFUSE"
    else:
        near = [k for k, v in ev.g.items() if _MARGINAL_G < v <= 0.0]
        if near:
            marginal.append(f"constraint margin thin: {near}")
        if ev.targets.get("cp_conformant") is False:
            marginal.append(
                f"delivered Cp {ev.targets['cp_delivered']:.3f} misses the "
                f"mission target {ev.targets['cp_target']:.3f} beyond "
                f"tolerance")
        cruise_pts = [p for p in curve
                      if abs(p.v_ms - mission.cruise_speed_ms()) < 1e-6]
        at_cruise = cruise_pts[0] if cruise_pts else None
        cruise_band = (at_cruise.validity if at_cruise is not None else
                       ("VALID" if ev.resistance.valid else "UNSUPPORTED"))
        if cruise_band in ("TRANSITION", "EXTRAPOLATED"):
            marginal.append(f"resistance at cruise is {cruise_band}")
        rel_sigma = (ev.resistance.uncertainty
                     / max(ev.resistance.total, 1e-9))
        if rel_sigma > 0.35:
            marginal.append(f"resistance sigma {rel_sigma:.0%} — the model "
                            f"partly disowns this hull")
        verdict = "MARGINAL" if marginal else "ACCEPT"
        reasons.extend(marginal)

    # --- §24 CFD-worthiness (single-design factors; population factors —
    # Pareto rank, novelty — belong to the dataset layer and say so) -------
    # C-19 (forensics B13): buildability's REFUSAL (a sheet-development
    # analyser refusing a round bilge) is a missing metric, never an
    # eligibility veto — the old conjunct made the project's own
    # round-bilge target class structurally CFD-ineligible. Eligibility is
    # physics + validity; when the buildable metric is missing, the score
    # is the mean of the parts that exist and the omission is named.
    eligible = (ev.ok and supported
                and all(p.validity != "UNSUPPORTED" for p in curve[:1]))
    score = 0.0
    parts: dict[str, float] = {}
    if eligible:
        parts["validity"] = 1.0 if ev.resistance.valid else 0.0
        parts["certainty"] = max(0.0, 1.0 - rel_sigma)
        parts["mission"] = 1.0 if ev.targets.get("cp_conformant") else 0.5
        if "refused" not in buildability:
            parts["buildable"] = max(
                0.0, 1.0 - 2.0 * buildability.get("non_developable_frac",
                                                  0.5))
        score = sum(parts.values()) / len(parts)
    cfd_candidate = {
        "score": round(score, 3), "eligible": eligible, "parts": parts,
        "note": ("buildable part omitted: developability analyser "
                 "inapplicable to this hull; " if "refused" in
                 buildability else "")
                + "single-design factors only; Pareto/novelty rank requires "
                "the population layer (dataset generator)",
    }

    return DesignCertification(
        verdict=verdict,
        genome_sha256=hashlib.sha256(x.tobytes()).hexdigest(),
        code_version=_NAVALAI_VERSION,
        reasons=tuple(reasons), regime=regime,
        regime_supported=supported, quantities=quantities,
        descriptors=desc if isinstance(desc, dict) else desc,
        targets=dict(ev.targets), speed_curve=curve, loading=loading,
        stability=stability, buildability=buildability,
        cfd_candidate=cfd_candidate, violations=tuple(ev.violations),
        assumptions=tuple(assumptions), evaluation_ok=bool(ev.ok))
