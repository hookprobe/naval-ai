"""THE FIDELITY GOVERNOR — which model may answer, and whether it is worth it.

The directive's §21 "CFD decision engine" and §11 fidelity hierarchy, turned
from prose into a deterministic function. The design is not invented here: it
is `docs/research/SMALL-CRAFT-REGIMES.md` §16 (the gate sketch), §5/§6/§7 (the
measured wave-share, capillary and wave-environment numbers), §13 (the
decision-worthiness threshold) and §14/§15 (the regime x model table), plus
`docs/BUILD-PLAN.md` §11.8. Every threshold below cites the section it came
from, and every threshold that already had a home in this tree is IMPORTED
rather than retyped (`limits.RE_TRANSITION_BAND`,
`limits.WH_PER_NM_SIGMA_PRODUCT`, `resistance.FN_MICHELL_MAX`,
`resistance.flow_regime`, `dynamics.RHO_AIR`/`CD_LATERAL`).

WHAT THIS CHANGES, STATED PLAINLY. Before this module every valid design ran
the SAME L1 model and was BADGED (`resistance.FlowRegime`, `SpeedPoint`
validity bands) — never ROUTED. `certify.cfd_candidate` therefore meant
"anything valid is CFD-worthy". Of the five gates the study asked for, the
ENVIRONMENT and WAVE-EXISTENCE gates did not exist at all, the friction and
Froude gates existed as FLOORS with no routing, and
`limits.WH_PER_NM_SIGMA_PRODUCT` (0.10) had ZERO consumers repo-wide. This
module is that constant's first consumer (gate 4) and the router the badges
never were.

THE FIVE GATES, IN ORDER (§16):

  0. ENVIRONMENT      lambda/L > 5 (wave-follower), windage/R > 2, or
                      u_orbital >= 0.5 V  -> calm-water refinement cannot
                      change the decision -> ANALYTICAL, flagged.
  1. WAVE EXISTENCE   V < 0.23 m/s: no steady wave system exists at all
                      (the gravity-capillary phase-speed minimum);
                      V < 0.50 m/s: the wave prediction is capillary
                      -contaminated. CFD never, below 0.5 m/s.
  2. FRICTION REGIME  Re < 5e5 laminar -> analytical only, CFD REFUSED;
                      5e5..5e6 transitional -> CFD BARRED unless the run is
                      declared transition-modelled, and the empirical sigma
                      widens to the study's +-30..50% band.
  3. FROUDE           Fn <= 0.20 -> ANALYTICAL suffices (wave share < 5-8%,
                      MEASURED); 0.20 < Fn <= 0.45 -> EMPIRICAL (Michell);
                      0.45 < Fn <= 0.65 -> CFD is the only honest tier, and
                      only at L >= 3 m; Fn > 0.65 -> REFUSE (no Savitsky).
  4. DECISION-WORTHY  escalate only when the expected correction could exceed
                      `limits.WH_PER_NM_SIGMA_PRODUCT` AND a verdict could
                      plausibly flip.

PURE AND TOTAL. No I/O, no solver, no geometry: everything it needs arrives as
an argument. MISSING INFORMATION IS NEVER A PASS — a gate that cannot be
decided returns outcome CANNOT_DECIDE with the input it lacks NAMED, and the
governor carries a warning. An undeclared environment does not silently mean
"the environment is fine"; it means nobody said.

WHAT IS NEW PHYSICS HERE, AND HOW HONEST IT IS. Gates 2/3/4 are wiring over
seams this tree already owns. Gates 0/1 are not: the windage and orbital
estimators did not exist and are written here, minimally, each carrying its
formula and its basis at the point of use. They are ESTIMATORS for a routing
decision — a factor-of-two question ("is the environment 2x the hull drag?")
— never reported as forces a design may be built to.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import G_STANDARD as _G
from .constants import RHO_FRESH as _RHO_FRESH
from .dynamics import CD_LATERAL as _CD_LATERAL
from .dynamics import RHO_AIR as _RHO_AIR
from .limits import RE_TRANSITION_BAND, WH_PER_NM_SIGMA_PRODUCT
from .resistance import FN_MICHELL_MAX, flow_regime

# --------------------------------------------------------------------------
# THE TIER VOCABULARY (§11 fidelity hierarchy, §15's regime x model table)
# --------------------------------------------------------------------------
TIER_ANALYTICAL = "ANALYTICAL"          # L0: friction + form factor + margin
TIER_EMPIRICAL = "EMPIRICAL"            # L1: Michell + ITTC-57 + form factor
TIER_LOW_FIDELITY_CFD = "LOW_FIDELITY_CFD"
TIER_FULL_CFD = "FULL_CFD"
TIER_REFUSE = "REFUSE"                  # no tier in this tree may answer

# Ordered by what a tier COSTS, which is also the order §16 escalates in.
_RANK: dict[str, int] = {
    TIER_ANALYTICAL: 0,
    TIER_EMPIRICAL: 1,
    TIER_LOW_FIDELITY_CFD: 2,
    TIER_FULL_CFD: 3,
}
_BY_RANK = {v: k for k, v in _RANK.items()}

# Gate outcomes. A gate either does not bite (CLEAR), decides the tier
# (ROUTE), forbids a tier without choosing one (BAR), or admits it cannot be
# decided from what it was given (CANNOT_DECIDE). There is deliberately no
# "PASS": a gate that was never evaluated must not read like one that was.
OUT_CLEAR = "CLEAR"
OUT_ROUTE = "ROUTE"
OUT_BAR = "BAR"
OUT_CANNOT_DECIDE = "CANNOT_DECIDE"

GATE_ENVIRONMENT = "ENVIRONMENT"
GATE_WAVE_EXISTENCE = "WAVE_EXISTENCE"
GATE_FRICTION_REGIME = "FRICTION_REGIME"
GATE_FROUDE = "FROUDE"
GATE_DECISION_WORTHINESS = "DECISION_WORTHINESS"

# --------------------------------------------------------------------------
# GATE 0 — the environment thresholds (§16; the physics in §7 and §8)
# --------------------------------------------------------------------------
# lambda/L >= 5 is the study's "pure wave-follower" band (§7's table): the
# hull rides the surface and sees the local slope as gravity, so there is
# nothing to pierce and the calm-water wave pattern is not the energy budget.
LAMBDA_OVER_LWL_WAVE_FOLLOWER = 5.0
# windage/hull-resistance > 2 and u_orbital >= 0.5 V are §16's own bars. The
# measured anchor behind them (§1, repo Holtrop): a 0.5 m hull at 0.5 m/s has
# R ~ 0.06 N against 2-3 N of windage on a non-scaling sensor area (30-50x),
# and the sea-state-3 orbital velocity, 0.57 m/s, EXCEEDS the cruise speed.
WINDAGE_OVER_RESISTANCE_MAX = 2.0
ORBITAL_OVER_SPEED_MAX = 0.5

# --------------------------------------------------------------------------
# GATE 1 — where a wave system stops existing (§6)
# --------------------------------------------------------------------------
# c_min = (4 g sigma / rho)^(1/4) ~ 0.23 m/s is the gravity-capillary phase
# speed MINIMUM: below it no steady wave pattern of any wavelength can be
# generated, so wave resistance is not small — it is qualitatively absent.
C_MIN_GRAVITY_CAPILLARY_MS = 0.23
# The contamination bar: transverse wavelength lambda_t = 2 pi V^2 / g must be
# >> lambda_m ~ 17 mm. At 0.25 m/s lambda_t is 4.0 cm (2.3x capillary, the
# whole system is gravity-capillary); at 0.5 m/s it is 16 cm (9x, mild
# contamination of the shortest divergent components); at 1 m/s, 64 cm, clean.
# 0.5 m/s is [ROT] in the study and is labelled as such here.
WAVE_CAPILLARY_CLEAN_MS = 0.50

# --------------------------------------------------------------------------
# GATE 2 — the friction regime. The band is IMPORTED, never retyped.
# --------------------------------------------------------------------------
RE_TRANSITION_ONSET, RE_FULLY_TURBULENT = RE_TRANSITION_BAND
# Laminar: the study's ×2 friction margin (§14's 0.3-0.5 m row, §16's
# "sigma x2"), which is the size of the ITTC-57-vs-Blasius spread measured at
# Re 2.3e5 (a factor 2.4) on the component that is 72-92% of total resistance.
LAMINAR_SIGMA_MULTIPLIER = 2.0
# Transitional: the study's declared band for an untransitioned friction line
# (§15/§17 — "+-40%", tightening to +-15% only once a transitional line
# exists). The FLOOR applied is the conservative edge, 0.50: a sigma is only
# ever wrong in the refusing direction here.
TRANSITIONAL_SIGMA_BAND = (0.30, 0.50)
TRANSITIONAL_SIGMA_FLOOR = TRANSITIONAL_SIGMA_BAND[1]

# --------------------------------------------------------------------------
# GATE 3 — the Froude bands (§5, §15, §16)
# --------------------------------------------------------------------------
# Below Fn 0.20 the wave share is <=5-8% at every size in the measured grid
# (§5), and L0 friction+form matches anything fancier inside the product's own
# sigma. FN_MICHELL_MAX (0.45) is imported: the wave half's envelope has one
# home, `resistance`.
FN_ANALYTICAL_MAX = 0.20
# Michell is linearised on hull SLOPE, so its envelope is a beam/length bar,
# not a length/beam one: trustworthy for B/L <~ 0.10-0.15 (§5; the Wigley
# benchmark is B/L = 0.10). NOTE this is NOT `certify`'s slenderness test
# (L/B >= 6, which NAMES a regime); this one bounds a model.
BL_MICHELL_MAX = 0.15
# The planing onset. Conventional practice figure, used only to name the
# regime that has no model in this tree; `certify._FN_PLANING_ONSET` is an
# alias of this one so the number has a single home.
FN_PLANING_ONSET = 0.65
# The length below which CFD is not an honest answer even where it is the only
# remaining tier. Evidence, both directions (Appendix A): RANS is DEMONSTRATED
# trustworthy at 3 m (Delft 372, 2-5% vs tank) and DEMONSTRATED broken at 1 m
# (>=30% measured friction error) — and a fully-turbulent RANS inside the
# transition band reproduces ITTC-57's own bias, i.e. higher cost, same
# wrongness (§20 row 6).
LWL_CFD_FLOOR_M = 3.0

# --------------------------------------------------------------------------
# GATE 4 — decision-worthiness (§13). WH_PER_NM_SIGMA_PRODUCT's FIRST consumer.
# --------------------------------------------------------------------------
# The guard factor in §16's second clause: a correction is only decision-
# relevant if the nearest verdict flip is within 2.5x of it. 2.5 is the guard
# the product sigma was CHOSEN to preserve (limits.py: the nearest measured
# flip is 25.2% of Wh/NM away against a +-10% band).
WORTHINESS_FLIP_GUARD = 2.5

# --------------------------------------------------------------------------
# SEA STATE -> (Hs, T). DECLARED FROM THE STUDY, NOT TRANSCRIBED FROM WMO.
# --------------------------------------------------------------------------
# `mission.PayloadSpec.sea_state` is an int the mission DECLARES and that
# nothing in this tree has ever consumed. To use it, a wave height and period
# are needed; those come from §7's own bands, and only from there:
#   "SS2-3 (Hs 0.3-0.9 m, T 3-5 s)"  and  "SS4-5 (Hs 1.9-3 m, T 7-9 s)",
#   "short chop T 2-3 s".
# The lower state of each pair takes the band's lower edge and the upper state
# its upper edge. The cross-check that the pairing is the study's own: SS3 ->
# u = pi H / T = pi * 0.9 / 5 = 0.565 m/s, which is the 0.57 m/s the study
# quotes for sea state 3 in §1.
# ABOVE SS5 THIS TABLE REFUSES rather than extrapolating. WMO code 3700 gives
# Hs for states 6-9, but no period this study states, and a fabricated period
# would fabricate BOTH lambda and the orbital velocity — the two quantities
# gate 0 is made of.
SEA_STATE_HS_T: dict[int, tuple[float, float | None]] = {
    0: (0.0, None),      # calm (glassy): no wave environment at all
    1: (0.1, 2.0),
    2: (0.3, 3.0),
    3: (0.9, 5.0),
    4: (1.9, 7.0),
    5: (3.0, 9.0),
}

# --------------------------------------------------------------------------
# THE MEASURED WAVE SHARE (§5, repo Holtrop on an L/B 5, B/T 3, Cb 0.45,
# Cp 0.60 geosim family). Gate 4 uses it as the EXPECTED CORRECTION available
# to a better wave model when the analytical tier is the incumbent: what a
# wave-resolving tier can move is bounded by what the wave term is worth.
#   (LWL [m], share at Fn 0.25, share at Fn 0.35)
# --------------------------------------------------------------------------
WAVE_SHARE_MEASURED: tuple[tuple[float, float, float], ...] = (
    (0.5, 0.085, 0.28),
    (1.0, 0.105, 0.32),
    (2.0, 0.125, 0.37),
    (5.0, 0.151, 0.42),
    (12.0, 0.177, 0.46),
)
# §5's stated bound below Fn 0.20, at every size in the grid.
WAVE_SHARE_BELOW_FN_020 = 0.05


# --------------------------------------------------------------------------
# receipts
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class GateOutcome:
    """One gate's verdict, its MEASURED value, and the sentence that names it.

    `value` is the number the gate was decided on (Re, Fn, lambda/L, ...) so a
    reader never has to re-derive it, and `measure` says which number it is.
    `why` always contains the value: a bare verdict is not a receipt.
    """

    name: str
    outcome: str                       # CLEAR | ROUTE | BAR | CANNOT_DECIDE
    measure: str
    value: float | None
    why: str
    tier_cap: str | None = None        # the most expensive tier it permits
    bars_cfd: bool = False
    detail: tuple[str, ...] = ()       # sub-criterion receipts

    def to_dict(self) -> dict:
        return {"gate": self.name, "outcome": self.outcome,
                "measure": self.measure, "value": self.value,
                "why": self.why, "tier_cap": self.tier_cap,
                "bars_cfd": self.bars_cfd, "detail": list(self.detail)}


@dataclass(frozen=True)
class FidelityDecision:
    """WHICH TIER MAY ANSWER, why, and what each gate measured.

    `why` names the GATE that decided and carries its measured value; it is
    never a bare verdict. `gates` is the full ladder of receipts, including
    the gates that did not bite and the gates that could not be decided.
    """

    tier: str
    why: str
    gates: tuple[GateOutcome, ...]
    warnings: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    cfd_allowed: bool = False
    cfd_decision_worthy: bool = False
    fn: float | None = None
    re: float | None = None
    lwl_m: float | None = None
    speed_ms: float | None = None
    # What the FRICTION gate demands of the empirical sigma. `sigma_multiplier`
    # is the laminar x2; `sigma_floor_frac` is the transitional band's floor as
    # a fraction of the answer. Both are None/1.0 when ITTC-57 is in its regime.
    sigma_multiplier: float = 1.0
    sigma_floor_frac: float | None = None
    expected_correction_frac: float | None = None
    expected_correction_basis: str = "not established"

    @property
    def refused(self) -> bool:
        return self.tier == TIER_REFUSE

    def gate(self, name: str) -> GateOutcome:
        """The named gate's receipt (KeyError-equivalent if it never ran)."""
        for g in self.gates:
            if g.name == name:
                return g
        raise KeyError(f"no gate named {name!r} in this decision")

    def to_dict(self) -> dict:
        return {
            "tier": self.tier, "why": self.why,
            "gates": [g.to_dict() for g in self.gates],
            "warnings": list(self.warnings), "flags": list(self.flags),
            "cfd_allowed": self.cfd_allowed,
            "cfd_decision_worthy": self.cfd_decision_worthy,
            "fn": self.fn, "re": self.re,
            "lwl_m": self.lwl_m, "speed_ms": self.speed_ms,
            "sigma_multiplier": self.sigma_multiplier,
            "sigma_floor_frac": self.sigma_floor_frac,
            "expected_correction_frac": self.expected_correction_frac,
            "expected_correction_basis": self.expected_correction_basis,
            "worthiness_bar": WH_PER_NM_SIGMA_PRODUCT,
        }


