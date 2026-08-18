"""PHYSICAL FORM REGRESSION — descriptors + the six deterministic cases.

WHY THIS MODULE EXISTS. `grammar.check` is an ADMISSIBILITY gate: it says a
parameter vector can be built, not that the resulting form is a boat anybody
would recognise. A hull can clear every algebraic clause and still carry a
double-humped sectional area curve, a 33-degree entrance on a hull whose family
runs 7-12, or a displacement distribution no lines plan shows. The directive
this module answers: *"Do not accept a hull merely because it passes
grammar.check ... Add regression tests so future architecture changes cannot
make the generated forms progressively less boat-like while all software tests
remain green."*

WHAT IT IS NOT. It re-transcribes NO geometry. Every descriptor is a reading of
the kernel's own arrays and methods (`geometry.sectional_area`,
`geometry.design_waterline`, `geometry.station_geometry`,
`Hull.form_coefficients`, `Hull.alpha_e_deg`, `Hull.wetted_surface`) or of the
evaluated state (`evaluate.evaluate` -> `HydroState`, GM, Fn, Re). Where a
descriptor cannot be computed it is marked ABSENT WITH A REASON — never
fabricated (LESSONS.md defect class 1: an unmeasurable quantity scored as a
passing one).

SOURCED RANGES. `sourced_range()` returns a range ONLY when one exists in this
tree with provenance (grammar.PROPORTION_BANDS, limits.prismatic_target /
LCB_BAND_PCT_LWL, formlib family bands, formlib.alpha_e_chord_floor_deg,
formlib.DRAWN_DIMENSION_RANGES, mission.SEPARATION_OVER_LWL_BAND). Everything
else is "UNKNOWN — no sourced range in tree" and stays that way until a source
lands; a range invented to make a table look finished is the defect this
repository keeps paying for.

THE SIX CASES are fixed parameter vectors (no sampling, no seeds needed —
determinism is by construction) shared by `scripts/physical_form_report.py`
and `tests/test_physical_form.py`, defined ONCE here so the report and the
regression tests can never drift apart. The report script prints every vector
verbatim, so the numbers are recorded in the generated document too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import formlib, grammar, geometry
from .energy import EnergySpec
from .formlib import Topology, alpha_e_chord_floor_deg
from .geometry import Hull, RHO_WATER
from .limits import (LCB_BAND_PCT_LWL, PRISMATIC_TOLERANCE,
                     RE_TRANSITION_BAND, HullRole, gm_floor, hull_role,
                     prismatic_target)
from .mission import (SEPARATION_OVER_LWL_BAND, Manning, MissionSpec,
                      VesselConfig)

# Stations for the reported SAC distribution. Eleven is the classical
# ten-interval station set of a lines plan (stations 0..10); the unimodality
# TEST uses a denser grid so a hump cannot hide between report stations.
N_SAC_STATIONS = 11

# Provisional entrance-angle ceiling for the regression test, DEG.
# PROVISIONAL AND LABELLED SO: no source in this tree bounds a small beamy
# hull's entrance from above. What the tree does hold: family bands run 4-14
# deg for slender hulls (formlib.FAMILIES, approx/drawing) and the arithmetic
# chord floor at the monohull L/B floor of 2.2 is 19-26 deg
# (formlib.alpha_e_chord_floor_deg), so beamy-small-craft entrances in the
# high 20s-low 30s are geometry, not deformity. 45 deg is a ceiling above
# which the "bow" is no longer finer than the midbody in any meaningful sense
# — a coarse tripwire against a collapse into a barge front, not a design bar.
ALPHA_E_PROVISIONAL_CEILING_DEG = 45.0

UNKNOWN_RANGE = "UNKNOWN — no sourced range in tree"


# ---------------------------------------------------------------------------
# The six deterministic cases
# ---------------------------------------------------------------------------


def _vec(lwl: float, bwl: float, t: float, cp: float,
         roundness: float = 0.0, **over: float) -> np.ndarray:
    """The `tests/test_vessel_bands._hull` idiom: a known-buildable shape-gene
    set with the principal dimensions and design targets on top. D defaults to
    the shallowest depth that clears both freeboard floors with margin."""
    d = max(t + grammar.MIN_FREEBOARD_ABS_M,
            t + grammar.MIN_FREEBOARD_FRAC_LWL * lwl) + 0.02
    p = dict(LWL=lwl, BWL=bwl, T=t, D=d, Cp=cp, lcb=0.0, x_mb=0.55,
             r_transom=0.20, beta_mid=8.0, beta_bow=20.0, beta_len=0.35,
             roundness=roundness, rocker=0.05, forefoot=0.30, flare=5.0,
             sheer_rise=0.10)
    p.update(over)
    return grammar.vector(p)


@dataclass(frozen=True)
class FormCase:
    key: str
    title: str
    params: np.ndarray = field(repr=False)
    mission: MissionSpec = field(repr=False)
    drawn_row: str            # DRAWN_DIMENSION_RANGES row this case maps to
    family_key: str | None    # formlib family whose bands apply, or None
    rationale: str

    @property
    def vessel(self) -> VesselConfig:
        return self.mission.vessel

    @property
    def named(self) -> dict[str, float]:
        return grammar.named(self.params)


def _cases() -> tuple[FormCase, ...]:
    # Every Cp gene below is centred on `limits.prismatic_target` at the
    # mission's design Froude number (R1.1's form-follows-function rule,
    # applied by hand here since nothing in production applies it yet) —
    # the tests assert delivered Cp against that target with its tolerance.
    return (
        FormCase(
            key="a", title="5 m recreational monohull (hard chine dayboat)",
            params=_vec(5.0, 2.05, 0.40, 0.573),
            mission=MissionSpec(
                name="case-a 5m dayboat", displacement_target_kg=800.0,
                cruise_speed_kn=4.0, design_category="D", crew=2,
                energy=EnergySpec(payload_kg=250.0, battery_kwh=8.0)),
            drawn_row="small monohull", family_key="hard_chine_displacement",
            rationale="L/B 2.44, B/T 5.13 — a beamy plywood dinghy-class "
                      "hull; Fn 0.29 at 4 kn, Cp gene on "
                      "prismatic_target(0.29)."),
        FormCase(
            key="b", title="15 m recreational monohull (round-bilge cruiser)",
            params=_vec(15.0, 3.8, 0.85, 0.573, roundness=0.5),
            mission=MissionSpec(
                name="case-b 15m cruiser", displacement_target_kg=14000.0,
                cruise_speed_kn=7.0, design_category="C", crew=6),
            drawn_row="large monohull", family_key="round_bilge_displacement",
            rationale="L/B 3.95, B/T 4.47, half-round bilge; Fn 0.30 at "
                      "7 kn; inside the NPL round-bilge series envelope "
                      "on both proportions."),
        FormCase(
            key="c", title="10 m solar catamaran (slender demihull, 8-12 m "
                           "class)",
            params=_vec(10.0, 0.82, 0.52, 0.558, roundness=0.8),
            mission=MissionSpec(
                name="case-c 10m solar cat", displacement_target_kg=3400.0,
                cruise_speed_kn=5.0, design_category="D", crew=2,
                vessel=VesselConfig(topology=Topology.CATAMARAN,
                                    separation_over_lwl=0.32)),
            drawn_row="catamaran", family_key="slender_symmetric_cat_demihull",
            rationale="demihull L/B 12.2 (inside the drawn 12-18 band and "
                      "the Southampton envelope), B/T 1.58 >= the 1.50 "
                      "series floor; s/L 0.32."),
        FormCase(
            key="d", title="12 m solar catamaran — the project's 12 x 0.8 m "
                           "demihull class",
            params=_vec(12.0, 0.8, 0.52, 0.559, roundness=0.8),
            mission=MissionSpec(
                name="case-d 12x0.8 solar cat", displacement_target_kg=4300.0,
                cruise_speed_kn=5.5, design_category="C", crew=2,
                vessel=VesselConfig(topology=Topology.CATAMARAN,
                                    separation_over_lwl=0.30)),
            drawn_row="catamaran", family_key="slender_symmetric_cat_demihull",
            rationale="THE target class: L/B 15.0 (inside Southampton's "
                      f"[{formlib.SOTON_DEMIHULL_L_OVER_B.low:.2f}, "
                      f"{formlib.SOTON_DEMIHULL_L_OVER_B.high:.2f}]). "
                      "T = 0.52 m so design B/T 1.538 sits "
                      "ABOVE the sourced 1.50 floor — the owner's 0.6 m "
                      "draft is refused on evidence (grammar's "
                      "OUT_OF_SOURCED_RANGE) and is deliberately not used."),
        FormCase(
            key="e", title="5 m autonomous survey drone (UNCREWED)",
            params=_vec(5.0, 1.4, 0.33, 0.573),
            mission=MissionSpec(
                name="case-e 5m survey drone", displacement_target_kg=500.0,
                cruise_speed_kn=4.0, design_category="D", crew=1,
                energy=EnergySpec(payload_kg=100.0, battery_kwh=6.0,
                                  hotel_kwh_day=0.5),
                vessel=VesselConfig(manning=Manning.UNCREWED)),
            drawn_row="small monohull", family_key="hard_chine_displacement",
            rationale="L/B 3.57 monohull, Manning.UNCREWED — exercises the "
                      "drone rule-routing (ISO 12217-1 refused by name, "
                      "nothing invented in its place)."),
        FormCase(
            key="f", title="7 m fishing/research drone (UNCREWED)",
            params=_vec(7.0, 2.0, 0.45, 0.568),
            mission=MissionSpec(
                name="case-f 7m fishing drone", displacement_target_kg=1400.0,
                cruise_speed_kn=4.5, design_category="C", crew=1,
                energy=EnergySpec(payload_kg=300.0, battery_kwh=12.0,
                                  hotel_kwh_day=1.0),
                vessel=VesselConfig(manning=Manning.UNCREWED)),
            drawn_row="small monohull", family_key="hard_chine_displacement",
            rationale="L/B 3.50, B/T 4.44, category C — a working-payload "
                      "uncrewed hull; same UNCREWED routing at a heavier "
                      "displacement."),
    )


CASES: tuple[FormCase, ...] = _cases()


def design_froude(mission: MissionSpec, lwl_m: float) -> float:
    """Fn at the mission cruise speed on the DECLARED waterline length."""
    return mission.cruise_speed_ms() / math.sqrt(geometry.G * lwl_m)


# ---------------------------------------------------------------------------
# Descriptors
# ---------------------------------------------------------------------------


def form_descriptors(params: np.ndarray, mission: MissionSpec | None = None
                     ) -> dict:
    """Physical design descriptors of one genome, honestly partitioned.

    Returns a dict with four keys:

      "scalars"  {name: float}     — every computed scalar descriptor
      "arrays"   {name: list}      — SAC distribution & per-station fullness
      "absent"   {name: reason}    — descriptors that COULD NOT be computed,
                                     each with the reason (never fabricated)
      "meta"     {...}             — provenance: which kernel call produced
                                     what, evaluation tier/ok/violations

    Geometry-side descriptors come straight from the kernel (`Hull`,
    `geometry.sectional_area`, `geometry.design_waterline`,
    `Hull.form_coefficients`, `Hull.alpha_e_deg`, `Hull.wetted_surface`) at
    the DESIGN waterline. Float-state descriptors (GM, KB, BM, KG, floated
    draft/displacement, Fn, Re) come from `evaluate.evaluate(params, mission)`
    and are ABSENT with a reason when no mission is given or the float is
    refused.
    """
    x = np.asarray(params, dtype=float)
    scalars: dict[str, float] = {}
    arrays: dict[str, list] = {}
    absent: dict[str, str] = {}
    meta: dict = {"kernel": {}, "evaluation": None}

    p = grammar.named(x)
    L, B, T = p["LWL"], p["BWL"], p["T"]
    vessel = getattr(mission, "vessel", None)
    n_hulls = int(getattr(vessel, "n_hulls", 1) or 1)
    role = hull_role(vessel)

    rep = grammar.check(x, vessel=vessel)
    meta["grammar_ok"] = rep.ok
    meta["grammar_violations"] = list(rep.violations)
    if not rep.ok:
        # No geometry can be built from a refused vector; everything is
        # absent for the same one reason. Refusal, not fabrication.
        reason = ("grammar.check refused this vector: "
                  + "; ".join(rep.violations))
        for name in ("L_over_B", "B_over_T", "Cp", "Cb", "Cm", "Cwp"):
            absent[name] = reason
        return {"scalars": scalars, "arrays": arrays, "absent": absent,
                "meta": meta}

    hull = Hull(x)
    fc = hull.form_coefficients()
    meta["kernel"]["form_coefficients"] = "Hull.form_coefficients(n=401)"

    # -- proportions at the DESIGN waterline (the genome's own numbers)
    scalars["L_over_B"] = L / B
    scalars["B_over_T"] = B / T
    scalars["lwl_m"] = L
    scalars["bwl_m"] = B
    scalars["draft_design_m"] = T

    # -- form coefficients of the DELIVERED surface (not the genes)
    vol = fc["volume_m3"]
    scalars["Cp"] = fc["Cp"]
    scalars["Cm"] = fc["Cm"]
    scalars["Cwp"] = fc["Cwp"]
    scalars["Cb"] = vol / (L * B * T)      # Cb = Cp * Cm by identity
    scalars["lcb_pct_lwl"] = fc["lcb_pct"]
    scalars["lcf_pct_lwl"] = fc["lcf_pct"]
    scalars["volume_design_m3"] = vol
    scalars["displacement_design_kg"] = RHO_WATER * vol * n_hulls
    meta["kernel"]["rho"] = ("geometry.RHO_WATER = 1000 kg/m^3 (fresh, "
                             "Danube) — design-WL displacement only")

    # -- entrance geometry, FROM the design-waterline curve of the kernel.
    # `Hull.alpha_e_deg` is the chord over the forward `frac` of LWL of the
    # first-class `design_waterline` curve — the method is part of the number
    # (the tangent at the stem would measure the geometric floor, not the
    # hull; see the kernel docstring). Both the lines-plan-ish 2% chord and a
    # 10% chord are reported so a blunt closing envelope is distinguishable
    # from a genuinely full forebody.
    scalars["entrance_half_angle_deg"] = hull.alpha_e_deg()
    scalars["entrance_half_angle_10pct_deg"] = hull.alpha_e_deg(frac=0.10)
    scalars["alpha_e_chord_floor_deg"] = alpha_e_chord_floor_deg(
        scalars["L_over_B"], 0.60)
    meta["kernel"]["entrance"] = ("Hull.alpha_e_deg(frac=0.02 and 0.10): "
                                  "chord of geometry.design_waterline at the "
                                  "stem; floor = formlib."
                                  "alpha_e_chord_floor_deg(L/B, 0.60)")

    # -- exit/run angle at the stern: chord of the SAME design-waterline
    # curve over the aft 10% of LWL. There is no kernel method for the run,
    # so this reads the kernel's curve directly (no re-transcription).
    yw_aft = geometry.design_waterline(x, np.array([0.0, 0.10 * L]))
    scalars["run_half_angle_deg"] = math.degrees(
        math.atan2(float(yw_aft[1] - yw_aft[0]), 0.10 * L))

    # -- SAC distribution: the kernel's own sectional-area curve, delivered,
    # at the 11 lines-plan stations, normalised by its maximum.
    xs11 = np.linspace(0.0, L, N_SAC_STATIONS)
    A11 = geometry.sectional_area(x, xs11)
    xs_d = np.union1d(np.linspace(0.0, L, 401), [p["x_mb"] * L])
    A_d = geometry.sectional_area(x, xs_d)
    a_max = float(A_d.max())
    arrays["sac_x_over_L"] = [float(v) for v in xs11 / L]
    arrays["sac_norm"] = [float(v / a_max) for v in A11]
    scalars["A_max_m2"] = a_max

    # -- sectional fullness: area coefficient per station,
    # A(x) / (2 * y_wl(x) * d(x)), all three read from the kernel.
    zk, _yc, _zc, _ys, _zs = geometry.station_geometry(x, xs11)
    yw11 = geometry.design_waterline(x, xs11)
    d11 = -zk
    denom = 2.0 * yw11 * d11
    fullness = np.where(denom > 1e-9, A11 / np.maximum(denom, 1e-9),
                        float("nan"))
    arrays["section_fullness"] = [float(v) for v in fullness]
    meta["kernel"]["fullness"] = ("sectional_area / (2 * design_waterline * "
                                  "local keel depth); nan where the section "
                                  "has vanished (the stem)")

    # -- bow fineness & stern fullness from the SAC integrals
    tot = float(np.trapezoid(A_d, xs_d))
    fwd = xs_d >= 0.8 * L
    aft = xs_d <= 0.2 * L
    scalars["fwd20_sac_fraction"] = float(np.trapezoid(A_d[fwd], xs_d[fwd])) / tot
    scalars["aft20_sac_fraction"] = float(np.trapezoid(A_d[aft], xs_d[aft])) / tot
    # normalised SAC slope over the forward 20%: d(a)/d(x/L) as a chord
    a_80 = float(geometry.sectional_area(x, np.array([0.8 * L]))[0]) / a_max
    a_L = float(geometry.sectional_area(x, np.array([L]))[0]) / a_max
    scalars["bow_sac_slope"] = (a_80 - a_L) / 0.2

    # -- transom: the DELIVERED area ratio and the waterline-beam ratio.
    # The second is the finding-detector: the kernel delivers the transom
    # AREA at near-full local draft, so the transom WATERLINE half-breadth
    # comes out far narrower than the area ratio suggests (a deep, narrow
    # transom section — plan view closes almost to a canoe stern).
    scalars["transom_area_ratio"] = float(
        geometry.sectional_area(x, np.array([0.0]))[0]) / a_max
    y_wl_max = float(np.max(geometry.design_waterline(x, xs_d)))
    scalars["transom_waterline_beam_ratio"] = float(yw_aft[0]) / max(
        y_wl_max, 1e-9)

    # -- wetted surface & the transport coefficient
    ws = hull.wetted_surface(0.0)
    scalars["wetted_design_m2_per_hull"] = ws
    scalars["ws_over_vol23"] = (n_hulls * ws) / (n_hulls * vol) ** (2.0 / 3.0)
    meta["kernel"]["wetted"] = ("Hull.wetted_surface(0.0), design WL; "
                                "ws_over_vol23 is VESSEL wetted over VESSEL "
                                "volume^(2/3), so it carries n_hulls^(1/3)")

    # -- multihull configuration
    if n_hulls > 1:
        sep_ratio = float(vessel.separation_over_lwl)
        scalars["separation_over_lwl"] = sep_ratio
        scalars["separation_m"] = vessel.separation_m(L)
        scalars["demihull_beam_m"] = B
    else:
        absent["separation_over_lwl"] = ("monohull — no second hull to be "
                                         "separated from")

    # -- the evaluated (floated) state
    if mission is None:
        for name in ("Fn", "Re", "GM_m", "KB_m", "BM_m", "KG_m",
                     "displacement_floated_kg", "draft_floated_m"):
            absent[name] = ("no mission given — Fn/Re need a cruise speed "
                            "and the float needs a displacement target")
    else:
        from .evaluate import evaluate     # local: evaluate imports widely
        ev = evaluate(x, mission)
        meta["evaluation"] = {
            "tier": ev.tier, "ok": ev.ok,
            "violations": list(ev.violations),
        }
        if ev.hydro is None:
            reason = ("the ladder refused the float: "
                      + "; ".join(ev.violations))
            for name in ("Fn", "Re", "GM_m", "KB_m", "BM_m", "KG_m",
                         "displacement_floated_kg", "draft_floated_m"):
                absent[name] = reason
        else:
            hs = ev.hydro
            scalars["Fn"] = float(ev.vessel["fn"])
            scalars["Re"] = float(ev.vessel["re"])
            scalars["displacement_floated_kg"] = hs.disp_kg
            scalars["draft_floated_m"] = hs.draft
            scalars["L_over_B_floated"] = hs.lwl_eff / max(hs.b_wl_max, 1e-9)
            scalars["B_over_T_floated"] = hs.b_wl_max / max(hs.draft, 1e-9)
            scalars["KB_m"] = hs.kb
            scalars["BM_m"] = hs.bm
            if ev.gm_m is not None and math.isfinite(ev.gm_m):
                scalars["GM_m"] = float(ev.gm_m)
                t_design = -float(hull.z_keel.min())
                scalars["KG_m"] = ev.masses.vcg_above_keel(t_design)
            else:
                absent["GM_m"] = "evaluate returned no finite GM"
                absent["KG_m"] = "no mass aggregate KG without a finite GM"
            if n_hulls > 1:
                scalars["demihull_beam_floated_m"] = hs.b_wl_max
            meta["evaluation"]["role"] = role.value

    return {"scalars": scalars, "arrays": arrays, "absent": absent,
            "meta": meta}


# ---------------------------------------------------------------------------
# Sourced ranges — ONLY what exists in this tree, with provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourcedRange:
    low: float | None          # None = one-sided
    high: float | None
    source: str
    provisional: bool = False  # True only for the labelled test ceiling

    def contains(self, v: float) -> bool:
        if self.low is not None and v < self.low:
            return False
        if self.high is not None and v > self.high:
            return False
        return True

    def __str__(self) -> str:
        lo = "-inf" if self.low is None else f"{self.low:g}"
        hi = "+inf" if self.high is None else f"{self.high:g}"
        return f"[{lo}, {hi}]"


def _family(case: FormCase) -> formlib.FormFamily | None:
    if case.family_key is None:
        return None
    for f in formlib.FAMILIES:
        if f.key == case.family_key:
            return f
    return None


def sourced_ranges(case: FormCase) -> dict[str, SourcedRange | str]:
    """descriptor name -> SourcedRange, or the UNKNOWN sentinel string.

    Every range here is IMPORTED from the module that owns it — grammar,
    limits, formlib, mission — never restated as a literal (the
    number-declared-twice defect). Descriptors with no source in the tree map
    to the UNKNOWN string and the report prints them that way.
    """
    role = hull_role(case.vessel)
    bands = grammar.PROPORTION_BANDS[role]
    fam = _family(case)
    p = case.named
    fn = design_froude(case.mission, p["LWL"])
    cp_t = prismatic_target(fn)
    out: dict[str, SourcedRange | str] = {}

    (lb_lo, lb_hi), lb_src = bands["L/B"]
    (bt_lo, bt_hi), bt_src = bands["B/T"]
    out["L_over_B"] = SourcedRange(lb_lo, lb_hi,
                                   f"grammar.PROPORTION_BANDS[{role.value}] "
                                   f"— {lb_src}")
    out["B_over_T"] = SourcedRange(bt_lo, bt_hi,
                                   f"grammar.PROPORTION_BANDS[{role.value}] "
                                   f"— {bt_src}")
    out["L_over_B_floated"] = out["L_over_B"]
    out["B_over_T_floated"] = out["B_over_T"]

    out["Cp"] = SourcedRange(
        cp_t - PRISMATIC_TOLERANCE, cp_t + PRISMATIC_TOLERANCE,
        f"limits.prismatic_target(Fn={fn:.3f}) = {cp_t:.4f} "
        f"+- limits.PRISMATIC_TOLERANCE (practice curve, basis 'approx')")
    out["lcb_pct_lwl"] = SourcedRange(
        -LCB_BAND_PCT_LWL, LCB_BAND_PCT_LWL,
        "limits.LCB_BAND_PCT_LWL (+-3 %LWL, displacement-hull practice, "
        "basis 'approx')")

    if fam is not None:
        cb = fam.band("cb")
        if cb is not None:
            out["Cb"] = SourcedRange(
                cb.low, cb.high,
                f"formlib.FAMILIES[{fam.key}].cb {cb} — {cb.source}")
        else:
            out["Cb"] = (f"{UNKNOWN_RANGE} (family {fam.key} carries no cb "
                         f"band)")
        ae = fam.band("alpha_e_deg")
        if ae is not None:
            out["entrance_half_angle_deg"] = SourcedRange(
                ae.low, ae.high,
                f"formlib.FAMILIES[{fam.key}].alpha_e_deg {ae} — {ae.source}")
        else:
            out["entrance_half_angle_deg"] = (
                f"{UNKNOWN_RANGE} (family {fam.key} carries no alpha_e band; "
                f"the arithmetic floor formlib.alpha_e_chord_floor_deg "
                f"applies)")
        out["Fn"] = SourcedRange(
            fam.fn.low, fam.fn.high,
            f"formlib.FAMILIES[{fam.key}].fn {fam.fn} — {fam.fn.source}")
    else:
        out["Cb"] = UNKNOWN_RANGE
        out["entrance_half_angle_deg"] = UNKNOWN_RANGE
        out["Fn"] = UNKNOWN_RANGE

    # Re: ITTC-57 is a FULLY TURBULENT correlation line; below the transition
    # ceiling it is being read outside the regime it correlates.
    out["Re"] = SourcedRange(
        RE_TRANSITION_BAND[1], None,
        "limits.RE_TRANSITION_BAND — ITTC-57 valid only above the "
        "laminar-turbulent transition ceiling (5e6); see "
        "limits.friction_line_validity")

    # GM: sourced floor for a crewed monohull ONLY. A multihull GM verdict is
    # explicitly refused (hydrostatics.multihull_stability_refusal), and no
    # rule set exists for uncrewed craft — saying so is the verdict.
    if role is HullRole.MONOHULL and case.vessel.manning is not Manning.UNCREWED:
        out["GM_m"] = SourcedRange(
            gm_floor(case.mission.design_category), None,
            f"limits.gm_floor({case.mission.design_category!r}) — "
            f"CATEGORY_TABLE, basis 'approx' (an L1 feasibility floor, not "
            f"ISO text)")
    elif role is not HullRole.MONOHULL:
        out["GM_m"] = ("REFUSED — multihull stability has NO implemented "
                       "criterion; GM does not establish safety "
                       "(hydrostatics.multihull_stability_refusal, "
                       "limits.MULTIHULL_RIGHTING_CRITERIA)")
    else:
        out["GM_m"] = ("UNKNOWN — no stability rule set exists for uncrewed "
                       "craft in this tree (RCD/ISO 12217-1 do not govern "
                       "them; evaluate refuses by name)")

    # drawn dimension ranges (Basis.DRAWING) for the case's class row.
    # NOT applied to uncrewed craft: the 000 dimension table depicts
    # RECREATIONAL solar craft and no drone row exists in the tree — banding
    # a survey drone by a dayboat drawing would be the drawn-catamaran-beam
    # category error in another costume.
    if case.vessel.manning is Manning.UNCREWED:
        for name in ("lwl_m", "draft_design_m", "bwl_m"):
            out[name] = (f"{UNKNOWN_RANGE} (DRAWN_DIMENSION_RANGES depicts "
                         f"recreational craft; no drone row exists)")
    else:
        drawn = formlib.DRAWN_DIMENSION_RANGES[case.drawn_row]
        for key, name in (("lwl_m", "lwl_m"), ("draft_m", "draft_design_m")):
            b = drawn.get(key)
            if b is not None:
                out[name] = SourcedRange(
                    b.low, b.high,
                    f"formlib.DRAWN_DIMENSION_RANGES[{case.drawn_row!r}]"
                    f"[{key!r}] {b} — {b.source}")
        # beam: per-hull ONLY for monohull rows; the catamaran row's beam is
        # OVERALL beam (B_oa) and must not band a demihull beam.
        if role is HullRole.MONOHULL and "beam_m" in drawn:
            b = drawn["beam_m"]
            out["bwl_m"] = SourcedRange(
                b.low, b.high,
                f"formlib.DRAWN_DIMENSION_RANGES[{case.drawn_row!r}]"
                f"['beam_m'] {b} — {b.source}")
        else:
            out["bwl_m"] = (f"{UNKNOWN_RANGE} (the drawn catamaran beam row "
                            f"is OVERALL beam B_oa, not a demihull beam — "
                            f"formlib.DRAWN_DIMENSION_RANGES docstring)")

    if hasattr(case.vessel, "n_hulls") and case.vessel.n_hulls > 1:
        lo, hi = SEPARATION_OVER_LWL_BAND
        out["separation_over_lwl"] = SourcedRange(
            lo, hi,
            "mission.SEPARATION_OVER_LWL_BAND (a CONTRACT bound, not an "
            "optimum; the measured Wigley Fn 0.30 interference optimum is "
            "s/L 0.4450, formlib._S_OVER_L_BEST_FN030)")

    # Everything else: honestly unknown.
    for name in ("Cwp", "Cm", "lcf_pct_lwl", "run_half_angle_deg",
                 "ws_over_vol23", "fwd20_sac_fraction", "aft20_sac_fraction",
                 "bow_sac_slope", "entrance_half_angle_10pct_deg",
                 "KB_m", "BM_m", "KG_m", "transom_waterline_beam_ratio"):
        out.setdefault(name, UNKNOWN_RANGE)
    # Transom area ratio: the ONE related in-tree citation is
    # formlib._TRANSOM_AREA_RATIO (A_T/A_M 0.31-0.52, MARIN/S64/NPL), but
    # those are SEMI-DISPLACEMENT series at Fn 0.3+ — applying their band to
    # a displacement hull at Fn 0.26-0.30 would be a category stretch, so it
    # is quoted as reference and NOT used as a bar.
    out.setdefault(
        "transom_area_ratio",
        f"{UNKNOWN_RANGE} for displacement craft at this Fn (reference only: "
        f"formlib's transom citation holds A_T/A_M 0.31-0.52 for the "
        f"MARIN/Series-64/NPL SEMI-DISPLACEMENT series)")
    return out


# ---------------------------------------------------------------------------
# The ratchet
# ---------------------------------------------------------------------------

# Descriptor-appropriate ABSOLUTE tolerance floors, applied on top of the 10%
# relative default. Angles and percentages are near-zero-crossing quantities
# where a pure relative band collapses to nothing.
_RATCHET_ABS_FLOOR = {
    "lcb_pct_lwl": 0.50,               # %LWL
    "lcf_pct_lwl": 0.75,
    "entrance_half_angle_deg": 0.75,
    "entrance_half_angle_10pct_deg": 0.75,
    "run_half_angle_deg": 0.75,
    "alpha_e_chord_floor_deg": 0.25,
    "GM_m": 0.05,
    "Fn": 0.01,
    "draft_floated_m": 0.02,
    "bow_sac_slope": 0.10,
    "fwd20_sac_fraction": 0.01,
    "aft20_sac_fraction": 0.01,
    "transom_area_ratio": 0.02,
    "transom_waterline_beam_ratio": 0.02,
}
_RATCHET_REL = 0.10


def ratchet_entries(descriptors: dict) -> dict[str, dict[str, float]]:
    """Baseline entries for one case: {name: {"value": v, "tol": t}}.

    Tolerance = max(10% of |value|, the descriptor's absolute floor). The
    entries pin the MEASURED form of the current tree; a future change that
    moves one outside its band fails the ratchet test with instructions to
    re-baseline WITH justification, not to widen the tolerance.
    """
    out: dict[str, dict[str, float]] = {}
    for name, v in descriptors["scalars"].items():
        if not (isinstance(v, (int, float)) and math.isfinite(v)):
            continue
        tol = max(_RATCHET_REL * abs(float(v)),
                  _RATCHET_ABS_FLOOR.get(name, 1e-9))
        out[name] = {"value": float(v), "tol": float(tol)}
    return out
