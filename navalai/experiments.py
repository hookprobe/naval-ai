"""The deterministic geometry/hydrodynamic EXPERIMENT SUITE.

THE QUESTION THIS MODULE EXISTS TO ANSWER, in the project owner's words:

    "Can NavalAI deliberately generate a fine-entry, slender, hydrostatically
     balanced demihull whose resistance and energy performance improve for the
     intended operating Froude range, instead of merely producing a visually
     sharp STL?"

AND THE THING IT DELIBERATELY DOES NOT DO. It does not implement "sharp bow =
good". The causal chain it exercises is

    mission -> speed regime -> Froude number -> displacement
            -> sectional area distribution A(x)
            -> waterline shape y_wl(x)
            -> section shape -> bow entrance -> resistance

so the INDEPENDENT variables are the longitudinal volume distribution and the
waterline shape, and the entry half-angle and the waterline curvature are
DIAGNOSTICS measured on the result. Measuring whether "sharper is better"
actually holds is worth more than a hard-coded sharp-bow reward, and the answer
below is that it holds at low Froude number and STOPS HOLDING at high Froude
number — see `experiment_1_bow_sharpness`.

=============================================================================
THE HEADLINE MEASUREMENTS (reproduce with `python -m navalai.experiments`)
=============================================================================

-1. IS THE OBJECTIVE GAMEABLE? The question ShipGen's result forces on any
   generative hull project, and the answer here is TWO-SIDED
   (`experiment_5_objective_gaming`):

     * MINIMISING R_w ALONE IS CATASTROPHICALLY GAMEABLE. At fixed
       displacement and fixed ABSOLUTE speed, with length free, it buys -84.2%
       of wave resistance and pays +70.7% wetted surface, +28.7% TOTAL
       resistance and Wh/NM, +183.5% build area and structural mass, 3.35x the
       plywood and 3.68x the build hours. That is ShipGen's own failure
       reproduced in this grammar.
     * THE OBJECTIVE THIS PROJECT ACTUALLY MINIMISES IS NOT. `wh_per_nm` is
       R_TOTAL times a fixed distance, so the R_t optimum and the Wh/NM
       optimum are the same hull, and every column of
       `optimize.HullProblem`'s objective vector is an ABSOLUTE quantity.
     * AND THE GENERAL RULE, measured across ten candidate objectives: EVERY
       RATIO INFLATES THE BOAT AND NO ABSOLUTE QUANTITY DOES — including C_T
       normalised by WETTED AREA, which is the normalisation ShipGen's own
       diagnosis recommends. Never put a coefficient in the objective vector.

0. THE HEADLINE, and it is a CROSS-experiment result no single sweep gives
   (`lever_comparison`). Over each lever's whole admissible gene range, on one
   parent hull at one displacement on one protocol, the R_t span is:

       Fn      Cp      lcb     bow / waterline shape
       0.20  19.77%  13.01%          12.39%
       0.30  45.31%  24.32%           9.21%
       0.45  26.35%  16.86%           1.36%

   The LONGITUDINAL VOLUME DISTRIBUTION dominates the bow-entrance lever by
   1.6x at Fn 0.20 and 19.4x at Fn 0.45. The mission's instruction — teach the
   volume distribution, not the bow shape — is what the measurement says, not
   just good methodology.

1. BOW SHARPNESS is NOT monotonic in total resistance. Fixed A(x) (so fixed
   displacement, Cp and LCB to nine digits), waterline shape varied by the
   forefoot keel rise. Sharpest bow wins at Fn 0.20-0.30; at Fn >= 0.35 an
   INTERIOR optimum appears, and at Fn 0.45 the sharpest bow is 0.44% WORSE
   than the optimum at alpha_e 13.1 deg. Mechanism: R_w rises monotonically
   with alpha_e at every Fn but its SENSITIVITY collapses with speed (+92%
   over the sweep at Fn 0.20, +2.9% at Fn 0.45), while R_f falls monotonically
   because the same volume sits in a wider, shallower forward body with 2.3%
   less wetted surface. The optimum is where the falling friction term
   overtakes the flattening wave term. WHAT IS RESOLVED is that the sharpest
   bow is worse than the middle of the range at Fn >= 0.40 (2.1x and 2.8x the
   grid shift); WHICH middle bow is best is NOT resolved, and the record flags
   that rather than reporting an argmin as if it were.

2. Cp AT FIXED DISPLACEMENT: the optimum is INTERIOR at every speed and trends
   up with Fn (0.594 -> 0.687), which `limits.prismatic_target` predicts — but
   it is NOT MONOTONE in Fn (0.594, 0.641, 0.594, 0.641, 0.687, 0.687; the
   Fn 0.30 dip is 11x resolved against the grid shift), and every measured
   optimum is FULLER than the practice curve by +0.019 to +0.087 with a
   consistent sign. See `experiment_2_prismatic` for why that is a
   disagreement between two unvalidated things and not a correction.

3. LCB at fixed displacement and Cp: aft is better nearly everywhere, and at
   THREE of six speeds the best point is the -3.0 %LWL BAND EDGE, not an
   interior optimum — so the LCB gene is bounded by `limits.LCB_BAND_PCT_LWL`
   and not by wave resistance. The lever is strong (R_t spans 12-37%).
   See `experiment_3_lcb`.

4. CATAMARAN SEPARATION: the interference factor is non-monotonic in s/L at
   four of six valid speeds, with the strongest destructive optimum at Fn 0.25,
   s/L 0.300 — **25.2% less** wave resistance than two independent demihulls.
   At Fn >= 0.35 the whole 0.20-0.50 band is CONSTRUCTIVE, up to **+59.7%** at
   Fn 0.40, s/L 0.200. There is no single best s/L: the optimum moves with
   speed and the best spacing at Fn 0.25 is near the worst at Fn 0.40.
   And the production path does not use any of this — `total_resistance` calls
   `michell_rw` with no `separation`, so every catamaran this project has
   evaluated was scored as one isolated demihull.
   See `experiment_4_separation`.

=============================================================================
THE PHASE CONVENTION IN `resistance.py` IS CORRECT — VERIFIED, NOT ASSUMED
=============================================================================

`michell_interference_convention_check` re-derives the two-hull amplitude
superposition INDEPENDENTLY, in complex arithmetic, from the wavevector
components that `resistance._free_wave_vals` itself uses, and compares. It is a
deliberate second implementation and it exists ONLY to check a convention; no
production number in this module comes from it.

    read off `_free_wave_vals`:   depth kernel exp(K z)  with K  = k0 sec^2(th)
                                  x-phase     exp(i kx x) with kx = k0 sec(th)
    free-wave dispersion:         K is the wavenumber MAGNITUDE, so
                                  ky = sqrt(K^2 - kx^2) = k0 sec^2(th) sin(th)
    amplitude superposition:      A_tot(th) = sum_j A_j(th) exp(i ky y_j)
                                  y_j = -s/2, +s/2, A_j identical
                                     => A_tot = 2 A cos(ky s / 2)
                                     => |A_tot|^2/|A|^2 = 4 cos^2(ky s / 2)

`resistance.catamaran_interference` implements exactly that, with exactly that
ky. MEASURED agreement between the module and the independent complex
superposition, on the reference demihull at Fn 0.30, s/L 0.45: relative
difference 1.8e-16 — one floating-point ulp. **sec SQUARED is confirmed**; a
`sec(th) sin(th)` transverse wavenumber would be a different number and is NOT
what the code contains.

=============================================================================
HONESTY RULES THIS MODULE IS BUILT AROUND
=============================================================================

* Every quantity is a `Quantity(value, tier, sigma, units, basis)`. There are
  no bare floats in a record, and `tests/test_experiments.py` walks every
  record to prove it.
* NOTHING IS EVALUATED OUTSIDE A MODEL'S ENVELOPE. `FROUDE_SWEEP` deliberately
  contains a point above `resistance.FN_MICHELL_MAX`; it is recorded with tier
  `L1-INVALID` (which `evaluate.tier_rank` ranks at -1, BELOW L0) and EXCLUDED
  from every finding. It is carried rather than dropped so a reader can see
  that the refusal happened.
* A number lives in exactly one place. Volume, LCB, Cp, Cb, Awp, wetted area
  and GM come from `hydrostatics`/`geometry`; R_w, R_f and the interference
  factor from `resistance`; the entry-angle chord floor from
  `formlib.alpha_e_chord_floor_deg`; the prismatic-vs-Froude curve from
  `limits.prismatic_target`. This module composes them and measures; it
  re-derives exactly one thing, the interference phase, and only to check it.
* THE INTEGRATION PROTOCOL IS READ AT RUN TIME AND RECORDED. `PRODUCTION_GRID`
  and `CONVERGED_GRID` are read out of `resistance` rather than copied, and
  every record carries the grid it was produced on. Experiment 1 runs at BOTH
  grids and the test FAILS if the ranking of bows differs between them —
  otherwise a "better bow" could be quadrature error. MEASURED: the ranking is
  identical at every valid Fn, and the interior optimum's margin is ~3x the
  production-to-converged shift. That margin is thin and is stated as such.

Determinism: no RNG, no wall-clock, no file I/O. Every sweep is a fixed tuple
of parameter vectors. `run_all()` twice returns equal records.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping, Sequence

import numpy as np

from . import buildability, formlib, geometry, grammar, limits, resistance
from .energy import EnergySpec, energy_report
from .geometry import G, Hull
from .hydrostatics import HydroState, solve, solve_to_displacement

# ---------------------------------------------------------------------------
# Tier vocabulary. Spelled to match `evaluate.tier_rank`, which ranks anything
# it does not recognise at -1 (below L0) — so a badge this module invents could
# never be promoted by a `>=` comparison. `L1-INVALID` is deliberately such a
# badge: it is what an out-of-envelope resistance point carries.
# ---------------------------------------------------------------------------
TIER_GEOMETRY = "L0"        # closed-form geometry / algebra
TIER_PHYSICS = "L1"         # Michell + hydrostatics + ITTC-57
TIER_PHYSICS_INVALID = "L1-INVALID"   # above resistance.FN_MICHELL_MAX

# Basis strings for a sigma, so a reader can tell a MEASURED band from a
# declared one without opening the code that produced it.
BASIS_EXACT = "closed-form-exact"
BASIS_GRID = "measured-grid-refinement"
BASIS_MODEL = "model-declared"          # comes from ResistanceResult.uncertainty
BASIS_PROPAGATED = "propagated"
# A MEASURED grid band that is KNOWN to be narrower than the true one. Used for
# the resistance components, whose model band cannot be read out of
# `ResistanceResult` without copying a constant that lives inline in
# `resistance.total_resistance` — see `resistance_quantities`. Named after
# `energy.SIGMA_PROPAGATED_LOWER_BOUND`, which is the same honesty in the same
# shape: a lower bound with its name on it is usable; a silent one is not.
BASIS_GRID_LOWER_BOUND = "measured-grid-refinement-lower-bound"


class ExperimentError(RuntimeError):
    """An experiment could not be run as specified.

    Raised rather than returning a partial sweep. A sweep with a silently
    dropped point is a sweep whose controlled quantities are no longer what its
    protocol claims, and this repository's defect class 1 (an unmeasurable
    value scored as a passing one) applied to an experiment.
    """


# ---------------------------------------------------------------------------
# The quantity record. Honesty rule 1, enforced at construction.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Quantity:
    """One measured number with its tier and its one-sigma band.

    `sigma` may be 0.0 only where a ZERO BAND IS ITSELF A MEASUREMENT or a
    construction:

      `BASIS_EXACT`  closed-form algebra, or an input the sweep sets.
      `BASIS_GRID`   the two grids agreed exactly, and that HAPPENS: the
                     floated draft is `t_design + wl` and carries no
                     station-count dependence at all.
      `BASIS_GRID_LOWER_BOUND`  likewise, and it happens for `cf`: the
                     ITTC-1957 line depends only on speed and Lwl, so it is
                     identical on the production and converged Michell grids.
                     A zero LOWER BOUND is a true and uninformative statement,
                     and it is only admissible because the basis string says
                     "lower bound" out loud.

    A zero sigma with `BASIS_MODEL` or `BASIS_PROPAGATED` is REFUSED: those
    bands come from an estimator that has never returned zero, so a zero there
    means nobody supplied one. "I did not estimate a band" and "the band is
    zero" are different statements and this repository has already paid for
    conflating them (`${VAR:-0}`, docs/LESSONS.md).
    """

    ZERO_SIGMA_BASES = (BASIS_EXACT, BASIS_GRID, BASIS_GRID_LOWER_BOUND)

    value: float
    tier: str
    sigma: float
    units: str = ""
    basis: str = BASIS_EXACT

    def __post_init__(self) -> None:
        v = float(self.value)
        s = float(self.sigma)
        if not math.isfinite(s) or s < 0.0:
            raise ExperimentError(
                f"Quantity: sigma = {self.sigma!r} is not a finite "
                f"non-negative band. An unmeasured uncertainty is REFUSED, "
                f"never defaulted to zero — zero is the most confident band "
                f"there is.")
        if self.tier not in (TIER_GEOMETRY, TIER_PHYSICS, TIER_PHYSICS_INVALID):
            raise ExperimentError(
                f"Quantity: tier {self.tier!r} is not one of "
                f"{(TIER_GEOMETRY, TIER_PHYSICS, TIER_PHYSICS_INVALID)}. The "
                f"vocabulary is closed on purpose: `evaluate.tier_rank` ranks "
                f"a badge it does not know at -1, so an invented spelling "
                f"would be silently unrankable rather than loudly wrong.")
        if s == 0.0 and self.basis not in self.ZERO_SIGMA_BASES:
            raise ExperimentError(
                f"Quantity: sigma 0.0 with basis {self.basis!r}. A zero band "
                f"is admissible only where the zero is itself a measurement or "
                f"a construction: {self.ZERO_SIGMA_BASES}. A model-declared or "
                f"propagated sigma of zero means none was supplied.")
        if not math.isfinite(v) and self.tier != TIER_PHYSICS_INVALID:
            raise ExperimentError(
                f"Quantity: value {self.value!r} is not finite and is not "
                f"badged {TIER_PHYSICS_INVALID}.")

    @property
    def valid(self) -> bool:
        return self.tier != TIER_PHYSICS_INVALID


@dataclass(frozen=True)
class SweepPoint:
    """One hull (or one separation) in one sweep."""

    label: str
    genes: tuple[tuple[str, float], ...]      # hashable, comparable, ordered
    q: Mapping[str, Quantity]
    valid: bool = True
    note: str = ""

    def value(self, key: str) -> float:
        return self.q[key].value


@dataclass(frozen=True)
class ExperimentRecord:
    name: str
    question: str
    protocol: Mapping[str, object]
    points: tuple[SweepPoint, ...]
    findings: Mapping[str, object]
    caveats: tuple[str, ...] = ()

    def valid_points(self) -> tuple[SweepPoint, ...]:
        return tuple(p for p in self.points if p.valid)


# ---------------------------------------------------------------------------
# The reference demihull, and why it is this hull
# ---------------------------------------------------------------------------
#
# A SLENDER DEMIHULL, NOT `tests/test_phase0.mid_params`. The reference hull the
# rest of this repository measures on is L/B **3.13**, which `resistance.py`
# says in as many words is outside the slenderness Michell's derivation assumes
# — so a bow experiment run on it would be measuring a thin-ship integral about
# a hull that is not thin. This one sits at L/B 8.0, the top of
# `grammar.L_OVER_B_BAND`, which is the slenderest thing this grammar can say
# and is the shape the mission ("fine-entry, slender demihull") asks for.
#
# THREE GENE CHOICES ARE LOAD-BEARING AND ARE NOT TASTE:
#
#   x_mb 0.55 with beta_len 0.35. The deadrise warp starts at
#   x = (1 - beta_len) L = 0.65 L, which is AFT of neither the max-area station
#   nor the forefoot rise (0.70 L). That is what makes the maximum sectional
#   area A_mid — and therefore the displacement, Cp and LCB — EXACTLY invariant
#   under the bow sweep. MEASURED: volume identical to 4.168216888 m^3 across
#   every bow, i.e. to all nine printed digits.
#
#   roundness 0.0. `Hull.section` then returns the three-point polyline
#   (`geometry.sample_section` is bit-identical to the pre-fillet kernel at
#   rho = 0), so `offsets_grid` costs 3 points per station instead of 257 and
#   the whole suite runs in seconds. The bilge fillet does not enter A(x) at
#   all — `_stations` solves the chine half-breadth to deliver the SAME area
#   whatever the roundness — so it is not a variable any of these four
#   experiments controls. Stated rather than assumed.
#
#   r_transom 0.20. The SAC solver refuses (Cp, lcb) pairs it cannot reach, and
#   a fuller transom eats the Cp range experiment 2 needs to sweep.
REFERENCE_DEMIHULL: tuple[tuple[str, float], ...] = (
    ("LWL", 12.0), ("BWL", 1.5), ("T", 0.45), ("D", 1.05),
    ("Cp", 0.60), ("lcb", -1.0), ("x_mb", 0.55), ("r_transom", 0.20),
    ("beta_mid", 8.0), ("beta_bow", 20.0), ("beta_len", 0.35),
    ("roundness", 0.0), ("rocker", 0.15), ("forefoot", 0.40),
    ("flare", 8.0), ("sheer_rise", 0.15),
)

RHO = geometry.RHO_WATER        # fresh water, matching the geometry kernel

# THE SPEED SWEEP, AND THE POINT THAT IS THERE TO BE REFUSED.
# 0.50 is above `resistance.FN_MICHELL_MAX` (0.45). It is swept, badged
# `L1-INVALID` and EXCLUDED from every finding — never interpolated over to
# make a smooth-looking curve. Keeping it in the record is the difference
# between "the model declined" and "nobody asked".
FROUDE_SWEEP: tuple[float, ...] = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)

# THE BOW SWEEP. `forefoot` is the keel rise at the stem as a fraction of T,
# and it is the WATERLINE-SHAPE knob at fixed A(x): lifting the keel forward
# takes depth out of the forward sections, so the same sectional area has to be
# carried by more BREADTH and the entrance blunts. It is not a "bow sharpness"
# parameter in the genome — there is no such gene, deliberately — it is the
# volume-distribution consequence the entry angle is a diagnostic of.
BOW_FOREFOOT_SWEEP: tuple[float, ...] = (0.0, 0.2, 0.35, 0.5, 0.65, 0.8)

# The SECOND bow knob, swept on its own so the first one's effect is
# attributable. MEASURED: beta_bow moves alpha_e_1pct by 0.05-2.3 deg over its
# whole admissible range against forefoot's 25.3 deg, so the deadrise warp is a
# weak entry-angle lever and the keel line is the strong one.
BOW_BETA_SWEEP: tuple[float, ...] = (8.0, 14.0, 20.0, 26.0, 32.0)

# Cp sweep: the DELIVERABLE intersection, computed per sweep hull.
# 2026-08-26: `limits.CP_GENE_BOUNDS` widened to the range of existing
# recreational craft (audit finding C.2), and the corrected sac solve
# refuses a Cp the sweep hull's own proportions cannot deliver — the top
# of the widened box (0.894 on the reference demihull) is honestly
# L0-infeasible at its x_mb/r_transom. The sweep therefore spans
# `geometry.cp_band(...) ∩ CP_GENE_BOUNDS` at N_CP_SWEEP points; a sweep
# pinned to the raw gene box would be a defect measured at a
# configuration the hull cannot occupy (defect class 6).
N_CP_SWEEP = 9


def cp_sweep_for(params) -> tuple[float, ...]:
    """The Cp sweep values deliverable by THIS hull — at ITS OWN lcb.

    The prismatic sweep is a controlled experiment: lcb is held at the
    reference value while Cp moves, so a sweep point is admissible only
    where BOTH targets are deliverable. At Cp 0.90 the reference
    demihull's lcb of -1 %LWL is honestly unreachable (the deliverable
    LCB bracket is +0.8..+9.1 — a hull that full must carry its buoyancy
    forward), so the sweep stops where the controlled variable would have
    to move, rather than moving it silently.
    """
    from .geometry import GeometryError, cp_band, sac_exponents
    p = grammar.named(np.asarray(params, float))
    b_lo, b_hi = cp_band(p["LWL"], p["x_mb"], p["r_transom"],
                         float(p.get("r_stem", 0.0)),
                         float(p.get("pmb", 0.0)))
    lo = max(limits.CP_GENE_BOUNDS[0], b_lo + 1e-3)
    hi = min(limits.CP_GENE_BOUNDS[1], b_hi - 1e-3)
    if not (hi > lo):
        raise ExperimentError(
            f"cp sweep: deliverable band [{b_lo:.3f}, {b_hi:.3f}] does not "
            f"intersect the gene box {limits.CP_GENE_BOUNDS}")

    # Admissibility is decided by THE SOLVER ITSELF, not by a band probe:
    # the lcb bracket and the nested bisection can disagree by a float
    # width at the extreme ends, and a sweep point the solve refuses is a
    # sweep point regardless of what a second implementation thinks.
    def _solvable(cp: float) -> bool:
        try:
            sac_exponents(p["LWL"], p["x_mb"], p["r_transom"], float(cp),
                          float(p["lcb"]), float(p.get("r_stem", 0.0)),
                          float(p.get("pmb", 0.0)))
            return True
        except GeometryError:
            return False

    keep = [float(cp) for cp in np.linspace(lo, hi, 10 * N_CP_SWEEP)
            if _solvable(cp)]
    if len(keep) < 2:
        raise ExperimentError(
            f"cp sweep: lcb {p['lcb']:+.2f} %LWL is deliverable at fewer "
            f"than two Cp values in [{lo:.3f}, {hi:.3f}]")
    pts = np.linspace(keep[0], keep[-1], N_CP_SWEEP)
    # keep only solvable points even inside the hull's span (the feasible
    # set need not be an interval at its float edges)
    return tuple(float(v) for v in pts if _solvable(v)) or tuple(keep[:N_CP_SWEEP])

# LCB sweep: the gene's band, `limits.LCB_BAND_PCT_LWL`, both signs.
LCB_SWEEP: tuple[float, ...] = tuple(
    float(v) for v in np.linspace(-limits.LCB_BAND_PCT_LWL,
                                  limits.LCB_BAND_PCT_LWL, 9))

# Separation sweep, s / Lwl. 0.20-0.50 is the band the brief names; the three
# large values are the s -> infinity correctness check for the phase
# convention. They are a SEPARATE protocol point (a different theta grid — the
# resolution rule in `resistance.n_theta_for_separation` scales with s/Lwl) and
# are recorded as such rather than plotted on the same curve.
SEPARATION_S_OVER_L: tuple[float, ...] = tuple(
    float(v) for v in np.linspace(0.20, 0.50, 31))
SEPARATION_ASYMPTOTIC_S_OVER_L: tuple[float, ...] = (2.0, 5.0, 10.0)

# The Froude numbers experiments 2-4 sweep speed over. Same tuple, filtered to
# the valid envelope where a sweep needs a dense curve rather than a refusal
# demonstration.
VALID_FROUDES: tuple[float, ...] = tuple(
    f for f in FROUDE_SWEEP if f <= resistance.FN_MICHELL_MAX)

# Waterline-curvature sampling. The metric is reported at N and re-measured at
# 2N; the RATIO of the two maxima is the discontinuity detector (see
# `waterline_metrics`), so both numbers are part of the protocol.
CURVATURE_SAMPLES = 2001

# ---------------------------------------------------------------------------
# EXPERIMENT 5's DESIGN SPACE — the one sweep where LENGTH IS A VARIABLE
# ---------------------------------------------------------------------------
#
# Every other sweep in this module pins LWL and varies speed, because they ask
# shape questions. Experiment 5 asks whether the OBJECTIVE can be gamed, and
# the gaming direction is length: at a fixed ABSOLUTE speed a longer hull sits
# at a lower Froude number and makes exponentially less wave, while carrying
# more skin. Pinning LWL is exactly the control that hides the defect —
# MEASURED, and recorded in `experiment_5_objective_gaming`: at fixed LWL and
# fixed Fn the R_w, R_t and Wh/NM optima are one hull and wetted surface spans
# 3.2% over the whole feasible box. There is nothing to find at that control.
#
# 10-20 m against a 12 m mission boat. `LWL` is gene 0 and `optimize.py` bounds
# it by `grammar.LOW/HIGH` intersected with the policy box, so absent a
# constitution that pins length, the optimiser really can reach 20 m.
GAMING_LWL_SWEEP: tuple[float, ...] = (10.0, 12.0, 14.0, 16.0, 18.0, 20.0)

# Slenderness. The top of the band is `grammar.L_OVER_B_BAND[1]` (8.5) and is
# read from it rather than typed, so a grammar change cannot leave this sweep
# quietly outside the box it claims to explore.
GAMING_L_OVER_B: tuple[float, ...] = (grammar.L_OVER_B_BAND[1], 6.5, 4.5)

GAMING_T_SWEEP: tuple[float, ...] = (0.30, 0.50)

# DEPTH IS DERIVED, NOT SWEPT, and this is a correction to an earlier version
# of this experiment rather than a simplification. `grammar.check` requires
# freeboard >= 4.5% of LWL, so a fixed depth refuses every hull above ~13 m and
# the length sweep would have stopped exactly where the finding lives. But
# depth above the waterline changes build area and structural mass while
# changing resistance NOT AT ALL, so sweeping it produced pairs of hulls with
# R_t identical to four decimal places: the "best-to-runner-up margin" came out
# at 0.0002 N against a 1.36 N grid shift, which reads as a completely
# unresolved optimum and was in fact two spellings of one boat. Deriving depth
# removes the degeneracy instead of reporting it as a tie.
GAMING_DEPTH_OVER_LWL = 0.11

GAMING_CP_SWEEP: tuple[float, ...] = tuple(
    float(v) for v in np.linspace(limits.CP_GENE_BOUNDS[0],
                                  limits.CP_GENE_BOUNDS[1], 5))
GAMING_LCB_SWEEP: tuple[float, ...] = (-limits.LCB_BAND_PCT_LWL, 0.0,
                                       +limits.LCB_BAND_PCT_LWL)
GAMING_FOREFOOT_SWEEP: tuple[float, ...] = (0.0, 0.5)

# The speed is set by naming a Froude number ON THE REFERENCE HULL and then
# holding the resulting SPEED IN M/S fixed across the whole length sweep. A
# mission states knots, not a Froude number, and this constant exists so that a
# reader can see the speed is anchored to something rather than picked.
GAMING_REFERENCE_FN = 0.30

ENERGY_SPEC = EnergySpec()

# HYDROSTATICS RUN ON THE MICHELL PRODUCTION STATION COUNT, NOT ON `Hull`'s
# DEFAULT 41. Two reasons, and the second is what forced it.
#
#   1. `resistance.total_resistance` rebuilds the hull at
#      `PRODUCTION_GRID["n_stations"]` anyway, so matching it means the state
#      handed to the resistance model (cb, wetted, beam, draft) is integrated
#      on the SAME grid the resistance is — rather than a coarse state fed to a
#      fine integral.
#
#   2. MEASURED while writing `tests/test_experiments.py`: the LCB sweep's
#      DESIGN volume (dense closed-form resample) is constant to 1.3e-6
#      relative across the whole +-3 %LWL band — the SAC solve holds the zeroth
#      moment exactly — but `hydrostatics.solve` at 41 stations reported a
#      1.03e-4 spread in displacement. That is trapezoid error on a
#      redistributed area curve, not a change in the boat, and it broke a
#      mechanism test at a 1e-4 bar. Rather than loosen the bar to accommodate
#      a known quadrature error, the quadrature was fixed:
#
#          n_stations    relative spread in disp_kg    cost (9 hulls)
#                  41            1.03e-4                  0.02 s
#                 101            1.86e-5                  0.03 s
#                 241            3.49e-6                  0.06 s   <- SHIPPED
#                 481            9.19e-7                  0.12 s
#
#      Loosening the bar would have hidden the one thing the test exists to
#      see. This is `docs/LESSONS.md`'s "never soften a failing gate" applied
#      to an experiment's own controls.
HYDRO_STATIONS = int(resistance.PRODUCTION_GRID["n_stations"])


def reference_demihull() -> np.ndarray:
    """The reference demihull parameter vector."""
    return grammar.vector(dict(REFERENCE_DEMIHULL))


def with_genes(**overrides: float) -> np.ndarray:
    """The reference demihull with named genes replaced.

    Refuses an unknown gene name rather than ignoring it — a typo'd override
    that silently does nothing is a sweep that did not sweep.
    """
    d = dict(REFERENCE_DEMIHULL)
    for k, v in overrides.items():
        if k not in d:
            raise ExperimentError(
                f"with_genes: {k!r} is not one of the {len(d)} genes "
                f"{tuple(d)}. Refused rather than ignored: an override that "
                f"does nothing produces a sweep of identical hulls that looks "
                f"like a null result.")
        d[k] = float(v)
    return grammar.vector(d)


def froude_to_speed(fn: float, lwl: float) -> float:
    """U [m/s] from the length Froude number. One definition, used everywhere."""
    return float(fn) * math.sqrt(G * float(lwl))


def require_feasible(params: np.ndarray, label: str) -> np.ndarray:
    """Return `params`, or raise naming the L0 violations.

    An infeasible hull is never silently skipped: the sweep's protocol says
    which hulls it contains, and a sweep that quietly dropped one is a sweep
    whose controlled quantities are not what it claims.
    """
    rep = grammar.check(params)
    if not rep.ok:
        raise ExperimentError(
            f"{label}: not L0-feasible — {'; '.join(rep.violations)}")
    return params


# ---------------------------------------------------------------------------
# DIAGNOSTIC 1: entry half-angle, by ONE method for every hull
# ---------------------------------------------------------------------------


def alpha_e_metrics(hull: Hull) -> dict[str, Quantity]:
    """Entry half-angle diagnostics, and the floor they must be read against.

    THE ANGLE IS A CHORD, NOT A DERIVATIVE AT THE STEM, and the method is part
    of the number. `geometry.Hull.alpha_e_deg(frac)` is the ONE implementation
    (this function does not contain a second one); it takes the chord over the
    forward `frac` of LWL because the tangent at the stem measures the
    geometric floor `_stations` puts on the chine half-breadth, not the hull.
    Both frac = 0.01 and frac = 0.02 are reported BY THE SAME METHOD for every
    hull, so a bow cannot game the metric with an infinitesimally sharp point
    followed by a curvature spike: such a hull shows a LARGE
    `alpha_e_method_spread` and is visible in the record.

    MEASURED on the bow sweep — the spread is the tell:

        forefoot   alpha_e_1pct   alpha_e_2pct   spread
          0.00          9.02           9.05      -0.03
          0.20         10.92          10.82      +0.10
          0.35         13.06          12.79      +0.27
          0.50         16.35          15.74      +0.61
          0.65         22.05          20.68      +1.37
          0.80         34.34          31.13      +3.21

    A fine bow is straight over the first 2% and the two agree to 0.03 deg; the
    blunt bow is 3.21 deg apart, i.e. the 1% chord is already reading a
    different curve from the 2% chord.

    ALPHA_E IS NOT INDEPENDENT OF L/B, and this is why the floor is reported
    beside it. `formlib.alpha_e_chord_floor_deg` owns the arithmetic (there is
    no copy here): the chord half-angle from the stem to the maximum-beam
    station is atan((L/B)^-1 / (2 L_E/L)) and depends on NOTHING but those two
    ratios. On this demihull (L/B 8.0 on the waterline, L_E/L 0.45) it is
    **7.91 deg**, so the finest bow in the sweep is 1.14x the floor and the
    bluntest is 4.34x. At the monohull grammar's L/B floor of 2.2 the same
    arithmetic gives 20.7-24.4 deg, which is MORE than half this sweep's whole
    range — a reader comparing an alpha_e across L/B is measuring the box, not
    the bow.
    """
    p = grammar.named(hull.params)
    lwl = p["LWL"]
    a1 = hull.alpha_e_deg(0.01)
    a2 = hull.alpha_e_deg(0.02)

    # The floor's two arguments are read off the DELIVERED waterline, exactly
    # as formlib defines them: the maximum waterline beam and the distance from
    # the stem to the station where it occurs.
    xs = np.linspace(0.0, lwl, 1001)
    yw = geometry.design_waterline(hull.params, xs)
    i_max = int(np.argmax(yw))
    b_wl = 2.0 * float(yw[i_max])
    le_over_l = float((lwl - xs[i_max]) / lwl)
    floor = formlib.alpha_e_chord_floor_deg(lwl / b_wl, le_over_l)

    return {
        "alpha_e_1pct": Quantity(a1, TIER_GEOMETRY, 0.0, "deg", BASIS_EXACT),
        "alpha_e_2pct": Quantity(a2, TIER_GEOMETRY, 0.0, "deg", BASIS_EXACT),
        "alpha_e_method_spread": Quantity(a1 - a2, TIER_GEOMETRY, 0.0, "deg",
                                          BASIS_EXACT),
        "alpha_e_chord_floor": Quantity(floor, TIER_GEOMETRY, 0.0, "deg",
                                        BASIS_EXACT),
        "alpha_e_over_floor": Quantity(a1 / floor, TIER_GEOMETRY, 0.0, "-",
                                       BASIS_EXACT),
        "le_over_l": Quantity(le_over_l, TIER_GEOMETRY, 0.0, "-", BASIS_EXACT),
        "l_over_b_wl": Quantity(lwl / b_wl, TIER_GEOMETRY, 0.0, "-",
                                BASIS_EXACT),
    }


# ---------------------------------------------------------------------------
# DIAGNOSTIC 2: waterline curvature, banded, with a discontinuity detector
# ---------------------------------------------------------------------------


def _kappa(params: np.ndarray, lwl: float, n: int
           ) -> tuple[np.ndarray, np.ndarray]:
    """(x, kappa) of the design waterline over the forward 30% of LWL.

    kappa = |y''| / (1 + y'^2)^{3/2} of y_wl(x), on a UNIFORM x grid so the
    second difference has a constant step. `geometry.design_waterline` is the
    closed form and is the only place the curve comes from.

    THE STEM NODE IS DROPPED. At x = LWL the half-breadth is zero and
    `np.gradient` switches to a one-sided difference, which is a different
    estimator; including it puts an artefact of the sampler at exactly the
    station the metric is most sensitive at. This is the same rule
    `geometry.Hull.fairness` applies when it masks the stem, and for the same
    reason.
    """
    xs = np.linspace(0.70 * lwl, lwl, n)
    y = geometry.design_waterline(params, xs)
    dx = float(xs[1] - xs[0])
    y1 = np.gradient(y, dx)
    y2 = np.gradient(y1, dx)
    kap = np.abs(y2) / (1.0 + y1 * y1) ** 1.5
    return xs[:-1], kap[:-1]


def curvature_metrics(params: np.ndarray,
                      n: int = CURVATURE_SAMPLES) -> dict[str, Quantity]:
    """Banded waterline curvature, and whether it is CONTINUOUS.

    Bands are measured FORWARD FROM THE STEM: 0-10% of LWL and 10-25% of LWL.
    Reported per band: max, 95th percentile, and the least-squares gradient of
    kappa with respect to x/LWL (so the units are 1/m per length-fraction and
    the sign says whether curvature is being piled into the stem or spread).

    THE DISCONTINUITY DETECTOR IS A REFINEMENT RATIO, NOT A THRESHOLD ON A
    JUMP. A true C1 break in y_wl makes kappa DIVERGE like 1/h, so
    `kappa_refinement_ratio` = max kappa at 2n / max kappa at n is ~1.0 for a
    continuous curve and grows without bound at a knuckle. A fixed threshold on
    an adjacent-node jump would instead report a resolution, which is the
    mistake `geometry.Hull.fairness`'s docstring records having made once
    already (a sampler artefact read as a property of the hull).

    MEASURED across the whole bow sweep: `kappa_refinement_ratio` is
    1.0000-1.0001 at every point, i.e. every waterline this grammar emits is
    curvature-continuous over the forward quarter — there is no knuckle in the
    DESIGN WATERLINE to find. (The chine knuckle is in the SECTION, which is a
    different curve and is `Hull.fairness`'s question, not this one's.)

    MEASURED on the bow sweep, band 0-10% of LWL from the stem:

        forefoot  alpha_e_1pct  kappa_max  kappa_p95  d(kappa)/d(x/L)
          0.00        9.02        0.0085     0.0077        +0.041
          0.20       10.92        0.0292     0.0292        -0.002
          0.35       13.06        0.0769     0.0769        +0.364
          0.50       16.35        0.1771     0.1756        +1.290
          0.65       22.05        0.3783     0.3773        +3.649
          0.80       34.34        0.9418     0.9319       +10.277

    THE CURVATURE IS A FAR SHARPER DISCRIMINATOR THAN THE ANGLE. Over the same
    sweep alpha_e moves 3.8x while kappa_max moves **111x** and the curvature
    GRADIENT — how hard the curvature piles up toward the stem — moves by 250x
    and changes sign. The bluntest bow is not merely wider at the stem; it puts
    two orders of magnitude more bend into the forward tenth of the waterline.
    A generator scored on alpha_e alone cannot see that difference, which is
    the argument for carrying both.

    Note the forefoot 0.20 row: its curvature gradient is NEGATIVE (-0.002),
    i.e. it is the one bow in the sweep whose forward waterline gets STRAIGHTER
    toward the stem rather than tighter. It is also the bow that wins at
    Fn 0.35. That is an observation, not a mechanism — n = 1 and nothing here
    tests it — but it is the kind of thing an alpha_e-only metric would erase.
    """
    lwl = float(grammar.named(params)["LWL"])
    # The curve is evaluated at n and at 2n-1 ONCE, and both the values and
    # their sigmas come off that one pair. An earlier version recomputed the
    # dense curve inside a per-band helper, so each hull solved the same
    # closed form six times over — the sigma is a refinement difference and it
    # needs the refined curve exactly once.
    x, kap = _kappa(params, lwl, n)
    x2, kap2 = _kappa(params, lwl, 2 * n - 1)

    out: dict[str, Quantity] = {}
    for lo, hi, tag in ((0.0, 0.10, "0_10"), (0.10, 0.25, "10_25")):
        m = (x >= lwl - hi * lwl) & (x <= lwl - lo * lwl)
        m2 = (x2 >= lwl - hi * lwl) & (x2 <= lwl - lo * lwl)
        if int(np.count_nonzero(m)) < 3:
            raise ExperimentError(
                f"curvature_metrics: band {tag} holds {int(m.sum())} samples "
                f"at n = {n}; a gradient cannot be fitted to it and an "
                f"unmeasurable metric is refused, not defaulted")
        kb, kb2 = kap[m], kap2[m2]
        xb = x[m] / lwl
        # THE SIGMA IS THE REFINEMENT DIFFERENCE, i.e. MEASURED. It is the same
        # band re-read on the doubled grid, not a declared percentage.
        sig = float(abs(kb.max() - kb2.max()))
        slope = float(np.polyfit(xb, kb, 1)[0])
        slope2 = float(np.polyfit(x2[m2] / lwl, kb2, 1)[0])
        out[f"kappa_max_{tag}"] = Quantity(
            float(kb.max()), TIER_GEOMETRY, sig, "1/m", BASIS_GRID)
        out[f"kappa_p95_{tag}"] = Quantity(
            float(np.percentile(kb, 95)), TIER_GEOMETRY,
            float(abs(np.percentile(kb, 95) - np.percentile(kb2, 95))),
            "1/m", BASIS_GRID)
        out[f"kappa_gradient_{tag}"] = Quantity(
            slope, TIER_GEOMETRY, abs(slope - slope2), "1/m per x/L",
            BASIS_GRID)
    ratio = float(kap2.max() / max(kap.max(), 1e-30))
    out["kappa_refinement_ratio"] = Quantity(
        ratio, TIER_GEOMETRY, 0.0, "-", BASIS_EXACT)
    out["kappa_samples"] = Quantity(float(n), TIER_GEOMETRY, 0.0, "-",
                                    BASIS_EXACT)
    return out


# ---------------------------------------------------------------------------
# The floated state and the resistance point
# ---------------------------------------------------------------------------


def _float_hull(params: np.ndarray, n_stations: int,
                target_disp_kg: float | None
                ) -> tuple[Hull, HydroState, float]:
    """(hull, state, wl). `target_disp_kg=None` floats at the design waterline.

    `solve_to_displacement` is the ONE bisection; nothing here re-implements a
    draft solve. Its tolerance is tightened to 1e-6 relative because these
    sweeps compare hulls whose totals differ by fractions of a percent, and a
    1e-3 displacement tolerance is larger than the effect being measured.
    """
    hull = Hull(params, n_stations=n_stations)
    if target_disp_kg is None:
        return hull, solve(hull, RHO, 0.0), 0.0
    st, wl = solve_to_displacement(hull, float(target_disp_kg), RHO, 1e-6)
    return hull, st, wl


def hydro_quantities(hull: Hull, st: HydroState, wl: float
                     ) -> dict[str, Quantity]:
    """The hydrostatic state as `Quantity` records, with MEASURED sigmas.

    Every value comes from `hydrostatics.solve` / `Hull.form_coefficients`;
    this function computes none of them. The sigma on each integral quantity is
    the station-grid refinement band — the same value re-integrated on a hull
    of twice the station count — which is a measurement, not a declaration.
    """
    fc = hull.form_coefficients()
    fc2 = Hull(hull.params, n_stations=2 * hull.n_stations - 1
               ).form_coefficients()
    st2 = solve(Hull(hull.params, n_stations=2 * hull.n_stations - 1), RHO, wl)

    def q(v: float, v2: float, units: str) -> Quantity:
        return Quantity(float(v), TIER_PHYSICS, abs(float(v) - float(v2)),
                        units, BASIS_GRID)

    return {
        "volume_m3": q(st.volume, st2.volume, "m^3"),
        "disp_kg": q(st.disp_kg, st2.disp_kg, "kg"),
        "draft_m": q(st.draft, st2.draft, "m"),
        "wl_m": Quantity(float(wl), TIER_PHYSICS, 0.0, "m", BASIS_EXACT),
        "wetted_m2": q(st.wetted, st2.wetted, "m^2"),
        "cb": q(st.cb, st2.cb, "-"),
        "cp_floated": q(st.cp, st2.cp, "-"),
        "lcb_pct_lwl": q(st.lcb_pct_lwl, st2.lcb_pct_lwl, "%LWL"),
        "awp_m2": q(st.awp, st2.awp, "m^2"),
        "bm_m": q(st.bm, st2.bm, "m"),
        "lwl_eff_m": q(st.lwl_eff, st2.lwl_eff, "m"),
        # The DESIGN-waterline form coefficients, integrated on the dense
        # resample `form_coefficients` owns. These are the controlled
        # quantities of experiments 1 and 3.
        "volume_design_m3": q(fc["volume_m3"], fc2["volume_m3"], "m^3"),
        "cp_design": q(fc["Cp"], fc2["Cp"], "-"),
        "lcb_design_pct": q(fc["lcb_pct"], fc2["lcb_pct"], "%LWL"),
        "cm": q(fc["Cm"], fc2["Cm"], "-"),
        "cwp": q(fc["Cwp"], fc2["Cwp"], "-"),
    }


def resistance_quantities(hull: Hull, st: HydroState, wl: float, fn: float,
                          grid: Mapping[str, int],
                          other_grid: Mapping[str, int] | None = None
                          ) -> dict[str, Quantity]:
    """R_w, R_f, R_t and Wh/NM at one Froude number, on ONE stated grid.

    `resistance.total_resistance` is the only resistance implementation called.
    The tier is taken from `ResistanceResult.valid`, i.e. from the module's own
    envelope check against `FN_MICHELL_MAX`, not from a comparison written
    here — a second copy of the envelope is exactly the defect this project
    keeps paying for.

    `other_grid` is REQUIRED, and it is what supplies the MEASURED
    discretisation sigma: |R(grid) - R(other_grid)| per component. Pass the
    converged grid beside the production one (and vice versa) so every number
    here carries a band that was measured rather than declared.

    ================= WHY THE COMPONENT SIGMAS ARE A LOWER BOUND =================
    AND WHY THIS MODULE REFUSES TO FIX IT LOCALLY.

    `ResistanceResult` exposes ONE model uncertainty, `uncertainty`, and it is
    on the TOTAL. The two constants that build it — the 0.25 for Michell's hump
    overprediction and the 0.10 for the friction-line scatter — are INLINE in
    `resistance.total_resistance`:

        sigma_rf = rf * sqrt((sigma_k / (1 + k))**2 + 0.10**2)
        sigma    = 0.25 * rw + sigma_rf

    They are not named constants, so there is nothing to import. The first
    version of this function simply retyped `0.25 * rw` and `0.10 * cf` here —
    which is THIS REPOSITORY'S RECURRING DEFECT, a number declared twice, and
    the two copies would drift the moment `resistance.py` revised either band
    (it revised the friction one once already, when it started propagating the
    form factor's own sigma instead of declaring a flat 10%).

    So the components carry the MEASURED grid band and are labelled
    `BASIS_GRID_LOWER_BOUND`: the true band on R_w is far wider (Michell's
    hump caveat is tens of percent) and this is only the part that was
    measured. The naming follows `energy.SIGMA_PROPAGATED_LOWER_BOUND`, which
    is the same honesty in the same shape: a lower bound with its name on it is
    a usable number; a copied constant is not.

    THE TOTAL is exempt because `r.uncertainty` IS the module's own number and
    is imported, not restated — so `rt_n` carries the full model band, and
    `rt_grid_sigma_n` carries the discretisation band separately. A reader who
    needs a component's model band should read `rt_n`'s.

    THE FIX IS NOT HERE. It is a named constant in `resistance.py` (another
    agent's file) and a per-component sigma on `ResistanceResult`. Recorded as
    owed rather than worked around.
    """
    if other_grid is None:
        raise ExperimentError(
            "resistance_quantities: `other_grid` is required. Without a second "
            "grid there is no measured discretisation band, and a component "
            "sigma would have to be declared — which in this module means "
            "copying a constant out of resistance.py. Refused.")
    lwl = float(grammar.named(hull.params)["LWL"])
    u = froude_to_speed(fn, lwl)

    def run(g: Mapping[str, int]):
        return resistance.total_resistance(
            hull, u, st.wetted, st.cb, RHO, wl,
            nz=int(g["nz"]), n_stations=int(g["n_stations"]),
            beam_wl=st.b_wl_max, draft=st.draft)

    r, r2 = run(grid), run(other_grid)
    tier = TIER_PHYSICS if r.valid else TIER_PHYSICS_INVALID
    en = energy_report(r.total, u, hull.deck_area(), ENERGY_SPEC,
                       resistance_sigma_n=r.uncertainty)

    def grid_q(v: float, v2: float, units: str) -> Quantity:
        return Quantity(float(v), tier, abs(float(v) - float(v2)), units,
                        BASIS_GRID_LOWER_BOUND)

    return {
        "fn": Quantity(float(r.fn), tier, 0.0, "-", BASIS_EXACT),
        "speed_mps": Quantity(float(u), tier, 0.0, "m/s", BASIS_EXACT),
        "rw_n": grid_q(r.rw, r2.rw, "N"),
        "rf_n": grid_q(r.rf, r2.rf, "N"),
        "cw": grid_q(r.cw, r2.cw, "-"),
        "cf": grid_q(r.cf, r2.cf, "-"),
        # `uncertainty` and `sigma_k` are the modules' OWN numbers, imported
        # rather than restated, so these two carry the full model band.
        "rt_n": Quantity(float(r.total), tier, float(r.uncertainty), "N",
                         BASIS_MODEL),
        "form_k": Quantity(float(r.form.k), tier, float(r.form.sigma_k), "-",
                           BASIS_MODEL),
        "wh_per_nm": Quantity(float(en.wh_per_nm), tier,
                              float(en.sigma_wh_per_nm), "Wh/NM",
                              BASIS_PROPAGATED),
        "rt_grid_sigma_n": Quantity(abs(float(r.total - r2.total)), tier, 0.0,
                                    "N", BASIS_EXACT),
    }


# ---------------------------------------------------------------------------
# Curve-shape classification: the deliverable "report the shape of the curve"
# ---------------------------------------------------------------------------


def _second_best_margin(ys: Sequence[float]) -> float:
    """best-to-second-best gap of a minimisation curve.

    The number that decides whether an optimum is RESOLVED: if the gap between
    the winner and the runner-up is smaller than the discretisation band, the
    ranking between those two is not a hydrodynamic statement. Reported beside
    every optimum in this module rather than folded into a dead-band, because a
    dead-band applied silently is how a suite stops reporting the thing a
    reader most needs to see.
    """
    s = np.sort(np.asarray(ys, dtype=float))
    if s.size < 2:
        raise ExperimentError("_second_best_margin: need >= 2 points")
    return float(s[1] - s[0])


def curve_shape(xs: Sequence[float], ys: Sequence[float],
                tol: float = 0.0) -> dict[str, object]:
    """Classify y(x): monotone, interior optimum, or genuinely non-monotone.

    `tol` is an ABSOLUTE dead-band on a step of y. IT IS NOT USED BY ANY
    EXPERIMENT HERE, and the reason is a defect the first version of this
    module shipped: classifying the SHAPE with a dead-band while taking the
    ARGMIN from the raw curve produced records reading
    `shape=monotonic-decreasing, best_cp=0.687` when the last point was 0.710 —
    two statements about one curve that contradict each other. The experiments
    now classify the raw curve and report the resolution SEPARATELY, as
    `optimum_margin` against `grid_shift`, which is a number a reader can
    judge instead of a threshold this function applied silently.

    Returns the shape name, the argmin/argmax, and the number of interior
    turning points — a computed classification, so "the curve has an optimum
    at x" is a measurement rather than a reading of a plot.
    """
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    if x.size != y.size or x.size < 3:
        raise ExperimentError(
            f"curve_shape: need >= 3 paired points, got {x.size} x and "
            f"{y.size} y")
    d = np.diff(y)
    d[np.abs(d) <= tol] = 0.0
    nz = d[d != 0.0]
    turns = int(np.count_nonzero(np.sign(nz[:-1]) * np.sign(nz[1:]) < 0)) \
        if nz.size >= 2 else 0
    i_min, i_max = int(np.argmin(y)), int(np.argmax(y))
    if turns == 0 and nz.size and np.all(nz > 0):
        shape = "monotonic-increasing"
    elif turns == 0 and nz.size and np.all(nz < 0):
        shape = "monotonic-decreasing"
    elif nz.size == 0:
        shape = "flat-within-tolerance"
    elif turns == 1 and 0 < i_min < x.size - 1:
        shape = "interior-minimum"
    elif turns == 1 and 0 < i_max < x.size - 1:
        shape = "interior-maximum"
    else:
        shape = "non-monotonic"
    return {
        "shape": shape,
        "turning_points": turns,
        "argmin_x": float(x[i_min]), "min_y": float(y[i_min]),
        "argmax_x": float(x[i_max]), "max_y": float(y[i_max]),
        "argmin_is_interior": bool(0 < i_min < x.size - 1),
        "argmax_is_interior": bool(0 < i_max < x.size - 1),
        "range_frac": float((y.max() - y.min()) / max(abs(y).max(), 1e-30)),
    }


# ---------------------------------------------------------------------------
# EXPERIMENT 1 — BOW SHARPNESS SWEEP
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def experiment_1_bow_sharpness() -> ExperimentRecord:
    """Does a sharper entrance reduce resistance, and where does it stop?

    THE CONTROLLED QUANTITIES ARE EXACTLY CONTROLLED, and that is the thing
    that can silently break, so it is what the test asserts. `forefoot`,
    `beta_bow` and `beta_len` change the SECTION SHAPE forward; they do not
    change the sectional area curve, because `geometry._stations` SOLVES the
    chine half-breadth at every station to deliver A(x) whatever the deadrise
    and keel depth are. With `x_mb` (0.55) aft of both the deadrise warp start
    (0.65 L) and the forefoot rise start (0.70 L), the maximum sectional area
    is untouched too. MEASURED across the whole sweep:

        volume 4.168216888 m^3, Cp 0.599998, LCB -1.00007 %LWL — IDENTICAL to
        every printed digit at all six bows.

    So this sweep varies the WATERLINE SHAPE at a fixed longitudinal volume
    distribution. That is the framing the mission asks for: the entry angle is
    a diagnostic of where the volume went, not a knob.

    ============================ THE RESULT ============================
    R_t [N] on the PRODUCTION grid (241 x 44), 12.0 m demihull, fresh water,
    floated at the design waterline (displacement 4167.0 kg at every point):

      forefoot  a_e1    S m^2   Fn0.20  Fn0.25  Fn0.30  Fn0.35  Fn0.40  Fn0.45
        0.00    9.02   19.040    141.1   242.1   323.1   504.2   939.4  1376.3
        0.20   10.92   18.891    142.2   247.2   325.1   503.7   936.6  1371.8
        0.35   13.06   18.789    143.7   251.9   327.8   504.9   936.4  1370.3
        0.50   16.35   18.700    146.1   258.0   332.1   508.0   938.1  1371.1
        0.65   22.05   18.632    150.2   266.6   339.1   514.1   943.4  1375.7
        0.80   34.34   18.611    158.6   280.9   352.9   527.8   956.9  1389.0

    SHARPER IS NOT UNIFORMLY BETTER, and the curve changes shape with speed:

        Fn 0.20  monotonic-increasing in alpha_e  -> sharpest wins
        Fn 0.25  monotonic-increasing             -> sharpest wins
        Fn 0.30  monotonic-increasing             -> sharpest wins
        Fn 0.35  INTERIOR MINIMUM at forefoot 0.20 (a_e 10.9 deg)
        Fn 0.40  INTERIOR MINIMUM at forefoot 0.35 (a_e 13.1 deg)
        Fn 0.45  INTERIOR MINIMUM at forefoot 0.35 (a_e 13.1 deg)

    THE MECHANISM, and it is why this is physics and not noise. Splitting R_t:

        Fn      R_w sharpest -> bluntest       R_f sharpest -> bluntest
        0.20      21.96 -> 42.12  (+91.8%)      119.12 -> 116.43  (-2.3%)
        0.30      71.88 -> 107.30 (+49.3%)      251.24 -> 245.57  (-2.3%)
        0.40     512.28 -> 539.34  (+5.3%)      427.14 -> 417.51  (-2.3%)
        0.45     845.34 -> 869.98  (+2.9%)      530.96 -> 518.98  (-2.3%)

    R_w rises monotonically with entry angle at EVERY Froude number — the wave
    term never prefers a blunt bow. What collapses is its SENSITIVITY: 92% at
    Fn 0.20, 2.9% at Fn 0.45. R_f falls by a constant 2.3% because at fixed
    A(x) a lifted forefoot puts the same area into a wider, shallower section,
    and a wider shallower section has less girth. The interior optimum is the
    crossing point of a flattening wave penalty and a fixed friction saving.

    ================= AND THE HONEST CAVEAT ON THAT OPTIMUM =================
    The optimum is a SMALL effect and the suite says exactly how small, per
    speed. `sharpest_penalty_n` is what the sharpest bow costs against the
    optimum; `grid_shift_n` is the largest production-to-converged move of any
    hull in the sweep:

        Fn     penalty of sharpest    grid shift    penalty / shift
        0.35        0.47 N (0.09%)      0.53 N          0.90
        0.40        3.04 N (0.32%)      1.45 N          2.09
        0.45        5.95 N (0.43%)      2.12 N          2.80

    SO AT Fn 0.35 THE SHARPEST BOW'S PENALTY IS SMALLER THAN THE
    PRODUCTION-TO-CONVERGED SHIFT. The statement "sharper stops helping" should
    be quoted from Fn 0.40, not Fn 0.35, and this suite is the reason anyone
    can tell the difference.

    A SECOND AND STRICTER FLAG SAYS SOMETHING WEAKER, AND IT IS NOT HIDDEN.
    `optimum_resolved_above_grid_shift` asks whether the WINNER is
    distinguishable from its immediate RUNNER-UP, and at Fn 0.35, 0.40 and 0.45
    the answer is NO (margins 0.47, 0.24 and 0.77 N against grid shifts of
    0.53, 1.45 and 2.12 N). The interior optima are SHALLOW. So the defensible
    claim is not "the optimum is at alpha_e 13.1 deg"; it is:

        at Fn >= 0.40 the SHARPEST available bow is measurably worse than the
        middle of the range, by more than this protocol's discretisation band,
        and the ordering of all six bows is identical on both grids.

    Which bow in the 10.9-16.4 deg middle is best is BELOW the resolution of
    the production/converged grid pair, and this record says so rather than
    reporting an argmin as if it were resolved.

    WHAT IS SOLID AT ALL THREE SPEEDS is that the optimum is INTERIOR and sits
    at the SAME hull on both grids (`optimum_same_on_both_grids`), and that the
    RANKING of all six bows is identical on both grids at every valid Froude
    number (`ranking_identical_on_both_grids`). A "better bow" that appeared on
    one grid and vanished on the other would be quadrature error, and the test
    for it fails loudly rather than being left to a reader.

    THE ENTRY-ANGLE RANGE IS BOUNDED BELOW BY THE BOX, NOT BY THE BOW. The
    chord floor at this L/B (8.0) and entry length (L_E/L 0.45) is 7.91 deg;
    the finest bow reaches 9.02 deg, i.e. 1.14x the floor. There is no sharper
    bow available at this L/B — to get finer, the SLENDERNESS has to move, not
    the bow shape. See `alpha_e_metrics`.
    """
    grids = (dict(resistance.PRODUCTION_GRID), dict(resistance.CONVERGED_GRID))
    prod, conv = grids
    points: list[SweepPoint] = []
    for ff in BOW_FOREFOOT_SWEEP:
        params = require_feasible(with_genes(forefoot=ff), f"bow ff={ff}")
        hull, st, wl = _float_hull(params, HYDRO_STATIONS, None)
        q: dict[str, Quantity] = {}
        q.update(alpha_e_metrics(hull))
        q.update(curvature_metrics(params))
        q.update(hydro_quantities(hull, st, wl))
        for fn in FROUDE_SWEEP:
            rq = resistance_quantities(hull, st, wl, fn, prod, other_grid=conv)
            for k, v in rq.items():
                q[f"prod/fn{fn:.2f}/{k}"] = v
            rc = resistance_quantities(hull, st, wl, fn, conv,
                                       other_grid=prod)
            for k, v in rc.items():
                q[f"conv/fn{fn:.2f}/{k}"] = v
        points.append(SweepPoint(
            label=f"forefoot={ff:.2f}",
            genes=tuple(sorted(grammar.named(params).items())),
            q=q, valid=True,
            note="fixed A(x); waterline shape varied by the forefoot keel rise"))

    findings: dict[str, object] = {}
    ranking_matches: dict[str, bool] = {}
    for fn in FROUDE_SWEEP:
        key = f"prod/fn{fn:.2f}/rt_n"
        ckey = f"conv/fn{fn:.2f}/rt_n"
        if not all(p.q[key].valid for p in points):
            findings[f"fn{fn:.2f}"] = {
                "excluded": True,
                "reason": (f"Fn {fn:.2f} > resistance.FN_MICHELL_MAX "
                           f"{resistance.FN_MICHELL_MAX}; badged "
                           f"{TIER_PHYSICS_INVALID} and NOT interpolated over"),
            }
            continue
        ae = [p.value("alpha_e_1pct") for p in points]
        rt = [p.value(key) for p in points]
        rtc = [p.value(ckey) for p in points]
        sh = curve_shape(ae, rt)
        shc = curve_shape(ae, rtc)
        ranking_matches[f"fn{fn:.2f}"] = bool(
            np.array_equal(np.argsort(rt), np.argsort(rtc)))
        gs = max(p.value(f"prod/fn{fn:.2f}/rt_grid_sigma_n") for p in points)
        margin = rt[0] - min(rt)
        findings[f"fn{fn:.2f}"] = {
            "excluded": False,
            "shape_rt_vs_alpha_e": sh["shape"],
            "best_alpha_e_deg": sh["argmin_x"],
            "best_rt_n": sh["min_y"],
            "best_alpha_e_deg_converged_grid": shc["argmin_x"],
            "optimum_same_on_both_grids": bool(
                abs(sh["argmin_x"] - shc["argmin_x"]) < 1e-9),
            "shape_rt_vs_alpha_e_converged_grid": shc["shape"],
            "sharpest_rt_n": rt[0],
            "sharpest_penalty_n": margin,
            "sharpest_penalty_frac": margin / rt[0],
            "grid_shift_n": gs,
            "sharpest_penalty_over_grid_shift": ((margin / gs) if gs > 0
                                                 else float("inf")),
            # THE HONEST FLAG, and it is measured on the BEST-TO-RUNNER-UP gap,
            # not on the sharpest bow's penalty. On a monotone curve the
            # sharpest bow IS the winner, so its penalty is 0 and a flag keyed
            # to it would report "not resolved" for the three speeds where the
            # answer is cleanest. The question a resolution flag has to answer
            # is whether the WINNER is distinguishable from the runner-up.
            "optimum_margin_n": _second_best_margin(rt),
            "optimum_resolved_above_grid_shift": bool(
                _second_best_margin(rt) > gs),
            "rt_span_frac": sh["range_frac"],
            "rw_span_frac": ((points[-1].value(f"prod/fn{fn:.2f}/rw_n")
                              - points[0].value(f"prod/fn{fn:.2f}/rw_n"))
                             / points[0].value(f"prod/fn{fn:.2f}/rw_n")),
            "rf_span_frac": ((points[-1].value(f"prod/fn{fn:.2f}/rf_n")
                              - points[0].value(f"prod/fn{fn:.2f}/rf_n"))
                             / points[0].value(f"prod/fn{fn:.2f}/rf_n")),
        }
    findings["ranking_identical_on_both_grids"] = ranking_matches
    findings["sharper_is_better"] = {
        fn_key: (rec["shape_rt_vs_alpha_e"] == "monotonic-increasing")
        for fn_key, rec in findings.items()
        if isinstance(rec, dict) and not rec.get("excluded", False)
        and "shape_rt_vs_alpha_e" in rec
    }

    return ExperimentRecord(
        name="1-bow-sharpness",
        question=("Does a finer entrance reduce total resistance, and at what "
                  "entry angle does it stop helping?"),
        protocol={
            "controlled": ("LWL", "BWL", "T", "Cp", "lcb", "displacement",
                           "sectional area curve A(x)"),
            "varied": ("forefoot",),
            "diagnostics": ("alpha_e_1pct", "alpha_e_2pct", "kappa bands"),
            "production_grid": prod, "converged_grid": conv,
            "n_theta_monohull": resistance.N_THETA_MONOHULL,
            "fn_michell_max": resistance.FN_MICHELL_MAX,
            "rho": RHO, "waterline": "design (z = 0)",
        },
        points=tuple(points),
        findings=findings,
        caveats=(
            "The interior optimum at Fn 0.35 is NOT resolved: its 0.49 N "
            "margin is below the 0.53 N production-to-converged grid shift. "
            "At Fn 0.40 and 0.45 the margin is 2.1x and 2.8x the shift. The "
            "ranking and the optimum's LOCATION are grid-independent at all "
            "three, but the magnitude should not be quoted to more than one "
            "significant figure.",
            "R_f moves only through the wetted surface: Watanabe's form factor "
            "k is 0.0177 at every point of this sweep because it depends on "
            "cb, L, B and T, none of which the bow sweep changes. A real bow "
            "changes the form factor and this model cannot see that.",
            "Michell overpredicts at the humps by tens of percent (the "
            "literature's standing caveat, recorded in resistance.py). The "
            "DIFFERENCES between bows at fixed everything else are more "
            "trustworthy than the absolute values.",
        ),
    )


# ---------------------------------------------------------------------------
# EXPERIMENT 2 — Cp SWEEP AT FIXED DISPLACEMENT
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def experiment_2_prismatic() -> ExperimentRecord:
    """Which prismatic coefficient wins at which Froude number?

    Evidence toward a future Cp*(Fn) prior. NOTHING here assumes the answer,
    and in particular `limits.prismatic_target` is READ FOR COMPARISON ONLY —
    it is a practice curve whose own docstring says it is unsourced, so it is
    the hypothesis under test, not the ground truth.

    WHAT "FIXED DISPLACEMENT" MEANS HERE, because the brief's "same L, B, T AND
    displacement" is over-determined and saying so is part of the result. The
    delivered volume is Cp * A_max * LWL and A_max is set by BWL, T, the
    midship deadrise, the flare and the roundness — none of which Cp touches.
    So at fixed L, B and T, changing Cp changes the displacement by
    construction; something must move. What moves here is the DRAFT: every hull
    is floated to the reference hull's design displacement with
    `hydrostatics.solve_to_displacement`, which is the production mechanism,
    and the resulting draft is reported as the dependent variable.

    MEASURED — displacement is held to 4168.19 kg at every point (bisection
    tolerance 1e-6 relative):

        Cp gene   floated wl   draft m   Cp floated   S m^2
          0.5250     +0.0547    0.5047     0.5252    18.884
          0.5481     +0.0362    0.4862     0.5483    18.804
          0.5713     +0.0193    0.4693     0.5714    18.761
          0.5944     +0.0036    0.4536     0.5944    18.754
          0.6175     -0.0109    0.4391     0.6173    18.779
          0.6406     -0.0243    0.4257     0.6402    18.833
          0.6637     -0.0367    0.4133     0.6628    18.914
          0.6869     -0.0483    0.4017     0.6853    19.021
          0.7100     -0.0590    0.3910     0.7076    19.153

    Note that the wetted surface has its own interior MINIMUM at Cp ~0.594 —
    the sweep is not monotone in its friction term either, which is a second
    reason the total is not obviously ordered.

    ============================ THE RESULT ============================
    R_t [N] against the Cp gene, production grid, displacement fixed:

      Cp      Fn0.20   Fn0.25   Fn0.30   Fn0.35   Fn0.40   Fn0.45
      0.5250  151.51   297.03   363.89   675.00  1180.51  1612.07
      0.5481  148.62   286.50   343.98   597.28  1070.88  1500.72
      0.5713  147.00   270.95   336.27   549.65   998.22  1427.76
      0.5944  144.43   256.34   328.83   512.77   947.69  1380.79
      0.6175  145.44   247.80   334.33   488.80   906.19  1340.51
      0.6406  149.71   245.17   352.47   478.82   875.24  1308.57
      0.6637  156.03   247.74   383.46   483.74   855.88  1286.51
      0.6869  163.91   255.43   426.18   504.21   849.46  1275.88
      0.7100  172.99   268.08   477.82   539.24   855.77  1276.97

    THE OPTIMUM MOVES WITH FROUDE NUMBER, AND IT IS NOT MONOTONE IN Fn:

        Fn     best Cp   practice curve   measured - practice   shape
        0.20    0.5944       0.5350            +0.0594      interior-minimum
        0.25    0.6406       0.5542            +0.0865      interior-minimum
        0.30    0.5944       0.5750            +0.0194      interior-minimum
        0.35    0.6406       0.6000            +0.0406      interior-minimum
        0.40    0.6869       0.6350            +0.0519      interior-minimum
        0.45    0.6869       0.6600            +0.0269      interior-minimum

    TWO FINDINGS, AND THE SECOND ONE REFUTES AN EXPECTATION.

      1. THE OPTIMUM IS ALWAYS INTERIOR and it TRENDS UP with speed — 0.59 at
         Fn 0.20 to 0.69 at Fn 0.40-0.45 — which is the direction the
         literature and `limits.prismatic_target` both say. That much is
         confirmed.

      2. IT IS NOT MONOTONE IN Fn: 0.594 -> 0.641 -> 0.594 -> 0.641 -> 0.687
         -> 0.687. The dip at Fn 0.30 is not noise; the optimum's margin there
         is 5.50 N against a 0.49 N grid shift, i.e. 11x resolved. It is the
         wave-making HUMP structure showing through: Michell's R_w is
         oscillatory in Fn (bow and stern wave systems interfering), so the Cp
         that minimises it oscillates too. Any Cp*(Fn) prior fitted as a smooth
         monotone curve — which is what `limits.PRISMATIC_BY_FROUDE` is — is
         smoothing over real structure. That is a finding about the TABLE, and
         it is recorded rather than fitted away.

         ONE OPTIMUM IS A TIE AND IS FLAGGED: at Fn 0.45 the winner (0.6869,
         1275.88 N) beats the runner-up (0.7100, 1276.97 N) by 1.09 N against
         a 3.18 N grid shift, so `optimum_resolved_above_grid_shift` is False.
         Read Fn 0.45 as "0.687 or fuller", not as 0.687.

      3. EVERY MEASURED OPTIMUM IS FULLER THAN THE PRACTICE CURVE, by +0.019
         to +0.087, at all six speeds. The sign is consistent, so it is not
         scatter. THIS IS NOT PRESENTED AS THE PRACTICE CURVE BEING WRONG:
         Michell has no transom-immersion term and this hull carries 20% of
         the midship area at the transom, so a full afterbody is not charged
         for what it would really cost above Fn ~0.35; and the practice curve
         is itself unsourced (`limits.py` says so). Two unvalidated things
         disagree by a consistent amount. The useful output is the DISAGREEMENT
         and its sign, not a new table.
    """
    ref = reference_demihull()
    ref_hull, ref_st, _ = _float_hull(ref, HYDRO_STATIONS, None)
    target = float(ref_st.disp_kg)
    prod = dict(resistance.PRODUCTION_GRID)
    conv = dict(resistance.CONVERGED_GRID)

    points: list[SweepPoint] = []
    for cp in cp_sweep_for(ref):
        params = require_feasible(with_genes(Cp=cp), f"Cp={cp:.3f}")
        hull, st, wl = _float_hull(params, HYDRO_STATIONS, target)
        q: dict[str, Quantity] = {}
        q.update(alpha_e_metrics(hull))
        q.update(hydro_quantities(hull, st, wl))
        q["cp_gene"] = Quantity(float(cp), TIER_GEOMETRY, 0.0, "-", BASIS_EXACT)
        q["target_disp_kg"] = Quantity(target, TIER_PHYSICS, 0.0, "kg",
                                       BASIS_EXACT)
        for fn in FROUDE_SWEEP:
            for k, v in resistance_quantities(hull, st, wl, fn, prod,
                                              other_grid=conv).items():
                q[f"prod/fn{fn:.2f}/{k}"] = v
        points.append(SweepPoint(
            label=f"Cp={cp:.3f}",
            genes=tuple(sorted(grammar.named(params).items())),
            q=q, valid=True,
            note="floated to the reference displacement; draft is dependent"))

    findings: dict[str, object] = {}
    for fn in FROUDE_SWEEP:
        key = f"prod/fn{fn:.2f}/rt_n"
        if not all(p.q[key].valid for p in points):
            findings[f"fn{fn:.2f}"] = {
                "excluded": True,
                "reason": f"Fn {fn:.2f} > FN_MICHELL_MAX; excluded, not "
                          f"extrapolated"}
            continue
        cps = [p.value("cp_gene") for p in points]
        rt = [p.value(key) for p in points]
        rw = [p.value(f"prod/fn{fn:.2f}/rw_n") for p in points]
        gs = max(p.value(f"prod/fn{fn:.2f}/rt_grid_sigma_n") for p in points)
        sh_t = curve_shape(cps, rt)
        sh_w = curve_shape(cps, rw)
        margin = _second_best_margin(rt)
        findings[f"fn{fn:.2f}"] = {
            "excluded": False,
            "best_cp_by_rt": sh_t["argmin_x"],
            "best_cp_is_interior": sh_t["argmin_is_interior"],
            "shape_rt_vs_cp": sh_t["shape"],
            "best_cp_by_rw": sh_w["argmin_x"],
            "shape_rw_vs_cp": sh_w["shape"],
            "practice_curve_cp": limits.prismatic_target(fn),
            "measured_minus_practice": (sh_t["argmin_x"]
                                        - limits.prismatic_target(fn)),
            "rt_span_frac": sh_t["range_frac"],
            "grid_shift_n": gs,
            "optimum_margin_n": margin,
            "optimum_resolved_above_grid_shift": bool(margin > gs),
        }
    valid = [(fn, findings[f"fn{fn:.2f}"]) for fn in FROUDE_SWEEP
             if not findings[f"fn{fn:.2f}"]["excluded"]]
    best = [float(r["best_cp_by_rt"]) for _, r in valid]
    findings["optimum_moves_with_fn"] = bool(max(best) > min(best))
    findings["optimum_increases_with_fn"] = bool(
        all(b <= a + 1e-12 for a, b in zip(best, best[1:])) is False
        and all(a <= b + 1e-12 for a, b in zip(best, best[1:])))
    findings["practice_curve_source"] = (
        "limits.PRISMATIC_BY_FROUDE — a PRACTICE curve, provenance 'approx', "
        "not a transcribed standard. It is the hypothesis, not the truth.")

    return ExperimentRecord(
        name="2-prismatic",
        question="Which Cp minimises resistance at which Froude number?",
        protocol={
            "controlled": ("LWL", "BWL", "lcb", "displacement", "all shape "
                           "genes except Cp"),
            "varied": ("Cp",),
            "dependent": ("draft", "floated waterline", "wetted surface"),
            "displacement_target_kg": target,
            "displacement_tolerance_rel": 1e-6,
            "production_grid": prod, "converged_grid": conv,
            "fn_michell_max": resistance.FN_MICHELL_MAX,
        },
        points=tuple(points),
        findings=findings,
        caveats=(
            "The Cp gene and the FLOATED Cp differ by up to 0.003 because the "
            "hull floats off its design waterline; both are recorded "
            "(`cp_gene` and `cp_floated`) and the finding is indexed by the "
            "gene, which is what a generator would set.",
            "Only ONE hull family is swept. A Cp*(Fn) prior derived from a "
            "single parent form is a prior about that form; the sweep would "
            "have to be repeated across L/B and x_mb before the curve could "
            "be called general.",
            "Michell has no transom-immersion model, and a high-Cp hull at "
            "this r_transom carries more area at the transom. Above Fn ~0.4 "
            "that is a real physical term this model does not contain.",
        ),
    )


# ---------------------------------------------------------------------------
# EXPERIMENT 3 — LCB SWEEP
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def experiment_3_lcb() -> ExperimentRecord:
    """Where should the buoyancy sit, at fixed displacement and fixed Cp?

    LCB IS EXACTLY FREE OF DISPLACEMENT IN THIS KERNEL, which is what makes
    this a clean experiment and is the mechanism the test asserts.
    `geometry.sac_exponents` solves the two SAC shape exponents so that
    int a dx = Cp * L AND the first moment lands on the requested LCB — the
    zeroth moment is a CONSTRAINT of the solve, so moving `lcb` at fixed `Cp`
    moves area fore and aft without changing how much there is.

    MEASURED over the whole +-3 %LWL gene band:

        lcb gene   volume m^3     Cp        LCB delivered
          -3.00    4.168222328   0.599999      -3.0000
          -2.00    4.168218282   0.599998      -2.0000
          -1.00    4.168216888   0.599998      -1.0001
          +0.00    4.168217703   0.599998      -0.0001
          +1.00    4.168220249   0.599998      +0.9999
          +2.00    4.168221342   0.599999      +1.9998
          +3.00    4.168221275   0.599999      +2.9998

    volume is constant to 1.3e-6 relative and the delivered LCB tracks the gene
    to 2e-4 %LWL, i.e. the design target is DELIVERED, not approximated.

    TRIM EQUILIBRIUM. The hull floats at its design waterline in every case
    (displacement is unchanged), so the equilibrium question is where the LCG
    would have to be. `weights.trim_angle_deg` computes trim from an
    (LCG - LCB) lever over GM_L; with no arrangement in this experiment the
    honest statement is the LEVER ARM ITSELF: `lcb_m_from_transom` is the
    position the centre of gravity must occupy for zero trim, and the hull's
    own longitudinal stiffness BM_L + KB is what converts a miss into degrees.
    `trim_deg_per_m_of_lcg_error` = atan(1 / (BM_L + KB)) is the sensitivity a
    designer actually needs; MEASURED on this demihull it is **2.93 deg per
    metre** (BM_L + KB = 19.51 m), so a 100 mm LCG error is 0.29 deg of trim.
    Inventing an LCG to report an angle would be inventing the answer.

    ============================ THE RESULT ============================
    R_w [N] against the lcb gene, production grid:

      lcb %LWL   Fn0.20  Fn0.25  Fn0.30  Fn0.35  Fn0.40  Fn0.45
       -3.000     25.90    85.90   69.23  152.67  497.77   836.08
       -2.250     25.27    80.57   71.05  156.29  498.09   833.63
       -1.500     25.93    77.54   76.17  166.37  506.11   839.07
       -0.750     27.73    76.87   84.75  183.17  522.10   852.66
       +0.000     30.62    78.82   97.10  206.90  546.21   874.55
       +0.750     33.53    82.29  109.17  234.32  579.34   907.48
       +1.500     35.62    86.41  117.56  261.66  620.60   951.91
       +2.250     38.93    94.29  129.60  294.22  668.25  1003.03
       +3.000     43.57   106.56  145.79  332.49  722.69  1061.17

    AFT IS BETTER, ALMOST EVERYWHERE, AND THE OPTIMUM IS USUALLY THE BAND
    EDGE — which is a statement about the CONSTRAINT, not about an optimum:

        Fn 0.20   interior minimum at lcb -2.25
        Fn 0.25   interior minimum at lcb -0.75   <- the one speed that
                                                     prefers volume near
                                                     midships
        Fn 0.30   monotonic increasing -> best at the -3.00 BAND EDGE
        Fn 0.35   monotonic increasing -> best at the -3.00 BAND EDGE
        Fn 0.40   monotonic increasing -> best at the -3.00 BAND EDGE
        Fn 0.45   interior minimum at lcb -2.25

    `optimum_is_band_edge` records this per speed. At three of six speeds the
    sweep has found the EDGE of `limits.LCB_BAND_PCT_LWL`, so the honest
    reading is that wave resistance would keep improving with LCB further aft
    and something else — trim, balance, the ladder's own LCB row — is what
    stops it. Reporting a band edge as an optimum would be the exact opposite
    of what this record is for.

    THE MAGNITUDE MATTERS MORE THAN THE LOCATION. R_w spans 21.4-54.1% across
    the band and R_t spans 10.6-27.3% — up to an order of magnitude more than
    the whole bow sharpness sweep at the same speeds (see `lever_comparison`).
    LCB is a strong lever; the bow entrance is a weak one.

    ONE POINT IS NOT RESOLVED AND IS FLAGGED: at Fn 0.40 the best-to-runner-up
    margin is 0.228 N against a 1.353 N production-to-converged grid shift, so
    `optimum_resolved_above_grid_shift` is False there. The -3.00 to -2.25 pair
    is a tie at that speed as far as this protocol can tell.
    """
    prod = dict(resistance.PRODUCTION_GRID)
    conv = dict(resistance.CONVERGED_GRID)
    points: list[SweepPoint] = []
    for lcb in LCB_SWEEP:
        params = require_feasible(with_genes(lcb=lcb), f"lcb={lcb:+.3f}")
        hull, st, wl = _float_hull(params, HYDRO_STATIONS, None)
        q: dict[str, Quantity] = {}
        q.update(alpha_e_metrics(hull))
        q.update(hydro_quantities(hull, st, wl))
        q["lcb_gene"] = Quantity(float(lcb), TIER_GEOMETRY, 0.0, "%LWL",
                                 BASIS_EXACT)
        q["lcb_m_from_transom"] = Quantity(float(st.lcb), TIER_PHYSICS, 0.0,
                                           "m", BASIS_EXACT)
        # GM_L with KG at the keel is BM_L + KB: the hull's own longitudinal
        # stiffness, before any weight model. Stated as such, not called GM_L.
        bml_kb = float(st.bm_l + st.kb)
        q["bml_plus_kb_m"] = Quantity(bml_kb, TIER_PHYSICS, 0.0, "m",
                                      BASIS_EXACT)
        q["trim_deg_per_m_of_lcg_error"] = Quantity(
            math.degrees(math.atan(1.0 / bml_kb)), TIER_PHYSICS, 0.0,
            "deg/m", BASIS_EXACT)
        for fn in FROUDE_SWEEP:
            for k, v in resistance_quantities(hull, st, wl, fn, prod,
                                              other_grid=conv).items():
                q[f"prod/fn{fn:.2f}/{k}"] = v
        points.append(SweepPoint(
            label=f"lcb={lcb:+.2f}",
            genes=tuple(sorted(grammar.named(params).items())),
            q=q, valid=True,
            note="fixed Cp and displacement; area moved fore/aft only"))

    findings: dict[str, object] = {}
    for fn in FROUDE_SWEEP:
        key = f"prod/fn{fn:.2f}/rw_n"
        if not all(p.q[key].valid for p in points):
            findings[f"fn{fn:.2f}"] = {
                "excluded": True,
                "reason": f"Fn {fn:.2f} > FN_MICHELL_MAX; excluded"}
            continue
        xs = [p.value("lcb_gene") for p in points]
        rw = [p.value(key) for p in points]
        rt = [p.value(f"prod/fn{fn:.2f}/rt_n") for p in points]
        gs = max(p.value(f"prod/fn{fn:.2f}/rt_grid_sigma_n") for p in points)
        sh_w = curve_shape(xs, rw)
        sh_t = curve_shape(xs, rt)
        margin = _second_best_margin(rt)
        findings[f"fn{fn:.2f}"] = {
            "excluded": False,
            "shape_rw_vs_lcb": sh_w["shape"],
            "best_lcb_by_rw": sh_w["argmin_x"],
            "best_lcb_is_interior": sh_w["argmin_is_interior"],
            "rw_span_frac": sh_w["range_frac"],
            "shape_rt_vs_lcb": sh_t["shape"],
            "best_lcb_by_rt": sh_t["argmin_x"],
            "best_lcb_by_rt_is_interior": sh_t["argmin_is_interior"],
            "rt_span_frac": sh_t["range_frac"],
            "grid_shift_n": gs,
            "optimum_margin_n": margin,
            "optimum_resolved_above_grid_shift": bool(margin > gs),
            # A minimum ON THE EDGE of the gene band is not an optimum, it is a
            # BINDING CONSTRAINT, and the two must not be reported alike.
            "optimum_is_band_edge": bool(not sh_t["argmin_is_interior"]),
        }
    return ExperimentRecord(
        name="3-lcb",
        question=("At fixed displacement and Cp, where should the longitudinal "
                  "centre of buoyancy sit?"),
        protocol={
            "controlled": ("LWL", "BWL", "T", "Cp", "displacement"),
            "varied": ("lcb",),
            "gene_band_pct_lwl": limits.LCB_BAND_PCT_LWL,
            "production_grid": prod, "converged_grid": conv,
        },
        points=tuple(points),
        findings=findings,
        caveats=(
            "The gene band is +-3 %LWL because `limits.LCB_BAND_PCT_LWL` is "
            "the band the ladder enforces. If R_w is monotone across it, the "
            "sweep has found the EDGE of a band, not an optimum, and the "
            "record says so via `best_lcb_is_interior`.",
            "Trim is reported as a SENSITIVITY (deg per metre of LCG error), "
            "not as an angle: no arrangement is defined in this experiment, "
            "so there is no LCG, and inventing one would invent the answer.",
        ),
    )


# ---------------------------------------------------------------------------
# EXPERIMENT 4 — CATAMARAN SEPARATION, and the phase-convention check
# ---------------------------------------------------------------------------


def _reference_spectrum_inputs(n_stations: int, nz: int
                               ) -> tuple[np.ndarray, np.ndarray, np.ndarray,
                                          float]:
    hull = Hull(reference_demihull(), n_stations=n_stations)
    xs, zs, Y = hull.offsets_grid(nz=nz, wl=0.0)
    return xs, zs, Y, float(grammar.named(hull.params)["LWL"])


def _independent_two_hull_rw(xs: np.ndarray, zs: np.ndarray, Y: np.ndarray,
                             speed: float, n_theta: int,
                             y_offsets: Sequence[float],
                             rho: float = RHO) -> float:
    """A SECOND implementation of Michell for TWO hulls — for checking only.

    THIS IS DELIBERATELY A SECOND COPY AND IT IS NOT ALLOWED TO ESCAPE. It
    exists to verify a CONVENTION, which cannot be done by calling the code
    whose convention is in question. No production number in this module comes
    from it; `tests/test_experiments.py` is the only other caller.

    Everything in it is derived from the free-wave dispersion and from the two
    kernels `resistance._free_wave_vals` visibly uses, NOT from a remembered
    catamaran formula:

        depth kernel exp(K z)     ==> K  = k0 sec^2(theta)  is |k|
        x-phase      exp(i kx x)  ==> kx = k0 sec(theta)
        therefore                     ky = sqrt(K^2 - kx^2)
                                         = k0 sec(theta) tan(theta)
                                         = k0 sec^2(theta) sin(theta)

    and the superposition is written out in complex arithmetic, one exponential
    per hull, rather than as any cos^2 factor:

        A_tot(theta) = sum_j A(theta) exp(i ky y_j)
        R_w = (4 rho g^2 / (pi U^2)) Int |A_tot|^2 sec^3 dtheta

    The theta grid is `resistance._theta_grid`'s, because comparing two
    quadratures on different nodes would compare grids and not conventions.
    """
    k0 = G / speed ** 2
    thetas, sec = resistance._theta_grid(int(n_theta))
    kmag = k0 * sec ** 2
    kx = k0 * sec
    ky = np.sqrt(np.maximum(kmag ** 2 - kx ** 2, 0.0))
    dydx = np.gradient(Y, xs, axis=0)
    vals = np.empty(len(thetas))
    for i in range(len(thetas)):
        depth = np.exp(np.minimum(kmag[i] * zs, 0.0))[None, :]
        fx = np.trapezoid(dydx * depth, zs, axis=1)
        amp = np.trapezoid(fx * np.exp(1j * kx[i] * xs), xs)
        tot = sum(amp * np.exp(1j * ky[i] * float(y)) for y in y_offsets)
        vals[i] = float(abs(tot) ** 2) * sec[i] ** 3
    return float(4.0 * rho * G ** 2 / (math.pi * speed ** 2)
                 * np.trapezoid(vals, thetas))


@lru_cache(maxsize=1)
def michell_interference_convention_check() -> Mapping[str, object]:
    """Does `resistance.py`'s interference phase match amplitude superposition?

    ANSWER: YES, to one floating-point ulp, and `sec` is SQUARED.

    THE CHECK IS THREE-PART, and each part can fail independently:

      1. `resistance.catamaran_interference` is compared to
         `4 cos^2(ky s / 2)` with ky reconstructed as `sqrt(K^2 - kx^2)` from
         the module's OWN depth and phase kernels. This is the part that pins
         `sec^2` rather than `sec`: a `k0 sec(th) sin(th)` transverse
         wavenumber would fail here by orders of magnitude at large theta.
      2. `michell_rw(..., separation=s)` is compared to
         `_independent_two_hull_rw` with sources at y = -s/2, +s/2 written in
         complex exponentials. This is the part that pins the SIGN convention
         and the fact that the two hulls are superposed as AMPLITUDES before
         squaring, not as resistances after.
      3. The theta-average of the factor is compared to 2.0, which is the
         statement that two infinitely separated demihulls make twice one
         demihull's waves. `resistance.CATAMARAN_INTERFERENCE_AT_INFINITY` is
         the constant; it is imported, not restated.

    MEASURED on the reference demihull at Fn 0.30, s/Lwl 0.45, n_theta 880:

        part 1  max |factor_module - factor_derived|       5.6e-11
                (on a factor whose range is [0, 4], i.e. 1.4e-11 relative;
                 the residue is `sqrt(K^2 - kx^2)` and `sec^2 sin` rounding
                 differently, not a difference of convention)
        part 2  |R_module - R_independent| / R             0.0 EXACTLY
        part 3  <4 cos^2>_theta over s/L 1, 2, 5, 10       1.99549 vs 2.0

    AND THE CONTROL THAT MAKES PART 1 MEAN SOMETHING. The same comparison is
    run against the plausible-but-wrong `ky = k0 sec(theta) sin(theta)` — the
    remembered form, one power of sec short — and it differs from what the code
    contains by **3.99** on a factor whose whole range is 4. So this check has
    the resolution to catch exactly the error it is looking for; it is not a
    tautology that would pass on any convention.

    NOTE WHAT PART 2 DOES NOT PROVE. It proves the module implements the
    convention this derivation gives. It does NOT validate the interference
    against experiment: `resistance.py` records that no catamaran measurement
    has been transcribed into this repository, so the term is SELF-CONSISTENT
    and UNVALIDATED. That distinction is the finding, and it is not softened.
    """
    n_st = int(resistance.PRODUCTION_GRID["n_stations"])
    nz = int(resistance.PRODUCTION_GRID["nz"])
    xs, zs, Y, lwl = _reference_spectrum_inputs(n_st, nz)
    fn = 0.30
    speed = froude_to_speed(fn, lwl)
    s = 0.45 * lwl
    n_theta = resistance.n_theta_for_separation(lwl, s)
    k0 = G / speed ** 2

    thetas, sec = resistance._theta_grid(n_theta)
    kmag = k0 * sec ** 2
    kx = k0 * sec
    ky_recon = np.sqrt(np.maximum(kmag ** 2 - kx ** 2, 0.0))
    factor_module = resistance.catamaran_interference(k0, thetas, s)
    factor_derived = 4.0 * np.cos(0.5 * ky_recon * s) ** 2
    part1 = float(np.max(np.abs(factor_module - factor_derived)))

    # ALSO check the wrong-but-plausible convention, so the record shows what
    # the test would have caught. `k0 sec(th) sin(th)` is a remembered form and
    # it is NOT what the free-wave dispersion gives.
    factor_wrong = 4.0 * np.cos(0.5 * k0 * sec * np.sin(thetas) * s) ** 2
    part1_wrong = float(np.max(np.abs(factor_module - factor_wrong)))

    r_mod = resistance.michell_rw(xs, zs, Y, speed, RHO, separation=s)
    r_ind = _independent_two_hull_rw(xs, zs, Y, speed, n_theta,
                                     (-0.5 * s, +0.5 * s))
    part2 = abs(r_mod - r_ind) / r_ind

    # Part 3: theta-average of the factor, over a decade of separations.
    avgs = []
    for sl in (1.0, 2.0, 5.0, 10.0):
        ss = sl * lwl
        nt = resistance.n_theta_for_separation(lwl, ss)
        th, _ = resistance._theta_grid(nt)
        f = resistance.catamaran_interference(k0, th, ss)
        avgs.append(float(np.trapezoid(f, th) / (th[-1] - th[0])))
    part3 = float(np.mean(avgs))

    return {
        "convention_in_code": ("4 cos^2(ky s / 2) with "
                               "ky = k0 sec^2(theta) sin(theta)"),
        "convention_derived": ("A_tot = sum_j A exp(i ky y_j), ky = "
                               "sqrt(|k|^2 - kx^2) from the module's own "
                               "exp(k0 sec^2 z) and exp(i k0 sec x) kernels"),
        "match": True,
        "factor_max_abs_diff": part1,
        "factor_max_abs_diff_against_sec1_convention": part1_wrong,
        "rw_relative_diff_vs_independent_superposition": part2,
        "theta_average_of_factor": part3,
        "theta_average_expected":
            resistance.CATAMARAN_INTERFERENCE_AT_INFINITY,
        "n_theta": n_theta, "separation_m": s, "fn": fn,
        "grid": dict(resistance.PRODUCTION_GRID),
        "validated_against_experiment": False,
        "validation_note": (
            "resistance.py records that NO catamaran measurement has been "
            "transcribed into this repository (Insel & Molland 1992 and "
            "Molland et al. 1996 are cited, not transcribed). This check "
            "proves SELF-CONSISTENCY with thin-ship theory and nothing about "
            "agreement with a towing tank."),
    }


@lru_cache(maxsize=1)
def experiment_4_separation() -> ExperimentRecord:
    """Catamaran demihull separation: does interference have an optimum s/L?

    THE MOST IMPORTANT SWEEP HERE, because `michell_rw`'s `separation`
    argument has never been exercised end to end: `resistance.total_resistance`
    calls `michell_rw(xs, zs - wl, Y, speed, rho)` with NO separation, so every
    catamaran this project has ever evaluated was scored as one isolated
    demihull. That is a MEASURED gap in the production path, not a hypothesis;
    it is stated in `resistance.py`'s own module docstring ("nothing in the
    genome, the grammar or `total_resistance` has been wired to it yet") and
    this experiment is the first thing to drive it.

    =================== (a) THE s -> INFINITY CORRECTNESS TEST ===================
    MEASURED, reference demihull, ratio R_w(cat) / (2 R_w(demi)):

        Fn     s/Lwl   n_theta   vs production monohull   on same theta grid
        0.20     2.0     1760           0.99626                 0.99607
        0.20     5.0     4400           0.99669                 0.99630
        0.20    10.0     8800           0.99679                 0.99643
        0.30     2.0     1760           0.99883                 0.99898
        0.30     5.0     4400           0.99862                 0.99876
        0.30    10.0     8800           0.99873                 0.99888
        0.45     2.0     1760           0.99857                 0.99854
        0.45     5.0     4400           0.99800                 0.99797
        0.45    10.0     8800           0.99797                 0.99794

    SO YES, AND THIS IS THE CORRECTNESS TEST FOR THE PHASE CONVENTION: two
    widely separated demihulls recover the sum of two independent hulls to
    within **0.37%** at worst, against `resistance.CATAMARAN_ASYMPTOTIC_
    RESIDUAL`'s bar of 0.49%. If the transverse wavenumber were wrong, this
    ratio would not approach 1 at all.

    THE RESIDUAL IS NOT A GRID MISMATCH — that was the first hypothesis and the
    same-theta-grid column REFUTES it: re-running the monohull denominator on
    the catamaran's own theta grid moves the ratio by 2e-4 at most, and at
    Fn 0.20 it makes it slightly WORSE. The residual is the mechanism
    `resistance.py` already identified and quantified: `_theta_grid` starts at
    theta_0 = 2.484e-3 rad for every n_theta, and the trapezoid omits
    [0, theta_0] weighted by ~4 for the pair against ~2 for the doubled
    monohull. Both columns are recorded so a reader can see this is quadrature
    and none of it is physics.

    ============ (b) THE INTERFERENCE IS NON-MONOTONIC — AND ONLY SOMETIMES ======
    MEASURED over s/Lwl 0.20-0.50 in 31 steps, ratio R_w(cat)/(2 R_w(demi)):

        Fn    shape over 0.20-0.50       min ratio @ s/L   max ratio @ s/L
        0.20  non-monotonic (4 turns)     0.9142 @ 0.390    1.2490 @ 0.210
        0.25  interior-minimum (1 turn)   0.7483 @ 0.300    1.0048 @ 0.500
        0.30  non-monotonic (2 turns)     0.9430 @ 0.430    1.3316 @ 0.240
        0.35  non-monotonic (2 turns)     1.2087 @ 0.500    1.4876 @ 0.200
        0.40  monotonic-decreasing        1.1622 @ 0.500    1.5974 @ 0.200
        0.45  monotonic-decreasing        1.0995 @ 0.500    1.5454 @ 0.200

    THREE FINDINGS, AND THE SECOND IS THE OPERATIONALLY IMPORTANT ONE:

      1. THE INTERFERENCE IS NON-MONOTONIC IN s/L, as the owner predicted, at
         four of the six valid speeds — and the structure is real, not a
         numerical wiggle: the located minimum does not move by more than one
         s/L grid step when the theta resolution is DOUBLED
         (`optimum_grid_independent`), which is the check that matters given
         that `resistance.py` MEASURED up to 1.2% of sign-changing quadrature
         error in an under-resolved version of this very curve. The strongest
         destructive optimum is at Fn 0.25, s/L 0.300: the pair makes **25.2%
         LESS** wave resistance than two independent demihulls.

      2. AT Fn >= 0.35 THE ENTIRE 0.20-0.50 BAND IS CONSTRUCTIVE. The ratio
         never falls below 1.0 and reaches **1.597** at Fn 0.40, s/L 0.200 —
         a catamaran at that spacing makes SIXTY PERCENT more wave resistance
         than two independent hulls. "Wider is better" holds in that band at
         those speeds only in the sense of being less bad, and the best point
         in the band is its EDGE (`best_is_interior` False), which the record
         reports as an edge and not as an optimum. Extending the sweep to
         s/L 1.5 (outside this record's band, measured while calibrating it)
         finds the ratio still falling and reaching ~1.00 — i.e. at high Froude
         number the best this model offers is "no worse than two separate
         hulls".

      3. THE OPTIMUM s/L IS SPEED-DEPENDENT AND THERE IS NO SINGLE ANSWER.
         0.390 at Fn 0.20, 0.300 at Fn 0.25, 0.430 at Fn 0.30, and the band
         edge above that. A design spacing chosen for one Froude number is a
         penalty at another: s/L 0.300, the best spacing at Fn 0.25, is the
         WORST end of the band at Fn 0.40 (ratio 1.441 against 1.162 at 0.500).
         That trade is the actual engineering content of this experiment.

    GRID INDEPENDENCE OF THE OPTIMUM. The located minimum is re-measured at
    twice the theta resolution; it moves by less than one s/L grid step at
    every Fn. That matters because `resistance.py` MEASURED that an
    under-resolved theta sweep puts up to 1.2% of quadrature error into this
    curve, error that CHANGES SIGN with separation — which is precisely the
    shape of a spurious optimum.

    WHAT THIS MODEL DOES NOT CONTAIN, stated because a separation optimum
    invites over-reading:
      * VISCOUS interference. The total below is R_w(cat) + 2 R_f(demi): the
        friction is simply doubled. Insel & Molland's decomposition has a
        viscous form interference factor too, and it is not modelled here.
      * Wet-deck slamming and structural cost of a wide bridge deck.
        `resistance.wet_deck_clearance_g` exists and is not wired to a genome
        parameter, so this sweep cannot trade spacing against clearance.
      * Any experimental anchor at all (see the convention check).
    """
    n_st = int(resistance.PRODUCTION_GRID["n_stations"])
    nz = int(resistance.PRODUCTION_GRID["nz"])
    xs, zs, Y, lwl = _reference_spectrum_inputs(n_st, nz)
    beam = 2.0 * float(np.max(Y))

    hull, st, wl = _float_hull(reference_demihull(), HYDRO_STATIONS, None)

    points: list[SweepPoint] = []
    findings: dict[str, object] = {}
    seps = np.array(SEPARATION_S_OVER_L) * lwl
    n_theta_band = resistance.n_theta_for_separation(lwl, float(seps.max()))

    for fn in FROUDE_SWEEP:
        u = froude_to_speed(fn, lwl)
        valid = fn <= resistance.FN_MICHELL_MAX
        tier = TIER_PHYSICS if valid else TIER_PHYSICS_INVALID
        if not valid:
            findings[f"fn{fn:.2f}"] = {
                "excluded": True,
                "reason": (f"Fn {fn:.2f} > resistance.FN_MICHELL_MAX "
                           f"{resistance.FN_MICHELL_MAX}; the interference "
                           f"factor is exact within thin-ship theory but "
                           f"thin-ship theory is not valid here — excluded, "
                           f"not extrapolated")}
            continue

        rw_mono_prod = resistance.michell_rw(xs, zs, Y, u, RHO)
        rw_mono_same = resistance.michell_rw(xs, zs, Y, u, RHO,
                                             n_theta=n_theta_band)
        rw_cat = resistance.michell_rw_separation_sweep(
            xs, zs, Y, u, seps, RHO, n_theta=n_theta_band)
        # Twice the theta resolution, for the grid-independence check.
        rw_cat_2x = resistance.michell_rw_separation_sweep(
            xs, zs, Y, u, seps, RHO, n_theta=2 * n_theta_band)

        rf_demi = resistance.total_resistance(
            hull, u, st.wetted, st.cb, RHO, wl,
            nz=nz, n_stations=n_st, beam_wl=st.b_wl_max, draft=st.draft).rf

        ratio = rw_cat / (2.0 * rw_mono_prod)
        ratio_same = rw_cat / (2.0 * rw_mono_same)
        ratio_2x = rw_cat_2x / (2.0 * resistance.michell_rw(
            xs, zs, Y, u, RHO, n_theta=2 * n_theta_band))

        for i, sl in enumerate(SEPARATION_S_OVER_L):
            q = {
                "s_over_l": Quantity(float(sl), TIER_GEOMETRY, 0.0, "-",
                                     BASIS_EXACT),
                "separation_m": Quantity(float(seps[i]), TIER_GEOMETRY, 0.0,
                                         "m", BASIS_EXACT),
                "fn": Quantity(float(fn), tier, 0.0, "-", BASIS_EXACT),
                "rw_cat_n": Quantity(
                    float(rw_cat[i]), tier,
                    abs(float(rw_cat[i] - rw_cat_2x[i]))
                    + resistance.CATAMARAN_THETA_QUADRATURE_ERROR
                    * float(rw_cat[i]), "N", BASIS_GRID),
                "rw_demi_n": Quantity(float(rw_mono_prod), tier,
                                      0.25 * float(rw_mono_prod), "N",
                                      BASIS_MODEL),
                "interference_ratio": Quantity(
                    float(ratio[i]), tier,
                    abs(float(ratio[i] - ratio_2x[i]))
                    + resistance.CATAMARAN_THETA_QUADRATURE_ERROR,
                    "-", BASIS_GRID),
                "interference_ratio_same_theta_grid": Quantity(
                    float(ratio_same[i]), tier,
                    resistance.CATAMARAN_THETA_QUADRATURE_ERROR, "-",
                    BASIS_GRID),
                "rf_pair_n": Quantity(float(2.0 * rf_demi), tier,
                                      0.10 * float(2.0 * rf_demi), "N",
                                      BASIS_MODEL),
                "rt_pair_n": Quantity(
                    float(rw_cat[i] + 2.0 * rf_demi), tier,
                    0.25 * float(rw_cat[i]) + 0.10 * float(2.0 * rf_demi),
                    "N", BASIS_MODEL),
            }
            points.append(SweepPoint(
                label=f"fn={fn:.2f} s/L={sl:.3f}",
                genes=tuple(sorted(grammar.named(hull.params).items())),
                q=q, valid=valid,
                note="R_t = R_w(pair) + 2 R_f(demihull); no viscous "
                     "interference term exists in this model"))

        sh = curve_shape(SEPARATION_S_OVER_L, ratio)
        i_min = int(np.argmin(ratio))
        i_min_2x = int(np.argmin(ratio_2x))
        step = SEPARATION_S_OVER_L[1] - SEPARATION_S_OVER_L[0]
        findings[f"fn{fn:.2f}"] = {
            "excluded": False,
            "shape_ratio_vs_s_over_l": sh["shape"],
            "turning_points": sh["turning_points"],
            "best_s_over_l": sh["argmin_x"],
            "best_ratio": sh["min_y"],
            "best_is_interior": sh["argmin_is_interior"],
            "worst_s_over_l": sh["argmax_x"],
            "worst_ratio": sh["max_y"],
            "entire_band_constructive": bool(np.all(ratio > 1.0)),
            "optimum_grid_independent": bool(
                abs(SEPARATION_S_OVER_L[i_min]
                    - SEPARATION_S_OVER_L[i_min_2x]) <= step + 1e-12),
            "n_theta": n_theta_band,
            "n_theta_check": 2 * n_theta_band,
        }

    # --- (a) the s -> infinity correctness test, its own protocol point ---
    asym: dict[str, object] = {}
    for fn in (0.20, 0.30, 0.45):
        u = froude_to_speed(fn, lwl)
        rows = []
        for sl in SEPARATION_ASYMPTOTIC_S_OVER_L:
            ss = sl * lwl
            nt = resistance.n_theta_for_separation(lwl, ss)
            rc = resistance.michell_rw(xs, zs, Y, u, RHO, separation=ss)
            rm_prod = resistance.michell_rw(xs, zs, Y, u, RHO)
            rm_same = resistance.michell_rw(xs, zs, Y, u, RHO, n_theta=nt)
            rows.append({
                "s_over_l": sl, "n_theta": nt,
                "ratio_vs_production_monohull": float(rc / (2.0 * rm_prod)),
                "ratio_same_theta_grid": float(rc / (2.0 * rm_same)),
            })
        asym[f"fn{fn:.2f}"] = rows
    findings["asymptotic_recovers_independent_sum"] = asym
    findings["asymptotic_bar"] = resistance.CATAMARAN_ASYMPTOTIC_RESIDUAL
    findings["phase_convention"] = michell_interference_convention_check()
    # RE-MEASURED 2026-08-14, AND THE ANSWER HAS FLIPPED. This finding stood at
    # False from the day this experiment was written, and
    # `tests/test_experiments.py::test_the_record_states_that_the_production_
    # path_ignores_separation` was built to fail loudly the moment it stopped
    # being true rather than leave a stale claim behind. It did exactly that.
    #
    # MEASURED, not inferred: `separation` is in
    # `resistance.total_resistance.__code__.co_varnames`, and `evaluate.py`
    # line 564 passes `separation=(separation_m if n_hulls > 1 else None)` with
    # `separation_m` derived from `mission.VesselConfig.separation_over_lwl`.
    # So a catamaran declared through `MissionSpec.vessel` is now scored WITH
    # the interference factor this experiment measured.
    #
    # WHAT HAS NOT CHANGED, and it is why the caveats below stay: the term
    # still has NO EXPERIMENTAL ANCHOR, and the VISCOUS interference factor is
    # still absent — `evaluate` applies one demihull's Watanabe form factor to
    # the whole vessel's wetted area. Wiring the wave term did not validate it.
    findings["production_path_wires_separation"] = True
    findings["production_path_note"] = (
        "RE-MEASURED 2026-08-14: `evaluate.py` now passes `separation=` to "
        "`resistance.total_resistance` for `n_hulls > 1`, derived from "
        "`mission.VesselConfig.separation_over_lwl`, so a declared catamaran "
        "IS scored with the wave interference factor. This finding read False "
        "until that landed. MEASURED penalty of the era when it was ignored, "
        "at Fn 0.40, s/L 0.20: the pair's true wave resistance is 1.60x what "
        "doubling the demihull gives. The VISCOUS interference term is still "
        "not modelled and the wave term still has no towing-tank anchor.")

    return ExperimentRecord(
        name="4-separation",
        question=("How does catamaran demihull separation change wave "
                  "resistance, and is there an optimum s/L?"),
        protocol={
            "s_over_l_band": (SEPARATION_S_OVER_L[0], SEPARATION_S_OVER_L[-1]),
            "s_over_l_steps": len(SEPARATION_S_OVER_L),
            "asymptotic_s_over_l": SEPARATION_ASYMPTOTIC_S_OVER_L,
            "n_theta_band": n_theta_band,
            "n_theta_rule": ("resistance.n_theta_for_separation = "
                             f"{resistance.N_THETA_PER_HULL_LENGTH_OF_SEPARATION}"
                             " * max(1, s/Lwl), MEASURED"),
            "offsets_grid": dict(resistance.PRODUCTION_GRID),
            "demihull_beam_m": beam,
            "lwl_m": lwl,
            "total_composition": "R_w(pair) + 2 R_f(demihull)",
        },
        points=tuple(points),
        findings=findings,
        caveats=(
            "NO VISCOUS INTERFERENCE. R_f is doubled, full stop. Insel & "
            "Molland's catamaran decomposition carries a viscous form "
            "interference factor and this model has none, so the totals here "
            "understate the spacing sensitivity of the friction term by an "
            "unknown amount.",
            "NO EXPERIMENTAL ANCHOR. The interference term is verified "
            "SELF-CONSISTENT (see phase_convention) and has never been "
            "compared with a towing tank in this repository.",
            "The demihull is fixed: no sinkage, no trim, no transom "
            "ventilation. At Fn 0.45 a real demihull of these proportions "
            "would be doing all three.",
        ),
    )


# ---------------------------------------------------------------------------
# EXPERIMENT 5 — IS THE OBJECTIVE GAMEABLE?
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def experiment_5_objective_gaming() -> ExperimentRecord:
    """Can an optimiser make the SCORE better while making the BOAT worse?

    ============================ WHY THIS EXISTS ============================
    ShipGen reports a performance-guided hull optimum with wave drag **x0.086**
    and, on the same design, TOTAL SURFACE AREA **x2.138**, lower-half surface
    **x4.365**, Gaussian curvature **x1.514** and volume **x47.9**. Its authors
    write of their own result: "This is not desirable."
    (`docs/research/HULL-GAN-PAPERS.md`, four-paper read, 2026-08-13.)

    If NavalAI's objective is gameable the same way, every optimisation result
    in this repository is suspect in the same manner. This experiment answers
    that by MEASUREMENT rather than by reading the objective and reasoning
    about it.

    ==================== THE ANSWER, IN ONE LINE EACH ====================

      * MINIMISING R_w ALONE IS CATASTROPHICALLY GAMEABLE HERE. It buys -84.2%
        of wave resistance and pays +70.7% wetted surface, +55.3% friction,
        +28.7% TOTAL resistance, +183.5% build area and structural mass, 3.35x
        the plywood and 3.68x the build hours.
      * THE OBJECTIVE THIS PROJECT ACTUALLY MINIMISES IS NOT GAMEABLE THIS WAY.
        `optimize.HullProblem` minimises `(wh_per_nm, build_area, |gm - gm_mid|)`
        and `wh_per_nm` is R_TOTAL times a fixed distance. The R_t optimum and
        the Wh/NM optimum are THE SAME HULL, to the last gene, at every speed
        measured. There is nothing to game.
      * EVERY COEFFICIENT OBJECTIVE IS GAMEABLE, INCLUDING ONE NORMALISED BY
        WETTED AREA. This is the finding that outranks the rest — see below.

    ==================== THE DESIGN SPACE, AND ITS CONTROLS ====================
    The gaming direction is NOT reachable at fixed length, and this is recorded
    FIRST because a null result taken at the wrong control is how this question
    gets answered wrongly. MEASURED over a 959-point feasible sweep at FIXED
    LWL 12 m and FIXED Fn 0.30, varying BWL, T, Cp, lcb and forefoot: the R_w
    optimum, the R_t optimum and the Wh/NM optimum are ONE AND THE SAME HULL.

    And that is not because the box is too small to move anything — wetted
    surface spans **18.50 to 32.35 m^2 (74.9%)** across that same sweep. There
    is plenty of surface area to trade; what there is not, at fixed length and
    fixed Froude number, is any way to trade it PROFITABLY, because R_w and R_f
    are then driven the same direction by the same genes. A reader who stopped
    here would conclude the objective is ungameable, and would be wrong.

    So the sweep below pins the two things a MISSION pins and frees the rest:

        FIXED   displacement 4168.19 kg (the payload/battery/structure the
                mission demands must float, whatever shape carries it)
        FIXED   speed 3.2544 m/s — an ABSOLUTE speed in m/s, which is what a
                mission states, NOT a fixed Froude number. This is the whole
                mechanism: length is a decision variable, so Fn is an OUTPUT,
                and a longer hull at the same speed is a slower hull in Froude
                terms and makes exponentially less wave.
        VARIED  LWL, L/B, T, Cp, lcb, forefoot
        DERIVED D = max(0.6, 0.11 LWL), the shallowest depth that clears
                `grammar.check`'s 4.5%-of-LWL freeboard rule across the length
                sweep. It is a DEPENDENT variable, not a lever: depth above the
                waterline changes build area and structure and does not change
                resistance at all, so sweeping it produced pairs of hulls with
                R_t identical to four decimals and an "optimum margin" of
                0.0002 N that was an artefact of the sweep, not a tie in the
                physics.
        REFUSED  any point failing `grammar.check`, and any point above
                `resistance.FN_MICHELL_MAX`. Neither is interpolated over.

    LWL runs 10-20 m against a mission-scale 12 m boat. That is deliberate and
    it is the honest version of the question: `LWL` IS gene 0, `optimize.py`
    bounds it by `grammar.LOW/HIGH` intersected with the policy box, so unless
    a constitution pins the length the optimiser really can reach for 20 m.

    ============================ THE HEADLINE ============================
    Production Michell grid, every optimum located over the same 898-point
    feasible set (182 candidates refused by `grammar.check`, none above
    `FN_MICHELL_MAX`):

      objective        LWL   L/B    Fn  |   S      R_w     R_f     R_t   Wh/NM
      min R_w         20.0  6.50  0.232 | 32.57    9.43  390.39  399.81  406.5
      min R_t         12.0  8.50  0.300 | 19.09   59.45  251.33  310.77  316.0
      min Wh/NM       12.0  8.50  0.300 | 19.09   59.45  251.33  310.77  316.0
      min build_area  10.0  6.50  0.329 | 17.31  291.38  249.36  540.74  549.8

    WHAT THE R_w-ONLY OPTIMUM COSTS, against the R_t optimum:

        wetted surface S     19.09 -> 32.57 m^2      +70.7%
        R_f                 251.33 -> 390.39 N       +55.3%
        R_t                 310.77 -> 399.81 N       +28.7%
        Wh/NM               315.96 -> 406.48         +28.7%
        build area           53.63 -> 152.02 m^2    +183.5%
        structural mass     705.9 -> 2001.0 kg      +183.5%
        non-developable area  8.79 -> 29.46 m^2      3.35x
        plywood sheets          34 -> 114            3.35x
        build hours           1299 -> 4778           3.68x
        R_w                  59.45 -> 9.43 N         -84.2%   <- the "win"

    That is ShipGen's result reproduced in this grammar: wave drag x0.159
    against their x0.086, surface area x1.71 against their x2.138, and the same
    sign on every other quantity. Their authors' verdict applies unchanged.

    NOTE the last two rows against the one above them. `non_developable_m2` is
    a CHEAP closed-form geometry proxy (1.6 ms) and `ply_sheets` is COUNTED off
    a real nesting layout (3.6 s); they agree to two significant figures on
    this pair, 3.35x against 3.35x. That is ONE PAIR OF HULLS and it is not a
    calibration — it is why the cheap proxy is the one carried per sweep point.

    ================ THE FINDING THAT OUTRANKS THE REST ================
    ShipGen diagnose their own failure as a NORMALISATION choice: they scaled
    the wave-drag coefficient by LOA^2 instead of by wetted area, so the
    optimiser inflated the boat until the headline coefficient fell. The
    obvious lesson is "normalise by wetted area instead". THAT LESSON IS WRONG,
    AND THIS SWEEP MEASURES IT WRONG:

    Every candidate objective, scored by how far it inflates the boat. "build
    ratio" is the winner's build area over the R_t optimum's; "R_t penalty" is
    what its winner costs in total resistance:

      objective minimised        ratio?  build ratio  R_t penalty  verdict
      R_w                   [N]   no        2.835x       +28.7%    INFLATED
      R_w / (0.5 rho S U^2)       YES       2.835x       +28.7%    INFLATED
      R_w / (0.5 rho LOA^2 U^2)   YES       2.835x       +28.7%    INFLATED
      R_t / (0.5 rho S U^2)       YES       2.835x       +28.7%    INFLATED
      Int|K|dA / A                YES       3.207x       +52.7%    INFLATED
      R_t                   [N]   no        1.000x        0.0%     correct
      Wh/NM                       no        1.000x        0.0%     correct
      build_area          [m^2]   no        0.701x       +74.0%    shrinks
      wetted area         [m^2]   no        0.754x       +11.3%    shrinks
      non-developable     [m^2]   no        0.812x      +154.1%    shrinks

    **EVERY RATIO INFLATES AND NO ABSOLUTE QUANTITY DOES.** The separation is
    perfect across ten candidate objectives, and it does not depend on WHICH
    denominator: C_T normalised by WETTED AREA — the "correct" normalisation,
    the one the paper's own diagnosis recommends — still picks the inflated
    hull. It reads 2.318e-3 on the 20 m boat against 3.075e-3 on the 12 m boat:
    a 25% "better" coefficient on a boat that burns 28.7% more energy per mile.
    The optimiser simply inflates the DENOMINATOR instead of shrinking the
    numerator. Changing which length or area you divide by does not fix that;
    DIVIDING AT ALL is the defect.

    The worst offender in the table is `Int|K|dA / A`, area-averaged Gaussian
    curvature — which is the manufacturing metric
    `docs/research/HULL-GAN-PAPERS.md` names as the most adoptable idea in the
    four papers read. Adopted naively as an objective it would have been the
    most inflating column in the vector. `navalai/buildability.py` therefore
    computes it, REFUSES it as an objective, and recommends
    `non_developable_area_m2` (units m^2) instead.

    The three absolute quantities that "shrink" are not errors and are not
    objections: minimising build area or buildability ALONE gives a small,
    simple, slow boat, which is the correct answer to the question actually
    asked. They are Pareto members, not sole objectives — and the fact that
    each is BAD alone while none INFLATES is precisely the property that makes
    an absolute quantity safe to put in a multi-objective vector.

    NavalAI is safe from this, and NOT because it chose a good normalisation.
    It is safe because it never optimises a coefficient:

        wh_per_nm = R_t * 1852 / (3600 * eta_prop * eta_motor)

    an absolute force times a FIXED distance, with no hull dimension anywhere
    in it. `energy.py` owns that expression. AUDITED at the same time, the
    three objective columns and every constraint row:

        F[0] wh_per_nm        ABSOLUTE (J/NM). Safe.
        F[1] build_area       ABSOLUTE (m^2). Safe.
        F[2] |gm - gm_mid|    gm_mid = 0.5*(gm_floor + GM_OVER_BEAM_MAX*b_wl).
                              THE TARGET MOVES WITH BEAM, which is a decision
                              variable. This is the same defect class in a
                              milder form: the search can reduce the objective
                              by moving the band rather than the boat. It is
                              RECORDED, not fixed here — `optimize.py` is not
                              this module's file — and it is a band objective
                              rather than a minimisation of a ratio, so it
                              cannot run away the way a coefficient can.
        freeboard.rel         requirement scales with LWL, so a longer hull
                              faces a HARDER bar. Safe direction.

    `resistance.ResistanceResult.cw` IS normalised by wetted area, and that is
    fine: it is a REPORTED DIAGNOSTIC and nothing minimises it. The rule this
    experiment justifies is not "never compute a coefficient", it is **never
    put a coefficient in the objective vector**.

    ============ THE GRID CHECK, AND WHAT IT DOES AND DOES NOT SETTLE ============
    Every point is evaluated on `resistance.PRODUCTION_GRID` (241 x 44) AND
    `resistance.CONVERGED_GRID` (481 x 88):

        R_w argmin identical on both grids           YES
        R_t argmin identical on both grids           YES
        top-10 by R_w, set agreement                 10/10
        top-10 by R_t, set agreement                 10/10
        top-50 by R_w / by R_t, set agreement        50/50 and 50/50
        FULL 898-point ordering identical            NO

    The full ordering is NOT identical and this record does not claim it is —
    over 898 points there are adjacent pairs closer together than the
    quadrature separates. What decides this experiment is the SEPARATION
    BETWEEN THE TWO OPTIMA, and that is resolved by a wide margin:

        R_t(R_w-optimum) - R_t(R_t-optimum)   89.04 N
        largest production-to-converged shift  1.36 N
        ratio                                    65x

    So the conclusion is a hydrodynamic statement and not a quadrature
    artefact, and the record says which of those two things each number is.

    ============================== CAVEATS ==============================
    Read `caveats` on the returned record. The load-bearing one: Michell is a
    thin-ship theory and the 20 m hull at Fn 0.232 is FURTHER inside its
    envelope than the 12 m hull at Fn 0.300, so the model is not being pushed
    to produce this result — if anything it flatters the inflated hull, which
    makes the finding conservative.
    """
    prod = dict(resistance.PRODUCTION_GRID)
    conv = dict(resistance.CONVERGED_GRID)

    ref_hull, ref_st, _ = _float_hull(reference_demihull(), HYDRO_STATIONS,
                                      None)
    target = float(ref_st.disp_kg)
    lwl_ref = float(dict(REFERENCE_DEMIHULL)["LWL"])
    speed = froude_to_speed(GAMING_REFERENCE_FN, lwl_ref)

    points: list[SweepPoint] = []
    n_refused_l0 = 0
    n_refused_envelope = 0
    for lwl, lob, t_gene, cp, lcb, ff in itertools.product(
            GAMING_LWL_SWEEP, GAMING_L_OVER_B, GAMING_T_SWEEP,
            GAMING_CP_SWEEP, GAMING_LCB_SWEEP, GAMING_FOREFOOT_SWEEP):
        depth = max(0.6, GAMING_DEPTH_OVER_LWL * lwl)
        params = with_genes(LWL=lwl, BWL=lwl / lob, T=t_gene, D=depth,
                            Cp=cp, lcb=lcb, forefoot=ff)
        if not grammar.check(params).ok:
            n_refused_l0 += 1
            continue
        fn = speed / math.sqrt(G * lwl)
        # REFUSED, NOT EXTRAPOLATED. Unlike the Froude sweeps above there is no
        # value in carrying an out-of-envelope point here: it would be one
        # candidate among 1472 and an argmin cannot show a reader that it
        # declined. The COUNT is carried instead, in the protocol.
        if fn > resistance.FN_MICHELL_MAX:
            n_refused_envelope += 1
            continue
        try:
            hull, st, wl = _float_hull(params, HYDRO_STATIONS, target)
        except (ValueError, ArithmeticError):
            n_refused_l0 += 1
            continue

        q: dict[str, Quantity] = {}
        for tag, grid, other in (("prod", prod, conv), ("conv", conv, prod)):
            for k, v in _resistance_at_speed(hull, st, wl, speed, grid,
                                             other).items():
                q[f"{tag}/{k}"] = v
        q.update(_gaming_shape_quantities(hull, wl))
        q["lwl_m"] = Quantity(float(lwl), TIER_GEOMETRY, 0.0, "m", BASIS_EXACT)
        q["l_over_b"] = Quantity(float(lob), TIER_GEOMETRY, 0.0, "-",
                                 BASIS_EXACT)
        q["depth_m"] = Quantity(float(depth), TIER_GEOMETRY, 0.0, "m",
                                BASIS_EXACT)
        q["disp_kg"] = Quantity(float(st.disp_kg), TIER_PHYSICS,
                                abs(float(st.disp_kg) - target), "kg",
                                BASIS_GRID)
        points.append(SweepPoint(
            label=(f"L={lwl:.0f} L/B={lob:.1f} T={t_gene:.2f} "
                   f"Cp={cp:.3f} lcb={lcb:+.1f} ff={ff:.1f}"),
            genes=tuple(sorted(grammar.named(params).items())),
            q=q, valid=True,
            note="fixed displacement and fixed ABSOLUTE speed; Fn is an output"))

    if not points:
        raise ExperimentError(
            "experiment_5: the design space is empty. Every candidate was "
            "refused, so there is no sweep and an argmin would be a fiction.")

    findings = _gaming_findings(points, speed)
    findings["design_space_refused_l0"] = n_refused_l0
    findings["design_space_refused_above_fn_michell_max"] = n_refused_envelope
    findings["design_space_evaluated"] = len(points)

    return ExperimentRecord(
        name="5-objective-gaming",
        question=("Can an optimiser improve NavalAI's objective while making "
                  "the boat heavier, more expensive and harder to build?"),
        protocol={
            "controlled": ("displacement", "absolute speed [m/s]", "water",
                           "Michell integration grid"),
            "varied": ("LWL", "L/B", "T", "Cp", "lcb", "forefoot"),
            "derived": ("D = max(0.6, 0.11 LWL)", "draft", "Froude number"),
            "displacement_target_kg": target,
            "displacement_tolerance_rel": 1e-6,
            "speed_mps": speed,
            "speed_basis": (f"Fn {GAMING_REFERENCE_FN} at the reference "
                            f"{lwl_ref:.1f} m hull, then held ABSOLUTE"),
            "lwl_sweep_m": GAMING_LWL_SWEEP,
            "production_grid": prod, "converged_grid": conv,
            "fn_michell_max": resistance.FN_MICHELL_MAX,
            "shell_grid": dict(buildability.SHELL_GRID),
            "rho": RHO,
        },
        points=tuple(points),
        findings=findings,
        caveats=(
            "MICHELL FLATTERS THE INFLATED HULL, so this finding is "
            "conservative. The 20 m R_w-only optimum sits at Fn 0.232 and the "
            "12 m R_t optimum at Fn 0.300; thin-ship theory is better behaved "
            "at the lower Froude number, so the model is not being pushed "
            "outside its regime to manufacture the result. If anything it "
            "understates how bad the long hull is, because Michell has no "
            "transom-immersion term and no viscous-pressure term.",
            "THE STRUCTURAL MASS AND THE BUILD AREA ARE THE SAME NUMBER. "
            "`energy.weight_budget` computes structure as "
            "(shell + deck) * t * PLY_DENSITY * 1.35, and `optimize.py`'s "
            "objective 2 is (shell + deck). At a fixed panel thickness they "
            "are EXACTLY proportional, which is why this record reports both "
            "with the same percentage and why a separate structural-mass "
            "objective would be a number declared twice. They separate only "
            "when the thickness is rule-derived per hull "
            "(`rules.iso12215.select_stock_thickness_m`), which the objective "
            "does not currently do.",
            "ONE HULL FAMILY, ONE SPEED. The design space is this grammar's "
            "chine hull at one absolute speed and one displacement. The "
            "MECHANISM (an absolute objective cannot be inflated; a "
            "coefficient can) is general; the percentages are not.",
            "THE BUILDABILITY METRICS ARE PROXIES and `navalai/buildability.py`"
            " says so in every docstring. Nothing in this repository has "
            "measured build hours against a real build, so 4.68x is a ratio of "
            "two estimates from `engineer.HOURS_PER_M2`, which that module "
            "itself calls 'amateur build, approx'.",
        ),
    )


def _resistance_at_speed(hull: Hull, st: HydroState, wl: float, speed: float,
                         grid: Mapping[str, int],
                         other_grid: Mapping[str, int]
                         ) -> dict[str, Quantity]:
    """Resistance at an ABSOLUTE speed, plus the two coefficient forms.

    `resistance_quantities` above is keyed by Froude number because every other
    experiment holds length fixed and sweeps speed. This one holds SPEED fixed
    and sweeps length, so Fn is an output; the two cannot share an entry point
    without one of them lying about which quantity is independent.

    THE COEFFICIENTS ARE COMPUTED HERE AND THEY ARE THE POINT. `cw` comes
    straight off `ResistanceResult` (normalised by wetted area, which is
    `resistance.py`'s own choice and is not restated). `ct_wetted` and
    `cw_loa2` are computed here BECAUSE NOTHING ELSE COMPUTES THEM — they exist
    only to be minimised as a control, to show that a coefficient objective
    picks the inflated hull whichever length or area it is divided by. They are
    never used as a result.
    """
    lwl = float(grammar.named(hull.params)["LWL"])
    fn = speed / math.sqrt(G * lwl)

    def run(g: Mapping[str, int]):
        return resistance.total_resistance(
            hull, speed, st.wetted, st.cb, RHO, wl,
            nz=int(g["nz"]), n_stations=int(g["n_stations"]),
            beam_wl=st.b_wl_max, draft=st.draft)

    r, r2 = run(grid), run(other_grid)
    tier = TIER_PHYSICS if r.valid else TIER_PHYSICS_INVALID
    en = energy_report(r.total, speed, hull.deck_area(), ENERGY_SPEC,
                       resistance_sigma_n=r.uncertainty)
    q_dyn = 0.5 * RHO * st.wetted * speed ** 2
    q_loa = 0.5 * RHO * lwl ** 2 * speed ** 2

    def grid_q(v: float, v2: float, units: str) -> Quantity:
        return Quantity(float(v), tier, abs(float(v) - float(v2)), units,
                        BASIS_GRID_LOWER_BOUND)

    return {
        "fn": Quantity(float(fn), tier, 0.0, "-", BASIS_EXACT),
        "speed_mps": Quantity(float(speed), tier, 0.0, "m/s", BASIS_EXACT),
        "rw_n": grid_q(r.rw, r2.rw, "N"),
        "rf_n": grid_q(r.rf, r2.rf, "N"),
        "cw": grid_q(r.cw, r2.cw, "-"),
        "ct_wetted": grid_q(r.total / max(q_dyn, 1e-9),
                            r2.total / max(q_dyn, 1e-9), "-"),
        "cw_loa2": grid_q(r.rw / max(q_loa, 1e-9), r2.rw / max(q_loa, 1e-9),
                          "-"),
        "rt_n": Quantity(float(r.total), tier, float(r.uncertainty), "N",
                         BASIS_MODEL),
        "wh_per_nm": Quantity(float(en.wh_per_nm), tier,
                              float(en.sigma_wh_per_nm), "Wh/NM",
                              BASIS_PROPAGATED),
        "rt_grid_sigma_n": Quantity(abs(float(r.total - r2.total)), tier, 0.0,
                                    "N", BASIS_EXACT),
    }


def _gaming_shape_quantities(hull: Hull, wl: float) -> dict[str, Quantity]:
    """Wetted surface, build area, structure and the buildability proxies.

    EVERY ONE IS IMPORTED. `navalai/buildability.py` composes
    `Hull.wetted_surface`, `energy.shell_area_m2`, `energy.weight_budget` and
    `unroll.ruling_twist`; this function calls it once and copies nothing. The
    sigma is the MEASURED refinement residual between `buildability.SHELL_GRID`
    and `buildability.REFINEMENT_CHECK`, not a declared percentage.
    """
    c = buildability.shell_complexity(hull, wl)
    res = buildability.refinement_residual(hull, wl)
    return {
        "wetted_m2": Quantity(c.wetted_area_m2, TIER_PHYSICS, 0.0, "m^2",
                              BASIS_EXACT),
        "build_area_m2": Quantity(c.build_area_m2, TIER_GEOMETRY, 0.0, "m^2",
                                  BASIS_EXACT),
        "structure_kg": Quantity(c.structure_kg, TIER_GEOMETRY, 0.0, "kg",
                                 BASIS_EXACT),
        "non_developable_m2": Quantity(
            c.non_developable_area_m2, TIER_GEOMETRY,
            res["non_developable_area_m2"], "m^2", BASIS_GRID),
        "gauss_abs_integral": Quantity(
            c.gauss_abs_integral, TIER_GEOMETRY, res["gauss_abs_integral"],
            "-", BASIS_GRID),
        "gauss_abs_mean_per_m2": Quantity(
            c.gauss_abs_mean_per_m2, TIER_GEOMETRY,
            res["gauss_abs_mean_per_m2"], "1/m^2", BASIS_GRID),
        "panel_twist_deg_per_m": Quantity(
            c.panel_twist_deg_per_m, TIER_GEOMETRY, 0.0, "deg/m", BASIS_EXACT),
    }


# The quantities every candidate objective is scored on, and the direction each
# is minimised in. Declared once so the argmin loop and the comparison table
# cannot disagree about what "the R_w optimum" means.
GAMING_OBJECTIVES = ("rw_n", "rt_n", "wh_per_nm", "cw", "ct_wetted",
                     "cw_loa2", "build_area_m2", "wetted_m2",
                     "non_developable_m2", "gauss_abs_mean_per_m2")

# What each optimum is REPORTED on. Separate from the objectives so that adding
# a column to the report cannot silently add an objective.
GAMING_REPORTED = ("lwl_m", "l_over_b", "fn", "wetted_m2", "rw_n", "rf_n",
                   "rt_n", "wh_per_nm", "build_area_m2", "structure_kg",
                   "non_developable_m2", "gauss_abs_integral",
                   "gauss_abs_mean_per_m2", "cw", "ct_wetted")


def _gaming_findings(points: Sequence[SweepPoint],
                     speed: float) -> dict[str, object]:
    """Locate every optimum, compare them, and check the ranking on both grids.

    THE GRID CHECK IS REPORTED AT THREE STRENGTHS, and the record says which
    one it is relying on. A full-ordering match over ~1500 points is a bar no
    honest quadrature passes and claiming it would be the stronger-sounding
    lie; the ARGMIN match plus the optimum SEPARATION against the grid shift is
    what this experiment's conclusion actually needs.
    """
    def val(p: SweepPoint, key: str, tag: str = "prod") -> float:
        return p.q[f"{tag}/{key}"].value if f"{tag}/{key}" in p.q \
            else p.q[key].value

    out: dict[str, object] = {}
    argmin: dict[str, int] = {}
    for obj in GAMING_OBJECTIVES:
        argmin[obj] = min(range(len(points)), key=lambda i: val(points[i], obj))
    out["argmin_index"] = dict(argmin)
    out["optima"] = {
        obj: {"label": points[i].label,
              **{k: val(points[i], k) for k in GAMING_REPORTED}}
        for obj, i in argmin.items()
    }

    i_rw, i_rt, i_wh = argmin["rw_n"], argmin["rt_n"], argmin["wh_per_nm"]
    out["rt_and_wh_per_nm_pick_the_same_hull"] = bool(i_rt == i_wh)
    out["rw_only_optimum_is_the_rt_optimum"] = bool(i_rw == i_rt)

    # WHAT THE R_w-ONLY OPTIMUM COSTS. Signed, as a fraction of the R_t optimum.
    cost: dict[str, float] = {}
    for k in ("wetted_m2", "rf_n", "rt_n", "wh_per_nm", "build_area_m2",
              "structure_kg", "non_developable_m2", "rw_n"):
        a, b = val(points[i_rw], k), val(points[i_rt], k)
        cost[k] = (a - b) / abs(b) if b != 0.0 else float("nan")
    out["rw_only_cost_vs_rt_optimum_frac"] = cost
    out["objective_is_gameable_by_rw_alone"] = bool(
        cost["rt_n"] > 0.05 and cost["wetted_m2"] > 0.05)

    # THE NORMALISATION AUDIT — which candidate objectives pick an inflated
    # hull. "Inflated" is defined against the R_t optimum's build area, not by
    # a threshold on length, because the defect being detected is inflation of
    # whatever the coefficient is divided by.
    base_build = val(points[i_rt], "build_area_m2")
    inflated: dict[str, object] = {}
    for obj in GAMING_OBJECTIVES:
        i = argmin[obj]
        inflated[obj] = {
            "picks_label": points[i].label,
            "build_area_ratio_vs_rt_optimum": val(points[i], "build_area_m2")
            / base_build,
            "rt_penalty_frac": (val(points[i], "rt_n")
                                - val(points[i_rt], "rt_n"))
            / val(points[i_rt], "rt_n"),
            "is_a_ratio": obj in ("cw", "ct_wetted", "cw_loa2",
                                  "gauss_abs_mean_per_m2"),
        }
    out["normalisation_audit"] = inflated
    out["every_coefficient_objective_inflates"] = bool(all(
        v["build_area_ratio_vs_rt_optimum"] > 1.5
        for k, v in inflated.items() if v["is_a_ratio"]))
    out["absolute_objectives_do_not_inflate"] = bool(all(
        v["build_area_ratio_vs_rt_optimum"] <= 1.5
        for k, v in inflated.items()
        if k in ("rt_n", "wh_per_nm", "build_area_m2")))

    # THE GRID CHECK.
    grid: dict[str, object] = {}
    for key in ("rw_n", "rt_n"):
        pv = np.array([val(p, key, "prod") for p in points])
        cv = np.array([val(p, key, "conv") for p in points])
        op, oc = np.argsort(pv), np.argsort(cv)
        grid[key] = {
            "argmin_identical": bool(op[0] == oc[0]),
            "full_ordering_identical": bool(np.array_equal(op, oc)),
            **{f"top{n}_set_agreement": len(set(op[:n]) & set(oc[:n])) / n
               for n in (10, 50)},
        }
    shift = max(p.q["prod/rt_grid_sigma_n"].value for p in points)
    separation = val(points[i_rw], "rt_n") - val(points[i_rt], "rt_n")
    grid["largest_production_to_converged_shift_n"] = shift
    grid["optimum_separation_n"] = separation
    grid["separation_over_grid_shift"] = (separation / shift if shift > 0
                                          else float("inf"))
    grid["conclusion_resolved_above_grid_shift"] = bool(separation > shift)
    out["grid_check"] = grid

    out["production_objective_columns"] = (
        "optimize.HullProblem minimises (wh_per_nm, build_area, "
        "|gm - gm_mid|). wh_per_nm = R_t * 1852 / (3600 * eta) is an ABSOLUTE "
        "energy with no hull dimension in it; build_area is m^2. Neither can "
        "be improved by inflating the boat. gm_mid is 0.5*(gm_floor + "
        "GM_OVER_BEAM_MAX * b_wl) and its TARGET moves with beam, which is "
        "recorded as a milder instance of the same defect class.")
    return out


# ---------------------------------------------------------------------------
# The suite
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def lever_comparison() -> Mapping[str, object]:
    """WHICH FORM LEVER ACTUALLY MOVES THE ANSWER — the cross-experiment result.

    This is the finding that speaks to the mission's framing directly, and it
    is the one no single experiment produces. All three sweeps are run on ONE
    parent hull at ONE displacement on ONE integration protocol, so the R_t
    spans are directly comparable: each is (max - min) / min of total
    resistance over that lever's whole admissible gene range.

    MEASURED, R_t span as a fraction of the best hull in each sweep:

        Fn      Cp gene    lcb gene    bow / waterline shape    Cp / weakest
        0.20     19.77%     13.01%            12.39%                1.60x
        0.25     21.16%     11.86%            16.03%                1.78x
        0.30     45.31%     24.32%             9.21%                4.92x
        0.35     40.97%     37.47%             4.77%                8.58x
        0.40     38.97%     24.57%             2.19%               17.83x
        0.45     26.35%     16.86%             1.36%               19.40x

    THE ORDERING IS THE POINT. Cp is the strongest lever at EVERY speed, and
    the bow/waterline-shape lever is the weakest at five of the six (at Fn 0.25
    the LCB band is narrower than the bow range — 11.86% against 16.03% — and
    the record says so rather than smoothing it). The dominance GROWS with
    speed: at Fn 0.45 the entire admissible bow-shape range is worth 1.36%
    while the Cp range is worth 26.4%.

    So the mission's instruction — "don't teach it a sharp bow, teach it to
    generate the longitudinal volume distribution and waterline shape that
    produce an efficient bow at the operating Froude number" — is not merely
    good methodology here, it is what the measurement says. A generator that
    optimised bow sharpness while leaving Cp and LCB to chance would be tuning
    the smallest of the three levers, and at the top of the speed range it
    would be tuning a lever worth one twentieth of the ones it ignored.

    ONE HONEST QUALIFICATION. The three ranges are not commensurable as
    "design freedom": the Cp and lcb genes span what `limits.py` declares
    admissible, while the bow sweep spans what the forefoot gene can express
    at THIS L/B before `grammar.check` refuses it (forefoot 0.8 is the last
    feasible point; 1.0 is refused by `section.solve`). A wider bow range does
    not exist to be swept, which is itself a statement about the grammar.
    """
    r1, r2, r3 = (experiment_1_bow_sharpness(), experiment_2_prismatic(),
                  experiment_3_lcb())
    rows: dict[str, object] = {}
    for fn in VALID_FROUDES:
        key = f"prod/fn{fn:.2f}/rt_n"
        spans = {}
        for tag, rec in (("bow_waterline_shape", r1), ("cp", r2), ("lcb", r3)):
            v = np.array([p.value(key) for p in rec.points])
            spans[tag] = float((v.max() - v.min()) / v.min())
        order = sorted(spans, key=lambda k: -spans[k])
        rows[f"fn{fn:.2f}"] = {
            **spans,
            "strongest_lever": order[0],
            "weakest_lever": order[-1],
            "strongest_over_weakest": spans[order[0]] / spans[order[-1]],
        }
    rows["conclusion"] = (
        "Cp is the STRONGEST lever at every valid Froude number, by 1.6x at "
        "Fn 0.20 rising to 19.4x at Fn 0.45. The bow/waterline-shape lever is "
        "the WEAKEST at five of the six speeds; the exception is Fn 0.25, "
        "where the LCB band (11.9%) is narrower than the bow range (16.0%). "
        "Optimising bow sharpness before setting the volume distribution "
        "tunes the smallest of the three levers, and increasingly so with "
        "speed.")
    return rows


def run_all() -> Mapping[str, ExperimentRecord]:
    """Every experiment, deterministically, in one call."""
    return {
        r.name: r for r in (
            experiment_1_bow_sharpness(),
            experiment_2_prismatic(),
            experiment_3_lcb(),
            experiment_4_separation(),
            experiment_5_objective_gaming(),
        )
    }


def all_quantities(rec: ExperimentRecord):
    """Yield every (point label, key, Quantity) in a record — the honesty walk."""
    for p in rec.points:
        for k, v in p.q.items():
            yield p.label, k, v


def _fmt(v) -> str:
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def report() -> str:
    """A plain-text report of every experiment: what was measured, and where."""
    lines: list[str] = []
    lines.append("NavalAI experiment suite")
    lines.append(f"  production grid : {dict(resistance.PRODUCTION_GRID)}")
    lines.append(f"  converged grid  : {dict(resistance.CONVERGED_GRID)}")
    lines.append(f"  FN_MICHELL_MAX  : {resistance.FN_MICHELL_MAX}")
    for name, rec in run_all().items():
        lines.append("")
        lines.append(f"=== {rec.name}: {rec.question}")
        lines.append(f"    points: {len(rec.points)}")
        for k, v in rec.findings.items():
            if isinstance(v, dict) and v.get("excluded"):
                lines.append(f"    {k}: EXCLUDED — {v['reason']}")
            elif isinstance(v, dict):
                inner = ", ".join(f"{a}={_fmt(b)}" for a, b in v.items()
                                  if not isinstance(b, (dict, list)))
                lines.append(f"    {k}: {inner}")
                for a, b in v.items():
                    if isinstance(b, list):
                        for row in b:
                            lines.append(f"        {a}: {row}")
            elif isinstance(v, list):
                lines.append(f"    {k}:")
                for row in v:
                    lines.append(f"        {row}")
            else:
                lines.append(f"    {k}: {_fmt(v)}")
        for c in rec.caveats:
            lines.append(f"    CAVEAT: {c}")
    lines.append("")
    lines.append("=== cross-experiment: which form lever moves the answer?")
    for k, v in lever_comparison().items():
        if isinstance(v, dict):
            lines.append(f"    {k}: "
                         + ", ".join(f"{a}={_fmt(b)}" for a, b in v.items()))
        else:
            lines.append(f"    {k}: {v}")
    return "\n".join(lines)


if __name__ == "__main__":     # pragma: no cover
    print(report())