# --------------------------------------------------------------------------
# the minimal, honest estimators gate 0 needs and this tree did not have
# --------------------------------------------------------------------------
def _pos(v) -> float | None:
    """A finite POSITIVE number, or None. Never raises, never coerces junk."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f > 0.0 else None


def _nonneg(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) and f >= 0.0 else None


def deep_water_wavelength_m(period_s: float) -> float:
    """lambda = g T^2 / (2 pi) — the deep-water dispersion relation (§7).

    ~1.56 T^2 at standard gravity, which is the form §7 quotes.
    """
    return _G * float(period_s) ** 2 / (2.0 * math.pi)


def orbital_velocity_ms(wave_height_m: float, period_s: float) -> float:
    """Surface orbital speed of a deep-water wave: u = pi H / T.

    BASIS [THY]: a deep-water particle traverses a circle of diameter H once
    per period, so u = (2 pi / T)(H / 2) = pi H / T. Airy theory, surface,
    deep water — no shoaling, no Stokes drift, no directional spreading. It is
    used here for ONE ratio (u vs 0.5 V, §16 gate 0) and must not be read as a
    seakeeping quantity; `navalai.waves`/`seakeeping` own the response.
    CROSS-CHECK: sea state 3 (H 0.9 m, T 5 s) gives 0.565 m/s against the
    0.57 m/s the study quotes in §1.
    """
    return math.pi * float(wave_height_m) / float(period_s)


def windage_force_n(lateral_area_m2: float,
                    wind_speed_ms: float | None = None,
                    pressure_pa: float | None = None) -> tuple[float, str]:
    """The h_w-style windage force on a DECLARED lateral area: (force, basis).

    TWO BASES, both named, neither invented here:

    * a declared WIND SPEED -> the bluff-body form this tree already uses for
      the mooring load, `dynamics.mooring`:
          F = 0.5 * RHO_AIR * CD_LATERAL * A * V_wind^2
      with `dynamics.RHO_AIR` (1.225, ISA sea level) and `dynamics.CD_LATERAL`
      (1.0, bluff-body lateral, approx) IMPORTED, not retyped.
    * no wind speed -> the declared RULE PRESSURE that `mission.WindageSpec`
      already carries (NZ Part 40A App.1 cl 1.2(8)(d)(ii): 500/450/350 Pa,
      defaulting to the strictest row):
          F = p * A
      500 Pa is a design gale — 0.5 * 1.225 * V^2 = 500 at V = 28.6 m/s — so
      this basis answers "in the design wind", not "at cruise", and the receipt
      says which was used.

    HONESTY ON THE Cd. The study's own §1 anchor quotes 2-3 N on 0.05-0.15 m^2
    at 10 m/s, which implies Cd 0.33-0.65 (a streamlined sensor mast); this
    tree's declared bluff-body 1.0 gives 6.1 N on 0.10 m^2, i.e. ~2x larger.
    That error is in the TRIPPING direction for a gate whose job is to notice
    an environment-dominated budget, and 1.0 is the number this repository
    already declares for lateral windage. Using a second, flattering Cd here
    would be the defect `dynamics.RHO_AIR`'s own comment warns about.
    """
    a = float(lateral_area_m2)
    if wind_speed_ms is not None:
        v = float(wind_speed_ms)
        return (0.5 * _RHO_AIR * _CD_LATERAL * a * v * v,
                f"0.5 * rho_air {_RHO_AIR} * Cd {_CD_LATERAL} * A {a:.4g} m^2 "
                f"* V_wind {v:.4g} m/s ^2 (dynamics.mooring's bluff-body form)")
    p = float(pressure_pa if pressure_pa is not None else 500.0)
    return (p * a,
            f"p {p:.4g} Pa * A {a:.4g} m^2 (the declared WindageSpec rule "
            f"pressure, NZ Part 40A App.1 cl 1.2(8)(d)(ii))")


def wave_share_estimate(fn: float, lwl_m: float) -> tuple[float, str]:
    """Wave share of total resistance, from §5's MEASURED grid: (share, basis).

    Interpolated linearly in log10(LWL) between the measured lengths and
    linearly in Fn between the two measured columns (0.25, 0.35), with §5's
    stated <=5% bound anchoring Fn 0.20. CLAMPED at both ends of the Fn axis
    rather than extrapolated: the grid stops at Fn 0.35 and inventing a
    hump-region share above it would be exactly the fabrication this ladder
    refuses everywhere else.
    """
    ell = max(min(float(lwl_m), WAVE_SHARE_MEASURED[-1][0]),
              WAVE_SHARE_MEASURED[0][0])
    lg = math.log10(ell)
    s25 = s35 = None
    for (l0, a0, b0), (l1, a1, b1) in zip(WAVE_SHARE_MEASURED,
                                          WAVE_SHARE_MEASURED[1:]):
        if l0 <= ell <= l1:
            t = ((lg - math.log10(l0)) / (math.log10(l1) - math.log10(l0)))
            s25, s35 = a0 + t * (a1 - a0), b0 + t * (b1 - b0)
            break
    if s25 is None:                      # only reachable at the exact ends
        s25, s35 = WAVE_SHARE_MEASURED[-1][1], WAVE_SHARE_MEASURED[-1][2]
    f = float(fn)
    if f <= FN_ANALYTICAL_MAX:
        share = WAVE_SHARE_BELOW_FN_020
        band = f"Fn <= {FN_ANALYTICAL_MAX} (SMALL-CRAFT-REGIMES.md §5's <=5% bound)"
    elif f <= 0.25:
        t = (f - FN_ANALYTICAL_MAX) / (0.25 - FN_ANALYTICAL_MAX)
        share = WAVE_SHARE_BELOW_FN_020 + t * (s25 - WAVE_SHARE_BELOW_FN_020)
        band = f"interpolated Fn {FN_ANALYTICAL_MAX}..0.25"
    elif f <= 0.35:
        t = (f - 0.25) / 0.10
        share = s25 + t * (s35 - s25)
        band = "interpolated Fn 0.25..0.35"
    else:
        share = s35
        band = "CLAMPED at the grid's last measured column, Fn 0.35"
    return float(share), (f"§5 measured wave share at LWL {ell:.3g} m, {band} "
                          f"-> {share:.3f}")


# --------------------------------------------------------------------------
# the gates
# --------------------------------------------------------------------------
def _gate_environment(lwl_m, speed_ms, hull_resistance_n, sea_state,
                      wave_height_m, wave_period_s, lateral_area_m2,
                      wind_speed_ms, wind_pressure_pa) -> GateOutcome:
    """Gate 0 (§16): can calm-water refinement change the decision AT ALL?"""
    detail: list[str] = []
    undecided: list[str] = []
    tripped: list[tuple[str, float, str]] = []

    # --- the declared seaway ------------------------------------------------
    hs, tp = wave_height_m, wave_period_s
    if (hs is None or tp is None) and sea_state is not None:
        try:
            ss = int(sea_state)
        except (TypeError, ValueError):
            ss = None
        if ss is None or ss not in SEA_STATE_HS_T:
            detail.append(
                f"sea_state {sea_state!r} is outside the tabulated band "
                f"{min(SEA_STATE_HS_T)}..{max(SEA_STATE_HS_T)} "
                f"(SMALL-CRAFT-REGIMES.md §7); Hs/T NOT fabricated for it")
            undecided.append("wave height/period for the declared sea state")
        else:
            row_hs, row_tp = SEA_STATE_HS_T[ss]
            hs = row_hs if hs is None else hs
            tp = row_tp if tp is None else tp
            detail.append(f"sea state {ss} -> Hs {row_hs} m, "
                          f"T {row_tp if row_tp is not None else 'n/a'} s "
                          f"(§7's bands)")

    # (a) wave-follower: lambda / L
    lam_over_l = None
    if hs is not None and float(hs) == 0.0:
        detail.append("declared sea state 0 (calm): no wave environment, so "
                      "neither lambda/L nor an orbital velocity exists")
    elif tp is not None and lwl_m is not None:
        lam = deep_water_wavelength_m(tp)
        lam_over_l = lam / lwl_m
        detail.append(
            f"lambda/L = {lam:.3g} m / {lwl_m:.3g} m = {lam_over_l:.3g} "
            f"(bar {LAMBDA_OVER_LWL_WAVE_FOLLOWER}; lambda = g T^2 / 2 pi)")
        if lam_over_l > LAMBDA_OVER_LWL_WAVE_FOLLOWER:
            tripped.append(("lambda_over_lwl", lam_over_l,
                            f"lambda/L {lam_over_l:.3g} > "
                            f"{LAMBDA_OVER_LWL_WAVE_FOLLOWER}: the hull is a "
                            f"WAVE-FOLLOWER — it rides the surface and sees "
                            f"the local slope as gravity (§7)"))
    else:
        undecided.append("a declared wave period (or sea state) and LWL for "
                         "lambda/L")

    # (b) windage vs hull resistance
    ratio_w = None
    if lateral_area_m2 is None:
        undecided.append("a declared windage lateral area "
                         "(mission.windage.lateral_area_m2) for windage/R")
    elif hull_resistance_n is None:
        undecided.append("the hull resistance at this speed for windage/R")
    else:
        fw, basis = windage_force_n(lateral_area_m2, wind_speed_ms,
                                    wind_pressure_pa)
        ratio_w = fw / hull_resistance_n
        detail.append(f"windage/R = {fw:.4g} N / {hull_resistance_n:.4g} N = "
                      f"{ratio_w:.3g} (bar {WINDAGE_OVER_RESISTANCE_MAX}; "
                      f"{basis})")
        if ratio_w > WINDAGE_OVER_RESISTANCE_MAX:
            tripped.append(("windage_over_resistance", ratio_w,
                            f"windage/hull-resistance {ratio_w:.3g} > "
                            f"{WINDAGE_OVER_RESISTANCE_MAX}: the energy "
                            f"budget is environmental, not hydrodynamic (§1)"))

    # (c) orbital velocity vs boat speed
    ratio_u = None
    if hs is not None and tp is not None and speed_ms is not None:
        u = orbital_velocity_ms(hs, tp)
        ratio_u = u / speed_ms
        detail.append(f"u_orbital/V = {u:.3g} / {speed_ms:.3g} = "
                      f"{ratio_u:.3g} (bar {ORBITAL_OVER_SPEED_MAX}; "
                      f"u = pi H / T)")
        if ratio_u >= ORBITAL_OVER_SPEED_MAX:
            tripped.append(("u_orbital_over_speed", ratio_u,
                            f"orbital velocity is {ratio_u:.3g} of the boat "
                            f"speed (bar {ORBITAL_OVER_SPEED_MAX}): the water "
                            f"moves as fast as the boat (§1/§8)"))
    elif not (hs is not None and float(hs) == 0.0):
        undecided.append("a declared wave height and period (or sea state) "
                         "and a speed for u_orbital/V")

    if tripped:
        measure, value, why = max(tripped, key=lambda t: t[1] / (
            LAMBDA_OVER_LWL_WAVE_FOLLOWER if t[0] == "lambda_over_lwl"
            else WINDAGE_OVER_RESISTANCE_MAX
            if t[0] == "windage_over_resistance" else ORBITAL_OVER_SPEED_MAX))
        return GateOutcome(
            GATE_ENVIRONMENT, OUT_ROUTE, measure, value,
            f"{why} — calm-water refinement cannot change the decision",
            tier_cap=TIER_ANALYTICAL, bars_cfd=True, detail=tuple(detail))
    if undecided:
        return GateOutcome(
            GATE_ENVIRONMENT, OUT_CANNOT_DECIDE, "environment", None,
            "the environment gate CANNOT be decided: nothing declares "
            + "; ".join(undecided) + ". An undeclared environment is NOT a "
            "quiet 'the environment is fine' — it is nobody having said",
            detail=tuple(detail))
    return GateOutcome(
        GATE_ENVIRONMENT, OUT_CLEAR, "environment",
        lam_over_l if lam_over_l is not None else ratio_w,
        "the declared environment does not dominate the calm-water budget: "
        + "; ".join(detail), detail=tuple(detail))


def _gate_wave_existence(speed_ms) -> GateOutcome:
    """Gate 1 (§6): does a steady wave system exist, and is it clean?"""
    if speed_ms is None:
        return GateOutcome(
            GATE_WAVE_EXISTENCE, OUT_CANNOT_DECIDE, "V", None,
            "no speed given, so whether a wave system exists cannot be said")
    v = float(speed_ms)
    if v < C_MIN_GRAVITY_CAPILLARY_MS:
        return GateOutcome(
            GATE_WAVE_EXISTENCE, OUT_ROUTE, "V", v,
            f"V {v:.3g} m/s < c_min {C_MIN_GRAVITY_CAPILLARY_MS} m/s (the "
            f"gravity-capillary phase-speed minimum): NO steady wave system "
            f"exists at any wavelength, so a wave-resistance number here is "
            f"fiction, not an approximation (§6)",
            tier_cap=TIER_ANALYTICAL, bars_cfd=True)
    if v < WAVE_CAPILLARY_CLEAN_MS:
        lam_t = 2.0 * math.pi * v * v / _G
        return GateOutcome(
            GATE_WAVE_EXISTENCE, OUT_BAR, "V", v,
            f"V {v:.3g} m/s < {WAVE_CAPILLARY_CLEAN_MS} m/s: transverse "
            f"wavelength lambda_t = 2 pi V^2/g = {lam_t*100:.1f} cm against "
            f"the capillary lambda_m ~1.7 cm, so the wave prediction is "
            f"CAPILLARY-CONTAMINATED and Michell (pure gravity) misprices it. "
            f"CFD never, here (§6/§15)",
            bars_cfd=True)
    return GateOutcome(
        GATE_WAVE_EXISTENCE, OUT_CLEAR, "V", v,
        f"V {v:.3g} m/s >= {WAVE_CAPILLARY_CLEAN_MS} m/s: a gravity wave "
        f"system exists and is not capillary-contaminated "
        f"(lambda_t = {2.0*math.pi*v*v/_G*100:.1f} cm)")


def _gate_friction(re, transition_modelled: bool) -> GateOutcome:
    """Gate 2 (§16, seam `limits.RE_TRANSITION_BAND`): the drone blocker."""
    if re is None:
        return GateOutcome(
            GATE_FRICTION_REGIME, OUT_CANNOT_DECIDE, "Re", None,
            "no Reynolds number (needs a positive LWL and speed), so which "
            "friction line applies cannot be said — and an unknown regime is "
            "not a turbulent one")
    if re < RE_TRANSITION_ONSET:
        return GateOutcome(
            GATE_FRICTION_REGIME, OUT_ROUTE, "Re", re,
            f"Re {re:.3g} < {RE_TRANSITION_ONSET:.0e}: the boundary layer is "
            f"LAMINAR and ITTC-57 does not describe it at all. Blasius with a "
            f"x{LAMINAR_SIGMA_MULTIPLIER:g} friction margin, ANALYTICAL only; "
            f"CFD REFUSED — no correlation data exists at this Re and the "
            f"precision would be unusable anyway (§15/§16)",
            tier_cap=TIER_ANALYTICAL, bars_cfd=True)
    if re < RE_FULLY_TURBULENT:
        lo, hi = TRANSITIONAL_SIGMA_BAND
        base = (f"Re {re:.3g} is inside the transition band "
                f"[{RE_TRANSITION_ONSET:.0e}, {RE_FULLY_TURBULENT:.0e}): "
                f"ITTC-57 is a FULLY TURBULENT correlation read outside its "
                f"regime, so the empirical sigma widens to the study's "
                f"+-{lo:.0%}..{hi:.0%} band (§15/§17 — a transitional line, "
                f"once built, tightens it to ~+-15%)")
        if transition_modelled:
            return GateOutcome(
                GATE_FRICTION_REGIME, OUT_BAR, "Re", re,
                base + ". CFD is ADMITTED only because the caller declared a "
                       "transition-modelled, validated run",
                bars_cfd=False)
        return GateOutcome(
            GATE_FRICTION_REGIME, OUT_BAR, "Re", re,
            base + ". CFD is BARRED: a fully-turbulent RANS reproduces "
                   "ITTC-57's own bias here — higher cost, same wrongness "
                   "(§20 row 6). Declare a transition-modelled run to lift it",
            tier_cap=TIER_EMPIRICAL, bars_cfd=True)
    return GateOutcome(
        GATE_FRICTION_REGIME, OUT_CLEAR, "Re", re,
        f"Re {re:.3g} >= {RE_FULLY_TURBULENT:.0e}: ITTC-57 is inside the "
        f"fully-turbulent flow it correlates")


def _gate_froude(fn, lwl_m, bl_ratio) -> tuple[GateOutcome, str | None, bool]:
    """Gate 3 (§15/§16, seam `resistance.FN_MICHELL_MAX`).

    Returns (receipt, proposed tier, necessity) where `necessity` marks a tier
    that is not an upgrade but the ONLY honest answer — the flag that turns a
    later CFD bar into a REFUSE instead of a quiet downgrade.
    """
    if fn is None:
        return (GateOutcome(
            GATE_FROUDE, OUT_CANNOT_DECIDE, "Fn", None,
            "no Froude number (needs a positive LWL and speed), so no regime "
            "and no tier can be selected"), None, False)
    f = float(fn)
    if f <= FN_ANALYTICAL_MAX:
        return (GateOutcome(
            GATE_FROUDE, OUT_ROUTE, "Fn", f,
            f"Fn {f:.3f} <= {FN_ANALYTICAL_MAX}: MEASURED wave share is "
            f"<5-8% across the whole size range (§5), so L0 friction+form "
            f"matches anything fancier inside the product's own sigma — "
            f"ANALYTICAL SUFFICES",
            tier_cap=TIER_ANALYTICAL), TIER_ANALYTICAL, False)
    if f <= FN_MICHELL_MAX:
        if bl_ratio is None:
            return (GateOutcome(
                GATE_FROUDE, OUT_ROUTE, "Fn", f,
                f"Fn {f:.3f} is inside Michell's envelope "
                f"({FN_ANALYTICAL_MAX} < Fn <= {FN_MICHELL_MAX}) -> "
                f"EMPIRICAL (L1). SLENDERNESS UNDECIDED: no B/L was given, "
                f"so whether the thin-ship linearisation is strained "
                f"(B/L > {BL_MICHELL_MAX}) is NOT known and is not assumed "
                f"benign"), TIER_EMPIRICAL, False)
        if bl_ratio <= BL_MICHELL_MAX:
            return (GateOutcome(
                GATE_FROUDE, OUT_ROUTE, "Fn", f,
                f"Fn {f:.3f} inside ({FN_ANALYTICAL_MAX}, {FN_MICHELL_MAX}] "
                f"with B/L {bl_ratio:.3f} <= {BL_MICHELL_MAX}: Michell is IN "
                f"ENVELOPE (thin-ship, linearised on hull slope) -> EMPIRICAL "
                f"(L1)"), TIER_EMPIRICAL, False)
        return (GateOutcome(
            GATE_FROUDE, OUT_ROUTE, "Fn", f,
            f"Fn {f:.3f} inside ({FN_ANALYTICAL_MAX}, {FN_MICHELL_MAX}] but "
            f"B/L {bl_ratio:.3f} > {BL_MICHELL_MAX}: EMPIRICAL with the "
            f"thin-ship linearisation STRAINED — Michell degrades fast for "
            f"fuller forms (§5), so the wave half's sigma is the widened one",
            detail=("thin-ship strain: sigma widened, not refused",)),
            TIER_EMPIRICAL, False)
    if f <= FN_PLANING_ONSET:
        if lwl_m is not None and lwl_m >= LWL_CFD_FLOOR_M:
            return (GateOutcome(
                GATE_FROUDE, OUT_ROUTE, "Fn", f,
                f"Fn {f:.3f} is in ({FN_MICHELL_MAX}, {FN_PLANING_ONSET}]: "
                f"transom/trim/lift physics is absent from L1 and NO valid "
                f"empirical tier exists in this tree, so CFD is the only "
                f"honest answer — and LWL {lwl_m:.3g} m >= "
                f"{LWL_CFD_FLOOR_M} m, where RANS is demonstrated (Delft 372, "
                f"2-5% vs tank)", tier_cap=TIER_LOW_FIDELITY_CFD),
                TIER_LOW_FIDELITY_CFD, True)
        return (GateOutcome(
            GATE_FROUDE, OUT_ROUTE, "Fn", f,
            f"Fn {f:.3f} is in ({FN_MICHELL_MAX}, {FN_PLANING_ONSET}] where "
            f"no empirical tier exists, and LWL "
            f"{lwl_m if lwl_m is None else round(lwl_m, 3)} m is below the "
            f"{LWL_CFD_FLOOR_M} m floor at which RANS is demonstrated "
            f"(measured >=30% friction error at 1 m): REFUSE — there is no "
            f"tier, not a cheap one",
            tier_cap=TIER_REFUSE), TIER_REFUSE, True)
    return (GateOutcome(
        GATE_FROUDE, OUT_ROUTE, "Fn", f,
        f"Fn {f:.3f} > {FN_PLANING_ONSET}: the dynamic-lift regime. There is "
        f"NO Savitsky-class model in this tree and CFD of a planing hull is "
        f"outside everything this ladder has ever validated: REFUSE",
        tier_cap=TIER_REFUSE), TIER_REFUSE, True)


def _gate_worthiness(tier, correction, correction_basis, flip_distance,
                     cfd_allowed) -> tuple[GateOutcome, bool, bool]:
    """Gate 4 (§13/§16, seam `limits.WH_PER_NM_SIGMA_PRODUCT`).

    Returns (receipt, decision_worthy, may_upgrade_one_level).

    THE TWO CLAUSES ARE NOT THE SAME QUESTION, and conflating them is how a
    governor becomes a rubber stamp:
      * `decision_worthy` — could the correction exceed the product sigma at
        all? This is what makes a CFD request eligible.
      * `may_upgrade_one_level` — §16's literal escalation rule, which needs
        BOTH clauses, so it stays False until a caller declares how far the
        nearest verdict flip is. An undeclared flip distance never buys an
        upgrade; it is reported as undeclared.
    """
    bar = WH_PER_NM_SIGMA_PRODUCT
    if correction is None:
        return (GateOutcome(
            GATE_DECISION_WORTHINESS, OUT_CANNOT_DECIDE,
            "expected_correction_frac", None,
            f"nothing declares the expected correction a higher tier could "
            f"deliver, so it cannot be compared with the product sigma "
            f"{bar:.0%} (limits.WH_PER_NM_SIGMA_PRODUCT) — an unmeasured "
            f"correction is not a large one"), False, False)
    over = correction > bar
    flip_ok = None if flip_distance is None else (
        flip_distance < WORTHINESS_FLIP_GUARD * correction)
    parts = [f"expected correction {correction:.1%} vs the product sigma "
             f"{bar:.0%} (limits.WH_PER_NM_SIGMA_PRODUCT): "
             f"{'OVER' if over else 'UNDER'} the bar [{correction_basis}]"]
    if flip_ok is None:
        parts.append(f"the nearest verdict flip distance is NOT declared, so "
                     f"§16's second clause (flip < "
                     f"{WORTHINESS_FLIP_GUARD} x correction) is not evaluated "
                     f"— no tier is UPGRADED on an unevaluated clause")
    else:
        verdict_clause = ("a verdict could flip" if flip_ok else
                          "no verdict can flip — the correction cannot "
                          "reach one")
        parts.append(f"nearest verdict flip {flip_distance:.1%} vs "
                     f"{WORTHINESS_FLIP_GUARD} x correction "
                     f"{WORTHINESS_FLIP_GUARD * correction:.1%}: "
                     f"{verdict_clause}")
    worthy = bool(over and flip_ok is not False and cfd_allowed)
    if not cfd_allowed:
        parts.append("CFD is barred by an earlier gate, so no escalation is "
                     "on the table whatever the correction")
    upgrade = bool(over and flip_ok is True and cfd_allowed
                   and tier in (TIER_ANALYTICAL, TIER_EMPIRICAL))
    return (GateOutcome(
        GATE_DECISION_WORTHINESS,
        OUT_CLEAR if worthy else OUT_BAR,
        "expected_correction_frac", float(correction),
        "; ".join(parts), bars_cfd=not worthy), worthy, upgrade)


# --------------------------------------------------------------------------
# the governor
# --------------------------------------------------------------------------
def select_fidelity(*,
                    lwl_m: float | None = None,
                    speed_ms: float | None = None,
                    beam_wl_m: float | None = None,
                    lb_ratio: float | None = None,
                    displacement_kg: float | None = None,
                    mission=None,
                    sea_state: int | None = None,
                    wave_height_m: float | None = None,
                    wave_period_s: float | None = None,
                    windage=None,
                    wind_speed_ms: float | None = None,
                    hull_resistance_n: float | None = None,
                    rho: float = _RHO_FRESH,
                    transition_modelled: bool = False,
                    expected_correction_frac: float | None = None,
                    verdict_flip_distance_frac: float | None = None,
                    ) -> FidelityDecision:
    """Route a design to the fidelity tier that may honestly answer it.

    PURE, DETERMINISTIC, TOTAL. Every argument is optional and every missing
    one produces a NAMED "cannot decide this gate" receipt rather than an
    exception or a silent pass.

    Arguments
      lwl_m, speed_ms      the two numbers Fn and Re are made of.
      beam_wl_m, lb_ratio  either form of the slenderness fact; `lb_ratio` is
                           LWL/B (the `certify` convention) and B/L is derived
                           from whichever is given.
      displacement_kg      carried on the receipt only; no gate reads it today
                           (the cube-law wall of §8 is a SIZING doctrine, not a
                           model-admissibility gate) and this says so rather
                           than implying a check.
      mission              a `mission.MissionSpec`; `payload.sea_state` and
                           `windage` are read from it when not passed
                           explicitly. Read defensively — any object works.
      hull_resistance_n    the calm-water resistance at this speed, for gate
                           0's windage ratio. Passed in rather than computed:
                           this module owns no physics that `resistance` owns.
      transition_modelled  the caller DECLARES that a CFD run would use a
                           validated transition model. The only thing that
                           lifts gate 2's bar inside the transition band.
      expected_correction_frac, verdict_flip_distance_frac
                           gate 4's two inputs, as fractions of Wh/NM. The
                           first defaults to the §5 measured wave share when
                           the incumbent tier is ANALYTICAL (what a
                           wave-resolving tier could move is bounded by what
                           the wave term is worth); the second has no default
                           and its absence is reported, never assumed.

    MEASURED EXAMPLES (the study's own anchors, all reproduced in
    tests/test_select_fidelity.py):
      * 1 m hull at 1 m/s -> Re ~8.8e5 (fresh) -> transitional -> CFD BARRED.
      * 12 m hull at Fn 0.26 -> EMPIRICAL, and CFD-worthy when the declared
        correction clears 10%.
      * V = 0.2 m/s -> no wave system exists at all -> ANALYTICAL.
      * Fn 0.5 at 2 m -> REFUSE, because L < 3 m — not "CFD".
    """
    warnings: list[str] = []
    flags: list[str] = []

    ell = _pos(lwl_m)
    if lwl_m is not None and ell is None:
        warnings.append(f"lwl_m = {lwl_m!r} is not a positive finite length; "
                        f"treated as UNKNOWN, not as zero")
    u = _pos(speed_ms)
    if speed_ms is not None and u is None:
        warnings.append(f"speed_ms = {speed_ms!r} is not a positive finite "
                        f"speed; treated as UNKNOWN, not as zero")
    r_hull = _pos(hull_resistance_n)

    # slenderness, as B/L — the form Michell's envelope is stated in (§5).
    bl = None
    if lb_ratio is not None:
        lbv = _pos(lb_ratio)
        bl = (1.0 / lbv) if lbv else None
    elif beam_wl_m is not None and ell is not None:
        b = _pos(beam_wl_m)
        bl = (b / ell) if b else None

    # the declared environment, from the mission when not passed explicitly
    if sea_state is None and mission is not None:
        sea_state = getattr(getattr(mission, "payload", None),
                            "sea_state", None)
    if windage is None and mission is not None:
        windage = getattr(mission, "windage", None)
    lateral_area = _pos(getattr(windage, "lateral_area_m2", None))
    wind_pressure = None
    if windage is not None:
        try:
            wind_pressure = windage.pressure_pa()
        except (AttributeError, TypeError, ValueError):
            wind_pressure = _pos(getattr(windage, "wind_pressure_pa", None))
    hs = _nonneg(wave_height_m)
    tp = _pos(wave_period_s)

    # Fn and Re come from the EXISTING seam, `resistance.flow_regime`, so this
    # module cannot disagree with the ladder about which regime a hull is in.
    fn = re = None
    if ell is not None and u is not None:
        fr = flow_regime(u, ell, rho)
        fn, re = float(fr.fn), float(fr.re)

    g0 = _gate_environment(ell, u, r_hull, sea_state, hs, tp, lateral_area,
                           _pos(wind_speed_ms), wind_pressure)
    g1 = _gate_wave_existence(u)
    g2 = _gate_friction(re, transition_modelled)
    g3, proposed, necessity = _gate_froude(fn, ell, bl)

    if g0.outcome == OUT_ROUTE:
        flags.append("ENERGY_BUDGET_IS_ENVIRONMENTAL")
    if g0.outcome == OUT_CANNOT_DECIDE:
        warnings.append(g0.why)
    if g1.outcome == OUT_ROUTE:
        flags.append("WAVE_SYSTEM_ABSENT")
    elif g1.outcome == OUT_BAR:
        flags.append("WAVE_CAPILLARY_CONTAMINATED")
    elif g1.outcome == OUT_CANNOT_DECIDE:
        warnings.append(g1.why)

    sigma_multiplier, sigma_floor = 1.0, None
    if g2.outcome == OUT_ROUTE:                    # laminar
        flags.append("FRICTION_LAMINAR")
        sigma_multiplier = LAMINAR_SIGMA_MULTIPLIER
    elif g2.outcome == OUT_BAR:                    # transitional
        flags.append("FRICTION_TRANSITIONAL")
        sigma_floor = TRANSITIONAL_SIGMA_FLOOR
    elif g2.outcome == OUT_CANNOT_DECIDE:
        warnings.append(g2.why)
    if g3.outcome == OUT_CANNOT_DECIDE:
        warnings.append(g3.why)

    # --- resolve the tier -------------------------------------------------
    # A gate never RAISES the tier; it caps it. The answer is the cheapest
    # tier any gate insists on, and the gate credited in `why` is the EARLIEST
    # one that demands it — gate order is the study's order of precedence.
    ladder = (g0, g1, g2, g3)
    caps = [g for g in ladder if g.tier_cap is not None]
    cfd_allowed = not any(g.bars_cfd for g in ladder)

    if any(g.tier_cap == TIER_REFUSE for g in ladder):
        decider = next(g for g in ladder if g.tier_cap == TIER_REFUSE)
        tier, why = TIER_REFUSE, f"{decider.name}: {decider.why}"
    elif proposed is None:
        # Nothing could be routed. That is a REFUSAL to select, not a default
        # to the cheapest tier: an unknown hull is not a slow one.
        tier = TIER_REFUSE
        why = (f"{GATE_FROUDE}: {g3.why} — no tier is selected when the "
               f"governor was not told enough to select one")
        warnings.append("select_fidelity was given too little to route: "
                        "REFUSE here means 'undecidable', and the gate "
                        "receipts name every input that was missing")
    else:
        rank = min([_RANK[proposed]]
                   + [_RANK[g.tier_cap] for g in caps
                      if g.tier_cap in _RANK])
        tier = _BY_RANK[rank]
        if rank < _RANK[proposed] and necessity:
            # The cheaper tier is CAPPED, but gate 3 said no cheaper tier is
            # VALID. Downgrading here would hand back a number from a model
            # that has already been ruled out; the honest answer is that this
            # tree has nothing to say.
            decider = next(g for g in caps if _RANK.get(g.tier_cap, 99) == rank)
            tier = TIER_REFUSE
            why = (f"{decider.name}: {decider.why} — and {GATE_FROUDE} says "
                   f"no cheaper tier is VALID here ({g3.why}), so there is no "
                   f"tier left: REFUSE")
        else:
            decider = next((g for g in ladder
                            if g.tier_cap == tier
                            or (g is g3 and proposed == tier)), g3)
            why = f"{decider.name}: {decider.why}"

    # --- gate 4 -----------------------------------------------------------
    correction, basis = expected_correction_frac, "declared by the caller"
    if correction is not None and _nonneg(correction) is None:
        warnings.append(f"expected_correction_frac = "
                        f"{expected_correction_frac!r} is not a finite "
                        f"non-negative fraction; treated as UNDECLARED")
        correction = None
    if correction is None and tier == TIER_ANALYTICAL and fn is not None \
            and ell is not None:
        correction, basis = wave_share_estimate(fn, ell)
    elif correction is None:
        basis = "not established"

    g4, worthy, upgrade = _gate_worthiness(
        tier, correction, basis, _nonneg(verdict_flip_distance_frac),
        cfd_allowed and tier != TIER_REFUSE)

    if upgrade and tier in (TIER_ANALYTICAL, TIER_EMPIRICAL):
        target = _BY_RANK[_RANK[tier] + 1]
        cap_rank = min([_RANK[g.tier_cap] for g in caps
                        if g.tier_cap in _RANK] or [_RANK[TIER_FULL_CFD]])
        if _RANK[target] <= cap_rank:
            tier = target
            why = (f"{GATE_DECISION_WORTHINESS}: {g4.why} — §16's escalation "
                   f"clause upgrades ONE level, to {target}")
        else:
            warnings.append(
                f"the worthiness gate would upgrade to {target}, but an "
                f"earlier gate caps this design at {_BY_RANK[cap_rank]}")

    return FidelityDecision(
        tier=tier, why=why, gates=(g0, g1, g2, g3, g4),
        warnings=tuple(warnings), flags=tuple(flags),
        cfd_allowed=bool(cfd_allowed and tier != TIER_REFUSE),
        cfd_decision_worthy=bool(worthy),
        fn=fn, re=re, lwl_m=ell, speed_ms=u,
        sigma_multiplier=sigma_multiplier, sigma_floor_frac=sigma_floor,
        expected_correction_frac=(None if correction is None
                                  else float(correction)),
        expected_correction_basis=basis)
